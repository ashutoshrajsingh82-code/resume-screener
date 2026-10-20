import numpy as np
import pytest

from scoring import (
    calibrate,
    chunk_text,
    combine,
    coverage_similarity,
    expand_implied,
    extract_skills,
    l2_normalize,
    skill_score,
)


# ---- chunking ----
def test_chunk_empty_text_gives_no_chunks():
    assert chunk_text("   \n ") == []


def test_chunk_short_text_is_one_chunk():
    assert chunk_text("a b c") == ["a b c"]


def test_chunk_long_text_covers_every_word_and_respects_size():
    words = [f"w{i}" for i in range(400)]
    chunks = chunk_text(" ".join(words), size=150, overlap=30)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 150 for c in chunks)
    assert {w for c in chunks for w in c.split()} == set(words)


def test_chunk_rejects_overlap_not_smaller_than_size():
    with pytest.raises(ValueError):
        chunk_text("a b c", size=10, overlap=10)


# ---- skills ----
def test_extract_common_skills():
    found = extract_skills("Python, Flask, REST APIs, AWS/GCP, Docker, Git, CI/CD and SQL.")
    assert {"python", "flask", "rest api", "aws", "gcp", "docker", "git", "ci/cd", "sql"} <= found


def test_java_does_not_match_javascript_and_sql_does_not_match_mysql():
    assert "java" not in extract_skills("I write JavaScript daily")
    assert "sql" not in extract_skills("I use MySQL")
    assert "mysql" in extract_skills("I use MySQL")


def test_special_character_skills():
    found = extract_skills("Experienced in C++ and C#, plus Node.js")
    assert {"c++", "c#", "node.js"} <= found


def test_hyphenated_and_spaced_spellings_match():
    assert "scikit-learn" in extract_skills("Trained models with scikit-learn")
    assert "scikit-learn" in extract_skills("Trained models with scikit learn")


def test_implied_skills_apply_to_resumes():
    found = extract_skills("Built services with PostgreSQL and Django")
    assert "sql" not in found
    assert {"sql", "python"} <= expand_implied(found)


def test_no_false_positive_on_plain_prose():
    assert extract_skills("Managed social media campaigns and brand strategy") == set()


# ---- scores ----
def test_skill_score_fraction_and_none():
    assert skill_score({"python", "sql", "aws", "git"}, {"python", "git", "react"}) == 0.5
    assert skill_score(set(), {"python"}) is None


def test_calibrate_is_clamped_and_monotonic():
    assert calibrate(0.0) == 0.0
    assert calibrate(1.0) == 1.0
    assert calibrate(0.3) < calibrate(0.4)


def test_combine_weights():
    assert combine(0.8, 0.2, 1.0) == pytest.approx(0.8)
    assert combine(0.8, 0.2, 0.0) == pytest.approx(0.2)
    assert combine(0.8, 0.2, 0.5) == pytest.approx(0.5)
    assert combine(0.8, None, 0.1) == pytest.approx(0.8)  # nothing to blend


def test_coverage_prefers_resume_that_covers_every_jd_chunk():
    jd = l2_normalize(np.array([[1.0, 0.0], [0.0, 1.0]]))
    covers_both = l2_normalize(np.array([[1.0, 0.0], [0.0, 1.0]]))
    covers_one = l2_normalize(np.array([[1.0, 0.0], [1.0, 0.1]]))
    assert coverage_similarity(jd, covers_both) > coverage_similarity(jd, covers_one)
