from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from a4_printer_webserver import create_app

PRINTER_UUID = "8fd0d51f-12c8-5b50-a2f1-4f64641ae77c"


class AppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.app = create_app(
            printer_uuid=PRINTER_UUID,
            password="secret phrase",
            title="Office <Printer>",
            data_dir=self.temporary_directory.name,
            start_service=False,
        )
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def csrf_token(self) -> str:
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def login(self, password: str = "secret phrase"):
        self.client.get("/login")
        return self.client.post(
            "/login",
            data={"password": password, "csrf_token": self.csrf_token()},
        )

    def image_upload(self, name: str = "sample.png") -> dict:
        content = io.BytesIO()
        Image.new("RGB", (8, 8), "white").save(content, format="PNG")
        content.seek(0)
        response = self.client.post(
            "/api/uploads",
            data={"file": (content, name)},
            headers={"X-CSRF-Token": self.csrf_token()},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()["job"]

    def test_unauthenticated_users_are_blocked(self) -> None:
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.get("/api/state").status_code, 401)
        self.assertEqual(self.client.get("/api/jobs/unknown/download").status_code, 401)

    def test_login_and_custom_title(self) -> None:
        self.assertEqual(self.login("wrong").status_code, 200)
        response = self.login()
        self.assertEqual(response.status_code, 302)

        page = self.client.get("/")
        self.assertIn(b"Office &lt;Printer&gt;", page.data)

    def test_upload_queue_and_cancel(self) -> None:
        self.login()
        job = self.image_upload("folder\\photo.png")
        self.assertEqual(job["name"], "photo.png")
        headers = {"X-CSRF-Token": self.csrf_token()}

        response = self.client.post(f"/api/jobs/{job['id']}/print", headers=headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.delete(f"/api/jobs/{job['id']}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["job"]["status"], "canceled")

    def test_printing_job_cannot_be_canceled_and_completed_job_downloads(self) -> None:
        self.login()
        job = self.image_upload()
        store = self.app.extensions["job_store"]
        store.queue_job(job["id"])
        store.claim_next_job()
        headers = {"X-CSRF-Token": self.csrf_token()}

        response = self.client.delete(f"/api/jobs/{job['id']}", headers=headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()["error"], "printing_job_cannot_be_canceled"
        )

        store.finish_job(job["id"])
        response = self.client.get(f"/api/jobs/{job['id']}/download")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        response.close()

    def test_invalid_file_and_missing_csrf_are_rejected(self) -> None:
        self.login()
        response = self.client.post(
            "/api/uploads",
            data={"file": (io.BytesIO(b"not an image"), "bad.png")},
            headers={"X-CSRF-Token": self.csrf_token()},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "invalid_file")

        response = self.client.post("/logout")
        self.assertEqual(response.status_code, 400)

    def test_unsupported_file_type_is_rejected_without_creating_a_job(self) -> None:
        self.login()

        response = self.client.post(
            "/api/uploads",
            data={"file": (io.BytesIO(b"plain text"), "notes.txt")},
            headers={"X-CSRF-Token": self.csrf_token()},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "unsupported_file_type")
        self.assertEqual(self.app.extensions["job_store"].list_jobs(), [])

    def test_logout_revokes_the_server_side_session(self) -> None:
        self.login()
        headers = {"X-CSRF-Token": self.csrf_token()}

        self.assertEqual(self.client.post("/logout", headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/state").status_code, 401)

    def test_test_page_is_queued_and_can_be_canceled(self) -> None:
        self.login()
        headers = {"X-CSRF-Token": self.csrf_token()}

        response = self.client.post("/api/test-page", headers=headers)

        self.assertEqual(response.status_code, 201)
        job = response.get_json()["job"]
        self.assertEqual(job["kind"], "test_page")
        self.assertEqual(job["status"], "queued")
        self.assertTrue(job["can_cancel"])
        self.assertFalse(job["can_download"])
        self.assertFalse(job["can_delete_file"])
        response = self.client.delete(f"/api/jobs/{job['id']}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["job"]["status"], "canceled")

    def test_printing_can_be_paused_and_resumed(self) -> None:
        self.login()
        headers = {"X-CSRF-Token": self.csrf_token()}
        self.assertFalse(self.client.get("/api/state").get_json()["paused"])

        response = self.client.post(
            "/api/pause", json={"paused": True}, headers=headers
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["paused"])
        self.assertTrue(self.client.get("/api/state").get_json()["paused"])
        response = self.client.post(
            "/api/pause", json={"paused": False}, headers=headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["paused"])

        response = self.client.post(
            "/api/pause", json={"paused": "yes"}, headers=headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "invalid_pause_state")

    def test_completed_document_file_can_be_deleted_without_losing_history(self) -> None:
        self.login()
        job = self.image_upload()
        store = self.app.extensions["job_store"]
        store.queue_job(job["id"])
        store.claim_next_job()
        store.finish_job(job["id"])
        headers = {"X-CSRF-Token": self.csrf_token()}

        response = self.client.delete(
            f"/api/jobs/{job['id']}/file", headers=headers
        )

        self.assertEqual(response.status_code, 200)
        result = response.get_json()["job"]
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["file_available"])
        self.assertFalse(result["can_download"])
        self.assertFalse(result["can_delete_file"])
        self.assertIsNotNone(store.get_job(job["id"]))
        self.assertEqual(
            self.client.get(f"/api/jobs/{job['id']}/download").status_code,
            410,
        )
