#!/usr/bin/env python3
"""Merge public IPTV lists into small curated live lists for 光影.

Reads lives.json (sources, groups, line priority, blacklist), fetches every
list, classifies channels into 央视 / 卫视 / 4K / 港台, merges all lines of the
same channel (ordered by host priority, blacklisted hosts dropped) and writes
FongMi txt lists:  group,#genre#  then  name,url1#url2#...
"""
import concurrent.futures as cf
import json
import os
import re
import ssl
import sys
import urllib.request
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ssl._create_default_https_context = ssl._create_unverified_context
UA = "okhttp/3.15"


def fetch(url: str, ua: str = UA, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": ua or UA})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")


def parse_list(text: str):
    """Yield (name, url) from m3u or txt (name,url#url) lists."""
    name = None
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            name = line.rsplit(",", 1)[-1].strip()
            continue
        if line.startswith("#") or line.endswith("#genre#"):
            continue
        if line.startswith("http") and name:
            yield name, line
            name = None
        elif "," in line and "http" in line:
            n, urls = line.split(",", 1)
            for u in urls.split("#"):
                u = u.strip()
                if u.startswith("http"):
                    yield n.strip(), u


CCTV_DIGITAL = ("兵器科技", "风云音乐", "怀旧剧场", "第一剧场", "风云剧场", "风云足球", "世界地理",
                "女性时尚", "央视文化精品", "文化精品", "高尔夫网球", "电视指南", "卫生健康", "央视台球", "发现之旅", "老故事")


def canon(raw: str, rules: dict):
    """Return (group, display_name) or None when the channel is not wanted."""
    n = re.sub(r"[\s　]", "", raw)
    n = re.sub(r"(?i)(ipv[46]|高清|超清|标清|hd|fhd|蓝光|频道)$", "", n)
    n = n.replace("—", "-").replace("－", "-").replace("＋", "+").strip("-·")
    n = rules.get("rename", {}).get(n, n)
    if not n or n in rules.get("drop", []):
        return None
    for g, names in (rules.get("extra_groups") or {}).items():   # explicit per-group name lists (e.g. 上海本地)
        if n in names:
            return g, n
    up = n.upper()
    m = re.match(r"^CCTV-?(\d{1,2})(\+)?(.*)$", up)
    if m:
        num, plus, rest = m.group(1), m.group(2) or "", m.group(3)
        if re.search(r"4K|8K", rest):
            return "4K", f"CCTV{num}{plus} 4K" if "4K" in rest else f"CCTV{num}{plus} 8K"
        if num == "4" and re.search(r"欧洲|美洲", rest):
            return None
        if int(num) < 1 or int(num) > 17:
            return None
        return "央视", f"CCTV{num}{plus}"
    m = re.match(r"^CCTV-?(4K|8K)", up)
    if m:
        return "4K", f"CCTV{m.group(1)}"
    if up.startswith("CGTN"):
        tail = n[4:]
        tail = {"记录": "纪录", "英语": "", "西班牙语": "西语", "阿拉伯语": "阿语"}.get(tail, tail)
        return "央视", "CGTN" + (tail if tail in ("", "纪录", "俄语", "法语", "西语", "阿语") else "")
    if up.startswith("CCTV"):
        tail = n[4:].lstrip("-")
        if tail in CCTV_DIGITAL:
            return "央视", "CCTV" + tail
        return None
    if n in CCTV_DIGITAL:                      # 央视付费频道 without the CCTV prefix (e.g. 风云足球)
        return "央视", "CCTV" + n
    if re.search(r"(?i)4K|8K", n):
        base = re.sub(r"(?i)4K|8K|-", "", n)
        if base.endswith("卫视") or base in ("广东珠江",):
            return "4K", base + ("4K" if re.search(r"(?i)4K", n) else "8K")
        return None
    for pat in rules.get("hk_tw", []):
        if re.search(pat, n):
            return "港台", n
    if n.endswith("卫视"):
        return "卫视", n
    m = re.match(r"^(中国教育|CETV)-?(\d)(台)?$", n, re.I)
    if m:
        return "卫视", f"中国教育{m.group(2)}台"
    return None


def host_rank(url: str, prio: list, low: list, black: list):
    """Lower is better: priority hosts first, unknown hosts next, low-priority hosts last."""
    host = urlparse(url).netloc
    for pat in black:
        if re.search(pat, url):
            return None
    for i, pat in enumerate(prio):
        if re.search(pat, host):
            return i
    for j, pat in enumerate(low):
        if re.search(pat, host):
            return len(prio) + 1 + j
    return len(prio)


def cctv_key(name: str):
    m = re.match(r"^CCTV(\d{1,2})(\+?)(.*)$", name)
    if m:
        return (0, int(m.group(1)), 1 if m.group(2) else 0, m.group(3))
    if name.startswith("CGTN"):
        return (1, 0, 0, name)
    return (2, 0, 0, CCTV_DIGITAL.index(name[4:]) if name[4:] in CCTV_DIGITAL else 99)


def order_key(group: str, name: str, rules: dict):
    if group == "央视":
        return cctv_key(name)
    if group == "4K":
        return (0, cctv_key(name)) if name.startswith("CCTV") else (1, sat_key(name.replace("4K", "").replace("8K", ""), rules), name)
    if group == "卫视":
        return sat_key(name, rules)
    if group == "港台":
        lst = rules.get("hk_tw_order", [])
        return (lst.index(name) if name in lst else len(lst), name)
    lst = (rules.get("extra_groups") or {}).get(group, [])      # explicit groups keep their list order
    return (lst.index(name) if name in lst else len(lst), name)


def sat_key(name: str, rules: dict):
    first = rules.get("satellite_first", [])
    rest = rules.get("satellite_order", [])
    if name in first:
        return (0, first.index(name), name)
    if name in rest:
        return (1, rest.index(name), name)
    return (2, 0, name)


def build(output: dict, recipe: dict, src_text: dict):
    rules, prio, low, black = recipe["rules"], recipe["host_priority"], recipe.get("host_priority_low", []), recipe["blacklist"]
    groups = output.get("groups") or recipe["groups"]
    chans = {}            # (group, name) -> list of (rank, order, url)
    seen = set()
    order = 0
    for sid in output["sources"]:
        text = src_text.get(sid)
        if not text:
            continue
        for raw, url in parse_list(text):
            c = canon(raw, rules)
            if not c or c[0] not in groups or url in seen or ";" in url:
                continue
            rank = host_rank(url, prio, low, black)
            if rank is None:
                continue
            seen.add(url)
            order += 1
            chans.setdefault(c, []).append((rank, order, url))
    lines = []
    total = 0
    for g in groups:
        items = sorted((k for k in chans if k[0] == g), key=lambda k: order_key(g, k[1], rules))
        if not items:
            continue
        lines.append(f"{g},#genre#")
        for k in items:
            urls = [u for _, _, u in sorted(chans[k])][: recipe.get("max_lines", 8)]
            lines.append(f"{k[1]},{'#'.join(urls)}")
            total += 1
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n", total, {g: sum(1 for k in chans if k[0] == g) for g in groups}


def main():
    recipe = json.load(open(os.path.join(HERE, "lives.json"), encoding="utf-8"))
    out_dir = os.path.join(HERE, "live")
    os.makedirs(out_dir, exist_ok=True)
    src_text = {}
    def local(s):                              # committed copy of a list, used when there is no url or the fetch fails
        p = os.path.join(HERE, s["file"])
        return open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    for s in recipe["sources"]:
        if s.get("file") and not s.get("url"):
            src_text[s["id"]] = local(s)
            print(f"{s['id']:12s} {'local ' + str(len(src_text[s['id']])) + ' bytes' if src_text[s['id']] else 'local file missing, skipped'}")
    with cf.ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(fetch, s["url"], s.get("ua", UA)): s for s in recipe["sources"] if s.get("url")}
        for f in cf.as_completed(futs):
            s = futs[f]
            try:
                src_text[s["id"]] = f.result()
                print(f"{s['id']:12s} ok  {len(src_text[s['id']])} bytes")
            except Exception as e:  # noqa: BLE001
                fb = local(s) if s.get("file") else None
                src_text[s["id"]] = fb
                print(f"{s['id']:12s} FAIL {e}" + (f" -> fallback file {len(fb)} bytes" if fb else ""))
    changed = False
    for out in recipe["outputs"]:
        path = os.path.join(out_dir, out["file"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not any(src_text.get(s) for s in out["sources"]):
            print(f"{out['file']}: all sources failed, keeping previous file")
            continue
        text, total, per = build(out, recipe, src_text)
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if text != old:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            changed = True
        print(f"{out['file']}: {total} channels {per}{' (changed)' if text != old else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
