# SplitRename

**Batch TV episode break detector & splitter — Windows GUI**

---

## Files

| File | Purpose |
|------|---------|
| `episode_splitter.py` | Main GUI application |
| `ffmpeg_manager.py`   | FFmpeg auto-updater module |
| `setup.bat`           | Install Python dependencies |
| `run.bat`             | Launch the app |

## Quick Start

1. Run setup file.
2. On first launch, click **⬆ FFmpeg Manager** → **Download & Install**
3. FFmpeg is saved to `./bin/` — no PATH changes needed

---

## FFmpeg Auto-Updater

Click **⬆ FFmpeg Manager** in the header at any time to:

- See your installed FFmpeg version and where it lives
- Check GitHub (BtbN builds) for the latest release
- Download & install with one click — saved to `./bin/ffmpeg.exe`

**How it works:**
- Source: [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds) — the most widely trusted Windows FFmpeg build
- Downloads the nightly GPL build (`ffmpeg-master-latest-win64-gpl.zip`)
- Extracts `ffmpeg.exe` and `ffprobe.exe` into `./bin/`
- Stores a `.version_cache.json` to track what's installed
- Future "check for updates" compares the publish date of the cached build vs latest GitHub release
- The app always prefers `./bin/ffmpeg.exe` over any system PATH version

---

## MP4 & MKV Support

The app detects your file's container and applies format-specific FFmpeg flags:

### MP4
- **Stream copy** (no re-encoding) — fast and lossless
- `-movflags +faststart` — moves the moov atom to the front of the file, making output MP4s stream correctly in browsers and media players
- `-map 0:v -map 0:a` — copies video and audio streams
- **Subtitles:** only `mov_text` / `tx3g` subtitle tracks are kept (the only formats MP4 supports). ASS/SSA/SRT tracks are silently dropped since MP4 can't carry them natively
- `-avoid_negative_ts make_zero` — fixes PTS/DTS timestamp issues at cut points

### MKV
- **Stream copy** — fast and lossless
- `-map 0` — **all streams preserved**: video, audio, every subtitle track (ASS/SSA/SRT/PGS), chapter markers, attachments, fonts
- `-avoid_negative_ts make_zero` — prevents negative PTS glitches common in broadcast recordings

### Fallback (automatic)
If stream copy fails on any segment (e.g. corrupt index, incompatible edit point, muxer error), the app automatically retries with:
- `libx264` video re-encode (CRF 18, fast preset)
- `aac` audio at 192kbps

The log panel will show `⚠ Stream copy failed — retrying with re-encode` if this happens.

---

## Stream Info Display

After analysis, the right panel shows a stream info bar for the selected file:

```
Video: H264 1920×1080  |  Audio: AAC 2ch  |  Subs: ass  |  📦 MKV — all streams preserved
```

This helps you understand exactly what's in your file and how it'll be handled.

---

## How to Use

1. **Add files** — drag & drop `.mp4` / `.mkv` (and others) onto the list, or click **+ Add Files**
2. **Tune detection** (optional) — adjust the three sliders for your recording type
3. Click **▶ ANALYZE FILES** — FFmpeg scans for black frame segments
4. **Review split points** in the right panel — toggle, delete, or add manual timestamps
5. Choose an output folder (optional) — default is an `episodes/` subfolder next to the source
6. Click **✂ SPLIT EPISODES** — outputs `ShowName_E01.mp4`, `_E02.mp4`, etc.

---

## Detection Settings

| Setting | Default | When to change |
|---------|---------|----------------|
| Min black duration | 0.5s | Lower to 0.2s for short bumpers; raise to 2.0s for less noise |
| Pixel threshold | 0.10 | Raise to 0.15–0.20 for recordings with station watermarks |
| Picture threshold | 0.98 | Lower to 0.90–0.95 for VHS / analog recordings |

---

## File Status Icons

| Icon | Meaning |
|------|---------|
| ○ | Queued |
| ◌ | Analyzing |
| ◉ | Ready to split |
| ◈ | Splitting in progress |
| ✓ | Done |
| ✗ | Error |

---

## Building a Standalone .exe

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name SplitRename \
  --add-data "ffmpeg_manager.py;." \
  episode_splitter.py
```

The `.exe` will be in `dist/`. The `./bin/` folder (with FFmpeg) should sit next to the `.exe`.
