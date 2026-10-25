#!/usr/bin/env python3
"""Fetch missing channel logos for live/*.txt into logo/<name>.png (committed by the workflow).

Tries, per missing name: alias name (CCTV digital channels, CETV, 凤凰) then the name itself,
from cicivi/jsyd-iptv and fanmingming/live. Never overwrites an existing file.
"""
import glob
import os
import ssl
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ssl._create_default_https_context = ssl._create_unverified_context
TEMPLATES = [
    "https://raw.githubusercontent.com/cicivi/jsyd-iptv/main/logo/{n}.png",
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/{n}.png",
]
ALIAS = {"中国教育1台": "CETV1", "中国教育2台": "CETV2", "中国教育3台": "CETV3", "中国教育4台": "CETV4",
         "凤凰中文": "凤凰卫视中文", "凤凰资讯": "凤凰卫视资讯", "凤凰香港": "凤凰卫视香港", "卡酷卡通": "卡酷少儿",
         "早期教育": "CETV早期教育", "都市频道": "上海都市", "新闻综合": "上海新闻综合"}


def candidates(name):
    out = [ALIAS[name]] if name in ALIAS else []
    if name.startswith("CCTV") and not name[4:5].isdigit():
        out.append(name[4:])                    # CCTV兵器科技 -> 兵器科技
    if name.endswith("4K") and name[:-2].endswith("卫视"):
        out += [name, name[:-2]]
    out.append(name)
    return list(dict.fromkeys(out))


def main():
    names = set()
    for f in glob.glob(os.path.join(HERE, "live", "*.txt")):
        for line in open(f, encoding="utf-8"):
            if "," in line and not line.rstrip().endswith("#genre#"):
                names.add(line.split(",", 1)[0])
    os.makedirs(os.path.join(HERE, "logo"), exist_ok=True)
    missing = sorted(n for n in names if not os.path.exists(os.path.join(HERE, "logo", f"{n}.png")))
    got, still = [], []
    for n in missing:
        data = None
        for c in candidates(n):
            for t in TEMPLATES:
                url = t.format(n=urllib.parse.quote(c))
                try:
                    r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "okhttp/3.15"}), timeout=20)
                    if r.status == 200:
                        data = r.read()
                        break
                except Exception:  # noqa: BLE001
                    continue
            if data:
                break
        if data and data[:4] == b"\x89PNG":
            open(os.path.join(HERE, "logo", f"{n}.png"), "wb").write(data)
            got.append(n)
        else:
            still.append(n)
    print(f"logos: {len(names)} names, fetched {len(got)} new ({' '.join(got)}), still missing {len(still)}: {' '.join(still)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
