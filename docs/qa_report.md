# Final integration and QA report

**Scope:** Repository-level integration checks performed with the declared React/FastAPI architecture and synthetic sample documents. These are software QA results, not participant findings, hiring validation, or evidence of algorithmic fairness.

## Commands executed and results

| Command / check | Result |
|---|---|
| `npm ci` | Passed; installed the locked frontend dependencies. |
| `\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt` | Passed; installed the declared PDF, DOCX, multipart, pytest, and backend dependencies into the project virtual environment. |
| `\.venv\Scripts\python.exe -m pytest -q` | **54 passed, 0 failed** (0.81 s). Executed outside the restricted sandbox because the Windows asyncio Proactor loop used by the API tests requires local socket-pair support. |
| `npm run build` | Passed; generated `dist/` with precompiled React JSX and local React runtime assets. No external React/Babel CDN scripts remain in the built page. |
| `npm test` | **13 passed, 0 failed** (8.5 s): 8 frontend workflow unit tests and 5 browser/accessibility tests. |
| `$env:RESUME_SCREENER_FRONTEND='http://127.0.0.1:8011'; npm run test:e2e` | Passed against the production build served over HTTP and the live FastAPI service/model. The browser workflow completed all assertions. |
| `GET http://127.0.0.1:8000/health` | Passed: `status=ok`, `model_loaded=true`, 10 MiB per-file limit, maximum 100 resumes. |
| Live `/rank` with repository samples and malformed synthetic PDF | Passed: two readable resumes ranked, one malformed file reported as skipped, and the valid results remained available. |
| Live `/rank` with temporary synthetic PDF, DOCX, and TXT files | Passed: all three formats extracted and ranked; temporary files were deleted after the request. |
| Startup with offline mode and `MODEL_NAME=codex-qa/nonexistent-model` | Failed closed as expected; Uvicorn exited with status 3 during app startup rather than serving an uninitialized model. The exception remained in the server console. |

The initial backend test invocation stalled because the sandbox prevented asyncio from creating a Windows local socket pair; the elevated rerun above completed successfully. The first live multipart smoke request also exposed that the existing project virtual environment lacked `python-multipart`, `pypdf`, and `python-docx`. Installing `requirements-dev.txt` in that environment fixed the runtime setup; the PDF/DOCX/TXT workflow then passed. No source-level scoring or API changes were needed.

## Verified workflows

- The real sentence-transformer model loaded from the local cache, and `/health` reported it ready.
- The built frontend transmitted the supplied job description and selected resume files to the existing `/rank` endpoint.
- Backend-returned match, semantic, and skill scores were shown at the same two-decimal precision in the UI; no client-generated scores were used.
- Changing the weighting control triggered another real backend request and returned the selected effective semantic weight.
- Matched, implied, and potentially missing skill explanations were reachable by keyboard. The UI labels absent text evidence as potentially missing rather than asserting the candidate lacks the skill.
- Two candidates could be selected and compared side by side.
- Partial success was preserved when a malformed PDF was uploaded alongside valid text resumes.
- An all-malformed upload showed the no-ranked-resumes empty state. The browser also showed the backend-unavailable state and disabled screening when pointed at an unavailable local port.
- The browser e2e selected candidates and recalculated rankings with the slider via the actual backend; frontend unit tests additionally verified sorting by skill score without mutating score/rank values.
- Clearing the screening session removed the visible job description, selected files, results, and comparison state. The tested page used no `localStorage` or `sessionStorage`; backend multipart cleanup is covered by the backend suite.
- Axe WCAG 2.1 A/AA checks and horizontal-overflow assertions passed at 1365px, 768px, and 375px. The browser test verified initial keyboard order and visible focus, and checked the populated results state.
- The test suite covers input/file validation, malformed and empty documents, request limits, temporary upload closure, generic API failure responses, privacy log behavior, score calculations, and weight-dependent ranking.

The real e2e scenario does not wait two minutes to exercise the timeout; the request has a configured 120-second abort, while error recovery was verified with the unavailable-backend state and existing frontend tests.

## Production build

`npm run build` creates the ignored `dist/` directory. Serve it and the backend independently:

```powershell
# Terminal 1: backend (after installing requirements.txt)
$env:ALLOWED_ORIGINS = 'http://127.0.0.1:8010'
.\.venv\Scripts\python.exe -m uvicorn backend_api:app --host 127.0.0.1 --port 8000

# Terminal 2: frontend, after npm ci and npm run build
py -3 -m http.server 8010 --directory dist
```

With both running and the model ready, execute `npm run test:e2e` in terminal 3. Override the local URLs with `RESUME_SCREENER_FRONTEND` and `RESUME_SCREENER_API` when needed. The build does not include the FastAPI service or model weights.

## Known issues and remaining limits

- The project is a local research prototype with no authentication, authorization, tenant isolation, or persistent user sessions. Do not expose it as a public recruitment service.
- Scanned/image-only PDFs are not OCR processed. Extraction quality can affect both signals.
- Skill matching uses a finite vocabulary; absent detected terms are not proof of missing candidate experience.
- Sentence-transformer similarity and score calibration are not validated hiring probabilities or performance predictions. Fairness and validity have not been empirically established.
- Sensitive text not removed by the limited labeled-field/contact filter could still influence semantic similarity. Keep a human reviewer responsible for every decision and do not use protected characteristics.
- The source/development page still loads React and Babel from CDNs. The generated production build serves React locally; the backend and model still require their own setup.
- The e2e check uses Google Chrome and requires the model to be available/cached or downloadable. It uses only repository samples and synthetic failure fixtures.
- No TypeScript compiler or separate type-check command is configured; the frontend is plain JavaScript/JSX.

## Demonstration steps

1. Install Python and npm requirements using the Windows commands in the root README.
2. Start FastAPI and wait until `GET /health` reports `model_loaded: true`.
3. Run `npm run build` and serve `dist/` at `http://127.0.0.1:8010`.
4. Open the page, choose **Use example role**, and upload files under `samples/resumes/`.
5. Run screening; inspect the score components and candidate explanations, select two candidates to compare, then adjust the weighting and observe backend recalculation.
6. Optionally test partial-failure handling with `docs/test_dataset/resumes/extraction_failures/malformed.pdf` alongside a valid sample. Use **Clear screening session** when finished.
7. Run the automated suite with `\.venv\Scripts\python.exe -m pytest -q`, `npm test`, and (with the services running) `npm run test:e2e`.

No participants were recruited and no usability outcomes are reported here.
