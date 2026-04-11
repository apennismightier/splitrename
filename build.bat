@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title SplitRename - Build

echo.
echo  ================================================
echo   SPLITRENAME  --  Build + Package
echo  ================================================
echo.

:: ── Verify source files exist ────────────────────────────────────────────────
if not exist "episode_splitter.py" (
    echo  [ERROR] episode_splitter.py not found.
    echo  Make sure all files are in the same folder as build.bat.
    pause & exit /b 1
)

:: ── 1. Check Python ──────────────────────────────────────────────────────────
echo  [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found.
    echo  Download from https://python.org and check "Add to PATH" during install.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo        %PYVER% found.

:: ── 2. Install Python dependencies ───────────────────────────────────────────
echo.
echo  [2/4] Installing dependencies (PyQt6, PyInstaller, Pillow)...
pip install --quiet --upgrade PyQt6 pyinstaller Pillow
if errorlevel 1 (
    echo  [ERROR] pip install failed. Check your internet connection.
    pause & exit /b 1
)
echo        Dependencies ready.

:: ── 3. Generate assets + PyInstaller exe ─────────────────────────────────────
echo.
echo  [3/4] Generating icon + building exe (2-4 mins)...
echo.

if not exist "assets" mkdir assets

python generate_icon.py
if errorlevel 1 (
    echo  [WARN] Icon generation failed, using placeholder.
    python -c "open('assets/icon.ico','wb').write(bytes(22))"
)

if exist "dist\SplitRename" rmdir /s /q "dist\SplitRename" 2>nul
if exist "build"             rmdir /s /q "build"             2>nul

pyinstaller SplitRename.spec --noconfirm
if errorlevel 1 (
    echo.
    echo  [ERROR] PyInstaller failed - see output above.
    pause & exit /b 1
)

if not exist "dist\SplitRename\SplitRename.exe" (
    echo  [ERROR] SplitRename.exe not found after build.
    pause & exit /b 1
)
echo.
echo        Exe built successfully.

:: ── 4. Find Inno Setup and compile installer ─────────────────────────────────
echo.
echo  [4/4] Creating installer...

:: Search all common Inno Setup locations
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"  set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"         set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"  set "ISCC=C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
if exist "C:\Program Files\Inno Setup 5\ISCC.exe"         set "ISCC=C:\Program Files\Inno Setup 5\ISCC.exe"

:: Also check if ISCC is on PATH
if not defined ISCC (
    where ISCC.exe >nul 2>&1
    if not errorlevel 1 set "ISCC=ISCC.exe"
)

if not defined ISCC (
    echo.
    echo  [WARN] Inno Setup not found. Skipping installer creation.
    echo.
    echo  To create the installer:
    echo    1. Download Inno Setup 6 from https://jrsoftware.org/isdl.php
    echo    2. Install it, then run build.bat again.
    echo.
    echo  Your portable app is at: dist\SplitRename\SplitRename.exe
    echo  You can distribute that folder as a zip without an installer.
    echo.
    goto :done_portable
)

echo        Found Inno Setup at: %ISCC%
if not exist "installer_output" mkdir installer_output

"%ISCC%" installer.iss
if errorlevel 1 (
    echo.
    echo  [ERROR] Inno Setup compilation failed - see output above.
    pause & exit /b 1
)

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  ================================================
echo   BUILD COMPLETE
echo  ================================================
echo.
echo   Installer : installer_output\SplitRename_Setup.exe
echo   Portable  : dist\SplitRename\SplitRename.exe
echo.
echo  Double-click the installer to install on any Windows PC.
echo.
pause
exit /b 0

:done_portable
echo  ================================================
echo   BUILD COMPLETE  (portable only, no installer)
echo  ================================================
echo.
echo   App : dist\SplitRename\SplitRename.exe
echo.
pause
exit /b 0
