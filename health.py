#!/usr/bin/env python3
"""China-side line health for the probed live lists (lives.json outputs with "probe": true).

Runs on the Tencent Cloud Shanghai server every 3 hours (systemd timer tvsub-probe, see
/opt/tvsub-probe/README.md on the server). Each run probes the same candidate lines lives.py
would probe, but from inside China and with speed measured (whole newest segment downloaded),
appends the results to a rolling history, and publishes health.json: per URL the number of
samples in the window, how many played, and the median download/real-time ratio.
lives.py on GitHub Actions reads health.json (lives.json "health") to rank lines.

  python3 health.py --state DIR [--push git@github.com:OWNER/REPO.git]

--push force-pushes a single orphan commit with health.json to the branch probe-data, so main
does not collect a commit every run.
"""
import argparse
import concurrent.futures as cf
import json
import os
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lives  # noqa: E402

WINDOW_H = 24          # samples older than this are dropped
FORGET_H = 72          # URLs not probed for this long are forgotten
BRANCH = "probe-data"


def fetch_sources(recipe: dict, ids: set):
    out = {}
    srcs = [s for s in recipe["sources"] if s["id"] in ids]
    with cf.ThreadPoolExecutor(8) as ex:
        futs = {ex.submit(lives.fetch, s["url"], s.get("ua", lives.UA)): s for s in srcs if s.get("url")}
        for f in cf.as_completed(futs):
            s = futs[f]
            try:
                out[s["id"]] = f.result()
            except Exception as e:  # noqa: BLE001
                print(f"{s['id']}: fetch failed ({e})")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True, help="directory for history.json and the data checkout")
    ap.add_argument("--push", help="git remote to force-push health.json to (branch probe-data)")
    ap.add_argument("--vantage", default="tencent-cloud-shanghai")
    a = ap.parse_args()
    os.makedirs(a.state, exist_ok=True)

    recipe = json.load(open(os.path.join(HERE, "lives.json"), encoding="utf-8"))
    outputs = [o for o in recipe["outputs"] if o.get("probe")]
    cpath = os.path.join(HERE, "live", "candidates.json")
    if os.path.exists(cpath):
        # written by lives.py on Actions and pulled with the repo: exactly the lines lives.py ranks
        cand = [u for o in outputs for u in json.load(open(cpath, encoding="utf-8")).get(o["file"], [])]
        print(f"candidates: {len(cand)} from live/candidates.json")
    else:
        ids = {s for o in outputs for s in o["sources"]}
        src_text = fetch_sources(recipe, ids)
        missing = sorted(i for i in ids if i not in src_text and any(s["id"] == i and s.get("url") for s in recipe["sources"]))
        if missing:
            print(f"sources not fetched: {missing}; not publishing a partial result")
            return 1
        cand = []
        for o in outputs:
            cand += lives.candidates(lives.collect(o, recipe, src_text), o, recipe)
    cand = list(dict.fromkeys(cand))
    if not cand:
        print("no candidates; nothing to do")
        return 1
    t0 = time.time()
    res = lives.probe_all(cand, recipe.get("probe", {}), measure=True)
    now = int(time.time())

    hist_path = os.path.join(a.state, "history.json")
    try:
        hist = json.load(open(hist_path, encoding="utf-8"))
    except (OSError, ValueError):
        hist = {}
    for u, (st, why, ratio) in res.items():
        hist.setdefault(u, []).append([now, 1 if st == lives.OK else 0, ratio, why])
    for u in list(hist):
        hist[u] = [s for s in hist[u] if now - s[0] <= WINDOW_H * 3600]
        if not hist[u] or now - hist[u][-1][0] > FORGET_H * 3600:
            del hist[u]
    tmp = hist_path + ".tmp"
    json.dump(hist, open(tmp, "w", encoding="utf-8"))
    os.replace(tmp, hist_path)

    urls = {}
    for u in cand:
        s = hist.get(u, [])
        ratios = [x[2] for x in s if x[1] and x[2] is not None]
        urls[u] = {"n": len(s), "ok": sum(x[1] for x in s),
                   "ratio": round(statistics.median(ratios), 2) if ratios else None,
                   "last": s[-1][3] if s else None}
    health = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)), "generated_ts": now,
              "vantage": a.vantage, "window_hours": WINDOW_H, "urls": urls}
    ok = sum(1 for r in res.values() if r[0] == lives.OK)
    print(f"probed {len(res)} lines in {time.time() - t0:.0f}s: {ok} played; history {len(hist)} urls")

    if a.push:
        push(a.state, a.push, health)
    else:
        json.dump(health, open(os.path.join(a.state, "health.json"), "w", encoding="utf-8"), ensure_ascii=False)


def push(state: str, remote: str, health: dict):
    repo = os.path.join(state, "data")
    git = lambda *args, **kw: subprocess.run(
        ["git", "-c", "user.name=tvsub-probe", "-c", "user.email=tvsub-probe@users.noreply.github.com", *args],
        cwd=repo, check=True, capture_output=True, text=True, **kw).stdout.strip()
    if not os.path.isdir(os.path.join(repo, ".git")):
        os.makedirs(repo, exist_ok=True)
        git("init", "-q")
    with open(os.path.join(repo, "health.json"), "w", encoding="utf-8") as f:
        json.dump(health, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as f:
        f.write("# probe-data\n\nGenerated by health.py on the China-side prober; force-pushed as a single commit every run. "
                "Do not commit here by hand. lives.py reads health.json from this branch.\n")
    git("add", "-A")
    tree = git("write-tree")
    commit = git("commit-tree", tree, "-m", f"health {health['generated']}")
    git("push", "-q", "-f", remote, f"{commit}:refs/heads/{BRANCH}")
    git("gc", "-q", "--prune=now")
    print(f"pushed {commit[:7]} to {BRANCH}")


if __name__ == "__main__":
    sys.exit(main())
