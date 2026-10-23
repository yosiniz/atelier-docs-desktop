from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Job:
    id: str
    kind: str
    document_id: str
    status: str = "queued"
    progress: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result: dict | None = None
    error: str | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)
    future: Future | None = field(default=None, repr=False)

    def public(self) -> dict:
        return {"id": self.id, "kind": self.kind, "document_id": self.document_id, "status": self.status,
                "progress": self.progress, "created_at": self.created_at, "updated_at": self.updated_at,
                "result": self.result, "error": self.error}


class JobManager:
    def __init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="atelier-job")
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def submit(self, kind: str, document_id: str, operation: Callable[[threading.Event, Callable[[int], None]], dict]) -> dict:
        job = Job(uuid.uuid4().hex, kind, document_id)
        with self.lock:
            self.jobs[job.id] = job
            if len(self.jobs) > 200:
                for old_id in sorted(self.jobs, key=lambda item: self.jobs[item].created_at)[:-200]:
                    if self.jobs[old_id].status in {"completed", "failed", "cancelled"}:
                        self.jobs.pop(old_id, None)

        def progress(value: int) -> None:
            with self.lock:
                job.progress = max(0, min(100, value)); job.updated_at = time.time()

        def runner() -> None:
            with self.lock:
                if job.cancel_event.is_set(): job.status = "cancelled"; return
                job.status = "running"; job.updated_at = time.time()
            try:
                result = operation(job.cancel_event, progress)
                with self.lock:
                    job.status = "cancelled" if job.cancel_event.is_set() else "completed"
                    job.result = None if job.cancel_event.is_set() else result
                    job.progress = 100 if job.status == "completed" else job.progress
                    job.updated_at = time.time()
            except Exception as exc:
                with self.lock:
                    job.status = "cancelled" if job.cancel_event.is_set() else "failed"
                    job.error = None if job.cancel_event.is_set() else str(exc)
                    job.updated_at = time.time()

        job.future = self.executor.submit(runner)
        return job.public()

    def get(self, job_id: str) -> dict:
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError("İş bulunamadı")
            return self.jobs[job_id].public()

    def cancel(self, job_id: str) -> dict:
        with self.lock:
            if job_id not in self.jobs:
                raise KeyError("İş bulunamadı")
            job = self.jobs[job_id]
            if job.status in {"completed", "failed", "cancelled"}:
                return job.public()
            job.cancel_event.set()
            if job.future and job.future.cancel():
                job.status = "cancelled"
            else:
                job.status = "cancelling"
            job.updated_at = time.time()
            return job.public()


jobs = JobManager()
