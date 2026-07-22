# DAS OS — hồ sơ dự án

**Hệ điều hành AI cho người sáng lập.** Một CEO điều hành công ty qua một trí tuệ nhân tạo của riêng mình: chat/voice ra lệnh, đội bot thực thi, mọi bot uống chung một bộ não (DAS BRAIN). Web app chạy tại **os.das.vn**. Trạng thái: **LIVE**, đang phát triển tiếp.

Tên kỹ thuật trong code là **Boss OS** (repo `boss-os`) — Sếp gọi dự án là **DAS OS**.

## Code thật chạy ở đâu

| | |
|---|---|
| Máy Sếp (PC Windows) | `C:\Users\Minh Khoi\boss-os` |
| GitHub | `dascoach20/boss-os` (repo **DÙNG CHUNG**: Sếp + anh Đại + máy Mac + máy PC) |
| Web production | **os.das.vn** — Hostinger VPS, chạy bằng Docker |

⚠️ **Repo dùng chung** → luật vàng: **`git pull` trước khi sửa, `push` ngay sau khi xong**. Không pull trước là đè code của nhau.

## Dựng lại từ số 0 (cháy máy thì làm theo đây)

**Cách nhanh nhất — chạy trên VPS (giống production):**
1. hPanel Hostinger → VPS → **Docker Manager** → **Compose** → **Compose from URL**.
2. Dán: `https://raw.githubusercontent.com/dascoach20/boss-os/main/docker-compose.hostinger.yml`
3. Ô **Environment** đặt `DOMAIN_NAME=<tên miền>` (muốn HTTPS), rồi bấm **Deploy**, đợi 1-3 phút.
4. Lần đầu mở app: màn hình hỏi tạo tài khoản admin.
5. Vào terminal container đăng nhập Claude 1 lần: `claude auth login --claudeai`.

**Chạy trên máy Windows (không Docker):**
1. Cài **Python 3.12** + **Node 22**, rồi `npm i -g @anthropic-ai/claude-code`.
2. Lấy code: `git clone https://github.com/dascoach20/boss-os.git` (hoặc chép `ma-nguon/` trong kho này ra ổ C — **đừng chạy thẳng từ Drive**).
3. Trong thư mục dự án chạy `setup.bat` **một lần** (tạo `.venv` + cài thư viện).
4. `start-boss.bat` để chạy nền (tắt: `stop-boss.bat`).
5. Mở `http://localhost:7777`.

**Cập nhật bản mới lên web:** Docker Manager → **Redeploy** (KHÔNG dùng nút cập nhật trong app — Hostinger chặn Docker socket). Dữ liệu brain giữ nguyên trong volume.

## 🔑 Chìa khoá — KHO KHÔNG CHỨA, lấy lại ở đây

Tin mừng: **dự án này gần như không cần chìa khoá.** Bộ não chạy bằng **gói Claude Code CLI** của Sếp, không dùng API key trả tiền riêng.

| Cần gì | Lấy ở đâu | Ghi chú |
|---|---|---|
| Đăng nhập Claude | Chạy `claude auth login --claudeai` | Dùng tài khoản Claude Max của Sếp. **KHÔNG cần `ANTHROPIC_API_KEY`** |
| Tài khoản admin Boss OS | Tự tạo lúc mở app lần đầu (hoặc đặt `BOSS_ADMIN_USER` / `BOSS_ADMIN_PASSWORD` khi deploy) | Mã thiết lập lần đầu in trong log server |
| MCP (GoHighLevel, YouTube, Gmail...) | Cài vào Claude Code — Boss OS **tự kế thừa** | Xem `docs/09-mcp-va-so-lieu.md` |
| SSH key vào VPS | **Chỉ có trên máy Mac** | Trên PC không cần: cập nhật web bằng nút **Redeploy** |
| `WATCHTOWER_TOKEN` (tuỳ chọn) | Tự đặt chuỗi ngẫu nhiên | Chỉ cần nếu bật nút cập nhật 1-click |

File `env.example` trong mã nguồn liệt kê đầy đủ các biến — **mọi dòng để trống vẫn chạy được**.

## Thứ KHÔNG có trong kho (và vì sao)

| Bị loại | Vì sao |
|---|---|
| `.git/` | Lịch sử nằm trên GitHub (`dascoach20/boss-os`), clone lại là có |
| `.venv/`, `__pycache__/` | Máy tự sinh — chạy `setup.bat` là dựng lại |
| `data/`, `state/`, `logs/` | Dữ liệu chạy + state runtime, tái sinh được và **có thể chứa thông tin khách** |
| `.env` | Luật kho: không chứa chìa khoá (repo này vốn cũng không có `.env`) |
| Dữ liệu **DAS BRAIN** thật | Nằm ngoài repo (volume trên VPS / vault riêng). Sao lưu brain bằng chức năng **Sao lưu GitHub** trong app — xem `docs/18-sao-luu-github.md` |

## Bản đồ tài liệu

`docs/` có **18 tài liệu hướng dẫn** (01 thiết lập → 18 sao lưu), đọc `docs/README.md` trước để biết mở file nào. Một số mục quan trọng:

- `docs/03-do-thi-tri-thuc-3d.md` — **quả cầu tri thức 3D** (đồ thị DAS BRAIN)
- `docs/07-agents-va-workflows.md` — agent + workflow
- `docs/09-mcp-va-so-lieu.md` — đấu MCP để lấy số liệu thật
- `docs/13-second-brain-bo-nho-wiki.md` — Second Brain, bộ nhớ, wiki
- `docs/16-cau-hinh-env.md` — cấu hình
- `docs/17-khac-phuc-su-co.md` — khắc phục sự cố

⚠️ Dự án **chưa có `docs/doc_map.md`** (mục lục 3 tầng kiểu `/vebando`). Muốn có bản đồ chuẩn thì chạy `/vebando` — nhưng lưu ý đây là repo chung, nên bàn với anh Đại trước khi đụng `CLAUDE.md` (file đó là **system-prompt của chính app**, không phải luật cho AI lập trình).

## Đang làm dở (07/2026)

- **Giao diện Globe**: đã đổi theme tối + dock đáy + panel kính (stage 1-3) và **Agent Pods** ở trang Agents (pod kính, đèn trạng thái, nút Giao việc chạy agent ở **chế độ an toàn** — chặn Bash/Web, cô lập MCP tiền/đơn).
- **Quả cầu tri thức**: đã **viết lại engine** `dashboard/graph3d.js` từ kiểu "đám mây tự bung" (ForceGraph3D) sang **lồng cầu lưới neon** (kinh/vĩ tuyến + vành xích đạo + sao màu theo cụm + tia nan hoa + nhân thở), bám bản thiết kế `dasbrainnebula`. Dữ liệu thật qua `/graph`, cập nhật realtime qua WebSocket `/ws/graph`. Bản engine cũ giữ ở `dashboard/graph3d.forcegraph.bak.js`.
- **Còn lại**: ghép thẻ chi tiết nổi + nút bật/tắt hiệu ứng vào app thật, rồi deploy.
