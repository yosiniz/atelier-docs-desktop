from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from backend.app.main import app


if getattr(sys, "frozen", False):
    bundle_root = Path(getattr(sys, "_MEIPASS"))
    if str(bundle_root) not in sys.path:
        sys.path.insert(0, str(bundle_root))


def main() -> None:
    port = int(os.environ.get("ATELIER_PORT", "8765"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
