---
title: "Base × SAP Workspace"
description: "Một ứng dụng Python đưa nhiệm vụ Base và PO trên SAP vào cùng không gian đối chiếu."
number: "01"
status: "Đã có mã nguồn"
type: "PYTHON / TỰ ĐỘNG HÓA"
year: "2026"
repository: "https://github.com/ductranhuylund/MacquarieExcelTimeSeriesModelsforBusinessForecasting/tree/main/base-sap-workspace"
---
## Bài toán

Khi một nhiệm vụ trên Base liên quan đến PO trên SAP, người xử lý cần tìm đúng chứng từ, đối chiếu thông tin và thao tác trên từng hệ thống. Việc chuyển qua lại giữa các cửa sổ làm tăng số bước và nguy cơ nhầm PO.

## Cách tiếp cận

Ứng dụng Python dùng Base API để lấy danh sách nhiệm vụ của các workflow F011, F012 và F013. Giao diện đặt website Base và SAP GUI cạnh nhau.

Người dùng chọn một job rồi bấm **Tìm nhiệm vụ SAP**. App điều hướng tới ME29N và tìm PO tương ứng, đồng thời phân biệt mã PO yêu cầu với mã PO đang hiển thị trên SAP.

## Phạm vi hiện tại

- Lọc theo trạng thái và giữ dữ liệu tạm trong phiên làm việc.
- Xem và chuyển lần lượt các nhiệm vụ Base.
- Kết nối SAP GUI trên Windows và hỗ trợ điều hướng chứng từ.
- Người dùng tự quyết định và thực hiện phê duyệt trên từng hệ thống.

Ứng dụng **không tự bấm Release hoặc Save**, và không mặc định cả hai hệ thống đã hoàn tất chỉ từ việc gửi yêu cầu tìm PO.

## Điều còn cần kiểm tra

Các kiểm thử tự động có dùng mô phỏng API và SAP COM. Khả năng nhúng SAP GUI, hộp thoại và hành vi theo cấu hình máy cần được kiểm tra trong môi trường Windows thực tế.

Đây là dự án công cụ nghiệp vụ, không phải một thực nghiệm QML. Nó được đưa vào đây để minh họa một hướng thực hành: giảm thao tác lặp lại và làm rõ thông tin cần kiểm tra trước khi ra quyết định.
