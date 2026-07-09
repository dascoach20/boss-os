# Nhật ký cập nhật

Lịch sử phiên bản Boss OS. Bản mới nhất ở trên cùng. Xem ngay trong app tại mục **Cập nhật** trên thanh bên trái.

Định dạng: mỗi phiên bản là một khối `## [x.y.z] - ngày`, bên dưới nhóm thay đổi theo `### Thêm mới / Sửa lỗi / Cải thiện / Bảo mật`.

## [1.0.8] - 2026-07-08
### Sửa lỗi
- **Nhãn graph vẫn vỡ font sau khi fix NFC ở server**: bổ sung chuẩn hoá NFC ngay tại client (lúc `graph3d.load()` nhận data + lúc vẽ concept label) → nhãn tiếng Việt hiển thị đúng dù server/trình duyệt còn trả NFD (thêm `cache:no-store` cho `/graph` để không dính cache cũ). Đồng thời vá `_node_payload` (nguồn node realtime qua WebSocket) — trước đó chưa chuẩn hoá nên node thêm realtime vẫn NFD (vỡ font + mất cạnh nối).

## [1.0.7] - 2026-07-08
### Sửa lỗi
- **Import brain từ zip (macOS): graph rời rạc + nhãn vỡ font**: zip tạo trên macOS lưu tên file dạng Unicode NFD (tách dấu) → tên hiển thị vỡ font (ký tự lạ ╠) và `[[wikilink]]` (NFD) so không khớp tên file → mất hết cạnh nối → node trôi rời rạc. Đã chuẩn hoá mọi tên (nhãn node, khoá so khớp wikilink, tên nhóm) về NFC trong graph_builder → node co cụm lại + nhãn tiếng Việt hiển thị đúng. (Đường dẫn file giữ nguyên để vẫn mở đúng note trên đĩa.)

## [1.0.6] - 2026-07-08
### Sửa lỗi
- **2 giọng đọc đè lên nhau**: khi trả lời có thể có 2 nguồn phát chạy song song (audio Edge của server + giọng dự phòng của trình duyệt, hoặc callback cũ khởi động audio mới). Ép chỉ 1 nguồn kêu tại một thời điểm: trước khi phát chunk mới thì dừng giọng browser + audio trước; đọc dự phòng chỉ chạy 1 lần (onerror + catch không còn bắn đôi); khi đọc bằng browser thì tạm dừng audio Edge.

## [1.0.5] - 2026-07-08
### Sửa lỗi
- **Tắt tiếng mà vẫn đọc**: nút loa chỉ chặn ở khâu xếp hàng, còn cỗ máy phát (Edge TTS đang tải/đang phát + bản đọc dự phòng của trình duyệt) không kiểm tra trạng thái tắt. Đã thêm chốt "còn bật tiếng?" vào mọi tầng phát và gia cố stopSpeaking → bấm tắt là im ngay.
- **Nút loa có icon gạch chéo khi tắt** (🔇) thay vì chỉ mờ đi → nhìn biết ngay đang bật hay tắt.
### Bảo mật
- **Đổi mật khẩu phải nhập đúng mật khẩu hiện tại**: thêm endpoint `/auth/change-password` xác thực mật khẩu cũ (trước đây ô đổi mật khẩu gọi `/auth/setup` và bị chặn khi đã có tài khoản → không đổi được). Mật khẩu mới tối thiểu 8 ký tự, phải khác mật khẩu cũ.
### Cải thiện
- **Form đổi mật khẩu rõ ràng**: tách 2 ô "Mật khẩu hiện tại" và "Mật khẩu mới" có nhãn riêng, hết mơ hồ.
- **Nút con mắt xem/ẩn mật khẩu** cho các ô mật khẩu thật (đăng nhập, đặt/đổi mật khẩu). Ô API key / token KHÔNG gắn mắt (thừa và làm vỡ layout thẻ provider).
- **Chuẩn hoá placeholder**: chữ cái đầu của các placeholder đều viết hoa.
- **Khu chat gọn hơn**: thêm đường kẻ phân cách dưới tiêu đề HỘI THOẠI (có khoảng thở); badge engine hiện đủ chữ (vd "CLI · mặc định", hết bị cắt); thanh nhập cân đối lề trên = lề dưới (~16px đều nhau) + đồng đều chiều cao 44px cho micro/đính kèm/ô nhập/gửi → hàng thẳng, hết so le.
- **Viền bong bóng trả lời** đổi sang tím thương hiệu (tách với bubble người dùng màu cam).
- **Font tên workspace**: đổi từ serif sang font hệ thống (-apple-system / BlinkMacSystemFont) cho gọn, hiện đại.
- **Ô nhập chat**: viền xám mặc định, chỉ sáng màu brand khi hover/focus (bỏ viền cam thường trực).
- **Hết cuộn ngang trong tin nhắn**: nội dung dài (code block, chuỗi dài) tự xuống dòng thay vì tràn ngang.
- **Đồng bộ viền tương tác toàn app**: mọi ô nhập khi hover/focus hiện viền màu brand, không còn viền đỏ.

## [1.0.4] - 2026-07-08
### Thêm mới
- **Nút "Cập nhật ngay" 1-bấm trên Hostinger**: bật Watchtower (fix API Docker) → khi có bản mới trên GitHub, app hiện nút cập nhật ngay trong Tổng quan, bấm là tự kéo bản mới, khỏi vào Docker Manager.

## [1.0.3] - 2026-07-08
### Sửa lỗi
- Sửa app.js bị bỏ sót khi đổi tên (có NUL byte nên bị coi là file nhị phân) → graph/số liệu không hiện; nay đồng bộ BossGraph3D, xoá NUL byte.

## [1.0.2] - 2026-07-08
### Cải thiện
- **Đồng bộ thương hiệu Boss OS 100% toàn bộ source** → thống nhất tên cũ sang Boss: biến môi trường, header nội bộ (X-Boss-Mode), thư mục vault (Boss/), user Docker (boss, /home/boss), tên biến/hàm code, skill (boss-builder), loop mẫu (tu-cai-tien-boss), file launcher, docs.

## [1.0.1] - 2026-07-08
### Thêm mới
- **Boss OS** - đổi thương hiệu hoàn chỉnh (giao diện, avatar robot, tên bot, theme tối ấm amber/violet, font Fraunces + Manrope).
### Cải thiện
- Sidebar: thu/mở, submenu Cài đặt xổ ra/vào, đổi Models AI / Kênh Bot.
- Orb trung tâm: quả cầu hạt nebula + hiệu ứng thở; nhãn danh mục không bị cắt mép.
- Khối chat gộp bên phải + footer trạng thái hệ thống; ô nhập viền amber.
### Sửa lỗi
- Kiểm tra cập nhật trỏ đúng repo của bạn; deploy Hostinger (cổng host, đường dẫn auth, tự tạo admin qua env).

## [0.9.6] - 2026-07-04
### Cải thiện
- **Trang Cài đặt gọn và hợp lý hơn**: gộp "Nhà cung cấp giọng đọc" vào chung nhóm Giọng nói (trước đây nằm tách tận cuối trang, sau avatar và tên miền); bỏ nút "Nghe thử" bị trùng (giữ 1 nút duy nhất); ẩn danh sách giọng Edge (HoaiMy/NamMinh) khi chọn provider OpenAI/ElevenLabs vì lúc đó chọn giọng ngay trong khối provider; sửa tiêu đề gây hiểu nhầm (bỏ "Giao diện" vì không có mục đó); nút nghe thử chuyển sang viền để nút Lưu nổi đúng vai trò chính.
- **Thông báo cập nhật bản Docker rõ ràng hơn**: bản Docker không bật Watchtower giờ hướng dẫn thẳng cách **Redeploy** để lấy image mới nhất (Hostinger bấm nút Redeploy trong Docker Manager; VPS chạy `docker compose up -d --pull always`), thay vì bảo "tự thêm service watchtower". Panel Phiên bản hiện luôn hướng dẫn này khi có bản mới mà không tự cập nhật tại chỗ được, không còn để bấm nút "Cập nhật ngay" rồi mới báo lỗi.
### Sửa lỗi
- Nút "Cập nhật ngay" trước đây coi là tự cập nhật được chỉ vì biến `WATCHTOWER_TOKEN` có sẵn trong compose (dù Watchtower chưa chạy), bấm vào trigger âm thầm thất bại rồi báo "phiên bản chưa đổi". Nay **dò Watchtower thật** (kiểm tra cổng, không gửi HTTP để khỏi kích hoạt update nhầm) mới quyết định, tránh báo nhầm.

## [0.9.5] - 2026-07-04
### Thêm mới
- **Lark** vào kho Kết nối (MCP chính chủ của Lark/LarkSuite, chạy local qua `@larksuiteoapi/lark-mcp`): nhắn tin, tài liệu (Docs), bảng dữ liệu (Base/Bitable), wiki, danh bạ. Tạo một Lark app rồi dán App ID + App Secret; Boss chỉ làm được đúng quyền bạn cấp cho app. Cần Node.js 18+. Mặc định Chỉ đọc; gửi tin nhắn và cấp quyền file là hành động nguy hiểm (phải Toàn quyền). Phân loại quyền theo 19 tool thật đã kiểm chứng.
- **Logo Zalo và Google Sheets**: hai connector này giờ hiện logo thật thay cho emoji.

## [0.9.4] - 2026-07-04
### Thêm mới
- **Slack** vào kho Kết nối (MCP chính chủ của Slack, remote): tìm/đọc/gửi tin, xem kênh và thành viên, quản lý canvas. Đăng nhập bằng OAuth qua một Slack app của chính bạn (Slack không cho tự đăng ký client, cần tạo app trong workspace + admin duyệt). Mặc định Chỉ đọc; gửi tin phải nâng Toàn quyền.
- **Systeme.io** vào kho Kết nối (MCP chính chủ, remote): quản lý liên hệ, tag, trường tuỳ biến, newsletter, phễu. Chỉ cần dán MCP key (tạo trong Cài đặt hồ sơ, hạn tối đa 90 ngày). Mặc định Chỉ đọc.
- **Logo thương hiệu cho connector**: các thẻ trong kho Kết nối giờ hiện logo thật (Pancake POS, Botcake, Webcake, Meta Ads, Google Calendar, Gmail, Slack, Systeme.io) thay cho biểu tượng emoji; connector chưa có logo vẫn dùng emoji như cũ.
### Cải thiện
- Nhánh OAuth explicit của hub nhận thêm 2 tinh chỉnh theo hãng: tên tham số scope và dấu ngăn (Slack dùng `user_scope` + dấu phẩy cho token người dùng, Google giữ `scope` + dấu cách) - để hỗ trợ đúng các nhà cung cấp OAuth không theo chuẩn chung.

## [0.9.3] - 2026-07-04
### Thêm mới
- **Kho Kết nối có Google Calendar và Gmail** (MCP chính chủ của Google, remote - chạy được cả trên VPS): Calendar xem lịch, tìm chỗ trống, tạo/sửa/xoá sự kiện; Gmail đọc/tìm thư, soạn NHÁP, gắn nhãn. Gmail bản chính chủ KHÔNG có tool gửi thẳng nên Boss luôn dừng ở bản nháp để bạn tự bấm gửi. Đăng nhập Google ngay trong dashboard; cần tạo OAuth client 1 lần (~10 phút, hướng dẫn từng bước trong cửa sổ kết nối, dùng chung 1 client cho cả hai). Mặc định Chỉ đọc; nâng lên Ghi nháp để tạo sự kiện/soạn nháp, Toàn quyền mới xoá được sự kiện.
### Cải thiện
- Hub OAuth giờ nhận **client tự khai (BYO client_id/secret)** cho nhà cung cấp không hỗ trợ tự đăng ký client như Google (trước đây chỉ chạy với server có DCR). Tự xin `access_type=offline` để giữ kết nối lâu dài (tự làm mới token), gửi kèm client secret khi đổi/làm mới token, và tự đặt tên tài khoản bằng email Google sau khi đăng nhập.

## [0.9.2] - 2026-07-04
### Thêm mới
- **Kho Kết nối có nhóm Quảng cáo - đủ 3 nền tảng lớn**: **Meta Ads** (Facebook & Instagram) qua MCP chính chủ của Meta - bấm Kết nối là đăng nhập Facebook, không cần tạo app hay dán key; **Google Ads** qua MCP chính chủ của Google (chỉ đọc, truy vấn GAQL: chi phí, chuyển đổi, từ khoá); **TikTok Ads** qua server cộng đồng trên Marketing API chính thức (chỉ đọc - TikTok chưa mở MCP chính chủ, khi mở sẽ thay trong kho). Cả 3 mặc định Chỉ đọc; Meta bật Toàn quyền mới tạo/sửa được chiến dịch (cảnh báo tiền thật, chiến dịch tạo mới luôn ở trạng thái tạm dừng chờ bạn tự bật).
### Cải thiện
- Kết nối OAuth (vd Meta Ads) sau khi đăng nhập giờ **tự đặt tên tài khoản** (lấy đúng tên tài khoản ads) như flow dán key, và ghi ngay profile MCP cho Codex - trước đây tên để mặc định và Codex phải đợi lần đổi cấu hình sau.

## [0.9.1] - 2026-07-04
### Sửa lỗi
- `start-boss.bat` chạy server ẩn hoàn toàn - hết cửa sổ CMD đen nằm lì.

## [0.9.0] - 2026-07-04
### Thêm mới
- **Trang "Kết nối" thay trang MCP**: kho connector cài sẵn (Pancake POS, Zalo cá nhân, Webcake Landing, Botcake) - bấm Kết nối, dán key (hoặc quét QR với Zalo) là xong, không còn tự gõ URL/transport/header. Boss tự kiểm tra key và tự đặt tên tài khoản (lấy đúng tên cửa hàng từ POS). Form kỹ thuật cũ vẫn còn ở card "Tự thêm (nâng cao)".
- **Đa tài khoản chính thức**: một dịch vụ nối NHIỀU tài khoản (nhiều shop POS, nhiều số Zalo) - mỗi tài khoản một chip có tên + quyền + dấu mặc định, thêm/tắt/xoá từng cái. Zalo mỗi tài khoản chạy cô lập (home riêng) nên nhiều số chạy song song không giẫm nhau.
- **MCP HUB**: mọi bộ não (Claude Code, ChatGPT/Codex, OpenRouter, OpenAI API, Anthropic API) đấu qua MỘT điểm - Codex và engine API giờ dùng được cả MCP local dạng stdio (Zalo, Webcake) chứ không chỉ http như trước.
- **Anthropic API có vòng gọi tool** - hết cảnh "chat thuần không MCP". Engine API còn được thêm tool đọc/ghi file trong vault, `boss_use_skill` (kích hoạt skill của brain) và `boss_connections` - engine nào cũng là agent thực thụ.
- **Phân quyền 3 mức mỗi kết nối** (Chỉ đọc / Ghi nháp / Toàn quyền) chặn CỨNG tại hub theo từng lời gọi, hiểu cả tool đa hành động kiểu Pancake (`action=list` cho qua, `action=create` chặn). Loop nền mode suggest/auto bị hub chặn hành động ghi/tiền-đơn bất kể prompt nói gì. Bật Toàn quyền phải tick xác nhận rủi ro; Zalo có cảnh báo riêng về nguy cơ bị khoá tài khoản (API không chính thức).
- **Nhật ký gọi tool (audit)** xem theo từng kết nối, nút Test lại, rate limit chống spam cho Zalo.
- **Đăng nhập Zalo bằng quét QR ngay trong dashboard**: Boss tự chạy zalo-agent-cli, hiện mã QR trong modal, quét xong tự tạo kết nối (cần Node.js 20+).
- **OAuth chuẩn MCP** (PKCE + tự đăng ký client): server nào theo chuẩn thì bấm Kết nối là xong ngay trên VPS, Boss tự giữ và tự refresh token - bỏ cảnh mở terminal gõ /mcp.
- Cầu nối **Botcake** tự viết qua Public API v1 (13 tool: khách hàng, tag, flow, gửi flow, keyword...) - không cần cài gì thêm.
- **3 card Google cho kinh doanh**: Google Sheets (đổ báo cáo doanh thu/tồn kho ra bảng tính - dán service account JSON là chạy, không cần đăng nhập), Google Search Console (số liệu SEO: khách tìm gì ra website), Google Workspace (Gmail + Lịch + Drive + Docs trong 1 kết nối, OAuth tự tạo có hướng dẫn từng bước; mặc định Ghi nháp - soạn nháp được nhưng KHÔNG tự gửi mail/xoá, bật Toàn quyền phải xác nhận). Kho hỗ trợ field dạng file (dán JSON, Boss tự lo phần còn lại) và tự kèm sẵn uv/uvx để chạy connector Python.
### Cải thiện
- MCP client có **session pool sống lâu** (giữ kết nối giữa các tin nhắn) + hỗ trợ stdio/internal: hết cảnh "mỗi tin nhắn kết nối MCP lại nên hơi chậm". Hub tự làm nóng lúc khởi động.
- Registry MCP chuyển sang STATE_DIR (Docker ghi được) và **tự migrate** từ bản cũ: server cũ thành connection, backup nguyên bản ở `mcp_servers.v1.bak.json`, không mất dữ liệu.
### Bảo mật
- API key/token của kết nối **mã hoá at rest** (Fernet, key riêng theo máy). Nhật ký audit chỉ ghi TÊN tham số, không ghi giá trị. Endpoint hub xác thực bằng token nội bộ riêng, không dùng session dashboard.

## [0.8.13] - 2026-07-03
### Cải thiện
- Bảng chọn model trong Telegram làm lại theo UX gateway Hermes: chọn provider ĐÃ KẾT NỐI (Claude Code, **ChatGPT**, OpenRouter, Claude API, OpenAI API - trước đây thiếu hẳn ChatGPT) có dấu ✓ + số model, rồi lưới model 2 cột **phân trang ◀ 1/N ▶**. Danh sách model lấy LIVE từ provider (OpenRouter đủ vài trăm model thay vì vài cái trong catalog; ChatGPT hiện model Codex), có mẹo gõ `/model <id>` chọn nhanh.
- Gõ tay `/model gpt-5.5` hoặc `/model gpt-5.3-codex` giờ tự hiểu là ChatGPT (Codex) nếu đã kết nối OAuth, không còn bị nhét nhầm sang Claude.

## [0.8.12] - 2026-07-03
### Thêm mới
- Telegram có lệnh **`/brain`** - xem và đổi brain (vault) cho RIÊNG phiên của mình: gõ `/brain` mở bảng nút bấm chọn (brain đang dùng có dấu ✓), hoặc gõ thẳng tên `/brain <tên>` (khớp một phần cũng được). Đổi xong hội thoại tự reset để nạp đúng bộ nhớ/skill của brain mới; người khác dùng chung bot và dashboard KHÔNG bị ảnh hưởng. `/reset` giữ nguyên brain đã chọn.
- File gửi lên Telegram giờ rơi vào `inbox/telegram` của brain PHIÊN người gửi (trước đây luôn vào brain mặc định).
- `/status` hiển thị brain phiên đang dùng.

## [0.8.11] - 2026-07-03
### Thêm mới
- Telegram **đa phiên theo tài khoản**: mỗi chat ID giờ có ngữ cảnh hội thoại RIÊNG, không còn lẫn lộn khi nhiều người dùng chung 1 bot. Trước đây tất cả người dùng dùng chung một session (người sau nối tiếp mạch của người trước, và chỉ 1 người được trả lời tại một thời điểm). Nay mỗi tài khoản có session Claude riêng (giữ `--resume` độc lập), lịch sử OpenRouter riêng, câu `/retry` riêng.
- Các tài khoản **chạy song song**: A đang được trả lời thì B hỏi vẫn được xử lý ngay, không phải xếp hàng chờ. Trong CÙNG một tài khoản vẫn tuần tự 1 lượt/lúc (gửi câu mới khi đang bận sẽ báo "đang xử lý câu trước").
- `/reset` và `/stop` chỉ tác động **phiên của chính người gõ**: reset xoá đúng ngữ cảnh của họ, stop chỉ giết đúng tiến trình Claude của họ (không đụng người khác đang chat). `/status` hiển thị mã phiên.
- File Boss tạo ra gửi về **đúng người đang hỏi**: endpoint `POST /telegram/send-file` nhận thêm `chat_id`, và gateway nhắc engine luôn gắn chat_id của người hỏi vào lệnh gửi (thiếu thì rơi về chủ bot như cũ). Whitelist vẫn chặn ID lạ.
### Sửa lỗi
- Dashboard web: nút **Stop không còn giết nhầm lượt của người khác** đang chat song song. Mỗi kết nối WebSocket giờ có tag phiên riêng (server phát qua message hello, frontend gửi kèm khi POST `/stop`) - web vốn đã đa phiên (mỗi tab/kết nối một session, lưu SQLite resume được), đây là lỗ hổng chéo duy nhất còn lại.
- Khung chat **phóng to (chat workspace) trước đây KHÔNG hiện trạng thái** "đang suy nghĩ / đang gọi tool": thanh trạng thái cũ nằm ngoài `#chatArea` nên bị bỏ lại khi phóng to. Đã thay bằng chip hoạt động ngay trong khung chat.
### Cải thiện
- **Chip hoạt động trong khung chat** (cả thường lẫn phóng to): bong bóng 3 chấm nhún + dòng trạng thái sống ("Boss đang suy nghĩ...", "⚙ Đang gọi: pos_statistics", "✍ Đang soạn câu trả lời...") + đồng hồ đếm giây khi đợi lâu (hiện từ giây thứ 3). Chip hiện NGAY khi bấm gửi, luôn nằm dưới cùng kể cả dưới bubble đang stream, tự biến mất khi xong lượt.

## [0.8.10] - 2026-07-03
### Thêm mới
- Telegram hỗ trợ **NHIỀU chat ID** dùng chung 1 bot: ô "Chat ID được phép dùng" giờ nhận nhiều ID cách nhau dấu phẩy (vd `123456789, 987654321`) - thêm người thân/nhân viên nhắn với Boss mà không phải dựng bot riêng. Whitelist chặn đúng theo danh sách; ID nhóm (số âm) cũng dùng được.
- Nút **Gửi test** gửi tin thử tới TẤT CẢ ID và báo rõ ID nào lỗi (thường do người đó chưa bấm Start bot); thông báo nền (loop tự tạm dừng...) cũng gửi tới tất cả ID; dòng trạng thái hiện số ID được phép, cảnh báo rõ khi đang để trống (mọi người nhắn được). File tự gửi về Telegram không kèm chat cụ thể sẽ về ID ĐẦU TIÊN (chủ bot).
- Tương thích ngược hoàn toàn: cấu hình 1 ID cũ giữ nguyên, không phải làm lại gì.

## [0.8.9] - 2026-07-03
### Thêm mới
- **Trang chủ giới thiệu** (`website/index.html`): landing page 1 file HTML/CSS/JS thuần, phong cách dark nebula đồng bộ dashboard - hero gõ chữ tự động, nền đồ thị hạt sao canvas, bảng so sánh chatbot vs Boss, bento 8 tính năng, mockup Telegram có bong bóng chạy, timeline 3 bước deploy, section giới thiệu tác giả Phạm Quảng Đại, FAQ accordion, nút copy lệnh. Mọi link tài liệu trỏ về GitHub; KHÔNG hiển thị số phiên bản trên trang. Dùng ảnh thật: screenshot đồ thị tri thức trong ô tính năng lớn (kiêm og:image khi share) + chân dung tác giả (fallback chữ MQ nếu ảnh lỗi).

## [0.8.8] - 2026-07-03
### Sửa lỗi
- Đổi tên file mẫu `.env.example` → `env.example` (bỏ dấu chấm đầu): Docker Manager của Hostinger tự quét file `.env*` trong repo khi deploy từ URL và nhập nguyên nội dung (kể cả dòng chú thích `#`) vào ô Environment, gây một loạt biến đỏ "Invalid variable name" mỗi lần deploy. Ô Environment trên Hostinger giờ chỉ cần đúng 1 biến `DOMAIN_NAME`. Ai đã dính: xoá các dòng có dấu `#` trong ô Environment một lần là sạch vĩnh viễn. Chạy local không đổi gì ngoài lệnh copy: `cp env.example .env`.

## [0.8.7] - 2026-07-03
### Thêm mới
- **Telegram thành kênh làm việc đầy đủ** (port ý tưởng gateway của hermes-agent):
  - Boss giờ **biết mình đang trả lời qua kênh nào**: gateway chèn block "Kênh hội thoại hiện tại" (Telegram DM/nhóm với ai, chat_id, các nền tảng đang kết nối) vào system prompt mỗi lượt - hỏi "em đang chat với anh qua đâu" là khai đúng, không đoán.
  - **Tự gửi file về Telegram**: file Boss tạo trong lượt (tool Write) hoặc file có đường dẫn tuyệt đối nhắc trong câu trả lời được tự động đính kèm gửi ngay sau câu trả lời (tối đa 10 file/lượt, mỗi file dưới 50MB; ảnh gửi dạng photo có preview, còn lại gửi dạng document).
  - Endpoint nội bộ `POST /telegram/send-file` (CHỈ nhận từ localhost - bên ngoài qua proxy vẫn bị chặn đăng nhập): agent chủ động gửi file bất kỳ có sẵn trên máy giữa lượt bằng curl.
  - **Nhận file/ảnh từ Telegram**: gửi file/ảnh (kèm caption) cho bot là Boss tự tải về `inbox/telegram/` trong brain rồi đọc như file đính kèm trong chat (trần tải 20MB của bot API). Voice/video chưa hỗ trợ - Boss sẽ nói rõ.
  - Tin nhắn trả lời render **MarkdownV2** (đậm/nghiêng/code/link hiện đẹp), tự fallback plain text nếu Telegram từ chối parse - không mất tin.
### Cải thiện
- Dashboard web cũng có block kênh riêng: Boss phân biệt đang nói chuyện qua web hay Telegram, và biết cách đẩy file sang Telegram khi user yêu cầu (nếu bot đang chạy).

## [0.8.6] - 2026-07-02
### Thêm mới
- **Chat workspace**: phóng to chat (nút ⛶ hoặc 🕘 Lịch sử) giờ mở thành không gian làm việc gần full màn hình kiểu Claude/Cowork - cột trái là **sidebar Lịch sử hội thoại** (＋ Hội thoại mới, tìm toàn văn, danh sách nhóm Hôm nay/Hôm qua/7 ngày/Cũ hơn, badge engine + số tin, đổi tên/xoá khi rê chuột, phiên đang mở tô sáng, bấm phát mở lại ngay), cột phải là nội dung chat căn giữa rộng tối đa ~980px. Sidebar ẩn/hiện được (nhớ trạng thái); màn hẹp tự chuyển thành ngăn kéo nổi, Esc đóng ngăn kéo trước rồi mới thu nhỏ chat. Panel Lịch sử trượt bên phải cũ được gỡ, nút 🕘 góc phải mở thẳng workspace.
- Tiện ích đọc/soạn trong chat: nút **⧉ Copy** cho từng khối code + copy cả tin nhắn Boss (hiện khi rê chuột); tin nhắn dài của bạn tự thu gọn sau 10 dòng kèm "Xem thêm"; đang cuộn đọc phía trên thì tin mới KHÔNG kéo giật xuống - hiện nút **↓ Tin mới** ở đáy khung; chip file đính kèm hiển thị ngay trong workspace khi phóng to.
### Sửa lỗi
- Tin nhắn nhiều dòng của bạn (Shift+Enter) trước đây hiển thị dính thành một dòng - giờ giữ nguyên xuống dòng.
- Copy hoạt động cả khi trình duyệt chặn Clipboard API (tự fallback), vd truy cập qua HTTP LAN.

## [0.8.5] - 2026-07-02
### Thay đổi
- Sao lưu GitHub nâng cấp thành **đồng bộ 2 CHIỀU**: mỗi lượt vừa đẩy thay đổi của máy lên repo, vừa kéo thay đổi từ máy khác về và tự hoà nhập. Dùng được nhiều máy chung 1 repo (máy nhà + VPS làm việc xen kẽ, các máy tự khớp nhau) - hết cảnh 2 máy force-push đè mất backup của nhau.
- Xung đột cùng 1 file sửa ở 2 nơi: bản có lần sửa MỚI HƠN thắng, bản thua giữ nguyên thành file `.conflict-<local|remote>-<thời điểm>` ngay cạnh (không âm thầm mất chữ nào); một bên sửa một bên xoá thì bản sửa thắng. Đẩy lên bằng push thường (bỏ force-push); máy khác chen ngang thì tự kéo về hoà tiếp rồi đẩy lại.
- Khôi phục máy mới không cần git tay: dán repo + token rồi bấm Đồng bộ ngay là brain về đủ. Thư mục brains trống được coi là chế độ KHÔI PHỤC - chỉ nhận về, không bao giờ đẩy "trạng thái trống" lên đè backup. File thiếu cục bộ (wipe/volume mới) tự được vá lại từ bản đồng bộ.
### Sửa lỗi
- Đồng bộ truyền byte nguyên văn giữa các máy (tắt autocrlf của git trên mirror) - hết cảnh cùng 1 file lệch CRLF/LF giữa Windows và VPS Linux mãi không khớp.
### Cải thiện
- Trang Tự học: mục đổi tên "⇅ Đồng bộ brain với GitHub (2 chiều)", nút "Đồng bộ ngay" báo kết quả chi tiết (nhận về bao nhiêu file, có đẩy lên không, danh sách file xung đột); trạng thái lần cuối lưu kèm báo cáo. Không đẩy được về máy (file bị khoá) thì HOÃN push để giữ an toàn dữ liệu, lần sau tự thử lại.

## [0.8.4] - 2026-07-02
### Thay đổi
- Tách 2 tầng rõ ràng: **tầng hệ thống** (chức năng mặc định của Boss OS - skill boss-builder / ingest-source / query-wiki / lint-wiki + loop tự-cải-tiến) giờ đi theo mã nguồn app tại `.claude/skills/` và `system/loops/`, cập nhật cùng phiên bản khi update app; **tầng brain** chỉ còn dữ liệu của bạn (ký ức, sources, wiki, agent/skill/workflow/loop tự tạo). Đổi brain không còn mất chức năng mặc định.
- Đồng bộ có manifest (`.boss/system-manifest.json` trong mỗi brain): app lên bản mới thì bản skill/loop hệ thống trong brain được cập nhật theo, NHƯNG file bạn đã sửa thì giữ nguyên bản của bạn (user override); loop giữ nguyên trạng thái bật/tắt, chế độ, chu kỳ bạn đã chỉnh. Lỡ xoá file hệ thống thì tự cài lại (muốn ngừng dùng hãy TẮT skill - trạng thái tắt được tôn trọng qua mọi lần update).
- Lúc khởi động đồng bộ cho MỌI brain trong thư mục brains (trước đây chỉ Brain Default được seed lúc boot, brain tạo ở bản cũ không bao giờ nhận skill mới); brain ngoài chọn qua `path:` được đồng bộ ngay lượt dùng đầu. Nút "Tạo cấu trúc" (vault init) giờ seed đầy đủ như brain mới tạo.
- Skill hệ thống được nạp NATIVE cho chat ở mọi brain (nguồn chuẩn nằm trong thư mục app - engine Claude Code đọc trực tiếp), không còn phụ thuộc bản sao trong brain.
### Cải thiện
- Trang Skills: skill hệ thống có nhãn "hệ thống", không xoá được (chỉ tắt/bật hoặc sửa - sửa thì thành bản riêng của bạn và ngừng tự cập nhật).

## [0.8.3] - 2026-07-02
### Thêm mới
- Boss Index (`Boss/index.md`): chỉ mục tầng vận hành - liệt kê MỌI agent/skill/workflow/loop/lịch trong brain, tự sinh từ file (không sửa tay), kèm dòng tổng quan + cờ sức khoẻ (workflow trỏ agent không tồn tại, agent mồ côi, skill tắt, loop tự tạm dừng). Song song wiki/index.md để bất kỳ AI/engine đọc 1 chỗ là hiểu Boss có năng lực gì.
- Bản gọn (live) được chèn vào system prompt mọi engine (Claude/Codex/OpenRouter) → giải bài toán "đổi model là mất nhận biết skill", và giúp không tạo trùng năng lực. Endpoint GET /boss/index. Tự dựng lại khi khởi động + theo nhịp nền (chỉ ghi khi đổi, không churn git).

## [0.8.2] - 2026-07-02
### Cải thiện
- Engine Tự học siết 3 kỷ luật chống bịa (đồng bộ schema vault): citation cứng cho mọi câu wiki cụ thể, gắn nhãn mục-tiêu-vs-thực-tế (không biến câu tầm nhìn thành claim chắc nịch), giữ mâu thuẫn không ghi đè. Wiki tự sinh giờ ít mà chất, đáng tin để tích luỹ.
### Thêm mới
- 3 skill vận hành Second Brain (seed vào mỗi brain, create-if-missing): **ingest-source** (tiêu hoá source, kèm 3-pass cho source dài), **query-wiki** (trả lời có trích dẫn + lưu lại kết quả giá trị), **lint-wiki** (health-check 8 loại lỗi, chỉ trả checklist). Biến 3 phép toán INGEST/QUERY/LINT từ prose thành công cụ tự kích hoạt, nhất quán đa engine.

## [0.8.1] - 2026-07-02
### Thêm mới
- Brain mặc định giờ là bộ "compounding wiki" phổ quát (không còn tối giản): mỗi brain tự seed schema doc (CLAUDE.md + AGENTS.md để Claude Code lẫn Codex tự nạp) + file điều hướng wiki (index.md, log.md, _open-questions.md) + _session-handoff.md (chuyển giữa các model không mất mạch). Encode pattern tích luỹ tri thức + 3 kỷ luật chống bịa (citation bắt buộc, mục tiêu vs thực tế, mâu thuẫn giữ rõ) + 3 phép toán INGEST/QUERY/LINT.
- Trung lập ngành: KHÔNG seed folder marketing/Bullet Journal; taxonomy mọc dần theo source thật, gói theo-ngành để dành làm opt-in. Tất cả create-if-missing (không đè file bạn đã sửa).

## [0.8.0] - 2026-07-02
### Thay đổi
- Sao lưu GitHub giờ đồng bộ **TOÀN BỘ thư mục brains** (mọi brain) trong MỘT lần thay vì từng brain (sửa lỗi các brain đè nhau khi tự động backup vào cùng repo). Mỗi brain là một thư mục con trong repo; xoá brain khỏi máy thì backup sau cũng bỏ. Khuyến nghị để mọi brain trong thư mục brains (tạo brain mới bằng nút ➕ là tự vào đó) để chuyển máy dễ.
- Cơ chế mới dùng bản sao sạch (mirror): bỏ hội thoại gốc/log/khoá + git thô của từng brain (tránh lỗi nested-repo), token không lọt .git/config.
### Thêm mới
- Đổi avatar/logo mặc định của Boss.

## [0.7.9] - 2026-07-02
### Thêm mới
- Bộ "meta-capabilities" khởi đầu, tự seed vào mỗi brain: skill **boss-builder** (dạy Boss tự tạo agent/skill/workflow/loop đúng chuẩn, có chống trùng + rào an toàn) và loop **tự-cải-tiến-boss** (mặc định TẮT, chế độ đề xuất - mỗi vòng rà hệ thống, đề xuất 1 cải tiến nhỏ an toàn, ghi báo cáo vào 05 - Projects). Tạo dạng create-if-missing, không đè file bạn đã sửa.
- Quy tắc "Làm rõ trước khi trả lời" trong system prompt: câu hỏi phức tạp/mơ hồ thì Boss tự diễn đạt lại cách hiểu + nêu giả định rồi mới làm, chỉ hỏi lại khi thực sự tắc.

## [0.7.8] - 2026-07-02
### Thêm mới
- Agent chọn được model của ChatGPT/Codex (GPT-5.x) bên cạnh Claude (Sonnet/Opus/Haiku/Fable). Agent model Codex chạy qua Codex CLI - vẫn đọc/ghi file vault + dùng MCP. Dropdown model trong Studio chia 2 nhóm Claude / ChatGPT.
- An toàn: workflow chạy nền tự động (dispatcher, file-only) luôn dùng Claude Code để giữ giới hạn công cụ, kể cả khi agent chọn Codex; model Codex chỉ áp khi chạy workflow trực tiếp ở Studio.
### Thay đổi
- Tài liệu mô tả lại: Boss xây trên CLI dạng agent của nhà cung cấp (Claude Code + Codex) và tận dụng gói subscription, không còn xoay quanh chỉ Claude. Cập nhật README, docs 07/10, nhãn Docker và system prompt.

## [0.7.7] - 2026-07-02
### Sửa lỗi
- Agent: phần chọn Model (Sonnet/Opus/Haiku) trước đây lưu vào file nhưng KHÔNG được áp khi chạy - workflow luôn dùng model mặc định. Nay model của từng agent (kể cả agent kiểm chứng) được áp THẬT vào CLI lúc chạy. Thêm lựa chọn "Fable" + "Mặc định (theo CLI)" trong dropdown; agent để trống model = dùng model mặc định.

## [0.7.6] - 2026-07-02
### Sửa lỗi
- ChatGPT/Codex trên VPS báo "gpt-5-mini không hỗ trợ khi dùng Codex với tài khoản ChatGPT": model API thường (gpt-5-mini, gpt-4o, o3...) không chạy được qua Codex. Nay tự đổi (coerce) sang model Codex hợp lệ trong catalog (mặc định gpt-5.5) ở cả chat lẫn Telegram, tự chữa lại cấu hình đã lưu, và báo cho người dùng. Bộ chọn model của ChatGPT-OAuth cũng chỉ còn liệt kê đúng model Codex (bỏ nguồn trả model ChatGPT chung).
### Thêm mới
- Guide khi deploy: thêm OCI image labels (documentation/source/url) + nhãn compose để Docker Manager (Hostinger) hiện link Documentation/Quick start cho project. Thêm QUICKSTART.md (deploy 3 cách + sự cố hay gặp) ở gốc repo; mọi link tài liệu trỏ về docs trên GitHub.

## [0.7.5] - 2026-07-02
### Thêm mới
- Sao lưu brain lên GitHub: mục mới trong trang Tự học, có hướng dẫn 3 bước ngay trên màn hình (tạo repo private → tạo token fine-grained → dán vào). Nút Kiểm tra kết nối + Sao lưu ngay + công tắc tự sao lưu định kỳ. Tài liệu chi tiết: docs/18-sao-luu-github.md.
- Backup đẩy toàn bộ brain lên repo GitHub riêng (force-push, local là bản gốc); khôi phục bằng git clone khi mất máy/VPS.
### An toàn
- Token GitHub lưu nội bộ settings.json (gitignored), KHÔNG đẩy lên repo và tự che trong mọi thông báo lỗi; push dùng URL tạm nên token không nằm trong .git/config. File nhạy cảm (log thô, hội thoại gốc, khoá lock) được .gitignore loại khỏi bản đẩy. Cảnh báo rõ trên UI: chỉ dùng repo Private.

## [0.7.4] - 2026-07-02
### Thay đổi
- Tự học: mặc định BẬT sẵn + chế độ Tự ghi + bật cả 4 khả năng (Ký ức, Wiki, Kỹ năng, Việc) cho cài mới. Học chạy ngay từ đầu, không phải vào bật thủ công.
- Bỏ yêu cầu git: chế độ Tự ghi giờ hoạt động KỂ CẢ khi máy chưa có git (trước đây tự hạ về Chạy thử). Có git thì vẫn tự commit để hoàn tác 1 chạm; không có git thì vẫn ghi bình thường, chỉ thiếu undo/backup.
- Tự học giờ tự đăng ký brain đang trò chuyện: chat trên vault nào là học vault đó, không cần vào trang Tự học bấm lưu để thêm vault vào danh sách.
### An toàn
- Các rào an toàn của engine học GIỮ NGUYÊN: fork chỉ-đọc cô lập (0 MCP), quét lộ khoá + câu tiêm, chặn ghi ngoài phạm vi, ký ức chỉ thêm không đè.

## [0.7.3] - 2026-07-02
### Thêm mới
- Loop có thêm chế độ "Toàn quyền" (mode full): loop tự thao tác THẬT ra ngoài qua MCP không cần hỏi (tạo/sửa đơn, chạy quảng cáo tiêu tiền, gửi tin, đăng bài). Dành cho ai muốn loop tự làm hết. Kèm cảnh báo rủi ro đỏ trong form + hộp xác nhận khi lưu và khi bật; tab Lịch đánh dấu "⚠ TOÀN QUYỀN".
- 3 mức quyền rõ ràng: Đề xuất (chỉ đọc) · Tự làm an toàn (ghi nháp + đọc MCP, KHÔNG tiền/đơn) · Toàn quyền (làm mọi thứ). Mặc định vẫn là mức an toàn; chế độ toàn quyền phải tự bật.
### An toàn
- Loop toàn quyền vẫn tôn trọng cài đặt "chặn tool" (deny_tools) của từng MCP server; bước tự kiểm chứng chuyển sang soi "đúng phạm vi nhiệm vụ" thay vì cấm hành động. Boss khi chat KHÔNG bao giờ tự đặt loop sang toàn quyền - chỉ khi người dùng yêu cầu rõ.

## [0.7.2] - 2026-07-02
### Thay đổi
- Form tạo Loop gọn còn Tên + Mô tả (+ chế độ + chu kỳ): bỏ bộ chọn "Loại nhiệm vụ" 4 nút. Mỗi loop giờ chỉ cần mô tả việc cần làm mỗi vòng. Tinh chỉnh nâng cao (giờ im lặng, trần vòng/ngày, profile code) sửa trực tiếp trong file Boss/loops/<tên>.md.
- Loop giờ ĐỌC được dữ liệu thật qua MCP (POS, quảng cáo, lịch...) để làm việc - trước đây loop bị cô lập 0-MCP. An toàn giữ 3 lớp: tôn trọng deny_tools từng server, chỉ dẫn cứng cấm tạo đơn/tiêu tiền/quảng cáo/đăng bài/gửi tin (chỉ được đọc + ghi nháp), và kiểm chứng độc lập sẽ fail nếu phát hiện hành động ghi ra ngoài. Loop chạy nền vẫn KHÔNG có Bash/Web (trừ profile code cho loop sửa mã, vốn 0-MCP).

## [0.7.1] - 2026-07-02
### Cải thiện
- Trang loop: đổi tên mục sidebar "Tự cải thiện" thành "Loop" cho gọn, đúng bản chất.
- Bỏ nút "LINT Wiki" khỏi trang Loop (engine Tự học đã lo bảo trì Wiki qua curator/LINT chỉ-đề-xuất), tránh trùng chức năng.

## [0.7.0] - 2026-07-02
### Thêm mới
- MULTI-LOOP: "Vòng lặp tự cải thiện" nâng thành hệ NHIỀU loop. Mỗi loop = 1 file `Boss/loops/<slug>.md` trong vault (sửa được bằng Obsidian/chat/Studio), có bật/tắt, chu kỳ riêng, giờ im lặng (quiet_hours), trần vòng/ngày, workspace + tools_profile (vault-safe mặc định / code cho loop sửa mã). Thực thi TUẦN TỰ (1 vòng/lúc), state runtime tách riêng ở `Boss/loop-state.json`.
- Tự bảo vệ: loop lỗi/kiểm chứng ✗ 3 lần liên tiếp thì TỰ TẠM DỪNG (ghi lý do + log, báo Telegram nếu có bot); bật lại hoặc Chạy ngay để tiếp tục.
- API mới `/loops` (list/tạo/sửa/toggle/xoá/run-now/log lọc theo loop). `/loop/*` cũ giữ nguyên, trỏ về loop legacy `vong-lap-goc`.
- Trang "Tự cải thiện" thành DANH SÁCH loop: trạng thái, lần chạy cuối + kết quả kiểm chứng, next run, nút bật/tắt - chạy ngay - sửa - xoá, form tạo loop đầy đủ, nhật ký lọc theo loop.
- Tab Lịch hiện MỌI loop như routine builtin (id `__loop__:<slug>`): bật/tắt ngay tại đó; xoá thì phải sang trang Tự cải thiện.
- Boss chat = ĐIỀU PHỐI VIÊN: system prompt thêm quy trình chọn công cụ nhỏ nhất đủ hoàn thành (trả lời → task Kanban → skill → agent → workflow → lịch → loop), kiểm tra trùng trước khi tạo, loop tạo qua chat mặc định suggest + tắt.
### Cải thiện
- Migrate 1 lần: `loop_config.json` cũ tự sinh `Boss/loops/vong-lap-goc.md` (giữ nguyên toàn bộ custom_goal), json cũ giữ làm backup.

## [0.6.6] - 2026-07-02
### Thêm mới
- Nối engine tự học vào Kanban: capability "Việc (Kanban)" - sau mỗi hội thoại, engine học đề xuất việc nền vào backlog (dedup theo tên, chờ duyệt).
### Sửa lỗi
- Dashboard chết toàn bộ (Enter không gửi, stats trống, không graph) do app.js bám nút học cũ đã gỡ - đã guard + nghỉ hưu auto-learn client cũ.

## [0.6.5] - 2026-07-02
### Sửa lỗi
- docker-compose.hostinger.yml "không cài được": bỏ ${DOMAIN_NAME:?...} (bắt buộc biến, thiếu là deploy fail). Nay LUÔN deploy được: chưa đặt DOMAIN_NAME thì chạy tạm ở :7777, đặt DOMAIN_NAME thì có HTTPS. Publish lại cổng 7777 làm đường vào dự phòng.

## [0.6.4] - 2026-07-02
### Sửa lỗi
- docker-compose.yml: Watchtower chuyển sang profile "update" (mặc định TẮT) nên deploy base compose KHÔNG còn "Partially running" (Watchtower cần Docker socket, Hostinger hay chặn). Bật auto-update khi cần: docker compose --profile update up -d.
### Cải thiện
- README: sửa mục cài Hostinger dùng docker-compose.hostinger.yml + đặt DOMAIN_NAME cho tên miền/HTTPS; bỏ thông tin sai "Hostinger tự cấp URL hstgr.cloud".

## [0.6.3] - 2026-07-02
### Sửa lỗi
- docker-compose.hostinger.yml: đổi ports "7777:7777" (cố định) thành "7777" (ngẫu nhiên, giống Hermes) để nút Open trỏ thẳng domain HTTPS của Traefik thay vì http://<ip>:7777. Truy cập qua https://<DOMAIN_NAME>.

## [0.6.2] - 2026-07-02
### Sửa lỗi
- docker-compose.hostinger.yml: đã kiểm chứng Hostinger KHÔNG cấp biến TRAEFIK_HOST cho compose dán tay (link ra "boss-os." cụt). Nay Host BẮT BUỘC DOMAIN_NAME (dùng ${DOMAIN_NAME:?...}): thiếu thì deploy báo lỗi rõ ràng thay vì ra link hỏng. Tài liệu chỉ rõ đặt DOMAIN_NAME=boss.<hostname-vps>.hstgr.cloud ở ô Environment.

## [0.6.1] - 2026-07-01
### Sửa lỗi
- docker-compose.hostinger.yml: Host mặc định dùng ${COMPOSE_PROJECT_NAME}.${TRAEFIK_HOST} (đúng mẫu Hermes) thay cho giá trị localhost -> deploy trên Hostinger là TỰ có link <tên-project>.<hostname-vps>.hstgr.cloud + HTTPS, không cần đặt biến gì. Muốn tên miền riêng thì đặt DOMAIN_NAME (ghi đè). Ai deploy trên VPS của họ cũng ra link đúng.

## [0.6.0] - 2026-07-01
### Thay đổi
- Đồng bộ NỐT toàn bộ tên hạ tầng nội bộ sang boss: biến môi trường BOSS_*, volume boss-data/boss-brains, service/container/user boss (/home/boss), profile codex boss, marker BOSS_METRICS, và các file boss.service / start-boss.vbs / stop-boss.bat. Toàn dự án dùng một tên duy nhất.
- LƯU Ý khi redeploy: volume đã đổi tên nên bản mới bắt đầu TRỐNG (cần tạo lại admin + nạp lại brain), hoặc tự chép dữ liệu từ volume cũ sang boss-data/boss-brains. Nếu trước đó đặt biến admin trên Hostinger, đổi tiền tố sang BOSS_ADMIN_USER / BOSS_ADMIN_PASSWORD.

## [0.5.1] - 2026-07-01
### Thay đổi
- Đổi tên repo/image GitHub sang boss-os (image ghcr.io/pham-dai-2000/boss-os, GITHUB_REPO, link cài đặt trong README/DEPLOY).

## [0.5.0] - 2026-07-01
### Thay đổi
- Đổi thương hiệu hiển thị sang Boss (giao diện, tài liệu, README, system prompt).
### Thêm mới
- docker-compose.hostinger.yml dùng ${COMPOSE_PROJECT_NAME} cho tên router/service Traefik: chạy được nhiều bản Boss trên cùng 1 VPS mà không đụng nhau (giống đuôi ngẫu nhiên -efxd của Hermes).

## [0.4.7] - 2026-07-01
### Sửa lỗi
- docker-compose.hostinger.yml gắn nhãn Traefik đúng mẫu app Hermes: BỎ phần networks/external traefik-proxy (chính chỗ làm deploy báo "network not found"). Traefik của Hostinger tự thấy container qua nhãn.
### Thêm mới
- Có link mặc định chạy HTTPS mà không cần mua tên miền: đặt DOMAIN_NAME=boss.<hostname-vps>.hstgr.cloud (Hostinger có wildcard DNS + tự cấp SSL).

## [0.4.6] - 2026-07-01
### Sửa lỗi
- docker-compose.hostinger.yml không deploy được trên Hostinger: bỏ yêu cầu mạng ngoài `traefik-proxy` (gây lỗi "network not found"). Bản mới chỉ 1 container, publish cổng 7777, deploy là chạy; gắn tên miền + HTTPS là bước tùy chọn (Hostinger UI hoặc nhãn Traefik thủ công, hướng dẫn trong file).

## [0.4.5] - 2026-07-01
### Sửa lỗi
- docker-compose.hostinger.yml bỏ Watchtower (cần Docker socket, hay gây "Partially running" trên Hostinger Docker Manager). Bản Hostinger giờ chỉ 1 container boss + nhãn Traefik, cập nhật bằng Redeploy.

## [0.4.4] - 2026-07-01
### Thêm mới
- File docker-compose.hostinger.yml: chạy Boss trên Hostinger với tên miền riêng + HTTPS qua Traefik có sẵn của Hostinger, bỏ cổng :7777.
### Sửa lỗi
- Tài liệu Hostinger nói đúng thực tế: compose gốc chỉ vào bằng IP:7777; muốn tên miền và SSL phải dùng bản có nhãn Traefik (docker-compose.hostinger.yml).

## [0.4.3] - 2026-07-01
### Thêm mới
- Khu Tên miền & SSL trong Cài đặt làm mới: huy hiệu trạng thái DNS và SSL, nút Bật SSL chủ động xin chứng chỉ rồi kiểm tra kết quả.
### Sửa lỗi
- Số phiên bản ở góc thanh bên nay đọc đúng bản đang chạy (trước bị cố định 0.4.0).
### Cải thiện
- Trạng thái tên miền rõ ràng: DNS đã trỏ đúng chưa, SSL bật chưa, kèm lệnh bật Caddy cho bản Docker khi cần.

## [0.4.2] - 2026-07-01
### Thêm mới
- Trang **Cập nhật** (mục Logs cũ trên thanh bên): nhật ký phiên bản và các thay đổi mới, đọc thẳng trong app.
- Tự đối chiếu bản đang cài với bản mới nhất trên GitHub, đánh dấu phiên bản "đang dùng" và bản "có thể cập nhật".

## [0.4.1] - 2026-07-01
### Sửa lỗi
- Upload file trên Docker/VPS báo "lỗi máy chủ (500)": thư mục stage tạm đổi sang STATE_DIR ghi được (`/data/state`) thay vì code tree `/app` chỉ đọc.
- Endpoint upload bọc chống lỗi: sự cố môi trường trả thông báo rõ ràng kèm log thay vì lỗi 500 khó đoán.
### Thêm mới
- Bộ tài liệu hướng dẫn sử dụng chi tiết trong `docs/` (17 trang) và mục lục nối vào README.
### Cải thiện
- Bỏ toàn bộ ký tự gạch ngang dài khỏi giao diện và tài liệu cho giọng nói đọc mượt hơn.

## [0.4.0] - 2026-06-30
### Thêm mới
- Trang **Cài đặt** riêng: chọn giọng đọc theo nhà cung cấp (Edge TTS, OpenAI, ElevenLabs), tinh chỉnh giao diện, avatar, tên miền.
- Nút **Cập nhật ngay** trong Tổng quan: cập nhật phiên bản mới ngay trên giao diện, không cần terminal.
- Đổi logo/avatar và trỏ tên miền riêng chạy HTTPS ngay trong app.
### Cải thiện
- Gộp cài đặt vào thanh bên, thu gọn điều hướng.

## [0.3.0] - 2026-06-29
### Thêm mới
- Chạy ChatGPT qua Codex CLI trên VPS: đăng nhập bằng gói subscription, dùng được cả MCP của Boss.
- Đăng nhập Claude bằng OAuth device-code ngay trong giao diện (không cần terminal).
- Kiến trúc đa Second Brain: quản lý nhiều brain trong thư mục `brains/`, tạo và xoá brain trong app.
### Sửa lỗi
- Trạng thái bot Telegram hiển thị đúng thực tế (đang chạy, lỗi 409, chưa bật).

## [0.2.0] - 2026-06-28
### Thêm mới
- Bộ cài đặt lần đầu (wizard) chọn 1 trong 3 nhà cung cấp: Claude Code, ChatGPT, OpenRouter.
- Triển khai 1-click qua Hostinger Docker Manager (kéo image GHCR).
- Tự bật HTTPS bằng Caddy, logo và favicon thương hiệu.
### Bảo mật
- Bắt buộc đăng nhập khi chạy public, MÃ THIẾT LẬP chống chiếm tài khoản admin.

## [0.1.0] - 2026-06-26
### Thêm mới
- Bản đầu tiên: trợ lý AI cá nhân chạy bằng Claude Code, giọng nói, đồ thị tri thức 3D, Second Brain.
- README chi tiết: giới thiệu, cài đặt mọi cách, hướng dẫn dùng, bảo mật, khắc phục sự cố.
