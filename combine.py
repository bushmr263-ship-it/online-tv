import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

SONY_JSON_URL = (
    "https://raw.githubusercontent.com/bushmr263-ship-it/"
    "SonyLiv_Event_Playlist/refs/heads/main/SonyLiv_data.json"
)
SONY_M3U_URL = (
    "https://raw.githubusercontent.com/bushmr263-ship-it/"
    "SonyLiv_Event_Playlist/refs/heads/main/SonyLiv.m3u"
)
EAMIN_M3U_URL = (
    "https://raw.githubusercontent.com/bushmr263-ship-it/"
    "sm-eamin-playlists/refs/heads/main/playlists/eamin-tv.m3u"
)

TARGET_M3U_PATH = "combined.m3u"

# eamin-tv.m3u থেকে শুধু যেসব চ্যানেল নেবেন তাদের নাম
EAMIN_SELECTED_CHANNELS = [
    "Colors",
    "Colors Cineplex",
    "& Tv",
    "& Picture HD",
    "Star Gold HD",
    "Star Gold Select",
    "Star Plus",
    "Zee Tv",
    "Zee Bollywood",
    "Zee Cinema HD",
    "Sony Television HD",
    "Sony Max",
    "Sony Max HD",
    "Sony Max 1",
    "Sony Max 2",
    "Sony Sab HD",
    "Sony Pal",
    "Sony Wah",
    "Sony Kal",
    "Sony Marathi",
    "Sony Pix",
    "Movies Now",
    "Star Movies HD",
    "Star Movies Select",
    "Hum TV",
    "Gold Mines",
    "Gold Mines Movies",
    "Gold Mines Bollywood",
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


EAMIN_TARGET_SET = {normalize_text(name) for name in EAMIN_SELECTED_CHANNELS}


def extract_channel_name(extinf: str) -> str:
    tvg_name_match = re.search(r'tvg-name="([^"]*)"', extinf)
    if tvg_name_match and tvg_name_match.group(1).strip():
        return tvg_name_match.group(1).strip()
    if "," in extinf:
        return extinf.split(",")[-1].strip()
    return ""


def get_entry_key(extinf: str) -> str:
    tvg_id_match = re.search(r'tvg-id="([^"]*)"', extinf)
    if tvg_id_match and tvg_id_match.group(1).strip():
        return "id:" + normalize_text(tvg_id_match.group(1))

    name = extract_channel_name(extinf)
    if name:
        return "name:" + normalize_text(name)

    return "raw:" + normalize_text(extinf)


def fetch_text(url: str) -> str:
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    return resp.text


def fetch_json(url: str) -> dict:
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    return resp.json()


def find_stream_url_in_match(match_obj: dict) -> str | None:
    candidate_keys = [
        "stream_url",
        "streamUrl",
        "url",
        "m3u8",
        "m3u8_url",
        "hls_url",
        "play_url",
        "video_url",
        "link",
    ]
    for k in candidate_keys:
        val = match_obj.get(k)
        if isinstance(val, str) and re.match(r"^https?://", val.strip(), re.IGNORECASE):
            return val.strip()

    for _, val in match_obj.items():
        if isinstance(val, str):
            s = val.strip()
            if re.match(r"^https?://", s, re.IGNORECASE) and (
                ".m3u8" in s.lower() or "hdnea=" in s.lower() or "/hls/" in s.lower()
            ):
                return s
    return None


def parse_sony_json_blocks(data: dict) -> list[dict]:
    matches = data.get("matches", [])
    if not isinstance(matches, list):
        return []

    blocks = []
    for m in matches:
        if not isinstance(m, dict):
            continue

        stream_url = find_stream_url_in_match(m)
        if not stream_url:
            continue

        content_id = str(m.get("contentId") or "").strip()
        event_name = str(m.get("event_name") or m.get("title") or "SonyLiv Event").strip()
        lang = str(m.get("audioLanguageName") or "").strip()
        channel_name = str(m.get("broadcast_channel") or "").strip()
        category = str(m.get("event_category") or "Sports").strip()
        logo = str(m.get("src") or m.get("logo") or "").strip()

        display_name = event_name
        if lang and lang.upper() not in display_name.upper():
            display_name = f"{display_name} [{lang}]"
        elif channel_name and channel_name.lower() not in display_name.lower():
            display_name = f"{display_name} - {channel_name}"

        safe_display = display_name.replace('"', "")
        extinf = (
            f'#EXTINF:-1 tvg-id="{content_id}" '
            f'tvg-name="{safe_display}" '
            f'tvg-logo="{logo}" '
            f'group-title="{category}",{display_name}'
        )

        blocks.append({
            "key": get_entry_key(extinf),
            "extinf": extinf,
            "extras": [],
            "url": stream_url,
            "raw": "\n".join([extinf, stream_url]),
        })

    return blocks


def parse_m3u_blocks(m3u_text: str, allowed_names: set[str] | None = None) -> list[dict]:
    lines = [line.strip() for line in m3u_text.splitlines() if line.strip()]
    blocks = []
    i = 0

    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            extinf = lines[i]
            extras = []
            stream_url = None
            j = i + 1

            while j < len(lines) and not lines[j].startswith("#EXTINF"):
                if lines[j].startswith("#"):
                    extras.append(lines[j])
                elif re.match(r"^https?://", lines[j], re.IGNORECASE):
                    stream_url = lines[j]
                    break
                j += 1

            if stream_url:
                ch_name = normalize_text(extract_channel_name(extinf))
                if allowed_names is None or ch_name in allowed_names:
                    blocks.append({
                        "key": get_entry_key(extinf),
                        "extinf": extinf,
                        "extras": extras,
                        "url": stream_url,
                        "raw": "\n".join([extinf] + extras + [stream_url]),
                    })
            i = j + 1
        else:
            i += 1

    return blocks


def sync_all_blocks(existing_text: str, incoming_blocks: list[dict]) -> tuple[str, int, int]:
    lines = existing_text.splitlines()
    header_lines = []
    i = 0

    while i < len(lines) and not lines[i].startswith("#EXTINF"):
        header_lines.append(lines[i])
        i += 1

    existing_blocks = []
    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            extinf = lines[i].strip()
            extras = []
            stream_url = None
            j = i + 1

            while j < len(lines) and not lines[j].startswith("#EXTINF"):
                s = lines[j].strip()
                if s.startswith("#"):
                    extras.append(s)
                elif re.match(r"^https?://", s, re.IGNORECASE):
                    stream_url = s
                    break
                j += 1

            if stream_url:
                existing_blocks.append({
                    "key": get_entry_key(extinf),
                    "extinf": extinf,
                    "extras": extras,
                    "url": stream_url,
                    "raw": "\n".join([extinf] + extras + [stream_url]),
                })
            i = j + 1
        else:
            i += 1

    incoming_map = {}
    for blk in incoming_blocks:
        incoming_map[blk["key"]] = blk

    seen_keys = set()
    output_blocks = []
    added_count = 0
    updated_count = 0

    for blk in existing_blocks:
        k = blk["key"]
        if k in incoming_map:
            new_blk = incoming_map[k]
            if blk["url"] != new_blk["url"] or blk["raw"] != new_blk["raw"]:
                output_blocks.append(new_blk["raw"])
                updated_count += 1
            else:
                output_blocks.append(blk["raw"])
            seen_keys.add(k)
        else:
            output_blocks.append(blk["raw"])

    for blk in incoming_blocks:
        k = blk["key"]
        if k not in seen_keys:
            output_blocks.append(blk["raw"])
            seen_keys.add(k)
            added_count += 1

    header_text = "\n".join(header_lines).strip()
    if not header_text:
        header_text = (
            "#EXTM3U\n"
            "# ==========================================\n"
            "# Developed by: Shawon\n"
            "# Telegram: https://t.me/+VqDOF_-beaQyMWY1\n"
            "# Last Updated: \n"
            "# Channels Count: 0\n"
            "# =========================================="
        )

    total_channels = len(output_blocks)
    bd_now = datetime.now(ZoneInfo("Asia/Dhaka")).strftime("%Y-%m-%d %H:%M:%S")

    if re.search(r"#\s*Channels Count:\s*", header_text):
        header_text = re.sub(
            r"(#\s*Channels Count:\s*)\d+",
            rf"\g<1>{total_channels}",
            header_text,
            count=1,
        )
    else:
        header_text += f"\n# Channels Count: {total_channels}"

    if re.search(r"#\s*Last Updated:\s*", header_text):
        header_text = re.sub(
            r"(#\s*Last Updated:\s*).*",
            rf"\g<1>{bd_now} (BD Time)",
            header_text,
            count=1,
        )
    else:
        header_text += f"\n# Last Updated: {bd_now} (BD Time)"

    final_text = header_text + "\n\n" + "\n".join(output_blocks) + "\n"
    return final_text, added_count, updated_count


def main() -> None:
    all_incoming = []

    try:
        json_data = fetch_json(SONY_JSON_URL)
        json_blocks = parse_sony_json_blocks(json_data)
        all_incoming.extend(json_blocks)
        print(f"SonyLiv_data.json থেকে পাওয়া গেছে: {len(json_blocks)} টি ব্লক")
    except Exception as e:
        print(f"SonyLiv_data.json লোড করতে সমস্যা: {e}")

    try:
        sony_m3u_text = fetch_text(SONY_M3U_URL)
        sony_m3u_blocks = parse_m3u_blocks(sony_m3u_text, allowed_names=None)
        all_incoming.extend(sony_m3u_blocks)
        print(f"SonyLiv.m3u থেকে পাওয়া গেছে: {len(sony_m3u_blocks)} টি ব্লক")
    except Exception as e:
        print(f"SonyLiv.m3u লোড করতে সমস্যা: {e}")

    try:
        eamin_m3u_text = fetch_text(EAMIN_M3U_URL)
        eamin_blocks = parse_m3u_blocks(eamin_m3u_text, allowed_names=EAMIN_TARGET_SET)
        all_incoming.extend(eamin_blocks)
        print(f"eamin-tv.m3u থেকে বাছাইকৃত চ্যানেল পাওয়া গেছে: {len(eamin_blocks)} টি")
    except Exception as e:
        print(f"eamin-tv.m3u লোড করতে সমস্যা: {e}")

    if os.path.exists(TARGET_M3U_PATH):
        with open(TARGET_M3U_PATH, "r", encoding="utf-8") as f:
            existing_text = f.read()
    else:
        existing_text = ""

    final_text, added_count, updated_count = sync_all_blocks(existing_text, all_incoming)

    if added_count == 0 and updated_count == 0 and os.path.exists(TARGET_M3U_PATH):
        print("কোনো নতুন চ্যানেল বা লিংক/টোকেন পরিবর্তনের প্রয়োজন হয়নি।")
        return

    with open(TARGET_M3U_PATH, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"নতুন যুক্ত হয়েছে: {added_count}টি | লিংক/টোকেন আপডেট হয়েছে: {updated_count}টি")


if __name__ == "__main__":
    main()
