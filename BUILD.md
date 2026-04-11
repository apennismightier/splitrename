# Building SplitRename — Windows Installer

This produces two outputs:
- `installer_output\SplitRename_Setup.exe` — a proper Windows installer
- `dist\SplitRename\` — a portable folder (zip to share without an installer)

---

## Prerequisites

| Tool | Where to get it |
|------|----------------|
| Python 3.10+ (64-bit) | https://python.org — check **"Add to PATH"** during install |
| Inno Setup 6 | https://jrsoftware.org/isdl.php — for the installer only |

---

## Build Steps

### Option A — One command (recommended)

```
build.bat
```

It will:
1. Check Python is installed
2. Install/upgrade `PyQt6` and `pyinstaller` via pip
3. Generate the app icon (`assets/icon.ico`)
4. Run PyInstaller → produces `dist\SplitRename\SplitRename.exe`
5. Run Inno Setup → produces `installer_output\SplitRename_Setup.exe`

If Inno Setup isn't installed, step 5 is skipped and you'll get the portable folder only.

---

### Option B — Manual steps

```bat
:: 1. Install deps
pip install PyQt6 pyinstaller

:: 2. Generate icon
python generate_icon.py

:: 3. Build exe
pyinstaller SplitRename.spec --noconfirm

:: 4. Build installer (requires Inno Setup installed)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

---

## What the installer does

- Installs to `%ProgramFiles%\SplitRename\` (or `%LocalAppData%` if no admin rights)
- Creates a **Start Menu** shortcut
- Optionally creates a **Desktop** shortcut
- Pre-creates a `bin\` folder where FFmpeg will be downloaded on first use
- Registers a proper **uninstaller** (visible in Add/Remove Programs)
- On uninstall: removes the `bin\` folder and version cache, leaves user data alone

---

## What the user sees after installing

1. Launch SplitRename from Start Menu or Desktop
2. Click **⬆ FFmpeg Manager** → **Download & Install**
3. FFmpeg downloads into `bin\` inside the install folder (~90 MB)
4. Analyze and split video files

No Python required on the end user's machine — everything is bundled.

---

## File layout after build

```
dist\
  SplitRename\
    SplitRename.exe       ← main application
    ffmpeg_manager.py      ← bundled alongside exe
    PyQt6\                 ← Qt libraries
    bin\                   ← empty; FFmpeg downloads here at runtime
    ...

installer_output\
    SplitRename_Setup.exe ← distributable installer (~60–80 MB)
```

---

## Troubleshooting

**PyInstaller: "ModuleNotFoundError: No module named 'PyQt6'"**
Run `pip install PyQt6` then retry.

**Inno Setup not found**
Install from https://jrsoftware.org/isdl.php (free), then re-run `build.bat`.
Or open `installer.iss` manually in the Inno Setup IDE and press F9.

**App crashes on launch (end user machine)**
The PyInstaller build is self-contained — no Python needed. If it crashes,
run from Command Prompt to see the error:
```
cd "C:\Program Files\SplitRename"
SplitRename.exe
```

**Antivirus flags the exe**
Common with PyInstaller bundles. You can code-sign the exe with a certificate,
or submit it to Windows Defender for analysis at:
https://www.microsoft.com/en-us/wdsi/filesubmission
