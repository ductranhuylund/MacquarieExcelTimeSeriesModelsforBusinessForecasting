"""Capture real Qt app widgets with simulated services; no Base/SAP connections."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'base-sap-workspace'))
from test_workspace import GuiTests, job
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout

OUT=Path(__file__).resolve().parent/'screenshots'
OUT.mkdir(exist_ok=True)
GuiTests.setUpClass()
GuiTests.qt.setFont(QFont('DejaVu Sans',11))
test=GuiTests('test_session_setup_reuses_one_nonmodal_dialog');test.setUp()
w=test.window
w.resize(1740,920)
warning=QLabel('ẢNH CHỤP GIAO DIỆN APP • DỮ LIỆU MẪU • API / SAP ĐƯỢC MÔ PHỎNG')
warning.setStyleSheet('background:#DFF2ED;color:#087F78;padding:8px;font-weight:bold')
w.centralWidget().layout().insertWidget(0,warning)
# Render representative document content inside the simulated browser widget.
layout=QVBoxLayout(w.browser)
page=QTextBrowser()
page.setHtml('''<body style="font-family:DejaVu Sans;color:#163B40;font-size:16px">
<p style="color:#087F78">NỘI DUNG MINH HỌA — KHÔNG PHẢI TRANG BASE TRỰC TIẾP</p>
<h2>PO 4500000001 — Vật tư mẫu A</h2><p>Workflow: Nguyên liệu — F011</p>
<hr><h3>MÔ TẢ</h3><p>Nội dung nhiệm vụ và tài liệu phục vụ đối chiếu.</p>
<p>Người dùng kiểm tra thông tin rồi thao tác trên từng hệ thống.</p></body>''')
layout.addWidget(page)
rows=[job(3,name='PO 4500000003 — Vật tư mẫu C'),job(2,name='PO 4500000002 — Vật tư mẫu B'),job(1,name='PO 4500000001 — Vật tư mẫu A')]
test.populate(rows=rows)
w.api_status.setText('API Base: dữ liệu mẫu F011 / active')
w.sap_connection_label.setText('MÔ PHỎNG: phiên SAP sẵn sàng. Chưa kết nối SAP thật.')
w.table.selectRow(2)
w.sap_po.setText('4500000001')
w.sap_actual.setText('MÔ PHỎNG — PO đang hiển thị trên SAP: 4500000001')
w.sap_info.setText('Minh họa kết quả đối chiếu cùng mã PO.\nKhông phải xác nhận giao dịch SAP thực tế.')
w.sap_host.placeholder.setText('VÙNG NHÚNG SAP GUI TRÊN WINDOWS\n\nMáy chụp slide không kết nối SAP thật.\nẢnh này chỉ minh họa bố cục và thông tin đối chiếu.')
w.sap_host.placeholder.setStyleSheet('background:#E8F2EE;color:#587371;padding:20px;border:1px dashed #9DCAC0')
w.show();test.qt.processEvents()
# Queue crop uses Qt's widget capture, not a reconstructed illustration.
left=w.left
left.grab(QRect(0,0,left.width(),min(320,left.height()))).save(str(OUT/'02_base_queue_demo.png'))
w.right.grab(QRect(0,0,w.right.width(),min(205,w.right.height()))).save(str(OUT/'03_sap_match_demo.png'))
w.open_connections();test.qt.processEvents()
w.start_dialog.resize(720,590)
w.start_dialog.refresh_status();test.qt.processEvents()
w.start_dialog.grab().save(str(OUT/'04_session_start_demo.png'))
test.tearDown()
print('Captured 3 screenshots of native app widgets using simulated services.')
