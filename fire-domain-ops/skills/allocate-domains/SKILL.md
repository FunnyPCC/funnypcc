---
name: allocate-domains
description: 给某个 Fire 项目分配 N 个空域名（优先 .com），自动绑项目 + 改 IP 为项目 appIp，再联动宝塔。Use when the user says "给 007 分配 3 个新域名"、"给 007 分 5 个域名"、"给项目分配域名"、allocate N spare domains to a project.
argument-hint: <项目号> <数量N>
allowed-tools: Bash, AskUserQuestion
---

流程3：从空域名池给项目分配 N 个（优先 .com）。**不需确认、直接执行**，执行后反馈。

## 域名分配铁律（spare/allocate 默认强制，写在 app_domains.py）
- ① **只取创建 ≤6 个月**的空域名 —— 更老的可能临近过期/被风控，默认排除。
- ② 同窗口内 **优先取老的**（createTime 升序）—— 把临近过期的先用掉。
- 应急要用更老的：显式加 `--all-ages`（脚本会在提示里说明）。
- 想先看具体候选：`app_domains.py spare --tld com --list`（按上面规则、优先取老列出）。

## 1. 执行后端（后台 + 日志）
后台启动，**立刻把 `tail -F` 命令给用户**（脚本结尾也会打印）：

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/app_domains.py allocate --project <数字> --count <N> --apply
```

脚本会：解析项目（007→f007，取 appId/appIp）、从空域名池挑 N 个 **.com**、`editBatch` 绑项目、`batchUpdateIp` 原地重指 CF A 记录到 appIp，再回查。

处理脚本的特殊返回：
- 「匹配到多个项目」→ AskUserQuestion 让用户选完整 projectCode，再重跑。
- 「.com 不够 N 个」（脚本以 ⛔ 退出）→ **停下来问用户**：要减少数量，还是允许用其他后缀（默认不自动用）。不要自作主张。
- 「batchUpdateIp 返回 404」→ 后端尚未部署该接口（见 Plan2）。告知用户：项目已绑定成功，但 CF A 记录未重指；需部署 batchUpdateIp 后重跑重指，或暂用后台「应用IP更新」。

## 2. 联动宝塔
把分配的这批域名（从脚本输出/日志里的「选中」清单取）加到 `<projectCode>_app`：

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/bt.py add-domain <projectCode>_app <域名...> --apply
```

漂移写进反馈、不拦截。需 Clash 代理。

## 3. 反馈
后端分配结果（每个域名 ✅/❌）+ 宝塔 code-block + 漂移提示。
