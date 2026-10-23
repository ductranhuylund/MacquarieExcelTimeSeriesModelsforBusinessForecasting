# Boston Pharma — Đối chiếu PO / PR — Base & SAP

App Python chạy trên Windows, dùng Qt WebEngine để xem trang Base trong trình duyệt nhúng. Logo Boston Pharma chỉ dùng làm icon cạnh tiêu đề trên thanh cửa sổ, không có banner logo/tiêu đề lớn trong nội dung. File chạy chính: `base_sap_workspace.py`. Không cần các file Python phiên bản cũ hoặc các workbook Excel trong repository để chạy app này.

## Cài đặt và chạy

Cài Python 3.12 trở lên, bản 64-bit. Mở CMD trong thư mục `base-sap-workspace` rồi chạy:

```bat
python -m pip install -r requirements.txt
python base_sap_workspace.py
```

Hoặc sau khi cài thư viện, mở `run_windows.bat`. Nếu chỉ muốn dùng một file Python, cài `PySide6 requests` rồi chạy `base_sap_workspace.py`.

## Cách sử dụng

1. Bấm **Kết nối**, nhập token Base Workflow v2 và bấm **Lưu token**. App lấy danh sách của workflow đang chọn. Token chỉ giữ trong RAM đến khi đóng app, không được ghi vào mã nguồn hoặc file cấu hình.
2. Vào **Kết nối → Mở đăng nhập Base**, đăng nhập trực tiếp trên website trong khung trái. Token API và phiên đăng nhập trình duyệt là hai phần độc lập.
3. Chọn **Nguyên liệu — F011**, **Bao bì — F012**, hoặc **Khác — F013**. Với tab chưa có dữ liệu, bấm **Làm mới danh sách**. App không tự gọi API khi chuyển tab.
4. Ba tab workflow được đặt trong khung Base và căn trái. Lọc theo `state` gốc của Base, tìm theo mã job, PO hoặc tiêu đề; ô tìm kiếm thu gọn để **Làm mới danh sách** và **Danh sách nhiệm vụ** nằm cùng hàng. Bảng chỉ có **Mã job** và **Tiêu đề**, hiển thị trọn 3 dòng rồi cuộn để xem tiếp. Tất cả job vẫn được giữ, không giới hạn danh sách còn 3 job. Chọn một dòng hoặc dùng **Trước / Tiếp theo**; có thể thu gọn bảng.
5. Bộ lọc, từ tìm kiếm, nhiệm vụ đã chọn và trạng thái mở/thu gọn danh sách được nhớ riêng theo workflow trong phiên chạy. Không lọc theo ngày.
6. **Tìm nhiệm vụ SAP →** nhận PO từ tiêu đề job đang mở; nếu có nhiều PO, app cho chọn, nếu không nhận diện được thì cho nhập. **Chưa có kết nối SAP: hiện nút chỉ hiển thị yêu cầu tìm kiếm và nguồn PO, không tìm hoặc trả kết quả SAP.**
7. Có thể kéo thanh chia khung hoặc chọn **Mở rộng Base / Chia đôi / Mở rộng SAP**. **Xem trang Base đầy đủ** thay đổi bố cục hiển thị, không tải lại trang.

**PR đang tạm khóa**, chờ xác định workflow tương ứng. App không gộp trạng thái Base/SAP hoặc tạo trạng thái nghiệp vụ mới.

## Logo và màu Boston Pharma

Khung app có phối màu xanh ngọc gần theo ảnh nhận diện được cung cấp, chưa phải bảng mã màu chính thức từ brand guideline. Trang Base bên trong giữ giao diện gốc.

Chọn **Cài đặt → Chọn logo Boston Pharma…** để dùng ảnh PNG/JPG/WEBP trên máy. App sao chép nguyên file vào `%LOCALAPPDATA%\BaseF011Viewer\boston_logo`, tự dùng lại lần sau và đặt làm icon cửa sổ. Hoặc đặt `boston_logo.png` cạnh file Python. Logo hình không được đóng gói trong repository; khi chưa chọn ảnh, cửa sổ dùng icon mặc định của hệ điều hành.

## Phạm vi lấy dữ liệu

Endpoint đọc: `POST https://workflow.base.vn/extapi/v1/jobs/get`, gửi `access_token_v2`, `workflow_id`, `page_id` bắt đầu từ 0 và `limit=100`.

| Tab | Workflow ID |
|---|---:|
| F011 | 3991 |
| F012 | 4156 |
| F013 | 4157 |

App kiểm tra workflow ID, trang phản hồi và tổng số mã job duy nhất trước khi chấp nhận dữ liệu. Các nhiệm vụ chỉ nằm trong phạm vi token có quyền đọc. Nhận diện PO từ tiêu đề là gợi ý văn bản, không xác nhận PO tồn tại trên SAP.

## Lưu ý khi thao tác

Các nút trong trang Base thực hiện thao tác thật. Hoàn tất hoặc lưu nội dung trước khi chuyển job hoặc tải lại trang. **Làm mới danh sách** gọi lại API; **Tải lại trang Base** chỉ tải lại job đang mở. Không có cơ chế tự tải lại định kỳ.

Profile trình duyệt nằm tại `%LOCALAPPDATA%\BaseF011Viewer`. Không chia sẻ thư mục này hoặc đưa cookie/token vào Git. Không mở nhiều bản app dùng cùng profile cùng lúc. Một số nhà cung cấp SSO có thể hạn chế trình duyệt nhúng.

## Kiểm thử

```bat
python test_workspace.py
python test_boston_brand.py
```

Trên Linux không có màn hình, đặt `QT_QPA_PLATFORM=offscreen` khi chạy kiểm thử. Bộ kiểm thử dùng Qt widgets/model thực tế, mô phỏng API và trình duyệt để không gửi dữ liệu hoặc thao tác lên hệ thống thật.

Đã đạt 23 kiểm thử giao diện/logic và 3 kiểm thử nhận diện thương hiệu trên Linux. Ba kiểm thử bố cục mới cũng được chạy lại ở mức phóng đại 150% để kiểm tra hàng nút, tab căn trái và 3 dòng hiển thị. Đã kiểm tra riêng bố cục nhúng bằng Chromium ngoại tuyến. Giao diện/đăng nhập Base trên Windows và SAP cần kiểm tra trong môi trường sử dụng thực tế. Không có token, phiên đăng nhập hoặc dữ liệu xuất từ Base/SAP trong thư mục ứng dụng này.

## Minh họa bố cục

Ảnh sử dụng dữ liệu thử và khung trình duyệt mô phỏng, không phải phản hồi Base/SAP trực tiếp.

![Bố cục thu gọn: tab trong Base, bảng ba dòng, hai cột](docs/layout-preview.png)
