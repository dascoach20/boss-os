# -*- coding: utf-8 -*-
"""Chia hàng nút Telegram cho VỪA màn hình điện thoại - dùng chung cả đàn bot.

Sếp bắt lỗi 01/11 qua ảnh Lửng Đào: hàng 5 nút "📝 Tóm tắt kỹ · 💬 Mỏ từ bình luận ·
⭐ Lưu kho · 📥 Tải ảnh · 📋 Copy bản chép lời" hiện thành "Tó… Mở… Lư… Tải… Co…", không
đọc được. Telegram chia đều bề ngang cho mọi nút trong hàng rồi CẮT chữ, không tự xuống dòng.

Luật: mỗi hàng n nút thì mỗi nút được tối đa SUC_CHUA[n] "ô chữ" (emoji = 2 ô). Đo trên chính
ảnh Sếp gửi (iPhone dọc): 2 nút "🏗️ Tận dụng CẤU TRÚC" (21 ô) vừa khít, 5 nút thì "🔊 Nghe"
(7 ô) và "1.75" còn đủ còn "📝 Tóm tắt kỹ" (12 ô) bị cắt. Hàng nào có nút vượt sức chứa thì
tách thành nhiều hàng, GIỮ NGUYÊN thứ tự, và nhét được bao nhiêu nút mỗi hàng thì nhét.
Hàng vốn đã vừa thì để nguyên (không xáo bố cục người viết đã chọn)."""
import unicodedata

# n nút/hàng -> số ô chữ tối đa mỗi nút. Bề ngang ~46 ô, mỗi khe giữa 2 nút ~2,5 ô.
SUC_CHUA = {1: 44, 2: 21, 3: 13, 4: 9, 5: 7, 6: 5, 7: 4, 8: 3}


def do_rong(chu):
    """Số ô chữ khi hiển thị: emoji / chữ Hán = 2, dấu biến thể và dấu ghép = 0, còn lại = 1."""
    n = 0
    for c in str(chu or ""):
        o = ord(c)
        if o in (0xFE0F, 0xFE0E, 0x200D) or unicodedata.combining(c):
            continue
        if o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF \
                or unicodedata.east_asian_width(c) in ("W", "F"):
            n += 2
        else:
            n += 1
    return n


def _vua(hang):
    cap = SUC_CHUA.get(len(hang), 2)
    return all(do_rong(b.get("text")) <= cap for b in hang)


def xep_hang(ban_phim):
    """[[nút,...],...] -> [[nút,...],...] đã chia cho vừa. Đầu vào lạ thì trả nguyên."""
    if not isinstance(ban_phim, list):
        return ban_phim
    ra = []
    for hang in ban_phim:
        if not isinstance(hang, list) or not all(isinstance(b, dict) for b in hang) \
                or len(hang) <= 1 or _vua(hang):
            ra.append(hang)
            continue
        cur = []
        for b in hang:
            if cur and not _vua(cur + [b]):
                ra.append(cur)
                cur = []
            cur.append(b)
        if cur:
            ra.append(cur)
    return ra
