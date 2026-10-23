# tv-sub

Self-hosted mirror of a TVBox/FongMi subscription. A GitHub Actions job runs
`sync.py` every 6 hours: it fetches the upstream config, strips the image
wrapper, downloads the spider jar, and rewrites the jar URL to this repo
served through jsDelivr.

Subscription URL (choose any jsDelivr edge):

```
https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/tv.json
https://fastly.jsdelivr.net/gh/NavyL/tv-sub@main/tv.json
https://gcore.jsdelivr.net/gh/NavyL/tv-sub@main/tv.json
```

Files:

- `tv.json` – upstream config text with only the `spider` field rewritten
- `tv.clean.json` – same config, comments stripped, strict JSON
- `spider_<md5>.jar` – spider jar, named by md5 so CDN caches never go stale
- `sync.py` – the sync script, also runnable locally: `python sync.py`
