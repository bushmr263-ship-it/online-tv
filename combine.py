import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

# Kaynak M3U raw URL'si (18 kanallı liste veya ilgili .m3u raw adresi)
SOURCE_M3U_URL = "https://raw.githubusercontent.com/bushmr263-ship-it/sm-eamin-playlists/refs/heads/main/playlists/eamin-tv.m3u"

# Hedef dosya: online-tv deposundaki combined.m3u
TARGET_M3U_PATH = "combined.m3u"


def fetch_m3u_text(url: str) -> str:
    response = requests.get(url, timeout=25)
    response.raise_for_status()
    return response.text


def parse_m3u_entries(m3u_text: str) -> list[dict]:
    lines = [line.strip() for line in m3u_text.splitlines() if line.strip()]
    entries = []
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
                entries.append({
                    "extinf": extinf,
                    "extras": extras,
                    "url": stream_url,
                })
            i = j + 1
        else:
            i += 1

    return entries


def get_existing_urls(target_text: str) -> set[str]:
    urls = set()
    for line in target_text.splitlines():
        clean = line.strip()
        if re.match(r"^https?://", clean, re.IGNORECASE):
            urls.add(clean)
    return urls


def update_header_metadata(content: str, added_count: int) -> str:
    count_match = re.search(r"(#\s*Channels Count:\s*)(\d+)", content)
    if count_match:
        current_count = int(count_match.group(2))
        new_count = current_count + added_count
        content = re.sub(
            r"(#\s*Channels Count:\s*)\d+",
            rf"\g<1>{new_count}",
            content,
            count=1,
        )

    bd_now = datetime.now(ZoneInfo("Asia/Dhaka")).strftime("%Y-%m-%d %H:%M:%S")
    if re.search(r"#\s*Last Updated:\s*", content):
        content = re.sub(
            r"(#\s*Last Updated:\s*).*",
            rf"\g<1>{bd_now} (BD Time)",
            content,
            count=1,
        )
    return content


def main() -> None:
    source_text = fetch_m3u_text(SOURCE_M3U_URL)
    new_entries = parse_m3u_entries(source_text)

    if os.path.exists(TARGET_M3U_PATH):
        with open(TARGET_M3U_PATH, "r", encoding="utf-8") as f:
            target_content = f.read()
    else:
        bd_now = datetime.now(ZoneInfo("Asia/Dhaka")).strftime("%Y-%m-%d %H:%M:%S")
        target_content = (
            "#EXTM3U\n"
            "# ==========================================\n"
            "# Developed by: Shawon\n"
            "# Telegram: https://t.me/+VqDOF_-beaQyMWY1\n"
            f"# Last Updated: {bd_now} (BD Time)\n"
            "# Channels Count: 0\n"
            "# ==========================================\n\n"
        )

    existing_urls = get_existing_urls(target_content)
    blocks_to_add = []

    for entry in new_entries:
        if entry["url"] not in existing_urls:
            block_lines = [entry["extinf"]] + entry["extras"] + [entry["url"]]
            blocks_to_add.append("\n".join(block_lines))
            existing_urls.add(entry["url"])

    if not blocks_to_add:
        print("Eklenecek yeni kanal bulunamadı.")
        return

    if not target_content.endswith("\n"):
        target_content += "\n"

    target_content += "\n".join(blocks_to_add) + "\n"
    target_content = update_header_metadata(target_content, len(blocks_to_add))

    with open(TARGET_M3U_PATH, "w", encoding="utf-8") as f:
        f.write(target_content)

    print(f"{len(blocks_to_add)} kanal {TARGET_M3U_PATH} dosyasına eklendi.")


if __name__ == "__main__":
    main()
