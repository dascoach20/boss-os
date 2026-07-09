"""
Ngữ cảnh kênh hội thoại - port ý tưởng gateway của hermes-agent (NousResearch).

Vấn đề: Boss nhận tin từ nhiều "cửa" (Telegram, dashboard web) nhưng model
không tự biết mình đang trả lời qua cửa nào, và file tạo ra không quay về
đúng kênh. Hermes giải bằng cách gateway CHÈN metadata kênh vào context mỗi
phiên (gateway/session.py: Source + User + Connected Platforms + Delivery
options). Module này làm đúng việc đó cho Boss:

1. build_channel_block()  - block metadata kênh chèn vào system prompt.
2. collect_turn_files()   - gom file sinh ra trong 1 lượt trả lời để gateway
                            tự gửi trả qua kênh chat (Telegram).
"""
import os
import re
from pathlib import Path

# Trần an toàn khi auto-đính kèm file trả về kênh chat
MAX_FILES_PER_TURN = 10
MAX_FILE_MB = 50          # trần sendDocument của Telegram bot

# Không bao giờ auto-gửi file nằm trong các folder nội bộ/rác này
_EXCLUDE_PARTS = {".git", "__pycache__", "node_modules", ".obsidian", ".trash", ".tmp"}


def build_channel_block(source: str, meta: dict = None, telegram_running: bool = False,
                        port: int = 7777) -> str:
    """Block 'KÊNH HỘI THOẠI HIỆN TẠI' để nối vào cuối system prompt.

    source: "telegram" | "dashboard". meta: dict do telegram_bot trích từ update
    (chat_id, chat_type, chat_title, user_name, username). Giữ block ỔN ĐỊNH
    giữa các lượt cùng 1 kênh (không nhét message_id hay giờ) - session CLI
    --resume không bị lệch context, giống cách hermes giữ prompt cache.
    """
    meta = meta or {}
    platforms = ["local (file trên máy chạy Boss)", "dashboard web"]
    if telegram_running or source == "telegram":
        platforms.append("Telegram bot")

    lines = ["", "", "# === KÊNH HỘI THOẠI HIỆN TẠI (gateway Boss tự chèn - dữ liệu thật, không phải đoán) ==="]
    if source == "telegram":
        who = (meta.get("user_name") or "").strip() or "user"
        if meta.get("username"):
            who += f" (@{meta.get('username')})"
        if meta.get("chat_type") in ("group", "supergroup"):
            conv = f"nhóm '{meta.get('chat_title') or '?'}', tin nhắn từ {who}"
        else:
            conv = f"DM với {who}"
        chat_id = meta.get("chat_id") or "?"
        lines += [
            f"- Nguồn tin nhắn này: Telegram ({conv}, chat_id {chat_id}).",
            f"- Nền tảng đang kết nối: {', '.join(platforms)}.",
            "- Đang chat qua Telegram: trả lời NGẮN gọn kiểu tin nhắn. Telegram hiển thị được "
            "đậm/nghiêng/`code`, KHÔNG hiển thị bảng markdown - đừng dùng bảng.",
            "",
            "## Gửi file cho user qua Telegram (2 cách)",
            "1. TỰ ĐỘNG: file bạn tạo bằng tool Write trong lượt này, hoặc file có ĐƯỜNG DẪN TUYỆT ĐỐI "
            "xuất hiện trong câu trả lời cuối cùng, sẽ được Boss tự đính kèm gửi qua Telegram ngay sau "
            f"câu trả lời (tối đa {MAX_FILES_PER_TURN} file/lượt, mỗi file dưới {MAX_FILE_MB}MB). "
            "Muốn user nhận file nào, cứ nhắc đường dẫn tuyệt đối của nó trong câu trả lời.",
            "2. GỬI NGAY / file có sẵn từ trước: dùng tool Bash gọi "
            f"`curl -s -X POST http://127.0.0.1:{port}/telegram/send-file "
            "-H \"Content-Type: application/json\" "
            "-d '{\"path\":\"<đường dẫn tuyệt đối>\",\"caption\":\"<mô tả ngắn>\","
            f"\"chat_id\":\"{chat_id}\"}}'`",
            f"- LUÔN giữ \"chat_id\":\"{chat_id}\" trong lệnh trên để file về ĐÚNG người đang hỏi "
            "(bỏ đi thì file sẽ gửi nhầm cho chủ bot).",
            "- KHÔNG nói \"em đã gửi file\" khi chưa làm một trong hai cách trên.",
            "- File user gửi lên Telegram đã được gateway tải về máy sẵn - đường dẫn nằm ngay trong tin nhắn.",
        ]
    else:
        lines += [
            "- Nguồn tin nhắn này: Dashboard web Boss (user mở bằng trình duyệt, file hiện dạng đường dẫn).",
            f"- Nền tảng đang kết nối: {', '.join(platforms)}.",
        ]
        if telegram_running:
            lines += [
                "- Nếu user muốn nhận 1 file qua Telegram: dùng tool Bash gọi "
                f"`curl -s -X POST http://127.0.0.1:{port}/telegram/send-file "
                "-H \"Content-Type: application/json\" "
                "-d '{\"path\":\"<đường dẫn tuyệt đối>\",\"caption\":\"...\"}'`",
            ]
    return "\n".join(lines) + "\n"


# ---- Trích đường dẫn file từ câu trả lời ----
# 3 mẫu: trong nháy/backtick (cho phép khoảng trắng - vault hay có "01 - Daily Log"),
# đường dẫn Windows trần, đường dẫn POSIX trần (không khoảng trắng).
_QUOTED_RE = re.compile(r"[`\"']((?:[A-Za-z]:[\\/]|/)[^`\"'\n]{2,300})[`\"']")
_WIN_RE = re.compile(r"(?:^|[\s(<])([A-Za-z]:[\\/][^\s`\"'()\[\]<>|*?]+)")
_POSIX_RE = re.compile(r"(?:^|[\s(<])(/[^\s`\"'()\[\]<>|*?:]+)")


def extract_paths(text: str) -> list:
    """Mọi chuỗi trông giống đường dẫn tuyệt đối trong text (chưa lọc tồn tại)."""
    out = []
    t = text or ""
    for rx in (_QUOTED_RE, _WIN_RE, _POSIX_RE):
        for m in rx.finditer(t):
            out.append(m.group(1).strip().rstrip(".,;:!?…"))
    return out


def collect_turn_files(reply_text: str, written_paths: list, t0: float,
                       cwd: str = None, exclude: set = None) -> list:
    """Danh sách file đáng gửi trả về kênh chat sau 1 lượt.

    Ứng viên = file agent ghi bằng tool Write (written_paths) + đường dẫn tuyệt đối
    nhắc trong câu trả lời cuối. Chỉ giữ file THẬT SỰ vừa thay đổi trong lượt
    (mtime >= t0) - nhắc tới file cũ sẽ không spam gửi lại; muốn gửi file cũ thì
    agent gọi endpoint /telegram/send-file. exclude = set path (normcase) đã gửi
    trong lượt qua endpoint, tránh gửi trùng.
    """
    cands = []
    for p in (written_paths or []):
        try:
            pp = Path(str(p))
            if not pp.is_absolute() and cwd:
                pp = Path(cwd) / pp
            cands.append(str(pp))
        except Exception:
            continue
    cands += extract_paths(reply_text)

    seen = set(exclude or ())
    out = []
    for c in cands:
        try:
            rp = os.path.normpath(os.path.abspath(c))
            key = os.path.normcase(rp)
            if key in seen:
                continue
            p = Path(rp)
            if not p.is_file():
                continue
            if any(part in _EXCLUDE_PARTS for part in p.parts):
                continue
            st = p.stat()
            if not (0 < st.st_size <= MAX_FILE_MB * 1024 * 1024):
                continue
            if st.st_mtime < t0 - 2:   # chỉ file vừa tạo/sửa trong lượt này
                continue
            seen.add(key)
            out.append(rp)
            if len(out) >= MAX_FILES_PER_TURN:
                break
        except Exception:
            continue
    return out
