"""Base + native SAP GUI workspace. Opens ME29N; never automates Release/Save."""
import os
import re
import sys
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests
from PySide6.QtCore import Qt, QThread, QUrl, Signal, QAbstractTableModel, QModelIndex, QObject, QTimer
from PySide6.QtGui import QPixmap, QIcon, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QComboBox, QTabBar, QSplitter,
    QInputDialog, QDialog, QTableView, QAbstractItemView, QHeaderView,
    QToolButton, QMenu, QFileDialog, QMessageBox, QSizePolicy,
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
QWidget { font-family: "Segoe UI", Arial; font-size: 9pt; color: #193C37; }
QMainWindow, QDialog { background-color: #F3F8F6; }
QLabel { background: transparent; }
QLabel#connectionStatus { color: #50756D; font-size: 8pt; }
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



def console_notice(message):
    if ("Failed to execute 'postMessage'" in message
            and 'wchat.freshchat.com' in message and 'origin' in message):
        return 'freshchat_origin'
    if ('NotAllowedError' in message and 'play() failed' in message
            and "user didn't interact" in message):
        return 'autoplay_blocked'
    return None


class BrowserPage(QWebEnginePage):
    def __init__(self, profile, parent):
        super().__init__(profile, parent)
        self.notices = set()

    def javaScriptConsoleMessage(self, level, message, line, source):
        notice = console_notice(message)
        if notice:
            # Explain each known website warning once; do not disable security
            # checks, autoplay policy, or unrelated JavaScript error messages.
            if notice not in self.notices:
                self.notices.add(notice)
                text = ('Tiện ích chat Base gặp cảnh báo origin; không phải lỗi API.'
                        if notice == 'freshchat_origin' else
                        'Trình duyệt chặn âm thanh tự phát khi chưa tương tác.')
                print('[Base] ' + text, file=sys.stderr)
            return
        super().javaScriptConsoleMessage(level, message, line, source)


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


def fetch_jobs(token, workflow_id, cancelled, report, state='*'):
    jobs = {}
    with requests.Session() as session:
        def page(number):
            if cancelled():
                raise RuntimeError('Đã dừng lấy dữ liệu.')
            parameters = {'access_token_v2': token, 'workflow_id': workflow_id,
                          'page_id': number, 'limit': 100}
            if state != '*':
                # Base expects the textual state in the parameter named status.
                parameters['status'] = state
            response = session.post(API, data=parameters,
                                    timeout=(15, 45), allow_redirects=False)
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
                if state != '*' and str(job.get('state') or '') != state:
                    raise RuntimeError('API không áp dụng đúng bộ lọc trạng thái; không dùng kết quả chưa đầy đủ.')
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

    def __init__(self, token, workflow_id, parent, state='*'):
        super().__init__(parent)
        self.token, self.workflow_id = token, workflow_id
        self.request_state = state

    def run(self):
        try:
            jobs = fetch_jobs(self.token, self.workflow_id,
                              self.isInterruptionRequested, self.progress.emit, state=self.request_state)
            if not self.isInterruptionRequested():
                self.loaded.emit(jobs)
        except requests.RequestException:
            if not self.isInterruptionRequested():
                self.failed.emit('Không kết nối được Base API. Kiểm tra mạng rồi thử lại.')
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
        finally:
            self.token = ''


SAP_LOGON_PATH = r'C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe'
SAP_CONNECTION = 'PRD800'


def sap_find(node, control_id):
    try:
        return node.FindById(control_id, False)
    except Exception:
        return None


def sap_named(node, name, kind):
    try:
        return node.FindByName(name, kind)
    except Exception:
        return None


def sap_children(node):
    return [node.Children(i) for i in range(int(node.Children.Count))]


def sap_text(value):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', str(value or '').lower())
                   if unicodedata.category(c) != 'Mn')


class SapNavigationError(RuntimeError):
    pass


class SapNavigator:
    """Bounded, read/open-only ME29N navigation. Never presses Release/Save."""
    def __init__(self, po, clock=None):
        if not re.fullmatch(r'[0-9]{10}', po):
            raise SapNavigationError('PO phải gồm đúng 10 chữ số.')
        self.po = po
        self.clock = clock or __import__('time').monotonic
        self.phase = 'start'
        self.deadline = self.clock() + 25

    def select_dialog(self, session):
        # SAP themes may expose this as txt/ctxt or nest it in a subscreen.
        modals = [w for w in sap_children(session) if str(w.Type) == 'GuiModalWindow']
        for modal in modals:
            for kind in ('GuiCTextField', 'GuiTextField'):
                field = sap_named(modal, 'MEPO_SELECT-EBELN', kind)
                if field is not None:
                    return modal, field
            match = re.search(r'wnd\[\d+\]$', str(modal.Id))
            if match:
                for prefix in ('ctxt', 'txt'):
                    field = sap_find(session, match[0] + '/usr/' + prefix + 'MEPO_SELECT-EBELN')
                    if field is not None:
                        return modal, field
        return None, None

    @staticmethod
    def current_po(main):
        for name in ('MEPO_TOPLINE-EBELN', 'EKKO-EBELN', 'MEPOHEADER-EBELN'):
            for kind in ('GuiCTextField', 'GuiTextField'):
                field = sap_named(main, name, kind)
                if field is not None:
                    value = str(field.Text).strip()
                    if re.fullmatch(r'[0-9]{10}', value):
                        return value
        # SAP's document title can also provide positive confirmation.
        values = re.findall(r'(?<!\d)(\d{10})(?!\d)', str(main.Text))
        return values[0] if len(values) == 1 else None

    def other_document_button(self, session):
        roots = [sap_find(session, key) for key in ('wnd[0]/tbar[1]', 'wnd[0]/usr')]
        controls = []
        pending = [root for root in roots if root is not None]
        # ME29N places its document toolbar inside nested user containers on some themes.
        while pending and len(controls) < 1500:
            node = pending.pop(0)
            controls.append(node)
            try:
                pending.extend(sap_children(node))
            except Exception:
                pass
        allowed = ('other purchase order', 'other document', 'select document',
                   'other po', 'purchase order selection', 'chung tu khac',
                   'don hang khac', 'chon chung tu')
        for button in controls:
            if str(getattr(button, 'Type', '')) != 'GuiButton':
                continue
            label = sap_text(str(getattr(button, 'Tooltip', '')) + ' ' + str(getattr(button, 'Text', '')))
            if any(word in label for word in ('release', 'approve', 'save', 'duyet')):
                continue
            if any(term in label for term in allowed):
                return button
        return None

    def step(self, session):
        if session.Busy:
            if self.clock() > self.deadline:
                raise SapNavigationError('SAP xử lý quá lâu. Kiểm tra cửa sổ SAP rồi thử lại.')
            return None
        main = sap_find(session, 'wnd[0]')
        if main is None:
            raise SapNavigationError('Không tìm thấy cửa sổ chính của SAP.')
        modal, field = self.select_dialog(session)
        modals = [w for w in sap_children(session) if str(w.Type) == 'GuiModalWindow']
        unexpected_modal = (any(str(w.Id) != str(modal.Id) for w in modals)
                            if modal is not None else bool(modals))
        if unexpected_modal:
            unknown = next(w for w in modals if modal is None or str(w.Id) != str(modal.Id))
            try:
                unknown.SetFocus()  # Show the blocking dialog; never accept/dismiss it.
            except Exception:
                pass
            title = str(getattr(unknown, 'Text', '')).strip()[:160]
            identifier = str(unknown.Id).split('/')[-1]
            # Control IDs/types only: do not read input values or password fields.
            details = []
            queue = [unknown]
            visited = 0
            while queue and visited < 150:
                node = queue.pop(0)
                visited += 1
                kind = str(getattr(node, 'Type', ''))
                if kind in ('GuiTextField', 'GuiCTextField'):
                    details.append(str(getattr(node, 'Id', '')).split('/usr/')[-1][:120])
                try:
                    queue.extend(sap_children(node))
                except Exception:
                    pass
            fields = ' [Trường: ' + ', '.join(details[:8]) + ']' if details else ''
            raise SapNavigationError('Chưa mở được PO yêu cầu. Hộp thoại SAP đang chặn: '
                + identifier + (' — ' + title if title else '') + fields
                + '. Bấm Tách cửa sổ SAP để xem và xử lý hộp thoại, rồi bấm tìm lại.')
        status = sap_find(session, 'wnd[0]/sbar')
        if self.phase != 'start' and status is not None and str(status.MessageType) in ('E', 'A'):
            raise SapNavigationError('SAP báo lỗi: ' + str(status.Text))
        if self.phase == 'start':
            if modal is not None:
                self.phase = 'fill'
            elif str(session.Info.Transaction).upper() == 'ME29N':
                self.phase = 'open'
            else:
                session.StartTransaction('ME29N')
                self.phase = 'transaction'
            return None
        if self.phase == 'transaction':
            if str(session.Info.Transaction).upper() == 'ME29N':
                self.phase = 'open'
            elif self.clock() > self.deadline:
                raise SapNavigationError('Chưa mở được ME29N. Kiểm tra quyền transaction trên SAP.')
            return None
        if self.phase == 'open':
            if modal is not None:
                self.phase = 'fill'
                return None
            if self.current_po(main) == self.po:
                return ('verified', 'ME29N đang hiển thị đúng PO ' + self.po + '.')
            button = self.other_document_button(session)
            if button is None:
                raise SapNavigationError('Không nhận diện được nút Other Purchase Order. '
                    'Bạn bấm nút chọn chứng từ trên SAP thủ công, rồi bấm Tìm nhiệm vụ SAP lại.')
            button.Press()
            self.phase = 'dialog'
            self.deadline = self.clock() + 12
            return None
        if self.phase == 'dialog':
            if modal is not None:
                self.phase = 'fill'
            elif self.clock() > self.deadline:
                raise SapNavigationError('Chưa mở được hộp chọn PO trên SAP.')
            return None
        if self.phase == 'fill':
            if modal is None or field is None:
                raise SapNavigationError('Hộp chọn PO đã thay đổi. Bấm tìm lại.')
            container = sap_find(session, 'wnd[1]/usr')
            if container is not None:
                for control in sap_children(container):
                    if str(control.Type) == 'GuiRadioButton' and sap_text(control.Text).strip() in (
                            'pur. order', 'purchase order', 'don mua hang', 'don dat hang'):
                        control.Select()
            if not field.Changeable:
                raise SapNavigationError('Chọn loại Pur. Order trong hộp SAP rồi bấm tìm lại.')
            field.Text = self.po
            self.phase = 'submit'
            return None
        if self.phase == 'submit':
            if modal is None or field is None or str(field.Text).strip() != self.po:
                raise SapNavigationError('PO trong hộp chọn SAP không khớp yêu cầu.')
            # Enter ONLY in the positively identified document-selection dialog.
            modal.SendVKey(0)
            self.phase = 'verify'
            self.deadline = self.clock() + 15
            return None
        if self.phase == 'verify':
            if modal is None and str(session.Info.Transaction).upper() == 'ME29N':
                shown = self.current_po(main)
                if shown == self.po:
                    return ('verified', 'Đã mở ME29N và xác minh PO ' + self.po + '.')
                if self.clock() > self.deadline:
                    if shown:
                        raise SapNavigationError('SAP đang hiển thị PO khác: ' + shown + '. Chưa xác nhận kết quả.')
                    return ('unverified', 'Đã gửi yêu cầu mở PO ' + self.po
                            + ', nhưng chưa đọc được số PO để xác minh. Kiểm tra trên SAP.')
            elif self.clock() > self.deadline:
                raise SapNavigationError('SAP vẫn đang ở hộp chọn chứng từ. Kiểm tra thông báo trên SAP.')
        return None


class SapController(QObject):
    status_changed = Signal(str)
    document_changed = Signal(str)
    window_ready = Signal(object)
    navigation_changed = Signal()
    navigation_finished = Signal(int, str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.path, self.entry = SAP_LOGON_PATH, SAP_CONNECTION
        self.engine = self.connection = self.session = None
        self.mode = 'disconnected'
        self.pending = None
        self.navigator = None
        self.sequence = 0
        self.handle = None
        self.com = None
        self.opened = False
        self.initial_connections = set()
        self.polling = False
        self.login_probe_since = None
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.poll)

    @property
    def navigation_active(self):
        return self.pending is not None

    def connect_sap(self):
        if self.session is not None:
            try:
                self.status_changed.emit('Đang dùng kết nối SAP ' + self.entry + '.')
                self.show_window()
            except Exception:
                self.fail('Phiên SAP không còn sẵn sàng. Kiểm tra SAP Logon rồi kết nối lại.')
            return
        if self.mode in ('engine', 'connection', 'login'):
            return
        if sys.platform != 'win32':
            self.fail('SAP GUI nhúng chỉ chạy trên Windows.')
            return
        try:
            import pythoncom
            import win32com.client
            if self.com is None:
                pythoncom.CoInitialize()
                self.com = pythoncom
            self.dispatch = win32com.client
            try:
                self.engine = self.dispatch.GetObject('SAPGUI').GetScriptingEngine
            except Exception:
                path = Path(self.path)
                if not path.is_file():
                    self.fail('Không tìm thấy saplogon.exe. Kiểm tra Cài đặt → SAP GUI.')
                    return
                __import__('subprocess').Popen([str(path)])
            self.mode = 'engine'
            self.deadline = __import__('time').monotonic() + 60
            self.status_changed.emit('Đang mở SAP Logon. Chờ kết nối ' + self.entry + '…')
            self.timer.start()
        except ImportError:
            self.fail('Thiếu pywin32. Chạy: python -m pip install pywin32')
        except Exception:
            self.fail('Không truy cập được SAP GUI Scripting. Kiểm tra cài đặt Scripting trên máy.')

    def request_po(self, po):
        self.sequence += 1
        self.cancel_navigation()
        self.pending = (self.sequence, po)
        self.navigator = None
        self.navigation_changed.emit()
        # Defer so the UI records the Base source before any result is emitted.
        QTimer.singleShot(0, self.begin_pending)
        return self.sequence

    def begin_pending(self):
        if self.pending is None:
            return
        if self.session is None:
            self.connect_sap()
        else:
            self.timer.start()

    def cancel_navigation(self):
        if self.pending is not None:
            request_id, po = self.pending
            self.pending = self.navigator = None
            self.navigation_changed.emit()
            self.navigation_finished.emit(request_id, po, 'cancelled',
                'Đã dừng yêu cầu mở PO. Màn hình SAP có thể vẫn giữ chứng từ trước đó.')

    def finish_navigation(self, status, message):
        if self.pending is None:
            return
        request_id, po = self.pending
        self.pending = self.navigator = None
        self.navigation_changed.emit()
        self.navigation_finished.emit(request_id, po, status, message)

    def fail(self, message):
        self.status_changed.emit(message)
        self.document_changed.emit('Chưa đọc được PO trên SAP; không xác nhận khớp với Base.')
        self.mode = 'disconnected'
        self.opened = False
        self.timer.stop()
        self.engine = self.connection = self.session = None
        self.handle = None
        self.finish_navigation('error', message)

    def show_window(self):
        if self.session is not None and not self.session.Busy:
            main = sap_find(self.session, 'wnd[0]')
            if main is not None:
                handle = str(main.Handle)
                self.window_ready.emit(int(handle, 16) if handle.lower().startswith('0x') else int(handle))
                return True
        return False

    def poll(self):
        # COM calls may pump Windows messages while a SAP confirmation is open.
        # Do not let a nested Qt timer open another connection or navigate twice.
        if self.polling:
            return
        self.polling = True
        try:
            self.poll_once()
        finally:
            self.polling = False

    def poll_once(self):
        try:
            now = __import__('time').monotonic()
            if self.mode == 'engine':
                if self.engine is None:
                    try:
                        self.engine = self.dispatch.GetObject('SAPGUI').GetScriptingEngine
                    except Exception:
                        if now > self.deadline:
                            self.fail('Chưa truy cập được SAP Logon. Kiểm tra SAP GUI Scripting, rồi thử lại.')
                        return
                if not self.opened:
                    self.initial_connections = {str(c.Id) for c in sap_children(self.engine)}
                    self.opened = True
                    self.connection = self.engine.OpenConnection(self.entry, False)
                self.mode = 'connection'
                self.deadline = now + 60
            if self.mode == 'connection':
                if self.connection is None:
                    choices = [c for c in sap_children(self.engine)
                        if str(c.Id) not in self.initial_connections and str(c.Description).strip() == self.entry]
                    if len(choices) > 1:
                        self.fail('Có nhiều kết nối SAP mới cùng tên. Đóng kết nối thừa rồi thử lại.')
                        return
                    if choices:
                        self.connection = choices[0]
                if self.connection is not None:
                    if self.connection.DisabledByServer:
                        self.fail('SAP GUI Scripting bị tắt trên server. Cần quản trị SAP cho phép trước khi điều khiển.')
                        return
                    sessions = sap_children(self.connection)
                    if sessions:
                        self.session = sessions[0]
                        self.mode = 'login'
                        self.status_changed.emit('Đăng nhập trực tiếp trong cửa sổ SAP. App không đọc mật khẩu.')
                if self.session is None and now > self.deadline:
                    self.fail('Chưa mở được kết nối ' + self.entry + '. Kiểm tra cấu hình SAP Logon và mạng.')
                return
            if self.session is None:
                return
            if self.session.Busy:
                if self.navigator is not None:
                    self.navigator.step(self.session)  # Enforce timeout while SAP remains busy.
                return
            main = sap_find(self.session, 'wnd[0]')
            if main is not None:
                raw = str(main.Handle)
                handle = int(raw, 16) if raw.lower().startswith('0x') else int(raw)
                if handle != self.handle:
                    self.handle = handle
                    self.window_ready.emit(handle)
            try:
                user_ready = bool(str(self.session.Info.User).strip())
                transaction = str(self.session.Info.Transaction).strip()
            except Exception:
                if self.mode != 'login':
                    raise
                if self.login_probe_since is None:
                    self.login_probe_since = now
                    self.status_changed.emit('Đang chờ SAP hoàn tất đăng nhập; yêu cầu PO vẫn được giữ.')
                if now - self.login_probe_since > 120:
                    self.fail('Chưa đọc được phiên sau đăng nhập. Kiểm tra hộp thoại SAP rồi kết nối lại.')
                return
            self.login_probe_since = None
            if not user_ready or transaction.upper() in ('', 'S000', 'SAPMSYST'):
                return
            if self.mode != 'ready':
                self.mode = 'ready'
                self.status_changed.emit('SAP đã đăng nhập: ' + str(self.session.Info.SystemName)
                    + ' / client ' + str(self.session.Info.Client) + '. Chỉ mở PO, không tự duyệt.')
            shown = SapNavigator.current_po(main) if main is not None and transaction.upper() == 'ME29N' else None
            self.document_changed.emit('PO đang hiển thị trên SAP: ' + shown if shown
                else 'Chưa đọc được PO đang hiển thị trên SAP.')
            if self.pending is not None:
                if self.navigator is None:
                    self.navigator = SapNavigator(self.pending[1])
                result = self.navigator.step(self.session)
                if result is not None:
                    self.finish_navigation(*result)
        except SapNavigationError as exc:
            self.finish_navigation('error', str(exc))
        except Exception as exc:
            # Report phase/HRESULT only; raw COM messages may contain connection secrets.
            phase = self.navigator.phase if self.navigator is not None else self.mode
            code = getattr(exc, 'hresult', None)
            detail = f' [{phase}' + (f', HRESULT {code}' if isinstance(code, int) else '') + ']'
            self.fail('Không điều khiển được SAP' + detail + '. Kiểm tra hộp thoại SAP và quyền GUI Scripting.')

    def shutdown(self):
        self.timer.stop()
        self.pending = self.navigator = None
        self.session = self.connection = self.engine = None
        if self.com is not None:
            self.com.CoUninitialize()
            self.com = None


class Win32SapWindow:
    def __init__(self):
        if sys.platform != 'win32':
            raise RuntimeError('Nhúng SAP GUI yêu cầu Windows.')
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.rect_type = wintypes.RECT
        specs = {
            'IsWindow': ([wintypes.HWND], wintypes.BOOL),
            'GetParent': ([wintypes.HWND], wintypes.HWND),
            'SetParent': ([wintypes.HWND, wintypes.HWND], wintypes.HWND),
            'GetWindowRect': ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            'GetClientRect': ([wintypes.HWND, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
            'MoveWindow': ([wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL], wintypes.BOOL),
            'SetWindowPos': ([wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT], wintypes.BOOL),
            'ShowWindow': ([wintypes.HWND, ctypes.c_int], wintypes.BOOL),
        }
        for name, (args, result) in specs.items():
            function = getattr(self.user, name)
            function.argtypes, function.restype = args, result
        getter = 'GetWindowLongPtrW' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'GetWindowLongW'
        setter = 'SetWindowLongPtrW' if ctypes.sizeof(ctypes.c_void_p) == 8 else 'SetWindowLongW'
        self.get_long, self.set_long = getattr(self.user, getter), getattr(self.user, setter)
        self.get_long.argtypes = [wintypes.HWND, ctypes.c_int]
        self.get_long.restype = ctypes.c_ssize_t
        self.set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
        self.set_long.restype = ctypes.c_ssize_t

    def valid(self, handle):
        return bool(self.user.IsWindow(handle))

    def set_value(self, handle, index, value):
        self.ctypes.set_last_error(0)
        old = self.set_long(handle, index, value)
        if old == 0 and self.ctypes.get_last_error():
            raise self.ctypes.WinError(self.ctypes.get_last_error())

    def parent(self, handle, parent):
        self.ctypes.set_last_error(0)
        previous = self.user.SetParent(handle, parent)
        if not previous and self.ctypes.get_last_error():
            raise self.ctypes.WinError(self.ctypes.get_last_error())

    def capture(self, handle):
        if not self.valid(handle):
            raise RuntimeError('Cửa sổ SAP không còn tồn tại.')
        rectangle = self.rect_type()
        if not self.user.GetWindowRect(handle, self.ctypes.byref(rectangle)):
            raise self.ctypes.WinError()
        style = self.get_long(handle, -16) & 0xFFFFFFFF
        return dict(handle=handle, style=style,
            parent=self.user.GetParent(handle) if style & 0x40000000 else 0,
            owner=self.get_long(handle, -8), x=rectangle.left, y=rectangle.top,
            width=rectangle.right-rectangle.left, height=rectangle.bottom-rectangle.top)

    def embed(self, saved, host):
        handle = saved['handle']
        style = (saved['style'] | 0x40000000) & ~(0x80000000 | 0x00C00000 | 0x00040000 | 0x01000000 | 0x20000000)
        self.set_value(handle, -16, style)
        try:
            self.parent(handle, host)
            self.user.ShowWindow(handle, 9)
            self.resize(handle, host)
        except Exception:
            self.restore(saved)
            raise

    def resize(self, handle, host):
        if not self.valid(handle):
            return
        rectangle = self.rect_type()
        if self.user.GetClientRect(host, self.ctypes.byref(rectangle)):
            self.user.MoveWindow(handle, 0, 0, max(1, rectangle.right), max(1, rectangle.bottom), True)

    def restore(self, saved):
        handle = saved['handle']
        if not self.valid(handle):
            return
        self.parent(handle, saved['parent'])
        self.set_value(handle, -16, saved['style'])
        if not saved['style'] & 0x40000000:
            self.set_value(handle, -8, saved['owner'])
        self.user.SetWindowPos(handle, 0, saved['x'], saved['y'], saved['width'], saved['height'], 0x0034)
        self.user.ShowWindow(handle, 3 if saved['style'] & 0x01000000 else 9)


class SapHost(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.native = None
        self.saved = None
        self.last_handle = None
        self.setMinimumHeight(250)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        layout = QVBoxLayout(self)
        self.placeholder = QLabel('SAP GUI sẽ hiển thị tại đây sau khi mở PRD800.\n'
            'Bạn nhập tài khoản và mật khẩu trực tiếp trên SAP.')
        self.placeholder.setWordWrap(True)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder)

    def attach(self, handle):
        if self.saved and self.saved['handle'] == handle:
            self.resize_native()
            return
        self.detach()
        if self.native is None:
            self.native = Win32SapWindow()
        saved = self.native.capture(handle)
        self.saved = saved
        try:
            self.native.embed(saved, int(self.winId()))
        except Exception:
            # Retain the original window snapshot if restoring fails, so that
            # closing the app cannot silently destroy a still-parented SAP window.
            self.detach()
            raise
        self.last_handle = handle
        self.placeholder.hide()

    def reattach(self):
        if self.last_handle is None or self.native is None or not self.native.valid(self.last_handle):
            self.last_handle = None
            return False
        self.attach(self.last_handle)
        return True

    def detach(self):
        if self.saved is not None:
            self.native.restore(self.saved)
            self.saved = None
        self.placeholder.show()

    def resize_native(self):
        if self.saved:
            self.native.resize(self.saved['handle'], int(self.winId()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_native()


class JobModel(QAbstractTableModel):
    columns = [('Mã job', 'id'), ('Tiêu đề', 'name')]

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
            return value
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.columns[section][0]
        return None


class JobTable(QTableView):
    def showEvent(self, event):
        super().showEvent(event)
        # Measure after Qt has applied fonts, stylesheet and display scaling.
        header_height = self.horizontalHeader().sizeHint().height()
        row_height = self.verticalHeader().defaultSectionSize()
        self.setFixedHeight(header_height + 3 * row_height + 2 * self.frameWidth())


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
        self.pending_request = None
        self.closing = False
        self.rendering = False
        self.page_ready = False
        self.current_job = None
        self.sap_request = None
        self.sap_controller = SapController(self)
        self.current_index = 0
        self.sessions = {wid: {'jobs': None, 'state': 'active', 'query': '',
            'selected': None, 'expanded': True, 'updated': '',
            'batches': {}, 'loaded_state': None} for _, wid in WORKFLOWS}
        self.setWindowTitle('Boston Pharma — Đối chiếu PO / PR — Base & SAP')
        self.setStyleSheet(BRAND_STYLE)
        self.resize(1650, 1000)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        self.api_status = QLabel('API Base: chưa kiểm tra')
        self.api_status.setObjectName('connectionStatus')
        self.connection = QPushButton('Kết nối')
        self.connection.clicked.connect(self.open_connections)
        settings = QToolButton()
        settings.setText('Cài đặt')
        settings.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(settings)
        menu.addAction('Chọn logo Boston Pharma…', self.choose_brand_logo)
        menu.addAction('Cấu hình SAP GUI…', self.configure_sap)
        settings.setMenu(menu)
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
        row.addWidget(self.api_status)
        row.addWidget(self.connection)
        row.addWidget(settings)
        self.view_mode = QComboBox()
        self.view_mode.addItems(['Chia đôi', 'Mở rộng Base', 'Mở rộng SAP'])
        self.view_mode.currentIndexChanged.connect(self.change_layout)
        row.addWidget(self.view_mode)
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.setChildrenCollapsible(False)
        layout.addWidget(self.split, 1)
        self.left = QWidget()
        left = QVBoxLayout(self.left)
        left.setContentsMargins(0, 0, 0, 0)
        self.left.setMinimumWidth(380)
        self.split.addWidget(self.left)
        left.addWidget(QLabel('BASE — Nhiệm vụ của workflow đang chọn'))
        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setUsesScrollButtons(True)
        for name, _ in WORKFLOWS:
            self.tabs.addTab(name)
        tabs_row = QHBoxLayout()
        tabs_row.addWidget(self.tabs)
        tabs_row.addStretch()
        left.addLayout(tabs_row)
        row = QHBoxLayout()
        left.addLayout(row)
        self.states = QComboBox()
        self.states.setToolTip('Giữ nguyên giá trị state của Base API.')
        self.states.setMaximumWidth(190)
        row.addWidget(self.states)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Tìm job / PO / tiêu đề…')
        self.search.setMinimumWidth(90)
        self.search.setMaximumWidth(220)
        self.search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row.addWidget(self.search, 1)
        self.refresh = QPushButton('Làm mới danh sách')
        self.refresh.setObjectName('primary')
        row.addWidget(self.refresh)
        self.list_toggle = QToolButton()
        self.list_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.list_toggle.setCheckable(True)
        self.list_toggle.setChecked(True)
        self.list_toggle.setArrowType(Qt.ArrowType.DownArrow)
        row.addWidget(self.list_toggle)
        row.addStretch()
        self.model = JobModel(self)
        self.table = JobTable()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(35)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 90)
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
        self.page = BrowserPage(self.profile, self.browser)
        self.browser.setPage(self.page)
        self.middle = QWidget()
        self.middle.setFixedWidth(178)
        middle = QVBoxLayout(self.middle)
        self.sap_find = QPushButton('Tìm nhiệm vụ SAP →')
        self.sap_find.setObjectName('sapSearch')
        self.sap_find.setEnabled(False)
        self.sap_find.setToolTip('Mở ME29N và PO từ job Base. Không tự Release hoặc Save.')
        middle.addStretch()
        middle.addWidget(self.sap_find)
        middle.addStretch()
        self.split.addWidget(self.middle)
        self.right = QWidget()
        self.right.setMinimumWidth(300)
        right = QVBoxLayout(self.right)
        self.split.addWidget(self.right)
        right.addWidget(QLabel('SAP — Nhiệm vụ tương ứng'))
        sap_buttons = QHBoxLayout()
        right.addLayout(sap_buttons)
        self.sap_open = QPushButton('Mở SAP PRD800')
        self.sap_open.clicked.connect(self.sap_controller.connect_sap)
        sap_buttons.addWidget(self.sap_open)
        self.sap_detach = QPushButton('Tách cửa sổ SAP')
        self.sap_detach.clicked.connect(self.detach_sap)
        sap_buttons.addWidget(self.sap_detach)
        self.sap_reattach = QPushButton('Gắn lại SAP')
        self.sap_reattach.clicked.connect(self.reattach_sap)
        sap_buttons.addWidget(self.sap_reattach)
        self.sap_cancel = QPushButton('Hủy tìm PO')
        self.sap_cancel.clicked.connect(self.sap_controller.cancel_navigation)
        sap_buttons.addWidget(self.sap_cancel)
        self.sap_connection_label = QLabel('SAP chưa kết nối. Dùng profile PRD800 đã có trong SAP Logon.')
        self.sap_connection_label.setWordWrap(True)
        self.sap_connection_label.setTextFormat(Qt.TextFormat.PlainText)
        right.addWidget(self.sap_connection_label)
        self.sap_po = QLineEdit()
        self.sap_po.setReadOnly(True)
        self.sap_po.setPlaceholderText('PO nhận từ nhiệm vụ Base')
        right.addWidget(QLabel('PO yêu cầu từ Base (chưa phải xác nhận kết quả SAP):'))
        right.addWidget(self.sap_po)
        self.sap_actual = QLabel('Chưa đọc được PO đang hiển thị trên SAP.')
        self.sap_actual.setWordWrap(True)
        self.sap_actual.setTextFormat(Qt.TextFormat.PlainText)
        right.addWidget(self.sap_actual)
        self.sap_controller.document_changed.connect(self.sap_actual.setText)
        self.sap_info = QLabel()
        self.sap_info.setWordWrap(True)
        self.sap_info.setTextFormat(Qt.TextFormat.PlainText)
        right.addWidget(self.sap_info)
        self.sap_host = SapHost()
        right.addWidget(self.sap_host, 1)
        self.sap_controller.status_changed.connect(self.sap_connection_label.setText)
        self.sap_controller.window_ready.connect(self.attach_sap)
        self.sap_controller.navigation_changed.connect(self.sync_sap_button)
        self.sap_controller.navigation_changed.connect(self.update_sap_buttons)
        self.sap_controller.navigation_finished.connect(self.sap_navigation_finished)
        self.update_sap_buttons()
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
                    self.setWindowIcon(QIcon(pixmap))
                    return True
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
                    session.update(jobs=None, selected=None, updated='', batches={}, loaded_state=None)
                self.api_status.setText('API Base: chưa kiểm tra token mới')
                self.restore_tab()
            self.load_jobs()
        dialog.deleteLater()

    def change_tab(self, index):
        self.current_index = index
        self.pending_request = None
        self.restore_tab()
        self.update_load_controls()
        if self.api_token and self.session()['jobs'] is None:
            self.load_jobs()

    def workflow_label(self, workflow_id):
        return next(name for name, wid in WORKFLOWS if wid == workflow_id)

    def current_request(self):
        return (WORKFLOWS[self.current_index][1], self.session()['state'])

    def update_load_controls(self):
        target = self.current_request()
        busy_here = self.worker is not None and (
            (self.worker.workflow_id, self.worker.request_state) == target
            or self.pending_request == target)
        self.refresh.setEnabled(not busy_here)
        self.refresh.setText('Đang tải…' if busy_here else 'Làm mới danh sách')
        self.connection.setEnabled(self.worker is None)

    def activate_cached_state(self, session):
        requested = session['state']
        cached_state = requested if requested in session['batches'] else '*'
        cached = session['batches'].get(cached_state)
        session['jobs'] = cached['jobs'] if cached is not None else None
        session['updated'] = cached['updated'] if cached is not None else ''
        session['loaded_state'] = cached_state if cached is not None else None

    def restore_tab(self):
        session = self.session()
        self.activate_cached_state(session)
        self.states.blockSignals(True)
        self.states.clear()
        self.states.addItem('Tất cả trạng thái', '*')
        states = set(STATE_LABELS) | {j['state']
            for batch in session['batches'].values() for j in batch['jobs']}
        if session['state'] != '*':
            states.add(session['state'])
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
        session = self.session()
        changed = session['state'] != self.states.currentData()
        session['state'] = self.states.currentData()
        session['query'] = self.search.text()
        if changed:
            self.pending_request = None
            self.activate_cached_state(session)
        self.render_rows()
        self.update_load_controls()
        if changed and self.api_token and session['jobs'] is None:
            self.load_jobs()

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
        scope = ''
        if session['loaded_state'] is not None:
            scope = ' · API: ' + ('Tất cả' if session['loaded_state'] == '*' else state_label(session['loaded_state']))
        self.count.setText(f'{len(rows)} nhiệm vụ hiển thị / {len(jobs)} nhiệm vụ đã lấy' + scope + suffix)
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
        workflow_id, requested_state = self.current_request()
        # Keep ownership until the finished signal is processed, even if the
        # native thread has already stopped. This prevents late-signal races.
        if self.worker is not None:
            if ((self.worker.workflow_id, self.worker.request_state) != (workflow_id, requested_state)
                    or self.worker.isInterruptionRequested()):
                self.pending_request = (workflow_id, requested_state)
                self.worker.requestInterruption()
                self.info.setText('Đang chuyển sang ' + self.workflow_name()
                    + '. Chờ yêu cầu API hiện tại kết thúc…')
            self.update_load_controls()
            return
        if not self.api_token:
            self.open_connections()
            return
        self.api_status.setText('API Base: đang đọc ' + self.workflow_name() + ' / ' + str(requested_state))
        worker = Loader(self.api_token, workflow_id, self, state=requested_state)
        self.worker = worker
        worker.progress.connect(lambda message, wid=workflow_id, state=requested_state: self.load_progress(wid, message, state))
        worker.loaded.connect(lambda jobs, wid=workflow_id, state=requested_state: self.received(jobs, wid, state))
        worker.failed.connect(lambda message, wid=workflow_id, state=requested_state: self.load_failed(message, wid, state))
        worker.finished.connect(lambda current=worker: self.load_finished(current))
        self.update_load_controls()
        worker.start()

    def load_progress(self, workflow_id, message, state=None):
        if state is None:
            state = self.session()['state']
        if (self.worker is not None and not self.worker.isInterruptionRequested()
                and (workflow_id, state) == self.current_request()):
            self.info.setText(message)

    def received(self, jobs, workflow_id=None, state='*'):
        if workflow_id is None:
            workflow_id = WORKFLOWS[self.current_index][1]
        session = self.sessions[workflow_id]
        updated = datetime.now(timezone(timedelta(hours=7))).strftime('%d/%m/%Y %H:%M:%S')
        if state == '*':
            # A fresh full snapshot supersedes older per-state snapshots.
            session['batches'].clear()
        session['batches'][state] = {'jobs': jobs, 'updated': updated}
        self.activate_cached_state(session)
        self.api_status.setText('API Base: đã đọc ' + self.workflow_label(workflow_id) + ' / ' + state)
        if (workflow_id, state) == self.current_request() or (
                workflow_id == self.current_request()[0] and state == '*' and session['loaded_state'] == '*'):
            self.restore_tab()
            self.info.setText('Danh sách đã cập nhật theo trạng thái. Thao tác trong trang Base là thao tác thật.')

    def load_failed(self, message, workflow_id=None, state=None):
        if workflow_id is None:
            workflow_id = WORKFLOWS[self.current_index][1]
        if state is None:
            state = self.session()['state']
        self.api_status.setText('API Base: lỗi đọc ' + self.workflow_label(workflow_id))
        if (workflow_id, state) == self.current_request():
            self.info.setText(message + (' Đang giữ dữ liệu cũ.' if self.session()['jobs'] is not None else ''))

    def load_finished(self, worker):
        if self.worker is not worker:
            return
        was_cancelled = worker.isInterruptionRequested()
        self.worker = None
        pending = self.pending_request
        self.pending_request = None
        worker.deleteLater()
        self.update_load_controls()
        if self.closing:
            self.close()
        elif pending == self.current_request():
            self.load_jobs()
        elif was_cancelled:
            self.api_status.setText('API Base: đã dừng đọc ' + self.workflow_label(worker.workflow_id))

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
        enabled = bool(not self.sap_controller.navigation_active and self.page_ready and self.current_job and parsed.hostname == 'workflow.base.vn'
                       and match and match.group(1) == self.current_job['id'])
        self.sap_find.setEnabled(enabled)

    def configure_sap(self):
        if self.sap_controller.mode not in ('disconnected',) or self.sap_controller.navigation_active:
            QMessageBox.information(self, 'SAP GUI', 'Kết nối SAP đang hoạt động. Đóng và mở lại app để đổi môi trường.')
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('Cấu hình SAP GUI')
        dialog.resize(650, 190)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel('Đường dẫn SAP Logon:'))
        path = QLineEdit(self.sap_controller.path)
        layout.addWidget(path)
        layout.addWidget(QLabel('Tên kết nối đã cấu hình trong SAP Logon (không nhập router/password):'))
        entry = QLineEdit(self.sap_controller.entry)
        layout.addWidget(entry)
        save = QPushButton('Áp dụng')
        save.clicked.connect(dialog.accept)
        layout.addWidget(save)
        if dialog.exec() == QDialog.DialogCode.Accepted and path.text().strip() and entry.text().strip():
            self.sap_controller.path = path.text().strip()
            self.sap_controller.entry = entry.text().strip()
            self.sap_open.setText('Mở SAP ' + self.sap_controller.entry)
        dialog.deleteLater()

    def attach_sap(self, handle):
        try:
            self.sap_host.attach(handle)
        except Exception:
            self.sap_connection_label.setText('SAP đã mở nhưng chưa nhúng được cửa sổ. '
                'Có thể dùng SAP bên ngoài và thử Gắn lại SAP; kiểm tra quyền chạy và DPI của hai ứng dụng.')

    def detach_sap(self):
        try:
            self.sap_host.detach()
        except Exception:
            self.sap_connection_label.setText('Chưa tách được cửa sổ SAP. Giữ app mở và thử lại.')

    def reattach_sap(self):
        # Reattach the exact window we previously owned, even if COM lost the
        # session after a navigation error. Never open a new SAP connection here.
        try:
            if self.sap_host.reattach():
                self.sap_connection_label.setText('Đã gắn lại cửa sổ SAP. Kết nối điều khiển và PO cần được kiểm tra riêng.')
                return
        except Exception:
            self.sap_connection_label.setText('Chưa gắn được cửa sổ SAP. Kiểm tra SAP và app chạy cùng mức quyền; giữ SAP mở.')
            return
        try:
            if self.sap_controller.show_window():
                return
        except Exception:
            pass
        self.sap_connection_label.setText('Chưa có cửa sổ SAP hợp lệ để gắn lại. '
            'Nếu đã đóng SAP, bấm Mở SAP PRD800 để kết nối lại.')

    def update_sap_buttons(self):
        self.sap_cancel.setEnabled(self.sap_controller.navigation_active)

    def reset_sap(self):
        self.sap_request = None
        self.sap_controller.cancel_navigation()
        self.sap_po.clear()
        self.sap_info.setText('Chọn job Base rồi bấm Tìm nhiệm vụ SAP. '
            'Chứng từ cũ trên SAP không tự thay đổi khi chuyển job Base.')

    def sap_navigation_finished(self, request_id, po, result, message):
        request = self.sap_request
        if request is None or request['id'] != request_id:
            return
        self.sap_request = None
        if not self.current_job or self.current_job['id'] != request['job']:
            return
        self.sap_info.setText(f"PO {po} — {request['workflow']}, job {request['job']}.\n" + message)

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
        self.sap_info.setText(f'Đang mở ME29N cho PO {po}.\n'
            f'Nguồn: {self.workflow_name()}, job {source_id}.\n'
            'Nếu SAP chưa đăng nhập, nhập tài khoản trực tiếp trên SAP.')
        request_id = self.sap_controller.request_po(po)
        self.sap_request = {'id': request_id, 'job': source_id, 'workflow': self.workflow_name()}

    def closeEvent(self, event):
        if self.worker is not None:
            self.closing = True
            self.worker.requestInterruption()
            self.info.setText('Đang dừng yêu cầu API trước khi đóng…')
            event.ignore()
        else:
            try:
                self.sap_host.detach()
            except Exception:
                self.sap_connection_label.setText('Không tách được SAP. Hãy giữ app mở và thử Tách cửa sổ SAP trước khi đóng.')
                event.ignore()
                return
            self.sap_controller.shutdown()
            self.api_token = ''
            event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont('Segoe UI', 9))
    window = Window()
    window.show()
    sys.exit(app.exec())

# HẾT FILE — không cần các file Python cũ.
