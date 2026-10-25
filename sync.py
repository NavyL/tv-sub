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


def norm_name(n) -> str:
    return re.sub(r"[^0-9a-z一-鿿]", "", str(n).lower())


def find_site(sites, name: str):
    """Exact normalized match first, then a unique substring match."""
    want = norm_name(name)
    exact = [s for s in sites if norm_name(s.get("name")) == want]
    if exact:
        return exact[0]
    part = [s for s in sites if want in norm_name(s.get("name"))]
    return part[0] if len(part) == 1 else None


NAME_SEPARATORS = "┃|丨｜[]()（）【】<>/:：、,，"


def clean_name(name: str, opts: dict) -> str:
    """'🍅┃番茄┃APP' -> '番茄', '👽玩偶哥哥┃4K弹幕' -> '玩偶哥哥 · 4K弹幕'.
    Emoji and decoration go, tokens in opts['drop'] go, the first token is the
    name and the rest become one tag after opts['separator']."""
    text = re.sub(f"[{re.escape(NAME_SEPARATORS)}]", " ", str(name))
    text = re.sub(r"[^0-9A-Za-z一-鿿 ]", "", text)        # strips emoji, VS16, ZWJ …
    drop = {t.lower() for t in opts.get("drop", [])}
    tokens = [t for t in text.split() if t.lower() not in drop]
    if not tokens:
        return str(name)
    head, tags = tokens[0], [t for t in tokens[1:] if t not in tokens[0]]
    sep = opts.get("separator", " · ")
    return head + (sep + " ".join(tags) if tags else "")


def build_curated(cfgs: dict, picks: dict, source_names: dict = None):
    """Base source's sites (minus exclude) + picked sites from other sources,
    each picked site carrying its own source's jar. Returns (cfg, warnings)."""
    warnings, source_names = [], source_names or {}
    base = cfgs.get(picks["base"])
    if base is None:
        return None, [f"base source {picks['base']} unavailable"]
    cfg = {k: v for k, v in base.items() if k != "sites"}
    if picks.get("base_names"):   # explicit keep-list for the base source, in list order
        sites = []
        for name in picks["base_names"]:
            s = find_site(base["sites"], name)
            if s is None:
                warnings.append(f"{picks['base']}: no unique site matches '{name}'")
            elif all(s is not t for t in sites):
                sites.append(dict(s))
    else:                         # legacy: everything minus exclude
        excl = {norm_name(n) for n in picks.get("exclude", [])}
        sites = [dict(s) for s in base["sites"] if norm_name(s.get("name")) not in excl]
    seen = {norm_name(s.get("name")) for s in sites}
    for group in picks.get("picks", []):
        sid, src = group["source"], cfgs.get(group["source"])
        if src is None:
            warnings.append(f"{sid}: source unavailable, its picks skipped")
            continue
        jar = src.get("spider", "")
        for name in group["names"]:
            s = find_site(src.get("sites", []), name)
            if s is None:
                warnings.append(f"{sid}: no unique site matches '{name}'")
                continue
            if norm_name(s.get("name")) in seen:
                continue
            s = dict(s)
            s["key"] = f"{sid}_{s.get('key', norm_name(name))}"
            if str(s.get("api", "")).startswith("csp_") and jar and not s.get("jar"):
                s["jar"] = jar
            sites.append(s)
            seen.add(norm_name(s.get("name")))
    name_opts = picks.get("names")
    if name_opts is not None:
        sep, rename, used = name_opts.get("separator", " · "), name_opts.get("rename", {}), set()
        for s in sites:
            n = clean_name(s.get("name", ""), name_opts)
            n = rename.get(n, n)
            if n in used:   # same cleaned name from another source: tag it with the source
                sid = str(s.get("key", "")).split("_", 1)[0]
                n = f"{n}{sep}{source_names.get(sid) or source_names.get(picks['base'], picks['base'])}"
            used.add(n)
            s["name"] = n
    if picks.get("order"):   # group order by (cleaned) name; unlisted sites keep their order at the end
        by_name, ordered = {s["name"]: s for s in sites}, []
        for group in picks["order"]:
            for n in group.get("names", []):
                s = by_name.pop(n, None)
                if s is None:
                    warnings.append(f"order/{group.get('group')}: no site named '{n}'")
                else:
                    ordered.append(s)
        leftovers = [s for s in sites if s["name"] in by_name]
        for s in leftovers:
            warnings.append(f"order: '{s['name']}' not listed, placed at the end")
        sites = ordered + leftovers
    cfg["sites"] = sites
    live_opts = picks.get("lives", {})
    if live_opts.get("merge"):
        lives, urls, names = [], set(), set()
        excl = {norm_name(n) for n in live_opts.get("exclude", [])}
        for sid in [picks["base"]] + [g["source"] for g in picks.get("picks", [])]:
            for l in (cfgs.get(sid) or {}).get("lives", []) or []:
                u, n = l.get("url", ""), l.get("name", "")
                if not u.startswith("http") or u in urls or norm_name(n) in excl:
                    continue
                if live_opts.get("skip_local") and "127.0.0.1" in u:
                    continue
                if norm_name(n) in names:          # same name, other URL: keep the first
                    continue
                urls.add(u)
                names.add(norm_name(n))
                l = dict(l)
                if live_opts.get("prefix") and sid != picks["base"]:
                    sep = (picks.get("names") or {}).get("separator", " · ")
                    l["name"] = f"{source_names.get(sid, sid)}{sep}{n}"
                lives.append(l)
        cfg["lives"] = lives
    return cfg, warnings


def render_status(status: dict, sources: list) -> str:
    ok = sum(1 for s in status["sources"].values() if s.get("ok"))
    lines = [f"> 🔄 最近变化：{status['updated']}（北京时间） · 本次成功 **{ok}/{len(sources)}** 个源", "",
             "| id | 配置源 | 状态 | 站点 | 直播 | 本次使用的地址 |", "| --- | --- | --- | --- | --- | --- |"]
    for src in sources:
        info = status["sources"].get(src["id"], {})
        if info.get("ok"):
            kind = "多仓" if info.get("urls") and not info.get("sites") else ""
            sites = f"{info.get('urls')} 个子源" if kind else str(info.get("sites", 0))
            lines.append(f"| {src['id']} | {src['name']} | ✅ 正常 | {sites} | {info.get('lives', 0)} | `{info.get('url', '')}` |")
        elif info.get("cached"):
            lines.append(f"| {src['id']} | {src['name']} | 📦 缓存 | | | 本次未抓到，沿用上次成功的文件 |")
        else:
            err = str(info.get("error", "")).split(": ", 1)[-1][:60]
            lines.append(f"| {src['id']} | {src['name']} | ❌ 失败 | | | {err} |")
    return "\n".join(lines)


def render_curated(curated: dict, picks: dict, status: dict) -> str:
    sites, lives = curated.get("sites", []), curated.get("lives", [])
    by_name = {s["name"]: s for s in sites}
    lines = [f"`best.json` 当前 **{len(sites)}** 个站点、**{len(lives)}** 个直播源，按类型分块：", "",
             "| 分块 | 数量 | 站点 |", "| --- | --- | --- |"]
    for g in picks.get("order", []):
        names = [n for n in g.get("names", []) if n in by_name]
        lines.append(f"| {g.get('group')} | {len(names)} | {'，'.join(names)} |")
    warns = status.get("curated", {}).get("warnings", [])
    if warns:
        lines += ["", "配方里有需要处理的条目：", ""] + [f"- {w}" for w in warns]
    return "\n".join(lines)


def update_readme(path: str, blocks: dict) -> bool:
    """Replace <!-- X_START --> … <!-- X_END --> blocks. The STATUS block's first
    line is a timestamp; ignore it when deciding whether anything changed, so a
    run that found nothing new leaves README alone."""
    if not os.path.exists(path):
        return False
    text = new = open(path, encoding="utf-8").read()
    for key, body in blocks.items():
        new = re.sub(rf"(<!-- {key}_START -->\n).*?(<!-- {key}_END -->)", lambda m: m.group(1) + body + "\n" + m.group(2), new, flags=re.S)
    strip = lambda t: re.sub(r"> 🔄 最近变化：.*", "", t)
    if strip(new) == strip(text):
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    return True


def shield(label: str, message: str, color: str) -> str:
    return dump({"schemaVersion": 1, "label": label, "message": message, "color": color})


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
    status, multi, changed, ok, cfgs = {"updated": now, "sources": {}}, [], False, 0, {}

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
            cfgs[sid] = cfg
            multi.append({"name": src["name"], "url": f"{base}/output/{sid}.json"})

    picks_path = os.path.join(HERE, "picks.json")
    if os.path.exists(picks_path):
        curated, warns = build_curated(cfgs, json.load(open(picks_path, encoding="utf-8")),
                                       {s["id"]: s["name"] for s in sources})
        status["curated"] = {"sites": len(curated["sites"]) if curated else 0, "warnings": warns}
        for w in warns:
            print(f"  curated: {w}", file=sys.stderr)
        if curated:
            changed |= write_if_changed(os.path.join(a.out, "best.json"), dump(curated))
            multi.insert(0, {"name": "精选", "url": f"{base}/best.json"})

    changed |= write_if_changed(os.path.join(a.out, "multi.json"), dump({"urls": multi}))
    fty = os.path.join(out_dir, "fantaiying.json")
    if os.path.exists(fty):
        changed |= write_if_changed(os.path.join(a.out, "tv.json"), open(fty, encoding="utf-8").read())
    write_if_changed(os.path.join(a.out, "status.json"), dump(status))

    # README status blocks and badges (only rewritten when their content changes)
    blocks = {"STATUS": render_status(status, sources)}
    if os.path.exists(picks_path) and os.path.exists(os.path.join(a.out, "best.json")):
        picks = json.load(open(picks_path, encoding="utf-8"))
        curated_cfg = json.load(open(os.path.join(a.out, "best.json"), encoding="utf-8"))
        blocks["CURATED"] = render_curated(curated_cfg, picks, status)
        n_sites, n_lives = len(curated_cfg.get("sites", [])), len(curated_cfg.get("lives", []))
        changed |= write_if_changed(os.path.join(a.out, "shield-best.json"),
                                    shield("精选", f"{n_sites} 站点 · {n_lives} 直播", "blue"))
    changed |= update_readme(os.path.join(a.out, "README.md"), blocks)
    color = "brightgreen" if ok == len(sources) else "yellow" if ok else "red"
    changed |= write_if_changed(os.path.join(a.out, "shield.json"), shield("配置源", f"{ok}/{len(sources)} 可用", color))
    print(f"ok={ok}/{len(sources)} multi_entries={len(multi)} changed={changed}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
