"""Printer monitoring, queue processing, and WebSocket broadcasts."""

from __future__ import annotations

import json
import logging
import queue
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from a4_printer_interface import DefaultSettings, PrinterManager

from .storage import JobStore

LOGGER = logging.getLogger(__name__)


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: set[queue.Queue[str]] = set()
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[str]:
        subscriber: queue.Queue[str] = queue.Queue(maxsize=4)
        with self._lock:
            self._subscribers.add(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[str]) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)

    def publish(self, payload: dict[str, Any]) -> None:
        message = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(message)
            except queue.Full:
                try:
                    subscriber.get_nowait()
                except queue.Empty:
                    pass
                try:
                    subscriber.put_nowait(message)
                except queue.Full:
                    pass


class PrinterService:
    def __init__(
        self,
        *,
        printer_uuid: str,
        store: JobStore,
        upload_dir: Path,
        printer_manager_factory: Callable[[], PrinterManager] = PrinterManager,
        poll_interval: float = 2.0,
        auto_delete_days: int | None = None,
        cleanup_interval: float = 3600.0,
    ) -> None:
        if auto_delete_days is not None and auto_delete_days <= 0:
            raise ValueError("auto_delete_days must be a positive integer")
        self.printer_uuid = printer_uuid
        self.store = store
        self.upload_dir = upload_dir
        self.printer_manager_factory = printer_manager_factory
        self.poll_interval = poll_interval
        self.auto_delete_days = auto_delete_days
        self.cleanup_interval = cleanup_interval
        self.broker = EventBroker()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._state_lock = threading.Lock()
        self._dispatch_lock = threading.Lock()
        self._paused = False
        self._printer_state: dict[str, Any] = {
            "status": "disconnected",
            "name": None,
        }
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        if self._threads:
            return
        self.store.recover_interrupted_jobs()
        self._threads = [
            threading.Thread(
                target=self._monitor_loop,
                name="printer-status-monitor",
                daemon=True,
            ),
            threading.Thread(
                target=self._worker_loop,
                name="printer-queue-worker",
                daemon=True,
            ),
        ]
        if self.auto_delete_days is not None:
            self._threads.append(
                threading.Thread(
                    target=self._cleanup_loop,
                    name="print-history-cleanup",
                    daemon=True,
                )
            )
        for thread in self._threads:
            thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        for thread in self._threads:
            thread.join(timeout=5)
        self._threads.clear()

    def wake_worker(self) -> None:
        self._wake_event.set()

    def set_paused(self, paused: bool) -> bool:
        with self._dispatch_lock:
            changed = paused != self._paused
            self._paused = paused
        if not paused:
            self.wake_worker()
        if changed:
            self.publish_snapshot()
        return paused

    def is_paused(self) -> bool:
        with self._dispatch_lock:
            return self._paused

    def snapshot(self) -> dict[str, Any]:
        paused = self.is_paused()
        with self._state_lock:
            printer = dict(self._printer_state)
        jobs = [self.public_job(job) for job in self.store.list_jobs()]
        if printer["status"] == "busy":
            latest_completed = next(
                (job for job in jobs if job["status"] == "completed"), None
            )
            if latest_completed is not None:
                latest_completed["display_status"] = "printing"
                latest_completed["can_delete_file"] = False
        if printer["status"] != "disconnected" and any(
            job["status"] == "printing" for job in jobs
        ):
            printer["status"] = "busy"
        return {
            "type": "snapshot",
            "printer": printer,
            "paused": paused,
            "jobs": jobs,
        }

    def publish_snapshot(self) -> None:
        self.broker.publish(self.snapshot())

    def broker_message(self) -> str:
        return json.dumps(self.snapshot(), ensure_ascii=False)

    def refresh_printer_state(self) -> dict[str, Any]:
        try:
            printer = self.printer_manager_factory().get_printer_by_uuid(
                self.printer_uuid
            )
            if printer is None:
                state = {"status": "disconnected", "name": None}
            else:
                state = {
                    "status": "busy" if printer.get_busy() else "idle",
                    "name": printer.get_name(),
                }
        except Exception:
            LOGGER.exception("Could not query printer status")
            state = {"status": "disconnected", "name": None}

        with self._state_lock:
            changed = state != self._printer_state
            self._printer_state = state
        if changed:
            self.publish_snapshot()
        return state

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            self.refresh_printer_state()
            self._stop_event.wait(self.poll_interval)

    def _cleanup_loop(self) -> None:
        while not self._stop_event.is_set():
            self.delete_expired_files()
            self._stop_event.wait(self.cleanup_interval)

    def delete_expired_files(self) -> int:
        if self.auto_delete_days is None:
            return 0
        printer_state = self.refresh_printer_state()
        protected_job_id = None
        if printer_state["status"] == "busy":
            protected_job = next(
                (
                    job
                    for job in self.store.list_jobs()
                    if job["status"] == "completed"
                ),
                None,
            )
            if protected_job is not None:
                protected_job_id = protected_job["id"]
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.auto_delete_days)
        deleted_count = 0
        for job in self.store.list_completed_documents_before(
            cutoff.isoformat(timespec="seconds")
        ):
            if job["id"] == protected_job_id:
                continue
            path = self.upload_dir / job["stored_name"]
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            except OSError:
                LOGGER.exception("Could not auto-delete file for job %s", job["id"])
                continue
            deleted_count += 1
        if deleted_count:
            self.publish_snapshot()
        return deleted_count

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            if self.is_paused():
                self._wait_for_work()
                continue

            printer = self._available_printer()
            if printer is None:
                self._wait_for_work()
                continue

            with self._dispatch_lock:
                job = None if self._paused else self.store.claim_next_job()
            if job is None:
                self._wait_for_work()
                continue

            self.publish_snapshot()
            try:
                if job["kind"] == "test_page":
                    printer.print_test_page(DefaultSettings())
                else:
                    document_path = self.upload_dir / job["stored_name"]
                    printer.print(str(document_path), DefaultSettings())
            except Exception as error:
                LOGGER.exception("Print job %s failed", job["id"])
                message = str(error).strip() or type(error).__name__
                self.store.finish_job(job["id"], error=message[:1000])
            else:
                self.store.finish_job(job["id"])
            self.refresh_printer_state()
            self.publish_snapshot()

    def _available_printer(self) -> Any | None:
        try:
            printer = self.printer_manager_factory().get_printer_by_uuid(
                self.printer_uuid
            )
            if printer is None:
                return None
            if printer.get_busy():
                with self._state_lock:
                    self._printer_state = {
                        "status": "busy",
                        "name": printer.get_name(),
                    }
                return None
            with self._state_lock:
                self._printer_state = {
                    "status": "idle",
                    "name": printer.get_name(),
                }
            return printer
        except Exception:
            LOGGER.exception("Could not prepare printer for the next job")
            return None

    def _wait_for_work(self) -> None:
        self._wake_event.wait(self.poll_interval)
        self._wake_event.clear()

    def public_job(self, job: dict[str, Any]) -> dict[str, Any]:
        file_available = job["kind"] == "document" and (
            self.upload_dir / job["stored_name"]
        ).is_file()
        return {
            "id": job["id"],
            "kind": job["kind"],
            "name": job["original_name"],
            "media_type": job["media_type"],
            "size": job["size"],
            "status": job["status"],
            "display_status": job["status"],
            "file_available": file_available,
            "created_at": job["created_at"],
            "queued_at": job["queued_at"],
            "started_at": job["started_at"],
            "completed_at": job["completed_at"],
            "error": job["error"],
            "can_print": job["kind"] == "document"
            and job["status"] == "uploaded",
            "can_cancel": job["status"] in {"uploaded", "queued"},
            "can_download": file_available and job["status"] == "completed",
            "can_delete_file": file_available and job["status"] == "completed",
        }
