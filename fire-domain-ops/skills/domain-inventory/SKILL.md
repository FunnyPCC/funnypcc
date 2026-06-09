---
name: domain-inventory
description: Use when the user wants to know which project a domain belongs to (域名属于哪个项目 / 域名归属), pull/refresh the firepikata (火种/huozhong) domain × project inventory, check whether domains are risky (Google Safe Browsing / 欺骗性网页 / phishing), check whether domains are reachable (存活/可访问), or list a project's usable domains. Also trigger on mentions of firepikata domain backend, 域名维护, 可用域名, 域名风险, 域名存活, project domain availability, or huozhong domain ops.
---

# 域名库存盘点 · 风险/存活/可用(firepikata)

从火种后台(firepikata)拉全部「项目 × 域名」,检测 Google 风险与域名存活,维护成一张主表。是「火种域名运维」工作流的**盘点+体检**阶段(其余阶段:`batch-add-gsc` 加域名到 GSC;`baota-site-mgmt` 宝塔站点)。

## 查「域名属于哪个项目」(最常见,别走弯路)

**归属的权威源是后台,不是宝塔。** `raw_domains.json` 里 `域名.appId → 项目`(`appId_dictText` 即项目编号,如 `f076`)就是答案。
- ✅ 用本 skill:`fetch_domains.py` 抓 `raw_domains.json`,按 `domain` 命中取 `appId_dictText`。一批域名也是这样一次性映射出 `域名 → fNNN`。
- ❌ **别先去宝塔**(`bt.py` / `find-site` / `sites.csv`):那只反映「已部署到面板」,大量后台已登记但**未部署**的域名在面板里 0 命中 → 误判「不属于任何项目」。宝塔只回答「这域名部署在哪台机/哪个站点」。

## 数据与输出位置

全部产出在**当前项目**的 `./域名维护/`(相对运行目录;可用 `DOMAIN_DOC_DIR` 覆盖):
- `域名项目关联.{md,csv}` — 主表,8 列:项目编号/域名/项目状态/域名状态/Google风险/可访问/可用状态/备注
- `域名风险.{md,csv}`、`域名存活.csv`、`raw_domains.json`、`raw_apps.json`
- **务必在项目根运行**脚本,否则输出到别处。

## 凭证策略(全工具箱通用)

**1Password 是源,本地是缓存。** 经 `lib/op_secrets.py` 解析,优先级:**环境变量 > 本地缓存 > 1Password**(从 1P 取出后写回缓存;失效/过期自动 `refresh` 重取)。
- 缓存默认 **全局** `~/.fire/secrets.json`(0600;跨项目复用,**不会落进业务 git 仓库泄密**);旧版 CWD 相对 `gsc/.secrets.json` 仍**只读兼容**。`DOMAIN_SECRETS` 可覆盖路径。**插件不含密钥**。
- 键:`fire_username`/`fire_password`(1P item「火苗-公共运维后管」)、`sb_api_key`(1P item「Google Maps API」字段「API Key」;GCP 项目 `324812159513` 需启用 Safe Browsing API)。
- **逃生口(op 连不上时直接绕过 1Password)**:`SB_API_KEY=...`(风险检测)、`FIRE_USER=... FIRE_PASS=...`(登录)走环境变量即可。
- op 走 1Password **桌面端**:需桌面端**已解锁** + 设置 → Developer 打开 **「Integrate with 1Password CLI」**;有本地缓存时通常不触发 op。

## 工作规则(重要)

- **指纹探针决定重拉还是用快照(取代旧的"≥1天 mtime"猜测)**:用户提域名相关任务时,先跑 `freshness_probe.py`(便宜:`fire_login.py` 缓存 token + 4 个 1 行 list 请求)拿后台"版本指纹"和本地 `.freshness.json` 比对——
  - 退出码 **0 = FRESH** → 后台没变,**直接用快照**,不重拉。
  - 退出码 **10 = STALE** → 后台有增/删/改 → 先 `rebuild_domains.sh` 再答(rebuild 末尾会刷新 marker)。
  - 退出码 **2 = token 失效** → `fire_login.py --fresh` 换 token 后重拉(或直接重拉,rebuild 自带登录)。
  指纹/表 = `(total, maxUpdate, maxCreate)`:total 抓增删、maxUpdate 抓就地编辑(已验证改状态会 bump updateTime)、maxCreate 补强新增。这比 mtime 可靠——mtime 只代表"我上次拉取时间",探针直接比后台真实状态,**用户在别处静默改的也能发现**。用户若主动说改了后台,可跳过探针直接重拉。
- **风险+存活按需现查(实时,不读快照旧值)**:列某项目「可用域名」、或用户要查风险/存活时,对相关域名**现跑** `risk_check.py` + `liveness_check.py`;**不**读 `域名风险.csv`/`域名存活.csv` 的旧值。重拉(rebuild)仍会全量刷风险写进快照,但**可用判定一律以现查为准**。
- **只查域名状态=正常**:risk/liveness 只测 `status_dictText==正常` 的;已关闭/维护中不检查。
- **可用口径** = 域名状态正常(快照) + Google无风险(**实时**) + 能打开(**实时**);列「可用域名」时按此过滤,带 `https://` 前缀。
- **答复必须标注数据来源与时效**:凡引用域名**归属 / 状态(正常/关闭)** 的结论(来自快照),注明「来自快照 + `raw_domains.json` 修改时间」;风险/存活注明为**实时现查**。注:跑过探针判 FRESH 时,快照==后台,可标「已探针校验与后台一致 @ 时间」,可信度更高。
- **关联**:`域名.appId == 项目.id` → projectCode;取不到标(未绑定项目)/(已删除项目·<id>)。

## 命令(在项目根运行)

```bash
PLUGIN="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/fire-tools/fire-domain-ops}"
# 新鲜度探针:先判要不要重拉(退出码 0=FRESH/10=STALE/2=token失效)
FIRE_TOKEN="$(uv run "$PLUGIN/skills/domain-inventory/scripts/fire_login.py")" \
  uv run "$PLUGIN/skills/domain-inventory/scripts/freshness_probe.py"
# 一键重建(自动登录→抓取→风险→合并→写 .freshness.json;不跑存活)
bash "$PLUGIN/skills/domain-inventory/scripts/rebuild_domains.sh"
# 只取 token(JWT 自带缓存,~3天内复用不过验证码;--fresh 强制重登)
uv run "$PLUGIN/skills/domain-inventory/scripts/fire_login.py"
# 风险 / 存活:不带参=全量(仅域名状态正常);带域名=只测这些
uv run "$PLUGIN/skills/domain-inventory/scripts/risk_check.py" a.com b.com
uv run "$PLUGIN/skills/domain-inventory/scripts/liveness_check.py" a.com b.com
```
> 本项目里也有 1 行壳 `gsc/rebuild_domains.sh` → 调上面的脚本,保持 `bash gsc/rebuild_domains.sh` 可用。

## 列某项目「可用域名」的标准流程

1. 先跑 `freshness_probe.py`:STALE→`rebuild_domains.sh` 再继续,FRESH→直接用快照(用户主动说改了后台则跳过探针直接重拉);**归属/状态来自快照**。
2. 从快照取该项目「域名状态=正常」的候选(状态/归属是快照值)。
3. 对候选**现跑** `risk_check.py`(实时风险,**不读** `域名风险.csv` 旧值)→ 剔除有风险的。
4. 对剩余候选**现跑** `liveness_check.py`(实时存活)→ 剔除打不开的。
5. 输出「状态正常(快照) + 实时无风险 + 实时能打开」的,带 `https://`。
6. **答复中标注**:风险/存活是**实时现查**;域名状态/归属来自**快照 + `raw_domains.json` 修改时间**,让用户自行判断要不要重拉。

## 关键事实

- **GSC 官方 API 查不到「安全问题」**(已实测,URL Inspection 无安全字段)→ 改用 **Safe Browsing API v4**(同源威胁数据)。前提:GCP 项目 `324812159513` 已启用 Safe Browsing API 且 key 放行。
- **firepikata token 约 3 天过期**,且登录带图形验证码 → `fire_login.py` 用 `ddddocr` 自动过码换 token。
- **后台「正常」≠ Google 安全 ≠ 能打开**:三者独立,主表分三列,别用一个推另一个。
- 存活检测走本机网络(开了 Clash/Surge 与浏览器一致);判死域名会降并发复测一遍除假死。
