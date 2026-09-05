from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from a4_printer_webserver.service import PrinterService
from a4_printer_webserver.storage import JobStore


class FakePrinter:
    def __init__(self, *, busy: bool = False) -> None:
        self.printed: list[str] = []
        self.test_pages = 0
        self.busy = busy

    def get_name(self) -> str:
        return "Test Printer"

    def get_busy(self) -> bool:
        return self.busy

    def print(self, path: str, _settings) -> None:
        self.printed.append(path)

    def print_test_page(self, _settings) -> None:
        self.test_pages += 1


class FakeManager:
    def __init__(self, printer: FakePrinter | None) -> None:
        self.printer = printer

    def get_printer_by_uuid(self, _uuid: str) -> FakePrinter | None:
        return self.printer


class PrinterServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.upload_dir = self.root / "uploads"
        self.upload_dir.mkdir()
        self.store = JobStore(self.root / "jobs.sqlite3")
        self.store.initialize()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_worker_prints_queued_job(self) -> None:
        printer = FakePrinter()
        service = PrinterService(
            printer_uuid=PRINTER_UUID,
            store=self.store,
            upload_dir=self.upload_dir,
            printer_manager_factory=lambda: FakeManager(printer),
            poll_interval=0.01,
        )
        document = self.upload_dir / "job.png"
        document.write_bytes(b"test")
        self.store.create_job(
            job_id="job",
            original_name="job.png",
            stored_name="job.png",
            media_type="image/png",
            size=4,
        )
        self.store.queue_job("job")

        service.start()
        try:
            deadline = time.monotonic() + 2
            while self.store.get_job("job")["status"] != "completed":
                if time.monotonic() >= deadline:
                    self.fail("print worker did not complete the queued job")
                time.sleep(0.01)
        finally:
            service.stop()

        self.assertEqual(printer.printed, [str(document)])

    def test_missing_printer_is_disconnected(self) -> None:
        service = PrinterService(
            printer_uuid=PRINTER_UUID,
            store=self.store,
            upload_dir=self.upload_dir,
            printer_manager_factory=lambda: FakeManager(None),
        )

        state = service.refresh_printer_state()

        self.assertEqual(state["status"], "disconnected")

    def test_worker_prints_queued_test_page(self) -> None:
        printer = FakePrinter()
        service = PrinterService(
            printer_uuid=PRINTER_UUID,
            store=self.store,
            upload_dir=self.upload_dir,
            printer_manager_factory=lambda: FakeManager(printer),
            poll_interval=0.01,
        )
        self.store.create_test_page_job(job_id="test-page")

        service.start()
        try:
            deadline = time.monotonic() + 2
            while self.store.get_job("test-page")["status"] != "completed":
                if time.monotonic() >= deadline:
                    self.fail("print worker did not complete the test page")
                time.sleep(0.01)
        finally:
            service.stop()

        self.assertEqual(printer.test_pages, 1)
        self.assertEqual(printer.printed, [])

    def test_pause_holds_queued_job_until_printing_resumes(self) -> None:
        printer = FakePrinter()
        service = PrinterService(
            printer_uuid=PRINTER_UUID,
            store=self.store,
            upload_dir=self.upload_dir,
            printer_manager_factory=lambda: FakeManager(printer),
            poll_interval=0.01,
        )
        document = self.upload_dir / "paused.png"
        document.write_bytes(b"test")
        self.store.create_job(
            job_id="paused",
            original_name="paused.png",
            stored_name="paused.png",
            media_type="image/png",
            size=4,
        )
        self.store.queue_job("paused")
        service.set_paused(True)

        service.start()
        try:
            time.sleep(0.05)
            self.assertEqual(self.store.get_job("paused")["status"], "queued")
            self.assertEqual(printer.printed, [])
            self.assertTrue(service.snapshot()["paused"])

            service.set_paused(False)
            deadline = time.monotonic() + 2
            while self.store.get_job("paused")["status"] != "completed":
                if time.monotonic() >= deadline:
                    self.fail("print worker did not resume the queued job")
                time.sleep(0.01)
        finally:
            service.stop()

        self.assertEqual(printer.printed, [str(document)])

    def test_busy_printer_marks_latest_completed_job_as_printing(self) -> None:
        printer = FakePrinter(busy=True)
        service = PrinterService(
            printer_uuid=PRINTER_UUID,
            store=self.store,
            upload_dir=self.upload_dir,
            printer_manager_factory=lambda: FakeManager(printer),
        )
        self.store.create_test_page_job(job_id="completed")
        self.store.claim_next_job()
        self.store.finish_job("completed")

        service.refresh_printer_state()
        snapshot = service.snapshot()

        self.assertEqual(snapshot["jobs"][0]["status"], "completed")
        self.assertEqual(snapshot["jobs"][0]["display_status"], "printing")
        self.assertFalse(snapshot["jobs"][0]["can_delete_file"])
        printer.busy = False
        service.refresh_printer_state()
        self.assertEqual(service.snapshot()["jobs"][0]["display_status"], "completed")

    def test_auto_delete_removes_expired_file_but_keeps_history(self) -> None:
        document = self.upload_dir / "expired.png"
        document.write_bytes(b"test")
        self.store.create_job(
            job_id="expired",
            original_name="expired.png",
            stored_name="expired.png",
            media_type="image/png",
            size=4,
        )
        self.store.queue_job("expired")
        self.store.claim_next_job()
        self.store.finish_job("expired")
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE jobs SET completed_at = ? WHERE id = ?",
                ("2000-01-01T00:00:00+00:00", "expired"),
            )
        service = PrinterService(
            printer_uuid=PRINTER_UUID,
            store=self.store,
            upload_dir=self.upload_dir,
            printer_manager_factory=lambda: FakeManager(None),
            auto_delete_days=30,
        )

        deleted_count = service.delete_expired_files()

        self.assertEqual(deleted_count, 1)
        self.assertFalse(document.exists())
        self.assertEqual(self.store.get_job("expired")["status"], "completed")
        job = service.snapshot()["jobs"][0]
        self.assertFalse(job["file_available"])
        self.assertFalse(job["can_download"])
        self.assertFalse(job["can_delete_file"])

    def test_auto_delete_does_not_remove_job_displayed_as_printing(self) -> None:
        document = self.upload_dir / "still-printing.png"
        document.write_bytes(b"test")
        self.store.create_job(
            job_id="still-printing",
            original_name="still-printing.png",
            stored_name="still-printing.png",
            media_type="image/png",
            size=4,
        )
        self.store.queue_job("still-printing")
        self.store.claim_next_job()
        self.store.finish_job("still-printing")
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE jobs SET completed_at = ? WHERE id = ?",
                ("2000-01-01T00:00:00+00:00", "still-printing"),
            )
        printer = FakePrinter(busy=True)
        service = PrinterService(
            printer_uuid=PRINTER_UUID,
            store=self.store,
            upload_dir=self.upload_dir,
            printer_manager_factory=lambda: FakeManager(printer),
            auto_delete_days=30,
        )

        deleted_count = service.delete_expired_files()

        self.assertEqual(deleted_count, 0)
        self.assertTrue(document.exists())
        job = service.snapshot()["jobs"][0]
        self.assertEqual(job["display_status"], "printing")
        self.assertFalse(job["can_delete_file"])


PRINTER_UUID = "8fd0d51f-12c8-5b50-a2f1-4f64641ae77c"
