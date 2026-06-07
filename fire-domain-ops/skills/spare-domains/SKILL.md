---
name: spare-domains
description: 统计 firepikata 待分配的空域名（项目空 + 备注空 + 状态正常），按 TLD 后缀分组计数。Use when the user asks "还有多少空域名待分配"、"空域名还剩多少"、"待分配域名"、"spare domains count"，or wants the count of unassigned domains grouped by suffix.
allowed-tools: Bash
---

流程2：只读统计待分配空域名。直接运行，把结果转给用户。

## Run

```bash
uv run ${CLAUDE_PLUGIN_ROOT}/scripts/app_domains.py spare
```

输出形如：`待分配空域名：共 N 个`，下面按后缀 `com: X 个、info: Y 个…`（按数量排序）。原样转达即可。纯读，无任何写入。
