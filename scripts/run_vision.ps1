# Script khởi động Computer Vision Module (Synthetic ROI Stream)
Write-Host "Starting Computer Vision Module..." -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\.."
python -m vision.src.main --source synthetic --interval 2.0
