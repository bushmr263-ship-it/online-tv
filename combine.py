from datetime import datetime, timezone, timedelta
import requests

try:
    from zoneinfo import ZoneInfo
    BD_TZ = ZoneInfo("Asia/Dhaka")
except Exception:
    BD_TZ = timezone(timedelta(hours=6))

SOURCES = [
    "https://raw.githubusercontent.com/bushmr263-ship-it/SonyLiv_Event_Playlist/refs/heads/main/SonyLiv.m3u",
    "https://raw.githubusercontent.com/bushmr263-ship-it/Toffee-IPTV/refs/heads/main/Toffee.m3u",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def parse_m3u(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    entries = []
    current_extinf = None
    current_opts = []

    for line in lines:
        if line == "#EXTM3U":
            continue
        if line.startswith("#EXTINF:"):
            current_extinf = line
            current_opts = []
        elif line.startswith("#EXTVLCOPT:") or line.startswith("#EXTHTTP:"):
            current_opts.append(line)
        elif not line.startswith("#"):
            if current_extinf:
                entries.append((current_extinf, current_opts.copy(), line))
                current_extinf = None
                current_opts = []
    return entries


def main():
    seen_urls = set()
    all_entries = []

    for url in SOURCES:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            for extinf, opts, stream_url in parse_m3u(resp.text):
                if stream_url not in seen_urls:
                    seen_urls.add(stream_url)
                    all_entries.append((extinf, opts, stream_url))
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

    bd_now = datetime.now(BD_TZ).strftime("%Y-%m-%d %H:%M:%S")
    out = [
        "#EXTM3U",
        "# ==========================================",
        "# Developed by: Shawon",
        "# Telegram: https://t.me/+VqDOF_-beaQyMWY1",
        f"# Last Updated: {bd_now} (BD Time)",
        f"# Channels Count: {len(all_entries)}",
        "# ==========================================",
        "",
    ]

    for extinf, opts, stream_url in all_entries:
        out.append(extinf)
        out.extend(opts)
        out.append(stream_url)
        out.append("")

    with open("combined.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(out).strip() + "\n")

    print(f"Saved combined.m3u with {len(all_entries)} channels.")


if __name__ == "__main__":
    main()
