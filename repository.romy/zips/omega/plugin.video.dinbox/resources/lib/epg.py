import xbmc
import xbmcgui
import xbmcaddon
import requests
import urllib.parse
from datetime import datetime
from .dinbox import login_api

addon = xbmcaddon.Addon()
DEVICE = "android"
CLIENT_ID = 1
API_KEY = "3a589e724138409c9df12e3eaff68abd"
BASE_URL = "https://tv.dinbox.tv/api/tvmiddleware/api"
LOGERROR = 1


def get_epg_day_schedule(channel_id, date="today"):  # DEBUG
    data = login_api(addon.getSetting("autentificare"), addon.getSetting("parola"))
    if not data:
        return []

    authkey = data["authkey"]
    sess_key = "265492"  # DEBUG: hardcoded sess_key temporar
    # sess_key = str(data.get("sess_key") or data.get("abonement") or "").strip()
    if not sess_key:
        xbmc.log(f"[EPG] ❌ sess_key lipsă pentru canal {channel_id}", level=LOGERROR)
        return []

    url = (
        f"{BASE_URL}/channel/programs/?cid={channel_id}&timeshift_offset=0&compact=0&limit=6"
        f"&authkey={authkey}&sess_key={sess_key}&device=browser&client_id={CLIENT_ID}&api_key={API_KEY}&lang=ro"
    )
    xbmc.log(f"[EPG] 📡 URL cerere nou: {url}", level=xbmc.LOGWARNING)

    try:
        response = requests.get(url, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            xbmc.log(f"[EPG] ❌ Conținut invalid (non-JSON): {response.text[:300]}", level=LOGERROR)
            raise ValueError("Răspunsul nu este de tip JSON valid.")

        xbmc.log(f"[EPG] ✅ Răspuns JSON brut pentru canal {channel_id}: {response.text[:300]}", level=xbmc.LOGWARNING)
        items = response.json().get("programs", [])
        return items
    except Exception as e:
        xbmc.log(f"[EPG] ❌ Eroare extragere EPG pentru canal {channel_id}: {e}", level=LOGERROR)
        return []


def show_epg_dialog(channel_id, name):
    items = get_epg_day_schedule(channel_id)
    if not items:
        xbmcgui.Dialog().notification("EPG", "Niciun program disponibil.", xbmcgui.NOTIFICATION_INFO)
        return

    lines = []
    for i in items:
        try:
            start_ts = int(i.get('program_begin_time'))
            end_ts = int(i.get('program_end_time'))
            title = i.get('program_name', '').strip()

            start_str = datetime.fromtimestamp(start_ts).strftime('%H:%M')
            end_str = datetime.fromtimestamp(end_ts).strftime('%H:%M')
            lines.append(f"{start_str} - {end_str}: {title}")
        except Exception as e:
            xbmc.log(f"[EPG] ⚠️ Eroare la formatarea unei intrări EPG: {e}", level=LOGERROR)

    text = "\n".join(lines)
    xbmcgui.Dialog().textviewer(f"EPG - {name}", text)

def format_epg_time(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%H:%M")
    except:
        return ""

def build_now_next_epg(item):
    name = item.get("name", "").strip()

    epg_now = item.get("program_name", "").strip()
    start_now = format_epg_time(item.get("program_begin_time"))
    end_now = format_epg_time(item.get("program_end_time"))

    epg_next = item.get("next_program_name", "").strip()
    start_next = format_epg_time(item.get("next_program_begin_time"))
    end_next = format_epg_time(item.get("next_program_end_time"))

    label = name

    plot = ""
    if epg_now and start_now and end_now:
        plot += f"Acum: {epg_now} ({start_now} - {end_now})"
    elif epg_now:
        plot += f"Acum: {epg_now}"

    if epg_next and start_next and end_next:
        plot += f"\nUrmează: {epg_next} ({start_next} - {end_next})"
    elif epg_next:
        plot += f"\nUrmează: {epg_next}"

    return label, plot

def build_epg_context_menu(channel_id, name):
    epg_url = f"plugin://{addon.getAddonInfo('id')}?action=show_epg&channel_id={channel_id}&name={urllib.parse.quote(name)}"
    return [("📅 Vezi EPG complet", f"RunPlugin({epg_url})")]


def build_epg_label(name, start, end):
    if start and end:
        return f"{name} ({start}-{end})"
    return name
