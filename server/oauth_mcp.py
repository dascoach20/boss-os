"""
OAuth 2.1 cho remote MCP server (chuẩn MCP Authorization) - Boss TỰ giữ token,
mọi engine dùng chung, KHÔNG cần mở terminal gõ /mcp như trước.
Luồng: discovery (RFC 9728 / .well-known) → DCR (RFC 7591, nếu server hỗ trợ)
→ authorize PKCE S256 → callback → token → tự refresh.

Store: STATE_DIR/.oauth_mcp.json - token mã hoá qua secrets_store.
Không import mcp_client/mcp_hub (tránh vòng import).
"""
import base64
import hashlib
import json
import secrets as _secrets
import sys
import time
import urllib.parse

import httpx

import mcp_store
import secrets_store
from config import STATE_DIR

_STORE_PATH = STATE_DIR / ".oauth_mcp.json"
_pending = {}    # state -> {conn_id, verifier, token_endpoint, client_id, redirect_uri, ts}
_PENDING_TTL = 600


def _load():
    try:
        if _STORE_PATH.exists():
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save(d):
    _STORE_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def _conn(conn_id):
    return next((c for c in mcp_store.resolved(enabled_only=False) if c["id"] == conn_id), None)


async def _discover(url):
    """Tìm authorization server metadata cho 1 MCP url. Trả dict metadata hoặc None."""
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        issuer = None
        try:
            r = await client.post(url, json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                             "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                                        "clientInfo": {"name": "boss-os", "version": "1.0"}}},
                                  headers={"Accept": "application/json, text/event-stream"})
            www = r.headers.get("www-authenticate") or ""
            m = None
            for part in www.split(","):
                if "resource_metadata" in part:
                    m = part.split("=", 1)[-1].strip().strip('"')
            # Chống SSRF: metadata URL do server trả về CHỈ được fetch khi cùng host với
            # chính MCP url user đã khai (chuẩn RFC 9728 đặt metadata cùng origin).
            if m:
                mp = urllib.parse.urlparse(m)
                up = urllib.parse.urlparse(url)
                if mp.scheme in ("http", "https") and mp.netloc == up.netloc:
                    rm = (await client.get(m)).json()
                    servers = rm.get("authorization_servers") or []
                    if servers:
                        issuer = servers[0]
        except Exception:
            pass
        candidates = []
        if issuer:
            candidates.append(issuer.rstrip("/") + "/.well-known/oauth-authorization-server")
        p = urllib.parse.urlparse(url)
        origin = f"{p.scheme}://{p.netloc}"
        candidates += [origin + "/.well-known/oauth-authorization-server",
                       origin + "/.well-known/openid-configuration"]
        for c in candidates:
            try:
                r = await client.get(c)
                if r.status_code == 200:
                    md = r.json()
                    if md.get("authorization_endpoint") and md.get("token_endpoint"):
                        return md
            except Exception:
                continue
    return None


async def start_auth(conn_id, redirect_uri):
    """Bắt đầu OAuth cho 1 connection. Trả {ok, url?} hoặc {ok:False, error}.

    2 nhánh:
    - EXPLICIT (connector.auth khai authorize_url + token_url, vd Google): dùng cấu hình khai
      sẵn + client_id/secret user tự tạo (BYO). Dành cho provider KHÔNG hỗ trợ DCR như Google.
    - DISCOVERY (còn lại, vd Meta): tự tìm metadata + tự đăng ký client (DCR) như chuẩn MCP."""
    conn = _conn(conn_id)
    if not conn:
        return {"ok": False, "error": "Kết nối không tồn tại"}
    auth = (conn.get("connector") or {}).get("auth") or {}
    store = _load()
    ent = store.get(conn_id) or {}
    explicit = bool(auth.get("authorize_url") and auth.get("token_url"))

    if explicit:
        creds = mcp_store.connection_secrets(conn_id)
        client_id = (creds.get("client_id") or "").strip()
        client_secret = creds.get("client_secret") or ""
        if not client_id:
            return {"ok": False, "error": "Chưa có Client ID. Dán Client ID + Client Secret bạn tạo "
                                          "ở nhà cung cấp (Google Cloud / Slack app) rồi bấm Kết nối lại."}
        authorize_endpoint = auth["authorize_url"]
        token_endpoint = auth["token_url"]
        scopes = auth.get("scopes") or []
        # Tên param mang scope + dấu ngăn khác nhau theo hãng: Google dùng scope + dấu cách (mặc định),
        # Slack dùng user_scope + dấu phẩy (token người dùng).
        scope_param = auth.get("scope_param") or "scope"
        scope_sep = auth.get("scope_sep") or " "
        extra_params = dict(auth.get("authorize_params") or {})
        add_resource = False
    else:
        if not conn.get("url"):
            return {"ok": False, "error": "Kết nối không có URL"}
        md = await _discover(conn["url"])
        if not md:
            return {"ok": False, "error": "Server này không khai OAuth chuẩn MCP (không tìm thấy "
                                          ".well-known metadata). Dùng API key nếu nhà cung cấp có."}
        authorize_endpoint = md["authorization_endpoint"]
        token_endpoint = md["token_endpoint"]
        client_id = ent.get("client_id", "")
        client_secret = ""
        if not client_id and md.get("registration_endpoint"):
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    r = await client.post(md["registration_endpoint"], json={
                        "client_name": "Boss OS", "redirect_uris": [redirect_uri],
                        "grant_types": ["authorization_code", "refresh_token"],
                        "response_types": ["code"], "token_endpoint_auth_method": "none",
                    })
                    if r.status_code in (200, 201):
                        client_id = r.json().get("client_id", "")
            except Exception as e:
                print(f"[oauth dcr] {e}", file=sys.stderr)
        if not client_id:
            return {"ok": False, "error": "Server không hỗ trợ tự đăng ký client (DCR) - cần client_id thủ công"}
        scopes = md.get("scopes_supported") or []
        scope_param, scope_sep = "scope", " "
        extra_params = {}
        add_resource = True

    verifier = _secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = _secrets.token_urlsafe(24)
    now = time.time()
    for k in [k for k, v in _pending.items() if now - v["ts"] > _PENDING_TTL]:
        _pending.pop(k, None)
    _pending[state] = {"conn_id": conn_id, "verifier": verifier, "token_endpoint": token_endpoint,
                       "client_id": client_id, "client_secret": client_secret,
                       "redirect_uri": redirect_uri, "ts": now}
    q = {"response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri,
         "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}
    if scopes:
        q[scope_param] = scope_sep.join(scopes)
    if add_resource:
        q["resource"] = conn["url"]   # RFC 8707 - server bỏ qua nếu không dùng
    q.update(extra_params)            # vd Google: access_type=offline, prompt=consent (để có refresh_token)
    ent.update(client_id=client_id, token_endpoint=token_endpoint)
    store[conn_id] = ent
    _save(store)
    return {"ok": True, "url": authorize_endpoint + "?" + urllib.parse.urlencode(q)}


def _email_from_id_token(idt):
    """Bóc email từ id_token (JWT) Google trả về khi scope có openid+email - để tự đặt tên
    tài khoản. Chỉ đọc payload hiển thị, không cần verify chữ ký (token lấy trực tiếp qua TLS)."""
    try:
        payload = (idt or "").split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode()))
        return data.get("email") or ""
    except Exception:
        return ""


async def handle_callback(state, code):
    p = _pending.pop(state or "", None)
    if not p:
        return {"ok": False, "error": "Phiên OAuth không hợp lệ hoặc đã hết hạn - thử lại từ đầu"}
    try:
        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": p["redirect_uri"],
                "client_id": p["client_id"], "code_verifier": p["verifier"]}
        if p.get("client_secret"):   # client bảo mật (vd Google Web app) cần secret khi đổi token
            data["client_secret"] = p["client_secret"]
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(p["token_endpoint"], data=data, headers={"Accept": "application/json"})
        tk = r.json()
        if "access_token" not in tk:
            return {"ok": False, "error": f"Đổi code thất bại: {json.dumps(tk, ensure_ascii=False)[:200]}"}
    except Exception as e:
        return {"ok": False, "error": f"Đổi code thất bại: {type(e).__name__}: {e}"}
    store = _load()
    ent = store.get(p["conn_id"]) or {}
    first_auth = not ent.get("access_token")   # lần đăng nhập ĐẦU (chưa từng có token) mới tự đặt tên
    ent.update(access_token=secrets_store.encrypt(tk["access_token"]),
               refresh_token=secrets_store.encrypt(tk.get("refresh_token", "")),
               expires_at=time.time() + float(tk.get("expires_in") or 3600))
    store[p["conn_id"]] = ent
    _save(store)
    return {"ok": True, "conn_id": p["conn_id"], "first_auth": first_auth,
            "email": _email_from_id_token(tk.get("id_token", ""))}


async def _refresh(conn_id, ent):
    rt = secrets_store.decrypt(ent.get("refresh_token", ""))
    if not (rt and ent.get("token_endpoint") and ent.get("client_id")):
        return None
    try:
        data = {"grant_type": "refresh_token", "refresh_token": rt, "client_id": ent["client_id"]}
        cs = mcp_store.connection_secrets(conn_id).get("client_secret")
        if cs:   # BYO client bảo mật (Google) - refresh cũng cần client_secret
            data["client_secret"] = cs
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(ent["token_endpoint"], data=data, headers={"Accept": "application/json"})
        tk = r.json()
        if "access_token" not in tk:
            return None
    except Exception as e:
        print(f"[oauth refresh] {e}", file=sys.stderr)
        return None
    ent.update(access_token=secrets_store.encrypt(tk["access_token"]),
               expires_at=time.time() + float(tk.get("expires_in") or 3600))
    if tk.get("refresh_token"):
        ent["refresh_token"] = secrets_store.encrypt(tk["refresh_token"])
    store = _load()
    store[conn_id] = ent
    _save(store)
    return ent


async def auth_headers(conn_id):
    """{"Authorization": "Bearer ..."} cho connection oauth; tự refresh khi sắp hết hạn."""
    store = _load()
    ent = store.get(conn_id)
    if not ent or not ent.get("access_token"):
        return {}
    if time.time() > float(ent.get("expires_at") or 0) - 60:
        ent = await _refresh(conn_id, ent) or ent
    tok = secrets_store.decrypt(ent.get("access_token", ""))
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def status(conn_id):
    ent = _load().get(conn_id) or {}
    return {"connected": bool(ent.get("access_token")), "expires_at": float(ent.get("expires_at") or 0)}


def forget(conn_id):
    store = _load()
    if conn_id in store:
        store.pop(conn_id)
        _save(store)
    return {"ok": True}
