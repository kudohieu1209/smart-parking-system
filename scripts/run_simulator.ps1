# Script khởi động Mock ESP32 Telemetry Generator
Write-Host "Starting Mock ESP32 Simulator..." -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\.."
python simulator/mock_esp32.py --interval 2.0
