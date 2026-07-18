# Watch-Servers Release Build Script
# This script builds the executable and creates a release package

$ErrorActionPreference = "Stop"

# Get version from settings or use default
$version = "1.0.0"
if (Test-Path "app\config\settings.py") {
    $settingsContent = Get-Content "app\config\settings.py" -Raw
    if ($settingsContent -match "app_version\s*=\s*['""]([^'""]+)['""]") {
        $version = $matches[1]
    }
}

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Watch-Servers Release Build Script" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Version: $version" -ForegroundColor Green
Write-Host ""

# Release directory configuration
$releaseDir = "release\watch-servers-v$version-win-x64"
$zipName = "watch-servers-v$version-win-x64.zip"

Write-Host "Release Directory: $releaseDir" -ForegroundColor Yellow
Write-Host "ZIP File: $zipName" -ForegroundColor Yellow
Write-Host ""

# Clean previous build
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Cleaning previous build..." -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

if (Test-Path "build") {
    Write-Host "Removing build directory..." -ForegroundColor Yellow
    Remove-Item -Path "build" -Recurse -Force
}

if (Test-Path "dist") {
    Write-Host "Removing dist directory..." -ForegroundColor Yellow
    Remove-Item -Path "dist" -Recurse -Force
}

if (Test-Path "release") {
    Write-Host "Removing release directory..." -ForegroundColor Yellow
    Remove-Item -Path "release" -Recurse -Force
}

Write-Host "Cleanup complete." -ForegroundColor Green
Write-Host ""

# Build executable with PyInstaller
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Building executable with PyInstaller..." -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

try {
    pyinstaller watch-servers.spec --clean
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE"
    }
    Write-Host "Build successful!" -ForegroundColor Green
} catch {
    Write-Host "Build failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Create release directory structure
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Creating release directory structure..." -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

New-Item -ItemType Directory -Path "$releaseDir\config" -Force | Out-Null
New-Item -ItemType Directory -Path "$releaseDir\request\sql_files" -Force | Out-Null
New-Item -ItemType Directory -Path "$releaseDir\results" -Force | Out-Null
New-Item -ItemType Directory -Path "$releaseDir\log" -Force | Out-Null
New-Item -ItemType Directory -Path "$releaseDir\user_manual" -Force | Out-Null

Write-Host "Directory structure created." -ForegroundColor Green
Write-Host ""

# Copy files
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Copying files..." -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# Copy executable
if (Test-Path "dist\watch-servers.exe") {
    Write-Host "Copying watch-servers.exe..." -ForegroundColor Yellow
    Copy-Item "dist\watch-servers.exe" -Destination "$releaseDir\watch-servers.exe"
} else {
    Write-Host "ERROR: watch-servers.exe not found in dist directory" -ForegroundColor Red
    exit 1
}

# Copy config files
if (Test-Path "config\dbinfo.json") {
    Write-Host "Copying dbinfo.json..." -ForegroundColor Yellow
    Copy-Item "config\dbinfo.json" -Destination "$releaseDir\config\dbinfo.json"
} else {
    Write-Host "WARNING: dbinfo.json not found, creating empty config..." -ForegroundColor Yellow
    @{} | ConvertTo-Json | Out-File "$releaseDir\config\dbinfo.json" -Encoding utf8
}

# Copy sample files
if (Test-Path "request\sql_files\telnet_test_sample.csv") {
    Write-Host "Copying telnet_test_sample.csv..." -ForegroundColor Yellow
    Copy-Item "request\sql_files\telnet_test_sample.csv" -Destination "$releaseDir\request\sql_files\telnet_test_sample.csv"
}

if (Test-Path "request\sql_files\db_test_sample.csv") {
    Write-Host "Copying db_test_sample.csv..." -ForegroundColor Yellow
    Copy-Item "request\sql_files\db_test_sample.csv" -Destination "$releaseDir\request\sql_files\db_test_sample.csv"
}

# Copy documentation
if (Test-Path "README.md") {
    Write-Host "Copying README.md..." -ForegroundColor Yellow
    Copy-Item "README.md" -Destination "$releaseDir\README.md"
}

if (Test-Path "LICENSE") {
    Write-Host "Copying LICENSE..." -ForegroundColor Yellow
    Copy-Item "LICENSE" -Destination "$releaseDir\LICENSE"
}

Write-Host "Files copied successfully." -ForegroundColor Green
Write-Host ""

# Create launcher scripts
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Creating launcher scripts..." -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# English launcher
$runBat = @"
@echo off
echo Starting Watch-Servers...
echo.

watch-servers.exe

pause
"@
$runBat | Out-File "$releaseDir\run.bat" -Encoding ascii
Write-Host "Created run.bat (English)" -ForegroundColor Green

# Korean launcher
$runBatKr = @"
@echo off
echo Watch-Servers 시작 중...
echo.

watch-servers.exe

pause
"@
$runBatKr | Out-File "$releaseDir\run_kr.bat" -Encoding ascii
Write-Host "Created run_kr.bat (Korean)" -ForegroundColor Green

Write-Host ""

# Create .env file template
Write-Host "Creating .env template..." -ForegroundColor Yellow
$envTemplate = @"
APP_NAME=Watch Servers
DEBUG=True
HOST=0.0.0.0
PORT=8000
DB_CONNECTION_TIMEOUT=5
TELNET_TIMEOUT=3
MAX_CSV_SIZE_KB=200
MAX_CSV_ROWS=500
"@
$envTemplate | Out-File "$releaseDir\.env" -Encoding ascii
Write-Host ".env template created." -ForegroundColor Green
Write-Host ""

# Create release info
Write-Host "Creating release info..." -ForegroundColor Yellow
$releaseInfo = @"
Watch-Servers v$version Release Package

Build Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

Included Files:
- watch-servers.exe (Main executable file)
- run.bat (Launcher script - English)
- 실행하기.bat (Launcher script - Korean)
- config/ (Database configuration directory)
  - dbinfo.json (Database connection settings)
- request/sql_files/ (Sample test files)
  - telnet_test_sample.csv (Telnet connection test sample)
  - db_test_sample.csv (Database connection test sample)
- results/ (Results output directory)
- log/ (Log files directory)
- .env (Environment configuration template)
- README.md (Documentation)
- LICENSE (License file)

Usage:
1. Edit config/dbinfo.json with your database connection details
2. (Optional) Edit .env file to configure application settings
3. Run run.bat (English) or 실행하기.bat (Korean) to start the server
4. Access API documentation at http://localhost:8000/docs

Features:
- Database connection testing (MSSQL, MySQL, MariaDB, PostgreSQL, Oracle, Tibero)
- Telnet connection testing
- SQL query execution
- CSV-based batch operations
- CSV to DB data import
- REST API interface with Swagger UI

Supported Databases:
- Microsoft SQL Server (pymssql)
- MySQL/MariaDB (aiomysql)
- PostgreSQL (asyncpg)
- Oracle Database (oracledb)
- Tibero (cx_Oracle)

API Endpoints:
- POST /api/db/check - Single database connection test
- POST /api/db/check-batch - Batch database connection test (CSV)
- POST /api/telnet/check - Single telnet connection test
- POST /api/telnet/check-batch - Batch telnet connection test (CSV)
- POST /api/sql/execute - Execute SQL file
- POST /api/csv/query-batch - CSV-based query batch execution
- POST /api/csv/csv-to-db - Import CSV data to database
- GET /api/config/db-info - Get database configuration
- POST /api/config/db-info - Add database configuration
- PUT /api/config/db-info/{db_name} - Update database configuration
- DELETE /api/config/db-info/{db_name} - Delete database configuration
- GET /docs - Swagger UI documentation

System Requirements:
- Windows 64-bit operating system
- No additional software installation required (standalone executable)

Quick Start:
1. Extract all files to a folder
2. Edit config/dbinfo.json with your database connection details
3. Run run.bat (English) or 실행하기.bat (Korean)
4. Open http://localhost:8000/docs in your browser to access API documentation

For detailed instructions, please refer to README.md
"@
$releaseInfo | Out-File "$releaseDir\RELEASE_INFO.txt" -Encoding utf8
Write-Host "Release info created." -ForegroundColor Green
Write-Host ""

# Count files
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Release file summary" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$fileCount = (Get-ChildItem -Path $releaseDir -Recurse -File | Measure-Object).Count
Write-Host "Total files: $fileCount" -ForegroundColor Green
Write-Host ""

# Create ZIP file
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Creating ZIP file..." -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$zipPath = "release\$zipName"
try {
    Compress-Archive -Path "$releaseDir\*" -DestinationPath $zipPath -Force
    Write-Host "ZIP file created: $zipPath" -ForegroundColor Green
} catch {
    Write-Host "Failed to create ZIP file: $_" -ForegroundColor Red
}

Write-Host ""

# Final summary
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Release build complete!" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Release Directory: $releaseDir" -ForegroundColor Green
Write-Host "ZIP File: $zipPath" -ForegroundColor Green
Write-Host ""
Write-Host "Check the release folder for the output." -ForegroundColor Yellow
