"""
default.py — MovieDB Kodi Addon
================================
Main plugin entry-point for ``plugin.video.moviedb``.

Routing is done entirely through URL query-string parameters:

    ?action=<action_name>[&key=value …]

Actions
-------
(none / main)   — top-level menu
movies          — Movies sub-menu
tv              — TV Series sub-menu
search          — Search prompt + results
list_movies     — Paginated movie list  (?category=…&page=…)
list_tv         — Paginated TV list     (?category=…&page=…)
movie_details   — Movie detail & play   (?tmdb_id=…)
tv_seasons      — Season chooser        (?tmdb_id=…)
tv_episodes     — Episode list          (?tmdb_id=…&season=…)
play_movie      — Resolve & play movie  (?imdb_id=…&title=…)
play_tv         — Resolve & play ep     (?imdb_id=…&title=…&season=…&episode=…)
play_trailer    — Play YouTube trailer  (?url=…)
"""

import os
import sys

# ---------------------------------------------------------------------------
# Bootstrap: make sure our lib/ directory is on the path
# ---------------------------------------------------------------------------
ADDON_PATH = os.path.dirname(os.path.abspath(__file__))
LIB_PATH = os.path.join(ADDON_PATH, "lib")
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

import xbmc          # noqa: E402
import xbmcgui       # noqa: E402
import xbmcplugin    # noqa: E402
import xbmcaddon     # noqa: E402

if sys.version_info[0] >= 3:
    from urllib.parse import parse_qs, urlencode, urlparse, quote_plus
else:
    from urlparse import parse_qs, urlparse
    from urllib import urlencode, quote_plus

import tmdb_api  # noqa: E402  (from lib/)

# ---------------------------------------------------------------------------
# Plugin constants
# ---------------------------------------------------------------------------

# Built-in TMDB API key — users can override this in the addon settings.
DEFAULT_TMDB_API_KEY = "e1acdbad0316a49bd53412b31fcd0701"

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_NAME = ADDON.getAddonInfo("name")
PLUGIN_URL = sys.argv[0]              # e.g. plugin://plugin.video.moviedb
PLUGIN_HANDLE = int(sys.argv[1])      # numeric handle passed by Kodi
PLUGIN_ARGS_STR = sys.argv[2]         # e.g. ?action=movies

# String IDs (see resources/language/English/strings.xml)
S = {
    "movies":          30100,
    "tv":              30101,
    "search":          30102,
    "popular_movies":  30110,
    "toprated_movies": 30111,
    "nowplaying":      30112,
    "upcoming":        30113,
    "popular_tv":      30120,
    "toprated_tv":     30121,
    "ontheair":        30122,
    "airingtoday":     30123,
    "play_movie":      30200,
    "trailer":         30201,
    "cast":            30202,
    "season":          30203,
    "episode":         30204,
    "next_page":       30205,
    "search_label":    30206,
    "search_hint":     30207,
    "api_key_title":   30300,
    "api_key_msg":     30301,
    "no_results":      30302,
    "network_error":   30303,
    "no_imdb":         30304,
    "no_trailer":      30305,
}


def _s(key):
    """Return localised string for *key* (falls back to *key* itself)."""
    sid = S.get(key)
    if sid is None:
        return key
    try:
        return ADDON.getLocalizedString(sid)
    except Exception:
        return key


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------

def _build_url(**kwargs):
    """Build a plugin:// URL with the supplied query-string parameters."""
    return "{base}?{qs}".format(base=PLUGIN_URL, qs=urlencode(kwargs))


def _parse_args():
    """Return a flat dict of query-string parameters from sys.argv[2]."""
    qs = PLUGIN_ARGS_STR.lstrip("?")
    parsed = parse_qs(qs)
    return {k: v[0] for k, v in parsed.items()}


# ---------------------------------------------------------------------------
# API key guard
# ---------------------------------------------------------------------------

def _get_api_key():
    """Return the TMDB API key from settings, falling back to the built-in default."""
    key = ADDON.getSetting("tmdb_api_key").strip()
    return key if key else DEFAULT_TMDB_API_KEY


def _language():
    return ADDON.getSetting("tmdb_lang").strip() or "en-US"


# ---------------------------------------------------------------------------
# List-item helpers
# ---------------------------------------------------------------------------

def _set_video_info(li, info_dict, media_type="movie"):
    """Populate a ListItem's video info-tag."""
    tag = li.getVideoInfoTag() if hasattr(li, "getVideoInfoTag") else None
    if tag:
        # Kodi 20+ (Nexus) info-tag API
        if media_type == "movie":
            tag.setTitle(info_dict.get("title", ""))
            tag.setPlot(info_dict.get("overview", ""))
            tag.setYear(int(str(info_dict.get("release_date", "0000"))[:4] or 0))
            tag.setRating(float(info_dict.get("vote_average", 0)))
            tag.setVotes(info_dict.get("vote_count", 0))
            tag.setGenres([g["name"] for g in info_dict.get("genres", [])])
            tag.setMediaType("movie")
        else:
            tag.setTitle(info_dict.get("name", ""))
            tag.setPlot(info_dict.get("overview", ""))
            tag.setYear(int(str(info_dict.get("first_air_date", "0000"))[:4] or 0))
            tag.setRating(float(info_dict.get("vote_average", 0)))
            tag.setVotes(info_dict.get("vote_count", 0))
            tag.setGenres([g["name"] for g in info_dict.get("genres", [])])
            tag.setMediaType("tvshow")
    else:
        # Older Kodi setInfo API
        if media_type == "movie":
            li.setInfo("video", {
                "title": info_dict.get("title", ""),
                "plot": info_dict.get("overview", ""),
                "year": int(str(info_dict.get("release_date", "0000"))[:4] or 0),
                "rating": float(info_dict.get("vote_average", 0)),
                "votes": str(info_dict.get("vote_count", "")),
                "genre": ", ".join(g["name"] for g in info_dict.get("genres", [])),
                "mediatype": "movie",
            })
        else:
            li.setInfo("video", {
                "title": info_dict.get("name", ""),
                "tvshowtitle": info_dict.get("name", ""),
                "plot": info_dict.get("overview", ""),
                "year": int(str(info_dict.get("first_air_date", "0000"))[:4] or 0),
                "rating": float(info_dict.get("vote_average", 0)),
                "votes": str(info_dict.get("vote_count", "")),
                "genre": ", ".join(g["name"] for g in info_dict.get("genres", [])),
                "mediatype": "tvshow",
            })


def _make_list_item(title, thumbnail="", fanart="", is_folder=True):
    """Create and return a basic xbmcgui.ListItem."""
    li = xbmcgui.ListItem(label=title)
    art = {"thumb": thumbnail, "poster": thumbnail, "fanart": fanart}
    li.setArt(art)
    li.setProperty("IsPlayable", "false" if is_folder else "true")
    return li


# ---------------------------------------------------------------------------
# Directory-listing wrappers
# ---------------------------------------------------------------------------

def _add_item(url, li, is_folder=True):
    xbmcplugin.addDirectoryItem(PLUGIN_HANDLE, url, li, is_folder)


def _end_list(sort_method=xbmcplugin.SORT_METHOD_NONE):
    xbmcplugin.addSortMethod(PLUGIN_HANDLE, sort_method)
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE)


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

def action_main():
    """Top-level menu: Movies | TV Series | Search."""
    items = [
        (_s("movies"),  _build_url(action="movies"),
         "DefaultMovies.png"),
        (_s("tv"),      _build_url(action="tv"),
         "DefaultTVShows.png"),
        (_s("search"),  _build_url(action="search"),
         "DefaultAddonsSearch.png"),
    ]
    for label, url, icon in items:
        li = _make_list_item(label, thumbnail=icon)
        _add_item(url, li, is_folder=True)
    _end_list()


def action_movies():
    """Movies sub-menu."""
    categories = [
        ("popular",    _s("popular_movies")),
        ("top_rated",  _s("toprated_movies")),
        ("now_playing", _s("nowplaying")),
        ("upcoming",   _s("upcoming")),
    ]
    for cat, label in categories:
        url = _build_url(action="list_movies", category=cat, page=1)
        li = _make_list_item(label)
        _add_item(url, li, is_folder=True)
    _end_list()


def action_tv():
    """TV Series sub-menu."""
    categories = [
        ("popular",      _s("popular_tv")),
        ("top_rated",    _s("toprated_tv")),
        ("on_the_air",   _s("ontheair")),
        ("airing_today", _s("airingtoday")),
    ]
    for cat, label in categories:
        url = _build_url(action="list_tv", category=cat, page=1)
        li = _make_list_item(label)
        _add_item(url, li, is_folder=True)
    _end_list()


def action_list_movies(params):
    """Paginated list of movies for a given category."""
    api_key = _get_api_key()
    if not api_key:
        return

    category = params.get("category", "popular")
    page = int(params.get("page", 1))
    lang = _language()

    data = tmdb_api.get_movies(api_key, category=category, page=page,
                               language=lang)
    if not data:
        xbmcgui.Dialog().notification(ADDON_NAME, _s("network_error"),
                                      xbmcgui.NOTIFICATION_ERROR)
        _end_list()
        return

    for movie in data.get("results", []):
        tmdb_id = movie.get("id")
        title = movie.get("title", "")
        poster = tmdb_api.image_url(movie.get("poster_path"), size="w342")
        fanart = tmdb_api.image_url(movie.get("backdrop_path"), size="w1280")
        year = str(movie.get("release_date", ""))[:4]
        rating = movie.get("vote_average", 0)
        overview = movie.get("overview", "")
        label = "{t} ({y})".format(t=title, y=year) if year else title

        li = _make_list_item(label, thumbnail=poster, fanart=fanart,
                             is_folder=True)
        li.setInfo("video", {
            "title": title,
            "year": int(year) if year else 0,
            "rating": float(rating),
            "plot": overview,
            "mediatype": "movie",
        })
        url = _build_url(action="movie_details", tmdb_id=tmdb_id)
        _add_item(url, li, is_folder=True)

    # Next page
    total_pages = data.get("total_pages", 1)
    if page < total_pages:
        next_li = _make_list_item(
            "[B]{np} ({cur}/{tot})[/B]".format(
                np=_s("next_page"), cur=page + 1, tot=total_pages)
        )
        next_url = _build_url(action="list_movies", category=category,
                              page=page + 1)
        _add_item(next_url, next_li, is_folder=True)

    _end_list()


def action_list_tv(params):
    """Paginated list of TV series."""
    api_key = _get_api_key()
    if not api_key:
        return

    category = params.get("category", "popular")
    page = int(params.get("page", 1))
    lang = _language()

    data = tmdb_api.get_tv(api_key, category=category, page=page,
                           language=lang)
    if not data:
        xbmcgui.Dialog().notification(ADDON_NAME, _s("network_error"),
                                      xbmcgui.NOTIFICATION_ERROR)
        _end_list()
        return

    for show in data.get("results", []):
        tmdb_id = show.get("id")
        title = show.get("name", "")
        poster = tmdb_api.image_url(show.get("poster_path"), size="w342")
        fanart = tmdb_api.image_url(show.get("backdrop_path"), size="w1280")
        year = str(show.get("first_air_date", ""))[:4]
        rating = show.get("vote_average", 0)
        overview = show.get("overview", "")
        label = "{t} ({y})".format(t=title, y=year) if year else title

        li = _make_list_item(label, thumbnail=poster, fanart=fanart,
                             is_folder=True)
        li.setInfo("video", {
            "title": title,
            "tvshowtitle": title,
            "year": int(year) if year else 0,
            "rating": float(rating),
            "plot": overview,
            "mediatype": "tvshow",
        })
        url = _build_url(action="tv_seasons", tmdb_id=tmdb_id)
        _add_item(url, li, is_folder=True)

    # Next page
    total_pages = data.get("total_pages", 1)
    if page < total_pages:
        next_li = _make_list_item(
            "[B]{np} ({cur}/{tot})[/B]".format(
                np=_s("next_page"), cur=page + 1, tot=total_pages)
        )
        next_url = _build_url(action="list_tv", category=category,
                              page=page + 1)
        _add_item(next_url, next_li, is_folder=True)

    _end_list()


def action_movie_details(params):
    """Show movie details and provide Play / Trailer options."""
    api_key = _get_api_key()
    if not api_key:
        return

    tmdb_id = params.get("tmdb_id")
    lang = _language()

    details = tmdb_api.get_movie_details(api_key, tmdb_id, language=lang)
    if not details:
        xbmcgui.Dialog().notification(ADDON_NAME, _s("network_error"),
                                      xbmcgui.NOTIFICATION_ERROR)
        _end_list()
        return

    title = details.get("title", "")
    poster = tmdb_api.image_url(details.get("poster_path"), size="w342")
    fanart = tmdb_api.image_url(details.get("backdrop_path"), size="w1280")
    year = str(details.get("release_date", ""))[:4]
    overview = details.get("overview", "")
    rating = details.get("vote_average", 0)
    genres = [g["name"] for g in details.get("genres", [])]
    imdb_id = tmdb_api.extract_imdb_id(details)
    trailer_url = tmdb_api.extract_trailer_url(details)
    cast = tmdb_api.extract_cast(details, limit=10)

    # --- Play Movie ---
    if imdb_id:
        play_li = _make_list_item(
            "[B][COLOR lime]{p}[/COLOR][/B]".format(p=_s("play_movie")),
            thumbnail=poster, fanart=fanart, is_folder=False,
        )
        play_li.setInfo("video", {
            "title": title,
            "plot": overview,
            "year": int(year) if year else 0,
            "rating": float(rating),
            "genre": ", ".join(genres),
            "mediatype": "movie",
        })
        play_li.setProperty("IsPlayable", "true")
        play_url = _build_url(action="play_movie", imdb_id=imdb_id,
                              title=title)
        _add_item(play_url, play_li, is_folder=False)

    # --- Watch Trailer ---
    if trailer_url:
        tr_li = _make_list_item(
            "[COLOR yellow]{t}[/COLOR]".format(t=_s("trailer")),
            thumbnail=poster, fanart=fanart, is_folder=False,
        )
        tr_li.setProperty("IsPlayable", "true")
        tr_url = _build_url(action="play_trailer", url=trailer_url,
                            title=title + " — Trailer")
        _add_item(tr_url, tr_li, is_folder=False)

    # --- Cast info (non-playable entries) ---
    if cast:
        for member in cast:
            cast_label = "{n}  [I]as  {c}[/I]".format(
                n=member["name"], c=member["character"])
            c_li = _make_list_item(cast_label,
                                   thumbnail=member["profile_url"],
                                   fanart=fanart,
                                   is_folder=False)
            c_li.setProperty("IsPlayable", "false")
            # Cast items open nothing — just informational
            _add_item(_build_url(action="noop"), c_li, is_folder=False)

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, title)
    xbmcplugin.setContent(PLUGIN_HANDLE, "movies")
    _end_list()


def action_tv_seasons(params):
    """List seasons for a TV series."""
    api_key = _get_api_key()
    if not api_key:
        return

    tmdb_id = params.get("tmdb_id")
    lang = _language()

    details = tmdb_api.get_tv_details(api_key, tmdb_id, language=lang)
    if not details:
        xbmcgui.Dialog().notification(ADDON_NAME, _s("network_error"),
                                      xbmcgui.NOTIFICATION_ERROR)
        _end_list()
        return

    title = details.get("name", "")
    fanart = tmdb_api.image_url(details.get("backdrop_path"), size="w1280")
    imdb_id = tmdb_api.extract_imdb_id(details)
    trailer_url = tmdb_api.extract_trailer_url(details)

    # --- Trailer entry at the top ---
    if trailer_url:
        poster = tmdb_api.image_url(details.get("poster_path"), size="w342")
        tr_li = _make_list_item(
            "[COLOR yellow]{t}[/COLOR]".format(t=_s("trailer")),
            thumbnail=poster, fanart=fanart, is_folder=False,
        )
        tr_li.setProperty("IsPlayable", "true")
        tr_url = _build_url(action="play_trailer", url=trailer_url,
                            title=title + " — Trailer")
        _add_item(tr_url, tr_li, is_folder=False)

    # --- Seasons ---
    for season in details.get("seasons", []):
        s_number = season.get("season_number", 0)
        s_name = season.get("name", "{s} {n}".format(s=_s("season"), n=s_number))
        s_poster = tmdb_api.image_url(season.get("poster_path"), size="w342")
        ep_count = season.get("episode_count", 0)
        label = "{n}  ({ep} episodes)".format(n=s_name, ep=ep_count)

        s_li = _make_list_item(label, thumbnail=s_poster, fanart=fanart,
                               is_folder=True)
        s_li.setInfo("video", {
            "title": s_name,
            "tvshowtitle": title,
            "mediatype": "season",
            "season": s_number,
        })
        s_url = _build_url(action="tv_episodes", tmdb_id=tmdb_id,
                           imdb_id=imdb_id, season=s_number)
        _add_item(s_url, s_li, is_folder=True)

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE, title)
    xbmcplugin.setContent(PLUGIN_HANDLE, "tvshows")
    _end_list()


def action_tv_episodes(params):
    """List episodes for a season."""
    api_key = _get_api_key()
    if not api_key:
        return

    tmdb_id = params.get("tmdb_id")
    imdb_id = params.get("imdb_id", "")
    season = int(params.get("season", 1))
    lang = _language()

    season_data = tmdb_api.get_tv_season(api_key, tmdb_id, season,
                                         language=lang)
    if not season_data:
        xbmcgui.Dialog().notification(ADDON_NAME, _s("network_error"),
                                      xbmcgui.NOTIFICATION_ERROR)
        _end_list()
        return

    show_name = season_data.get("name", "")
    for episode in season_data.get("episodes", []):
        ep_number = episode.get("episode_number", 0)
        ep_name = episode.get("name", "Episode {n}".format(n=ep_number))
        ep_thumb = tmdb_api.image_url(episode.get("still_path"), size="w342")
        ep_overview = episode.get("overview", "")
        ep_rating = episode.get("vote_average", 0)
        air_date = episode.get("air_date", "")
        label = "{s}x{e:02d}  {n}".format(s=season, e=ep_number, n=ep_name)

        ep_li = _make_list_item(label, thumbnail=ep_thumb, is_folder=False)
        ep_li.setInfo("video", {
            "title": ep_name,
            "tvshowtitle": show_name,
            "season": season,
            "episode": ep_number,
            "plot": ep_overview,
            "rating": float(ep_rating),
            "aired": air_date,
            "mediatype": "episode",
        })
        ep_li.setProperty("IsPlayable", "true")

        if imdb_id:
            play_url = _build_url(action="play_tv", imdb_id=imdb_id,
                                  title=label, season=season,
                                  episode=ep_number)
        else:
            play_url = _build_url(action="noop")

        _add_item(play_url, ep_li, is_folder=False)

    xbmcplugin.setPluginCategory(
        PLUGIN_HANDLE,
        "{name} — {s} {n}".format(name=show_name, s=_s("season"), n=season))
    xbmcplugin.setContent(PLUGIN_HANDLE, "episodes")
    _end_list()


def action_search(params):
    """Prompt for a search term, then show combined movie + TV results."""
    query = params.get("query", "")
    if not query:
        query = xbmcgui.Dialog().input(_s("search_hint")).strip()
    if not query:
        return

    api_key = _get_api_key()
    if not api_key:
        return

    page = int(params.get("page", 1))
    lang = _language()

    data = tmdb_api.search_multi(api_key, query=query, page=page,
                                 language=lang)
    if not data:
        xbmcgui.Dialog().notification(ADDON_NAME, _s("network_error"),
                                      xbmcgui.NOTIFICATION_ERROR)
        _end_list()
        return

    results = data.get("results", [])
    if not results:
        xbmcgui.Dialog().ok(ADDON_NAME, _s("no_results"))
        _end_list()
        return

    for item in results:
        media_type = item.get("media_type", "")
        if media_type not in ("movie", "tv"):
            continue

        if media_type == "movie":
            title = item.get("title", "")
            year = str(item.get("release_date", ""))[:4]
            dest_action = "movie_details"
        else:
            title = item.get("name", "")
            year = str(item.get("first_air_date", ""))[:4]
            dest_action = "tv_seasons"

        poster = tmdb_api.image_url(item.get("poster_path"), size="w342")
        fanart = tmdb_api.image_url(item.get("backdrop_path"), size="w1280")
        label = "{t} ({y})  [{mt}]".format(
            t=title, y=year,
            mt="Movie" if media_type == "movie" else "TV")

        li = _make_list_item(label, thumbnail=poster, fanart=fanart,
                             is_folder=True)
        li.setInfo("video", {
            "title": title,
            "plot": item.get("overview", ""),
            "rating": float(item.get("vote_average", 0)),
            "mediatype": media_type,
        })
        url = _build_url(action=dest_action, tmdb_id=item.get("id"))
        _add_item(url, li, is_folder=True)

    total_pages = data.get("total_pages", 1)
    if page < total_pages:
        next_li = _make_list_item(
            "[B]{np} ({cur}/{tot})[/B]".format(
                np=_s("next_page"), cur=page + 1, tot=total_pages)
        )
        next_url = _build_url(action="search", query=query, page=page + 1)
        _add_item(next_url, next_li, is_folder=True)

    xbmcplugin.setPluginCategory(PLUGIN_HANDLE,
                                 "{s}: {q}".format(s=_s("search"), q=query))
    _end_list()


# ---------------------------------------------------------------------------
# Playback actions
# ---------------------------------------------------------------------------

def action_play_movie(params):
    """Resolve the VidSrc URL and hand it to Kodi's player."""
    imdb_id = params.get("imdb_id", "")
    title = params.get("title", "")

    if not imdb_id:
        xbmcgui.Dialog().ok(ADDON_NAME, _s("no_imdb"))
        return

    stream_url = tmdb_api.build_vidsrc_movie_url(imdb_id)
    xbmc.log("[MovieDB] Playing movie: {url}".format(url=stream_url),
             xbmc.LOGINFO)

    li = xbmcgui.ListItem(label=title, path=stream_url)
    li.setProperty("IsPlayable", "true")
    li.setMimeType("text/html")
    li.setContentLookup(False)
    xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, listitem=li)


def action_play_tv(params):
    """Resolve the VidSrc URL for a TV episode and play it."""
    imdb_id = params.get("imdb_id", "")
    title = params.get("title", "")
    season = params.get("season", "1")
    episode = params.get("episode", "1")

    if not imdb_id:
        xbmcgui.Dialog().ok(ADDON_NAME, _s("no_imdb"))
        return

    stream_url = tmdb_api.build_vidsrc_tv_url(imdb_id, season, episode)
    xbmc.log("[MovieDB] Playing TV episode: {url}".format(url=stream_url),
             xbmc.LOGINFO)

    li = xbmcgui.ListItem(label=title, path=stream_url)
    li.setProperty("IsPlayable", "true")
    li.setMimeType("text/html")
    li.setContentLookup(False)
    xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, listitem=li)


def action_play_trailer(params):
    """Play a YouTube trailer URL via Kodi."""
    url = params.get("url", "")
    title = params.get("title", "Trailer")

    if not url:
        xbmcgui.Dialog().notification(ADDON_NAME, _s("no_trailer"),
                                      xbmcgui.NOTIFICATION_INFO)
        return

    xbmc.log("[MovieDB] Playing trailer: {url}".format(url=url), xbmc.LOGINFO)
    li = xbmcgui.ListItem(label=title, path=url)
    li.setProperty("IsPlayable", "true")
    xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, listitem=li)


def action_noop():
    """No-op action used for informational (non-playable) list entries."""
    xbmcplugin.endOfDirectory(PLUGIN_HANDLE, succeeded=False)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def router(params):
    """Dispatch to the correct handler based on *params['action']*."""
    action = params.get("action", "main")

    if action == "main":
        action_main()
    elif action == "movies":
        action_movies()
    elif action == "tv":
        action_tv()
    elif action == "list_movies":
        action_list_movies(params)
    elif action == "list_tv":
        action_list_tv(params)
    elif action == "movie_details":
        action_movie_details(params)
    elif action == "tv_seasons":
        action_tv_seasons(params)
    elif action == "tv_episodes":
        action_tv_episodes(params)
    elif action == "search":
        action_search(params)
    elif action == "play_movie":
        action_play_movie(params)
    elif action == "play_tv":
        action_play_tv(params)
    elif action == "play_trailer":
        action_play_trailer(params)
    elif action == "noop":
        action_noop()
    else:
        xbmc.log("[MovieDB] Unknown action: {a}".format(a=action), xbmc.LOGWARNING)
        action_main()


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    router(_parse_args())
