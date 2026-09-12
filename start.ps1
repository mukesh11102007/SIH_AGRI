#!/usr/bin/env pwsh
# start.ps1 — One-command startup for the Smart Farming Platform
# Usage: .\start.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Smart Farming Platform — Starting Up  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker is available
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Docker is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Docker Desktop from https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    exit 1
}

# Check Docker daemon is running
try {
    docker info 2>&1 | Out-Null
} catch {
    Write-Host "ERROR: Docker daemon is not running. Start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host "Building images (first run may take 5-10 minutes)..." -ForegroundColor Yellow
docker compose build

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed. See errors above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting all services..." -ForegroundColor Yellow
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "Startup failed. See errors above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting for services to become healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "Service status:" -ForegroundColor Cyan
docker compose ps

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  System is running!" -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard:   http://localhost:3000    " -ForegroundColor White
Write-Host "  API Docs:    http://localhost:8000/api/docs" -ForegroundColor White
Write-Host "  Health:      http://localhost:8000/api/v1/health" -ForegroundColor White
Write-Host ""
Write-Host "  View logs:   docker compose logs -f  " -ForegroundColor Gray
Write-Host "  Stop:        docker compose down      " -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Green
