# Boston Pharma — Giới thiệu app hồ sơ thanh toán

20 slide tiếng Việt dành cho người không chuyên kỹ thuật. PowerPoint có thể chỉnh sửa và có ghi chú thuyết trình; PDF để xem nhanh.

- [Tải PowerPoint](https://github.com/ductranhuylund/MacquarieExcelTimeSeriesModelsforBusinessForecasting/raw/refs/heads/main/docs/presentations/boston-ocr/Boston_OCR_Gioi_thieu_ung_dung.pptx)
- [Xem PDF](Boston_OCR_Gioi_thieu_ung_dung.pdf)
- [Xem bìa](preview.png)

Nội dung dựa trên mã nguồn trong gói OCR_BP-main.zip người dùng cung cấp. Ảnh giao diện dùng dữ liệu giả lập và kết nối Electron/OCR/AI mô phỏng. Không đưa mã nguồn ứng dụng, chứng từ gốc, khóa truy cập hoặc địa chỉ máy chủ vào thư mục này. Chưa kiểm thử OCR/AI đầu cuối với dịch vụ thực tế.

Nếu liên kết tải trực tiếp không hoạt động: mở file trong GitHub, chọn **Download raw file** ở góc trên bên phải hoặc mở **Raw** rồi lưu file.

## Bản cập nhật: ý nghĩa ứng dụng và hai lớp AI

- Slide 3: từ chứng từ rời rạc tới thông tin dùng lại để lập hồ sơ.
- Slide 4–5: OCR / AI nhận diện, từ ảnh sang chữ; tài liệu có chữ sẵn được đọc trực tiếp.
- Slide 6: LLM / Generative AI hỗ trợ phân biệt ngữ cảnh, đề xuất trường trong biểu mẫu và bổ sung trường thiếu từ chữ nguồn.
- Slide 7: vai trò phối hợp của OCR, LLM, quy tắc nghiệp vụ và người dùng.

Nhãn “Classic ML” trên slide có chú thích: phân nhóm theo vai trò nhận diện, không phải khẳng định OCR không dùng deep learning. Tài liệu API có ví dụ các mô hình nhận diện, nhưng máy chủ triển khai chưa được kiểm tra live. LLM có thể tắt, dùng lại bộ nhớ hoặc fallback theo quy tắc; không phải mỗi lượt đều gọi AI. Không giao LLM tự quyết số tiền, phê duyệt hoặc thanh toán.
