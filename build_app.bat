@echo off
chcp 65001 >nul
title Building CSE Backend — PyInstaller

echo ============================================
echo  Building CSE Backend Server
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
if exist "dist\cse" rmdir /s /q "dist\cse"
if exist "build\cse" rmdir /s /q "build\cse"
if exist "cse.spec" del "cse.spec"

echo.
echo Building standalone executable...
echo.

pyinstaller ^
    --name cse ^
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
copy "backend\.env.example" "dist\cse\.env.example" >nul
copy "dist_readme.txt" "dist\cse\README.txt" >nul

REM Create launcher script
echo @echo off > "dist\cse\run.bat"
echo chcp 65001 ^>nul >> "dist\cse\run.bat"
echo echo Starting CSE Backend Server... >> "dist\cse\run.bat"
echo. >> "dist\cse\run.bat"
echo REM Edit the IP below to match your MongoDB host >> "dist\cse\run.bat"
echo cse.exe --db-host 192.168.1.100 >> "dist\cse\run.bat"
echo pause >> "dist\cse\run.bat"

echo.
echo ============================================
echo  Build complete!
echo.
echo  Output: dist\cse\
echo  Executable: dist\cse\cse.exe
echo.
echo  To distribute:
echo    1. Install MongoDB on target machine
echo    2. Copy dist\cse\ folder to target
echo    3. Edit .env.example -^> rename to .env
echo       and set MONGO_HOST or use --db-host
echo    4. Run: cse.exe --db-host IP_ADDRESS
echo       Or double-click run.bat (edit IP first)
echo ============================================
pause
