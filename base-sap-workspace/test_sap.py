"""SAP navigation tests with simulated COM controls; no SAP connection."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from types import SimpleNamespace as NS
from PySide6.QtWidgets import QApplication
import base_sap_workspace as m

class Collection:
    def __init__(self, values): self.values = values
    @property
    def Count(self): return len(self.values)
    def __call__(self, i): return self.values[i]

class Session:
    def __init__(self):
        self.Busy = False
        self.Info = NS(Transaction='SESSION_MANAGER', User='TEST', SystemName='TEST', Client='800')
        self.header = NS(Text='4100000000')
        self.main = NS(Type='GuiMainWindow', Id='wnd[0]', Text='ME29N', Handle='123',
                       FindByName=lambda name, kind: self.header)
        self.controls = {'wnd[0]': self.main, 'wnd[0]/sbar': NS(MessageType='', Text='')}
        self.children = [self.main]
        self.Children = Collection(self.children)
        self.actions = []
        self.field = NS(Text='', Changeable=True)
        self.button = NS(Type='GuiButton', Text='', Tooltip='Other Purchase Order', Press=self.open_dialog)
        self.controls['wnd[0]/tbar[1]'] = NS(Children=Collection([self.button]))
    def FindById(self, key, required=False): return self.controls.get(key)
    def StartTransaction(self, code):
        self.actions.append(('transaction', code)); self.Info.Transaction = code
    def open_dialog(self):
        self.actions.append(('open',))
        modal = NS(Type='GuiModalWindow', Id='wnd[1]', SendVKey=self.submit)
        self.children.append(modal)
        self.controls.update({'wnd[1]': modal, 'wnd[1]/usr/ctxtMEPO_SELECT-EBELN': self.field,
                              'wnd[1]/usr': NS(Children=Collection([]))})
    def submit(self, key):
        self.actions.append(('enter', key, self.field.Text))
        self.header.Text = self.field.Text
        self.children.pop()
        for key in list(self.controls):
            if key.startswith('wnd[1]'): del self.controls[key]

class SapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])
    def run_navigation(self, session, navigator=None):
        navigator = navigator or m.SapNavigator('4100000001')
        for _ in range(12):
            result = navigator.step(session)
            if result: return result
        self.fail('Navigation did not finish')
    def test_open_me29n_select_po_and_verify(self):
        s = Session()
        self.assertEqual(self.run_navigation(s)[0], 'verified')
        self.assertEqual(s.actions, [('transaction', 'ME29N'), ('open',), ('enter', 0, '4100000001')])
    def test_matching_po_needs_no_document_action(self):
        s = Session(); s.Info.Transaction = 'ME29N'; s.header.Text = '4100000001'
        self.assertEqual(self.run_navigation(s)[0], 'verified'); self.assertEqual(s.actions, [])
    def test_unknown_modal_is_not_acknowledged(self):
        s = Session(); s.children.append(NS(Type='GuiModalWindow', Id='wnd[2]'))
        with self.assertRaises(m.SapNavigationError): self.run_navigation(s)
        self.assertEqual(s.actions, [])
    def test_release_button_cannot_be_used_as_document_button(self):
        s = Session(); s.Info.Transaction = 'ME29N'; s.button.Tooltip = 'Release Other Document'
        with self.assertRaises(m.SapNavigationError): self.run_navigation(s)
        self.assertEqual(s.actions, [])
    def test_disabled_po_field_not_submitted(self):
        s = Session(); s.field.Changeable = False
        with self.assertRaises(m.SapNavigationError): self.run_navigation(s)
        self.assertFalse(any(a[0] == 'enter' for a in s.actions))
    def test_existing_selection_dialog_supported(self):
        s = Session(); s.Info.Transaction = 'ME29N'; s.open_dialog(); s.actions.clear()
        self.assertEqual(self.run_navigation(s)[0], 'verified')
        self.assertEqual(s.actions, [('enter', 0, '4100000001')])
    def test_busy_timeout(self):
        now = [0]; n = m.SapNavigator('4100000001', clock=lambda: now[0])
        s = Session(); s.Busy = True; now[0] = 26
        with self.assertRaises(m.SapNavigationError): n.step(s)
    def test_wrong_po_is_not_reported_successful(self):
        s = Session(); n = m.SapNavigator('4100000001', clock=lambda: 100)
        n.phase = 'verify'; n.deadline = 99; s.Info.Transaction = 'ME29N'
        with self.assertRaises(m.SapNavigationError): n.step(s)
    def test_server_disabled_scripting(self):
        c = m.SapController(); c.mode = 'connection'; c.deadline = 1e20
        c.connection = NS(DisabledByServer=True)
        messages = []; c.status_changed.connect(messages.append); c.poll()
        self.assertEqual(c.mode, 'disconnected'); self.assertTrue(any('server' in v for v in messages))
        c.shutdown()
    def test_login_does_not_navigate_until_user_logged_in(self):
        s = Session(); s.Info.User = ''
        c = m.SapController(); c.session = s; c.mode = 'login'; c.pending = (1, '4100000001')
        c.poll(); self.assertEqual(s.actions, []); self.assertIsNone(c.navigator)
        s.Info.User = 'TEST'; c.poll()
        self.assertEqual(s.actions, [('transaction', 'ME29N')]); c.shutdown()
    def test_host_restores_external_window(self):
        events = []
        host = m.SapHost()
        host.native = NS(capture=lambda h: {'handle': h},
            embed=lambda saved, parent: events.append('embed'),
            restore=lambda saved: events.append('restore'), resize=lambda *args: None)
        host.attach(123); host.detach()
        self.assertEqual(events, ['embed', 'restore']); self.assertIsNone(host.saved)
        host.close()
    def test_failed_restore_keeps_snapshot(self):
        host = m.SapHost(); host.saved = {'handle': 123}
        def fail(saved): raise RuntimeError('unavailable')
        host.native = NS(restore=fail)
        with self.assertRaises(RuntimeError): host.detach()
        self.assertEqual(host.saved['handle'], 123)
        host.saved = None; host.close()

if __name__ == '__main__': unittest.main(verbosity=2)
