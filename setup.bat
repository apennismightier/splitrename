@echo off
title EpisodeSplit - Setup
echo.
echo  ================================================
echo   EPISODESPLIT - Setup
echo  ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)
echo  [OK] Python found

:: Install dependencies
echo.
echo  Installing Python dependencies...
pip install PyQt6 --quiet
if errorlevel 1 (
    echo  [ERROR] Failed to install PyQt6. Try: pip install PyQt6 manually.
    pause
    exit /b 1
)
echo  [OK] PyQt6 installed

:: Check ffmpeg
echo.
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo  [WARNING] FFmpeg not found in PATH.
    echo.
    echo  FFmpeg is required for video analysis and splitting.
    echo  Download it from: https://ffmpeg.org/download.html
    echo.
    echo  Quick install via winget:
    echo    winget install Gyan.FFmpeg
    echo.
    echo  Or via chocolatey:
    echo    choco install ffmpeg
    echo.
    echo  After installing, re-run this setup to verify.
) else (
    echo  [OK] FFmpeg found
)

echo.
echo  ================================================
echo   Setup complete! Run: python episode_splitter.py
echo  ================================================
echo.
pause
