"""Endpoint-level API tests using a small in-process ASGI Request harness."""
import asyncio
import json
from dataclasses import dataclass

import pytest

pytest.importorskip("fastapi")

from fastapi import HTTPException  # noqa: E402
from starlette.requests import Request as StarletteRequest  # noqa: E402
from starlette.requests import Request  # noqa: E402

from backend_api import RankResponse, app, health, rank  # noqa: E402
import backend_api  # noqa: E402
from ranker import rank_resumes  # noqa: E402
from tests.fake_model import FakeModel  # noqa: E402

JD = "Python Flask REST API AWS Docker SQL Git"
BOUNDARY = "resume-screener-test-boundary"


@dataclass
class EndpointResponse:
    status_code: int
    payload: dict

    def json(self):
        return self.payload


def _multipart(fields, files):
    chunks = []
    for name, value in fields.items():
        chunks.extend([
            f"--{BOUNDARY}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n".encode(),
            str(value).encode(),
            b"\r\n",
        ])
    for name, (filename, content, mime) in files:
        chunks.extend([
            f"--{BOUNDARY}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: {mime}\r\n\r\n".encode(),
            content,
            b"\r\n",
        ])
    chunks.append(f"--{BOUNDARY}--\r\n".encode())
    return b"".join(chunks)


def _request(method, path, *, json_body=None, data=None, files=None):
    if json_body is not None:
        body = json.dumps(json_body).encode()
        content_type = "application/json"
    elif files is not None:
        body = _multipart(data or {}, files)
        content_type = f"multipart/form-data; boundary={BOUNDARY}"
    else:
        body = b""
        content_type = ""
    headers = [(b"content-type", content_type.encode()), (b"content-length", str(len(body)).encode())]
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
        "scheme": "http", "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
        "headers": headers, "server": ("test", 80), "client": ("test", 1234), "app": app,
    }
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    request = Request(scope, receive)
    try:
        if method == "GET" and path == "/health":
            payload = health(request)
        else:
            payload = asyncio.run(rank(request))
            # Exercise the same response schema FastAPI applies after the endpoint.
            payload = RankResponse.model_validate(payload).model_dump()
        return EndpointResponse(200, payload)
    except HTTPException as exc:
        return EndpointResponse(exc.status_code, {"detail": exc.detail})


@pytest.fixture()
def client():
    app.state.model = FakeModel()
    yield _request
    app.state.model = None


def test_health(client):
    response = client("GET", "/health")
    assert response.json()["status"] == "ok"
    assert response.json()["model_loaded"] is True
    assert response.json()["max_upload_bytes"] == backend_api.MAX_UPLOAD_BYTES


def test_health_reports_model_not_loaded():
    app.state.model = None
    assert health(Request({"type": "http", "headers": [], "method": "GET", "path": "/health", "query_string": b"", "app": app}))["model_loaded"] is False


def test_rank_happy_path(client):
    r = client("POST", "/rank", json_body={"jd_text": JD, "resumes": [{"filename": "a.txt", "text": JD}]})
    assert r.status_code == 200
    assert r.json()["ranked_resumes"][0]["rank"] == 1


def test_empty_jd_is_a_422_with_a_readable_message(client):
    r = client("POST", "/rank", json_body={"jd_text": " ", "resumes": [{"filename": "a.txt", "text": JD}]})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)


def test_validation_error_for_missing_resumes(client):
    r = client("POST", "/rank", json_body={"jd_text": JD, "resumes": []})
    assert r.status_code == 422


def test_503_while_model_not_loaded(client):
    app.state.model = None
    r = client("POST", "/rank", json_body={"jd_text": JD, "resumes": [{"filename": "a.txt", "text": JD}]})
    assert r.status_code == 503


def test_multipart_upload_processes_resume_on_server(client):
    response = client("POST", "/rank", data={"jd_text": JD, "semantic_weight": "0.6"}, files=[("resumes", ("candidate.txt", JD.encode(), "text/plain"))])
    assert response.status_code == 200
    assert response.json()["ranked_resumes"][0]["filename"] == "candidate.txt"
    assert response.json()["skipped"] == []


def test_multipart_weight_and_explanation_fields_match_ranker_response(client):
    text = "Built Python FastAPI services with PostgreSQL."
    response = client("POST", "/rank", data={"jd_text": JD, "semantic_weight": "1.0"}, files=[("resumes", ("candidate.txt", text.encode(), "text/plain"))])
    assert response.status_code == 200
    actual = response.json()["ranked_resumes"][0]
    expected = rank_resumes(FakeModel(), JD, [("candidate.txt", text)], semantic_weight=1.0)["ranked_resumes"][0]
    for field in ("score", "semantic_score", "skill_score", "matched_skills", "explicit_matched_skills", "implied_matched_skills", "missing_skills"):
        assert actual[field] == expected[field]


def test_multipart_keeps_valid_result_when_one_file_is_malformed(client):
    response = client("POST", "/rank", data={"jd_text": JD}, files=[
        ("resumes", ("candidate.txt", JD.encode(), "text/plain")),
        ("resumes", ("broken.pdf", b"not a PDF", "application/pdf")),
    ])
    assert response.status_code == 200
    body = response.json()
    assert [item["filename"] for item in body["ranked_resumes"]] == ["candidate.txt"]
    assert body["skipped"][0]["filename"] == "broken.pdf"


def test_multipart_reports_empty_and_unsupported_files_as_skipped(client):
    response = client("POST", "/rank", data={"jd_text": JD}, files=[
        ("resumes", ("empty.txt", b"", "text/plain")),
        ("resumes", ("unsupported.exe", b"binary", "application/octet-stream")),
    ])
    assert response.status_code == 200
    body = response.json()
    assert body["ranked_resumes"] == []
    assert len(body["skipped"]) == 2
    assert "empty" in body["skipped"][0]["reason"].lower()
    assert "unsupported" in body["skipped"][1]["reason"].lower()


def test_multipart_enforces_configured_file_size_limit(client, monkeypatch):
    monkeypatch.setattr(backend_api, "MAX_UPLOAD_BYTES", 32)
    response = client("POST", "/rank", data={"jd_text": JD}, files=[("resumes", ("large.txt", b"x" * 33, "text/plain"))])
    assert response.status_code == 200
    assert "upload limit" in response.json()["skipped"][0]["reason"].lower()


def test_resume_text_and_filename_are_not_logged_or_returned(client, caplog):
    secret = "PRIVATE-RESUME-SENTINEL-7a91"
    filename = "candidate-private-name.txt"
    content = f"Python backend experience {secret}."
    caplog.set_level("INFO", logger="resume-ranker")
    response = client("POST", "/rank", data={"jd_text": JD}, files=[("resumes", (filename, content.encode(), "text/plain"))])
    assert response.status_code == 200
    assert secret not in caplog.text
    assert filename not in caplog.text
    assert secret not in json.dumps(response.json())
    assert content not in json.dumps(response.json())


def test_legacy_validation_errors_do_not_echo_rejected_resume_contents(client):
    secret = "PRIVATE-VALIDATION-SENTINEL-31df"
    too_long = "x" * backend_api.MAX_TEXT_CHARS + secret
    response = client("POST", "/rank", json_body={
        "jd_text": JD,
        "resumes": [{"filename": "candidate.txt", "text": too_long}],
    })
    assert response.status_code == 422
    assert secret not in json.dumps(response.json())


@pytest.mark.parametrize("protocol", ["multipart", "json"])
def test_unexpected_ranker_errors_are_generic_and_not_logged(client, monkeypatch, caplog, protocol):
    secret = "PRIVATE-RESUME-ERROR-SENTINEL-16c3"

    def fail(*args, **kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(backend_api, "rank_resumes", fail)
    caplog.set_level("ERROR", logger="resume-ranker")
    if protocol == "multipart":
        response = client("POST", "/rank", data={"jd_text": JD}, files=[("resumes", ("candidate.txt", JD.encode(), "text/plain"))])
    else:
        response = client("POST", "/rank", json_body={"jd_text": JD, "resumes": [{"filename": "candidate.txt", "text": JD}]})
    assert response.status_code == 500
    assert response.json()["detail"] == "Ranking could not be completed. Check the service configuration and try again."
    assert secret not in json.dumps(response.json())
    assert secret not in caplog.text
    assert "Traceback" not in caplog.text


def test_unexpected_model_value_error_does_not_echo_exception_text(client, monkeypatch):
    secret = "PRIVATE-RESUME-VALUE-ERROR-SENTINEL-5c22"
    monkeypatch.setattr(backend_api, "rank_resumes", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError(secret)))
    response = client("POST", "/rank", data={"jd_text": JD}, files=[("resumes", ("candidate.txt", JD.encode(), "text/plain"))])
    assert response.status_code == 422
    assert secret not in json.dumps(response.json())
    assert "Check the job description and resume text" in response.json()["detail"]


def test_multipart_upload_temp_file_is_closed_after_processing(client, monkeypatch):
    original_form = StarletteRequest.form
    captured_forms = []

    async def capture_form(self, *args, **kwargs):
        form = await original_form(self, *args, **kwargs)
        captured_forms.append(form)
        return form

    monkeypatch.setattr(StarletteRequest, "form", capture_form)
    large_text = b"x" * (1024 * 1024 + 32)
    response = client("POST", "/rank", data={"jd_text": JD}, files=[("resumes", ("large.txt", large_text, "text/plain"))])
    assert response.status_code == 200
    assert response.json()["ranked_resumes"] == []
    assert len(captured_forms) == 1
    uploads = [value for _, value in captured_forms[0].multi_items() if hasattr(value, "file")]
    assert len(uploads) == 1
    assert uploads[0].file.closed


def test_rank_responses_are_marked_no_store_including_rejected_oversize_requests():
    async def downstream(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}", "more_body": False})

    async def run_case(headers):
        messages = []
        scope = {
            "type": "http", "method": "POST", "path": "/rank", "headers": headers,
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        middleware = backend_api.UploadRequestSizeLimitMiddleware(downstream, max_body_bytes=64)
        await middleware(scope, receive, send)
        return messages

    ordinary = asyncio.run(run_case([(b"content-type", b"application/json")]))
    rejected = asyncio.run(run_case([(b"content-type", b"multipart/form-data; boundary=x"), (b"content-length", b"128")]))
    for messages in (ordinary, rejected):
        start = next(message for message in messages if message["type"] == "http.response.start")
        response_headers = dict(start["headers"])
        assert response_headers[b"cache-control"] == b"no-store"
        assert response_headers[b"pragma"] == b"no-cache"
    assert next(message for message in rejected if message["type"] == "http.response.start")["status"] == 413


def test_legacy_json_rejects_path_traversal_filename(client):
    response = client("POST", "/rank", json_body={"jd_text": JD, "resumes": [{"filename": "../candidate.txt", "text": JD}]})
    assert response.status_code == 422
    assert "unsafe" in response.json()["detail"].lower()
