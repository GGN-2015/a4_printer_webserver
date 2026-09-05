from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from a4_printer_webserver.storage import JobStore


class JobStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.store = JobStore(Path(self.temporary_directory.name) / "jobs.sqlite3")
        self.store.initialize()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def create_job(self, job_id: str = "job-1") -> dict:
        return self.store.create_job(
            job_id=job_id,
            original_name="page.png",
            stored_name=f"{job_id}.png",
            media_type="image/png",
            size=25,
        )

    def test_job_lifecycle(self) -> None:
        self.assertEqual(self.create_job()["status"], "uploaded")
        self.assertEqual(self.store.queue_job("job-1")["status"], "queued")
        self.assertEqual(self.store.claim_next_job()["status"], "printing")
        self.assertIsNone(self.store.cancel_job("job-1"))

        self.store.finish_job("job-1")

        self.assertEqual(self.store.get_job("job-1")["status"], "completed")

    def test_only_queued_jobs_can_be_claimed(self) -> None:
        self.create_job()
        self.assertIsNone(self.store.claim_next_job())

    def test_interrupted_print_is_not_requeued(self) -> None:
        self.create_job()
        self.store.queue_job("job-1")
        self.store.claim_next_job()

        recovered = self.store.recover_interrupted_jobs()

        job = self.store.get_job("job-1")
        self.assertEqual(recovered, 1)
        self.assertEqual(job["status"], "failed")
        self.assertIn("server stopped", job["error"].lower())

    def test_test_page_is_created_in_the_queue_and_can_be_canceled(self) -> None:
        job = self.store.create_test_page_job(job_id="test-page")

        self.assertEqual(job["kind"], "test_page")
        self.assertEqual(job["status"], "queued")
        self.assertEqual(job["size"], 0)
        self.assertEqual(self.store.cancel_job("test-page")["status"], "canceled")
