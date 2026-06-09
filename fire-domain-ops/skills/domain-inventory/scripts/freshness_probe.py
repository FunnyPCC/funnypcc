#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28"]
# ///
"""
快照新鲜度探针 —— 用便宜的 1 行 list 请求拿后台"版本指纹",和本地 marker 比对,
决定「用快照」还是「重拉」。无需后台新接口:复用 jeecgboot 现成 list(pageSize=1 即返回 total + 最新一行)。

指纹/表 = (total, maxUpdate, maxCreate):
  total     —— 域名/项目总数:捕捉 增/删
  maxUpdate —— 最大 updateTime:捕捉 就地编辑(改状态/改归属) ← 已验证编辑会 bump updateTime
  maxCreate —— 最大 createTime:补强 新增

用法:
  uv run freshness_probe.py            # 探针模式:调 API → 与 .freshness.json 比对
      退出码 0=FRESH(用快照)  10=STALE(需重拉)  2=token失效/错误(应登录后重拉)
  uv run freshness_probe.py --seed     # 播种模式:从本地 raw_*.json 算指纹写 .freshness.json(重拉末尾调,不访问 API)
  uv run freshness_probe.py --json     # 探针模式但只输出 JSON(current/marker/verdict)

鉴权同 fetch_domains.py:请求头 X-Access-Token,token 经 FIRE_TOKEN 传入。
输出目录相对 CWD(DOMAIN_DOC_DIR 覆盖),请在项目根运行。
"""
import json
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "https://firepikatacommon.huozhongtech.org"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
DOC_DIR = Path(os.environ.get("DOMAIN_DOC_DIR", "域名维护"))
MARKER = DOC_DIR / ".freshness.json"

# 表名 → (list 路径, 本地快照文件名)
TABLES = {
    "domains": ("/api/app/appDomainManager/list", "raw_domains.json"),
    "apps":    ("/api/app/appManager/list",       "raw_apps.json"),
}


def _fp_from_rows(rows):
    ups = [r.get("updateTime") for r in rows if r.get("updateTime")]
    crs = [r.get("createTime") for r in rows if r.get("createTime")]
    return {
        "total": len(rows),
        "maxUpdate": max(ups) if ups else None,
        "maxCreate": max(crs) if crs else None,
    }


def seed():
    """从本地快照算指纹写 marker(不访问 API)。重拉末尾调用,此时快照==后台。"""
    fp = {}
    for name, (_, fname) in TABLES.items():
        p = DOC_DIR / fname
        if not p.exists():
            sys.exit(f"❌ 缺少 {p},无法播种 marker(先跑 fetch_domains.py)。")
        rows = json.loads(p.read_text(encoding="utf-8"))
        fp[name] = _fp_from_rows(rows)
    MARKER.write_text(json.dumps(fp, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 已写快照指纹 → {MARKER}")
    for name, v in fp.items():
        print(f"   {name}: total={v['total']} maxUpdate={v['maxUpdate']} maxCreate={v['maxCreate']}")


def _probe_table(path, token):
    import requests
    out = {"total": None, "maxUpdate": None, "maxCreate": None}
    for col, key in (("updateTime", "maxUpdate"), ("createTime", "maxCreate")):
        params = {"column": col, "order": "desc", "pageNo": 1, "pageSize": 1, "_t": 1}
        r = requests.get(f"{BASE}{path}", params=params,
                         headers={"X-Access-Token": token, "User-Agent": UA}, timeout=30)
        data = r.json()
        if not data.get("success"):
            if data.get("code") == 401:
                raise PermissionError(data.get("message", "401"))
            raise RuntimeError(data.get("message", "接口错误"))
        res = data["result"]
        out["total"] = res.get("total")
        recs = res.get("records") or []
        if recs:
            out[key] = recs[0].get(col)
    return out


def probe(as_json=False):
    token = (os.environ.get("FIRE_TOKEN") or (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "")).strip()
    if not token:
        sys.exit("❌ 缺少 token。设 FIRE_TOKEN 或先跑 fire_login.py。")

    # 快照文件缺失 → 直接判 STALE(无需 API)
    missing = [f for _, (_, f) in TABLES.items() if not (DOC_DIR / f).exists()]
    marker = json.loads(MARKER.read_text(encoding="utf-8")) if MARKER.exists() else None

    try:
        current = {name: _probe_table(path, token) for name, (path, _) in TABLES.items()}
    except PermissionError as e:
        print(f"⚠️ Token 失效({e})→ 视为需登录后重拉。", file=sys.stderr)
        if as_json:
            print(json.dumps({"verdict": "TOKEN_EXPIRED"}, ensure_ascii=False))
        sys.exit(2)
    except Exception as e:
        print(f"⚠️ 探针请求失败({e})→ 保守判 STALE。", file=sys.stderr)
        sys.exit(10)

    reasons = []
    if missing:
        reasons.append(f"快照文件缺失: {missing}")
    if marker is None:
        reasons.append("无 marker(.freshness.json)")
    else:
        for name in TABLES:
            c, m = current.get(name, {}), marker.get(name, {})
            for k in ("total", "maxUpdate", "maxCreate"):
                if c.get(k) != m.get(k):
                    reasons.append(f"{name}.{k}: 快照={m.get(k)} ≠ 后台={c.get(k)}")

    verdict = "STALE" if reasons else "FRESH"
    if as_json:
        print(json.dumps({"verdict": verdict, "current": current,
                          "marker": marker, "reasons": reasons}, ensure_ascii=False, indent=2))
    else:
        if verdict == "FRESH":
            print("✅ FRESH —— 后台指纹与快照一致,用快照即可。")
            for name, v in current.items():
                print(f"   {name}: total={v['total']} maxUpdate={v['maxUpdate']}")
        else:
            print("♻️ STALE —— 后台已变,需重拉。原因:")
            for r in reasons:
                print(f"   - {r}")
    sys.exit(0 if verdict == "FRESH" else 10)


if __name__ == "__main__":
    args = set(sys.argv[1:])
    if "--seed" in args:
        seed()
    else:
        probe(as_json="--json" in args)
