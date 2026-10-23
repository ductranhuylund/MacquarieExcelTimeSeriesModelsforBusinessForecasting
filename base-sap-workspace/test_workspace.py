import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from PySide6.QtCore import QObject, QUrl, Signal, Qt, QPoint
from PySide6.QtWidgets import QApplication, QWidget
import base_sap_workspace as appmod


class FakeProfile(QObject):
    PersistentCookiesPolicy = SimpleNamespace(AllowPersistentCookies=1)
    def __init__(self, name, parent): super().__init__(parent)
    def setPersistentStoragePath(self, value): pass
    def setCachePath(self, value): pass
    def setPersistentCookiesPolicy(self, value): pass


class FakePage(QObject):
    def __init__(self, profile, parent):
        super().__init__(parent)
        self.scripts = []
        self.title = 'Vật tư kiểm thử - 4500000001'
    def runJavaScript(self, script, callback=None):
        self.scripts.append(script)
        if callback: callback(self.title)


class FakeBrowser(QWidget):
    loadStarted = Signal()
    loadFinished = Signal(bool)
    urlChanged = Signal(QUrl)
    def __init__(self):
        super().__init__()
        self.current_url = QUrl()
        self.loads = []
    def setPage(self, page): self.webpage = page
    def page(self): return self.webpage
    def url(self): return self.current_url
    def setUrl(self, url):
        self.loadStarted.emit()
        self.loads.append(url.toString())
        self.current_url = url
        self.urlChanged.emit(url)
        self.loadFinished.emit(True)
    def reload(self): self.setUrl(self.current_url)


def job(i, state='active', name=None):
    return dict(id=str(i), name=name or f'PO 450000000{i}', state=state,
                status='0', stage='Duyệt PO')


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.qt = QApplication.instance() or QApplication([])
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name})
        self.env.start()
        self.patches = [patch.object(appmod, 'QWebEngineProfile', FakeProfile),
                        patch.object(appmod, 'QWebEnginePage', FakePage),
                        patch.object(appmod, 'QWebEngineView', FakeBrowser)]
        for p in self.patches: p.start()
        self.window = appmod.Window()
        self.window.show()
        self.qt.processEvents()
    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.qt.processEvents()
        for p in reversed(self.patches): p.stop()
        self.env.stop()
        self.temp.cleanup()
    def populate(self, wid=3991, rows=None):
        self.window.sessions[wid]['jobs'] = rows if rows is not None else [job(3), job(2), job(1,'done')]
        self.window.restore_tab()
        self.qt.processEvents()

    def test_pr_disabled_workflow_names_and_default(self):
        w = self.window
        self.assertFalse(w.business.isTabEnabled(1))
        self.assertEqual(w.tabs.count(), 3)
        self.assertIn('Nguyên liệu', w.tabs.tabText(0))
        self.assertEqual(w.states.currentData(), 'active')
        self.assertFalse(w.sap_find.isEnabled())
        self.assertEqual(w.model.rowCount(),0)

    def test_selection_and_navigation(self):
        self.populate()
        w = self.window
        self.assertEqual(w.model.rowCount(),2)
        self.assertEqual(w.current_job['id'],'3')
        self.assertFalse(w.previous.isEnabled())
        w.move(1)
        self.assertEqual(w.current_job['id'],'2')
        self.assertTrue(w.previous.isEnabled())
        self.assertFalse(w.next.isEnabled())
        w.move(-1)
        self.assertEqual(w.current_job['id'],'3')
        self.assertIn('2 nhiệm vụ hiển thị / 3 nhiệm vụ đã lấy',w.count.text())

    def test_each_tab_remembers_state_query_selection_and_collapse(self):
        self.populate()
        w = self.window
        w.states.setCurrentIndex(w.states.findData('*'))
        w.search.setText('PO')
        w.move(2)
        w.list_toggle.setChecked(False)
        self.assertEqual(w.current_job['id'],'1')
        w.tabs.setCurrentIndex(1)
        self.assertIsNone(w.current_job)
        self.assertEqual(w.model.rowCount(),0)
        self.populate(4156,[job(9,'failed')])
        w.states.setCurrentIndex(w.states.findData('failed'))
        w.tabs.setCurrentIndex(0)
        self.assertEqual(w.states.currentData(),'*')
        self.assertEqual(w.search.text(),'PO')
        self.assertEqual(w.current_job['id'],'1')
        self.assertFalse(w.list_toggle.isChecked())
        self.assertTrue(w.table.isHidden())
        w.tabs.setCurrentIndex(1)
        self.assertEqual(w.states.currentData(),'failed')
        self.assertEqual(w.current_job['id'],'9')

    def test_unknown_state_preserved(self):
        self.populate(rows=[job(1,'paused_by_base')])
        w=self.window
        i=w.states.findData('paused_by_base')
        self.assertGreaterEqual(i,0)
        self.assertEqual(w.states.itemText(i),'paused_by_base')
        w.states.setCurrentIndex(i)
        self.assertEqual(w.model.rowCount(),1)
        self.assertEqual(w.current_job['state'],'paused_by_base')
        self.assertEqual(w.model.columnCount(),2)

    def test_sap_request_no_false_search_and_cleared_on_navigation(self):
        self.populate()
        w=self.window
        self.assertTrue(w.sap_find.isEnabled())
        w.find_sap()
        self.assertEqual(w.sap_po.text(),'4500000001')
        self.assertIn('chưa thực hiện tìm kiếm',w.sap_info.text())
        self.assertIn('job 3',w.sap_info.text())
        w.move(1)
        self.assertEqual(w.sap_po.text(),'')
        self.assertTrue(w.sap_find.isEnabled())

    def test_sap_disabled_on_external_navigation_login_and_failed_load(self):
        self.populate()
        w=self.window
        w.browser.setUrl(QUrl('https://workflow.base.vn/job/9999'))
        self.assertFalse(w.sap_find.isEnabled())
        w.browser.setUrl(QUrl('https://workflow.base.vn/'))
        self.assertFalse(w.sap_find.isEnabled())
        w.browser.setUrl(QUrl('https://workflow.base.vn/job/3'))
        self.assertTrue(w.sap_find.isEnabled())
        w.page_loaded(False)
        self.assertFalse(w.sap_find.isEnabled())

    def test_multi_po_selection(self):
        self.populate()
        w=self.window
        with patch.object(appmod.QInputDialog,'getItem',return_value=('4500000002',True)) as choose:
            w.prepare_sap('3','4500000001 / 4500000002')
        choose.assert_called_once()
        self.assertEqual(w.sap_po.text(),'4500000002')

    def test_missing_po_manual_invalid_rejected(self):
        self.populate()
        w=self.window
        with patch.object(appmod.QInputDialog,'getText',return_value=('bad',True)):
            w.prepare_sap('3','No PO')
        self.assertEqual(w.sap_po.text(),'')
        self.assertIn('10 chữ số',w.sap_info.text())

    def test_stale_async_title_callback_ignored(self):
        self.populate()
        w=self.window
        w.move(1)
        w.prepare_sap('3','4500000001')
        self.assertEqual(w.sap_po.text(),'')

    def test_search_does_not_reload_same_job(self):
        self.populate()
        w=self.window
        before=len(w.browser.loads)
        w.search.setText('PO')
        self.assertEqual(len(w.browser.loads),before)
        w.search.setText('not found')
        self.assertEqual(w.model.rowCount(),0)
        self.assertIsNone(w.current_job)
        self.assertFalse(w.sap_find.isEnabled())

    def test_layout_modes(self):
        w=self.window
        w.view_mode.setCurrentIndex(1)
        self.assertFalse(w.left.isHidden())
        self.assertTrue(w.right.isHidden())
        w.view_mode.setCurrentIndex(2)
        self.assertTrue(w.left.isHidden())
        self.assertFalse(w.right.isHidden())
        w.view_mode.setCurrentIndex(0)
        self.assertFalse(w.left.isHidden())
        self.assertFalse(w.right.isHidden())
        self.assertFalse(w.middle.isHidden())

    def test_full_original_page_switch(self):
        self.populate()
        w=self.window
        w.full_page.setChecked(True)
        self.assertTrue(any('baseViewerFullPage=true' in s for s in w.page.scripts))
        w.full_page.setChecked(False)
        self.assertIn('baseViewerFullPage=false',w.page.scripts[-1])

    def test_empty_data_and_stale_failure(self):
        self.populate(rows=[])
        w=self.window
        self.assertFalse(w.next.isEnabled())
        self.assertIsNone(w.current_job)
        w.load_failed('error')
        self.assertIn('Đang giữ dữ liệu cũ',w.info.text())

    def test_token_not_visible_on_main_screen(self):
        w=self.window
        self.assertCountEqual(w.findChildren(appmod.QLineEdit),[w.search,w.sap_po])
        dialog=appmod.ConnectionDialog(False,w)
        self.assertEqual(dialog.token.echoMode(),appmod.QLineEdit.EchoMode.Password)
        dialog.deleteLater()

    def test_worker_refresh_preserves_selection_and_filters(self):
        self.populate()
        w=self.window
        w.search.setText('PO')
        w.move(1)
        w.api_token='placeholder'
        with patch.object(appmod,'fetch_jobs',return_value=[job(3),job(2),job(1,'done')]):
            w.load_jobs()
            self.assertFalse(w.tabs.isEnabled())
            self.assertFalse(w.connection.isEnabled())
            self.assertTrue(w.worker.wait(3000))
            self.qt.processEvents()
        self.assertTrue(w.tabs.isEnabled())
        self.assertEqual(w.current_job['id'],'2')
        self.assertEqual(w.search.text(),'PO')
        self.assertEqual(w.states.currentData(),'active')
        self.assertTrue(w.session()['updated'])

    def test_replacing_token_clears_all_workflow_data(self):
        self.populate()
        w=self.window
        w.api_token='old-placeholder'
        w.sessions[4156]['jobs']=[job(9)]
        real_dialog=appmod.ConnectionDialog
        def dialog_factory(has_token,parent):
            dialog=real_dialog(has_token,parent)
            dialog.token.setText('new-placeholder')
            dialog.exec=lambda:appmod.QDialog.DialogCode.Accepted
            return dialog
        with patch.object(appmod,'ConnectionDialog',side_effect=dialog_factory), patch.object(w,'load_jobs') as load:
            w.open_connections()
            load.assert_called_once()
        self.assertEqual(w.api_token,'new-placeholder')
        self.assertTrue(all(s['jobs'] is None for s in w.sessions.values()))
        self.assertIsNone(w.current_job)

    def test_workflow_tabs_belong_to_base_and_align_left(self):
        w=self.window
        self.assertTrue(w.left.isAncestorOf(w.tabs))
        self.assertFalse(w.right.isAncestorOf(w.tabs))
        self.assertFalse(w.tabs.expanding())
        self.assertEqual(w.tabs.mapTo(w.left,QPoint(0,0)).x(),0)
        self.assertLess(w.tabs.width(),w.left.width())

    def test_list_toggle_and_refresh_share_compact_filter_row(self):
        w=self.window
        self.populate()
        centres=[widget.mapTo(w.left,widget.rect().center()).y()
                 for widget in (w.states,w.search,w.refresh,w.list_toggle)]
        self.assertLessEqual(max(centres)-min(centres),1)
        self.assertLessEqual(w.search.width(),220)
        self.assertFalse(hasattr(w,'brand_logo'))
        self.assertIsNone(w.findChild(appmod.QLabel,'brandTitle'))

    def test_three_visible_job_rows_without_discarding_remaining_jobs(self):
        self.populate(rows=[job(i) for i in range(8,0,-1)])
        w=self.window
        self.assertEqual(w.model.columnCount(),2)
        self.assertEqual([x[0] for x in w.model.columns],['Mã job','Tiêu đề'])
        self.assertEqual(w.model.rowCount(),8)
        height=w.table.viewport().height()
        row_height=w.table.verticalHeader().defaultSectionSize()
        self.assertGreaterEqual(height,3*row_height)
        self.assertLess(height,4*row_height)
        self.assertEqual(w.table.rowAt(height-1),2)
        w.move(4)
        self.qt.processEvents()
        self.assertEqual(w.current_job['id'],'4')
        self.assertGreater(w.table.verticalScrollBar().value(),0)
        self.assertLessEqual(w.table.visualRect(w.model.index(4,0)).bottom(),height)

    def test_table_handles_thousands(self):
        rows=[job(i,'active') for i in range(6000,0,-1)]
        self.populate(rows=rows)
        self.assertEqual(self.window.model.rowCount(),6000)
        self.assertEqual(self.window.model.data(self.window.model.index(5999,0)),'1')


class ApiTests(unittest.TestCase):
    def run_fetch(self,wid=3991,duplicate=False,wrong=False,drift=False):
        calls=[]
        records=[dict(id=i,workflow_id=999 if wrong else wid,name=f'PO {i}',state=state)
                 for i,state in enumerate(['active','done','failed','custom'],1)]
        class Session:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def post(self,url,data,**kwargs):
                calls.append(data.copy());p=data['page_id']
                obj=dict(code=1,page=p,total_items=5 if drift and p else 4,items_per_page=2,
                         jobs=records[:2] if duplicate else records[p*2:p*2+2])
                return SimpleNamespace(raise_for_status=lambda:None,json=lambda:obj)
        with patch.object(appmod.requests,'Session',Session):
            rows=appmod.fetch_jobs('placeholder',wid,lambda:False,lambda _:None)
        return rows,calls

    def test_pagination_scope_and_no_dates(self):
        for wid in (3991,4156,4157):
            rows,calls=self.run_fetch(wid)
            self.assertEqual([j['id'] for j in rows],['4','3','2','1'])
            self.assertEqual([x['workflow_id'] for x in calls],[wid,wid])
            self.assertEqual(set(calls[0]),{'access_token_v2','workflow_id','page_id','limit'})
            self.assertEqual({j['state'] for j in rows},{'active','done','failed','custom'})

    def test_reject_wrong_scope_duplicates_and_drift(self):
        for kw in ({'wrong':True},{'duplicate':True},{'drift':True}):
            with self.assertRaises(RuntimeError):self.run_fetch(**kw)

    def test_po_recognition(self):
        self.assertEqual(appmod.po_candidates('PO 4500000003 | PR 1000000001'),['4500000003'])
        self.assertEqual(appmod.po_candidates('Đường trắng - 4500000001'),['4500000001'])
        self.assertEqual(appmod.po_candidates('4500000001 / 4500000002'),['4500000001','4500000002'])
        self.assertEqual(appmod.po_candidates('PR 1000000001'),[])
        self.assertEqual(appmod.po_candidates('145000000010'),[])


if __name__=='__main__':unittest.main(verbosity=2)
