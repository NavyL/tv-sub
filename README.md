# tv-sub

Self-hosted mirror of a TVBox/FongMi subscription. A GitHub Actions job runs
`sync.py` every 6 hours: it fetches the upstream config, strips the image
wrapper, and keeps a copy of the spider jar in the repo. The `spider` field
keeps the upstream jar URL by default, because jsDelivr does not serve `.jar`
files. To serve the jar from this repo instead, enable GitHub Pages on `main`
and set the repository variable `SPIDER_BASE` to
`https://navyl.github.io/tv-sub`.

Subscription URL (choose any jsDelivr edge):

```
https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/tv.json
https://fastly.jsdelivr.net/gh/NavyL/tv-sub@main/tv.json
https://gcore.jsdelivr.net/gh/NavyL/tv-sub@main/tv.json
```

Files:

- `tv.json` – upstream config text with only the `spider` field rewritten
- `tv.clean.json` – same config, comments stripped, strict JSON
- `spider_<md5>.jar` – backup copy of the spider jar, named by md5
- `sync.py` – the sync script, also runnable locally: `python sync.py`
