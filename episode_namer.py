"""
episode_namer.py — TVDB + TMDB episode lookup for EpisodeSplit
Fetches episode titles and builds output filenames, much like FileBot.

APIs used:
  TMDB: https://www.themoviedb.org/documentation/api  (free, no auth for search)
  TVDB: https://thetvdb.com/api-information            (free tier, requires key)

We use TMDB as primary (no API key required for basic search) and TVDB as
optional secondary if the user provides a key.
"""

from __future__ import annotations
import json
import re
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

# ── TMDB (The Movie Database) ─────────────────────────────────────────────────
# Public endpoints don't require auth; detailed episode data needs a free API key.
# Sign up free at https://www.themoviedb.org/settings/api
TMDB_BASE    = "https://api.themoviedb.org/3"
TMDB_API_KEY = "181eaf5e7326b9d157a652d0e591087e"

# ── TVDB ──────────────────────────────────────────────────────────────────────
TVDB_BASE    = "https://api4.thetvdb.com/v4"
TVDB_API_KEY = "3bc3f1c3-058b-4b42-9949-466b4f7aba20"


# ─────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────

@dataclass
class ShowResult:
    id:          int
    name:        str
    year:        str
    overview:    str
    source:      str          # "tmdb" | "tvdb"
    poster_url:  str = ""


@dataclass
class EpisodeInfo:
    season:     int
    episode:    int
    title:      str
    overview:   str = ""
    air_date:   str = ""


@dataclass
class NamingPlan:
    """
    Maps one VideoJob → a list of output filenames (one per split segment).
    """
    job_filename:   str
    show_name:      str
    season:         int
    episodes:       list[EpisodeInfo] = field(default_factory=list)
    output_names:   list[str]         = field(default_factory=list)
    confirmed:      bool              = False


# ─────────────────────────────────────────────
# HTTP HELPER
# ─────────────────────────────────────────────

def _get(url: str, headers: dict | None = None, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers=headers or {
        "User-Agent": "EpisodeSplit/1.4 (github.com/apennismightier)"
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ─────────────────────────────────────────────
# TMDB CLIENT
# ─────────────────────────────────────────────

class TMDBClient:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def _url(self, path: str, **params) -> str:
        if self.api_key:
            params["api_key"] = self.api_key
        qs = urllib.parse.urlencode(params)
        return f"{TMDB_BASE}{path}?{qs}"

    def search_show(self, query: str, year: str = "") -> list[ShowResult]:
        params = {"query": query, "include_adult": "false"}
        if year:
            params["first_air_date_year"] = year
        try:
            data = _get(self._url("/search/tv", **params))
        except Exception as e:
            raise RuntimeError(f"TMDB search failed: {e}")

        results = []
        for r in data.get("results", [])[:8]:
            yr = (r.get("first_air_date") or "")[:4]
            results.append(ShowResult(
                id=r["id"], name=r.get("name", ""), year=yr,
                overview=(r.get("overview") or "")[:120],
                source="tmdb",
                poster_url=(f"https://image.tmdb.org/t/p/w92{r['poster_path']}"
                            if r.get("poster_path") else ""),
            ))
        return results

    def get_episodes(self, show_id: int, season: int) -> list[EpisodeInfo]:
        if not self.api_key:
            raise RuntimeError(
                "A TMDB API key is required to fetch episode details.\n"
                "Get a free key at themoviedb.org/settings/api"
            )
        try:
            data = _get(self._url(f"/tv/{show_id}/season/{season}"))
        except Exception as e:
            raise RuntimeError(f"TMDB episode fetch failed: {e}")

        episodes = []
        for ep in data.get("episodes", []):
            episodes.append(EpisodeInfo(
                season=ep.get("season_number", season),
                episode=ep.get("episode_number", 0),
                title=ep.get("name", f"Episode {ep.get('episode_number', '?')}"),
                overview=(ep.get("overview") or "")[:200],
                air_date=ep.get("air_date") or "",
            ))
        return episodes

    def get_all_episodes(self, show_id: int) -> dict[int, list[EpisodeInfo]]:
        """Fetch every season's episodes."""
        try:
            show_data = _get(self._url(f"/tv/{show_id}"))
        except Exception as e:
            raise RuntimeError(f"TMDB show details failed: {e}")

        seasons_info = [s for s in show_data.get("seasons", [])
                        if s.get("season_number", 0) > 0]
        all_eps: dict[int, list[EpisodeInfo]] = {}
        for s in seasons_info:
            sn = s["season_number"]
            try:
                all_eps[sn] = self.get_episodes(show_id, sn)
            except Exception:
                pass
        return all_eps


# ─────────────────────────────────────────────
# TVDB CLIENT
# ─────────────────────────────────────────────

class TVDBClient:
    def __init__(self, api_key: str = ""):
        self.api_key  = api_key
        self._token: Optional[str] = None

    def _auth(self):
        if self._token:
            return
        if not self.api_key:
            raise RuntimeError("TVDB API key required. Get one free at thetvdb.com")
        try:
            req_data = json.dumps({"apikey": self.api_key}).encode()
            req = urllib.request.Request(
                f"{TVDB_BASE}/login",
                data=req_data,
                headers={"Content-Type": "application/json",
                         "User-Agent": "EpisodeSplit/1.4"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
            self._token = data["data"]["token"]
        except Exception as e:
            raise RuntimeError(f"TVDB auth failed: {e}")

    def _headers(self) -> dict:
        self._auth()
        return {"Authorization": f"Bearer {self._token}",
                "User-Agent": "EpisodeSplit/1.4"}

    def search_show(self, query: str, year: str = "") -> list[ShowResult]:
        try:
            params = urllib.parse.urlencode({"query": query, "type": "series"})
            data = _get(f"{TVDB_BASE}/search?{params}", headers=self._headers())
        except Exception as e:
            raise RuntimeError(f"TVDB search failed: {e}")

        results = []
        for r in (data.get("data") or [])[:8]:
            yr = (r.get("year") or "")
            results.append(ShowResult(
                id=int(r.get("tvdb_id", 0) or 0),
                name=r.get("name") or r.get("translations", {}).get("eng", ""),
                year=str(yr),
                overview=(r.get("overview") or r.get("overviews", {}).get("eng", ""))[:120],
                source="tvdb",
                poster_url=r.get("image_url") or "",
            ))
        return [r for r in results if r.id]

    def get_episodes(self, show_id: int, season: int) -> list[EpisodeInfo]:
        try:
            data = _get(
                f"{TVDB_BASE}/series/{show_id}/episodes/official?season={season}",
                headers=self._headers()
            )
        except Exception as e:
            raise RuntimeError(f"TVDB episode fetch failed: {e}")

        episodes = []
        for ep in (data.get("data", {}).get("episodes") or []):
            if ep.get("seasonNumber") != season:
                continue
            episodes.append(EpisodeInfo(
                season=ep.get("seasonNumber", season),
                episode=ep.get("number", 0),
                title=ep.get("name") or f"Episode {ep.get('number', '?')}",
                overview=(ep.get("overview") or "")[:200],
                air_date=ep.get("aired") or "",
            ))
        return sorted(episodes, key=lambda e: e.episode)


# ─────────────────────────────────────────────
# FILENAME BUILDER
# ─────────────────────────────────────────────

_SAFE_CHARS = re.compile(r'[\\/:*?"<>|]')

def safe_filename(name: str) -> str:
    """Strip characters Windows won't allow in filenames."""
    return _SAFE_CHARS.sub("", name).strip(" .")


def build_output_names(
    show_name:   str,
    season:      int,
    episodes:    list[EpisodeInfo],
    ext:         str,
    include_show: bool = True,
) -> list[str]:
    """
    Build one output filename per episode segment.

    e.g.  Curious George - S01E01 - Hundley's Great Escape.mkv
    """
    names = []
    for ep in episodes:
        tag   = f"S{ep.season:02d}E{ep.episode:02d}"
        title = safe_filename(ep.title)
        if include_show:
            name = f"{safe_filename(show_name)} - {tag} - {title}{ext}"
        else:
            name = f"{tag} - {title}{ext}"
        names.append(name)
    return names


def guess_season_episode(filename: str) -> tuple[int, int]:
    """
    Try to extract season + first episode number from a filename.
    Returns (season, episode) or (1, 1) as fallback.
    """
    stem = re.sub(r'\.[^.]+$', '', filename)   # remove extension
    m = re.search(r'(?i)[Ss](\d+)[Ee](\d+)', stem)
    if m:
        return int(m.group(1)), int(m.group(2))
    m2 = re.search(r'(\d+)[xX](\d+)', stem)
    if m2:
        return int(m2.group(1)), int(m2.group(2))
    return 1, 1
