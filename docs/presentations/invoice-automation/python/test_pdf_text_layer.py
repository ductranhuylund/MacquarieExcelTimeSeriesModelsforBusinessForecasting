import tempfile
import unittest
from pathlib import Path

import fitz
from pdf_text_layer import PDFTextError, read_pdf_text, require_text_for_next_step

TEXT = "Demo invoice INV-001. Supplier Example Ltd. Amount 3.500.000,00 VND. Date 03.11.2026."

class PDFReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def make_pdf(self, *, blank=False, encrypted=False):
        target = self.root / 'invoice.pdf'
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((50, 80), TEXT, fontsize=9)
            if blank:
                doc.new_page()
            kwargs = dict(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw='owner-demo', user_pw='user-demo') if encrypted else {}
            doc.save(target, **kwargs)
        return target
    def test_text_and_money_format_are_preserved(self):
        result = read_pdf_text(self.make_pdf())
        self.assertFalse(result.low_text_pages)
        self.assertIn('3.500.000,00', result.text)
        self.assertIn('Trang 1', require_text_for_next_step(result))
    def test_empty_page_is_flagged_without_claiming_scan_detection(self):
        result = read_pdf_text(self.make_pdf(blank=True))
        self.assertEqual(result.low_text_pages, [2])
        with self.assertRaises(PDFTextError):
            require_text_for_next_step(result)
    def test_image_only_pdf_does_not_magically_produce_text(self):
        source = self.make_pdf()
        with fitz.open(source) as doc:
            image = doc[0].get_pixmap().tobytes('png')
        target = self.root / 'scan.pdf'
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_image(page.rect, stream=image)
            doc.save(target)
        result = read_pdf_text(target)
        self.assertEqual(result.pages[0].text, '')
        self.assertEqual(result.low_text_pages, [1])
    def test_encrypted_pdf_requires_correct_password(self):
        source = self.make_pdf(encrypted=True)
        for password in [None, 'wrong']:
            with self.assertRaises(PDFTextError):
                read_pdf_text(source, password=password)
        self.assertIn('INV-001', read_pdf_text(source, password='user-demo').text)
    def test_bad_file_and_invalid_threshold(self):
        with self.assertRaises(FileNotFoundError):
            read_pdf_text(self.root / 'missing.pdf')
        target = self.root / 'bad.pdf'; target.write_bytes(b'not a pdf')
        with self.assertRaises(PDFTextError):
            read_pdf_text(target)
        with self.assertRaises(ValueError):
            read_pdf_text(target, min_text_chars=0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
