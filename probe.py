#!/usr/bin/env python3
"""Live-test every site of a config on a FongMi/光影 device through its /spider-api.

The device runs the real spider jar, so this measures what the TV will see:
  load   - jar download + class init
  home   - home(filter) → number of categories / recommended items
  cat    - category(first class id, page 1) → number of items
  search - optional search(keyword) → number of hits (--search 关键词)

Usage: python probe.py --tv 192.168.31.78 [config.json] [--search 周处除三害] [--timeout 20]
The app must be in the foreground (its web server lives in the activity) and no other
FongMi app may hold port 9978.
"""
import argparse, json, os, sys, time, urllib.request


class Api:
    def __init__(self, tv, timeout_s):
        self.base, self.tok, self.timeout_s = f"http://{tv}:9978/spider-api", "", timeout_s

    def call(self, path="", body=None, method=None, timeout=60):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method or ("POST" if data is not None else "GET"),
                                     headers={"X-Spider-Session": self.tok, "Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8", "replace") or "{}")

    def open(self):
        st, v = self.call("", {})
        if st != 200:
            raise SystemExit(f"session failed: {st} {v}")
        self.tok = v["session"]

    def close(self):
        self.call("", None, "DELETE")

    def work(self, path, body):
        """POST then poll until the device reports a terminal state. Returns (state, result, elapsed_ms)."""
        st, v = self.call(path, {**body, "timeout": self.timeout_s})
        if st != 200:
            return "http" + str(st), v.get("error", ""), 0
        t0 = time.time()
        while v.get("state") in ("loading", "running") and time.time() - t0 < self.timeout_s + 30:
            time.sleep(0.25)
            st, v = self.call("")
        return v.get("state"), v.get("result"), v.get("elapsed", 0)


def parse(result):
    if isinstance(result, str):
        try:
            return json.loads(result)
        except Exception:  # noqa: BLE001
            return None
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.json"))
    ap.add_argument("--tv", required=True)
    ap.add_argument("--search", default="")
    ap.add_argument("--timeout", type=int, default=20, help="per-call timeout on the device, seconds (1-300)")
    ap.add_argument("--only", default="", help="comma-separated site names to test")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = json.load(open(a.config, encoding="utf-8"))
    sites = cfg["sites"]
    if a.only:
        want = set(a.only.split(","))
        sites = [s for s in sites if s["name"] in want]
    api = Api(a.tv, a.timeout)
    api.open()
    rows = []
    try:
        for s in sites:
            name, jar = s["name"], s.get("jar") or cfg.get("spider", "")
            row = {"name": name, "api": s.get("api", "")}
            st, res, ms = api.work("/load", {"api": s.get("api", ""), "jar": jar, "ext": s.get("ext", "")})
            row["load"] = (st, ms)
            if st != "loaded":
                row["note"] = f"load {st}: {str(res)[:80]}"
                rows.append(row); print(f"{name:14} load FAIL {st} {str(res)[:80]}", flush=True); continue
            st, res, ms = api.work("/run", {"method": "home", "args": [True]})
            home = parse(res) or {}
            classes = home.get("class") or []
            row["home"] = (st, ms, len(classes), len(home.get("list") or []))
            first = classes[0].get("type_id") if classes else None
            if st == "done" and first is not None:
                st2, res2, ms2 = api.work("/run", {"method": "category", "args": [str(first), "1", True, {}]})
                cat = parse(res2) or {}
                row["cat"] = (st2, ms2, len(cat.get("list") or []))
            if a.search and s.get("searchable", 1):
                st3, res3, ms3 = api.work("/run", {"method": "search", "args": [a.search, False, "1"]})
                sr = parse(res3) or {}
                row["search"] = (st3, ms3, len(sr.get("list") or []))
            rows.append(row)
            h = row["home"]; c = row.get("cat"); q = row.get("search")
            print(f"{name:14} load {row['load'][1]:5}ms | home {h[0]:9} {h[1]:5}ms cls={h[2]:3} rec={h[3]:3}"
                  + (f" | cat {c[0]:9} {c[1]:5}ms n={c[2]:3}" if c else " | cat -")
                  + (f" | search {q[0]:9} {q[1]:5}ms n={q[2]:3}" if q else ""), flush=True)
    finally:
        api.close()
    out = os.path.join(os.path.dirname(os.path.abspath(a.config)), "probe.json")
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
