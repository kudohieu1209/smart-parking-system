# Script chạy toàn bộ 5 kịch bản kiểm thử mô phỏng E2E
Write-Host "Running All 5 End-to-End Simulation Scenarios..." -ForegroundColor Yellow
Set-Location -Path "$PSScriptRoot\.."
python simulator/scenarios/run_all_scenarios.py

