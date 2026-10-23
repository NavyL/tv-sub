#!/usr/bin/env python3
"""Mirror several TVBox/FongMi subscriptions into this repo.

For every source in sources.json:
  1. try its URLs in order (Chinese domains are punycoded automatically)
  2. unwrap the response: UTF-8 BOM, "image + ** + base64" wrapper,
     leading // comments, trailing HTML garbage, raw control characters
  3. make relative paths (./fty.jar, ./x.js) absolute against the source URL,
     because the file will be served from a different host
  4. write output/<id>.json; a failed source keeps its previous file
Then write multi.json (多仓订阅: one entry per source, 多仓 sources nested),
tv.json (= 饭太硬, kept for the original subscription URL) and status.json.

Usage: python sync.py [--base URL] [--out DIR]
  --base  public URL prefix of this repo, default jsDelivr for $GITHUB_REPOSITORY
Exit code 0 when at least one source succeeded, 2 when all failed.
"""
import argparse, base64, datetime, json, os, re, sys, urllib.parse, urllib.request

UA = "okhttp/3.15"
HERE = os.path.dirname(os.path.abspath(__file__))
URL_FIELDS = ("spider", "wallpaper", "logo")
SITE_FIELDS = ("api", "ext", "jar")


def punycode(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    host = p.hostname.encode("idna").decode("ascii")
    if p.port:
        host += f":{p.port}"
    return urllib.parse.urlunsplit((p.scheme, host, p.path or "/", p.query, p.fragment))


def fetch(url: str, timeout=30) -> bytes:
    req = urllib.request.Request(punycode(url), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def unwrap(raw: bytes) -> str:
    """Return the config text, stripping image/base64 wrappers."""
    if raw[:2] == b"\xff\xd8" or raw[:3] == b"GIF" or raw[:4] == b"\x89PNG":
        i = raw.find(b"**")
        if i < 0:
            raise ValueError("image without ** marker")
        raw = base64.b64decode(re.sub(rb"[^A-Za-z0-9+/=]", b"", raw[i + 2:]) + b"==")
    text = raw.decode("utf-8-sig", "replace").replace("\r\n", "\n")
    if not text.lstrip().startswith(("{", "[", "/")):
        # plain base64 (possibly after a ** marker)
        b = text.split("**", 1)[-1]
        text = base64.b64decode(re.sub(r"[^A-Za-z0-9+/=]", "", b) + "==").decode("utf-8-sig", "replace")
    return text


def parse(text: str) -> dict:
    t = re.sub(r"^\s*//.*$", "", text, flags=re.M)          # full-line comments
    t = re.sub(r",\s*([\]}])", r"\1", t)                     # trailing commas
    start = t.find("{")
    if start < 0:
        raise ValueError("no JSON object found")
    obj, _ = json.JSONDecoder(strict=False).raw_decode(t[start:])   # ignores trailing garbage
    if not isinstance(obj, dict) or not any(k in obj for k in ("sites", "urls", "lives", "spider")):
        raise ValueError("not a TVBox config")
    return obj


def is_relative(v) -> bool:
    return isinstance(v, str) and (v.startswith(("./", "../")) or (v.startswith("/") and not v.startswith("//")))


def absolutize(cfg: dict, base_url: str) -> dict:
    """Rewrite ./x paths so they still resolve when served from another host."""
    def fix(v):
        if is_relative(v):
            url, sep, md5 = v.partition(";md5;")
            return urllib.parse.urljoin(base_url, url) + sep + md5
        return v
    for k in URL_FIELDS:
        if k in cfg:
            cfg[k] = fix(cfg[k])
    for s in cfg.get("sites", []) or []:
        for k in SITE_FIELDS:
            if k in s:
                s[k] = fix(s[k])
    for l in cfg.get("lives", []) or []:
        if "url" in l:
            l["url"] = fix(l["url"])
    for u in cfg.get("urls", []) or []:
        if "url" in u:
            u["url"] = fix(u["url"])
    return cfg


def load_source(src: dict):
    """Return (cfg, used_url) or raise with the last error."""
    err = None
    for url in src["urls"]:
        try:
            cfg = parse(unwrap(fetch(url)))
            return absolutize(cfg, punycode(url)), url
        except Exception as e:  # noqa: BLE001
            err = f"{url}: {type(e).__name__}: {str(e)[:80]}"
            print(f"  {src['id']}: {err}", file=sys.stderr)
    raise RuntimeError(err or "no urls")


def write_if_changed(path: str, data: str) -> bool:
    if os.path.exists(path) and open(path, encoding="utf-8").read() == data:
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)
    return True


def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def main():
    ap = argparse.ArgumentParser()
    repo = os.environ.get("GITHUB_REPOSITORY", "NavyL/tv-sub")
    ap.add_argument("--base", default=os.environ.get("BASE_URL") or f"https://cdn.jsdelivr.net/gh/{repo}@main")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    base = a.base.rstrip("/")
    out_dir = os.path.join(a.out, "output")
    os.makedirs(out_dir, exist_ok=True)

    sources = json.load(open(os.path.join(HERE, "sources.json"), encoding="utf-8"))["sources"]
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    status, multi, changed, ok = {"updated": now, "sources": {}}, [], False, 0

    for src in sources:
        sid, path = src["id"], os.path.join(out_dir, f"{src['id']}.json")
        try:
            cfg, used = load_source(src)
            changed |= write_if_changed(path, dump(cfg))
            info = {"ok": True, "url": used, "sites": len(cfg.get("sites", []) or []),
                    "lives": len(cfg.get("lives", []) or []), "urls": len(cfg.get("urls", []) or [])}
            ok += 1
        except Exception as e:  # noqa: BLE001
            cfg = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
            info = {"ok": False, "error": str(e)[:160], "cached": cfg is not None}
        status["sources"][sid] = info
        print(f"{sid:12} {'ok ' if info['ok'] else 'ERR'} {info}")
        if cfg is not None:   # 多仓 sources nest: FongMi opens them as a second-level list
            multi.append({"name": src["name"], "url": f"{base}/output/{sid}.json"})

    changed |= write_if_changed(os.path.join(a.out, "multi.json"), dump({"urls": multi}))
    fty = os.path.join(out_dir, "fantaiying.json")
    if os.path.exists(fty):
        changed |= write_if_changed(os.path.join(a.out, "tv.json"), open(fty, encoding="utf-8").read())
    write_if_changed(os.path.join(a.out, "status.json"), dump(status))
    print(f"ok={ok}/{len(sources)} multi_entries={len(multi)} changed={changed}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
