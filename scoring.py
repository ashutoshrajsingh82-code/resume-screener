"""
Pure scoring helpers for the resume ranker.

Nothing in this module imports a web framework or an ML model, so everything
here can be unit-tested quickly (see tests/test_scoring.py).

The final score for a resume is a blend of two signals:

1. Semantic coverage - how well the resume's text covers each part of the job
   description, measured with sentence-embedding cosine similarity.
2. Skill coverage - what fraction of the skills named in the job description
   also appear in the resume (matched against a curated vocabulary).
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Set

import numpy as np

# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #
# all-MiniLM-L6-v2 only reads ~256 word pieces and silently drops the rest, so
# long texts are split into overlapping windows of words that fit under that.
CHUNK_WORDS = 150
CHUNK_OVERLAP = 30


def chunk_text(text: str, size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping windows of at most `size` words."""
    if size <= overlap:
        raise ValueError("size must be larger than overlap")
    words = text.split()
    if not words:
        return []
    if len(words) <= size:
        return [" ".join(words)]

    step = size - overlap
    chunks: List[str] = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
    return chunks


# --------------------------------------------------------------------------- #
# Semantic score
# --------------------------------------------------------------------------- #
# Raw cosine similarity between a job description and a resume rarely goes
# above ~0.6 even for a great match, and rarely drops below ~0.1. Showing the
# raw value as a percentage makes good candidates look bad, so it is stretched
# linearly between these two heuristic anchor points. These are tuning
# constants for all-MiniLM-L6-v2, not universal truths.
SIM_FLOOR = 0.15
SIM_CEIL = 0.65


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """Scale each row to unit length (rows of zeros are left as zeros)."""
    vectors = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def coverage_similarity(jd_vectors: np.ndarray, resume_vectors: np.ndarray) -> float:
    """
    For every chunk of the job description, find the best-matching chunk of the
    resume, then average those best matches. Both inputs must be unit vectors.

    A resume scores high when *each part* of the job description is covered
    somewhere in it, regardless of how long the resume is.
    """
    sims = jd_vectors @ resume_vectors.T  # (jd_chunks, resume_chunks)
    return float(sims.max(axis=1).mean())


def calibrate(similarity: float, floor: float = SIM_FLOOR, ceil: float = SIM_CEIL) -> float:
    """Map a raw cosine similarity onto 0..1 using the anchor points above."""
    return float(np.clip((similarity - floor) / (ceil - floor), 0.0, 1.0))


# --------------------------------------------------------------------------- #
# Skill extraction
# --------------------------------------------------------------------------- #
# canonical skill name -> spellings that count as that skill (lower-case).
# Hyphens/underscores are treated as spaces, so "scikit-learn" == "scikit learn".
SKILLS: Dict[str, List[str]] = {
    # languages
    "python": ["python", "python3"],
    "java": ["java"],
    "javascript": ["javascript", "ecmascript", "js"],
    "typescript": ["typescript"],
    "c++": ["c++"],
    "c#": ["c#"],
    ".net": [".net", "dotnet"],
    "go": ["golang"],
    "rust": ["rust"],
    "kotlin": ["kotlin"],
    "swift": ["swift"],
    "php": ["php"],
    "ruby": ["ruby"],
    "scala": ["scala"],
    "bash": ["bash", "shell scripting"],
    # frontend
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs"],
    "vue": ["vue", "vue.js", "vuejs"],
    "angular": ["angular"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "tailwind": ["tailwind", "tailwindcss"],
    # backend / APIs
    "node.js": ["node.js", "nodejs", "node js"],
    "express": ["express", "express.js", "expressjs"],
    "flask": ["flask"],
    "django": ["django"],
    "fastapi": ["fastapi"],
    "spring boot": ["spring boot", "springboot"],
    "rest api": ["rest api", "rest apis", "restful", "restful api", "restful apis"],
    "graphql": ["graphql"],
    "grpc": ["grpc"],
    "microservices": ["microservices", "microservice"],
    # data stores / messaging
    "sql": ["sql", "t sql", "pl/sql"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "sqlite": ["sqlite"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch"],
    "kafka": ["kafka"],
    "rabbitmq": ["rabbitmq"],
    "celery": ["celery"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "spark": ["spark", "pyspark"],
    # cloud / devops
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud"],
    "azure": ["azure"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "terraform": ["terraform"],
    "ci/cd": ["ci/cd", "ci cd", "cicd", "continuous integration", "continuous delivery"],
    "jenkins": ["jenkins"],
    "github actions": ["github actions"],
    "linux": ["linux"],
    "nginx": ["nginx"],
    # ML
    "machine learning": ["machine learning"],
    "deep learning": ["deep learning"],
    "nlp": ["nlp", "natural language processing"],
    "pytorch": ["pytorch"],
    "tensorflow": ["tensorflow"],
    "scikit-learn": ["scikit learn", "sklearn"],
    "llm": ["llm", "llms", "large language models"],
    # practices
    "git": ["git", "github", "gitlab", "bitbucket"],
    "agile": ["agile", "scrum"],
    "testing": ["unit testing", "pytest", "jest", "junit", "test driven development", "tdd"],
    "system design": ["system design"],
    "data structures": ["data structures", "algorithms"],
    "oop": ["oop", "object oriented"],
}

# Having the first skill is good evidence of the second ("knows PostgreSQL"
# => "knows SQL"). Applied to resumes only, never to the job description.
IMPLIES: Dict[str, Set[str]] = {
    "postgresql": {"sql"},
    "mysql": {"sql"},
    "sqlite": {"sql"},
    "flask": {"python"},
    "django": {"python"},
    "fastapi": {"python"},
    "celery": {"python"},
    "pandas": {"python"},
    "typescript": {"javascript"},
    "node.js": {"javascript"},
    "react": {"javascript"},
    "next.js": {"react", "javascript"},
    "vue": {"javascript"},
    "express": {"node.js", "javascript"},
    "github actions": {"ci/cd"},
    "jenkins": {"ci/cd"},
}

_SEPARATORS = re.compile(r"[-_\s]+")


def _normalize(text: str) -> str:
    return _SEPARATORS.sub(" ", text.lower())


def _alias_pattern(alias: str) -> str:
    # The lookarounds stop "java" matching inside "javascript", "sql" inside
    # "mysql", "go" inside "mongo" and so on, while still allowing "c++"/"c#".
    return rf"(?<![a-z0-9+#.]){re.escape(_normalize(alias))}(?![a-z0-9+#])"


_SKILL_REGEX: Dict[str, "re.Pattern[str]"] = {
    skill: re.compile("|".join(_alias_pattern(a) for a in aliases))
    for skill, aliases in SKILLS.items()
}


def extract_skills(text: str) -> Set[str]:
    """Return the canonical skills from the vocabulary that appear in `text`."""
    normalized = _normalize(text)
    return {skill for skill, rx in _SKILL_REGEX.items() if rx.search(normalized)}


def expand_implied(skills: Iterable[str]) -> Set[str]:
    """Add skills that are strongly implied by the ones already present."""
    expanded = set(skills)
    for skill in list(expanded):
        expanded |= IMPLIES.get(skill, set())
    return expanded


# --------------------------------------------------------------------------- #
# Combining the signals
# --------------------------------------------------------------------------- #
def skill_score(required: Set[str], present: Set[str]) -> Optional[float]:
    """Fraction of required skills present, or None if nothing was required."""
    if not required:
        return None
    return len(required & present) / len(required)


def combine(semantic: float, skills: Optional[float], semantic_weight: float) -> float:
    """
    Blend the two 0..1 signals. If the job description named no recognisable
    skills there is nothing to blend, so the semantic score is used alone.
    """
    if skills is None:
        return semantic
    w = float(np.clip(semantic_weight, 0.0, 1.0))
    return w * semantic + (1.0 - w) * skills
