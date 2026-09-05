"""Flask application factory and HTTP/WebSocket endpoints."""

from __future__ import annotations

import functools
import hmac
import os
import queue
import re
import secrets
import threading
import time
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable

import pypdfium2 as pdfium
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_sock import Sock
from PIL import Image, UnidentifiedImageError

from .service import PrinterService
from .storage import JobStore

ALLOWED_IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}


def create_app(
    *,
    printer_uuid: str,
    password: str,
    title: str = "Printer Website",
    data_dir: str | Path = "printer_data",
    max_upload_mb: int = 100,
    auto_delete_days: int | None = None,
    start_service: bool = True,
    printer_manager_factory: Callable[..., Any] | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secrets.token_bytes(32),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=max_upload_mb * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        TITLE=title,
        PRINTER_UUID=printer_uuid,
        LOGIN_PASSWORD=password,
    )

    root = Path(data_dir).expanduser().resolve()
    upload_dir = root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    store = JobStore(root / "jobs.sqlite3")
    store.initialize()

    service_options: dict[str, Any] = {
        "printer_uuid": printer_uuid,
        "store": store,
        "upload_dir": upload_dir,
        "auto_delete_days": auto_delete_days,
    }
    if printer_manager_factory is not None:
        service_options["printer_manager_factory"] = printer_manager_factory
    service = PrinterService(**service_options)

    app.extensions["job_store"] = store
    app.extensions["printer_service"] = service
    app.extensions["upload_dir"] = upload_dir

    sock = Sock(app)
    active_sessions: dict[str, float] = {}
    active_sessions_lock = threading.Lock()

    def session_is_authenticated() -> bool:
        auth_token = session.get("auth_token")
        if not session.get("authenticated") or not auth_token:
            return False
        with active_sessions_lock:
            expires_at = active_sessions.get(auth_token, 0)
            if expires_at <= time.time():
                active_sessions.pop(auth_token, None)
                return False
        return True

    @app.before_request
    def ensure_csrf_token() -> None:
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)

    @app.after_request
    def secure_response(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        return response

    def authenticated(view: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if not session_is_authenticated():
                return jsonify(error="authentication_required"), 401
            return view(*args, **kwargs)

        return wrapped

    def csrf_protected(view: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            supplied = request.headers.get("X-CSRF-Token", "")
            expected = session.get("csrf_token", "")
            if not supplied or not hmac.compare_digest(supplied, expected):
                return jsonify(error="invalid_csrf_token"), 400
            return view(*args, **kwargs)

        return wrapped

    @app.get("/")
    def index() -> Response | str:
        if not session_is_authenticated():
            return redirect(url_for("login"))
        return render_template(
            "index.html",
            title=app.config["TITLE"],
            csrf_token=session["csrf_token"],
        )

    @app.route("/login", methods=["GET", "POST"])
    def login() -> Response | str:
        error = None
        if request.method == "POST":
            supplied_csrf = request.form.get("csrf_token", "")
            supplied_password = request.form.get("password", "")
            valid_csrf = hmac.compare_digest(
                supplied_csrf, session.get("csrf_token", "")
            )
            valid_password = hmac.compare_digest(
                supplied_password, app.config["LOGIN_PASSWORD"]
            )
            if valid_csrf and valid_password:
                session.clear()
                auth_token = secrets.token_urlsafe(32)
                session["authenticated"] = True
                session["auth_token"] = auth_token
                session["csrf_token"] = secrets.token_urlsafe(32)
                session.permanent = True
                with active_sessions_lock:
                    active_sessions[auth_token] = time.time() + (
                        app.permanent_session_lifetime.total_seconds()
                    )
                return redirect(url_for("index"))
            error = "invalid_password" if valid_csrf else "invalid_request"
        elif session_is_authenticated():
            return redirect(url_for("index"))
        return render_template(
            "login.html",
            title=app.config["TITLE"],
            csrf_token=session["csrf_token"],
            error=error,
        )

    @app.post("/logout")
    @authenticated
    @csrf_protected
    def logout() -> Response:
        auth_token = session.get("auth_token")
        if auth_token:
            with active_sessions_lock:
                active_sessions.pop(auth_token, None)
        session.clear()
        return jsonify(ok=True)

    @app.get("/api/state")
    @authenticated
    def get_state() -> Response:
        return jsonify(service.snapshot())

    @app.post("/api/pause")
    @authenticated
    @csrf_protected
    def set_printing_paused() -> tuple[Response, int] | Response:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or type(payload.get("paused")) is not bool:
            return jsonify(error="invalid_pause_state"), 400
        return jsonify(paused=service.set_paused(payload["paused"]))

    @app.post("/api/uploads")
    @authenticated
    @csrf_protected
    def upload() -> tuple[Response, int] | Response:
        uploaded = request.files.get("file")
        if uploaded is None or not uploaded.filename:
            return jsonify(error="missing_file"), 400

        original_name = _display_filename(uploaded.filename)
        extension = Path(original_name).suffix.lower()
        if extension != ".pdf" and extension not in ALLOWED_IMAGE_EXTENSIONS:
            return jsonify(error="unsupported_file_type"), 400

        job_id = str(uuid.uuid4())
        stored_name = f"{job_id}{extension}"
        final_path = upload_dir / stored_name
        temporary_path = upload_dir / f".{job_id}.part"
        try:
            uploaded.save(temporary_path)
            if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
                raise ValueError("empty_file")
            _validate_document(temporary_path, extension)
            os.replace(temporary_path, final_path)
        except ValueError as error:
            temporary_path.unlink(missing_ok=True)
            return jsonify(error=str(error)), 400
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        try:
            job = store.create_job(
                job_id=job_id,
                original_name=original_name,
                stored_name=stored_name,
                media_type=uploaded.mimetype or "application/octet-stream",
                size=final_path.stat().st_size,
            )
        except Exception:
            final_path.unlink(missing_ok=True)
            raise
        service.publish_snapshot()
        return jsonify(job=service.public_job(job)), 201

    @app.post("/api/jobs/<job_id>/print")
    @authenticated
    @csrf_protected
    def queue_for_printing(job_id: str) -> tuple[Response, int] | Response:
        job = store.get_job(job_id)
        if job is None:
            return jsonify(error="job_not_found"), 404
        if job["status"] != "uploaded":
            return jsonify(error="job_cannot_be_queued"), 409
        if not (upload_dir / job["stored_name"]).is_file():
            return jsonify(error="file_missing"), 410
        queued_job = store.queue_job(job_id)
        if queued_job is None:
            return jsonify(error="job_cannot_be_queued"), 409
        service.publish_snapshot()
        service.wake_worker()
        return jsonify(job=service.public_job(queued_job))

    @app.post("/api/test-page")
    @authenticated
    @csrf_protected
    def queue_test_page() -> tuple[Response, int]:
        job = store.create_test_page_job(job_id=str(uuid.uuid4()))
        service.publish_snapshot()
        service.wake_worker()
        return jsonify(job=service.public_job(job)), 201

    @app.delete("/api/jobs/<job_id>")
    @authenticated
    @csrf_protected
    def cancel_job(job_id: str) -> tuple[Response, int] | Response:
        job = store.get_job(job_id)
        if job is None:
            return jsonify(error="job_not_found"), 404
        if job["status"] == "printing":
            return jsonify(error="printing_job_cannot_be_canceled"), 409
        canceled_job = store.cancel_job(job_id)
        if canceled_job is None:
            return jsonify(error="job_cannot_be_canceled"), 409
        (upload_dir / job["stored_name"]).unlink(missing_ok=True)
        service.publish_snapshot()
        return jsonify(job=service.public_job(canceled_job))

    @app.delete("/api/jobs/<job_id>/file")
    @authenticated
    @csrf_protected
    def delete_job_file(job_id: str) -> tuple[Response, int] | Response:
        job = store.get_job(job_id)
        if job is None:
            return jsonify(error="job_not_found"), 404
        visible_job = next(
            (
                candidate
                for candidate in service.snapshot()["jobs"]
                if candidate["id"] == job_id
            ),
            None,
        )
        if visible_job is None or not visible_job["can_delete_file"]:
            return jsonify(error="job_file_cannot_be_deleted"), 409
        (upload_dir / job["stored_name"]).unlink(missing_ok=True)
        service.publish_snapshot()
        return jsonify(job=service.public_job(job))

    @app.get("/api/jobs/<job_id>/download")
    @authenticated
    def download_job(job_id: str) -> Response | tuple[Response, int]:
        job = store.get_job(job_id)
        if job is None:
            return jsonify(error="job_not_found"), 404
        if job["kind"] != "document" or job["status"] != "completed":
            return jsonify(error="job_not_downloadable"), 409
        document_path = upload_dir / job["stored_name"]
        if not document_path.is_file():
            return jsonify(error="file_missing"), 410
        return send_file(
            document_path,
            as_attachment=True,
            download_name=job["original_name"],
        )

    @app.errorhandler(413)
    def upload_too_large(_: Exception) -> tuple[Response, int]:
        return jsonify(error="file_too_large"), 413

    @sock.route("/ws")
    def websocket(ws: Any) -> None:
        if not session_is_authenticated():
            ws.send('{"type":"authentication_required"}')
            ws.close()
            return
        subscriber = service.broker.subscribe()
        try:
            ws.send(service.broker_message())
            while True:
                try:
                    message = subscriber.get(timeout=20)
                except queue.Empty:
                    message = service.broker_message()
                if not session_is_authenticated():
                    ws.send('{"type":"authentication_required"}')
                    ws.close()
                    return
                ws.send(message)
        except Exception:
            return
        finally:
            service.broker.unsubscribe(subscriber)

    if start_service:
        service.start()
    return app


def _display_filename(filename: str) -> str:
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    basename = re.sub(r"[\x00-\x1f\x7f]", "", basename)
    return basename[:255] or "document"


def _validate_document(path: Path, extension: str) -> None:
    try:
        if extension == ".pdf":
            document = pdfium.PdfDocument(str(path))
            try:
                if len(document) < 1:
                    raise ValueError("invalid_file")
            finally:
                document.close()
        else:
            with Image.open(path) as image:
                image.verify()
    except (ValueError, UnidentifiedImageError, OSError, RuntimeError):
        raise ValueError("invalid_file") from None
