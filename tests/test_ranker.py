import pytest

from ranker import rank_resumes
from tests.fake_model import FakeModel

JD = "Backend engineer. Python, Flask, REST API, AWS, Docker, SQL, Git."
STRONG = "Built Python Flask REST API services deployed on AWS with Docker. PostgreSQL, Git, CI/CD."
WEAK = "Managed social media campaigns, brand strategy and event planning."


def run(resumes, **kw):
    return rank_resumes(FakeModel(), JD, resumes, **kw)


def test_strong_resume_ranks_first_with_ranks_assigned():
    out = run([("weak.txt", WEAK), ("strong.txt", STRONG)])
    names = [r["filename"] for r in out["ranked_resumes"]]
    assert names == ["strong.txt", "weak.txt"]
    assert [r["rank"] for r in out["ranked_resumes"]] == [1, 2]


def test_matched_and_missing_skills_are_reported():
    out = run([("strong.txt", STRONG)])
    item = out["ranked_resumes"][0]
    assert {"python", "flask", "aws", "docker", "sql", "git"} <= set(item["matched_skills"])  # sql implied by PostgreSQL
    assert item["missing_skills"] == []
    assert "python" in item["explicit_matched_skills"]
    assert "sql" in item["implied_matched_skills"]
    weak = run([("weak.txt", WEAK)])["ranked_resumes"][0]
    assert "python" in weak["missing_skills"]


def test_blank_resume_is_skipped_not_fatal():
    out = run([("blank.txt", "   "), ("strong.txt", STRONG)])
    assert [r["filename"] for r in out["ranked_resumes"]] == ["strong.txt"]
    assert out["skipped"][0]["filename"] == "blank.txt"


def test_duplicate_filenames_are_both_ranked():
    out = run([("cv.txt", STRONG), ("cv.txt", WEAK)])
    assert len(out["ranked_resumes"]) == 2


def test_exact_ties_keep_input_order_instead_of_using_candidate_filename():
    out = rank_resumes(
        FakeModel(), "Python engineer", [("z_candidate.txt", "Python engineer"), ("a_candidate.txt", "Python engineer")]
    )
    assert [item["filename"] for item in out["ranked_resumes"]] == ["z_candidate.txt", "a_candidate.txt"]
    assert out["ranked_resumes"][0]["score"] == out["ranked_resumes"][1]["score"]


def test_empty_jd_and_all_blank_resumes_raise_value_error():
    with pytest.raises(ValueError):
        rank_resumes(FakeModel(), "  ", [("a.txt", STRONG)])
    with pytest.raises(ValueError):
        run([("a.txt", ""), ("b.txt", "  ")])


def test_jd_without_known_skills_uses_semantic_only():
    out = rank_resumes(FakeModel(), "We value curiosity and kindness.", [("a.txt", "curiosity and kindness")])
    assert out["jd_skills"] == []
    assert out["effective_semantic_weight"] == 1.0
    assert out["ranked_resumes"][0]["skill_score"] is None


def test_weighting_changes_scores_and_ranking_through_scoring_pipeline():
    jd = "We need Python and AWS to design distributed systems and build reliable production services."
    resumes = [
        ("semantic.txt", "We need to design distributed systems and build reliable production services."),
        ("skills.txt", "Python Python AWS AWS."),
    ]
    meaning_only = rank_resumes(FakeModel(), jd, resumes, semantic_weight=1.0)
    skills_only = rank_resumes(FakeModel(), jd, resumes, semantic_weight=0.0)
    assert meaning_only["ranked_resumes"][0]["filename"] == "semantic.txt"
    assert skills_only["ranked_resumes"][0]["filename"] == "skills.txt"
    assert meaning_only["ranked_resumes"][0]["score"] == meaning_only["ranked_resumes"][0]["semantic_score"]
    assert skills_only["ranked_resumes"][0]["score"] == skills_only["ranked_resumes"][0]["skill_score"]


def test_personal_fields_and_contact_data_do_not_reach_embedding_or_skill_scoring():
    class RecordingModel(FakeModel):
        def encode(self, texts, **kwargs):
            self.seen = list(texts)
            return super().encode(texts, **kwargs)

    model = RecordingModel()
    resume = "Name: Ada Lovelace\nEmail: ada@example.org\nPhone: +1 (555) 123-4567\nAge: 61\nGender: Female\nPython and FastAPI experience building web services."
    result = rank_resumes(model, "Python FastAPI backend services", [("candidate.txt", resume)])
    joined = " ".join(model.seen).lower()
    assert "ada lovelace" not in joined
    assert "ada@example.org" not in joined
    assert "555" not in joined
    assert "female" not in joined
    item = result["ranked_resumes"][0]
    assert {"python", "fastapi"} <= set(item["explicit_matched_skills"])


def test_long_resume_tail_still_counts():
    # The relevant skills sit far past 256 tokens, where plain encode() would truncate.
    filler = "lorem ipsum dolor sit amet " * 120
    long_resume = filler + " Python Flask REST API AWS Docker SQL Git"
    out = run([("long.txt", long_resume), ("weak.txt", WEAK)])
    assert out["ranked_resumes"][0]["filename"] == "long.txt"
