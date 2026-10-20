"""
Ranking pipeline: ties the pure helpers in scoring.py to an embedding model.

`model` can be anything with a SentenceTransformer-style
`encode(list_of_str, normalize_embeddings=..., batch_size=..., show_progress_bar=...)`
method, which is what lets the tests run with a tiny fake model instead of
downloading SBERT.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

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

_PERSONAL_FIELD = re.compile(
    r"^\s*(?:name|email|e-mail|phone|telephone|mobile|address|location|date of birth|dob|age|gender|sex|pronouns|nationality|citizenship|ethnicity|race|marital status|religion|disability|veteran status|photo|profile photo)\s*(?::|\||–|-)\s*",
    re.IGNORECASE,
)
_CONTACT_TOKEN = re.compile(
    r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|https?://\S+|(?:\+?\d[\d().\s-]{7,}\d)"
)


def _job_relevant_resume_text(text: str) -> str:
    """Remove labeled personal attributes and direct contact tokens before scoring."""
    relevant_lines = [line for line in text.splitlines() if not _PERSONAL_FIELD.match(line)]
    return _CONTACT_TOKEN.sub(" ", "\n".join(relevant_lines))


def rank_resumes(
    model: Any,
    jd_text: str,
    resumes: Sequence[Tuple[str, str]],
    semantic_weight: float = 0.6,
) -> Dict[str, Any]:
    """
    Rank `resumes` (a sequence of (filename, text)) against `jd_text`.

    Raises ValueError with a user-readable message if there is nothing to rank.
    """
    jd_chunks = chunk_text(jd_text)
    if not jd_chunks:
        raise ValueError("The job description is empty.")

    valid: List[Tuple[str, str, List[str]]] = []
    skipped: List[Dict[str, str]] = []
    for filename, text in resumes:
        scoring_text = _job_relevant_resume_text(text)
        chunks = chunk_text(scoring_text)
        if chunks:
            valid.append((filename, scoring_text, chunks))
        else:
            skipped.append({"filename": filename, "reason": "No readable text found in this file."})

    if not valid:
        raise ValueError("None of the resumes contained readable text.")

    # One encode() call for everything is much faster than one call per resume.
    all_chunks = jd_chunks + [c for _, _, chunks in valid for c in chunks]
    vectors = np.asarray(
        model.encode(
            all_chunks,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
    )
    vectors = l2_normalize(vectors)

    jd_vectors = vectors[: len(jd_chunks)]
    offset = len(jd_chunks)
    jd_skills = extract_skills(jd_text)

    results: List[Dict[str, Any]] = []
    for filename, text, chunks in valid:
        resume_vectors = vectors[offset: offset + len(chunks)]
        offset += len(chunks)

        raw = coverage_similarity(jd_vectors, resume_vectors)
        semantic = calibrate(raw)

        explicit_resume_skills = extract_skills(text)
        resume_skills = expand_implied(explicit_resume_skills)
        skills = skill_score(jd_skills, resume_skills)
        final = combine(semantic, skills, semantic_weight)
        matched_skills = jd_skills & resume_skills

        results.append(
            {
                "filename": filename,
                "score": round(final, 4),
                "semantic_score": round(semantic, 4),
                "skill_score": None if skills is None else round(skills, 4),
                "raw_similarity": round(raw, 4),
                "matched_skills": sorted(matched_skills),
                "explicit_matched_skills": sorted(jd_skills & explicit_resume_skills),
                "implied_matched_skills": sorted(matched_skills - explicit_resume_skills),
                "missing_skills": sorted(jd_skills - resume_skills),
            }
        )

    # Stable sort keeps input order for an otherwise exact tie. Filenames may
    # contain candidate names, so they must not decide who ranks higher.
    results.sort(key=lambda r: (-r["score"], -r["raw_similarity"]))
    for position, item in enumerate(results, start=1):
        item["rank"] = position

    return {
        "ranked_resumes": results,
        "jd_skills": sorted(jd_skills),
        "skipped": skipped,
        # 1.0 when the JD named no recognisable skills (semantic score only).
        "effective_semantic_weight": 1.0 if not jd_skills else float(np.clip(semantic_weight, 0.0, 1.0)),
    }
