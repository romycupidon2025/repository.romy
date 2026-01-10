import sys
import xbmcgui
import xbmcvfs
import xbmcaddon
import xbmcplugin
import urllib.parse
from resources.lib import epg
from resources.lib import dinbox
from urllib.parse import quote

addon = xbmcaddon.Addon()
addon_handle = int(sys.argv[1])
args = urllib.parse.parse_qs(sys.argv[2][1:]) if len(sys.argv) > 2 else {}

action = args.get("action", [None])[0]
cat_id = args.get("cat_id", [None])[0]
genre_id = args.get("genre_id", [None])[0]
page = int(args.get("page", [1])[0])
vid = args.get("vid", [None])[0]
season_id = args.get("season_id", [None])[0]
file_id = args.get("file_id", [None])[0]
url = args.get("url", [None])[0]

def main_menu():

    addon_path = addon.getAddonInfo('path')
    media_menu_path = xbmcvfs.translatePath(addon_path + '/resources/media/menu/')
    addon_fanart = addon.getAddonInfo('fanart')

    # --- TV ---
    li_tv = xbmcgui.ListItem(label="TV")
    li_tv.setArt({
        'thumb': f"{media_menu_path}tv.png",
        'icon': f"{media_menu_path}tv.png",
        'fanart': addon_fanart
    })
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=f"{sys.argv[0]}?action=tv_categories",
                                listitem=li_tv, isFolder=True)

    # --- Movies ---
    li_vod = xbmcgui.ListItem(label="Filme")
    li_vod.setArt({
        'thumb': f"{media_menu_path}movies.png",
        'icon': f"{media_menu_path}movies.png",
        'fanart': addon_fanart
    })
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=f"{sys.argv[0]}?action=vod_genres",
                                listitem=li_vod, isFolder=True)

    # --- Series ---
    li_series = xbmcgui.ListItem(label="Seriale")
    li_series.setArt({
        'thumb': f"{media_menu_path}tvshows.png",
        'icon': f"{media_menu_path}tvshows.png",
        'fanart': addon_fanart
    })
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=f"{sys.argv[0]}?action=series",
                                listitem=li_series, isFolder=True)

    # --- Search ---
    li_search = xbmcgui.ListItem(label="Căutare")
    li_search.setArt({
        'thumb': f"{media_menu_path}search.png",
        'icon': f"{media_menu_path}search.png",
        'fanart': addon_fanart
    })
    xbmcplugin.addDirectoryItem(handle=addon_handle,
                                url=f"{sys.argv[0]}?action=search",
                                listitem=li_search,isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)

if action == "tv_categories":
    dinbox.list_categories(addon_handle)
elif action == "channels" and cat_id:
    dinbox.list_channels_by_category(addon_handle, cat_id)
elif action == "vod":
    dinbox.list_vod_movies(addon_handle, page)
elif action == "vod_genres":
    dinbox.list_vod_genres(addon_handle)
elif action == "vod_by_genre" and genre_id:
    dinbox.list_vod_movies_by_genre(addon_handle, genre_id, page)
elif action == "play" and url:
    dinbox.play(url)
elif action == "play_vod" and vid:
    dinbox.play_vod(vid)
elif action == "series":
    dinbox.list_series(addon_handle, page)
elif action == "seasons" and vid:
    dinbox.list_seasons(addon_handle, vid)
elif action == "episodes" and season_id:
    dinbox.list_episodes(addon_handle, season_id)
elif action == "play_episode" and file_id:
    dinbox.play_episode(file_id)
elif action == "search":
    dinbox.search_dialog(addon_handle)
elif action == "show_epg":
    channel_id = args.get("channel_id", [None])[0]
    name = urllib.parse.unquote(args.get("name", [""])[0])
    if channel_id:
        epg.show_epg_dialog(channel_id, name)
else:
    main_menu()
