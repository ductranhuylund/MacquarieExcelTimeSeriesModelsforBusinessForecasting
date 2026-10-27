# Boston Pharma — So sánh Python Workspace và Reply Email

Deck 14 slide, tỷ lệ 16:9, tiếng Việt, cập nhật ngày 27/10/2026.

- `Boston_Pharma_So_sanh_Python_Email.pptx`: PowerPoint có thể chỉnh sửa; chữ và sơ đồ là đối tượng native.
- `Boston_Pharma_So_sanh_Python_Email.pdf`: bản xem nhanh được dựng từ cùng nội dung và bố cục.
- `build_deck.py`: mã tạo deck, dùng python-pptx, reportlab, PyMuPDF và Pillow; font DejaVu Sans cho PDF trên Linux.

## Nguồn và phạm vi

1. App và README tại `base-sap-workspace/`, tham chiếu commit `705933d`.
2. Tài liệu người dùng cung cấp: “MÔ TẢ LUỒNG VẬN HÀNH (FLOW) CƠ CHẾ REPLY EMAIL.docx”. Không lưu bản tài liệu gốc trong thư mục này.

App hiện hỗ trợ đối chiếu và điều hướng ME29N; người dùng duyệt thủ công. PR chưa có mapping. Kiểm thử SAP GUI dùng mô phỏng; vẫn cần UAT Windows thực tế.

Luồng email là thiết kế đề xuất, không phải bằng chứng đã triển khai. Các nhận định về xác thực, duyệt trùng, từ chối, commit và audit cần được đội SAP/mail xác minh. Đồng bộ kết quả email về Base chưa được mô tả trong tài liệu.

Deck không đưa ra ngân sách, tiến độ cam kết hoặc mức tiết kiệm chưa được đo. Không chứa thông tin đăng nhập, token, router hoặc dữ liệu PO thực tế. Màu theo ảnh nhận diện được cung cấp; không thay thế brand guideline chính thức. Nhãn BOSTON PHARMA được trình bày bằng chữ, không giả lập logo hình chính thức.
