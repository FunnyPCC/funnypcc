#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["requests>=2.28", "ddddocr"]
# ///
"""
firepikata 后台自动登录 → 返回有效 X-Access-Token(临时 JWT,约 3 天过期)。

流程(JeecgBoot 带图形验证码):
  1. GET /api/sys/randomImage/{checkKey}  取 base64 验证码图
  2. ddddocr 识别 4 位验证码
  3. POST /api/sys/login {username,password,captcha,checkKey}  → result.token

账密:经 op_secrets 解析(环境变量 FIRE_USER/FIRE_PASS > 本地缓存 > 1Password
「火苗-公共运维后管」)。若缓存账密导致登录失败,自动回 1P 重取一次再试。

用法(在项目根运行):
  uv run <plugin>/skills/domain-inventory/scripts/fire_login.py   # 打印一个新 token
"""
import base64
import json
import os
import sys
try: sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception: pass
import time
from pathlib import Path

import ddddocr
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "lib"))
from op_secrets import get_secret, refresh_secret  # noqa: E402

BASE = "https://firepikatacommon.huozhongtech.org"
OP_ITEM = "火苗-公共运维后管"
# token 缓存(JWT 自带 exp,约 3 天):放 gitignored 的 DOC_DIR,复用避免每次过验证码
TOKEN_CACHE = Path(os.environ.get("DOMAIN_DOC_DIR", "域名维护")) / ".fire_token.json"
TOKEN_MARGIN = 600  # 距过期 <10min 视为需刷新


def _jwt_exp(token):
    """不验签,仅解出 JWT payload 的 exp(unix 秒);失败返回 None。"""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)            # 补 base64 padding
        return json.loads(base64.urlsafe_b64decode(payload)).get("exp")
    except Exception:
        return None


def _read_cached_token():
    try:
        d = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
        tok, exp = d.get("token"), d.get("exp")
        if tok and exp and (exp - time.time()) > TOKEN_MARGIN:
            return tok, exp
    except Exception:
        pass
    return None, None


def _write_cached_token(token):
    try:
        TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE.write_text(json.dumps({"token": token, "exp": _jwt_exp(token)}),
                               encoding="utf-8")
    except Exception:
        pass


def _creds(force_op=False):
    if force_op:
        return (refresh_secret("fire_username", OP_ITEM, "username"),
                refresh_secret("fire_password", OP_ITEM, "password"))
    return (get_secret("fire_username", OP_ITEM, "username", env="FIRE_USER"),
            get_secret("fire_password", OP_ITEM, "password", env="FIRE_PASS"))


def _login_once(user, pwd, max_tries=8) -> str:
    ocr = ddddocr.DdddOcr(show_ad=False)
    s = requests.Session()
    last = ""
    for _ in range(max_tries):
        ck = str(int(time.time() * 1000))
        img = s.get(f"{BASE}/api/sys/randomImage/{ck}", timeout=15).json()
        b64 = (img.get("result") or "").split(",", 1)[-1]
        code = ocr.classification(base64.b64decode(b64))
        if len(code) != 4:
            continue
        r = s.post(f"{BASE}/api/sys/login", timeout=15,
                   json={"username": user, "password": pwd,
                         "captcha": code, "checkKey": ck}).json()
        if r.get("success"):
            return r["result"]["token"]
        last = r.get("message") or ""
        if "验证码" not in last:                      # 非验证码错误(账密错等)
            raise _AuthError(last)
        time.sleep(0.5)
    raise SystemExit(f"❌ 验证码多次识别失败(最后:{last})")


class _AuthError(Exception):
    pass


def get_token(force=False) -> str:
    if not force:
        tok, exp = _read_cached_token()
        if tok:
            left = int(exp - time.time())
            print(f"♻️ 复用缓存 token(剩 {left // 3600}h{left % 3600 // 60}m,未过验证码)", file=sys.stderr)
            return tok
    user, pwd = _creds()
    try:
        tok = _login_once(user, pwd)
    except _AuthError as e:                            # 缓存账密可能过期 → 回 1P 重取再试
        try:
            user, pwd = _creds(force_op=True)
        except Exception:
            raise SystemExit(f"❌ 登录失败:{e}(且无法从 1Password 重取账密,请解锁 op 或更新缓存)")
        try:
            tok = _login_once(user, pwd)
        except _AuthError as e2:
            raise SystemExit(f"❌ 登录失败:{e2}")
    _write_cached_token(tok)
    return tok


if __name__ == "__main__":
    # --fresh / FIRE_TOKEN_REFRESH=1 强制重登(忽略缓存,如遇 401)
    force = "--fresh" in sys.argv[1:] or os.environ.get("FIRE_TOKEN_REFRESH") == "1"
    sys.stdout.write(get_token(force=force))
