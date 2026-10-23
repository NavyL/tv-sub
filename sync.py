#!/usr/bin/env python3
"""Mirror the 饭太硬 TVBox subscription into this repo.

Steps:
  1. fetch http://www.饭太硬.cc/tv (a JPEG with "**<base64>" appended)
  2. strip the image, base64-decode -> config JSON text
  3. download the spider jar, verify md5, save as spider_<md5>.jar
  4. keep the upstream spider URL unless --spider-base is given (then the
     field points at <spider-base>/spider_<md5>.jar, e.g. a GitHub Pages site;
     jsDelivr refuses to serve .jar files, so the jar is not routed through it)
  5. write tv.json (and the clean JSON) only if something changed

Usage: python sync.py [--spider-base URL] [--out DIR]
Exit code 0 = ok (changed or unchanged), 2 = source unreachable (keep old files).
"""
import argparse, base64, glob, hashlib, json, os, re, sys, urllib.request

SRC = "http://www.xn--sss604efuw.cc/tv"          # www.饭太硬.cc
UA = "okhttp/3.15"


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def unwrap(raw: bytes) -> str:
    """Return the config text hidden after the '**' marker, or the raw text if plain."""
    if raw.lstrip().startswith(b"{"):
        return raw.decode("utf-8")
    i = raw.find(b"**")
    if i < 0:
        raise ValueError("no '**' marker in response, format changed?")
    b64 = re.sub(rb"[^A-Za-z0-9+/=]", b"", raw[i + 2:])
    return base64.b64decode(b64 + b"=" * (-len(b64) % 4)).decode("utf-8").replace("\r\n", "\n")


def to_json(text: str) -> dict:
    t = re.sub(r"^\s*//.*$", "", text, flags=re.M)
    t = re.sub(r",\s*([\]}])", r"\1", t)
    return json.loads(t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spider-base", default=os.environ.get("SPIDER_BASE", ""),
                    help="base URL for the mirrored jar; empty keeps the upstream URL")
    ap.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    try:
        raw = fetch(SRC)
        text = unwrap(raw)
        cfg = to_json(text)
    except Exception as e:
        print(f"source fetch failed, keeping previous files: {e}", file=sys.stderr)
        return 2

    spider = cfg.get("spider", "")
    jar_url, _, want_md5 = spider.partition(";md5;")
    if not jar_url:
        print("config has no spider url", file=sys.stderr)
        return 2

    try:
        jar = fetch(jar_url, timeout=120)
    except Exception as e:
        print(f"jar fetch failed, keeping previous files: {e}", file=sys.stderr)
        return 2
    md5 = hashlib.md5(jar).hexdigest()
    if want_md5 and md5 != want_md5:
        print(f"jar md5 mismatch: got {md5}, config says {want_md5}; aborting", file=sys.stderr)
        return 2
    if jar[:2] != b"PK":
        print("jar is not a zip, aborting", file=sys.stderr)
        return 2

    jar_name = f"spider_{md5}.jar"
    jar_path = os.path.join(a.out, jar_name)
    if not os.path.exists(jar_path):
        with open(jar_path, "wb") as f:
            f.write(jar)
        print(f"saved {jar_name} ({len(jar)} bytes)")
    # keep the newest two jars so a stale cached tv.json still resolves
    old = sorted(glob.glob(os.path.join(a.out, "spider_*.jar")), key=os.path.getmtime)
    for p in old[:-2]:
        os.remove(p)
        print(f"removed {os.path.basename(p)}")

    base = a.spider_base.rstrip("/")
    new_spider = f"{base}/{jar_name};md5;{md5}" if base else spider
    # rewrite only the spider value, keep author's comments/layout intact
    out_text, n = re.subn(r'("spider"\s*:\s*")[^"]*(")', lambda m: m.group(1) + new_spider + m.group(2), text, count=1)
    if n != 1:
        print("could not locate spider field in text", file=sys.stderr)
        return 2
    cfg["spider"] = new_spider

    changed = False
    for name, data in (("tv.json", out_text), ("tv.clean.json", json.dumps(cfg, ensure_ascii=False, indent=1))):
        p = os.path.join(a.out, name)
        if not os.path.exists(p) or open(p, encoding="utf-8").read() != data:
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(data)
            changed = True
            print(f"updated {name}")
    print(f"sites={len(cfg.get('sites', []))} lives={len(cfg.get('lives', []))} spider={jar_name} changed={changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
