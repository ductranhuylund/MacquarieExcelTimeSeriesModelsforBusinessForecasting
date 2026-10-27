# CT / Journal

Website cá nhân độc lập về Quantum Machine Learning và Marketing. Astro xuất HTML tĩnh, bài viết bằng Markdown, không cần cơ sở dữ liệu hoặc tài khoản quản trị. Ngôn ngữ bản đầu: tiếng Việt. Thư mục này không phụ thuộc app Python hoặc các workbook trong repository.

## Xem thử trên máy

Cài Node.js 22.12 trở lên, mở terminal trong `personal-site`:

```sh
npm ci
npm run dev
```

Mở `http://localhost:4321`. Kiểm tra bản xuất bản:

```sh
npm run build
npm test
npm run preview
```

`npm test` kiểm tra các trang đã build: liên kết nội bộ, anchor, tài nguyên, heading và metadata. Giao diện cũng đã được kiểm tra bằng Chromium tại các chiều rộng 360, 390, 768, 1024 và 1440 px. Những kiểm tra này không thay thế kiểm thử trên mọi trình duyệt hoặc đánh giá accessibility đầy đủ.

## Đăng bài từ GitHub

1. Vào `personal-site/src/content/posts/` trên GitHub.
2. Chọn **Add file → Create new file** và đặt tên, ví dụ `mot-cau-hoi-moi.md`.
3. Viết frontmatter và nội dung Markdown, rồi commit.
4. Khi đã kết nối Cloudflare Pages, commit sẽ kích hoạt build/deploy mới.

```md
---
title: "Một câu hỏi mới về QML và Marketing"
description: "Giới thiệu ngắn cho bài viết."
date: 2026-10-27
category: "QML × MARKETING"
readingMinutes: 4
sample: false
---

Nội dung mở đầu.

## Câu hỏi nghiên cứu

Viết nội dung tại đây.
```

Tên file là đường dẫn bài. Bài viết được xếp theo ngày giảm dần. **Cả ba bài hiện tại có `sample: true` và hiển thị nhãn Bài mẫu**; chúng chưa phải công bố nghiên cứu của CT. Nhãn này chỉ phân biệt nội dung, không ẩn bài. Xóa hoặc thay các bài mẫu trước khi công bố nội dung chính thức. Đề cương QML trong dự án cũng được đánh dấu là minh họa, chưa có kết quả.

## Chỉnh nội dung

- Tên và liên hệ: `src/site.ts`. Email, LinkedIn, GitHub cá nhân hiện để trống; không tạo liên kết giả.
- Giới thiệu: `src/pages/gioi-thieu.astro`.
- Trang chủ: `src/pages/index.astro`.
- Bài viết: `src/content/posts/*.md`.
- Dự án: `src/content/projects/*.md`.
- Màu, font, bố cục: `src/styles/global.css` và `src/layouts/Base.astro`.
- Ảnh minh họa: `src/assets/research-desk.png`; bản public dùng cho metadata chia sẻ ở `public/images/research-desk.png`.

Thông tin học vị, đơn vị công tác và thành tích không được tự tạo. Nội dung giới thiệu dài, các bài mẫu và đề cương cần CT duyệt trước khi công bố như thông tin cá nhân chính thức. Dự án Base × SAP có liên kết mã nguồn thật; website không tuyên bố dự án đó là một nghiên cứu QML.

## Đưa lên Cloudflare Pages

Mã nguồn đã có thể build, nhưng chưa có website công khai hoặc tên miền nào được tạo tự động.

Trong Cloudflare, tạo **Pages project → Connect to Git** rồi chọn repository:

| Cài đặt | Giá trị |
|---|---|
| Production branch | `main` |
| Root directory | `personal-site` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Node version | `22` hoặc bản >=22.12 tương thích |

Cloudflare cung cấp địa chỉ `*.pages.dev`. Sau khi biết địa chỉ thật, thêm biến môi trường `SITE_URL=https://ten-thuc-te.pages.dev` rồi deploy lại; nếu có tên miền riêng, thay bằng tên miền đó. Không điền địa chỉ ví dụ như một địa chỉ đã thuộc về mình. Canonical và metadata URL tuyệt đối chỉ được thêm khi cấu hình SITE_URL. Không cần API key của Base hoặc SAP.

Có thể gắn tên miền riêng sau trong Custom domains. Không cần thuê VPS hay chạy server Astro trong production.

## Thiết kế và tài nguyên

Lấy cảm hứng editorial từ OSPAIC: cam đất, typography serif lớn, đường kẻ và chỉ mục bên trái. Không sao chép logo, tranh hay thư viện Pretext từ website mẫu. Bố cục và script đọc trang được viết riêng; cân dòng bằng CSS `text-wrap: balance`, không tuyên bố có toàn bộ thuật toán Pretext.

Font Piazzolla Variable và Commissioner Variable được self-host qua Fontsource, có subset tiếng Việt và giấy phép trong package font tương ứng. Tranh bàn nghiên cứu được tạo riêng bằng công cụ sinh ảnh; là minh họa, không phải ảnh chụp bàn làm việc của CT. Không dùng analytics, cookie quảng cáo hoặc biểu mẫu thu thập dữ liệu trong bản đầu.

## Ảnh chụp bản đầu

- [Desktop](preview/desktop.png)
- [Mobile](preview/mobile.png)
- [Trang đọc bài](preview/article.png)

Ảnh chụp từ Chromium của bản build, không phải mockup. Bài và đề cương mẫu được ghi nhãn ngay trên website.
