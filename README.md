# Resume Ranker

Rank a stack of resumes against a job description and see *why* each one scored the way it did.
A FastAPI backend validates and extracts uploaded PDF / DOCX / TXT documents, embeds their text with
SBERT, and checks skill overlap; a single-page React frontend uploads the original files and shows the
results. The source page uses CDN React/Babel for development; `npm run build` creates a production
static build with JSX precompiled and local React assets in `dist/`.
The dashboard guides reviewers through the role description, resume management, and matching weights,
then presents ranked evidence and a side-by-side comparison of up to three candidates. File type, MIME
type, filename, and size are validated in both the browser and backend. Individual unreadable files are
reported while readable files continue through ranking.

## How scoring works

Each resume gets a match score from 0 to 100% that blends two signals. It is a model-generated comparison signal, not a hiring probability or guarantee of job performance. A human reviewer must make the final decision.

1. **Meaning match.** Long texts are split into overlapping ~150-word chunks (the model only reads
   about 256 tokens, so without this the end of a resume would be ignored). For every chunk of the
   job description, the best-matching resume chunk is found, and those best matches are averaged.
   The raw cosine similarity is then stretched onto 0-1 (see `SIM_FLOOR` / `SIM_CEIL` in `scoring.py`).
2. **Skill evidence.** Skills named in the job description are found with a curated vocabulary
   (`SKILLS` in `scoring.py`) and checked against extracted resume text. Explicitly detected and configured implied matches are returned separately; for example, PostgreSQL counts toward SQL. A potentially missing skill means no matching text was detected, not that a candidate lacks it.

The slider in the UI sets the blend (default 60% meaning, 40% skills) and automatically re-runs screening through the backend when results are visible. If the job description names no recognized skills, only the meaning match is used. Results show the two signals separately, matched text evidence, configured implications, and potentially missing vocabulary terms.

## Prerequisites

- Python 3.10 or newer (the sentence-transformers stack and a compatible CPU PyTorch build are required).
- Node.js 22.12 or newer and npm to build the frontend and run browser/accessibility tests.
- Google Chrome for the Playwright browser tests. The runtime frontend itself can be served by any static file server.
- Internet access for initial Python/npm dependency installation and, unless cached, the sentence-transformers model download.

The application uses no API keys or credentials. Do not commit `.env` files or secret configuration. No `.env` file is needed for local use.

## Install and run locally

From the repository root, install the backend and frontend dependencies:

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
```

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
npm ci
```

### Start the backend

In terminal 1, from the repository root:

```powershell
# Optional local settings; defaults work for the documented local frontend.
$env:MODEL_NAME = 'all-MiniLM-L6-v2'
$env:ALLOWED_ORIGINS = 'http://127.0.0.1:8010'
.\.venv\Scripts\python.exe -m uvicorn backend_api:app --host 127.0.0.1 --port 8000 --reload
```

The API listens at `http://127.0.0.1:8000`; interactive API documentation is at `/docs`. The first
startup downloads the configured sentence-transformers model if it is not cached. Wait for the log
message that the model loaded; check `GET /health` for `model_loaded: true` before screening.

### Start the frontend independently

For the source/development page, in terminal 2:

```powershell
py -3 -m http.server 8010
```

Open `http://127.0.0.1:8010/index.html`. The source page loads React and Babel from CDNs and therefore
needs network access for those assets.

To build and serve the production frontend instead:

```powershell
npm run build
py -3 -m http.server 8010 --directory dist
```

Open `http://127.0.0.1:8010/`. The build compiles the JSX and copies React runtime assets locally; it does
not bundle the FastAPI backend. Both frontend modes use the real `POST /rank` API. Use **Use example role**
and choose files in `samples/resumes/` to try it out.

### Formative HCI evaluation materials

Study preparation documents and explicitly synthetic task fixtures are in [`docs/`](docs/usability_test_plan.md), including a neutral task protocol, participant questionnaire, blank observation sheet, and analysis template. The fixtures in [`docs/test_dataset/`](docs/test_dataset/README.md) contain no real candidate data and do not assert expected match scores. Do not report participant outcomes until a study has actually been conducted.

See the [final integration and QA report](docs/qa_report.md) for the executed test counts, real backend/browser workflows, production build status, and remaining limits.

To point the page at a backend elsewhere, use `index.html?api=https://your-backend.example.com`. The selected
files and job description are sent to that configured endpoint, so use a service you trust and HTTPS for
remote deployments.

### Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `MODEL_NAME` | `all-MiniLM-L6-v2` | any sentence-transformers model |
| `ALLOWED_ORIGINS` | `*` | comma-separated CORS origins; set this when you deploy |
| `MAX_RESUMES` | `100` | max resumes per request |
| `MAX_TEXT_CHARS` | `100000` | max characters per document |
| `MAX_UPLOAD_BYTES` | `10485760` | maximum uploaded file size (10 MiB) |
| `MAX_TOTAL_UPLOAD_BYTES` | `52428800` | maximum total multipart request size (50 MiB plus form overhead) |

Windows PowerShell example for setting one optional variable for the current terminal session:

```powershell
$env:MAX_UPLOAD_BYTES = '10485760'
```

`ALLOWED_ORIGINS` defaults to `*` for local development. Restrict it for deployment. CORS is a browser
policy, not authentication or access control. This prototype has no login, user identity, or authorization;
do not expose it as a public service without adding appropriate access controls, HTTPS, request limits at
the hosting proxy, and an operational review of infrastructure logging and retention.

## API

`POST /rank` accepts multipart files (`jd_text`, `semantic_weight`, and repeated `resumes` file fields).
The legacy JSON request with pre-extracted text remains available:

```json
{
  "jd_text": "…",
  "resumes": [{ "filename": "a.pdf", "text": "…" }],
  "semantic_weight": 0.6
}
```

Returns `ranked_resumes` (each with `rank`, `score`, `semantic_score`, `skill_score`, `matched_skills`,
`explicit_matched_skills`, `implied_matched_skills`, and `missing_skills`), plus `jd_skills`, `skipped`, and `effective_semantic_weight`.
Errors use proper status codes: `422` for bad input (with a readable `detail`), `503` while the model
is loading, `500` for unexpected server faults. Unexpected model/library errors are returned as generic
messages; exception text and stack traces are not returned to the client. `GET /health` reports whether the
model is loaded and the configured upload limits.

## Privacy and security behavior

- When screening runs, the browser sends each selected PDF/DOCX/TXT file and the job description to the
  configured FastAPI endpoint. The backend extracts text and computes embeddings and scores in its own
  process; it does not call an external embedding API. Candidate filenames are returned as result metadata.
  The upload request targets the configured API, not the React/Babel asset URLs. Those third-party scripts
  still execute in the page context; self-host them for deployments requiring tighter supply-chain control.
- The application has no database, browser storage, cookie-based session, or cross-request result store.
  Uploaded bytes and extracted text are held in request/process memory while processing. Starlette's
  multipart parser may spool larger file parts to server temporary storage; the parsed form is closed in a
  `finally` block after the request, which closes the upload files. This is normal cleanup, not a guarantee
  of secure erasure from RAM, filesystem snapshots, backups, or storage hardware.
- In the browser, selected `File` objects, the job description, and results live in the active page's
  memory. **Clear screening session** resets them from the page; closing or reloading the tab also discards
  the page state. The button cannot erase server, operating-system, browser-process, or infrastructure data.
- Application logs contain operational counts and error types, not resume text or filenames. Hosting,
  reverse proxies, or external monitoring can have separate access/body logging; configure those systems
  so request bodies and candidate information are not captured.
- The backend validates filenames, extensions, MIME types, file content, per-file and total request sizes,
  document structure, extracted-text length, PDF page count, and DOCX archive expansion. Scanned PDFs are
  not OCR processed. Per-file parser failures are returned as generic, actionable messages. Temporary
  multipart uploads are closed after processing, including unexpected ranking failures.
- The service is stateless per request and does not associate results with a user. That avoids application
  persistence but does not provide user isolation for a publicly reachable instance: anyone with network
  access may submit requests unless deployment-level authentication and access control are added.
- `POST /rank` success and error responses include `Cache-Control: no-store` and `Pragma: no-cache` to ask
  browsers and compliant intermediaries not to cache candidate results.

## Tests

Install development dependencies into the same Python environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Then run the automated checks from the repository root:

```bash
python -m pytest -q
npm ci
npm run build
npm test
```

The Python scoring, ranking, document-validation, and API tests use a small fake embedding model and run
offline. `npm test` runs the frontend workflow tests plus Playwright and axe-core checks at desktop, tablet,
and mobile widths, including keyboard focus order and the populated-results state. Chrome must be installed
for the browser checks. To run the real browser-to-backend end-to-end test, start the backend and a static
server serving `dist/` on port 8010, confirm `/health` reports a loaded model, then run
`npm run test:e2e`. Set `$env:RESUME_SCREENER_FRONTEND` or `$env:RESUME_SCREENER_API` to use different
local URLs. The e2e test uses only repository sample resumes plus an intentionally malformed synthetic PDF.
`node --test tests/frontend/upload_workflow.test.cjs` runs the workflow unit tests alone.

### Troubleshooting

- **`model_loaded` is false or the backend exits at startup:** wait while first-time model weights download. Check the `MODEL_NAME`, Python/PyTorch compatibility, and outbound model-host access. The service cannot rank until initialization succeeds; startup errors are logged server-side.
- **`ModuleNotFoundError` for multipart, PDF, DOCX, or pytest packages:** activate/recreate `.venv` and install `requirements.txt` (or `requirements-dev.txt` for tests) into that same environment. Do not work around missing requirements with a different interpreter's `PYTHONPATH`.
- **Browser shows backend unavailable:** confirm the API is listening at `127.0.0.1:8000`, `/health` returns `model_loaded: true`, and `ALLOWED_ORIGINS` includes the exact frontend origin (scheme, host, and port).
- **Upload is rejected:** use non-empty, text-extractable PDF, DOCX, or UTF-8 TXT files under the configured per-file and batch limits. Scanned/image-only PDFs are not OCR processed.
- **Playwright cannot find Chrome:** install Google Chrome. `npm ci` installs Playwright tooling but this project does not automatically download a browser executable.

The accessibility checks cover WCAG 2.1 A/AA axe rules and horizontal overflow at 1365px, 768px, and 375px.
They do not replace testing with assistive technology or a human review of the full interaction flow.

## Project layout

```
backend_api.py   FastAPI app: validation, errors, model loading
ranker.py        ranking pipeline (works with any model that has encode())
scoring.py       chunking, skill extraction, calibration, score blending
index.html       frontend (React and Babel from CDNs)
style.css        accessibility and motion preferences
document_processing.py server-side file validation and extraction
upload_workflow.js frontend upload validation and state transitions
tests/frontend/  frontend workflow tests (Node built-in test runner)
samples/         example job description and resumes
tests/           pytest suite
```

## Responsible use and limitations

- This is decision support for a human reviewer, not an autonomous hiring or rejection system. A person must
  review the source documents and make all decisions. Match scores are model-generated comparison signals,
  not hiring probabilities or guarantees of job performance.
- The scorer has no explicit protected-characteristic fields or dedicated scoring rules. Common labeled
  personal fields and direct contact tokens are removed before scoring, but this rule-based filter is not
  full de-identification. Sensitive attributes in unlabeled text may still influence semantic similarity.
  Bias and fairness have not been empirically evaluated; this prototype makes no fairness or compliance claim.
- Text extraction can omit layout, tables, columns, images, or context. Scanned/image-only PDFs have no OCR
  support and are reported as unreadable. Extraction errors can affect semantic and skill evidence.
- The skill vocabulary is finite (about 90 skills, tech-focused). Skills outside it are only seen by the meaning match.
- "Flask **or** FastAPI" in a job description is treated as two separate requirements.
- The frontend depends on CDN-hosted React and Babel; offline use needs those assets bundled or cached.
- The default model is English-centric.
