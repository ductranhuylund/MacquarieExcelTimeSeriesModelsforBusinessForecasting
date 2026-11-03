"""Đọc text layer của PDF bằng PyMuPDF. Không OCR và không gửi dữ liệu lên mạng."""
from dataclasses import dataclass
from pathlib import Path

import fitz  # Cài: python -m pip install PyMuPDF


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str
    alnum_chars: int
    needs_review: bool


@dataclass(frozen=True)
class PDFTextResult:
    filename: str
    pages: tuple[PageText, ...]

    @property
    def text(self) -> str:
        """Gom chữ và giữ dấu trang để đối chiếu được nguồn."""
        return "\n\n".join(
            f"--- Trang {page.page_number} ---\n{page.text}" for page in self.pages
        )

    @property
    def low_text_pages(self) -> list[int]:
        return [page.page_number for page in self.pages if page.needs_review]


class PDFTextError(ValueError):
    """Không đọc được tài liệu hoặc tài liệu chưa phù hợp để chuyển bước tiếp."""


def read_page_text(page: fitz.Page, *, sort: bool = True) -> str:
    """Lấy chữ có sẵn, không nhận diện chữ trong ảnh.

    sort=True sắp chữ theo vị trí; không bảo đảm đúng thứ tự mọi bảng/nhiều cột.
    Không đổi định dạng tiền, tên hoặc mã số trong kết quả.
    """
    return page.get_text("text", sort=sort).strip()


def read_pdf_text(
    pdf_path: str | Path,
    *,
    password: str | None = None,
    min_text_chars: int = 40,
    sort: bool = True,
) -> PDFTextResult:
    """Đọc từng trang và đánh dấu trang ít chữ để người dùng kiểm tra.

    Trang ít chữ có thể là ảnh scan, trang trống, nội dung ngắn hoặc chữ lỗi;
    đây chỉ là gợi ý kiểm tra, không phải kết luận đã xác định PDF scan.
    Ngược lại, nhiều chữ không chứng minh mọi vùng ảnh trong trang đã được đọc.
    """
    if min_text_chars < 1:
        raise ValueError("min_text_chars phải >= 1.")
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file: {path.name}")
    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        raise PDFTextError("Không mở được tài liệu; kiểm tra file PDF.") from exc

    with doc:  # Tự đóng file, kể cả khi xử lý gặp lỗi.
        if not doc.is_pdf:
            raise PDFTextError("Tài liệu được chọn không phải PDF.")
        if doc.needs_pass and (not password or not doc.authenticate(password)):
            raise PDFTextError("PDF cần mật khẩu đúng trước khi đọc.")
        if doc.page_count == 0:
            raise PDFTextError("PDF không có trang.")
        pages = []
        for number, page in enumerate(doc, start=1):
            text = read_page_text(page, sort=sort)
            chars = sum(char.isalnum() for char in text)
            pages.append(PageText(number, text, chars, chars < min_text_chars))
        return PDFTextResult(path.name, tuple(pages))


def require_text_for_next_step(result: PDFTextResult) -> str:
    """Điểm dừng mẫu trước LLM; hàm này không tự OCR hoặc gọi API.

    Dừng nếu có trang ít chữ. Đối chiếu/OCR nếu cần rồi đọc lại. Ngưỡng này
    không thay thế việc kiểm tra chất lượng chữ, bảng và vùng ảnh của con người.
    """
    if not result.pages:
        raise PDFTextError("Không có trang để xử lý.")
    if result.low_text_pages:
        pages = ", ".join(map(str, result.low_text_pages))
        raise PDFTextError(
            f"Trang {pages} ít hoặc không có chữ. Kiểm tra bản gốc và OCR nếu cần; "
            "chưa chuyển sang LLM."
        )
    return result.text


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", help="Đường dẫn file PDF")
    parser.add_argument("--min-chars", type=int, default=40)
    parser.add_argument("--output", help="File TXT để lưu chữ đọc được (không gửi mạng)")
    args = parser.parse_args()
    result = read_pdf_text(args.pdf, min_text_chars=args.min_chars)
    print(f"Đã đọc {len(result.pages)} trang.")
    print("Trang cần kiểm tra:", result.low_text_pages or "Không thấy theo ngưỡng ký tự")
    if args.output:
        Path(args.output).write_text(result.text, encoding="utf-8")
        print("Đã lưu file TXT. Đây là chữ trích xuất, chưa phải dữ liệu đã xác nhận.")
