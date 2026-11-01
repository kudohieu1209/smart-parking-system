# Script khởi động Backend FastAPI Server
Write-Host "Starting Smart Parking Backend API on http://localhost:8000..." -ForegroundColor Cyan
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
