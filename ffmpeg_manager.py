"""
ffmpeg_manager.py  -  EpisodeSplit FFmpeg Manager
Handles: discovery, version checking, and auto-updating FFmpeg from BtbN GitHub releases.

Strategy:
  1. Look for ffmpeg in <app_dir>/bin/  (app-local, managed by this module)
  2. Fall back to system PATH
  3. Download latest Windows GPL build from GitHub if requested

Works correctly both when run as a Python script and when bundled by PyInstaller.
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess
import urllib.request
import urllib.error
import sys as _sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

GITHUB_API_URL = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
ASSET_PATTERN  = "ffmpeg-master-latest-win64-gpl.zip"
BINARIES       = ["ffmpeg.exe", "ffprobe.exe"]


def _get_app_dir() -> Path:
    """
    Return the directory that contains the running application.

    - When run as a PyInstaller .exe:  sys.executable parent
    - When run as a Python script:     the script's parent directory
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


def _get_local_bin_dir() -> Path:
    """
    Return a user-writable directory for the managed FFmpeg binaries.

    C:\Program Files (x86) is write-protected — even the app itself cannot
    write there without elevation. We therefore always store the downloaded
    FFmpeg under %LOCALAPPDATA%\EpisodeSplit\bin\ which is always writable
    by the current user with no admin rights required.

    Falls back to <app_dir>/bin/ when running as a plain Python script (dev).
    """
    if getattr(sys, "frozen", False):
        # Installed .exe — use per-user AppData so no admin is needed
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            return Path(local_app_data) / "EpisodeSplit" / "bin"
        # Fallback if LOCALAPPDATA not set (shouldn't happen on Windows)
        return _get_app_dir() / "bin"
    else:
        # Dev / script mode — store next to the script
        return _get_app_dir() / "bin"


def _get_version_cache() -> Path:
    return _get_local_bin_dir() / ".version_cache.json"


# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class FFmpegInfo:
    path:       str    # full path to ffmpeg.exe
    probe_path: str    # full path to ffprobe.exe
    version:    str    # e.g. "7.1"
    build_date: str    # e.g. "2025-04-01"
    is_local:   bool   # True = managed in ./bin/
    source:     str    # "local" | "system"


@dataclass
class ReleaseInfo:
    tag:          str
    published_at: str
    download_url: str
    asset_name:   str
    size_bytes:   int


# ─────────────────────────────────────────────
# MANAGER
# ─────────────────────────────────────────────

class FFmpegManager:
    """
    Locate, inspect, and update FFmpeg.
    All blocking network/disk ops run in a background thread via DownloadWorker.
    """

    def __init__(self, progress_callback: Optional[Callable[[str, int], None]] = None):
        self._cb   = progress_callback or (lambda msg, pct: None)
        self._info: Optional[FFmpegInfo] = None

    # ── PUBLIC API ──────────────────────────────────────────────────────────

    def locate(self) -> Optional[FFmpegInfo]:
        """Find best available FFmpeg — local bin/ first, then system PATH."""
        local = self._check_local()
        if local:
            self._info = local
            return local
        system = self._check_system()
        if system:
            self._info = system
            return system
        return None

    def get_info(self) -> Optional[FFmpegInfo]:
        return self._info

    def ffmpeg_path(self) -> str:
        return self._info.path if self._info else "ffmpeg"

    def ffprobe_path(self) -> str:
        return self._info.probe_path if self._info else "ffprobe"

    def fetch_latest_release(self) -> ReleaseInfo:
        """
        Query GitHub API for the latest BtbN FFmpeg build.
        Raises RuntimeError on any failure so the caller can show the error.
        """
        self._cb("Checking GitHub for latest FFmpeg release...", 5)
        try:
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={
                    "User-Agent": "EpisodeSplit/1.0",
                    "Accept":     "application/vnd.github+json",
                }
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Could not reach GitHub. Check your internet connection.\n\nDetail: {e}"
            )
        except Exception as e:
            raise RuntimeError(f"GitHub request failed: {e}")

        tag       = data.get("tag_name", "unknown")
        published = data.get("published_at", "")[:10]
        assets    = data.get("assets", [])

        for asset in assets:
            if asset["name"] == ASSET_PATTERN:
                return ReleaseInfo(
                    tag=tag,
                    published_at=published,
                    download_url=asset["browser_download_url"],
                    asset_name=asset["name"],
                    size_bytes=asset["size"],
                )

        # List available assets to help diagnose if pattern changed
        names = [a["name"] for a in assets[:10]]
        raise RuntimeError(
            f"Asset '{ASSET_PATTERN}' not found in release '{tag}'.\n"
            f"Available assets: {names}"
        )

    def is_update_available(self, release: ReleaseInfo) -> bool:
        cache_path = _get_version_cache()
        if not cache_path.exists():
            return True
        try:
            cache = json.loads(cache_path.read_text())
            return release.published_at > cache.get("published_at", "")
        except Exception:
            return True

    def download_and_install(self, release: ReleaseInfo) -> FFmpegInfo:
        """Download, extract, and install FFmpeg into <app_dir>/bin/. Runs in a thread."""
        local_bin = _get_local_bin_dir()
        local_bin.mkdir(parents=True, exist_ok=True)

        zip_size_mb = release.size_bytes / (1024 * 1024)
        self._cb(f"Downloading FFmpeg ({zip_size_mb:.0f} MB)...", 5)

        tmp_zip = Path(tempfile.mktemp(suffix=".zip"))
        try:
            self._download_with_progress(release.download_url, tmp_zip)

            self._cb("Extracting archive...", 75)
            tmp_dir = Path(tempfile.mkdtemp())
            try:
                with zipfile.ZipFile(tmp_zip, "r") as zf:
                    zf.extractall(tmp_dir)

                bin_dir = self._find_bin_dir(tmp_dir)
                if not bin_dir:
                    raise RuntimeError(
                        "Could not find bin/ directory inside the downloaded archive. "
                        "The archive structure may have changed."
                    )

                self._cb("Installing binaries...", 88)
                for binary in BINARIES:
                    src = bin_dir / binary
                    if not src.exists():
                        raise RuntimeError(
                            f"Expected binary not found in archive: {binary}\n"
                            f"bin_dir contents: {list(bin_dir.iterdir())}"
                        )
                    dst = local_bin / binary
                    if dst.exists():
                        dst.unlink()
                    shutil.copy2(src, dst)

            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        finally:
            if tmp_zip.exists():
                tmp_zip.unlink(missing_ok=True)

        # Write version cache
        self._cb("Finalizing...", 95)
        cache = {
            "tag":          release.tag,
            "published_at": release.published_at,
            "asset_name":   release.asset_name,
        }
        _get_version_cache().write_text(json.dumps(cache, indent=2))

        # Verify the install works
        self._cb("Verifying installation...", 98)
        info = self._check_local()
        if not info:
            raise RuntimeError(
                "FFmpeg was installed but could not be verified. "
                f"Check that files exist in: {local_bin}"
            )
        self._info = info
        self._cb("FFmpeg installed successfully!", 100)
        return info

    def get_cached_release_info(self) -> Optional[dict]:
        cache_path = _get_version_cache()
        if cache_path.exists():
            try:
                return json.loads(cache_path.read_text())
            except Exception:
                pass
        return None

    # ── PRIVATE ─────────────────────────────────────────────────────────────

    def _check_local(self) -> Optional[FFmpegInfo]:
        local_bin = _get_local_bin_dir()
        ffmpeg    = local_bin / "ffmpeg.exe"
        ffprobe   = local_bin / "ffprobe.exe"
        if ffmpeg.exists() and ffprobe.exists():
            return self._probe_binary(str(ffmpeg), str(ffprobe), is_local=True)
        return None

    def _check_system(self) -> Optional[FFmpegInfo]:
        ffmpeg  = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if ffmpeg and ffprobe:
            return self._probe_binary(ffmpeg, ffprobe, is_local=False)
        return None

    def _probe_binary(self, ffmpeg: str, ffprobe: str, is_local: bool) -> Optional[FFmpegInfo]:
        try:
            r = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, timeout=10)
            if r.returncode != 0:
                return None
            version, build_date = self._parse_version(r.stdout or r.stderr)
            return FFmpegInfo(
                path=ffmpeg, probe_path=ffprobe,
                version=version, build_date=build_date,
                is_local=is_local,
                source="local" if is_local else "system",
            )
        except Exception:
            return None

    def _parse_version(self, text: str):
        import re
        version    = "unknown"
        build_date = ""
        m = re.search(r"ffmpeg version ([^\s]+)", text)
        if m:
            version = m.group(1)
        m2 = re.search(r"built on (\w+ +\d+ \d+)", text)
        if m2:
            try:
                from datetime import datetime
                build_date = datetime.strptime(m2.group(1).strip(), "%b %d %Y").strftime("%Y-%m-%d")
            except Exception:
                build_date = m2.group(1).strip()
        return version, build_date

    def _find_bin_dir(self, root: Path) -> Optional[Path]:
        if (root / "bin").is_dir() and (root / "bin" / "ffmpeg.exe").exists():
            return root / "bin"
        for child in root.iterdir():
            if child.is_dir():
                candidate = child / "bin"
                if candidate.is_dir() and (candidate / "ffmpeg.exe").exists():
                    return candidate
        return None

    def _download_with_progress(self, url: str, dest: Path):
        req = urllib.request.Request(url, headers={"User-Agent": "EpisodeSplit/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            total      = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 256  # 256 KB

            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct     = 5 + int((downloaded / total) * 65)   # 5% -> 70%
                        mb_done = downloaded / (1024 * 1024)
                        mb_tot  = total / (1024 * 1024)
                        self._cb(f"Downloading... {mb_done:.1f} / {mb_tot:.1f} MB", pct)
