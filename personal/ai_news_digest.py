#!/usr/bin/env python3
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime


def fetch_url(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (ai-news-bot)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="ignore")


def strip_tags(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_rss(xml_text):
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for item in root.findall(".//item"):
        title = strip_tags(item.findtext("title", "").strip())
        link = item.findtext("link", "").strip()
        desc = strip_tags(item.findtext("description", "").strip())
        pub = item.findtext("pubDate", "").strip()
        items.append(
            {
                "title": title,
                "link": link,
                "description": desc,
                "pubDate": pub,
            }
        )
    return items


def naver_rss(keyword):
    query = urllib.parse.quote(keyword)
    url = f"https://newssearch.naver.com/search.naver?where=rss&query={query}"
    xml_text = fetch_url(url)
    return parse_rss(xml_text)


def google_news_rss(keyword, hl="ko", gl="KR", ceid="KR:ko"):
    query = urllib.parse.quote(keyword)
    url = (
        "https://news.google.com/rss/search?q="
        f"{query}&hl={hl}&gl={gl}&ceid={ceid}"
    )
    xml_text = fetch_url(url)
    return parse_rss(xml_text)


def parse_date(text):
    if not text:
        return None
    try:
        return parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None


def dedupe_items(items):
    seen = set()
    out = []
    for item in items:
        key = (item.get("link") or "") + "|" + (item.get("title") or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def make_summary(title, desc, limit=140):
    if title and desc and title not in desc:
        summary = f"{title} - {desc}"
    elif title:
        summary = title
    else:
        summary = desc
    summary = summary.strip()
    if len(summary) > limit:
        summary = summary[: limit - 3].rstrip() + "..."
    return summary


def shorten_link(link, max_len):
    if not link:
        return ""
    link = link.strip()
    if len(link) <= max_len:
        return link
    return link[: max_len - 3].rstrip() + "..."


def format_link_html(link, max_len):
    if not link:
        return ""
    short = shorten_link(link, max_len)
    href = html.escape(link, quote=True)
    text = html.escape(short)
    return f'<a href="{href}">{text}</a>'


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_cache_dir(base_dir):
    cache_dir = os.path.join(base_dir, ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def load_channel_cache(cache_path):
    if not os.path.exists(cache_path):
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_channel_cache(cache_path, data):
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def resolve_channel_id(handle, cache, cache_path):
    if handle in cache:
        return cache[handle]
    url = f"https://www.youtube.com/@{handle}"
    html_text = fetch_url(url)
    match = re.search(r'"channelId":"(UC[0-9A-Za-z_-]+)"', html_text)
    if not match:
        match = re.search(
            r"https://www\.youtube\.com/channel/(UC[0-9A-Za-z_-]+)", html_text
        )
    if not match:
        return None
    channel_id = match.group(1)
    cache[handle] = channel_id
    save_channel_cache(cache_path, cache)
    return channel_id


def fetch_youtube_feed(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    xml_text = fetch_url(url)
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", default="", namespaces=ns).strip()
        link_el = entry.find("atom:link[@rel='alternate']", ns)
        link = link_el.get("href", "").strip() if link_el is not None else ""
        published = entry.findtext("atom:published", default="", namespaces=ns).strip()
        items.append(
            {
                "title": title,
                "link": link,
                "published": published,
            }
        )
    return items


def build_message(config, base_dir):
    keywords = config.get("naver_keywords", [])
    use_google = bool(config.get("use_google_news", True))
    tools = config.get("tools", [])
    people = config.get("people", [])
    popular_keywords = config.get("popular_tools_keywords", [])
    popular_use_english = bool(config.get("popular_use_english", False))
    handles = config.get("youtube_handles", [])
    youtube_links = config.get("youtube_links", [])
    max_items = int(config.get("max_items_per_tool", 2))
    max_popular = int(config.get("max_popular_items", 3))
    max_yt = int(config.get("max_youtube_items", 6))
    max_link_len = int(config.get("max_link_length", 60))
    max_chars = int(config.get("max_total_chars", 3500))

    all_items = []
    for kw in keywords:
        try:
            all_items.extend(naver_rss(kw))
        except Exception:
            continue
        if use_google:
            try:
                all_items.extend(google_news_rss(kw))
            except Exception:
                continue
    all_items = dedupe_items(all_items)
    all_items.sort(
        key=lambda x: parse_date(x.get("pubDate")) or dt.datetime.min,
        reverse=True,
    )

    items_by_tool = {t["name"]: [] for t in tools}
    people_items = []
    popular_items = []

    for item in all_items:
        text = f"{item.get('title','')} {item.get('description','')}".lower()
        for tool in tools:
            if any(kw.lower() in text for kw in tool.get("keywords", [])):
                items_by_tool[tool["name"]].append(item)
        if any(name in text for name in people):
            people_items.append(item)
        if any(kw.lower() in text for kw in popular_keywords):
            popular_items.append(item)

    if popular_use_english and popular_keywords:
        extra = []
        for kw in popular_keywords:
            try:
                extra.extend(google_news_rss(kw, hl="en", gl="US", ceid="US:en"))
            except Exception:
                continue
        if extra:
            popular_items.extend(extra)
            popular_items = dedupe_items(popular_items)
            popular_items.sort(
                key=lambda x: parse_date(x.get("pubDate")) or dt.datetime.min,
                reverse=True,
            )

    sections = []
    today = dt.datetime.now().strftime("%Y-%m-%d")
    sections.append(f"AI 업데이트 알림 ({today})")

    base_tools = {"Gemini", "ChatGPT", "Claude", "Google Antigravity"}
    for tool in tools:
        name = tool["name"]
        items = items_by_tool.get(name, [])[:max_items]
        if not items and name not in base_tools:
            continue
        lines = [f"[{name}]"]
        if not items:
            lines.append("- 오늘 관련 한국어 소식 없음.")
        else:
            for item in items:
                summary = make_summary(item.get("title", ""), item.get("description", ""))
                link = format_link_html(item.get("link", ""), max_link_len)
                lines.append(f"- {summary}")
                if link:
                    lines.append(f"  {link}")
        sections.append("\n".join(lines))

        if name == "Google Antigravity":
            lines = ["[해외 인기 AI 툴]"]
            if not popular_items:
                lines.append("- 오늘 관련 한국어 소식 없음.")
            else:
                for item in popular_items[:max_popular]:
                    summary = make_summary(item.get("title", ""), item.get("description", ""))
                    link = format_link_html(item.get("link", ""), max_link_len)
                    lines.append(f"- {summary}")
                    if link:
                        lines.append(f"  {link}")
            sections.append("\n".join(lines))

    if people_items:
        lines = ["[인물 기사]"]
        for item in people_items[:max_items]:
            summary = make_summary(item.get("title", ""), item.get("description", ""))
            link = format_link_html(item.get("link", ""), max_link_len)
            lines.append(f"- {summary}")
            if link:
                lines.append(f"  {link}")
        sections.append("\n".join(lines))

    if handles:
        cache_dir = ensure_cache_dir(base_dir)
        cache_path = os.path.join(cache_dir, "channel_ids.json")
        cache = load_channel_cache(cache_path)
        yt_items = []
        for handle in handles:
            try:
                channel_id = resolve_channel_id(handle, cache, cache_path)
                if not channel_id:
                    continue
                entries = fetch_youtube_feed(channel_id)
                if entries:
                    entry = entries[0]
                    yt_items.append(
                        {
                            "handle": handle,
                            "title": entry.get("title", ""),
                            "link": entry.get("link", ""),
                        }
                    )
            except Exception:
                continue
        if yt_items:
            lines = ["[유튜브]"]
            for item in yt_items[:max_yt]:
                title = item.get("title", "").strip()
                link = format_link_html(item.get("link", "").strip(), max_link_len)
                handle = item.get("handle", "")
                lines.append(f"- {handle}: {title}")
                if link:
                    lines.append(f"  {link}")
            sections.append("\n".join(lines))

    if youtube_links:
        lines = ["[YouTube Links]"]
        for link in youtube_links[:max_yt]:
            formatted = format_link_html(link, max_link_len)
            lines.append(f"- {formatted}" if formatted else f"- {link}")
        sections.append("\n".join(lines))

    message = "\n\n".join(sections).strip()
    if len(message) > max_chars:
        message = message[: max_chars - 20].rstrip() + "\n\n(내용 일부 생략)"
    return message


def main():
    parser = argparse.ArgumentParser(description="Build AI news digest message.")
    parser.add_argument(
        "--config",
        default="ai_news_config.json",
        help="Path to config JSON.",
    )
    args = parser.parse_args()
    base_dir = os.path.dirname(os.path.abspath(args.config))
    config = load_json(args.config)
    message = build_message(config, base_dir)
    if not message:
        sys.exit(1)
    print(message)


if __name__ == "__main__":
    main()
