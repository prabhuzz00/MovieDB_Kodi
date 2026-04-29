# MovieDB — Kodi Video Addon

Browse popular **Movies** and **TV Series**, view full details (poster, backdrop,
synopsis, cast, trailers) scraped from [The Movie Database (TMDB)](https://www.themoviedb.org/),
and play movies / TV episodes through the embedded
[VidSrc](https://vidsrcme.ru/) player.

---

## Features

| Feature | Details |
|---------|---------|
| 🎬 Movies | Popular · Top Rated · Now Playing · Upcoming |
| 📺 TV Series | Popular · Top Rated · On The Air · Airing Today |
| 🔍 Search | Combined movie + TV search via TMDB |
| 🖼️ Rich metadata | Poster, backdrop, rating, genres, overview, release year |
| 👥 Cast | Top 10 cast members with profile photos |
| 🎞️ Trailers | YouTube trailers fetched from TMDB |
| ▶️ Playback | Movies & TV episodes via `https://vidsrcme.ru/embed/…` |
| 📄 Pagination | "Next page" entry for every long list |

---

## Requirements

* Kodi 18 (Leia) or newer  
* A free **TMDB API key** — get one at <https://www.themoviedb.org/settings/api>

---

## Installation

### Option A — Install from ZIP (recommended)

1. Clone / download this repository and zip the folder:
   ```
   zip -r plugin.video.moviedb.zip MovieDB_Kodi/
   ```
2. In Kodi: **Add-ons → Install from ZIP file** → select the zip.
3. Open the addon settings and paste your **TMDB API Key**.

### Option B — Manual installation

1. Copy the entire repository folder into your Kodi `addons` directory,
   renaming it to `plugin.video.moviedb`:
   ```
   ~/.kodi/addons/plugin.video.moviedb/
   ```
2. Restart Kodi, then enable the addon under
   **Add-ons → My add-ons → Video add-ons → MovieDB**.
3. Open settings and enter your **TMDB API Key**.

---

## File Structure

```
plugin.video.moviedb/
├── addon.xml                        ← Addon manifest
├── default.py                       ← Main entry-point & URL router
├── lib/
│   └── tmdb_api.py                  ← TMDB REST API v3 wrapper
└── resources/
    ├── settings.xml                 ← Addon settings (API key, language)
    └── language/
        └── English/
            └── strings.xml          ← Localisation strings
```

---

## Configuration

| Setting | Description |
|---------|-------------|
| **TMDB API Key** | Your personal key from tmdb.org (required) |
| **Language Code** | IETF tag used for metadata, e.g. `en-US`, `fr-FR` |
| **Results per page** | 10 – 40 items per list page (default 20) |
| **Enable Trailers** | Show/hide the trailer entry in movie details |
| **Play Quality Hint** | Embed / 720p / 1080p hint sent to VidSrc |

---

## Play URLs

| Content | URL pattern |
|---------|-------------|
| Movie | `https://vidsrcme.ru/embed/movie?imdb=<imdb_id>` |
| TV Episode | `https://vidsrcme.ru/embed/tv?imdb=<imdb_id>&season=<s>&episode=<e>` |

---

## Disclaimer

This addon uses the TMDB API for metadata and VidSrc for streaming.
Neither service is affiliated with this project.
Use in accordance with your local laws and the respective terms of service.

---

## License

GPL v2.0 — see [LICENSE](LICENSE).
