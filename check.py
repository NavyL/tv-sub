#!/usr/bin/env python3
"""Static health check of a TVBox config (default: best.json).

Checks what can be checked without running the spiders:
  - every jar (spider + per-site jar) downloads and matches its md5
  - every live source responds and contains channels
  - site api/ext URLs (js spiders, 采集 APIs, remote json ext) respond
  - duplicate site names, sites that need local token files

Usage: python check.py [config.json] [--timeout 20] [--workers 16]
"""
import argparse, concurrent.futures, hashlib, json, os, re, sys, urllib.parse, urllib.request

UA = "okhttp/3.15"


def encode_url(url):
    """Punycode the host and percent-encode non-ASCII path/query characters."""
    p = urllib.parse.urlsplit(url)
    host = p.hostname.encode("idna").decode("ascii") + (f":{p.port}" if p.port else "")
    return urllib.parse.urlunsplit((p.scheme, host, urllib.parse.quote(p.path, safe="/%:@"),
                                    urllib.parse.quote(p.query, safe="=&%+/:?"), ""))


def fetch(url, timeout, ua=UA, limit=4_000_000):
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"not an http url: {url[:30]}")
    req = urllib.request.Request(encode_url(url), headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(limit), r.headers.get("Content-Type", "")


def check_url(url, timeout, ua=UA):
    try:
        st, body, ct = fetch(url, timeout, ua)
        return st, body, ct, None
    except Exception as e:  # noqa: BLE001
        return None, b"", "", f"{type(e).__name__}: {str(e)[:60]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.json"))
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    sites, lives = cfg.get("sites", []), cfg.get("lives", [])
    report = {"jars": [], "lives": [], "urls": [], "dupes": [], "local": []}

    # --- jars ---
    jars = {}
    for s in [{"jar": cfg.get("spider", "")}] + sites:
        j = s.get("jar")
        if j and j not in jars:
            jars[j] = []
    for s in sites:
        if s.get("jar"):
            jars[s["jar"]].append(s.get("name"))

    def jar_task(spec):
        url, _, md5 = spec.partition(";md5;")
        st, body, ct, err = check_url(url, a.timeout * 3)
        if err:
            return spec, f"FAIL {err}"
        got = hashlib.md5(body).hexdigest()
        if body[:2] != b"PK":
            return spec, f"FAIL not a zip ({len(body)} bytes, {ct})"
        if md5 and got.lower() != md5.lower():
            return spec, f"WARN md5 mismatch (got {got[:8]}, config {md5[:8]})"
        return spec, f"ok {len(body)//1024} KB"

    # --- lives ---
    def live_task(l):
        url = l.get("url", "")
        st, body, ct, err = check_url(url, a.timeout, l.get("ua") or UA)
        if err:
            return l.get("name"), f"FAIL {err}"
        text = body.decode("utf-8", "replace")
        n = len(re.findall(r"^#EXTINF", text, flags=re.M)) or len(re.findall(r"^[^#\s].*?,\s*\S+://", text, flags=re.M))
        if n == 0 and "{" in text[:200]:
            return l.get("name"), f"WARN json/other response ({len(body)} bytes)"
        msg = f"ok {n} channels" if n else f"WARN no channels found ({len(body)} bytes, {ct[:30]})"
        for epg in str(l.get("epg", "")).split(","):          # static xmltv files (api templates with {name} are not probed)
            if epg.startswith("http") and "{" not in epg and ("xml" in epg or "gz" in epg):
                st2, body2, _, err2 = check_url(epg, a.timeout)
                msg += f"; epg {'FAIL ' + err2 if err2 else 'ok ' + str(len(body2)//1024) + ' KB'}"
        return l.get("name"), msg

    # --- site urls ---
    url_tasks = []
    for s in sites:
        api, ext = str(s.get("api", "")), s.get("ext", "")
        if api.startswith("http"):
            url_tasks.append((s.get("name"), "api", api))
        if isinstance(ext, str) and ext.startswith("http") and "127.0.0.1" not in ext:
            url_tasks.append((s.get("name"), "ext", ext))
        blob = json.dumps(s, ensure_ascii=False)
        if "127.0.0.1" in blob or "tvfan/" in blob or "file://" in blob:
            report["local"].append(s.get("name"))

    def url_task(t):
        name, kind, url = t
        st, body, ct, err = check_url(url, a.timeout)
        if err:
            return name, kind, url, f"FAIL {err}"
        if kind == "api" and s_type_api(url):
            text = body.decode("utf-8", "replace")
            if "<html" in text[:300].lower():
                return name, kind, url, "WARN html page instead of api"
        return name, kind, url, f"ok {len(body)} bytes"

    def s_type_api(url):
        return "provide/vod" in url or "api.php" in url

    with concurrent.futures.ThreadPoolExecutor(a.workers) as ex:
        report["jars"] = list(ex.map(jar_task, jars))
        report["lives"] = list(ex.map(live_task, lives))
        report["urls"] = list(ex.map(url_task, url_tasks))

    # --- dupes ---
    seen = {}
    for s in sites:
        n = re.sub(r"[^0-9a-z一-鿿]", "", str(s.get("name")).lower())
        seen.setdefault(n, []).append(s.get("name"))
    report["dupes"] = [v for v in seen.values() if len(v) > 1]

    out = sys.stdout
    out.reconfigure(encoding="utf-8")
    print(f"sites={len(sites)} lives={len(lives)} jars={len(jars)} url-checks={len(url_tasks)}\n")
    print("== jars ==")
    for spec, res in report["jars"]:
        names = jars[spec]
        print(f"  {res:40} {spec.split(';')[0][:70]}  <- {len(names)} sites" + (f" ({', '.join(str(n)[:12] for n in names[:3])}…)" if names else " (base)"))
    print("\n== lives ==")
    for name, res in report["lives"]:
        print(f"  {res:34} {name}")
    print("\n== site api/ext urls ==")
    for name, kind, url, res in sorted(report["urls"], key=lambda r: not r[3].startswith("ok")):
        print(f"  {res:40} {kind:3} {str(name)[:16]:16} {url[:70]}")
    print("\n== duplicate names ==")
    for v in report["dupes"]:
        print("  ", v)
    print("\n== sites using local token/cloud-drive files ==")
    print("  ", ", ".join(str(n) for n in report["local"]))


if __name__ == "__main__":
    main()
