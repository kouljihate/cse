@echo off
chcp 65001 >nul
title Building Document Manager Backend — PyInstaller

echo ============================================
echo  Building Document Manager Backend Server
echo ============================================
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

cd /d "%~dp0"

REM Clean previous builds
if exist "dist\docmanager" rmdir /s /q "dist\docmanager"
if exist "build\docmanager" rmdir /s /q "build\docmanager"
if exist "docmanager.spec" del "docmanager.spec"

echo.
echo Building standalone executable...
echo.

pyinstaller ^
    --name docmanager ^
    --onedir ^
    --console ^
    --add-data "backend/app/templates;app/templates" ^
    --add-data "backend/app/static;app/static" ^
    --add-data "backend/app/static/fonts;app/static/fonts" ^
    --hidden-import flask_socketio ^
    --hidden-import simple_websocket ^
    --hidden-import engineio.async_drivers.threading ^
    --hidden-import pydantic_settings ^
    --hidden-import weasyprint ^
    --hidden-import reportlab ^
    --hidden-import bcrypt ^
    --hidden-import email_validator ^
    --collect-all weasyprint ^
    --collect-all reportlab ^
    backend\run.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo Copying additional files...
copy "backend\.env.example" "dist\docmanager\.env.example" >nul
copy "dist_readme.txt" "dist\docmanager\README.txt" >nul

REM Create launcher script
echo @echo off > "dist\docmanager\run.bat"
echo chcp 65001 ^>nul >> "dist\docmanager\run.bat"
echo echo Starting Document Manager Backend Server... >> "dist\docmanager\run.bat"
echo. >> "dist\docmanager\run.bat"
echo REM Edit the IP below to match your MongoDB host >> "dist\docmanager\run.bat"
echo docmanager.exe --db-host 192.168.1.100 >> "dist\docmanager\run.bat"
echo pause >> "dist\docmanager\run.bat"

echo.
echo ============================================
echo  Build complete!
echo.
echo  Output: dist\docmanager\
echo  Executable: dist\docmanager\docmanager.exe
echo.
echo  To distribute:
echo    1. Install MongoDB on target machine
echo    2. Copy dist\cse\ folder to target
echo    3. Edit .env.example -^> rename to .env
echo       and set MONGO_HOST or use --db-host
echo    4. Run: docmanager.exe --db-host IP_ADDRESS
echo       Or double-click run.bat (edit IP first)
echo ============================================
pause
