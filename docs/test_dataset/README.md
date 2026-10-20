# Synthetic evaluation fixtures

Every resume and job description in this directory is fictional and was written solely for interface evaluation. The files contain no real person's contact details, employment history, or other personal data. Do not treat these examples as representative of real applicants.

## Files

| File | Purpose |
|---|---|
| `job_descriptions/backend_engineer.txt` | Example role description for the backend resume set. |
| `resumes/synthetic_profile_a_backend.txt` | Explicitly describes several technologies and activities in the backend role. |
| `resumes/synthetic_profile_b_backend.txt` | Describes some related experience but leaves several role terms unspecified. |
| `resumes/synthetic_profile_c_backend.txt` | Uses general project language without naming the role's technical vocabulary. It tests how the interface presents unobserved terms; it must not be interpreted as proof the fictional profile lacks those skills. |
| `job_descriptions/data_analyst.txt` and `resumes/synthetic_profile_d_analyst.txt` | A separate, small role/resume example. |
| `resumes/extraction_failures/empty.txt` | Zero-byte fixture for empty-file handling. |
| `resumes/extraction_failures/malformed.pdf` | Plain text with a PDF extension; intentionally not a valid PDF. |
| `resumes/extraction_failures/malformed.docx` | Plain text with a DOCX extension; intentionally not a valid DOCX package. |

The examples are scenario fixtures, not labeled expected outcomes. The application/model version and preprocessing can affect scores; no score, ranking, or ideal decision is asserted here. Scanned PDFs are not included as supported examples because OCR is not implemented.

## Use

Start the application using the repository README. Enter a sample job description in the role-description field and select the matching synthetic resume text files. To try validation and recovery, select a single fixture from `resumes/extraction_failures/`; expect an actionable processing error, not a fabricated result. The fixture's extension may be rejected or processed depending on validation order, which itself can be observed during formative evaluation.

For the evaluation protocol, recruit consenting participants and use pseudonyms. Do not place real candidate documents in this directory or collect them as study materials.
