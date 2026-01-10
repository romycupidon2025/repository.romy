# dinbox.py
import os
import re
import sys
import xbmc
import time
import xbmcgui
import xbmcvfs
import xbmcplugin
import xbmcaddon
import requests
import urllib.parse
from resources.lib import epg

addon = xbmcaddon.Addon()
AUTENTIFICARE = addon.getSetting('autentificare')
PAROLA = addon.getSetting('parola')

LOGERROR = 1
LOGINFO = 4

API_KEY = "3a589e724138409c9df12e3eaff68abd"
CLIENT_ID = 1
DEVICE = "android"

BASE_URL = "https://tv.dinbox.tv/api/tvmiddleware/api"
LOGIN_API_URL = (
    f"{BASE_URL}/login/?abonement={{abonement}}&password={{password}}&client_id={CLIENT_ID}"
    f"&api_key={API_KEY}&device=web_app&device_uid=6f210e43-3760-4f9e-9c11-4e4ecb2961c1"
)

_auth_data = None

# ======================== AUTENTIFICARE ========================

def login_api(abonement, parola):
    global _auth_data

    if _auth_data and "authkey" in _auth_data:
        return _auth_data

    addon = xbmcaddon.Addon()
    cached_auth = addon.getSettingString("cached_authkey")
    cached_sess = addon.getSettingString("cached_sesskey")
    cached_time = addon.getSettingInt("cached_auth_time")

    if cached_auth and cached_time and time.time() - cached_time < 60:
        _auth_data = {
            "authkey": cached_auth,
            "sess_key": cached_sess,
            "abonement": abonement
        }
        xbmc.log(f"[Dinbox] ♻️ Autentificare din cache reușită", level=LOGINFO)
        return _auth_data

    url = LOGIN_API_URL.format(abonement=abonement, password=parola)
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare la login API: {e}", level=LOGERROR)
        return None

    if data.get("error") == 0 and "authkey" in data:
        xbmc.log(f"[Dinbox] ✅ Autentificare API reușită pentru abonement {abonement}", level=LOGINFO)
        addon.setSettingString("cached_authkey", data["authkey"])
        addon.setSettingString("cached_sesskey", str(data.get("sess_key") or abonement))
        addon.setSettingInt("cached_auth_time", int(time.time()))
        _auth_data = data
        return data

    xbmc.log(f"[Dinbox] ❌ Autentificare API eșuată: {data}", level=LOGERROR)
    xbmcgui.Dialog().notification("Dinbox", "Autentificare eșuată!", xbmcgui.NOTIFICATION_ERROR)
    return None

# ======================== TV ========================

def list_categories(handle):
    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return
    authkey = data["authkey"]
    sess_key = str(data.get("sess_key") or data.get("abonement"))
    url = (f"{BASE_URL}/program/category/list/?authkey={authkey}&sess_key={sess_key}&device={DEVICE}&client_id={CLIENT_ID}&api_key={API_KEY}&lang=ro")
    try:
        response = requests.get(url, timeout=10)
        categories = response.json().get("categories", [])
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare extragere categorii TV: {e}", level=LOGERROR)
        return
    for cat in categories:
        name = cat.get("name", "Fără nume")
        cat_id = cat.get("id")
        icon = cat.get("icon_tv", "")
        li = xbmcgui.ListItem(label=name)
        if icon:
            li.setArt({"icon": icon, "thumb": icon})
        url = f"{sys.argv[0]}?action=channels&cat_id={cat_id}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(handle)

def list_channels_by_category(handle, cat_id):
    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return

    authkey = data["authkey"]
    sess_key = data.get("sess_key") or data.get("abonement")

    url = (
        f"{BASE_URL}/program/category/channel/list/?category_id={cat_id}&icon_width=176&icon_height=104"
        f"&authkey={authkey}&device={DEVICE}&client_id={CLIENT_ID}&api_key={API_KEY}&sess_key={sess_key}&lang=ro"
    )

    try:
        response = requests.get(url, timeout=10)
        programs = response.json().get("programs", [])
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare canale categorie {cat_id}: {e}", level=LOGERROR)
        return

    for item in programs:
        icon = item.get("icon", "")
        playback_url = item.get("url", "")
        channel_id = item.get("id")
        name = item.get("name", "Fără nume")

        if not playback_url:
            continue

        # Obținem titlul + descrierea EPG din epg.py
        label, plot = epg.build_now_next_epg(item)

        li = xbmcgui.ListItem(label=label)
        li.setArt({"thumb": icon, "icon": icon})

        info = li.getVideoInfoTag()
        info.setTitle(name)
        info.setPlot(plot)

        li.setProperty("IsPlayable", "true")

        # Adăugăm context menu pentru EPG complet
        li.addContextMenuItems(epg.build_epg_context_menu(channel_id, name))

        play_url = f"{sys.argv[0]}?action=play&url={urllib.parse.quote_plus(playback_url)}"
        xbmcplugin.addDirectoryItem(handle=handle, url=play_url, listitem=li, isFolder=False)

    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle)

# ======================== VOD Filme ========================

def list_vod_genres(handle):
    ICON_PATH = xbmcvfs.translatePath(os.path.join(addon.getAddonInfo("path"), "resources", "media", "categories"))
    FANART_PATH = addon.getAddonInfo("fanart")

    # Mapare manuală pentru iconițe personalizate
    GENRE_ICON_MAP = {
        "desene animate": "animatie",
        "animație": "animatie",
        "acțiune": "actiune",
        "comedy": "comedie",
        "comedie": "comedie",
        "copii": "copii",
        "crimă": "crima",
        "dramă": "drama",
        "fantezie": "fantezie",
        "familie": "familie",
        "documentar": "documentar",
        "istoric": "istoric",
        "aventuri": "aventuri",
        "western": "western",
        "mister": "mister",
        "militar": "militar",
        "biografic": "biografic",
        "fantasy": "fantezie",
        "ultimele adaugate": "recente",
        "filme indiene": "indiene",
        "stand up": "standup",
    }

    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return

    authkey = data["authkey"]
    sess_key = data.get("sess_key") or data.get("abonement")

    url = f"{BASE_URL}/genre/list/?authkey={authkey}&device={DEVICE}&client_id={CLIENT_ID}&api_key={API_KEY}&sess_key={sess_key}&lang=ro"

    try:
        response = requests.get(url, timeout=10)
        genres = response.json().get("genres", [])
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare extragere categorii VOD: {e}", level=LOGERROR)
        return

    for genre in genres:
        name = genre.get("name", "Fără nume")
        if name.lower().strip() == "serie":
            continue

        genre_id = genre.get("id")
        slug_key = name.lower().strip()
        slug = GENRE_ICON_MAP.get(slug_key)

        if not slug:
            # fallback la normalizare automată
            slug = slug_key
            slug = slug.replace("ă", "a").replace("â", "a").replace("î", "i").replace("ș", "s").replace("ț", "t")
            slug = slug.replace(" ", "_").replace("-", "_")

        icon_path = os.path.join(ICON_PATH, f"{slug}.png")
        if not xbmcvfs.exists(icon_path):
            icon_path = os.path.join(ICON_PATH, "default.png")

        li = xbmcgui.ListItem(label=name)
        li.setArt({
            "icon": icon_path,
            "thumb": icon_path,
            "fanart": FANART_PATH
        })

        url = f"{sys.argv[0]}?action=vod_by_genre&genre_id={genre_id}&page=1"
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(handle)

def list_vod_movies_by_genre(handle, genre_id, page=1):
    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return

    authkey = data["authkey"]
    sess_key = data.get("sess_key") or data.get("abonement")

    url = f"{BASE_URL}/video/list/?order=-created_at&gid={genre_id}&limit=24&page={page}&profile_id=-1&authkey={authkey}&device={DEVICE}&client_id={CLIENT_ID}&api_key={API_KEY}&sess_key={sess_key}&lang=ro"

    try:
        response = requests.get(url, timeout=10)
        videos = response.json().get("videos", [])
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare extragere filme gen {genre_id}: {e}", level=LOGERROR)
        return

    for item in videos:
        title = item.get("name", "Fără titlu")
        plot = re.sub('<[^<]+?>', '', item.get("description", ""))
        poster = item.get("thumbnail_big", "")
        thumb = item.get("thumbnail_small", "")
        fanart = item.get("screenshot_big", "")
        year = item.get("year", "")
        duration = item.get("duration", 0)
        rating = item.get("imdb_rating", 0.0)
        genre = item.get("genres", "")
        video_id = item.get("id")

        li = xbmcgui.ListItem(label=title)
        li.setArt({"thumb": thumb, "poster": poster, "fanart": fanart})
        li.setProperty("IsPlayable", "true")

        li.setInfo("video", {
            "title": title,
            "plot": plot,
            "year": int(year) if str(year).isdigit() else 0,
            "duration": int(duration),
            "rating": float(rating),
            "genre": genre
        })

        url = f"{sys.argv[0]}?action=play_vod&vid={video_id}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=False)

    if page > 1:
        li = xbmcgui.ListItem(label="<< Pagina anterioară")
        url_prev = f"{sys.argv[0]}?action=vod_by_genre&genre_id={genre_id}&page={page - 1}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url_prev, listitem=li, isFolder=True)

    if len(videos) == 24:
        li = xbmcgui.ListItem(label=">> Pagina următoare")
        url_next = f"{sys.argv[0]}?action=vod_by_genre&genre_id={genre_id}&page={page + 1}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url_next, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(handle)

# ======================== Seriale ========================

def list_series(handle, page=1):
    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return

    authkey = data["authkey"]
    sess_key = data.get("sess_key") or data.get("abonement")
    url = f"{BASE_URL}/video/list/?order=-created_at&gid=6&limit=24&page={page}&profile_id=-1&authkey={authkey}&device={DEVICE}&client_id={CLIENT_ID}&api_key={API_KEY}&sess_key={sess_key}&lang=ro"

    try:
        response = requests.get(url, timeout=10)
        videos = response.json().get("videos", [])
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare extragere seriale: {e}", level=LOGERROR)
        return

    for item in videos:
        title = item.get("name", "Fără titlu")
        plot = re.sub('<[^<]+?>', '', item.get("description", ""))
        poster = item.get("thumbnail_big", "")
        thumb = item.get("thumbnail_small", "")
        fanart = item.get("screenshot_big", "")
        year = item.get("year", "")
        duration = item.get("duration", 0)
        rating = item.get("imdb_rating", 0.0)
        genre = item.get("genres", "")
        video_id = item.get("id")

        li = xbmcgui.ListItem(label=title)
        li.setArt({"thumb": thumb, "poster": poster, "fanart": fanart})
        li.setInfo("video", {
            "title": title,
            "plot": plot,
            "year": int(year) if str(year).isdigit() else 0,
            "duration": int(duration),
            "rating": float(rating),
            "genre": genre
        })

        url = f"{sys.argv[0]}?action=seasons&vid={video_id}&thumb={urllib.parse.quote(thumb)}&fanart={urllib.parse.quote(fanart)}&poster={urllib.parse.quote(poster)}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)

    if page > 1:
        li = xbmcgui.ListItem(label="<< Pagina anterioară")
        url_prev = f"{sys.argv[0]}?action=series&page={page - 1}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url_prev, listitem=li, isFolder=True)

    if len(videos) == 24:
        li = xbmcgui.ListItem(label=">> Pagina următoare")
        url_next = f"{sys.argv[0]}?action=series&page={page + 1}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url_next, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(handle)

# ======================== SEZOANE ========================

def list_seasons(handle, vid, thumb=None, fanart=None, poster=None):
    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return
    authkey = data["authkey"]
    sess_key = data.get("sess_key") or data.get("abonement")
    url = f"{BASE_URL}/video/detail/?vid={vid}&authkey={authkey}&device={DEVICE}&client_id={CLIENT_ID}&api_key={API_KEY}&sess_key={sess_key}&lang=ro"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare extragere sezoane: {e}", level=LOGERROR)
        return
    seasons = data.get("seasons", [])
    for season in seasons:
        season_id = season.get("id")
        number = season.get("number", "?")
        li = xbmcgui.ListItem(label=f"Sezon {number}")
        li.setArt({"thumb": thumb, "fanart": fanart, "poster": poster or thumb})
        url = f"{sys.argv[0]}?action=episodes&season_id={season_id}&thumb={urllib.parse.quote(thumb or '')}&fanart={urllib.parse.quote(fanart or '')}&poster={urllib.parse.quote(poster or thumb or '')}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(handle)

# ======================== EPISOADE ========================

def list_episodes(handle, season_id, thumb=None, fanart=None, poster=None):
    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return
    authkey = data["authkey"]
    sess_key = data.get("sess_key") or data.get("abonement")
    url = f"{BASE_URL}/video/episode/list/?season_id={season_id}&authkey={authkey}&device={DEVICE}&client_id={CLIENT_ID}&api_key={API_KEY}&sess_key={sess_key}&lang=ro"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare extragere episoade: {e}", level=LOGERROR)
        return

    episodes = data.get("episodes", [])
    for episode in episodes:
        number = episode.get("number", "?")
        title = episode.get("name", f"Episodul {number}")
        plot = re.sub('<[^<]+?>', '', episode.get("description", ""))
        duration = episode.get("duration", 0)

        file = episode.get("files", [{}])[0]
        stream_id = file.get("id")
        if not stream_id:
            continue

        li = xbmcgui.ListItem(label=title)
        li.setArt({"thumb": thumb, "fanart": fanart, "poster": poster or thumb})

        info = li.getVideoInfoTag()
        info.setTitle(title)
        info.setPlot(plot)
        info.setEpisode(int(number) if str(number).isdigit() else -1)
        info.setDuration(int(duration))

        li.setProperty("IsPlayable", "true")

        play_url = f"{sys.argv[0]}?action=play_episode&file_id={stream_id}"
        xbmcplugin.addDirectoryItem(handle=handle, url=play_url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)

# ======================== Playback ========================

def play(playback_url):
    if not playback_url:
        xbmcgui.Dialog().notification("Dinbox", "URL lipsă!", xbmcgui.NOTIFICATION_ERROR)
        return
    if "redirect=0" not in playback_url:
        joiner = "&" if "?" in playback_url else "?"
        playback_url += f"{joiner}redirect=0"
    try:
        r = requests.get(playback_url, timeout=10)
        data = r.json()
        final_url = data.get("url") or data.get("uri")
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare extragere link redare: {e}", level=LOGERROR)
        xbmcgui.Dialog().notification("Dinbox", "Eroare extragere stream!", xbmcgui.NOTIFICATION_ERROR)
        return
    if not final_url:
        xbmcgui.Dialog().notification("Dinbox", "Stream invalid!", xbmcgui.NOTIFICATION_ERROR)
        return
    li = xbmcgui.ListItem(path=final_url)
    li.setMimeType("application/vnd.apple.mpegurl")
    li.setContentLookup(False)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)

def play_vod(vid):
    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return
    authkey = data["authkey"]
    sess_key = data.get("sess_key") or data.get("abonement")
    url = f"{BASE_URL}/video/detail/?vid={vid}&authkey={authkey}&device={DEVICE}&client_id={CLIENT_ID}&api_key={API_KEY}&sess_key={sess_key}&lang=ro"
    try:
        response = requests.get(url, timeout=10)
        detail = response.json()
    except Exception as e:
        xbmcgui.Dialog().notification("Dinbox", f"Eroare API: {e}", xbmcgui.NOTIFICATION_ERROR)
        return
    actions = detail.get("actions", [])
    if not actions:
        xbmcgui.Dialog().notification("Dinbox", "Fără sursă video!", xbmcgui.NOTIFICATION_ERROR)
        return
    stream_api_url = actions[0].get("url")
    if not stream_api_url:
        xbmcgui.Dialog().notification("Dinbox", "URL video lipsă!", xbmcgui.NOTIFICATION_ERROR)
        return
    headers = {
        "User-Agent": "okhttp/4.10.0",
        "Accept": "*/*"
    }
    try:
        resp = requests.get(stream_api_url, headers=headers, allow_redirects=True)
        final_url = resp.url
    except Exception as e:
        xbmcgui.Dialog().notification("Dinbox", f"Redirect eșuat: {e}", xbmcgui.NOTIFICATION_ERROR)
        return
    if not final_url or ".m3u8" not in final_url:
        xbmcgui.Dialog().notification("Dinbox", "Stream invalid (nu e .m3u8)", xbmcgui.NOTIFICATION_ERROR)
        return
    li = xbmcgui.ListItem(path=final_url)
    li.setMimeType("application/vnd.apple.mpegurl")
    li.setContentLookup(False)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)

def play_episode(file_id):
    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return
    authkey = data["authkey"]
    url = f"https://mw.dinbox.tv/tvmiddleware/api/video/url/?vfid={file_id}&device=android&client_id=1&authkey={authkey}"
    headers = {
        "User-Agent": "okhttp/4.10.0",
        "Accept": "*/*"
    }
    try:
        resp = requests.get(url, headers=headers, allow_redirects=True)
        final_url = resp.url
    except Exception as e:
        xbmcgui.Dialog().notification("Dinbox", f"Redirect eșuat: {e}", xbmcgui.NOTIFICATION_ERROR)
        return
    if not final_url or ".m3u8" not in final_url:
        xbmcgui.Dialog().notification("Dinbox", "Stream invalid (nu e .m3u8)", xbmcgui.NOTIFICATION_ERROR)
        return
    li = xbmcgui.ListItem(path=final_url)
    li.setMimeType("application/vnd.apple.mpegurl")
    li.setContentLookup(False)
    xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)

# ======================== Căutare =========================

def search_dialog(handle): # Continuă să primească 'handle' din default.py
    keyboard = xbmcgui.Dialog().input("Căutare", type=xbmcgui.INPUT_ALPHANUM)
    if not keyboard:
        xbmcplugin.endOfDirectory(handle, succeeded=False) # Închide directorul dacă utilizatorul anulează
        return

    search_term = keyboard.strip()
    if not search_term:
        xbmcplugin.endOfDirectory(handle, succeeded=False) # Închide directorul dacă termenul e gol
        return

    choice = xbmcgui.Dialog().select("Selectează domeniul", ["🎬 Filme/Seriale", "📺 TV"])

    all_results = []

    if choice == 0: # Cautare Filme/Seriale (VOD)
        all_results = search_vod(search_term) # Apelez fără handle, colectez rezultatele
    elif choice == 1: # Cautare TV
        all_results = search_tv(search_term) # Apelez fără handle, colectez rezultatele
    else: # Utilizatorul a anulat selecția de domeniu (a apăsat ESC)
        xbmcplugin.endOfDirectory(handle, succeeded=False) # Închide directorul
        return

    # Acum, adaugă toate rezultatele colectate în directorul Kodi
    if not all_results:
        xbmcgui.Dialog().notification("Dinbox", "Niciun rezultat găsit.", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(handle, succeeded=False) # Închide directorul gol, sau cu succes=True dacă vrei doar o notificare
        return

    for url_item, listitem_item, is_folder_item in all_results:
        xbmcplugin.addDirectoryItem(handle=handle, url=url_item, listitem=listitem_item, isFolder=is_folder_item)

    xbmcplugin.endOfDirectory(handle) # <-- ACUM și O SINGURĂ DATĂ, închide directorul deschis de 'search'

def search_tv(query): # NU mai primește 'handle' aici
    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return [] # Returnează listă goală în caz de eroare/lipsă autentificare

    authkey = data["authkey"]
    sess_key = str(data.get("sess_key") or data.get("abonement"))

    url = (
        f"{BASE_URL}/channel/list/search/?search={urllib.parse.quote_plus(query)}&icon_width=32&icon_height=19"
        f"&authkey={authkey}&device={DEVICE}&client_id={CLIENT_ID}&api_key={API_KEY}&sess_key={sess_key}&lang=ro"
    )

    channels_to_add = []
    try:
        response = requests.get(url, timeout=10)
        xbmc.log(f"[Dinbox] 🔍 Rezultate TV brute: {response.text}", xbmc.LOGWARNING)
        channels = response.json().get("channels", [])
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare căutare TV: {e}", level=LOGERROR)
        return [] # Returnează listă goală în caz de eroare

    if not channels:
        # Nu mai afișăm notificare aici, o va face search_dialog dacă nu sunt rezultate combinate
        return []

    for item in channels:
        name = item.get("name", "Fără nume")
        icon = item.get("icon", "")
        playback_url = item.get("url", "")

        if not playback_url:
            continue

        li = xbmcgui.ListItem(label=name)
        li.setArt({"thumb": icon, "icon": icon, "fanart": icon})
        li.setInfo("video", {"title": name})
        li.setProperty("IsPlayable", "true")

        play_url = f"{sys.argv[0]}?action=play&url={urllib.parse.quote_plus(playback_url)}"
        channels_to_add.append((play_url, li, False)) # Adaugă la lista de returnat

    return channels_to_add # Returnează lista


def search_vod(query): # NU mai primește 'handle' aici
    data = login_api(AUTENTIFICARE, PAROLA)
    if not data:
        return [] # Returnează listă goală

    authkey = data["authkey"]
    sess_key = str(data.get("sess_key") or data.get("abonement"))

    url = (
        f"{BASE_URL}/video/list/?limit=30&page=1&search={urllib.parse.quote_plus(query)}&order=-created_at"
        f"&authkey={authkey}&device={DEVICE}&client_id={CLIENT_ID}&api_key={API_KEY}&sess_key={sess_key}&lang=ro"
    )

    videos_to_add = []
    try:
        response = requests.get(url, timeout=10)
        xbmc.log(f"[Dinbox] 🔍 Rezultate VOD brute: {response.text}", xbmc.LOGWARNING)
        videos = response.json().get("videos", [])
    except Exception as e:
        xbmc.log(f"[Dinbox] ❌ Eroare căutare VOD: {e}", level=LOGERROR)
        return [] # Returnează listă goală

    if not videos:
        # Nu mai afișăm notificare aici
        return []

    for item in videos:
        title = item.get("name", "Fără titlu")
        plot = re.sub('<[^<]+?>', '', item.get("description", ""))
        poster = item.get("thumbnail_big", "")
        thumb = item.get("thumbnail_small", "")
        fanart = item.get("screenshot_big", "")
        year = item.get("year", "")
        duration = item.get("duration", 0)
        rating = item.get("imdb_rating", 0.0)
        genre = item.get("genres", "")
        video_id = item.get("id")

        li = xbmcgui.ListItem(label=title)
        li.setArt({"thumb": thumb, "poster": poster, "fanart": fanart})
        li.setInfo("video", {
            "title": title,
            "plot": plot,
            "year": year,
            "duration": duration,
            "genre": genre,
            "rating": rating
        })
        li.setProperty("IsPlayable", "true")
        url = f"{sys.argv[0]}?action=play_vod&vid={video_id}"
        videos_to_add.append((url, li, False)) # Adaugă la lista de returnat

    return videos_to_add # Returnează lista
