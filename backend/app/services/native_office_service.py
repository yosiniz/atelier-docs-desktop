from __future__ import annotations

import base64
import os
import subprocess
import threading
from pathlib import Path


_OFFICE_CONVERSION_LOCK = threading.Lock()


_POWERSHELL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$source = [IO.Path]::GetFullPath($env:ATELIER_OFFICE_SOURCE)
$output = [IO.Path]::GetFullPath($env:ATELIER_OFFICE_OUTPUT)
$kind = $env:ATELIER_OFFICE_KIND
$application = $null
$document = $null

try {
    if ($kind -eq 'docx') {
        $application = New-Object -ComObject Word.Application
        $application.Visible = $false
        $application.DisplayAlerts = 0
        try { $application.AutomationSecurity = 3 } catch {}
        $document = $application.Documents.Open($source, $false, $true, $false, '', '', $false, '', '', 0, 0, $false, $true, 0, $true)
        $document.ExportAsFixedFormat($output, 17, $false, 0, 0, 1, 2147483647, 0, $true, $true, 1, $true, $true, $false)
    }
    elseif ($kind -eq 'xlsx' -or $kind -eq 'csv') {
        $application = New-Object -ComObject Excel.Application
        $application.Visible = $false
        $application.DisplayAlerts = $false
        try { $application.AutomationSecurity = 3 } catch {}
        $document = $application.Workbooks.Open($source, 0, $true)
        $document.ExportAsFixedFormat(0, $output, 0, $true, $false)
    }
    elseif ($kind -eq 'pptx') {
        $application = New-Object -ComObject PowerPoint.Application
        try { $application.AutomationSecurity = 3 } catch {}
        $document = $application.Presentations.Open($source, $true, $true, $false)
        $document.SaveAs($output, 32)
    }
    else {
        throw "Unsupported Office kind: $kind"
    }
}
finally {
    if ($document -ne $null) {
        try {
            if ($kind -eq 'docx') { $document.Close($false) }
            elseif ($kind -eq 'xlsx' -or $kind -eq 'csv') { $document.Close($false) }
            elseif ($kind -eq 'pptx') { $document.Close() }
        } catch {}
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) } catch {}
    }
    if ($application -ne $null) {
        try { $application.Quit() } catch {}
        try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($application) } catch {}
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
"""


def _encoded_command(script: str) -> str:
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def office_to_pdf_native(path: Path, output: Path, timeout_seconds: int = 120) -> dict | None:
    """Use the locally installed Microsoft Office renderer when available.

    The source is opened read-only, macros are disabled, and the converter runs in
    a separate hidden PowerShell process. Returning ``None`` lets callers use their
    deterministic local fallback on systems without Microsoft Office.
    """
    suffix = path.suffix.lower().lstrip(".")
    if suffix not in {"docx", "xlsx", "csv", "pptx"} or os.name != "nt":
        return None

    env = os.environ.copy()
    env["ATELIER_OFFICE_SOURCE"] = str(path.resolve())
    env["ATELIER_OFFICE_OUTPUT"] = str(output.resolve())
    env["ATELIER_OFFICE_KIND"] = suffix
    output.unlink(missing_ok=True)

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        with _OFFICE_CONVERSION_LOCK:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-EncodedCommand",
                    _encoded_command(_POWERSHELL_SCRIPT),
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                creationflags=creation_flags,
                check=False,
            )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        output.unlink(missing_ok=True)
        return None

    if completed.returncode != 0 or not output.exists() or output.stat().st_size < 5:
        output.unlink(missing_ok=True)
        return None
    try:
        if output.read_bytes()[:5] != b"%PDF-":
            output.unlink(missing_ok=True)
            return None
    except OSError:
        output.unlink(missing_ok=True)
        return None

    return {
        "mode": "native-microsoft-office",
        "warning": "Yerleşim, yerel Microsoft Office PDF motoruyla korundu.",
    }
