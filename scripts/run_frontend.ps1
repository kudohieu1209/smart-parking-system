# Script khởi động Frontend Vite React Server
Write-Host "Starting Smart Parking Dashboard on http://localhost:5173..." -ForegroundColor Cyan
Set-Location -Path "$PSScriptRoot\..\frontend"
npm run dev
