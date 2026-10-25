# tv-sub · 自建影视订阅镜像

![配置源状态](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FNavyL%2Ftv-sub%2Fmain%2Fshield.json)
![精选站点](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FNavyL%2Ftv-sub%2Fmain%2Fshield-best.json)
![更新频率](https://img.shields.io/badge/%E8%87%AA%E5%8A%A8%E6%9B%B4%E6%96%B0-%E6%AF%8F%206%20%E5%B0%8F%E6%97%B6-blue)
![同步状态](https://github.com/NavyL/tv-sub/actions/workflows/sync.yml/badge.svg)

把 **饭太硬、肥猫、王二小、老刘备、小马、小盒子、拾光多仓、挺好分享多仓** 等公开的 TVBox / FongMi 单仓配置镜像到本仓库，由 **GitHub Actions 每 6 小时自动抓取**，通过 jsDelivr 分发。原站域名被运营商屏蔽时，电视端仍然能拿到最新配置。

在镜像之外还生成一份 **精选单仓** `best.json`：以饭太硬为底，从其他源挑选不重复、能用的站点合并成一个列表，站点名统一成"名称 · 标签"格式并按类型分块排列。

> 所有配置均来自互联网公开分享，版权归原作者所有；本仓库仅做镜像与整理，仅供学习交流，请勿商用。

---

## 一、订阅地址

把下面任一地址填入 FongMi / 影视仓 / TVBox 的「设置 → 点播」：

| 类型 | 地址 | 说明 |
| --- | --- | --- |
| **精选单仓（推荐）** | `https://navyl.github.io/tv-sub/best.json` | 一个列表用全部，名称统一，按类型分块；GitHub Pages，更新后 10 分钟内生效 |
| 多仓订阅 | `https://navyl.github.io/tv-sub/multi.json` | App 内可在精选和各源之间切换 |
| 饭太硬原版 | `https://navyl.github.io/tv-sub/tv.json` | 与原站内容一致，只换了地址 |
| 单个源 | `https://navyl.github.io/tv-sub/output/<id>.json` | `<id>` 见下方状态表 |
| 备用（jsDelivr） | `https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/best.json` 等，路径同上 | `github.io` 不通时用；分支缓存最长 24 小时才刷新 |

jsDelivr 的 `cdn.jsdelivr.net` 不通时可换成 `fastly.jsdelivr.net` 或 `gcore.jsdelivr.net`，路径相同。想立刻拿到某个提交的内容，可以用按提交固定的地址 `…/gh/NavyL/tv-sub@<commit>/best.json`。

## 二、源可用性状态

<!-- STATUS_START -->
> 🔄 最近变化：2026-10-25 18:59（北京时间） · 本次成功 **9/9** 个源

| id | 配置源 | 状态 | 站点 | 直播 | 本次使用的地址 |
| --- | --- | --- | --- | --- | --- |
| fantaiying | 饭太硬 | ✅ 正常 | 49 | 6 | `http://www.饭太硬.cc/tv` |
| feimao | 肥猫 | ✅ 正常 | 40 | 1 | `http://肥猫.net/tv` |
| wangerxiao | 王二小 | ✅ 正常 | 99 | 2 | `https://9280.kstore.vip/newwex.json` |
| laoliubei | 老刘备 | ✅ 正常 | 234 | 3 | `https://raw.liucn.cc/box/m.json` |
| xiaoma | 小马 | ✅ 正常 | 62 | 10 | `https://szyyds.cn/tv/x.json` |
| 4k | 4K小盒子 | ✅ 正常 | 53 | 2 | `http://xhztv.top/4k.json` |
| xiaohezi | 小盒子 | ✅ 正常 | 54 | 1 | `http://xhztv.top/xhz` |
| shiguang | 拾光多仓 | ✅ 正常 | 54 个子源 | 0 | `http://xmbjm.fh4u.org/dc.txt` |
| tinghao | 挺好分享多仓 | ✅ 正常 | 32 个子源 | 0 | `http://ztha.top/TVBox/GYCK.json` |
<!-- STATUS_END -->

状态说明：✅ 本次抓取成功；📦 本次没抓到，沿用上一次成功的文件；❌ 失败且没有缓存。机器可读版本在 `status.json`。

## 三、精选单仓

<!-- CURATED_START -->
`best.json` 当前 **33** 个站点、**4** 个直播源，按类型分块：

| 分块 | 数量 | 站点 |
| --- | --- | --- |
| 影视 | 18 | 豆豆 · 片单，玩偶哥哥 · 4K，奶酪，瓜子，伊影，独播，茉莉，糯米，热播，咕噜，伯伯，文采，干饭，再来，厂长，火火，360，量子 |
| 外剧 | 2 | 韩剧，韩圈 |
| 网盘 | 8 | 花卷 · 4K，观影 · 4K，聚剧 · 四盘，盘她 · 夸父，易搜 · 四盘，盘搜 · 四盘，盘他 · 嘟嘟，新6V · 磁力 |
| 其他 | 2 | 巴士 · 动漫，八八 · 看球 |
| 工具 | 3 | 我的云盘 · 配置，王二小网盘登录，手机 · 推送 |
<!-- CURATED_END -->

精选的配方在 `picks.json`：

- `base`：底本来源。给了 `base_names` 时只保留名单里的站点（按名单顺序）；否则全部保留（`exclude` 列出的除外）。
- `picks`：按来源列出要补进来的站点名。名字在去掉表情和符号后做匹配，所以写 `"一起看"` 就能找到 `🌎一起看`。补进来的站点自动带上来源自己的 jar，不同作者的站点才能在一个列表里共存。
- `names`：统一命名规则。去掉表情和符号，丢掉 `drop` 里的宣传词（不卡、秒播、多线……），第一个词是名称，其余作为标签接在 `separator` 后面；`rename` 做个别手动改名；清洗后重名的站点自动带上来源名。
- `drop_keys`：从底本配置里去掉的顶层字段（去掉了饭太硬的 `wallpaper`）。
- `wallpaper`：用仓库里 `wallpaper/` 下的图片（光影自带的四张）作为壁纸，按日期轮换，地址指向 Pages。
- `overrides`：按统一后的站点名覆盖字段，例如把搜索很慢的站标成 `searchable: 0`。
- `order`：分块顺序，每块列出站点名。没列到的站点排在最后，并在 `status.json` 的 `curated.warnings` 里提示。
- `lives`：直播源不再直接引用各家的直播条目（`only_extra: true`），而是用 `lives.py` 按 `lives.json` 生成三份精简列表（`live/*.txt`，FongMi txt 格式，同一频道多条线路）：
  - `上海联通 · IPTV`：运营商 IPTV 单播流（`live/shlt-source.m3u` 加 hxchtiewei/sh-iptv 的第二套 token 作备用线路，10.223.x.x 内网地址），无广告、全高清带 4K，只有上海联通宽带能播。分组：央视 / 卫视 / 4K / 上海 / 影视少儿。
  - `光影 · 直播`：合并 综合直播、Kimentanm、ssili126、vbskycn，只留 央视 / 卫视 / 4K / 港台 四组，线路按 `host_priority` 排序，`blacklist` 里插广告的中转直接丢掉。
  - `光影 · 移动IPv6`：fanmingming 的北京移动 IPv6 组播转发，只在移动宽带下能播。
  - `江苏移动 · IPTV`：江苏移动 OTT 列表（`live/jsyd-source.m3u`，ott.mobaibox.com），同样只在移动宽带下能播。
  所有直播条目都带台标和节目单：台标镜像在仓库 `logo/`（来自 cicivi/jsyd-iptv 与 fanmingming/live，按频道名取 `logo/{name}.png`），节目单主用仓库自己生成的 `live/epg.xml.gz`（`epg.py` 把 fanmingming、51zmt 的 xmltv 按我们的频道名重排，每次工作流运行重建并发到 Pages，不入库），51zmt 的接口做兜底；两者在 `epg` 字段里用逗号并列，FongMi 先用 xml 再查接口。

要删站、改名或调顺序，改 `picks.json` 推送即可，工作流会自动重新生成。

## 四、仓库结构

```
tv-sub/
├── .github/workflows/sync.yml   # 定时同步工作流
├── sources.json                 # 配置源列表（主地址 + 备用地址）
├── picks.json                   # 精选单仓配方
├── lives.json / lives.py        # 直播列表配方与生成脚本 → live/*.txt
├── epg.py                       # 节目单：生成 live/epg.xml.gz（只发 Pages）
├── sync.py                      # 抓取 → 解包 → 整理 → 落盘 → 更新 README
├── check.py                     # 静态体检：jar、直播源、站点地址
├── best.json                    # 精选单仓
├── multi.json                   # 多仓订阅索引
├── tv.json                      # 饭太硬原版（output/fantaiying.json 的副本）
├── status.json                  # 最近一次运行的结果
├── shield.json / shield-best.json  # 徽章数据
└── output/<id>.json             # 各源独立配置
```

## 五、自动更新机制

- 工作流每 6 小时运行一次（UTC 0:17 / 6:17 / 12:17 / 18:17），也可以在 Actions 页面手动触发。
- 修改 `sources.json`、`picks.json`、`lives.json`、`sync.py` 或 `lives.py` 并推送时会立即运行一次。
- 只有产物内容真正变化时才提交，`status.json` 里的时间戳不算，避免无意义的提交。
- 提交后自动请求 jsDelivr 清缓存（对 `@main` 的效果有限，见上文）。
- 工作流使用内置 `GITHUB_TOKEN`，不需要配置任何密钥。

## 六、脚本做了什么

`sync.py` 对每个源依次尝试主地址和备用地址，中文域名自动转 punycode，然后处理各家不同的"壳"：

- 饭太硬那种 **JPEG 图片 + `**` + base64** 的隐藏格式
- UTF-8 BOM、顶部 `//` 注释、JSON 后面拖着的 HTML、未转义的控制字符
- `./fty.jar` 这类相对路径转成绝对地址，换了托管位置后 jar 和 js 仍能找到

某个源抓不到时保留上一次的文件，不会把订阅弄空。

`check.py` 可以本地跑：下载每个 jar 核对 md5，拉取每个直播源数频道，探测站点的 js / 采集 / ext 地址，列出重名站点和依赖本机 token 文件的站点。它跑不了爬虫本身，所以通过检查的站仍可能播不了，但没通过的基本可以断定已失效。

```bash
python lives.py           # 生成直播列表 live/*.txt
python epg.py             # 生成节目单 live/epg.xml.gz
python sync.py            # 抓取并生成全部产物
python check.py best.json # 体检精选单仓
```

## 七、常见问题

- **spider jar 为什么不镜像？** jsDelivr 拒绝提供 `.jar` 文件，所以 `spider` 字段保留各作者自己的 jar 地址（相对路径已转成绝对地址）。
- **某些站点打开是空的？** 网盘类站点（我的云盘、玩偶哥哥、盘搜、易搜等）依赖本机的网盘 token 文件，需要先在「我的云盘 · 配置」里登录夸克或阿里云盘。
- **讴歌为什么没有？** 它的接口对任何来源都返回 403，GitHub 的服务器也拉不到，已从源列表移除。
- **精选里为什么没有某个源的站点？** 要么在其他源里已有同名站点，要么 `check.py` 检查时它的 jar 或接口已失效。`picks.json` 里的 `_removed` 字段记录了删除原因。
- **直播换了四五个台之后就卡住，退出等一会儿又好？** 不是源的问题，是节目单地址不通。FongMi 每次换台都会去拉该频道的节目单，`epg.112114.xyz` 在部分家庭网络会被 DNS 污染（解析到国外地址），连接要 30 秒才超时；FongMi 的 EPG 任务和取流任务共用一个 5 线程的任务池，EPG 任务超时后线程仍被占着，四五次换台后池子就满了，新频道的取流任务排不上队，直到旧的超时释放。本仓库的直播条目已改用 `epg.51zmt.top`；自己写配置时务必给 `epg` 一个能连通的地址，或者干脆不写。
