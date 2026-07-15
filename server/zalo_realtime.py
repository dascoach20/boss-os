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
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import httpx
from fastapi import Request

from claude_cli import find_claude_cli
import mcp_store


def _log(msg: str) -> None:
    print(f"[zalo-rt] {msg}", file=sys.stderr, flush=True)


# ---- Tin nhắn cố định (Sếp chỉnh lời tuỳ ý ở đây) ----
# Chỉ còn tin TRẤN AN khi sinh câu trả lời lâu (>REASSURE_AFTER_S). BỎ tin "đã nhận" mỗi lượt
# (gây lặp/robot khi reply đã nhanh ~6s) - câu trả lời thật chính là sự tiếp nhận.
REASSURE_MSG = "Anh/chị chờ em xíu nhé, em đang tổng hợp thông tin để trả lời anh/chị cho kỹ ạ 🙏"

REASSURE_AFTER_S = 8.0        # sinh câu trả lời lâu hơn ngần này (giây) -> gửi tin giữ nhịp ngay
                              # (khách thấy được tiếp nhận liền, khỏi tưởng bot đứng hình)
REPLY_MAX_WALL_S = 180.0      # trần thời gian Claude sinh 1 câu trả lời
ESCALATE_TOKEN = "[[ESCALATE]]"


def _reply_system_prompt(agent_name: str, agent_role: str, kb: str = "", history: str = "") -> str:
    """Nhân cách NHÂN VIÊN TƯ VẤN BÁN HÀNG chủ động (generic, KHÔNG gắn công ty cụ thể) - ấm áp, khéo,
    luôn DẪN DẮT khách tiến tới ĐẶT LỊCH / để lại thông tin. Mọi thông tin công ty/sản phẩm lấy từ KB
    (biến ZALO_KB_FILE) - giữ code dùng chung cho mọi đơn vị, dữ liệu riêng nằm ở KB của từng nơi."""
    base = (
        f"Bạn là {agent_name}, {agent_role} - một người TƯ VẤN BÁN HÀNG chủ động, ấm áp và khéo léo. "
        "Bạn đang chat trực tiếp với khách trên Zalo như một nhân viên thật (không bao giờ tự nhận là AI/bot).\n"
        "MỌI thông tin về công ty, sản phẩm, giá, chính sách -> CHỈ lấy từ phần 'THÔNG TIN ĐỂ TƯ VẤN' bên dưới. "
        "Nếu phần đó trống hoặc thiếu thông tin cần thiết -> TUYỆT ĐỐI KHÔNG bịa; hãy chào hỏi lịch sự, khai thác "
        "nhu cầu và mời khách để lại thông tin/đặt lịch để được tư vấn chính xác.\n\n"
        "MỤC TIÊU MỖI CÂU TRẢ LỜI: đưa khách tiến GẦN HƠN tới đặt lịch tư vấn hoặc để lại tên + SĐT + nhu cầu.\n"
        "PHONG CÁCH: tiếng Việt, xưng 'em', gọi khách 'anh/chị', NGẮN GỌN - tự nhiên - có cảm xúc "
        "(2-4 câu, KHÔNG markdown, không dài dòng máy móc).\n"
        "NGUYÊN TẮC (rất quan trọng):\n"
        "1. KHÔNG lặp lại lời chào/giới thiệu nếu đã chào ở tin trước (nhìn LỊCH SỬ bên dưới). Vào thẳng nội dung.\n"
        "2. LUÔN kết bằng 1 câu HỎI KHƠI GỢI hoặc 1 lời MỜI HÀNH ĐỘNG - khai thác: khách đang làm gì, "
        "mong muốn/khó khăn gì, để tư vấn đúng và dẫn tới bước tiếp theo.\n"
        "3. Khi khách quan tâm/muốn đăng ký -> CHỦ ĐỘNG chốt: xin tên + SĐT + khung giờ tiện để bên em gọi/đặt "
        "lịch tư vấn cụ thể. Tạo giá trị & lý do nên tư vấn sớm.\n"
        "4. Khi bạn CHƯA biết chi tiết (giá chính xác, lịch khai giảng, cam kết cụ thể): ĐỪNG chỉ nói 'chờ'. "
        "Hãy vẫn giữ nhịp bán hàng: 'để em kết nối anh/chị với chuyên gia tư vấn để báo chính xác nhất, "
        "anh/chị cho em xin SĐT và giờ tiện nhé' -> lấy thông tin/đặt lịch. TUYỆT ĐỐI KHÔNG bịa giá/cam kết.\n"
        "5. Chỉ khi khách MUỐN gặp người thật, khiếu nại nặng, hoặc yêu cầu vượt tầm -> vẫn trả lời khách tử tế + "
        "xin thông tin, RỒI thêm token " + ESCALATE_TOKEN + " ở CUỐI (để báo quản lý follow-up). "
        "Token này khách KHÔNG thấy.\n"
        "Output CHỈ là lời nhắn gửi khách (kèm " + ESCALATE_TOKEN + " ở cuối nếu cần người thật tiếp)."
    )
    if kb.strip():
        base += ("\n\n=== THÔNG TIN ĐỂ TƯ VẤN (chỉ dùng thông tin có ở đây; thiếu thì mời đặt lịch tư vấn) ===\n"
                 + kb.strip())
    if history.strip():
        base += ("\n\n=== LỊCH SỬ HỘI THOẠI GẦN ĐÂY (để KHÔNG lặp lại, trả lời tiếp mạch) ===\n"
                 + history.strip())
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
        self.agent_role = os.getenv("ZALO_AGENT_ROLE", "nhân viên tư vấn & chăm sóc khách hàng").strip() \
            or "nhân viên tư vấn & chăm sóc khách hàng"
        self.status = "off"          # off | running | no-account | error
        self.last_error = ""
        self.started_at = 0.0
        self.replied = 0
        self.escalated = 0
        # chống trùng: msgId đã xử lý (webhook/listener có thể bắn 1 tin >1 lần)
        self._seen_ids: deque = deque(maxlen=2000)
        # serialize theo từng khách (không trả lời song song 2 tin cùng thread -> tránh trả lời chồng)
        self._thread_locks: dict[str, asyncio.Lock] = {}
        # lịch sử hội thoại ngắn theo thread (để không lặp lời chào + trả lời tiếp mạch)
        self._history: dict[str, deque] = {}
        # NHÓM được phép tự trả lời (env ZALO_GROUP_ALLOW, id cách nhau dấu phẩy). DM luôn trả lời;
        # nhóm chỉ trả lời khi id nằm trong đây -> chặn bot nhảy vào hàng chục nhóm cộng đồng nick
        # đang tham gia. Trống = KHÔNG đụng nhóm nào, chỉ trả lời chat riêng.
        self.allow_groups = {g.strip() for g in
                             os.getenv("ZALO_GROUP_ALLOW", "").replace(";", ",").split(",") if g.strip()}

    # ---------- tìm tài khoản Zalo đã kết nối ----------
    def _home_freshness(self, home: str) -> float:
        """Độ 'tươi' của 1 home = thời điểm credential được cập nhật gần nhất (lần quét QR /
        hoạt động Zalo mới nhất). Home vừa quét QR luôn tươi nhất -> chính là PHIÊN ĐANG SỐNG.
        Zalo chỉ cho 1 phiên/tài khoản: quét QR lại đá phiên cũ ra, home cũ 'đứng hình' mtime."""
        best = 0.0
        try:
            cred = os.path.join(home, ".zalo-agent-cli")
            for base in (home, cred):
                try:
                    best = max(best, os.path.getmtime(base))
                except OSError:
                    pass
            if os.path.isdir(cred):
                for name in os.listdir(cred)[:80]:
                    try:
                        best = max(best, os.path.getmtime(os.path.join(cred, name)))
                    except OSError:
                        pass
        except Exception:
            pass
        return best

    def _zalo_home(self, account: str = "") -> Optional[str]:
        """HOME cô lập chứa credential Zalo (đã quét QR) của MỘT tài khoản.

        account rỗng = tài khoản mặc định cho listener realtime -> BÁM NICK MỚI ĐĂNG NHẬP GẦN NHẤT
        (phiên đang sống), KHÔNG lấy mù nick đầu danh sách. Vì mỗi lần quét QR đẻ ra 1 home mới nối
        vào CUỐI list; nick cũ (đã bị đá khỏi phiên) vẫn đứng đầu -> lấy accts[0] sẽ trỏ nhầm nick
        chết. ZALO_HOME (nếu đặt tay) chỉ là 1 ứng viên, cũng phải TƯƠI nhất mới thắng -> pin cũ
        không còn bẫy được listener.
        account có giá trị = CHỌN đúng nick theo id / slug / tên gợi nhớ (label) - dùng cho
        hành động poll/@All/nhắc hẹn để không bị ép chạy bằng nick đầu tiên.
        KHÔNG đòi connection 'enabled' (credential/home vẫn còn khi user tắt Zalo MCP)."""
        env_home = os.getenv("ZALO_HOME", "").strip()
        try:
            accts = mcp_store.zalo_accounts()
        except Exception as e:
            _log(f"zalo_home error: {e}")
            accts = []
        # --- nick chỉ định (poll/@All/nhắc hẹn) ---
        if account:
            if not accts:
                return None
            a = account.strip().lower()
            hit = (next((x for x in accts if a in (str(x.get("id") or "").lower(),
                                                   str(x.get("slug") or "").lower(),
                                                   str(x.get("label") or "").lower())), None)
                   or next((x for x in accts if a in str(x.get("label") or "").lower()), None))
            return hit["home"] if hit else None
        # --- listener/mặc định: chọn home TƯƠI nhất còn tồn tại (phiên đang đăng nhập) ---
        candidates = [x["home"] for x in accts if x.get("home")]
        if env_home and env_home not in candidates:
            candidates.append(env_home)
        existing = [h for h in candidates if os.path.isdir(h)]
        if existing:
            best = max(existing, key=self._home_freshness)
            _log(f"home mặc định (tươi nhất) = {best}")
            return best
        # không home nào còn trên đĩa -> fallback giữ tương thích cũ
        if env_home:
            return env_home
        return accts[0]["home"] if accts else None

    def list_accounts(self) -> dict:
        """Trả danh sách tài khoản Zalo (id/tên/slug) để biết truyền 'account' nào cho hành động."""
        try:
            accts = mcp_store.zalo_accounts()
            return {"ok": True, "accounts": [{"id": x.get("id"), "name": x.get("label"),
                                              "slug": x.get("slug")} for x in accts]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _zalo_env(self) -> dict:
        env = dict(os.environ)
        if self.home:
            env["HOME"] = self.home
            env["USERPROFILE"] = self.home
        return env

    # ---------- gửi tin Zalo (đồng bộ, chạy trong thread) ----------
    def _send_sync(self, thread_id: str, text: str, thread_type: int = 0) -> None:
        # thread_type: 0 = chat riêng (User), 1 = nhóm (Group). Nhóm PHẢI có -t 1 mới vào đúng nhóm.
        try:
            subprocess.run(
                ["npx", "-y", "zalo-agent-cli", "msg", "send", str(thread_id), text,
                 "-t", str(int(thread_type))],
                env=self._zalo_env(), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                timeout=60, check=False,
            )
        except Exception as e:
            _log(f"send fail thread={thread_id}: {e}")

    async def _send(self, thread_id: str, text: str, thread_type: int = 0) -> None:
        if not text:
            return
        await asyncio.to_thread(self._send_sync, thread_id, text, thread_type)

    # ---------- HÀNH ĐỘNG THẬT trên Zalo (poll / @All / reminder / list nhóm) ----------
    # Gọi thẳng subcommand của zalo-agent-cli (MCP chỉ có send/get, nên phải dùng CLI).
    def _run_cli_sync(self, args: list, account: str = "") -> tuple:
        """Chạy 1 lệnh zalo-agent-cli (kèm --json) bằng credential của MỘT nick. Trả (ok, data, err).
        account rỗng = nick mặc định; có giá trị = chọn nick theo id/slug/tên."""
        home = self._zalo_home(account) if account else (self.home or self._zalo_home())
        if not home:
            if account:
                return False, None, f"Không tìm thấy tài khoản Zalo '{account}' (xem /zalo/accounts)"
            return False, None, "Chưa có tài khoản Zalo kết nối (quét QR ở trang Kết nối)"
        env = dict(os.environ)
        env["HOME"] = home
        env["USERPROFILE"] = home
        try:
            p = subprocess.run(
                ["npx", "-y", "zalo-agent-cli", *[str(a) for a in args], "--json"],
                env=env, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=90, check=False,
            )
        except Exception as e:
            return False, None, f"{type(e).__name__}: {e}"
        out = (p.stdout or "").strip()
        data = out
        if out:
            try:
                data = json.loads(out)
            except Exception:
                data = out
        if p.returncode != 0:
            return False, data, ((p.stderr or out or f"exit {p.returncode}")[:500])
        return True, data, ""

    async def _run_cli(self, args: list, account: str = "") -> dict:
        ok, data, err = await asyncio.to_thread(self._run_cli_sync, args, account)
        return {"ok": ok, "data": data, "error": err}

    async def create_poll(self, group_id: str, question: str, options: list, *,
                          multi: bool = False, anonymous: bool = False,
                          hide_preview: bool = False, expire_min: int = 0, account: str = "") -> dict:
        """Tạo POLL thật trong nhóm: poll create <groupId> <question> <opt...>."""
        opts = [str(o).strip() for o in (options or []) if str(o).strip()]
        if not group_id or not question or len(opts) < 2:
            return {"ok": False, "error": "Cần group_id, question và tối thiểu 2 lựa chọn"}
        args = ["poll", "create", group_id, question, *opts]
        if multi:
            args.append("--multi")
        if anonymous:
            args.append("--anonymous")
        if hide_preview:
            args.append("--hide-preview")
        if expire_min and int(expire_min) > 0:
            args += ["--expire", str(int(expire_min))]
        return await self._run_cli(args, account)

    async def send_mention_all(self, group_id: str, text: str, *, account: str = "") -> dict:
        """Gửi tin có tag @All THẬT: đặt '@All' đầu tin, mention pos=0 uid=-1 len=4 (-1 = tất cả)."""
        text = (text or "").strip()
        if not group_id or not text:
            return {"ok": False, "error": "Cần group_id và text"}
        tag = "@All"
        full = f"{tag} {text}"
        args = ["msg", "send", group_id, full, "-t", "1", "--mention", f"0:-1:{len(tag)}"]
        return await self._run_cli(args, account)

    async def create_reminder(self, thread_id: str, title: str, *, when: str = "",
                              group: bool = True, repeat: str = "none", emoji: str = "⏰",
                              account: str = "") -> dict:
        """Tạo NHẮC HẸN thật: reminder create <threadId> <title> [--time "YYYY-MM-DD HH:mm"] [-t 0|1] [--repeat]."""
        title = (title or "").strip()
        if not thread_id or not title:
            return {"ok": False, "error": "Cần thread_id và title"}
        args = ["reminder", "create", thread_id, title, "-t", "1" if group else "0"]
        if when and when.strip():
            args += ["--time", when.strip()]
        if repeat and repeat != "none":
            args += ["--repeat", repeat]
        if emoji:
            args += ["--emoji", emoji]
        return await self._run_cli(args, account)

    async def list_groups(self, account: str = "") -> dict:
        """Liệt kê nhóm Zalo (tên + id) của 1 nick để biết group_id: group list."""
        return await self._run_cli(["group", "list"], account)

    # ---------- sinh câu trả lời bằng Claude (chỉ đọc) ----------
    async def _generate(self, question: str, history: str = "") -> str:
        # KB khách-an-toàn (tuỳ chọn) - 1 file FAQ do Sếp biên tập, KHÔNG phải brain nội bộ.
        kb = ""
        kbf = os.getenv("ZALO_KB_FILE", "").strip()
        if kbf:
            try:
                kb = Path(kbf).read_text(encoding="utf-8")[:20000]
            except Exception as e:
                _log(f"KB read fail: {e}")
        claude = find_claude_cli()
        if not claude:
            return ESCALATE_TOKEN
        sys_prompt = _reply_system_prompt(self.agent_name, self.agent_role, kb, history)
        prompt = f"Khách hàng vừa nhắn trên Zalo:\n\"\"\"\n{question}\n\"\"\"\nTrả lời khách."
        # Gọi claude TRỰC TIẾP kiểu 'text' (KHÔNG dùng ClaudeCLI: tránh --dangerously-skip-permissions
        # + stream-json làm CLI treo khi .claude.json ở trạng thái first-run trong container).
        # KHÔNG dùng tool (reply thuần) -> nhanh (~4s) + không lộ dữ liệu nội bộ.
        args = [
            claude, "-p", prompt,
            "--model", (os.getenv("ZALO_MODEL", "sonnet") or "sonnet"),
            "--append-system-prompt", sys_prompt,
            "--output-format", "text",
            "--disallowedTools", "Read,Glob,Grep,Bash,Task,Write,Edit,NotebookEdit,WebFetch,WebSearch",
        ]
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *args, cwd=os.getenv("ZALO_CWD", "/tmp"),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=REPLY_MAX_WALL_S)
        except asyncio.TimeoutError:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            _log("generate timeout")
            return ESCALATE_TOKEN
        except Exception as e:
            _log(f"generate error: {type(e).__name__}: {e}")
            return ESCALATE_TOKEN
        text = (out or b"").decode("utf-8", "replace").strip()
        if not text:
            _log(f"generate empty; stderr={(err or b'').decode('utf-8','replace')[:200]}")
            return ESCALATE_TOKEN
        return text

    async def _generate_with_reassurance(self, thread_id: str, question: str, history: str = "",
                                         thread_type: int = 0) -> str:
        """Sinh câu trả lời; nếu lâu hơn REASSURE_AFTER_S thì gửi tin trấn an giữa chừng."""
        task = asyncio.create_task(self._generate(question, history))
        done, _ = await asyncio.wait({task}, timeout=REASSURE_AFTER_S)
        if task not in done:
            await self._send(thread_id, REASSURE_MSG, thread_type)
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
        thread_id, text, is_self, name, msgid, is_group = self._parse(payload)
        if not thread_id or not text or is_self:
            return
        # NHÓM: chỉ tự trả lời nhóm nằm trong allowlist (ZALO_GROUP_ALLOW) -> tránh spam hàng chục
        # nhóm cộng đồng nick đang tham gia. DM (chat riêng) luôn trả lời.
        if is_group and thread_id not in self.allow_groups:
            _log(f"bỏ qua tin nhóm ngoài allowlist: thread={thread_id}")
            return
        thread_type = 1 if is_group else 0
        # (a) CHỐNG TRÙNG: cùng msgId đã xử lý -> bỏ (listener/webhook đôi khi bắn lặp)
        if msgid:
            if msgid in self._seen_ids:
                return
            self._seen_ids.append(msgid)
        # (b) SERIALIZE theo khách: 1 thread chỉ xử lý 1 tin 1 lúc -> tránh trả lời chồng lên nhau
        lock = self._thread_locks.get(thread_id)
        if lock is None:
            lock = asyncio.Lock()
            self._thread_locks[thread_id] = lock
        async with lock:
            hist = self._history.get(thread_id)
            history_str = "\n".join(hist) if hist else ""
            # sinh câu trả lời (KHÔNG gửi ACK riêng nữa - câu trả lời ~6s chính là sự tiếp nhận;
            # chỉ gửi tin trấn an nếu > REASSURE_AFTER_S)
            reply = await self._generate_with_reassurance(thread_id, text, history_str, thread_type)
            escalate = bool(reply) and ESCALATE_TOKEN in reply
            reply = (reply or "").replace(ESCALATE_TOKEN, "").strip()
            if not reply:
                # sinh lỗi/rỗng -> vẫn giữ khách + báo Sếp
                reply = ("Dạ em ghi nhận rồi ạ, em nhờ chuyên gia bên em tư vấn kỹ hơn cho anh/chị. "
                         "Anh/chị cho em xin số điện thoại và giờ tiện để bên em gọi lại tư vấn cụ thể nhé ạ 🙏")
                escalate = True
            await self._send(thread_id, reply, thread_type)
            await self._log_qa(text, reply, thread_id, name or "")
            # cập nhật lịch sử hội thoại (giữ 6 lượt gần nhất)
            h = self._history.setdefault(thread_id, deque(maxlen=6))
            h.append(f"Khách: {text}")
            h.append(f"{self.agent_name}: {reply}")
            if escalate:
                self.escalated += 1
                try:
                    await self.deps.notify_owner(
                        "🔔 KHÁCH ZALO CẦN SẾP TIẾP\n"
                        f"Khách: {name or '(không rõ tên)'} · thread {thread_id}\n"
                        f"Khách hỏi: {text}\n"
                        f"{self.agent_name} đã trả lời & xin thông tin. Sếp vào tiếp/duyệt giúp nhé."
                    )
                except Exception as e:
                    _log(f"notify owner fail: {e}")
            else:
                self.replied += 1

    def _parse(self, p: dict):
        """Rút threadId + text + is_self + tên khách + is_group từ payload webhook của `zalo listen`.
        Schema thật (event message): {event, threadId, type, isSelf, uidFrom, dName, content}.
        type: 0/'user' = chat riêng, 1/'group' = nhóm. content là string với tin text, là object với
        đính kèm (bỏ qua). Có fallback phòng đổi version."""
        if not isinstance(p, dict):
            return None, None, False, None, None, False
        # message event phẳng; friend/group event lồng trong 'data' -> ưu tiên field phẳng của message
        thread = (p.get("threadId") or p.get("thread_id") or p.get("uidFrom") or p.get("fromId"))
        content = p.get("content")
        if content is None:
            content = p.get("text") or p.get("message") or p.get("body") or ""
        text = content if isinstance(content, str) else ""   # chỉ trả lời tin dạng text
        is_self = bool(p.get("isSelf") or p.get("self") or p.get("fromMe"))
        name = p.get("dName") or p.get("displayName") or p.get("name")
        msgid = p.get("msgId") or p.get("cliMsgId") or p.get("msgID") or p.get("id")
        ttype = p.get("type")
        if ttype is None:
            ttype = p.get("threadType") or p.get("thread_type") or p.get("isGroup")
        is_group = str(ttype).strip().lower() in ("1", "group", "true")
        return (str(thread) if thread else None), (text.strip() if text else None), is_self, name, \
            (str(msgid) if msgid else None), is_group

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
            "--events", "message", "--filter", "all", "--no-self",
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

    def restart(self) -> dict:
        """Dừng rồi bật lại listener để BÁM lại home mới nhất. Gọi khi vừa quét QR 1 nick mới
        (khôi phục/đổi nick trực khách) -> khỏi phải redeploy hay khởi động lại server bằng tay."""
        try:
            self.stop()
        except Exception as e:
            _log(f"restart-stop: {e}")
        r = self.start()
        _log(f"restart -> {r}")
        return r

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
            "allow_groups": sorted(self.allow_groups),
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
