import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from unittest.mock import patch
import unittest
from PySide6.QtGui import QPixmap,QColor
import test_workspace
import base_sap_workspace as brand

# Reuse real Qt widgets with the offline browser adapter.
test_workspace.appmod=brand
class BrandTests(test_workspace.GuiTests):
    def test_brand_header_palette_and_primary_actions(self):
        w=self.window
        self.assertIn('Boston Pharma',w.windowTitle())
        self.assertIn('#168D80',w.styleSheet())
        self.assertIsNone(w.findChild(brand.QLabel, 'brandLogo'))
        self.assertIsNone(w.findChild(brand.QLabel, 'brandTitle'))
        self.assertEqual(w.refresh.objectName(),'primary')
        self.assertEqual(w.sap_find.objectName(),'sapSearch')

    def test_logo_is_copied_persisted_and_used_as_icon(self):
        w=self.window
        source=Path(self.temp.name)/'test-logo.png'
        image=QPixmap(220,140);image.fill(QColor('#168D80'))
        self.assertTrue(image.save(str(source)))
        with patch.object(brand.QFileDialog,'getOpenFileName',return_value=(str(source),'')):
            w.choose_brand_logo()
        self.assertEqual(w.brand_path().read_bytes(),source.read_bytes())
        self.assertFalse(w.windowIcon().isNull())
        # Original can disappear and app still retains the exact selected file.
        source.unlink()
        again=brand.Window()
        self.assertFalse(again.windowIcon().isNull())
        again.close();again.deleteLater();self.qt.processEvents()

    def test_invalid_logo_preserves_existing_file(self):
        w=self.window
        old=QPixmap(20,20);old.fill(QColor('#168D80'));old.save(str(w.brand_path()),'PNG')
        before=w.brand_path().read_bytes()
        bad=Path(self.temp.name)/'bad.png';bad.write_text('not an image')
        with patch.object(brand.QFileDialog,'getOpenFileName',return_value=(str(bad),'')), patch.object(brand.QMessageBox,'warning') as warn:
            w.choose_brand_logo()
        warn.assert_called_once()
        self.assertEqual(w.brand_path().read_bytes(),before)

if __name__=='__main__':
    # Run brand-specific checks; other tests run in the regression suite.
    names=[n for n in BrandTests.__dict__ if n.startswith('test_')]
    suite=unittest.TestSuite(BrandTests(n) for n in names)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
