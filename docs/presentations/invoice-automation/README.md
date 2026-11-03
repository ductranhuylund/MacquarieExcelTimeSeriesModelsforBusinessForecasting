# Mô hình nhập hóa đơn tự động — Boston Pharma

17 slide tiếng Việt cho người không chuyên kỹ thuật, dựa trên tài liệu `Mo_hinh_nhap_hoa_don_tu_dong.txt` do người dùng cung cấp.

- [PowerPoint chỉnh sửa được](https://github.com/ductranhuylund/MacquarieExcelTimeSeriesModelsforBusinessForecasting/raw/refs/heads/main/docs/presentations/invoice-automation/Boston_Nhap_Hoa_Don_Tu_Dong.pptx)
- [PDF](Boston_Nhap_Hoa_Don_Tu_Dong.pdf)
- [Phân tích mã và các điểm cần sửa](PHAN_TICH.md)
- [Các hàm PyMuPDF đọc text layer](python/pdf_text_layer.py)

## Điểm chính

Mô hình gồm 4 đoạn Python: tải chứng từ từ link trong Excel xuất Base; xuất/lọc ME2N; đọc PDF và gọi LLM; nhập dữ liệu qua SAP GUI vào MIRO.

AI được cấu hình là **Llama 4 Scout** (`meta-llama/llama-4-scout-17b-16e-instruct`) qua **Groq API**. Thư viện OpenAI chỉ là client tương thích, không đồng nghĩa dùng mô hình GPT. Không phải Qwen/Ollama của ứng dụng trước.

Bản source dùng PyMuPDF lấy text layer, **chưa có bước OCR** hoặc gửi ảnh cho mô hình. Regex, SequenceMatcher và tự động hóa GUI là quy tắc/thao tác, không phải mô hình Classic ML được huấn luyện.

Code có nhánh cố ghi nhận trên SAP, không chỉ điền thử. Chưa thực thi hoặc xác minh ý nghĩa control ID trên hệ thống SAP thực tế. Deck phân biệt mã hiện tại với kiểm soát nên bổ sung, không khẳng định đạt hiệu quả hoặc độ chính xác đã đo.

## Hàm đọc PDF để học và dùng riêng

Các hàm được viết thêm trong `python/`, **chưa sửa hoặc tích hợp vào mô hình gốc**. Không tải file từ Base, gọi Groq hoặc thao tác SAP.

```bat
python -m pip install -r python/requirements.txt
python python/pdf_text_layer.py hoa_don_mau.pdf --output chu_doc_duoc.txt
python -m unittest discover -s python -v
```

Trong Python:

```python
from pdf_text_layer import read_pdf_text, require_text_for_next_step

result = read_pdf_text("hoa_don_mau.pdf", min_text_chars=40)
print("Trang cần kiểm tra:", result.low_text_pages)
text = require_text_for_next_step(result)
# Chỉ có văn bản ở đây; chưa gửi LLM hoặc xác nhận nghiệp vụ.
```

- `read_page_text(page)`: lấy chữ có sẵn trên một trang bằng `page.get_text("text", sort=True)`.
- `read_pdf_text(path)`: mở file, xử lý kiểm tra mật khẩu, đọc từng trang và tự đóng file. Trả kết quả có số trang và danh sách trang ít chữ.
- `require_text_for_next_step(result)`: điểm dừng minh họa nếu có trang ít chữ. Không tự OCR hoặc gọi API.

Ngưỡng ký tự không phát hiện chắc chắn ảnh scan: trang trống/nội dung ngắn cũng có thể bị đánh dấu. Trang nhiều chữ vẫn có thể chứa ảnh chưa được đọc. `sort=True` không bảo đảm mọi bảng/cột đúng thứ tự. Các hàm không diễn giải hay chuyển đổi số tiền. Cần kiểm tra nghiệp vụ riêng.

Đã chạy 5 kiểm thử với tài liệu giả lập: đọc text và giữ định dạng tiền; trang trống; PDF chỉ chứa ảnh; PDF có mật khẩu; file lỗi và tham số sai. Cả 4 khối source gốc được kiểm tra cú pháp bằng AST; điều này không xác nhận chạy được đầu cuối.

Không đưa tài liệu source gốc, phiên đăng nhập, khóa truy cập, đường dẫn cá nhân hoặc chứng từ thật lên thư mục công khai này.

## Phân biệt đọc chữ và reasoning

- PyMuPDF lấy text layer có sẵn; không phải OCR.
- OCR nhận diện chữ trong ảnh; chức năng này chưa phải suy luận nghiệp vụ.
- LLM có thể hỗ trợ reasoning, nhưng code đang dùng chủ yếu cho trích xuất, phân loại và chuẩn hóa. Không nên coi mọi lần gọi LLM là reasoning, hoặc coi kết quả JSON là chứng nhận hóa đơn hợp lệ.
- Phần mềm tính toán/kiểm tra các quy tắc đã lập trình. Người dùng đối chiếu chứng từ, xử lý ngoại lệ và xác nhận nghiệp vụ.

Đã đưa nội dung này vào slide 6 (Reading và Reasoning), trong cả PowerPoint và PDF.
