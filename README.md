________________________
WHAT IT DOES

SplitRename is a Windows desktop app that takes video files containing multiple TV episodes — e.g. Show.S01E01-E02.mkv — splits them into individual episode files, and renames them using real episode titles from TMDB and TVDB.
________________________
FILE MANAGEMENT
Drag and drop video files or folders directly into the app
Supports MKV, MP4, AVI, MOV, TS, M2TS, WMV
Multi-select files for batch processing
File list shows live status for every file:
○ queued → ◌ analyzing → ◉ ready → ◈ splitting → ✓ done / ✗ error
________________________
BLACK FRAME DETECTION

The app scans each video for the black frames that appear between episodes and uses them as cut points. Three tunable settings — each has a [?] help button:
Min Duration — how many seconds of black must appear to count as a break (default: 0.50s)
Pixel Threshold — how dark each pixel must be to count as "black" (default: 0.10)
Picture Threshold — what fraction of the frame must be dark (default: 0.98)
________________________
CUT MODES

Keyframe Snap — Fastest · Lossless
Cuts at the nearest keyframe inside the black gap. No re-encode, no quality loss. Recommended for most use.
Smart Encode — Fast · Near-lossless
Re-encodes only the first few seconds after each cut for frame accuracy, then stream-copies the rest. Best of both worlds.
Accurate Re-encode — Slow · Configurable quality
Full re-encode for frame-exact cuts using your chosen codec and quality settings.
Stream Copy — Fastest · Lossless
No re-encode at all. May start a few seconds before the actual cut point.
________________________
OUTPUT ENCODING OPTIONS

When re-encoding, you control:
Container — Same as source · MP4 · MKV
Video Codec — Same as source (copy) · H.264 · H.265 · HEVC NVENC (GPU/NVIDIA) · AV1
Audio Codec — AAC · AC3 (Dolby) · Copy
Speed Preset — Lossless → Ultra Fast → Fast → Medium → Very Slow
Quality Mode — CRF (quality-based) or fixed Bitrate (kbps)
________________________
SPLIT COUNT CONTROL
Auto-detect — splits at every detected black frame
Use first N breaks — if a file has 3 detected breaks but you only want 2 output files, set N=2 and only the first break is used
________________________
BATCH PROCESSING
Batch Analyze All — scans all files for break points with no splitting, so you can review detected timecodes before committing
Batch: Analyze + Split All — fully automated, analyze then split in one shot
Analyze / Split — step-by-step buttons for manual control
________________________
MANUAL SPLIT POINT EDITING

Click any file after analysis and the right panel shows every detected break with its timecode:
Edit any timecode — click Edit and type a new time in MM:SS or HH:MM:SS
Delete any break point you don't want
+ Add — type any timecode in the input box to insert a manual split point
________________________
EPISODE RENAMING — TMDB / TVDB

A built-in FileBot-style renaming module. No account required — API keys are pre-configured.

How it works:
Search for your TV show by name and optional year
Choose to search Both, TMDB only, or TVDB only — switch between them anytime
Load the full episode list for any season
The app maps each output file to the correct episode automatically using the episode number from the source filename
Preview every output filename before committing — e.g. Curious George - S01E11 - Hundley Goes to School.mkv
Double-click any title to edit it manually
Click Confirm to rename all files instantly
Two ways to access it:
Check "Rename output files (TMDB/TVDB)" in the Cut Mode section → the dialog opens automatically after splitting, pre-loaded with your fresh output files
Click Rename Files in the action bar at any time → pick any folder of video files to rename without splitting
