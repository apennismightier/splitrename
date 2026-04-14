# SPLIT**RENAME**
### by apennismightier

A Windows desktop app that splits multi-episode video files at black frame boundaries and renames the output files using real episode titles from TMDB and TVDB.

---

## Table of Contents
- [What It Does](#what-it-does)
- [File Management](#-file-management)
- [Black Frame Detection](#-black-frame-detection)
- [Cut Modes](#-cut-modes)
- [Output Encoding](#-output-encoding-options)
- [Split Count Control](#-split-count-control)
- [Batch Processing](#-batch-processing)
- [Manual Split Point Editing](#-manual-split-point-editing)
- [Episode Renaming](#️-episode-renaming--tmdb--tvdb)
- [Power Management](#-power-management)
- [Cancel](#-cancel)
- [FFmpeg Manager](#️-ffmpeg-manager)
- [Built-in Help](#-built-in-help)
- [Requirements](#requirements)
- [Installation](#installation)

---

## What It Does

SplitRename takes video files containing multiple TV episodes — e.g. `Show.S01E01-E02.mkv` — detects the black frames between episodes, splits them into individual files, and renames the output using real episode titles fetched from TMDB or TVDB.

---

## 📂 File Management

- Drag and drop video files or folders directly into the app
- Supports **MKV, MP4, AVI, MOV, TS, M2TS, WMV**
- Multi-select files for batch processing
- File list shows live status for every file:

```
○ queued  →  ◌ analyzing  →  ◉ ready  →  ◈ splitting  →  ✓ done  /  ✗ error
```

---

## 🔍 Black Frame Detection

The app scans each video for the black frames that appear between episodes and uses them as cut points. Three tunable settings — each has a **[?]** help button:

| Setting | Description | Default |
|---|---|---|
| Min Duration | Seconds of black that must appear to count as a break | 0.50s |
| Pixel Threshold | How dark each pixel must be to count as "black" | 0.10 |
| Picture Threshold | Fraction of the frame that must be dark | 0.98 |

---

## ✂️ Cut Modes

| Mode | Speed | Quality | Notes |
|---|---|---|---|
| **Keyframe Snap** | Fastest | Lossless | Cuts at nearest keyframe — recommended for most use |
| **Smart Encode** | Fast | Near-lossless | Re-encodes only the first few seconds after each cut, copies the rest |
| **Accurate Re-encode** | Slow | Configurable | Full re-encode for frame-exact cuts |
| **Stream Copy** | Fastest | Lossless | May start a few seconds before the actual cut point |

---

## 🎛️ Output Encoding Options

| Setting | Options |
|---|---|
| Container | Same as source · MP4 · MKV |
| Video Codec | Same as source (copy) · H.264 · H.265 · HEVC NVENC (GPU) · AV1 |
| Audio Codec | AAC · AC3 (Dolby) · Copy |
| Speed Preset | Lossless → Ultra Fast → Fast → Medium → Very Slow |
| Quality Mode | CRF (quality-based) or fixed Bitrate (kbps) |

---

## 🔢 Split Count Control

- **Auto-detect** — splits at every detected black frame
- **Use first N breaks** — if a file has 3 detected breaks but you only want 2 output files, set N=2 and only the first break is used

---

## ⚡ Batch Processing

| Button | What It Does |
|---|---|
| 🔍 Batch Analyze All | Scans all files for break points with no splitting — review timecodes first |
| ⚡ Batch: Analyze + Split All | Fully automated — analyze then split in one shot |
| Analyze / Split | Step-by-step buttons for manual control |

---

## ✏️ Manual Split Point Editing

Click any file after analysis and the right panel shows every detected break with its timecode:

- **Edit** any timecode — click Edit and type a new time in `MM:SS` or `HH:MM:SS`
- **Delete** any break point you don't want
- **+ Add** — type any timecode in the input box to insert a manual split point

---

## 🏷️ Episode Renaming — TMDB / TVDB

A built-in FileBot-style renaming module. **No account required** — API keys are pre-configured.

### How it works

1. Search for your TV show by name and optional year
2. Choose to search **Both**, **TMDB only**, or **TVDB only** — switch between them anytime
3. Load the full episode list for any season
4. The app maps each output file to the correct episode automatically, using the episode number from the source filename to set the starting offset
5. Preview every output filename before committing — e.g. `Curious George - S01E11 - Hundley Goes to School.mkv`
6. Double-click any title to edit it manually
7. Click **✓ Confirm** to rename all files instantly

### Two ways to access it

- Check **"Rename output files (TMDB/TVDB)"** in the Cut Mode section → the dialog opens automatically after splitting, pre-loaded with your fresh output files
- Click **🏷 Rename Files** in the action bar at any time → pick any folder of video files to rename without splitting anything

---

## 💤 Power Management

- The PC is **automatically prevented from sleeping or hibernating** during any batch job — no configuration needed
- A **"When done"** dropdown in the action bar controls what happens when the batch finishes:

| Option | Behaviour |
|---|---|
| Do nothing | Leaves the PC running normally (default) |
| Sleep | Low-power standby |
| Hibernate | Saves state to disk and powers off |
| Shut down | Full shutdown with a 30-second cancellable warning |

---

## ✕ Cancel

- A **Cancel** button appears in the action bar whenever a job is running
- Stops the job cleanly **after the current file finishes** — nothing gets abandoned mid-encode

---

## 🛠️ FFmpeg Manager

- SplitRename manages its own copy of FFmpeg — **no separate installation required**
- Stored in `%LOCALAPPDATA%\SplitRename\bin\`
- The **FFmpeg Manager** button in the header lets you check the current version and update automatically

---

## ❓ Built-in Help

Every setting has a **[?]** button that opens a plain-English popup explaining what it does, what the numbers mean, and when you'd want to change it.

---

## Requirements

- Windows 10 or later
- FFmpeg (auto-managed — downloaded on first launch)
- Internet connection for TMDB/TVDB lookups

---

## Installation

1. Download the latest `SplitRename_Setup.exe` from [Releases](../../releases)
2. Run the installer
3. Launch SplitRename
4. On first launch, click **FFmpeg Manager** to download FFmpeg automatically

### Building from source

```bat
git clone https://github.com/apennismightier/episodesplit.git
cd episodesplit
build.bat
```

Requires Python 3.10+ and Inno Setup 6 for the installer step.

---

*SplitRename v1.6.2 · by apennismightier*
