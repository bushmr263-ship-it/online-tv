import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

# ১. আপনার সোর্স M3U লিংক (অথবা লোকাল/রিমোট সোর্স)
SOURCE_M3U_URL = "https://raw.githubusercontent.com/your-username/your-repo/main/indian_hindi.m3u"

# ২. যে ফাইলে চ্যানেলগুলো অটোমেটিক যুক্ত হবে (যেমন: combined.m3u)
TARGET_M3U_PATH = "combined.m3u"


def fetch_m3u_text(url: str) -> str:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_m3u_entries(m3u_text: str):
    """
    প্রতিটি #EXTINF ব্লকের সাথে #EXTVLCOPT (যদি থাকে) এবং স্ট্রিম URL আলাদা করে রিটার্ন করে।
    """
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


def get_existing_urls(target_text: str) -> set:
    urls = set()
    for line in target_text.splitlines():
        s = line.strip()
        if re.match(r"^https?://", s, re.IGNORECASE):
            urls.add(s)
    return urls


def update_channel_count_header(content: str, added_count: int) -> str:
    match = re.search(r"(#\s*Channels Count:\s*)(\d+)", content)
    if match:
        current_count = int(match.group(2))
        new_count = current_count + added_count
        content = re.sub(
            r"(#\s*Channels Count:\s*)\d+",
            rf"\g<1>{new_count}",
            content,
            count=1,
        )

    bd_time = datetime.now(ZoneInfo("Asia/Dhaka")).strftime("%Y-%m-%d %H:%M:%S")
    content = re.sub(
        r"(#\s*Last Updated:\s*).*",
        rf"\g<1>{bd_time} (BD Time)",
        content,
        count=1,
    )
    return content


def main():
    source_text = fetch_m3u_text(SOURCE_M3U_URL)
    new_entries = parse_m3u_entries(source_text)

    if os.path.exists(TARGET_M3U_PATH):
        with open(TARGET_M3U_PATH, "r", encoding="utf-8") as f:
            target_content = f.read()
    else:
        target_content = "#EXTM3U\n"

    existing_urls = get_existing_urls(target_content)
    blocks_to_add = []

    for entry in new_entries:
        if entry["url"] not in existing_urls:
            block_lines = [entry["extinf"]] + entry["extras"] + [entry["url"]]
            blocks_to_add.append("\n".join(block_lines))
            existing_urls.add(entry["url"])

    if not blocks_to_add:
        print("কোনো নতুন চ্যানেল যুক্ত করার প্রয়োজন নেই (সবগুলো আগে থেকেই আছে)।")
        return

    if not target_content.endswith("\n"):
        target_content += "\n"

    target_content += "\n".join(blocks_to_add) + "\n"
    target_content = update_channel_count_header(target_content, len(blocks_to_add))

    with open(TARGET_M3U_PATH, "w", encoding="utf-8") as f:
        f.write(target_content)

    print(f"সফলভাবে {len(blocks_to_add)} টি চ্যানেল {TARGET_M3U_PATH} ফাইলে যুক্ত করা হয়েছে।")


if __name__ == "__main__":
    main()
