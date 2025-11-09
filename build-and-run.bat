@echo off
REM MTG Tournament Dashboard - Docker Build and Run Script for Windows

echo.
echo 🐳 MTG Tournament Dashboard - Docker Deployment
echo ================================================

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "tournament_dashboard.py" (
    echo ❌ tournament_dashboard.py not found in current directory
    pause
    exit /b 1
)

if not exist "templates\dashboard.html" (
    echo ❌ templates\dashboard.html not found
    pause
    exit /b 1
)

if not exist "July_CEDH_Event\13th July CEDH Participant List.xlsx" (
    echo ❌ Excel participant file not found
    pause
    exit /b 1
)

echo ✅ All required files found

REM Stop any existing container
echo 🛑 Stopping existing containers...
docker-compose down

REM Build and start the container
echo 🏗️  Building and starting container...
docker-compose up -d --build

REM Wait for container to be ready
echo ⏳ Waiting for container to be ready...
timeout /t 5 /nobreak >nul

REM Check if container is running
docker ps | findstr "mtg-tournament-dashboard" >nul
if %errorlevel% equ 0 (
    echo ✅ Container is running successfully!
    echo.
    echo 🎯 Access the application at:
    echo    Local: http://localhost:5000
    for /f "tokens=1" %%i in ('hostname') do echo    Network: http://%%i:5000
    echo.
    echo 📊 Container status:
    docker ps --filter "name=mtg-tournament-dashboard"
    echo.
    echo 📝 To view logs: docker-compose logs -f
    echo 🛑 To stop: docker-compose down
    echo.
    pause
) else (
    echo ❌ Container failed to start. Check logs:
    docker-compose logs
    pause
    exit /b 1
) 