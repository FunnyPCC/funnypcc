# Plan 1 — 插件合并 fire-domain-ops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `huozhong-domain-ops` 与 `fire-bt-ops` 合并为单一插件 `fire-domain-ops`，保留两边全部既有能力。

**Architecture:** 在 funnypcc 仓库用 `git mv` 把两个插件的 skills/scripts/lib/hooks 合到 `fire-domain-ops/` 一棵树；合并 `plugin.json` 与 `marketplace.json`；保持目录相对层级不变，使 `fire_login.py`（`parents[3]/lib`）与 fire-bt-ops 各 skill（`${CLAUDE_PLUGIN_ROOT}/scripts/bt.py`）路径仍有效。本计划只做结构合并，不改业务逻辑。

**Tech Stack:** Claude Code 插件（plugin.json / marketplace.json / SKILL.md / hooks.json）、Python 脚本、git。

**前置：** 已在 funnypcc 仓库分支 `feat/fire-domain-ops`（spec 已提交其上）。所有命令工作目录均为 `~/.claude/plugins/marketplaces/funnypcc`。

**参考规格：** [docs/specs/2026-06-08-app-domains-design.md](../specs/2026-06-08-app-domains-design.md) §5。

---

### Task 1: 建立目标目录骨架

**Files:**
- Create: `fire-domain-ops/`（及子目录）

- [ ] **Step 1: 确认在正确分支与目录**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc && git branch --show-current && ls -d huozhong-domain-ops fire-bt-ops
```
Expected: 输出 `feat/fire-domain-ops`，且两个旧插件目录存在。

- [ ] **Step 2: 建骨架目录**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc && mkdir -p fire-domain-ops/.claude-plugin fire-domain-ops/skills
```
Expected: 无输出（成功）。

---

### Task 2: 迁移 fire-bt-ops 的 scripts / hooks / skills（git mv 保留历史）

**Files:**
- Move: `fire-bt-ops/scripts` → `fire-domain-ops/scripts`
- Move: `fire-bt-ops/hooks` → `fire-domain-ops/hooks`
- Move: `fire-bt-ops/skills/*` → `fire-domain-ops/skills/*`

- [ ] **Step 1: 移动 scripts 与 hooks**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
git mv fire-bt-ops/scripts fire-domain-ops/scripts
git mv fire-bt-ops/hooks fire-domain-ops/hooks
```
Expected: 无输出。

- [ ] **Step 2: 移动 fire-bt-ops 的 8 个 skill**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
for s in add-domain bt-panel-ops domains find-site list-sites setup sync-domains sync-panels; do
  git mv "fire-bt-ops/skills/$s" "fire-domain-ops/skills/$s"
done
```
Expected: 无输出。

- [ ] **Step 3: 移动 fire-bt-ops 的 README（改名保留）**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc && git mv fire-bt-ops/README.md fire-domain-ops/README-bt.md
```
Expected: 无输出。

- [ ] **Step 4: 验证 fire-bt-ops 旧目录已空（仅剩 plugin.json）**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc && find fire-bt-ops -type f
```
Expected: 只剩 `fire-bt-ops/.claude-plugin/plugin.json`。

---

### Task 3: 迁移 huozhong-domain-ops 的 lib / skills / 文档

**Files:**
- Move: `huozhong-domain-ops/lib` → `fire-domain-ops/lib`
- Move: `huozhong-domain-ops/skills/*` → `fire-domain-ops/skills/*`
- Move: `huozhong-domain-ops/{AGENTS.md,LICENSE}` → `fire-domain-ops/`

- [ ] **Step 1: 移动 lib 与两个 skill**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
git mv huozhong-domain-ops/lib fire-domain-ops/lib
git mv huozhong-domain-ops/skills/domain-inventory fire-domain-ops/skills/domain-inventory
git mv huozhong-domain-ops/skills/batch-add-gsc fire-domain-ops/skills/batch-add-gsc
```
Expected: 无输出。

- [ ] **Step 2: 移动 AGENTS.md 与 LICENSE**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
git mv huozhong-domain-ops/AGENTS.md fire-domain-ops/AGENTS.md
git mv huozhong-domain-ops/LICENSE fire-domain-ops/LICENSE
git mv huozhong-domain-ops/README.md fire-domain-ops/README-domain.md
```
Expected: 无输出。

- [ ] **Step 3: 验证 huozhong 旧目录仅剩 plugin.json**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc && find huozhong-domain-ops -type f
```
Expected: 只剩 `huozhong-domain-ops/.claude-plugin/plugin.json`。

- [ ] **Step 4: 验证关键脚本相对路径仍成立**

`fire_login.py` 用 `parents[3]/lib` 找 op_secrets：`skills/domain-inventory/scripts/fire_login.py` → parents[3] = 插件根。

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
test -f fire-domain-ops/lib/op_secrets.py && echo "lib OK"
test -f fire-domain-ops/skills/domain-inventory/scripts/fire_login.py && echo "fire_login OK"
python3 - <<'PY'
from pathlib import Path
p = Path("fire-domain-ops/skills/domain-inventory/scripts/fire_login.py").resolve()
assert (p.parents[3] / "lib" / "op_secrets.py").exists(), "parents[3]/lib 解析失败"
print("fire_login parents[3]/lib 解析 OK")
PY
```
Expected: 三行 OK。

---

### Task 4: 写合并后的 plugin.json

**Files:**
- Create: `fire-domain-ops/.claude-plugin/plugin.json`

- [ ] **Step 1: 写 plugin.json**

写入 `fire-domain-ops/.claude-plugin/plugin.json`：
```json
{
  "name": "fire-domain-ops",
  "version": "1.0.0",
  "description": "Fire 域名运维一体化:firepikata 域名×项目盘点/批量加域名/空域名分配 + 宝塔面板批量管理(站点匹配/域名同步/漂移检测) + Google 风险·存活检测 + 批量加 GSC,会话开启自动 sync",
  "author": {
    "name": "FunnyPCC",
    "url": "https://github.com/FunnyPCC"
  },
  "repository": "https://github.com/FunnyPCC/funnypcc",
  "license": "MIT",
  "keywords": ["domain-ops", "firepikata", "huozhong", "fire", "baota", "btpanel", "cloudflare", "google-search-console", "gsc", "safe-browsing", "domain-verification", "seo"]
}
```

- [ ] **Step 2: 校验 JSON 合法 + hooks 仍在**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
python3 -c "import json; json.load(open('fire-domain-ops/.claude-plugin/plugin.json')); print('plugin.json OK')"
test -f fire-domain-ops/hooks/hooks.json && python3 -c "import json; json.load(open('fire-domain-ops/hooks/hooks.json')); print('hooks.json OK')"
```
Expected: `plugin.json OK` 与 `hooks.json OK`。（hooks.json 内 `${CLAUDE_PLUGIN_ROOT}/scripts/session_sync.py` 路径在新插件根下仍有效。）

---

### Task 5: 更新 marketplace.json（两条插件 → 一条）

**Files:**
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: 替换 plugins 数组**

把 `.claude-plugin/marketplace.json` 的 `plugins` 数组整体替换为：
```json
  "plugins": [
    {
      "name": "fire-domain-ops",
      "source": "./fire-domain-ops",
      "description": "Fire 域名运维一体化:firepikata 盘点/加域名/分配 + 宝塔批量管理 + GSC,会话自动 sync"
    }
  ]
```
（保留文件其余字段 name/owner/metadata 不变。）

- [ ] **Step 2: 校验 JSON**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
python3 -c "import json; d=json.load(open('.claude-plugin/marketplace.json')); assert [p['name'] for p in d['plugins']]==['fire-domain-ops'], d['plugins']; print('marketplace.json OK')"
```
Expected: `marketplace.json OK`。

---

### Task 6: 删除两个空的旧插件目录

**Files:**
- Delete: `huozhong-domain-ops/`、`fire-bt-ops/`

- [ ] **Step 1: git rm 残余 plugin.json 并删目录**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
git rm huozhong-domain-ops/.claude-plugin/plugin.json fire-bt-ops/.claude-plugin/plugin.json
rmdir huozhong-domain-ops/.claude-plugin huozhong-domain-ops fire-bt-ops/.claude-plugin fire-bt-ops 2>/dev/null || true
```
Expected: 无错误。

- [ ] **Step 2: 确认旧目录消失、新目录完整**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
test ! -e huozhong-domain-ops && test ! -e fire-bt-ops && echo "旧目录已删"
find fire-domain-ops -maxdepth 2 -type d | sort
ls fire-domain-ops/skills
```
Expected: `旧目录已删`；skills 下列出 10 个目录：add-domain bt-panel-ops domains find-site list-sites setup sync-domains sync-panels domain-inventory batch-add-gsc。

---

### Task 7: 静态冒烟验证（不需凭据）

**Files:** 无（仅校验）

- [ ] **Step 1: 所有 Python 脚本语法编译通过**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
python3 -m py_compile fire-domain-ops/scripts/bt.py fire-domain-ops/scripts/setup.py fire-domain-ops/scripts/session_sync.py fire-domain-ops/lib/op_secrets.py fire-domain-ops/skills/domain-inventory/scripts/*.py fire-domain-ops/skills/batch-add-gsc/scripts/*.py && echo "py_compile 全部通过"
```
Expected: `py_compile 全部通过`。

- [ ] **Step 2: bt.py 无参数打印用法（确认可运行）**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc && python3 fire-domain-ops/scripts/bt.py 2>&1 | head -3
```
Expected: 打印 bt.py 的 usage 文本（含 `add-domain`/`domains` 等子命令），不报 import/语法错。

- [ ] **Step 3: 确认 fire-bt-ops 各 skill 内 `${CLAUDE_PLUGIN_ROOT}` 引用未失效**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
grep -rl 'CLAUDE_PLUGIN_ROOT' fire-domain-ops/skills | xargs grep -o '\${CLAUDE_PLUGIN_ROOT}/scripts/[A-Za-z_]*\.py' | sort -u
for f in $(grep -rho '\${CLAUDE_PLUGIN_ROOT}/scripts/[A-Za-z_]*\.py' fire-domain-ops/skills | sed 's#\${CLAUDE_PLUGIN_ROOT}/##' | sort -u); do test -f "fire-domain-ops/$f" && echo "存在: $f" || echo "缺失: $f"; done
```
Expected: 列出的每个被引用脚本都显示「存在:」（如 `scripts/bt.py`）。

---

### Task 8: 提交合并

- [ ] **Step 1: 提交**

Run:
```bash
cd ~/.claude/plugins/marketplaces/funnypcc
git add -A
git commit -m "$(cat <<'EOF'
refactor(plugin): 合并 huozhong-domain-ops + fire-bt-ops 为 fire-domain-ops

git mv 迁移两边 skills/scripts/lib/hooks 到单一插件树;合并 plugin.json
与 marketplace.json;保留全部既有能力与相对路径,不改业务逻辑。

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -2
```
Expected: 提交成功，HEAD 为本次合并 commit。

---

### Task 9: 用户重装 + 既有能力冒烟（用户动作）

> 仓库改完后，需要在本地把插件换成合并后的版本。以下由用户在 Claude Code 里执行。

- [ ] **Step 1: 重新安装合并后的插件**

在 Claude Code 中：用 `/plugin` 进入插件管理 → 刷新/更新 `funnypcc` marketplace（指向本地 checkout 的当前分支）→ 卸载 `huozhong-domain-ops`、`fire-bt-ops`，安装 `fire-domain-ops`。
（若 marketplace 读取的是 `main` 分支，需先把本分支合并/切换到 marketplace 实际读取的分支，再刷新。）

- [ ] **Step 2: 冒烟：列出 fire-domain-ops 的 skills**

确认 `/fire-domain-ops:` 下能看到全部历史命令：`list-sites`、`find-site`、`domains`、`add-domain`、`sync-domains`、`sync-panels`、`bt-panel-ops`、`setup`、`domain-inventory`、`batch-add-gsc`。

- [ ] **Step 3: 冒烟：跑一个只读命令**

执行 `/fire-domain-ops:find-site f007`（或任意只读查询），确认能正常加载 skill 并调用 `${CLAUDE_PLUGIN_ROOT}/scripts/bt.py`，不报路径错。

- [ ] **Step 4: 冒烟：SessionStart 钩子**

开一个新会话，确认 fire-bt-ops 的 SessionStart 面板 sync 钩子仍触发（panels.yml 与 SQLite 一致时静默，不一致时给提示），证明 hooks 迁移成功。

---

## 自检（Self-Review）

- **Spec 覆盖**：对应 spec §5 迁移要点——目录骨架(Task1)、fire-bt-ops 迁移(Task2)、huozhong 迁移(Task3)、plugin.json 合并(Task4)、marketplace.json(Task5)、删旧目录(Task6)、相对路径校验(Task3 Step4 / Task7)、hooks 合并(Task4 Step2 / Task9 Step4)、重装(Task9)。✅
- **占位符**：无 TBD；每步含确切命令与期望输出。✅
- **一致性**：插件名统一 `fire-domain-ops`；skills 共 10 个，前后一致；`parents[3]/lib`、`${CLAUDE_PLUGIN_ROOT}/scripts/*` 均有校验步骤。✅
- **数据安全**：迁移不触碰 `~/.fire/ops/`、`./域名维护/`、`./gsc/` 等插件外数据。✅
