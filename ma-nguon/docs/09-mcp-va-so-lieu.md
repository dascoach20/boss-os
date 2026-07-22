# Kết nối & số liệu kinh doanh

Trang **Kết nối** là nơi bạn "đấu" Boss OS vào các công cụ bạn đang dùng: Pancake POS, Zalo, Webcake Landing, Botcake, quảng cáo Meta/Google/TikTok, lịch, CRM... Sau khi đấu, Boss OS đọc được số liệu THẬT và (nếu bạn cho quyền) thao tác thật trên các công cụ đó. Trang này hướng dẫn: kết nối một dịch vụ từ Kho, nối nhiều tài khoản, phân quyền, xem nhật ký, và cách đọc số liệu.

## Tính năng này là gì

Bên dưới, mỗi kết nối là một "đường ống" MCP (Model Context Protocol) nối Boss OS tới dịch vụ ngoài - nhưng bạn không cần biết chi tiết đó. Điểm mới từ bản 0.9:

- **Kho kết nối cài sẵn**: chọn dịch vụ, dán API key (hoặc quét QR với Zalo) là xong. Boss OS tự kiểm tra key và tự đặt tên tài khoản (ví dụ lấy đúng tên cửa hàng từ Pancake POS). Không còn phải gõ URL hay header.
- **Một dịch vụ, nhiều tài khoản**: 3 cửa hàng Pancake = 3 tài khoản trong cùng một thẻ Pancake POS. 2 số Zalo = 2 tài khoản Zalo chạy song song. Mỗi tài khoản bật/tắt, phân quyền, đặt mặc định riêng.
- **Mọi bộ não dùng chung**: Claude Code, ChatGPT (Codex), OpenRouter, OpenAI API, Anthropic API đều dùng chung kho Kết nối này qua "hub" của Boss OS - đấu một lần, đổi model thoải mái.
- **Phân quyền cứng**: mỗi tài khoản có mức quyền. Boss OS CHẶN thật sự (không phải chỉ nhắc bằng lời) các thao tác vượt quyền, ví dụ tạo đơn khi đang ở mức Chỉ đọc.

## Mở ở đâu trong Boss OS

1. Vào dashboard (cổng mặc định `7777`).
2. Thanh bên trái, bấm mục **Kết nối** (biểu tượng phích cắm, phụ đề "Nguồn dữ liệu & công cụ").
3. Trang có 3 khu: **Đã kết nối** (các tài khoản đang đấu), **Kho kết nối** (dịch vụ cài sẵn để đấu thêm), và **MCP từ Claude Code** (những MCP bạn kết nối trong app Claude - chỉ để xem).

## Cách dùng (từng bước)

### 1. Kết nối Pancake POS (dán API key)

1. Ở **Kho kết nối**, tìm thẻ **Pancake POS**, bấm **Kết nối**.
2. Làm theo hướng dẫn trong cửa sổ: mở Pancake POS > Cấu hình cửa hàng > Ứng dụng & API > tạo API key, rồi dán vào ô.
3. Bấm **Kết nối**. Boss OS tự kiểm tra key - đúng thì hiện "✓ Đã kết nối: <tên cửa hàng>" và tài khoản xuất hiện ở khu Đã kết nối. Key sai thì báo lỗi ngay tại chỗ.
4. Có nhiều cửa hàng? Bấm **+ Thêm tài khoản** trên thẻ Pancake POS, dán key của shop tiếp theo. Mỗi shop một chip riêng.

Pancake POS mặc định ở mức **Chỉ đọc** - Boss OS xem được doanh thu, đơn, khách... nhưng không thể tạo đơn hay đụng tiền. Muốn Boss OS thao tác thật, xem mục Phân quyền bên dưới.

### 2. Kết nối Zalo (quét QR)

Cần Node.js 20+ trên máy chạy Boss OS (tải tại nodejs.org, cài một lần).

1. Ở Kho kết nối, bấm **Kết nối** trên thẻ **Zalo (tài khoản cá nhân)**.
2. Đọc cảnh báo rủi ro: đây là công cụ KHÔNG chính thức, tài khoản Zalo có thể bị hạn chế hoặc khoá - khuyến nghị dùng tài khoản phụ. Bấm "Tôi hiểu rủi ro, hiện mã QR".
3. Mở Zalo trên điện thoại > biểu tượng QR góc trên > quét mã trong màn hình Boss OS.
4. Quét xong, tài khoản tự xuất hiện. Nối thêm số Zalo khác bằng **+ Thêm tài khoản** - các tài khoản chạy cô lập, không giẫm nhau.

Zalo mặc định được cả đọc lẫn gửi tin (Toàn quyền) theo lựa chọn của bạn khi kết nối - Boss OS chỉ gửi tin khi bạn yêu cầu trực tiếp trong chat, và loop chạy nền KHÔNG bao giờ được tự gửi. Có giới hạn tần suất tự động để tránh spam gây khoá tài khoản.

### 3b. Kết nối Slack / Systeme.io

- **Slack** (MCP chính chủ, chỉ cần đăng nhập trong dashboard): Slack bắt buộc MCP đi qua một app của chính bạn nên hơi nhiều bước một lần: vào api.slack.com/apps tạo app trong workspace, ở "OAuth & Permissions" thêm Redirect URL `http://localhost:7777/connect/oauth/callback` (VPS thì thêm địa chỉ tên miền) và thêm các "User Token Scopes" (search, channels, users, chat:write, canvases...), rồi copy Client ID + Secret dán vào cửa sổ kết nối. Nếu workspace bắt duyệt app thì cần admin chấp thuận. Mặc định Chỉ đọc - gửi tin phải nâng Toàn quyền.
- **Systeme.io** (MCP chính chủ, dán key là xong): vào systeme.io > Cài đặt hồ sơ > "MCP & API keys" > tạo MCP key (hạn tối đa 90 ngày), dán vào. Boss OS quản lý được liên hệ, tag, newsletter, phễu. Mặc định Chỉ đọc.
- **Lark** (MCP chính chủ, chạy local, cần Node.js 18+): nhắn tin, tài liệu, bảng dữ liệu Base, wiki, danh bạ trong Lark. Tạo một Lark app tại open.larksuite.com/app, cấp quyền (im, docx, bitable, contact...), lấy App ID + App Secret dán vào. Boss OS chỉ làm được đúng phạm vi quyền bạn cấp cho app. Mặc định Chỉ đọc - gửi tin nhắn và cấp quyền file phải nâng Toàn quyền.

### 3. Kết nối Webcake Landing / Botcake

- **Webcake Landing**: lấy JWT tại webcake.io > Cài đặt > Mã truy cập > Tạo API keys, dán vào. Boss OS sẽ thiết kế/sửa landing page bằng lời nói. Cần Node.js 18+.
- **Botcake**: mở Botcake > Cấu hình > Tích hợp > Public API > Tạo API Key; dán Page ID + key. Boss OS đọc được khách hàng, tag, flow và (nếu cho Toàn quyền) gửi flow tới khách.

### 4. Kết nối bộ Google (Sheets, Search Console, Workspace)

- **Google Sheets**: đổ báo cáo doanh thu/tồn kho/công nợ ra bảng tính. Tạo service account trong Google Cloud (hướng dẫn có trong cửa sổ kết nối), share thư mục Drive cho email service account, dán nội dung file key JSON + ID thư mục là xong - không cần đăng nhập gì thêm.
- **Google Search Console**: số liệu SEO website (khách tìm từ khoá gì, lượt bấm). Cũng dán service account JSON, thêm email đó làm người dùng trong Search Console.
- **Google Calendar** và **Gmail** (2 kết nối riêng, MCP chính chủ của Google, chạy remote nên dùng được cả trên VPS): Calendar xem lịch, tìm chỗ trống, tạo/sửa/xoá sự kiện, nhắc hẹn; Gmail đọc/tìm thư, soạn NHÁP, gắn nhãn. Điểm an toàn: server Gmail chính chủ KHÔNG có tool gửi thẳng, nên Boss OS luôn dừng ở bản nháp để bạn tự bấm gửi. Cần tạo OAuth client một lần (console.cloud.google.com > Thông tin xác thực > OAuth client ID loại "Ứng dụng web", thêm URI chuyển hướng đúng như cửa sổ kết nối chỉ, và thêm email mình vào Test users). Dán Client ID + Secret, bấm Kết nối là trình duyệt mở cho bạn đăng nhập Google. Dùng CHUNG một OAuth client cho cả Calendar lẫn Gmail (chỉ cần bật thêm API tương ứng). Cả hai mặc định Chỉ đọc; nâng lên Ghi nháp để tạo sự kiện/soạn nháp, Toàn quyền mới xoá được sự kiện.
- **Google Workspace** (Gmail + Lịch + Drive + Docs trong 1 kết nối, chạy local): cần tạo OAuth client trong Google Cloud một lần (~10 phút, hướng dẫn từng bước trong cửa sổ kết nối); lần đầu dùng, trình duyệt mở để bạn bấm đồng ý. Mặc định ở mức Ghi nháp: Boss OS soạn nháp mail, tạo lịch, tạo tài liệu được nhưng KHÔNG tự gửi mail hay xoá gì - bật Toàn quyền phải xác nhận rủi ro. Chọn cái này nếu muốn CẢ Drive/Docs/Sheets trong một mối; nếu chỉ cần Lịch + Gmail thì 2 kết nối riêng ở trên gọn hơn (ít công cụ, chạy remote).

Mẹo: nếu chỉ cần Gmail/Lịch/Drive và bạn dùng engine Claude Code, cách nhanh hơn là bấm Connect ngay trong app Claude (claude.ai > Settings > Connectors) - Boss OS tự thấy chúng ở khu "MCP từ Claude Code".

### 5. Kết nối quảng cáo (Meta Ads, Google Ads, TikTok Ads)

Cả 3 mặc định ở mức **Chỉ đọc** - Boss OS xem báo cáo, phân tích chi phí/hiệu quả nhưng không đụng được vào chiến dịch.

- **Meta Ads (Facebook & Instagram)**: dễ nhất - bấm **Kết nối**, đăng nhập Facebook, chọn tài khoản quảng cáo và mức quyền (chọn "chỉ xem" nếu chỉ cần báo cáo). Không cần tạo app hay dán key; đây là MCP chính chủ của Meta (đang beta, mở dần theo từng tài khoản - bị từ chối nghĩa là tài khoản chưa được mở). Nếu sau này bạn bật Toàn quyền để Boss OS tạo/sửa chiến dịch: mọi chiến dịch tạo qua đây luôn ở trạng thái TẠM DỪNG, bạn phải tự bật trong Ads Manager - tiền chỉ chạy khi chính bạn bấm.
- **Google Ads**: MCP chính chủ của Google, thuần chỉ đọc (truy vấn số liệu GAQL: chiến dịch, chi phí, chuyển đổi, từ khoá). Cài đặt kỹ thuật nhất trong kho: cần developer token (lấy trong Google Ads API Center của tài khoản quản lý MCC) + project Google Cloud + đăng nhập gcloud một lần - cửa sổ kết nối có hướng dẫn từng bước. Chạy ads qua agency/MCC thì điền thêm ID tài khoản quản lý.
- **TikTok Ads**: TikTok chưa mở MCP chính chủ (mới công bố tại TikTok World 5/2026), nên Boss OS dùng server cộng đồng chạy trên Marketing API chính thức - thuần chỉ đọc (tài khoản, chiến dịch, báo cáo). Tạo app Marketing API tại business-api.tiktok.com, lấy App ID + Secret + Access Token dán vào. Khi TikTok mở bản chính chủ sẽ thay trong kho.

Google Ads và TikTok Ads chạy local qua công cụ `uv` - máy chạy Boss OS cần cài một lần: `winget install astral-sh.uv` (Windows) hoặc xem docs.astral.sh/uv.

### 6. Quản lý một tài khoản (chip)

Bấm vào chip tài khoản ở khu Đã kết nối để mở menu:

- **Test kết nối**: gọi thử, báo số công cụ khả dụng.
- **Đặt làm mặc định**: khi có nhiều tài khoản cùng dịch vụ, Boss OS ưu tiên tài khoản mặc định khi bạn không nói rõ shop nào.
- **Đổi tên** / **Tắt tạm** / **Xoá**.
- **Đổi quyền**: xem mục Phân quyền.
- **Chặn tool cụ thể**: dành cho người rành - gõ tên tool muốn cấm hẳn.
- **Nhật ký gọi tool**: xem Boss OS đã gọi gì, lúc nào, bị chặn gì.

### 7. Phân quyền 3 mức (quan trọng)

Mỗi tài khoản có một mức quyền, Boss OS chặn CỨNG tại chỗ:

- **Chỉ đọc**: chỉ xem số liệu. Tạo đơn, sửa dữ liệu, gửi tin... đều bị chặn. An toàn nhất, mặc định cho POS.
- **Ghi nháp**: được ghi/sửa dữ liệu thường (ghi chú, sản phẩm...), vẫn CHẶN hành động tiền/đơn/gửi tin.
- **Toàn quyền**: thao tác THẬT - tạo đơn, gửi tin, publish trang. Khi bật phải tick "Tôi hiểu rủi ro"; với Zalo có cảnh báo riêng.

Thông minh hơn bản cũ: Boss OS hiểu cả công cụ "2 trong 1" của Pancake - cùng tool đơn hàng, hỏi `danh sách đơn` thì cho qua, `tạo đơn` thì chặn nếu chưa đủ quyền.

Loop chạy nền còn bị siết thêm theo mode của loop: loop `suggest` chỉ đọc, loop `auto` không bao giờ đụng tiền/đơn/gửi tin - bất kể tài khoản đặt quyền gì.

### 8. Tự thêm dịch vụ ngoài kho (nâng cao)

Dịch vụ chưa có trong Kho? Bấm thẻ **Tự thêm (nâng cao)** - form kỹ thuật như bản cũ (URL/lệnh + header/env, hỗ trợ HTTP, SSE, stdio). Dịch vụ đăng nhập kiểu OAuth chuẩn MCP thì Boss OS tự mở trang đăng nhập và tự giữ token, chạy được cả trên VPS.

### 9. Chế độ "Chỉ dùng kết nối của Boss OS" (strict)

Tick ô này ở khu Đã kết nối nếu muốn Boss OS CHỈ dùng các kết nối khai ở đây, bỏ qua MCP cài sẵn trong Claude Code trên máy - kiểm soát chặt, tránh gọi nhầm công cụ của tài khoản Claude.

## Đọc số liệu

Không đổi so với trước: hỏi trực tiếp trong chat ("hôm nay bán được bao nhiêu, so hôm qua thế nào?"), Boss OS gọi đúng nguồn, trả lời theo công thức số liệu + so kỳ trước + nguyên nhân + đề xuất, và tự đẩy 3-6 chỉ số lên bảng số liệu cột trái trang Boss OS. Kỳ đã đóng lưu cache trong `05 - Data Cache/` của brain. Có nhiều shop thì nói rõ tên shop, không nói thì Boss OS dùng tài khoản mặc định.

## Mẹo

- Đặt tên tài khoản theo cửa hàng cho dễ gọi trong chat ("shop Kim Khí" vs "shop 2").
- POS cứ để Chỉ đọc nếu bạn chỉ cần xem báo cáo - không lo Boss OS vô tình tạo đơn.
- Tin nhắn đầu sau khi bật máy có thể hơi chậm với kết nối dạng chạy local (Zalo, Webcake) do phải khởi động công cụ - các lượt sau nhanh vì Boss OS giữ kết nối sống.
- Nhật ký gọi tool là chỗ đầu tiên nên xem khi nghi Boss OS "làm gì đó lạ".

## Sự cố thường gặp

- **Dán key báo "Key chưa đúng hoặc chưa đủ quyền"**: tạo lại API key trong dịch vụ, dán lại. Với Pancake kiểm tra key thuộc đúng cửa hàng.
- **Zalo báo "Cần cài Node.js 20+"**: cài Node.js từ nodejs.org rồi thử lại.
- **Google Ads / TikTok Ads báo không kết nối được**: kiểm tra máy đã cài `uv` chưa (`winget install astral-sh.uv`). Lần kết nối đầu phải tải gói nên có thể chậm - bấm Test lại sau 1-2 phút.
- **Meta Ads đăng nhập bị từ chối**: MCP của Meta đang beta, mở dần theo từng tài khoản quảng cáo và yêu cầu tài khoản thuộc Business Manager - chưa được mở thì thử lại sau vài tuần.
- **Mã QR hết hạn**: bấm thử lại để lấy QR mới (QR Zalo sống ~3 phút).
- **Tool bị chặn kèm dòng "đang ở mức quyền hạn chế"**: đúng thiết kế - nâng quyền tài khoản trong menu chip nếu bạn thật sự muốn Boss OS làm việc đó.
- **Sau khi cập nhật từ bản cũ**: các server MCP cũ tự chuyển thành tài khoản trong trang Kết nối (bản gốc backup ở `mcp_servers.v1.bak.json`), không phải khai lại.
- **Muốn quay về cơ chế cũ** (mỗi server một entry, không qua hub): đặt `"mcp": {"hub": false}` trong `server/settings.json` rồi khởi động lại.

Liên quan: [Models & engine](10-models-va-engine.md) để hiểu bộ não nào dùng được gì, [Trò chuyện & giọng nói](02-tro-chuyen-va-giong-noi.md) để hỏi số liệu bằng lời.
