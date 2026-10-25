#!/usr/bin/env python3
"""Build epg.xml.gz for the live lists: XMLTV keyed by OUR channel names.

Sources (first match wins per channel): fanmingming/live e.xml (7 days), 老张 51zmt e.xml (2 days).
Channel names in live/*.txt are matched against source channel ids / display-names after
normalisation (strip 高清/HD/频道, "XX卫视4K" -> "XX卫视", "CCTV兵器科技" -> "兵器科技", 凤凰卫视 -> 凤凰, CETV -> 中国教育).
Output: live/epg.xml.gz (not committed; the workflow builds it on every run and publishes it on Pages).
"""
import datetime
import glob
import gzip
import os
import re
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ssl._create_default_https_context = ssl._create_unverified_context
SOURCES = [
    "https://raw.githubusercontent.com/fanmingming/live/main/e.xml",
    "http://epg.51zmt.top:8000/e.xml",
]
DAYS_BACK, DAYS_AHEAD = 1, 3


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "okhttp/3.15"})
    data = urllib.request.urlopen(req, timeout=60).read()
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


def norm(s):
    s = re.sub(r"[\s\-－—_·]|高清|HD|频道", "", s).upper()
    s = re.sub(r"卫视4K$|4K$", lambda m: "卫视" if m.group(0) == "卫视4K" else "", s)
    return s.replace("凤凰卫视", "凤凰").replace("CETV", "中国教育").replace("中国教育台", "中国教育")


def keys_for(name):
    ks = [norm(name)]
    if name.startswith("CCTV") and not re.match(r"CCTV\d", name):
        ks.append(norm(name[4:]))               # CCTV兵器科技 -> 兵器科技
    if name.endswith("4K"):
        ks.append(norm(name[:-2]))
    return ks


def our_names():
    names = []
    for f in sorted(glob.glob(os.path.join(HERE, "live", "*.txt"))):
        for line in open(f, encoding="utf-8"):
            if "," in line and not line.rstrip().endswith("#genre#"):
                n = line.split(",", 1)[0]
                if n not in names:
                    names.append(n)
    return names


def main():
    names = our_names()
    index = {}            # normalised name -> (source order, channel id, root)
    roots = []
    for i, url in enumerate(SOURCES):
        try:
            root = ET.fromstring(fetch(url))
        except Exception as e:  # noqa: BLE001
            print(f"{url}: FAIL {e}")
            continue
        roots.append(root)
        n = 0
        for ch in root.findall("channel"):
            cid = ch.get("id")
            for label in [cid] + [d.text or "" for d in ch.findall("display-name")]:
                index.setdefault(norm(label), (i, cid, root))
            n += 1
        print(f"{url}: {n} channels, {len(root.findall('programme'))} programmes")
    if not roots:
        print("no EPG source reachable")
        return 1
    today = datetime.date.today()
    lo = (today - datetime.timedelta(days=DAYS_BACK)).strftime("%Y%m%d")
    hi = (today + datetime.timedelta(days=DAYS_AHEAD + 1)).strftime("%Y%m%d")
    out = ET.Element("tv", {"generator-info-name": "tv-sub epg.py"})
    matched, programmes = 0, 0
    by_source = {}
    for root in roots:
        for p in root.findall("programme"):
            by_source.setdefault((id(root), p.get("channel")), []).append(p)
    for name in names:
        hit = next((index[k] for k in keys_for(name) if k in index), None)
        if not hit:
            continue
        _, cid, root = hit
        ch = ET.SubElement(out, "channel", {"id": name})
        ET.SubElement(ch, "display-name", {"lang": "zh"}).text = name
        matched += 1
        for p in by_source.get((id(root), cid), []):
            day = p.get("start", "")[:8]
            if not (lo <= day < hi):
                continue
            q = ET.SubElement(out, "programme", {"start": p.get("start"), "stop": p.get("stop", ""), "channel": name})
            t = p.find("title")
            ET.SubElement(q, "title", {"lang": "zh"}).text = (t.text if t is not None else "") or ""
            programmes += 1
    missing = [n for n in names if not any(k in index for k in keys_for(n))]
    path = os.path.join(HERE, "live", "epg.xml.gz")
    data = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(out, encoding="utf-8")
    with gzip.open(path, "wb") as f:
        f.write(data)
    print(f"epg.xml.gz: {matched}/{len(names)} channels, {programmes} programmes, {os.path.getsize(path)//1024} KB gz; no EPG for: {' '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
