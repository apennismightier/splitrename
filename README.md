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
- [Manual Split Points](#-manual-split-points)
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

\`\`\`
○ queued  →  ◌ analyzing  →  ◉ ready  →  ◈ splitting  →  ✓ done  /  ✗ error
\`\`\`

---

## 🔍 Black Frame Detection

The app scans each video for the black frames that appear between episodes and uses them as cut points. Three tunable settings — each has a **[?]** help button:

| Setting | Description | Default |
|---|---|---|
| Min Duration | Seconds of black that must appear to count as a break | 0.50s |
| Pixel Threshold | How dark each pixel must be to count as "black" | 0.10 |
| Picture Threshold | Fraction of the frame that must be dark | 0.98 |

### Ignore Credits Break

Check **"Ignore credits break (will ignore all breaks within the first 5 minutes)"** to prevent opening credits from being detected as a split point. Useful for shows that have a black frame after the cold open or title card.

---

## ✂️ Cut Modes

| Mode | Speed | Quality | Notes |
|---|---|---|---|
| **Keyframe Snap** | Fastest | Lossless | Cuts at nearest keyframe — recommended for most use |
| **Smart Encode** | Fast | Near-lossless | Re-encodes only the first few seconds at each cut, copies the rest |
| **Accurate Re-encode** | Slow | Configurable | Full re-encode for frame-exact cuts |
| **Stream Copy** | Fastest | Lossless | May start a few seconds before the actual cut point |

### Smart Encode — How It Works

Smart Encode achieves frame-accurate cuts without a full re-encode:

1. Probes the source file to find the exact keyframe (`K`) at the cut point
2. Re-encodes only the opening seconds of each segment up to `K` (typically 2–5 seconds)
3. Stream-copies the rest of the segment directly — fast, no quality loss
4. Concatenates both parts using MKV intermediates to avoid timestamp issues
5. Remuxes to your chosen output container

Handles H.264, H.265/HEVC, AV1 video and auto-transcodes EAC3/AC3/DTS audio to AAC where needed.

### Rename Output Files

Check **"Rename output files (TMDB/TVDB)"** in the Cut Mode section to automatically open the Episode Renaming dialog after splitting, pre-loaded with the freshly split files.

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

## ✏️ Manual Split Points

The right-hand panel shows detected break points for whichever file is selected. You can edit the split list at any time:

- **Edit** any timecode — click Edit and type a new time in `MM:SS` or `HH:MM:SS`
- **Delete** any break point you don't want
- **+ Add** — type any timecode in the input box to insert a manual split point

### Splitting Without Analysis

You don't need to run Analyze first. Add a file, type a timecode in the split point box, and click **+ Add**. The Split button activates immediately. Clicking Split probes the file on the fly and cuts at your manual point — no full black frame scan needed.

---

## 🏷️ Episode Renaming — TMDB / TVDB

A built-in FileBot-style renaming module. **No account required** — API keys are pre-configured.

### How it works

1. Search for your TV show by name and optional year
2. Choose to search **Both**, **TMDB only**, or **TVDB only** using the radio buttons — or use the **Search TMDB** / **Search TVDB** quick-switch buttons to re-run the search instantly
3. Click **Load All Episodes** to fetch every season in one shot
4. The app reads the `S##E##` pattern from each filename and maps it to the correct episode automatically — works across multiple seasons in the same batch
5. Preview every output filename before committing — e.g. `Curious George - S05E03 - The Big Sleepy.mkv`
6. Double-click any title to edit it manually
7. Click **✓ Confirm** to rename all files instantly

### Two ways to access it

- Check **"Rename output files (TMDB/TVDB)"** in the Cut Mode section → dialog opens automatically after splitting
- Click **🏷 Rename Files** in the action bar at any time → rename any folder of video files without splitting

---

## 💤 Power Management

- The PC is **automatically prevented from sleeping or hibernating** during any batch job
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
- Button changes to "Cancelling…" and disables itself to prevent double-clicks

---

## 🛠️ FFmpeg Manager

- SplitRename manages its own copy of FFmpeg — **no separate installation required**
- Stored in `%LOCALAPPDATA%\SplitRename\bin\`
- **Auto-update on startup** — SplitRename silently checks for a newer FFmpeg build each time it launches. If one is found it downloads and installs automatically with no interruptions. A small **"↑ Updated to vX"** label appears under the version in the top-right corner if an update was applied
- Click **FFmpeg Manager** in the header to manually check the version, force a reinstall, or see the installed path

---

## ❓ Built-in Help

Every setting has a **[?]** button that opens a plain-English popup explaining what it does, what the numbers mean, and when you'd want to change it.

---

## Requirements

- Windows 10 or later
- FFmpeg (auto-managed — downloaded and updated automatically on first run)
- Internet connection for TMDB/TVDB lookups and FFmpeg auto-update

---

## Installation

1. Download the latest `SplitRename_Setup.exe` from [Releases](../../releases)
2. Run the installer
3. Launch SplitRename — FFmpeg downloads automatically on first run

---

*SplitRename v1.6.4 · by apennismightier*
