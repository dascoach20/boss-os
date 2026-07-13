"""
Zalo Realtime auto-reply — event-driven qua `zalo-agent-cli listen --webhook`.

Bỏ vòng lặp 5 phút: khách nhắn Zalo -> WebSocket của zalo-agent-cli bắn event ->
POST webhook về endpoint /hooks/zalo -> Boss phản hồi NGAY.

Trải nghiệm khách (mục tiêu: khách LUÔN thấy được tiếp nhận tức thì):
  1. Vừa nhận tin  -> gửi ACK ngay ("Dạ em nhận được rồi ạ, em xem ngay ạ").
  2. Câu cơ bản    -> Claude trả lời luôn.
  3. Cần tra cứu   -> nếu sinh câu trả lời lâu quá REASSURE_AFTER_S giây thì gửi tin
                      trấn an ("anh đợi chút, phần này hơi nhiều, em trả lời ngay ạ").
  4. Câu quá khó   -> Claude trả về [[ESCALATE]] -> báo khách chờ + bắn về Telegram cho Sếp.
  5. Sau mỗi câu   -> tự học: lưu Q&A vào brain memory + (tuỳ chọn) Google Sheet realtime.

Python điều phối TOÀN BỘ việc gửi Zalo + timing + log; Claude chỉ sinh TEXT.
Gửi/nhận Zalo chạy dưới HOME cô lập của tài khoản đã kết nối (mcp_store).
"""
import asyncio
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import httpx
from fastapi import Request

from claude_cli import ClaudeCLI
import mcp_store


def _log(msg: str) -> None:
    print(f"[zalo-rt] {msg}", file=sys.stderr, flush=True)


# ---- Tin nhắn cố định (Sếp chỉnh lời tuỳ ý ở đây) ----
ACK_MSG = "Dạ em nhận được tin của mình rồi ạ, em xem và phản hồi ngay ạ 🌸"
REASSURE_MSG = "Anh/chị chờ em một chút xíu nhé, phần này hơi nhiều thông tin, em tổng hợp rồi trả lời ngay ạ 🙏"
HOLD_MSG = "Dạ câu này em xin phép xác nhận lại với bên em để trả lời anh/chị chính xác nhất, em phản hồi sớm nhất có thể ạ 🤝"

REASSURE_AFTER_S = 15.0       # sinh câu trả lời lâu hơn ngần này (giây) -> gửi tin trấn an
REPLY_MAX_WALL_S = 180.0      # trần thời gian Claude sinh 1 câu trả lời
ESCALATE_TOKEN = "[[ESCALATE]]"


def _reply_system_prompt(agent_name: str, agent_role: str, kb: str = "") -> str:
    """Nhân cách 1 NHÂN VIÊN AI của DAS (gọn, NHANH). Trả lời câu dễ, escalate câu cần chi tiết/số liệu.
    KHÔNG nạp brain nội bộ (chậm + rủi ro lộ dữ liệu mật) - chỉ dùng persona + KB khách-an-toàn (nếu có)."""
    base = (
        f"BẠN LÀ {agent_name.upper()} - {agent_role}.\n"
        f"Bạn tên là {agent_name}, đang trả lời TRỰC TIẾP một khách nhắn tin trên Zalo (như một nhân viên thật). "
        "Trả lời bằng tiếng Việt, xưng 'em', dùng tên khi phù hợp "
        f"(vd lời chào: 'Dạ em {agent_name} bên DAS đây ạ'), gọi khách 'anh/chị', giọng thân thiện - "
        "chuyên nghiệp - NGẮN GỌN như người thật đang chat (2-5 câu, KHÔNG markdown). "
        "Không bao giờ tự nhận là AI/bot/trợ lý ảo.\n"
        "DAS là công ty đào tạo & coaching cho chuyên gia, coach và chủ doanh nghiệp (website das.vn).\n"
        "- Câu cơ bản (DAS là gì, làm về gì, cách tham gia/tìm hiểu, thông tin chung) -> TRẢ LỜI thẳng, tự tin, ngắn.\n"
        "- Câu cần SỐ LIỆU/GIÁ/CAM KẾT cụ thể, chuyện tiền/hợp đồng, khiếu nại nặng, HOẶC bạn KHÔNG chắc chắn "
        "-> trả về DUY NHẤT một dòng: " + ESCALATE_TOKEN + "\n"
        "Tuyệt đối KHÔNG bịa giá/cam kết/chính sách. Không chắc thì escalate. "
        "Output CHỈ là lời nhắn gửi khách (hoặc đúng token escalate), không thêm gì ngoài lề."
    )
    if kb.strip():
        base += ("\n\n=== THÔNG TIN DAS ĐỂ TRẢ LỜI (chỉ nói những gì có ở đây, thiếu thì escalate) ===\n"
                 + kb.strip())
    return base


@dataclass
class ZaloRTDeps:
    build_system_prompt: Callable[[str], str]      # (brain) -> system prompt có tri thức + memory
    brain_root: Callable[[str], str]               # (brain) -> path gốc brain
    aux_model: Callable[[], Optional[str]]         # model phụ cho reply (rẻ/nhanh) hoặc None
    readonly_tools: list                           # tool chỉ-đọc cho fork reply
    state_dir: Path
    active_brain: Callable[[], str]                # brain dùng để trả lời khách
    notify_owner: Callable                         # async (text) -> gửi Telegram cho Sếp
    settings: Callable[[], dict]                    # đọc settings (lấy config zalo-rt nếu cần)


class ZaloRealtime:
    def __init__(self, deps: ZaloRTDeps):
        self.deps = deps
        self.proc: Optional[subprocess.Popen] = None
        self.home: Optional[str] = None
        # Danh tính "nhân viên AI" (1 số Zalo = 1 nhân viên). Đổi qua env cho từng account.
        self.agent_name = os.getenv("ZALO_AGENT_NAME", "Tuấn").strip() or "Tuấn"
        self.agent_role = os.getenv("ZALO_AGENT_ROLE", "nhân viên chăm sóc khách hàng của DAS").strip() \
            or "nhân viên chăm sóc khách hàng của DAS"
        self.status = "off"          # off | running | no-account | error
        self.last_error = ""
        self.started_at = 0.0
        self.replied = 0
        self.escalated = 0
        # chống trả lời trùng / xử lý song song cùng 1 khách
        self._threads: dict[str, float] = {}
        self._io = asyncio.Lock()

    # ---------- tìm tài khoản Zalo đã kết nối ----------
    def _zalo_home(self) -> Optional[str]:
        """HOME cô lập chứa credential Zalo (đã quét QR).

        QUAN TRỌNG: Zalo chỉ cho 1 phiên WebSocket/tài khoản. Listener realtime này PHẢI là
        phiên DUY NHẤT → nên KHÔNG đòi connection 'enabled' (user tắt Zalo MCP để nó thôi mở
        listener cạnh tranh, nhưng credential/home vẫn còn). Ưu tiên env ZALO_HOME nếu đặt tay."""
        env_home = os.getenv("ZALO_HOME", "").strip()
        if env_home:
            return env_home
        try:
            for c in mcp_store.list_connections():
                if c.get("connector_id") != "zalo":
                    continue
                home = (c.get("config") or {}).get("home_dir")
                if home:
                    return home
                return str(self.deps.state_dir / "connector-home" / f"{c['connector_id']}-{c.get('slug')}")
        except Exception as e:
            _log(f"zalo_home error: {e}")
        return None

    def _zalo_env(self) -> dict:
        env = dict(os.environ)
        if self.home:
            env["HOME"] = self.home
            env["USERPROFILE"] = self.home
        return env

    # ---------- gửi tin Zalo (đồng bộ, chạy trong thread) ----------
    def _send_sync(self, thread_id: str, text: str) -> None:
        try:
            subprocess.run(
                ["npx", "-y", "zalo-agent-cli", "msg", "send", str(thread_id), text],
                env=self._zalo_env(), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                timeout=60, check=False,
            )
        except Exception as e:
            _log(f"send fail thread={thread_id}: {e}")

    async def _send(self, thread_id: str, text: str) -> None:
        if not text:
            return
        await asyncio.to_thread(self._send_sync, thread_id, text)

    # ---------- sinh câu trả lời bằng Claude (chỉ đọc) ----------
    async def _generate(self, question: str) -> str:
        # KB khách-an-toàn (tuỳ chọn) - 1 file FAQ do Sếp biên tập, KHÔNG phải brain nội bộ.
        kb = ""
        kbf = os.getenv("ZALO_KB_FILE", "").strip()
        if kbf:
            try:
                kb = Path(kbf).read_text(encoding="utf-8")[:20000]
            except Exception as e:
                _log(f"KB read fail: {e}")
        cli = ClaudeCLI(
            system_prompt=_reply_system_prompt(self.agent_name, self.agent_role, kb),
            cwd=self.deps.brain_root(self.deps.active_brain()),
            tag="zalo-reply",
        )
        # NHANH: model gọn (sonnet mặc định) + KHÔNG cho lục file (tránh chậm + lộ dữ liệu nội bộ)
        cli.model = os.getenv("ZALO_MODEL", "sonnet") or "sonnet"
        cli.disallowed_tools = ["Read", "Glob", "Grep", "LS", "Bash", "Task",
                                "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch"]
        cli.max_wall_s = REPLY_MAX_WALL_S
        if not cli.is_available():
            return ESCALATE_TOKEN
        prompt = f"Khách hàng vừa nhắn trên Zalo:\n\"\"\"\n{question}\n\"\"\"\nTrả lời khách."
        out, err = "", ""
        try:
            async for ev in cli.query(prompt):
                if ev["type"] == "final":
                    out = ev.get("content", "") or out
                elif ev["type"] == "error":
                    err = ev.get("content", "") or err
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        if err and not out:
            _log(f"generate error: {err}")
            return ESCALATE_TOKEN
        return (out or "").strip()

    async def _generate_with_reassurance(self, thread_id: str, question: str) -> str:
        """Sinh câu trả lời; nếu lâu hơn REASSURE_AFTER_S thì gửi tin trấn an giữa chừng."""
        task = asyncio.create_task(self._generate(question))
        done, _ = await asyncio.wait({task}, timeout=REASSURE_AFTER_S)
        if task not in done:
            await self._send(thread_id, REASSURE_MSG)
        return await task

    # ---------- tự học: lưu Q&A ----------
    async def _log_qa(self, question: str, answer: str, thread_id: str, name: str = "") -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        who = name or "(không rõ)"
        # 1) brain memory (append file .md — curator/loop sẽ chưng cất sau)
        try:
            brain = self.deps.active_brain()
            mem_dir = Path(self.deps.brain_root(brain)) / "memory"
            mem_dir.mkdir(parents=True, exist_ok=True)
            f = mem_dir / "zalo-qa-hoc.md"
            entry = (f"\n## {ts} · {who} · thread {thread_id}\n"
                     f"**Khách hỏi:** {question}\n**Đã trả lời:** {answer}\n")
            with f.open("a", encoding="utf-8") as fh:
                fh.write(entry)
        except Exception as e:
            _log(f"log memory fail: {e}")
        # 2) Google Sheet realtime (Apps Script webhook) — chỉ khi có cấu hình
        url = os.getenv("ZALO_SHEET_WEBHOOK", "").strip()
        if url:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    await client.post(url, json={
                        "time": ts, "thread": str(thread_id), "name": who,
                        "question": question, "answer": answer,
                    })
            except Exception as e:
                _log(f"sheet webhook fail: {e}")

    # ---------- xử lý 1 event từ webhook ----------
    async def handle_event(self, payload: dict) -> None:
        try:
            _log(f"event: {json.dumps(payload, ensure_ascii=False)[:500]}")
        except Exception:
            pass
        thread_id, text, is_self, name = self._parse(payload)
        if not thread_id or not text or is_self:
            return
        # chống xử lý chồng cùng 1 khách trong 3s (gộp tin bắn liên tiếp)
        now = time.time()
        async with self._io:
            last = self._threads.get(thread_id, 0)
            self._threads[thread_id] = now
        # 1) ACK tức thì
        await self._send(thread_id, ACK_MSG)
        # 2) sinh câu trả lời (có trấn an nếu lâu)
        reply = await self._generate_with_reassurance(thread_id, text)
        # 3) escalate hay trả lời
        if not reply or reply.strip() == ESCALATE_TOKEN or ESCALATE_TOKEN in reply:
            self.escalated += 1
            await self._send(thread_id, HOLD_MSG)
            try:
                await self.deps.notify_owner(
                    "🔔 KHÁCH ZALO CẦN SẾP TRẢ LỜI\n"
                    f"Khách: {name or '(không rõ tên)'} · thread {thread_id}\n"
                    f"Khách hỏi: {text}\n\n"
                    "Bot đã báo khách chờ. Sếp trả lời giúp nhé."
                )
            except Exception as e:
                _log(f"notify owner fail: {e}")
            return
        self.replied += 1
        await self._send(thread_id, reply)
        await self._log_qa(text, reply, thread_id, name or "")

    def _parse(self, p: dict):
        """Rút threadId + text + is_self + tên khách từ payload webhook của `zalo listen`.
        Schema thật (event message): {event, threadId, type, isSelf, uidFrom, dName, content}.
        content là string với tin text, là object với đính kèm (bỏ qua). Có fallback phòng đổi version."""
        if not isinstance(p, dict):
            return None, None, False, None
        # message event phẳng; friend/group event lồng trong 'data' -> ưu tiên field phẳng của message
        thread = (p.get("threadId") or p.get("thread_id") or p.get("uidFrom") or p.get("fromId"))
        content = p.get("content")
        if content is None:
            content = p.get("text") or p.get("message") or p.get("body") or ""
        text = content if isinstance(content, str) else ""   # chỉ trả lời tin dạng text
        is_self = bool(p.get("isSelf") or p.get("self") or p.get("fromMe"))
        name = p.get("dName") or p.get("displayName") or p.get("name")
        return (str(thread) if thread else None), (text.strip() if text else None), is_self, name

    # ---------- vòng đời listener ----------
    def start(self) -> dict:
        if self.proc and self.proc.poll() is None:
            return {"ok": True, "status": "running", "note": "đã chạy sẵn"}
        self.home = self._zalo_home()
        if not self.home:
            self.status = "no-account"
            self.last_error = "Chưa có tài khoản Zalo kết nối"
            return {"ok": False, "status": self.status, "error": self.last_error}
        port = os.getenv("BOSS_PORT", "7777")
        args = [
            "npx", "-y", "zalo-agent-cli", "listen",
            "--events", "message", "--filter", "user", "--no-self",
            "--webhook", f"http://127.0.0.1:{port}/hooks/zalo",
        ]
        try:
            self.proc = subprocess.Popen(
                args, env=self._zalo_env(),
                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as e:
            self.status = "error"
            self.last_error = f"{type(e).__name__}: {e}"
            return {"ok": False, "status": self.status, "error": self.last_error}
        self.status = "running"
        self.last_error = ""
        self.started_at = time.time()
        _log(f"listener started pid={self.proc.pid} home={self.home}")
        return {"ok": True, "status": "running", "pid": self.proc.pid}

    def stop(self) -> dict:
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except Exception:
                    self.proc.kill()
            except Exception as e:
                _log(f"stop error: {e}")
        self.proc = None
        self.status = "off"
        return {"ok": True, "status": "off"}

    def info(self) -> dict:
        running = bool(self.proc and self.proc.poll() is None)
        if not running and self.status == "running":
            self.status = "error"
            self.last_error = self.last_error or "listener đã thoát"
        return {
            "status": self.status, "running": running,
            "agent_name": self.agent_name, "agent_role": self.agent_role,
            "home": self.home, "replied": self.replied,
            "escalated": self.escalated, "last_error": self.last_error,
            "sheet_webhook": bool(os.getenv("ZALO_SHEET_WEBHOOK", "").strip()),
        }


def register(app, deps: ZaloRTDeps) -> ZaloRealtime:
    feat = ZaloRealtime(deps)

    @app.post("/hooks/zalo")
    async def zalo_webhook(request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        # trả nhanh cho listener, xử lý nền
        asyncio.create_task(feat.handle_event(payload))
        return {"ok": True}

    @app.post("/zalo-rt/start")
    async def zalo_rt_start():
        return feat.start()

    @app.post("/zalo-rt/stop")
    async def zalo_rt_stop():
        return feat.stop()

    @app.get("/zalo-rt/status")
    async def zalo_rt_status():
        return feat.info()

    # tự bật khi khởi động nếu ZALO_REALTIME=1 và có tài khoản Zalo.
    # Delay ~6s để uvicorn kịp lắng nghe cổng (listener bắn webhook về 127.0.0.1).
    if os.getenv("ZALO_REALTIME", "").strip() in ("1", "true", "on"):
        import threading
        def _delayed_start():
            try:
                feat.start()
            except Exception as e:
                _log(f"auto-start fail: {e}")
        threading.Timer(6.0, _delayed_start).start()

    return feat
