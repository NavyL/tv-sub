# tv-sub

Self-hosted mirror of several TVBox / FongMi subscriptions. A GitHub Actions
job runs `sync.py` every 6 hours: it fetches each upstream config listed in
`sources.json`, strips whatever wrapper the author used (image + base64,
BOM, `//` comments, trailing HTML), makes relative jar/js paths absolute, and
commits the result here so the TV can read it from jsDelivr even when the
upstream domains are blocked.

## Subscription URLs

| Use | URL |
| --- | --- |
| 精选单仓 (curated: 饭太硬 + picked sites from the other sources) | `https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/best.json` |
| 多仓订阅 (all sources, switch inside the app; 精选 is the first entry) | `https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/multi.json` |
| 饭太硬 only (original URL, unchanged) | `https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/tv.json` |
| single source | `https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/output/<id>.json` |

`cdn.jsdelivr.net` can be swapped for `fastly.jsdelivr.net` or
`gcore.jsdelivr.net` with the same path. Note that jsDelivr caches `@main`
for up to 24 hours after a push.

## Sources

Edit `sources.json` to add or remove a source. Each entry has an `id` (output
file name), a `name` (shown in the 多仓 list) and `urls` tried in order.
Current status after each run is in `status.json`.

| id | name | upstream |
| --- | --- | --- |
| fantaiying | 饭太硬 | `http://www.饭太硬.cc/tv` |
| feimao | 肥猫 | `http://肥猫.net/tv` |
| wangerxiao | 王二小 | `https://9280.kstore.vip/newwex.json` |
| laoliubei | 老刘备 | `https://raw.liucn.cc/box/m.json` |
| xiaoma | 小马 | `https://szyyds.cn/tv/x.json` |
| 4k | 4K小盒子 | `http://xhztv.top/4k.json` |
| xiaohezi | 小盒子 | `http://xhztv.top/xhz` |
| shiguang | 拾光多仓 | `http://xmbjm.fh4u.org/dc.txt` |
| tinghao | 挺好分享多仓 | `http://ztha.top/TVBox/GYCK.json` |

Spider jars are not mirrored: jsDelivr refuses to serve `.jar` files, so the
`spider` field keeps each author's own jar URL (made absolute where it was
relative). A source that fails to fetch keeps its previous file.

## Curated single config

`best.json` is built from `picks.json`: every site of the `base` source
(minus `exclude`), plus the sites named under `picks` for each other source.
Names are matched after stripping emoji and punctuation, so `"一起看"` finds
`🌎一起看`. A picked site gets a `jar` field pointing at its own source's
spider, so sites from different authors can live in one list. Lives from all
involved sources are merged by URL (local 127.0.0.1 proxies skipped). To
tune it, edit the names in `picks.json` and push; unmatched names are listed
under `curated.warnings` in `status.json`.

## Files

- `best.json` – 精选单仓 built from `picks.json`
- `multi.json` – 多仓订阅 index pointing at `output/*.json`
- `tv.json` – copy of `output/fantaiying.json`, kept for the original URL
- `output/<id>.json` – one clean JSON per source
- `status.json` – result of the last run (which URL worked, site counts, errors)
- `sources.json` – the source list
- `sync.py` – the sync script, also runnable locally: `python sync.py`
