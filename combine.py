import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

SOURCE_M3U_URL = (
    "https://raw.githubusercontent.com/bushmr263-ship-it/"
    "sm-eamin-playlists/refs/heads/main/playlists/eamin-tv.m3u"
)
TARGET_M3U_PATH = "combined.m3u"

TARGET_CHANNELS = [
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


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


TARGET_NAME_SET = {normalize_name(n) for n in TARGET_CHANNELS}


def extract_channel_name(extinf: str) -> str:
    tvg_match = re.search(r'tvg-name="([^"]*)"', extinf)
    if tvg_match and tvg_match.group(1).strip():
        return tvg_match.group(1).strip()
    if "," in extinf:
        return extinf.split(",")[-1].strip()
    return ""


def fetch_m3u_text(url: str) -> str:
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    return resp.text


def parse_m3u_blocks(m3u_text: str) -> list[dict]:
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
                name = extract_channel_name(extinf)
                blocks.append({
                    "name": name,
                    "norm_name": normalize_name(name),
                    "extinf": extinf,
                    "extras": extras,
                    "url": stream_url,
                    "raw": "\n".join([extinf] + extras + [stream_url]),
                })
            i = j + 1
        else:
            i += 1

    return blocks


def rebuild_m3u_with_updates(existing_text: str, selected_updates: dict[str, dict]) -> tuple[str, int, int]:
    """
    existing_text থেকে চ্যানেল ব্লকগুলো পড়ে:
    - নাম মিলে গেলে এবং লিংক/ব্লক বদলালে নতুন ব্লক দিয়ে আপডেট করে।
    - নতুন চ্যানেল হলে শেষে যুক্ত করে।
    রিটার্ন করে: (updated_text, added_count, updated_count)
    """
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
                name = extract_channel_name(extinf)
                existing_blocks.append({
                    "name": name,
                    "norm_name": normalize_name(name),
                    "extinf": extinf,
                    "extras": extras,
                    "url": stream_url,
                    "raw": "\n".join([extinf] + extras + [stream_url]),
                })
            i = j + 1
        else:
            i += 1

    seen_norms = set()
    output_blocks = []
    added_count = 0
    updated_count = 0

    for blk in existing_blocks:
        nn = blk["norm_name"]
        if nn in selected_updates:
            new_blk = selected_updates[nn]
            if blk["url"] != new_blk["url"] or blk["raw"] != new_blk["raw"]:
                output_blocks.append(new_blk["raw"])
                updated_count += 1
            else:
                output_blocks.append(blk["raw"])
            seen_norms.add(nn)
        else:
            output_blocks.append(blk["raw"])

    for nn, new_blk in selected_updates.items():
        if nn not in seen_norms:
            output_blocks.append(new_blk["raw"])
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
    source_text = fetch_m3u_text(SOURCE_M3U_URL)
    source_blocks = parse_m3u_blocks(source_text)

    selected_updates = {}
    for blk in source_blocks:
        if blk["norm_name"] in TARGET_NAME_SET:
            selected_updates[blk["norm_name"]] = blk

    if os.path.exists(TARGET_M3U_PATH):
        with open(TARGET_M3U_PATH, "r", encoding="utf-8") as f:
            existing_text = f.read()
    else:
        existing_text = ""

    final_text, added_count, updated_count = rebuild_m3u_with_updates(
        existing_text, selected_updates
    )

    if added_count == 0 and updated_count == 0 and os.path.exists(TARGET_M3U_PATH):
        print("কোনো নতুন চ্যানেল বা লিংক পরিবর্তনের প্রয়োজন হয়নি।")
        return

    with open(TARGET_M3U_PATH, "w", encoding="utf-8") as f:
        f.write(final_text)

    print(f"নতুন যুক্ত হয়েছে: {added_count}টি | লিংক/তথ্য আপডেট হয়েছে: {updated_count}টি")


if __name__ == "__main__":
    main()
