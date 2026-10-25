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
| **精选单仓（推荐）** | `https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/best.json` | 一个列表用全部，名称统一，按类型分块 |
| 多仓订阅 | `https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/multi.json` | App 内可在精选和各源之间切换 |
| 饭太硬原版 | `https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/tv.json` | 与原站内容一致，只换了地址 |
| 单个源 | `https://cdn.jsdelivr.net/gh/NavyL/tv-sub@main/output/<id>.json` | `<id>` 见下方状态表 |

`cdn.jsdelivr.net` 不通时可换成 `fastly.jsdelivr.net` 或 `gcore.jsdelivr.net`，路径相同。

> jsDelivr 对 `@main` 分支地址有缓存，推送后最长 24 小时才会换成新内容。想立刻拿到最新版，可以用按提交固定的地址 `…/gh/NavyL/tv-sub@<commit>/best.json`。

## 二、源可用性状态

<!-- STATUS_START -->
> 🔄 最近变化：2026-10-25 14:32（北京时间） · 本次成功 **9/9** 个源

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
`best.json` 当前 **33** 个站点、**6** 个直播源，按类型分块：

| 分块 | 数量 | 站点 |
| --- | --- | --- |
| 影视 | 18 | 豆豆 · 片单，厂长，立播，瓜子，糯米，文采，奶酪，热播，茉莉，独播，伊影，伯伯，咕噜，干饭，再来，火火，360，量子 |
| 外剧 | 2 | 韩剧，韩圈 |
| 网盘 | 9 | 玩偶哥哥 · 4K弹幕，花卷 · 4K，观影 · 4K，聚剧 · 四盘，盘搜 · 四盘，易搜 · 四盘，盘她 · 夸父，盘他 · 嘟嘟，新6V · 磁力 |
| 其他 | 2 | 巴士 · 动漫，八八 · 看球 |
| 工具 | 2 | 我的云盘 · 配置，手机 · 推送 |
<!-- CURATED_END -->

精选的配方在 `picks.json`：

- `base`：底本来源。给了 `base_names` 时只保留名单里的站点（按名单顺序）；否则全部保留（`exclude` 列出的除外）。
- `picks`：按来源列出要补进来的站点名。名字在去掉表情和符号后做匹配，所以写 `"一起看"` 就能找到 `🌎一起看`。补进来的站点自动带上来源自己的 jar，不同作者的站点才能在一个列表里共存。
- `names`：统一命名规则。去掉表情和符号，丢掉 `drop` 里的宣传词（不卡、秒播、多线……），第一个词是名称，其余作为标签接在 `separator` 后面；`rename` 做个别手动改名；清洗后重名的站点自动带上来源名。
- `overrides`：按统一后的站点名覆盖字段，例如把搜索很慢的站标成 `searchable: 0`。
- `order`：分块顺序，每块列出站点名。没列到的站点排在最后，并在 `status.json` 的 `curated.warnings` 里提示。
- `lives`：直播源按 URL 合并去重，`exclude` 按名字剔除，非底本来源的加上"来源 · "前缀。

要删站、改名或调顺序，改 `picks.json` 推送即可，工作流会自动重新生成。

## 四、仓库结构

```
tv-sub/
├── .github/workflows/sync.yml   # 定时同步工作流
├── sources.json                 # 配置源列表（主地址 + 备用地址）
├── picks.json                   # 精选单仓配方
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
- 修改 `sources.json`、`picks.json` 或 `sync.py` 并推送时会立即运行一次。
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
python sync.py            # 抓取并生成全部产物
python check.py best.json # 体检精选单仓
```

## 七、常见问题

- **spider jar 为什么不镜像？** jsDelivr 拒绝提供 `.jar` 文件，所以 `spider` 字段保留各作者自己的 jar 地址（相对路径已转成绝对地址）。
- **某些站点打开是空的？** 网盘类站点（我的云盘、玩偶哥哥、盘搜、易搜等）依赖本机的网盘 token 文件，需要先在「我的云盘 · 配置」里登录夸克或阿里云盘。
- **讴歌为什么没有？** 它的接口对任何来源都返回 403，GitHub 的服务器也拉不到，已从源列表移除。
- **精选里为什么没有某个源的站点？** 要么在其他源里已有同名站点，要么 `check.py` 检查时它的 jar 或接口已失效。`picks.json` 里的 `_removed` 字段记录了删除原因。
