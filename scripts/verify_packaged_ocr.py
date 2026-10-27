"""Run a native backend with its bundled OCR and verify the actual queued API."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import fitz
import httpx


root = Path(__file__).resolve().parents[1]
resources = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "release/win-unpacked/resources"
exe = resources / "backend/atelier-backend.exe"
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
env = dict(os.environ, ATELIER_PORT=str(port), ATELIER_API_TOKEN="ocr-local-acceptance",
           ATELIER_TESSERACT_CMD=str(resources / "ocr/windows/tesseract.exe"),
           TESSDATA_PREFIX=str(resources / "ocr/windows/tessdata"))
process = subprocess.Popen([str(exe)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
try:
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", headers={"X-Atelier-Token": "ocr-local-acceptance"}, timeout=10) as client:
        for _ in range(120):
            try:
                health = client.get("/api/health").json()
                break
            except (httpx.HTTPError, ValueError):
                time.sleep(.25)
        else:
            raise RuntimeError("Native backend did not start")
        assert health["capabilities"]["ocr"]["turkish"]
        source = root / "output/pdf/ocr-quality-source.pdf"
        with source.open("rb") as handle:
            response = client.post("/api/files", files={"file": ("quality-scan.pdf", handle, "application/pdf")})
        response.raise_for_status()
        identifier = response.json()["data"]["id"]
        response = client.post(f"/api/jobs/pdf/{identifier}/ocr", json={"layout": "table", "dpi": 300})
        response.raise_for_status()
        job = response.json()["data"]
        for _ in range(300):
            job = client.get(f"/api/jobs/{job['id']}").json()["data"]
            if job["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(.3)
        assert job["status"] == "completed", job
        response = client.get(f"/api/files/{identifier}/download")
        response.raise_for_status()
        target = root / "output/pdf/ocr-native-verified.pdf"
        target.write_bytes(response.content)
        with fitz.open(target) as document:
            text = document[0].get_text()
            assert "12345" in text and "3.142,15" in text
        blocks = client.get(f"/api/pdf/{identifier}/pages/0/text").json()["data"]
        selected = next(block for block in blocks if block["text"] == "12345")
        assert selected["confidence"] is not None and selected["is_ocr"]
        probe = client.post(f"/api/pdf/{identifier}/text-style", json={"page": 0,
            "rect": selected["bbox"], "original_text": "12345"})
        probe.raise_for_status()
        style = probe.json()["data"]
        changed = client.post(f"/api/pdf/{identifier}/edit-text", json={"page": 0,
            "rect": selected["bbox"], "text": "67890", "original_text": "12345", "preserve_style": True})
        changed.raise_for_status()
        after_blocks = client.get(f"/api/pdf/{identifier}/pages/0/text").json()["data"]
        selected = next(block for block in after_blocks if block["text"] == "67890")
        assert abs(selected["font_size"] - style["font_size"]) < .05
        assert selected["color"] == style["color"]
        edited = client.post(f"/api/pdf/{identifier}/edit-text", json={"page": 0,
            "rect": selected["bbox"], "text": "", "original_text": "67890"})
        edited.raise_for_status()
        removed = client.get(f"/api/files/{identifier}/download").content
        assert b"12345" not in removed and b"67890" not in removed
        with fitz.open(stream=removed, filetype="pdf") as document:
            assert "12345" not in document[0].get_text()
        print(json.dumps({"packaged_ocr": "passed", "automatic_style": "passed", "permanent_ocr_delete": "passed", "turkish": True, "audit": job["result"]["audit"]}, ensure_ascii=True))
finally:
    if os.name == "nt":
        subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        process.terminate()
    process.wait(timeout=10)
