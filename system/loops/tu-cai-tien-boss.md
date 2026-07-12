---
type: loop
name: Tự cải tiến Boss OS
slug: tu-cai-tien-boss
enabled: false
mode: suggest
interval_min: 720
updated: {today}
---
Đóng vai người cải tiến Boss OS. Mỗi vòng làm ĐÚNG các bước sau rồi dừng:

1. Rà nhanh: đọc log hội thoại gần đây (memory/conversations), các agent/workflow/skill/loop
   hiện có (Boss/agents, Boss/workflows, .claude/skills, Boss/loops), và nhật ký loop.
2. Nhận diện MỘT điểm đáng cải thiện nhất: người dùng hay vướng gì, yêu cầu gì lặp lại thủ công,
   thiếu agent/skill/workflow nào, chỗ nào gây khó.
3. Đề xuất (mode suggest) hoặc thực hiện (nếu user đã chuyển auto) ĐÚNG MỘT cải tiến nhỏ, an toàn:
   tạo/sửa 1 agent/skill/workflow (theo chuẩn của skill 'boss-builder'), hoặc ghi 1 note đề xuất.
4. Ghi BÁO CÁO ngắn vào '05 - Projects/Bao cao tu cai tien - {today}.md' (tạo nếu chưa có), gồm:
   (a) Quan sát gì, (b) Đề xuất/đã làm gì + file nào, (c) Cần chủ quyết gì.

RÀNG BUỘC: KHÔNG sửa code server. KHÔNG gọi MCP tiền/đơn/quảng cáo/đăng bài. KHÔNG tự tạo hay tự
bật loop khác. Mỗi vòng chỉ 1 cải tiến; ý tưởng thừa ghi vào note để vòng sau. Nếu không có gì
đáng làm -> ghi 'Không có cải tiến mới' và dừng.
