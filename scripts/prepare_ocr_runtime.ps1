$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$targetRoot = Join-Path $projectRoot "ocr-runtime\windows"
$allowedRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "ocr-runtime"))
$resolvedTarget = [System.IO.Path]::GetFullPath($targetRoot)
if (-not $resolvedTarget.StartsWith($allowedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OCR hedef klasörü proje dışında olamaz."
}

$candidates = @(@(
    $env:ATELIER_TESSERACT_CMD,
    (Join-Path $env:ProgramFiles "Tesseract-OCR\tesseract.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Tesseract-OCR\tesseract.exe"),
    (Get-Command tesseract.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1)
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) })

if (-not $candidates) {
    throw "Tesseract bulunamadı. Önce UB-Mannheim.TesseractOCR paketini kurun."
}

$sourceExe = (Resolve-Path -LiteralPath $candidates[0]).Path
$sourceRoot = Split-Path -Parent $sourceExe
if (Test-Path -LiteralPath $resolvedTarget) {
    Get-ChildItem -LiteralPath $resolvedTarget -Force | Remove-Item -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $resolvedTarget | Out-Null
Copy-Item -LiteralPath $sourceExe -Destination $resolvedTarget -Force
Copy-Item -Path (Join-Path $sourceRoot "*.dll") -Destination $resolvedTarget -Force

$targetData = Join-Path $resolvedTarget "tessdata"
New-Item -ItemType Directory -Force -Path $targetData | Out-Null
Copy-Item -Path (Join-Path $projectRoot "assets\tessdata\*.traineddata") -Destination $targetData -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "assets\TESSERACT_LICENSE.txt") -Destination $resolvedTarget -Force

if (-not (Test-Path -LiteralPath (Join-Path $resolvedTarget "tesseract.exe"))) {
    throw "OCR motoru paketleme klasörüne kopyalanamadı."
}
Write-Host "OCR runtime hazır: $resolvedTarget"
