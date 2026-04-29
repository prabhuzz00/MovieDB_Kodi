"""
lib/tmdb_api.py
~~~~~~~~~~~~~~~
Thin wrapper around The Movie Database (TMDB) REST API v3.

All public functions return plain Python dicts / lists so that
``default.py`` stays free of HTTP details.

Image helper
------------
Use ``image_url(path, size)`` to build a full poster / backdrop URL.
Supported size values (poster):  w92  w154  w185  w342  w500  w780  original
Supported size values (backdrop): w300  w780  w1280  original

TMDB API reference: https://developers.themoviedb.org/3
"""

import json
import re
import sys

if sys.version_info[0] >= 3:
    from urllib.request import urlopen, Request
    from urllib.parse import urlencode, quote
    from urllib.error import URLError
else:
    from urllib2 import urlopen, Request, URLError
    from urllib import urlencode, quote

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TMDB_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/"
YOUTUBE_WATCH = "https://www.youtube.com/watch?v="

_DEFAULT_TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _get(endpoint, params, timeout=_DEFAULT_TIMEOUT):
    """Perform a GET request against the TMDB API.

    Args:
        endpoint (str): API path, e.g. ``"/movie/popular"``.
        params (dict):  Query-string parameters **including** ``api_key``.
        timeout (int):  Connection timeout in seconds.

    Returns:
        dict | None: Parsed JSON body, or ``None`` on any error.
    """
    url = "{base}{endpoint}?{qs}".format(
        base=TMDB_BASE,
        endpoint=endpoint,
        qs=urlencode(params),
    )
    try:
        req = Request(url, headers={"Accept": "application/json",
                                    "User-Agent": "MovieDB-Kodi/1.0"})
        response = urlopen(req, timeout=timeout)
        raw = response.read()
        return json.loads(raw.decode("utf-8"))
    except URLError:
        return None
    except ValueError:
        # JSON decode error
        return None


def _params(api_key, language="en-US", extra=None):
    """Build a base parameter dict."""
    p = {"api_key": api_key, "language": language}
    if extra:
        p.update(extra)
    return p


# ---------------------------------------------------------------------------
# Image URL helper
# ---------------------------------------------------------------------------

def image_url(path, size="w500"):
    """Return the full TMDB image URL for *path*.

    Args:
        path (str):  The ``poster_path`` / ``backdrop_path`` returned by TMDB.
        size (str):  One of the TMDB image sizes (default ``"w500"``).

    Returns:
        str: Full URL, or empty string when *path* is falsy.
    """
    if not path:
        return ""
    return "{base}{size}{path}".format(base=IMAGE_BASE, size=size, path=path)


# ---------------------------------------------------------------------------
# Movies
# ---------------------------------------------------------------------------

def get_movies(api_key, category="popular", page=1, language="en-US"):
    """Fetch a paginated list of movies.

    Args:
        category (str): One of ``popular | top_rated | now_playing | upcoming``.

    Returns:
        dict with keys ``results`` (list) and ``total_pages`` (int), or ``None``.
    """
    allowed = {"popular", "top_rated", "now_playing", "upcoming"}
    if category not in allowed:
        category = "popular"
    params = _params(api_key, language, {"page": page})
    return _get("/movie/{cat}".format(cat=category), params)


def get_movie_details(api_key, tmdb_id, language="en-US"):
    """Full movie details including external IDs (IMDB).

    Returns:
        dict or None.
    """
    params = _params(api_key, language,
                     {"append_to_response": "credits,videos,external_ids"})
    return _get("/movie/{id}".format(id=tmdb_id), params)


def get_movie_external_ids(api_key, tmdb_id):
    """Fetch only the external_ids for a movie (fast call)."""
    params = _params(api_key)
    return _get("/movie/{id}/external_ids".format(id=tmdb_id), params)


# ---------------------------------------------------------------------------
# TV Series
# ---------------------------------------------------------------------------

def get_tv(api_key, category="popular", page=1, language="en-US"):
    """Fetch a paginated list of TV series.

    Args:
        category (str): One of ``popular | top_rated | on_the_air | airing_today``.
    """
    allowed = {"popular", "top_rated", "on_the_air", "airing_today"}
    if category not in allowed:
        category = "popular"
    params = _params(api_key, language, {"page": page})
    return _get("/tv/{cat}".format(cat=category), params)


def get_tv_details(api_key, tmdb_id, language="en-US"):
    """Full TV series details including external IDs and season list."""
    params = _params(api_key, language,
                     {"append_to_response": "credits,videos,external_ids"})
    return _get("/tv/{id}".format(id=tmdb_id), params)


def get_tv_season(api_key, tmdb_id, season_number, language="en-US"):
    """Fetch episode list for a specific season."""
    params = _params(api_key, language)
    return _get("/tv/{id}/season/{s}".format(id=tmdb_id, s=season_number),
                params)


def get_tv_external_ids(api_key, tmdb_id):
    """Fetch external IDs for a TV series (includes IMDB id)."""
    params = _params(api_key)
    return _get("/tv/{id}/external_ids".format(id=tmdb_id), params)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_multi(api_key, query, page=1, language="en-US"):
    """Search for movies AND TV series in one request.

    Returns a dict with ``results`` (list) and ``total_pages``.
    Each item has a ``media_type`` key of ``"movie"`` or ``"tv"``.
    """
    params = _params(api_key, language,
                     {"query": query, "page": page,
                      "include_adult": "false"})
    return _get("/search/multi", params)


def search_movies(api_key, query, page=1, language="en-US"):
    """Search for movies only."""
    params = _params(api_key, language,
                     {"query": query, "page": page,
                      "include_adult": "false"})
    return _get("/search/movie", params)


def search_tv(api_key, query, page=1, language="en-US"):
    """Search for TV series only."""
    params = _params(api_key, language,
                     {"query": query, "page": page,
                      "include_adult": "false"})
    return _get("/search/tv", params)


# ---------------------------------------------------------------------------
# Helpers used by default.py
# ---------------------------------------------------------------------------

def extract_trailer_url(details):
    """Return the YouTube watch URL of the first available trailer.

    Args:
        details (dict): Full details response from TMDB (must contain
                        ``videos.results``).

    Returns:
        str: YouTube URL, or empty string when none found.
    """
    videos = (details or {}).get("videos", {}).get("results", [])
    for video in videos:
        if video.get("site") == "YouTube" and video.get("type") == "Trailer":
            return YOUTUBE_WATCH + video["key"]
    # fallback: any YouTube video
    for video in videos:
        if video.get("site") == "YouTube":
            return YOUTUBE_WATCH + video["key"]
    return ""


def extract_cast(details, limit=10):
    """Return up to *limit* cast members from a full details response.

    Returns:
        list of dicts with keys: name, character, profile_url.
    """
    cast = (details or {}).get("credits", {}).get("cast", [])
    result = []
    for member in cast[:limit]:
        result.append({
            "name": member.get("name", ""),
            "character": member.get("character", ""),
            "profile_url": image_url(member.get("profile_path"), size="w185"),
        })
    return result


def extract_imdb_id(details):
    """Return the IMDB id string (e.g. ``'tt0123456'``) from a details dict."""
    # Full details with append_to_response=external_ids
    ext = details.get("external_ids") if details else None
    if ext and ext.get("imdb_id"):
        return ext["imdb_id"]
    # Some endpoints embed it directly
    return (details or {}).get("imdb_id", "")


def build_vidsrc_movie_url(imdb_id):
    """Return the VidSrc embed URL for a movie."""
    return "https://vidsrc.to/embed/movie/{imdb}".format(imdb=imdb_id)


def build_vidsrc_tv_url(imdb_id, season, episode):
    """Return the VidSrc embed URL for a TV episode."""
    return (
        "https://vidsrc.to/embed/tv/{imdb}/{s}/{e}".format(
            imdb=imdb_id, s=season, e=episode)
    )


def build_vsembed_movie_url(imdb_id):
    """Return the VSEmbed URL for a movie.

    Format: https://vsembed.ru/embed/movie/<imdb_id>
    """
    return "https://vsembed.ru/embed/movie/{imdb}".format(imdb=imdb_id)


def build_vsembed_tv_url(imdb_id, season, episode):
    """Return the VSEmbed URL for a TV episode.

    Format: https://vsembed.ru/embed/tv?imdb=<imdb_id>&season=<s>&episode=<e>
    """
    return (
        "https://vsembed.ru/embed/tv?imdb={imdb}&season={s}&episode={e}".format(
            imdb=imdb_id, s=season, e=episode)
    )


# ---------------------------------------------------------------------------
# Stream URL resolver
# ---------------------------------------------------------------------------

# Ordered list of regex patterns used to find direct video stream URLs inside
# embed page HTML / inline JavaScript.  Each pattern must capture the raw URL
# in group 1.
_STREAM_PATTERNS = [
    # JW Player / Video.js  "file": "https://…/video.m3u8"
    re.compile(r'"file"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"'),
    # Generic  src="https://…/video.m3u8"  (double-quoted)
    re.compile(r'src="(https?://[^"]+\.m3u8[^"]*)"'),
    # Generic  src='https://…/video.m3u8'  (single-quoted)
    re.compile(r"src='(https?://[^']+\.m3u8[^']*)'"),
    # Generic  "url": "https://…/video.m3u8"
    re.compile(r'"url"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"'),
    # JW Player  "file": "https://…/video.mp4"
    re.compile(r'"file"\s*:\s*"(https?://[^"]+\.mp4[^"]*)"'),
    # Generic  src="https://…/video.mp4"  (double-quoted)
    re.compile(r'src="(https?://[^"]+\.mp4[^"]*)"'),
    # Generic  src='https://…/video.mp4'  (single-quoted)
    re.compile(r"src='(https?://[^']+\.mp4[^']*)'"),
    # Generic  "url": "https://…/video.mp4"
    re.compile(r'"url"\s*:\s*"(https?://[^"]+\.mp4[^"]*)"'),
]

# Browser-like headers to improve chances of getting a full HTML response
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
}


def resolve_stream_url(embed_url, timeout=_DEFAULT_TIMEOUT):
    """Attempt to extract a direct video stream URL from an embed page.

    Many video services serve an HTML embed page whose JavaScript dynamically
    loads the actual video.  This function fetches the embed page and searches
    its HTML/JavaScript source for direct stream URLs (HLS .m3u8 or .mp4).

    Args:
        embed_url (str): The embed page URL (e.g. from ``build_vsembed_*``).
        timeout (int):   Connection timeout in seconds.

    Returns:
        tuple(str | None, str):
            ``(stream_url, mime_type)`` where *stream_url* is the direct
            stream URL and *mime_type* is a suitable MIME-type string
            (``"application/x-mpegURL"`` for HLS, ``"video/mp4"`` for MP4).
            Returns ``(None, "")`` when no direct stream URL is found.
    """
    try:
        req = Request(embed_url, headers=_BROWSER_HEADERS)
        response = urlopen(req, timeout=timeout)
        html = response.read().decode("utf-8", errors="replace")

        for pattern in _STREAM_PATTERNS:
            match = pattern.search(html)
            if match:
                url = match.group(1)
                if ".m3u8" in url:
                    return url, "application/x-mpegURL"
                return url, "video/mp4"

    except (URLError, OSError):
        pass

    return None, ""


def resolve_movie_stream(imdb_id, timeout=_DEFAULT_TIMEOUT):
    """Try multiple embed sources and return the first working movie stream URL.

    Sources tried in order: vsembed → vidsrc.

    Args:
        imdb_id (str): The IMDB ID (e.g. ``'tt0123456'``).
        timeout (int): Connection timeout in seconds.

    Returns:
        tuple(str | None, str): ``(stream_url, mime_type)`` where *stream_url*
        is the resolved direct URL, or ``(None, "")`` when no stream could be
        found across all sources.
    """
    sources = [
        build_vsembed_movie_url(imdb_id),
        build_vidsrc_movie_url(imdb_id),
    ]
    for embed_url in sources:
        stream_url, mime_type = resolve_stream_url(embed_url, timeout=timeout)
        if stream_url:
            return stream_url, mime_type
    return None, ""


def resolve_tv_stream(imdb_id, season, episode, timeout=_DEFAULT_TIMEOUT):
    """Try multiple embed sources and return the first working TV episode stream URL.

    Sources tried in order: vsembed → vidsrc.

    Args:
        imdb_id (str): The IMDB ID of the series.
        season (int | str): Season number.
        episode (int | str): Episode number.
        timeout (int): Connection timeout in seconds.

    Returns:
        tuple(str | None, str): ``(stream_url, mime_type)`` where *stream_url*
        is the resolved direct URL, or ``(None, "")`` when no stream could be
        found across all sources.
    """
    sources = [
        build_vsembed_tv_url(imdb_id, season, episode),
        build_vidsrc_tv_url(imdb_id, season, episode),
    ]
    for embed_url in sources:
        stream_url, mime_type = resolve_stream_url(embed_url, timeout=timeout)
        if stream_url:
            return stream_url, mime_type
    return None, ""
