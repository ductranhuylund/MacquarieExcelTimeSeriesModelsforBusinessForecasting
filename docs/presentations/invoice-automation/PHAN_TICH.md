# Phân tích mô hình — đọc mã, không thực thi nghiệp vụ

## Luồng và ý nghĩa

Mục tiêu là giảm việc tải từng hóa đơn, đọc/chuyển thông tin thủ công và gõ lại trong SAP. Bốn script trao đổi qua thư mục, Excel và JSON; chưa thấy bộ điều phối hoặc màn hình duyệt thống nhất. Chưa có số đo hiệu quả vận hành.

1. **Code 1:** đọc sheet Service Tickets, lấy liên kết và thêm ID vào tên file; tải bằng phiên đăng nhập Base. Việc bỏ qua tên file đã tồn tại chưa chứng minh file đầy đủ hoặc hóa đơn đã được xử lý đúng một lần.
2. **Code 2:** chọn các điều kiện cố định trên ME2N, xuất Excel, lọc theo vị trí cột và chọn file có PO khớp trong tên. Cần xác minh cột GR/IR và ý nghĩa trạng thái trong layout thực tế.
3. **Code 3:** dùng PyMuPDF đọc chữ PDF, gửi chữ/tên file tới Llama 4 Scout qua Groq, lưu JSON và bảng Excel, chuyển file sang thư mục đã xử lý bước trích xuất.
4. **Code 4:** nhóm các dòng Reference liên tiếp, mở MIRO, điền PO/tiền/thuế, so khớp dòng hàng, yêu cầu một số thông tin bổ sung và có nhánh cố lưu/post theo control ID. Kết quả ghi Excel dựa vào từ khóa thông báo SAP.

## Vai trò AI

- LLM được cấu hình: `meta-llama/llama-4-scout-17b-16e-instruct`.
- Dịch vụ: Groq, giao diện API tương thích OpenAI. Không phải GPT và không phải triển khai LLM nội bộ.
- Đầu vào là tên file và chữ lấy từ PDF; không gửi ảnh. Chưa có OCR trong source này.
- Đầu ra gồm ngày hóa đơn, Reference, diễn giải, PO, tiền, mã/tiền thuế và items. JSON đúng cú pháp vẫn có thể sai nghiệp vụ.
- Chọn nhóm hàng/mã thuế là đề xuất theo prompt; cần xác nhận cách ánh xạ với cấu hình kế toán. Tên hàng có thể trùng từ khóa ở nhiều nhóm.
- Regex, danh sách từ đồng nghĩa, SequenceMatcher và SAP GUI Scripting không phải mô hình Classic ML đã huấn luyện.

## Đọc chữ không đồng nghĩa suy luận nghiệp vụ

PyMuPDF lấy chữ có sẵn, còn OCR nhận diện chữ trong ảnh. OCR có thể dùng mô hình học sâu/ngữ cảnh để đọc chính xác hơn, nhưng tác vụ đọc chữ không tự xác nhận điều kiện kế toán, tính hợp lệ của chứng từ hoặc quyết định được phép ghi nhận.

LLM có thể hỗ trợ suy luận; tuy nhiên source hiện chủ yếu yêu cầu trích xuất, phân loại nhóm hàng và chuẩn hóa trường hóa đơn. Chưa có quy trình suy luận nghiệp vụ có kiểm chứng đủ để tự xác nhận hóa đơn hợp lệ. Regex, fuzzy matching và các điều kiện Python vẫn là logic đã lập trình; kết quả cần đối chiếu và xác nhận.

## Các vấn đề ưu tiên

### 1. Cần kiểm tra điều kiện GR/IR

Code lọc `GR == 0` và `IR > 0` (sau chuyển số), lấy cột bằng vị trí. Nếu IR là invoice receipts đã ghi nhận, điều kiện này không chứng minh PO chưa có hóa đơn. Layout thay đổi có thể làm đọc nhầm cột. Cần xác nhận trường, đơn vị, phạm vi PO và quy tắc chống nhập trùng.

### 2. Tổng PO được tính trước khi có dòng

`line_items` được tạo rỗng rồi tính `po_total`; sau đó mới đọc và append các dòng SAP. Tổng không được tính lại trước nhánh so sánh. Đã tái hiện quy tắc độc lập: tổng giữ 0 dù danh sách sau đó có giá trị 3.500.000. Cần tính sau khi đọc đủ dòng và kiểm tra lỗi đọc.

### 3. Ép cân bằng có thể chọn sai dòng

Source có nhánh bổ sung dòng gần phần tiền còn thiếu và chọn tất cả nếu vẫn thiếu. Việc chọn đủ hoặc vượt tiền không chứng minh đúng hàng/PO. Nên chuyển ngoại lệ sang người dùng, không tự thêm dòng chỉ để đạt tổng.

### 4. Định dạng tiền chưa thống nhất

Hàm Code 4 bỏ mọi dấu chấm/phẩy làm `3.500.000,00` thành `350000000`, lệch 100 lần. Cần bộ parser số xác định rõ locale, đơn vị tiền và phần thập phân; từ chối trường hợp mơ hồ. Không lấy lỗi parse thành số 0 rồi tiếp tục hạch toán.

### 5. Các bản dữ liệu có thể lệch

JSON được lưu trước bước sửa PO từ tên file và chuẩn hóa tiền. Excel có thể chứa giá trị khác JSON. Nên có một record chuẩn sau kiểm tra, từ đó xuất cả hai. Mã PO lấy sau khi loại mọi ký tự không phải số có thể ghép các đoạn số không liên quan; không nên mặc định tên file là nguồn luôn đúng.

### 6. Cần bảo vệ việc ghi Excel và chạy lại

Code tạo threads, semaphore giới hạn lượt gọi LLM, nhưng bước đọc-nối-ghi Excel không có khóa. Có thể ghi đè kết quả khi xử lý đồng thời. Cũng chưa có khóa duy nhất theo nhà cung cấp/ký hiệu/số/ngày hóa đơn và cơ chế đối soát sau timeout. Trạng thái cũ trong Excel chưa được dùng để bỏ qua trước khi Code 4 xử lý.

### 7. Các xác nhận SAP còn yếu

Dùng phiên đầu tiên, đường dẫn control ID cố định, sleep/Enter và nhiều khối bỏ qua lỗi. Không phải mọi lần điền đều được đọc lại xác nhận. Từ khóa created/posted chưa thay thế kiểm tra số chứng từ, fiscal year, company code và trạng thái thực. Chưa chạy để xác định hành vi cụ thể của các nút trên SAP.

## Lộ trình đề xuất

1. Đọc PDF và xuất dữ liệu để kiểm tra; chặn trang ít chữ, lỗi schema, tiền/thuế/PO mơ hồ.
2. Xác minh ME2N, chuẩn hóa record, chống trùng và ghi Excel an toàn.
3. Chạy trên môi trường được phép; điền MIRO rồi dừng trước lưu/post.
4. Bổ sung bước xác nhận và đối chiếu sau ghi trước khi mở tự động hóa sâu hơn.

Thông tin đăng nhập phải được quản lý ngoài mã nguồn. Không dùng tài liệu công khai để lưu phiên đăng nhập. Không kiểm tra tính hợp lệ của phiên hoặc dùng chúng để gọi hệ thống trong lần phân tích này.
