"""One-file Windows desktop workspace. No SAP search is implemented yet."""
import os
import re
import sys
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from PySide6.QtCore import Qt, QThread, QUrl, Signal, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QComboBox, QTabBar, QSplitter,
    QInputDialog, QDialog, QTableView, QAbstractItemView, QHeaderView,
    QToolButton, QMenu, QFileDialog, QMessageBox,
)
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView

API = 'https://workflow.base.vn/extapi/v1/jobs/get'
WORKFLOWS = [
    ('Nguyên liệu — F011', 3991),
    ('Bao bì — F012', 4156),
    ('Khác — F013', 4157),
]
STATE_LABELS = {'active': 'Đang xử lý', 'done': 'Hoàn thành', 'failed': 'Thất bại'}
COMPACT_JS = r"""
(() => {
 if(location.hostname!=='workflow.base.vn')return;
 const sid='base-viewer-compact';
 if(document.getElementById(sid))return;
 const s=document.createElement('style');s.id=sid;
 s.textContent=`
 body.bvcompact #navigator,body.bvcompact #job-display>.side-layout{display:none!important}
 body.bvcompact #document,body.bvcompact #master,body.bvcompact #pagew,body.bvcompact #page{
 margin-left:0!important;margin-right:0!important;padding-left:0!important;
 left:0!important;right:0!important;width:100%!important;min-width:0!important;max-width:none!important}
 body.bvcompact #job-display-canvas{position:fixed!important;inset:0!important;
 width:100%!important;height:100%!important;overflow:auto!important;background:white!important}
 body.bvcompact #job-display{margin:0!important;width:100%!important;min-width:0!important;max-width:none!important}
 body.bvcompact #job-display>.main-layout{display:block!important;float:none!important;
 position:relative!important;left:auto!important;right:auto!important;margin:0!important;
 width:100%!important;min-width:0!important;max-width:none!important;box-sizing:border-box!important}`;
 document.head.appendChild(s);
 function update(){const on=!window.baseViewerFullPage&&/^\/job\/\d+(?:\/|$)/.test(location.pathname)&&!!document.querySelector('#job-display>.main-layout');
 if(document.body.classList.contains('bvcompact')!==on)document.body.classList.toggle('bvcompact',on);}
 update();let pending=false;
 new MutationObserver(()=>{if(!pending){pending=true;requestAnimationFrame(()=>{pending=false;update()})}})
 .observe(document.body,{childList:true,subtree:true});
})();
"""


# Teal palette approximated from the supplied Boston Pharma logo image.
BRAND_STYLE = """
QWidget { font-family: "Segoe UI", Arial; font-size: 12px; color: #193C37; }
QMainWindow, QDialog { background-color: #F3F8F6; }
QLabel { background: transparent; }
QLabel#brandLogo { background: white; color: #168D80; border: 1px solid #D9EAE5;
    border-radius: 8px; font-family: Georgia; font-size: 16px; font-weight: 600; }
QLabel#brandTitle { color: #086B61; font-size: 18px; font-weight: 600; }
QLabel#connectionStatus { color: #50756D; font-size: 11px; }
QLineEdit, QComboBox { background: white; border: 1px solid #BCD8D0;
    border-radius: 5px; padding: 6px; selection-background-color: #0C756A; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #168D80; }
QLineEdit:read-only { background: #EDF5F1; }
QPushButton, QToolButton { background: white; border: 1px solid #BCD8D0;
    border-radius: 5px; padding: 7px 10px; color: #185D52; }
QPushButton:hover, QToolButton:hover { background: #E4F3ED; border-color: #168D80; }
QPushButton:pressed, QToolButton:pressed { background: #CCE9DE; }
QPushButton:checked { background: #D8EFE5; border-color: #168D80; }
QPushButton#primary, QPushButton#sapSearch { background: #0C756A;
    border-color: #0C756A; color: white; font-weight: 600; }
QPushButton#primary:hover, QPushButton#sapSearch:hover { background: #095F56; }
QPushButton:disabled, QToolButton:disabled { background: #ECF0EE;
    color: #8C9F99; border-color: #DFE7E3; }
QPushButton#primary:disabled, QPushButton#sapSearch:disabled { background: #D9E5DF;
    color: #7C958A; border-color: #D9E5DF; }
QTabBar::tab { background: #E8F2ED; color: #426A60; border: 1px solid #D0E2DA;
    padding: 9px 15px; min-width: 100px; }
QTabBar::tab:selected { color: #075E54; background: white;
    border-bottom: 3px solid #168D80; font-weight: 600; }
QTabBar::tab:hover:!selected { background: #DCEFE6; }
QTabBar::tab:disabled { background: #EDF1EF; color: #99AAA3; }
QTabBar#businessTabs::tab:selected { color: white; background: #0C756A;
    border-color: #0C756A; }
QTableView { background: white; alternate-background-color: #F3F9F5;
    border: 1px solid #CEE2D8; gridline-color: #E0EBE5;
    selection-background-color: #D7EEE3; selection-color: #124F43; }
QTableView::item { padding: 5px; }
QTableView::item:selected { background: #D7EEE3; color: #124F43; }
QHeaderView::section { background: #E7F3EC; color: #195C4E;
    padding: 7px; border: none; border-bottom: 1px solid #BEDCCD; font-weight: 600; }
QSplitter::handle { background: #D4E6DC; }
QSplitter::handle:hover { background: #168D80; }
QMenu { background: white; border: 1px solid #C5DDD1; padding: 4px; }
QMenu::item { padding: 8px 18px; }
QMenu::item:selected { background: #DCEFE4; color: #075E54; }
QComboBox QAbstractItemView { background: white; selection-background-color: #D7EEE3;
    selection-color: #124F43; border: 1px solid #BCD8D0; }
"""


def state_label(state):
    if not state:
        return 'Không có giá trị state'
    label = STATE_LABELS.get(state)
    return f'{label} ({state})' if label else state


def po_candidates(title):
    # This is recognition from text, not validation that the PO exists in SAP.
    found = re.findall(r'\bPO\s*[:#/-]?\s*(4\d{9})(?!\d)', title, re.I)
    if not found:
        found = re.findall(r'(?<!\d)(4\d{9})(?!\d)', title)
    return list(dict.fromkeys(found))


def fetch_jobs(token, workflow_id, cancelled, report):
    jobs = {}
    with requests.Session() as session:
        def page(number):
            if cancelled():
                raise RuntimeError('Đã dừng lấy dữ liệu.')
            response = session.post(API, data={
                'access_token_v2': token, 'workflow_id': workflow_id,
                'page_id': number, 'limit': 100,
            }, timeout=(15, 45), allow_redirects=False)
            response.raise_for_status()
            obj = response.json()
            if obj.get('code') != 1:
                raise RuntimeError('Base API: ' + str(obj.get('message', 'Lỗi không xác định')))
            if int(obj.get('page', -1)) != number or not isinstance(obj.get('jobs'), list):
                raise RuntimeError('API trả sai trang hoặc cấu trúc dữ liệu.')
            return obj
        first = page(0)
        total, size = int(first['total_items']), int(first['items_per_page'])
        if size <= 0 or total < 0:
            raise RuntimeError('Thông tin phân trang không hợp lệ.')
        pages = max(1, (total + size - 1) // size)
        for number in range(pages):
            result = first if number == 0 else page(number)
            if int(result['total_items']) != total:
                raise RuntimeError('Danh sách thay đổi trong lúc đọc. Hãy làm mới lại.')
            for job in result['jobs']:
                if int(job['workflow_id']) != workflow_id:
                    raise RuntimeError('API trả nhiệm vụ ngoài workflow đang chọn.')
                stage = job.get('stage_export') or {}
                jid = str(int(job['id']))
                jobs[jid] = {
                    'id': jid, 'name': str(job.get('name') or ''),
                    'state': str(job.get('state') or ''),
                    'status': str(job.get('status', '')),
                    'stage': str(stage.get('name') or '') if isinstance(stage, dict) else '',
                }
            report(f'Đang đọc trang {number + 1}/{pages} — {len(jobs)}/{total} nhiệm vụ')
    if len(jobs) != total:
        raise RuntimeError(f'Chưa lấy đủ: {len(jobs)}/{total} mã job duy nhất.')
    return sorted(jobs.values(), key=lambda j: int(j['id']), reverse=True)


class Loader(QThread):
    loaded = Signal(list)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, token, workflow_id, parent):
        super().__init__(parent)
        self.token, self.workflow_id = token, workflow_id

    def run(self):
        try:
            jobs = fetch_jobs(self.token, self.workflow_id,
                              self.isInterruptionRequested, self.progress.emit)
            if not self.isInterruptionRequested():
                self.loaded.emit(jobs)
        except requests.RequestException:
            self.failed.emit('Không kết nối được Base API. Kiểm tra mạng rồi thử lại.')
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.token = ''


class JobModel(QAbstractTableModel):
    columns = [('Mã job', 'id'), ('Tiêu đề', 'name'),
               ('Trạng thái Base', 'state'), ('Giai đoạn', 'stage')]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []

    def replace(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.ToolTipRole):
            value = self.rows[index.row()][self.columns[index.column()][1]]
            return state_label(value) if index.column() == 2 else value
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.columns[section][0]
        return None


class ConnectionDialog(QDialog):
    def __init__(self, has_token, parent):
        super().__init__(parent)
        self.setWindowTitle('Kết nối Base')
        self.resize(570, 230)
        layout = QVBoxLayout(self)
        label = QLabel('Base API lấy danh sách; trình duyệt Base dùng phiên đăng nhập riêng.')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText('Đã có token trong RAM; nhập để thay token' if has_token else 'Access token v2')
        layout.addWidget(self.token)
        note = QLabel('Token chỉ giữ trong RAM đến khi đóng app. Không nhập mật khẩu Base vào ô này.')
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QHBoxLayout()
        layout.addLayout(row)
        login = QPushButton('Mở đăng nhập Base')
        login.clicked.connect(lambda: self.done(2))
        row.addWidget(login)
        save = QPushButton('Lưu token')
        save.clicked.connect(self.accept)
        row.addWidget(save)
        close = QPushButton('Đóng')
        close.clicked.connect(self.reject)
        row.addWidget(close)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_token = ''
        self.worker = None
        self.closing = False
        self.rendering = False
        self.page_ready = False
        self.current_job = None
        self.current_index = 0
        self.sessions = {wid: {'jobs': None, 'state': 'active', 'query': '',
            'selected': None, 'expanded': True, 'updated': ''} for _, wid in WORKFLOWS}
        self.setWindowTitle('Boston Pharma — Đối chiếu PO / PR — Base & SAP')
        self.setStyleSheet(BRAND_STYLE)
        self.resize(1650, 1000)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        top = QHBoxLayout()
        layout.addLayout(top)
        self.brand_logo = QLabel('BOSTON\nPHARMA')
        self.brand_logo.setObjectName('brandLogo')
        self.brand_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brand_logo.setFixedSize(160, 94)
        top.addWidget(self.brand_logo)
        title = QLabel('ĐỐI CHIẾU PO / PR\nBASE & SAP')
        title.setObjectName('brandTitle')
        top.addWidget(title)
        top.addStretch()
        self.api_status = QLabel('API Base: chưa kiểm tra')
        self.api_status.setObjectName('connectionStatus')
        top.addWidget(self.api_status)
        self.connection = QPushButton('Kết nối')
        self.connection.clicked.connect(self.open_connections)
        top.addWidget(self.connection)
        settings = QToolButton()
        settings.setText('Cài đặt')
        settings.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(settings)
        menu.addAction('Chọn logo Boston Pharma…', self.choose_brand_logo)
        settings.setMenu(menu)
        top.addWidget(settings)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.business = QTabBar()
        self.business.setObjectName('businessTabs')
        self.business.addTab('PO — Đơn mua hàng')
        self.business.addTab('PR — Yêu cầu mua hàng')
        self.business.setTabEnabled(1, False)
        self.business.setTabToolTip(1, 'Chờ xác định workflow PR trên Base.')
        row.addWidget(self.business)
        row.addStretch()
        self.view_mode = QComboBox()
        self.view_mode.addItems(['Chia đôi', 'Mở rộng Base', 'Mở rộng SAP'])
        self.view_mode.currentIndexChanged.connect(self.change_layout)
        row.addWidget(self.view_mode)
        self.tabs = QTabBar()
        self.tabs.setExpanding(True)
        for name, _ in WORKFLOWS:
            self.tabs.addTab(name)
        layout.addWidget(self.tabs)
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.setChildrenCollapsible(False)
        layout.addWidget(self.split, 1)
        self.left = QWidget()
        left = QVBoxLayout(self.left)
        left.setContentsMargins(0, 0, 0, 0)
        self.left.setMinimumWidth(380)
        self.split.addWidget(self.left)
        left.addWidget(QLabel('BASE — Nhiệm vụ của workflow đang chọn'))
        row = QHBoxLayout()
        left.addLayout(row)
        self.states = QComboBox()
        self.states.setToolTip('Giữ nguyên giá trị state của Base API.')
        row.addWidget(self.states)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Tìm mã job / PO / tiêu đề…')
        row.addWidget(self.search, 1)
        self.refresh = QPushButton('Làm mới danh sách')
        self.refresh.setObjectName('primary')
        row.addWidget(self.refresh)
        self.list_toggle = QToolButton()
        self.list_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.list_toggle.setCheckable(True)
        self.list_toggle.setChecked(True)
        self.list_toggle.setArrowType(Qt.ArrowType.DownArrow)
        left.addWidget(self.list_toggle)
        self.model = JobModel(self)
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setMinimumHeight(120)
        self.table.setMaximumHeight(220)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(35)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 120)
        left.addWidget(self.table)
        self.count = QLabel()
        left.addWidget(self.count)
        row = QHBoxLayout()
        left.addLayout(row)
        self.previous = QPushButton('← Trước')
        row.addWidget(self.previous)
        self.position = QLabel('Chưa chọn nhiệm vụ')
        row.addWidget(self.position, 1)
        self.next = QPushButton('Tiếp theo →')
        row.addWidget(self.next)
        self.full_page = QPushButton('Xem trang Base đầy đủ')
        self.full_page.setCheckable(True)
        row.addWidget(self.full_page)
        self.reload = QPushButton('Tải lại trang Base')
        row.addWidget(self.reload)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.TextFormat.PlainText)
        left.addWidget(self.info)
        self.browser = QWebEngineView()
        left.addWidget(self.browser, 1)
        self.browser_note = QLabel('Trình duyệt Base: chưa mở trang đăng nhập')
        self.browser_note.setWordWrap(True)
        left.addWidget(self.browser_note)
        data = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'BaseF011Viewer'
        data.mkdir(parents=True, exist_ok=True)
        self.profile = QWebEngineProfile('BaseF011', self)
        self.profile.setPersistentStoragePath(str(data / 'profile'))
        self.profile.setCachePath(str(data / 'cache'))
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        self.page = QWebEnginePage(self.profile, self.browser)
        self.browser.setPage(self.page)
        self.middle = QWidget()
        self.middle.setFixedWidth(178)
        middle = QVBoxLayout(self.middle)
        self.sap_find = QPushButton('Tìm nhiệm vụ SAP →')
        self.sap_find.setObjectName('sapSearch')
        self.sap_find.setEnabled(False)
        self.sap_find.setToolTip('Nhận PO từ job Base. Chưa kết nối để tìm trên SAP.')
        middle.addStretch()
        middle.addWidget(self.sap_find)
        middle.addStretch()
        self.split.addWidget(self.middle)
        self.right = QWidget()
        self.right.setMinimumWidth(300)
        right = QVBoxLayout(self.right)
        self.split.addWidget(self.right)
        right.addWidget(QLabel('SAP — Nhiệm vụ tương ứng'))
        self.sap_po = QLineEdit()
        self.sap_po.setReadOnly(True)
        self.sap_po.setPlaceholderText('PO nhận từ nhiệm vụ Base')
        right.addWidget(self.sap_po)
        self.sap_info = QLabel()
        self.sap_info.setWordWrap(True)
        self.sap_info.setTextFormat(Qt.TextFormat.PlainText)
        right.addWidget(self.sap_info)
        right.addStretch()
        self.tabs.currentChanged.connect(self.change_tab)
        self.states.currentIndexChanged.connect(self.filters_changed)
        self.search.textChanged.connect(self.filters_changed)
        self.refresh.clicked.connect(self.load_jobs)
        self.list_toggle.toggled.connect(self.toggle_list)
        self.table.selectionModel().currentRowChanged.connect(self.row_selected)
        self.previous.clicked.connect(lambda: self.move(-1))
        self.next.clicked.connect(lambda: self.move(1))
        self.full_page.toggled.connect(self.apply_page_layout)
        self.reload.clicked.connect(self.browser.reload)
        self.sap_find.clicked.connect(self.find_sap)
        self.browser.loadStarted.connect(self.page_loading)
        self.browser.loadFinished.connect(self.page_loaded)
        self.browser.urlChanged.connect(self.url_changed)
        self.load_brand_logo()
        self.reset_sap()
        self.restore_tab()
        self.change_layout(0)

    def brand_path(self):
        root = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'BaseF011Viewer'
        root.mkdir(parents=True, exist_ok=True)
        return root / 'boston_logo'

    def load_brand_logo(self):
        candidates = [self.brand_path(), Path(__file__).with_name('boston_logo.png')]
        for path in candidates:
            if path.is_file():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    self.brand_logo.setPixmap(pixmap.scaled(
                        148, 84, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation))
                    self.brand_logo.setToolTip('Boston Pharma')
                    self.setWindowIcon(QIcon(pixmap))
                    return True
        self.brand_logo.setToolTip('Chọn ảnh logo tại Cài đặt → Chọn logo Boston Pharma.')
        return False

    def choose_brand_logo(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Chọn logo Boston Pharma', '',
            'Ảnh logo (*.png *.jpg *.jpeg *.webp)')
        if not filename:
            return
        source = Path(filename)
        try:
            if source.stat().st_size > 10 * 1024 * 1024:
                raise ValueError('Chọn ảnh logo nhỏ hơn 10 MB.')
            if QPixmap(str(source)).isNull():
                raise ValueError('Không đọc được ảnh logo.')
            destination = self.brand_path()
            if source.resolve() != destination.resolve():
                shutil.copyfile(source, destination)
            self.load_brand_logo()
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Logo Boston Pharma', str(exc))

    def session(self):
        return self.sessions[WORKFLOWS[self.current_index][1]]

    def workflow_name(self):
        return WORKFLOWS[self.current_index][0]

    def open_connections(self):
        dialog = ConnectionDialog(bool(self.api_token), self)
        result = dialog.exec()
        token = dialog.token.text().strip()
        dialog.token.clear()
        if result == 2:
            self.browser.setUrl(QUrl('https://workflow.base.vn/'))
        elif result == QDialog.DialogCode.Accepted and token:
            if token != self.api_token:
                self.api_token = token
                for session in self.sessions.values():
                    session.update(jobs=None, selected=None, updated='')
                self.api_status.setText('API Base: chưa kiểm tra token mới')
                self.restore_tab()
            self.load_jobs()
        dialog.deleteLater()

    def change_tab(self, index):
        self.current_index = index
        self.restore_tab()
        # Fetch only when requested; switching tabs never submits API work.

    def restore_tab(self):
        session = self.session()
        self.states.blockSignals(True)
        self.states.clear()
        self.states.addItem('Tất cả trạng thái', '*')
        states = set(STATE_LABELS) | {j['state'] for j in (session['jobs'] or [])}
        for state in sorted(states):
            self.states.addItem(state_label(state), state)
        index = self.states.findData(session['state'])
        self.states.setCurrentIndex(index if index >= 0 else 0)
        self.states.blockSignals(False)
        self.search.blockSignals(True)
        self.search.setText(session['query'])
        self.search.blockSignals(False)
        self.list_toggle.blockSignals(True)
        self.list_toggle.setChecked(session['expanded'])
        self.list_toggle.blockSignals(False)
        self.set_list_visible(session['expanded'])
        self.info.setText('Chưa lấy dữ liệu. Bấm Làm mới danh sách.' if session['jobs'] is None else '')
        self.render_rows()

    def filters_changed(self, *_):
        self.session()['state'] = self.states.currentData()
        self.session()['query'] = self.search.text()
        self.render_rows()

    def render_rows(self):
        session = self.session()
        jobs = session['jobs'] or []
        query = session['query'].strip().casefold()
        rows = [j for j in jobs if (session['state'] == '*' or j['state'] == session['state'])
                and query in (j['id'] + ' ' + j['name']).casefold()]
        selected = next((i for i, j in enumerate(rows) if j['id'] == session['selected']), -1)
        if selected < 0 and rows:
            selected = 0
        self.rendering = True
        self.model.replace(rows)
        if selected >= 0:
            self.table.selectRow(selected)
        self.rendering = False
        self.list_toggle.setText(f'Danh sách nhiệm vụ ({len(rows)})')
        suffix = f" · lần lấy: {session['updated']} (giờ Việt Nam)" if session['updated'] else ''
        self.count.setText(f'{len(rows)} nhiệm vụ hiển thị / {len(jobs)} nhiệm vụ đã lấy' + suffix)
        self.show_job(rows[selected] if selected >= 0 else None)

    def toggle_list(self, expanded):
        self.session()['expanded'] = expanded
        self.set_list_visible(expanded)

    def set_list_visible(self, expanded):
        self.table.setVisible(expanded)
        self.list_toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)

    def row_selected(self, current, previous):
        if not self.rendering and current.isValid():
            self.show_job(self.model.rows[current.row()])

    def show_job(self, job):
        changed = self.current_job != job
        self.current_job = job
        if changed:
            self.reset_sap()
        self.session()['selected'] = job['id'] if job else None
        index = next((i for i, j in enumerate(self.model.rows) if job and j['id'] == job['id']), -1)
        self.previous.setEnabled(index > 0)
        self.next.setEnabled(0 <= index < len(self.model.rows) - 1)
        self.position.setText(f'Nhiệm vụ {index + 1}/{len(self.model.rows)}' if job else 'Chưa chọn nhiệm vụ')
        self.sync_sap_button()
        if job:
            target = QUrl(f"https://workflow.base.vn/job/{job['id']}")
            if self.browser.url() != target:
                self.page_ready = False
                self.sap_find.setEnabled(False)
                self.browser.setUrl(target)
        elif self.browser.url().toString() not in ('', 'about:blank'):
            self.browser.setUrl(QUrl('about:blank'))

    def move(self, delta):
        current = self.table.currentIndex().row()
        target = current + delta
        if 0 <= target < len(self.model.rows):
            self.table.selectRow(target)
            self.table.scrollTo(self.model.index(target, 0))

    def load_jobs(self):
        if self.worker and self.worker.isRunning():
            return
        if not self.api_token:
            self.open_connections()
            return
        self.refresh.setEnabled(False)
        self.connection.setEnabled(False)
        self.tabs.setEnabled(False)
        self.api_status.setText('API Base: đang đọc ' + self.workflow_name())
        self.worker = Loader(self.api_token, WORKFLOWS[self.current_index][1], self)
        self.worker.progress.connect(self.info.setText)
        self.worker.loaded.connect(self.received)
        self.worker.failed.connect(self.load_failed)
        self.worker.finished.connect(self.load_finished)
        self.worker.start()

    def received(self, jobs):
        session = self.sessions[self.worker.workflow_id]
        session['jobs'] = jobs
        session['updated'] = datetime.now(timezone(timedelta(hours=7))).strftime('%d/%m/%Y %H:%M:%S')
        self.api_status.setText('API Base: đã đọc ' + self.workflow_name())
        self.restore_tab()
        self.info.setText('Danh sách đã cập nhật. Thao tác trong trang Base là thao tác thật.')

    def load_failed(self, message):
        self.api_status.setText('API Base: lỗi đọc dữ liệu')
        self.info.setText(message + (' Đang giữ dữ liệu cũ.' if self.session()['jobs'] is not None else ''))

    def load_finished(self):
        self.refresh.setEnabled(True)
        self.connection.setEnabled(True)
        self.tabs.setEnabled(True)
        if self.closing:
            self.close()

    def change_layout(self, mode):
        self.left.setVisible(mode != 2)
        self.middle.setVisible(mode == 0)
        self.right.setVisible(mode != 1)
        if mode == 0:
            self.split.setSizes([700, 178, 700])

    def page_loading(self):
        self.page_ready = False
        self.sap_find.setEnabled(False)
        self.reset_sap()

    def page_loaded(self, success):
        self.page_ready = success
        if success:
            self.apply_page_layout()
        elif self.browser.url().toString() != 'about:blank':
            self.info.setText('Trang Base chưa tải được. Kiểm tra mạng hoặc mở đăng nhập trong Kết nối.')
        self.sync_sap_button()

    def apply_page_layout(self, *_):
        if not self.page_ready:
            return
        self.browser.page().runJavaScript(COMPACT_JS)
        # The observer honors this flag when Base updates its DOM.
        disabled = 'true' if self.full_page.isChecked() else 'false'
        self.browser.page().runJavaScript(
            'window.baseViewerFullPage=' + disabled + ';'
            "document.body.classList.toggle('bvcompact', !window.baseViewerFullPage && "
            "!!document.querySelector('#job-display>.main-layout') && /^\\/job\\/\\d+(?:\\/|$)/.test(location.pathname));")

    def url_changed(self, url):
        self.reset_sap()
        parsed = urlparse(url.toString())
        if parsed.hostname == 'workflow.base.vn':
            note = 'đang mở trang job' if re.fullmatch(r'/job/\d+/?', parsed.path) else 'đang mở trang Base / đăng nhập'
        elif parsed.scheme in ('http', 'https'):
            note = 'đang mở trang ngoài Base / SSO'
        else:
            note = 'chưa mở trang Base'
        self.browser_note.setText('Trình duyệt Base: ' + note + '. Không xác minh đăng nhập chỉ từ URL.')
        self.sync_sap_button()

    def sync_sap_button(self):
        parsed = urlparse(self.browser.url().toString())
        match = re.fullmatch(r'/job/(\d+)/?', parsed.path)
        enabled = bool(self.page_ready and self.current_job and parsed.hostname == 'workflow.base.vn'
                       and match and match.group(1) == self.current_job['id'])
        self.sap_find.setEnabled(enabled)

    def reset_sap(self):
        self.sap_po.clear()
        self.sap_info.setText('Chưa kết nối SAP. Chưa thực hiện tìm nhiệm vụ tương ứng.')

    def find_sap(self):
        if not self.sap_find.isEnabled() or not self.current_job:
            return
        source_id = self.current_job['id']
        self.browser.page().runJavaScript(
            "document.querySelector('#job-display>.main-layout h1')?.innerText || ''",
            lambda title: self.prepare_sap(source_id, title))

    def prepare_sap(self, source_id, title):
        if not self.current_job or self.current_job['id'] != source_id or not self.sap_find.isEnabled():
            return
        candidates = po_candidates(title or self.current_job['name'])
        if len(candidates) == 1:
            po = candidates[0]
        elif candidates:
            po, ok = QInputDialog.getItem(self, 'Chọn PO', 'Có nhiều số PO. Chọn số cần tìm:', candidates, 0, False)
            if not ok:
                return
        else:
            po, ok = QInputDialog.getText(self, 'Nhập PO', 'Chưa nhận diện được PO. Nhập PO gồm 10 chữ số:')
            if not ok:
                return
            po = po.strip()
        if not re.fullmatch(r'\d{10}', po):
            self.sap_info.setText('PO cần có đúng 10 chữ số.')
            return
        self.sync_sap_button()
        if not self.current_job or self.current_job['id'] != source_id or not self.sap_find.isEnabled():
            return
        self.sap_po.setText(po)
        self.sap_info.setText(f'Yêu cầu tìm nhiệm vụ SAP cho PO {po}.\n'
            f'Nguồn: {self.workflow_name()}, job {source_id}.\n'
            'Chưa kết nối SAP nên chưa thực hiện tìm kiếm.')

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.closing = True
            self.worker.requestInterruption()
            self.info.setText('Đang dừng yêu cầu API trước khi đóng…')
            event.ignore()
        else:
            self.api_token = ''
            event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())

# HẾT FILE — không cần các file Python cũ.
