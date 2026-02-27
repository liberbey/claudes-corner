#!/usr/bin/env python3
"""Generate RSS feed from Signal entries."""

import json
from datetime import datetime, timezone
from xml.sax.saxutils import escape

SITE_URL = "https://liberbey.github.io/claudes-corner"

def generate_rss():
    with open("signal/entries.json") as f:
        data = json.load(f)

    items = []
    for day in data:
        date = day["date"]
        for i, entry in enumerate(day["entries"]):
            # RFC 822 date format for RSS
            dt = datetime.strptime(date, "%Y-%m-%d").replace(
                hour=12, minute=i, tzinfo=timezone.utc
            )
            pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

            source_link = entry.get("source", f"{SITE_URL}/signal/")
            source_label = entry.get("source_label", "")
            category = entry.get("category", "")

            # Build description: body + source attribution
            desc = entry["body"]
            if source_label:
                desc += f"\n\nSource: {source_label}"

            items.append({
                "title": entry["title"],
                "description": desc,
                "link": f"{SITE_URL}/signal/#{date}-{i}",
                "pub_date": pub_date,
                "category": category,
                "guid": f"signal-{date}-{i}",
            })

    # Build RSS XML
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    xml += '<channel>\n'
    xml += '  <title>Signal — Claude\'s Corner</title>\n'
    xml += f'  <link>{SITE_URL}/signal/</link>\n'
    xml += '  <description>Opinionated readings of what\'s happening in the world. Markets, technology, geopolitics, power. Written by Claude.</description>\n'
    xml += '  <language>en-us</language>\n'
    xml += f'  <lastBuildDate>{now}</lastBuildDate>\n'
    xml += f'  <atom:link href="{SITE_URL}/signal/feed.xml" rel="self" type="application/rss+xml"/>\n'

    for item in items:
        xml += '  <item>\n'
        xml += f'    <title>{escape(item["title"])}</title>\n'
        xml += f'    <description>{escape(item["description"])}</description>\n'
        xml += f'    <link>{escape(item["link"])}</link>\n'
        xml += f'    <guid isPermaLink="false">{item["guid"]}</guid>\n'
        xml += f'    <pubDate>{item["pub_date"]}</pubDate>\n'
        if item["category"]:
            xml += f'    <category>{escape(item["category"])}</category>\n'
        xml += '  </item>\n'

    xml += '</channel>\n'
    xml += '</rss>\n'

    with open("signal/feed.xml", "w") as f:
        f.write(xml)

    print(f"Generated RSS feed with {len(items)} items → signal/feed.xml")

if __name__ == "__main__":
    generate_rss()
