import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import io
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




class FakeSapController(QObject):
    document_changed = Signal(str)
    status_changed=Signal(str)
    window_ready=Signal(object)
    navigation_changed=Signal()
    navigation_finished=Signal(int,str,str,str)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.pending=None
        self.requests=[]
        self.sequence=0
        self.mode='disconnected'
        self.path=appmod.SAP_LOGON_PATH
        self.entry=appmod.SAP_CONNECTION
    @property
    def navigation_active(self):return self.pending is not None
    def request_po(self,po):
        self.sequence+=1
        self.pending=(self.sequence,po)
        self.requests.append(self.pending)
        self.navigation_changed.emit()
        return self.sequence
    def cancel_navigation(self):
        if self.pending:
            rid,po=self.pending;self.pending=None
            self.navigation_changed.emit()
            self.navigation_finished.emit(rid,po,'cancelled','Đã hủy')
    def finish(self,result='verified',message='Đã mở đúng PO'):
        if self.pending:
            rid,po=self.pending;self.pending=None
            self.navigation_changed.emit()
            self.navigation_finished.emit(rid,po,result,message)
    def connect_sap(self):self.status_changed.emit('SAP thử nghiệm')
    def show_window(self):pass
    def shutdown(self):self.pending=None


class ControlledLoader(QObject):
    loaded=Signal(list)
    failed=Signal(str)
    progress=Signal(str)
    finished=Signal()
    created=[]
    def __init__(self,token,workflow_id,parent,state='*'):
        super().__init__(parent)
        self.workflow_id=workflow_id
        self.request_state=state
        self.running=False
        self.cancelled=False
        self.created.append(self)
    def start(self):self.running=True
    def isRunning(self):return self.running
    def isInterruptionRequested(self):return self.cancelled
    def requestInterruption(self):self.cancelled=True
    def finish(self,rows=None,error=None):
        self.running=False
        if not self.cancelled:
            if error:self.failed.emit(error)
            elif rows is not None:self.loaded.emit(rows)
        self.finished.emit()


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
                        patch.object(appmod, 'BrowserPage', FakePage),
                        patch.object(appmod, 'SapController', FakeSapController),
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
        values = rows if rows is not None else [job(3), job(2), job(1,'done')]
        self.window.sessions[wid]['batches']['*'] = {'jobs':values,'updated':''}
        self.window.sessions[wid]['jobs'] = values
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

    def test_sap_po_request_has_base_source_and_cancels_on_navigation(self):
        self.populate()
        w=self.window
        self.assertTrue(w.sap_find.isEnabled())
        w.find_sap()
        self.assertEqual(w.sap_po.text(),'4500000001')
        self.assertIn('Đang mở ME29N',w.sap_info.text())
        self.assertEqual(w.sap_controller.requests,[(1,'4500000001')])
        self.assertFalse(w.sap_find.isEnabled())
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
            self.assertTrue(w.tabs.isEnabled())
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

    def test_tabs_remain_clickable_and_load_f012_f013_on_first_selection(self):
        w=self.window
        w.api_token='placeholder'
        ControlledLoader.created=[]
        with patch.object(appmod,'Loader',ControlledLoader):
            w.load_jobs()
            first=w.worker
            self.assertTrue(w.tabs.isEnabled())
            w.tabs.setCurrentIndex(1)
            self.assertEqual(w.current_index,1)
            self.assertTrue(first.cancelled)
            self.assertEqual(w.pending_request,(4156,'active'))
            first.finish()
            self.assertEqual(w.worker.workflow_id,4156)
            w.worker.finish([job(9)])
            self.assertEqual(w.current_job['id'],'9')
            self.assertIsNone(w.worker)
            w.tabs.setCurrentIndex(2)
            self.assertEqual(w.worker.workflow_id,4157)
            w.worker.finish([job(8)])
            self.assertEqual(w.current_job['id'],'8')
            w.tabs.setCurrentIndex(1)
            self.assertIsNone(w.worker)
            self.assertEqual(w.current_job['id'],'9')
        self.assertEqual([x.workflow_id for x in ControlledLoader.created],[3991,4156,4157])

    def test_rapid_switch_only_fetches_last_requested_tab(self):
        w=self.window
        w.api_token='placeholder'
        ControlledLoader.created=[]
        with patch.object(appmod,'Loader',ControlledLoader):
            w.load_jobs();first=w.worker
            w.tabs.setCurrentIndex(1)
            w.tabs.setCurrentIndex(2)
            self.assertEqual(w.pending_request,(4157,'active'))
            first.finish()
            self.assertEqual(w.worker.workflow_id,4157)
            w.worker.finish([job(7)])
        self.assertEqual([x.workflow_id for x in ControlledLoader.created],[3991,4157])
        self.assertIsNone(w.sessions[4156]['jobs'])
        self.assertEqual(w.current_job['id'],'7')

    def test_cached_tab_cancels_pending_fetch_for_another_tab(self):
        self.populate()
        w=self.window
        w.api_token='placeholder'
        ControlledLoader.created=[]
        with patch.object(appmod,'Loader',ControlledLoader):
            w.load_jobs();first=w.worker
            w.tabs.setCurrentIndex(1)
            self.assertEqual(w.pending_request,(4156,'active'))
            w.tabs.setCurrentIndex(0)
            self.assertIsNone(w.pending_request)
            first.finish()
        self.assertEqual(len(ControlledLoader.created),1)
        self.assertEqual(w.current_job['id'],'3')
        self.assertIsNone(w.worker)

    def test_old_workflow_results_never_replace_visible_other_workflow(self):
        self.populate(4156,[job(9)])
        w=self.window
        w.tabs.setCurrentIndex(1)
        before=w.browser.url()
        w.received([job(3)],3991)
        self.assertEqual(w.current_job['id'],'9')
        self.assertEqual(w.browser.url(),before)
        self.assertEqual(w.sessions[3991]['jobs'][0]['id'],'3')
        self.assertEqual(w.sessions[4156]['jobs'][0]['id'],'9')

    def test_old_progress_ignored_and_api_failure_does_not_lock_tabs(self):
        w=self.window
        w.api_token='placeholder'
        with patch.object(appmod,'Loader',ControlledLoader):
            w.load_jobs();first=w.worker
            w.tabs.setCurrentIndex(1)
            first.progress.emit('WRONG OLD PROGRESS')
            self.assertNotEqual(w.info.text(),'WRONG OLD PROGRESS')
            first.finish()
            w.worker.progress.emit('F012 progress')
            self.assertEqual(w.info.text(),'F012 progress')
            w.worker.finish(error='F012 denied')
        self.assertIn('F012 denied',w.info.text())
        self.assertTrue(w.tabs.isEnabled())
        self.assertTrue(w.refresh.isEnabled())
        self.assertIsNone(w.worker)

    def test_finished_signal_race_waits_for_original_worker_cleanup(self):
        w=self.window
        w.api_token='placeholder'
        ControlledLoader.created=[]
        with patch.object(appmod,'Loader',ControlledLoader):
            w.load_jobs();first=w.worker
            first.running=False  # Native thread stopped; finished signal not processed.
            w.tabs.setCurrentIndex(1)
            self.assertIs(w.worker,first)
            self.assertEqual(len(ControlledLoader.created),1)
            first.finish()
            self.assertEqual(w.worker.workflow_id,4156)
            w.worker.finish([job(9)])
        self.assertEqual(w.current_job['id'],'9')

    def test_close_while_switching_does_not_launch_pending_fetch(self):
        w=self.window
        w.api_token='placeholder'
        ControlledLoader.created=[]
        with patch.object(appmod,'Loader',ControlledLoader):
            w.load_jobs();first=w.worker
            w.tabs.setCurrentIndex(1)
            w.close()
            self.assertTrue(w.closing)
            first.finish()
        self.assertEqual(len(ControlledLoader.created),1)
        self.assertIsNone(w.worker)
        self.assertFalse(w.isVisible())

    def test_state_snapshots_are_loaded_on_demand_and_reused(self):
        w=self.window
        w.api_token='placeholder'
        ControlledLoader.created=[]
        with patch.object(appmod,'Loader',ControlledLoader):
            w.load_jobs()
            self.assertEqual(w.worker.request_state,'active')
            w.worker.finish([job(3)])
            self.assertEqual(w.model.rowCount(),1)
            self.assertEqual(w.session()['loaded_state'],'active')
            w.states.setCurrentIndex(w.states.findData('failed'))
            self.assertEqual(w.worker.request_state,'failed')
            self.assertEqual(w.model.rowCount(),0)
            w.worker.finish([job(2,'failed')])
            self.assertEqual(w.current_job['id'],'2')
            w.states.setCurrentIndex(w.states.findData('active'))
            self.assertIsNone(w.worker)
            self.assertEqual(w.current_job['id'],'3')
            self.assertNotIn('*',w.session()['batches'])
            w.states.setCurrentIndex(w.states.findData('*'))
            self.assertEqual(w.worker.request_state,'*')
            w.worker.finish([job(3),job(2,'failed'),job(1,'done')])
        self.assertEqual([t.request_state for t in ControlledLoader.created],['active','failed','*'])
        self.assertEqual(w.model.rowCount(),3)

    def test_empty_active_result_never_falls_back_to_full_history(self):
        w=self.window
        w.api_token='placeholder'
        ControlledLoader.created=[]
        with patch.object(appmod,'Loader',ControlledLoader):
            w.load_jobs();w.worker.finish([])
            self.assertEqual(w.session()['jobs'],[])
            self.assertIn('active',w.session()['batches'])
            self.assertIsNone(w.worker)
            w.tabs.setCurrentIndex(1);w.worker.finish([job(9)])
            w.tabs.setCurrentIndex(0)
            self.assertIsNone(w.worker)
        self.assertEqual(w.model.rowCount(),0)
        self.assertEqual([t.request_state for t in ControlledLoader.created],['active','active'])

    def test_changing_state_during_fetch_queues_only_last_requested_state(self):
        w=self.window
        w.api_token='placeholder'
        ControlledLoader.created=[]
        with patch.object(appmod,'Loader',ControlledLoader):
            w.load_jobs();first=w.worker
            w.states.setCurrentIndex(w.states.findData('done'))
            w.states.setCurrentIndex(w.states.findData('failed'))
            self.assertTrue(first.cancelled)
            self.assertEqual(w.pending_request,(3991,'failed'))
            # Even a late successful active response must not populate failed view.
            w.received([job(3)],3991,'active')
            self.assertEqual(w.model.rowCount(),0)
            first.finish()
            self.assertEqual(w.worker.request_state,'failed')
            w.worker.finish([job(2,'failed')])
        self.assertEqual(w.current_job['id'],'2')
        self.assertEqual([t.request_state for t in ControlledLoader.created],['active','failed'])
        self.assertEqual(w.session()['batches']['active']['jobs'][0]['id'],'3')

    def test_refresh_replaces_active_snapshot_without_merging_history(self):
        w=self.window
        w.received([job(1,'done')],3991,'done')
        w.received([job(3),job(2)],3991,'active')
        self.assertEqual(w.model.rowCount(),2)
        w.received([job(2)],3991,'active')
        self.assertEqual([j['id'] for j in w.model.rows],['2'])
        self.assertEqual([j['id'] for j in w.session()['batches']['done']['jobs']],['1'])
        self.assertNotIn('*',w.session()['batches'])

    def test_fresh_all_snapshot_supersedes_older_state_snapshots(self):
        w=self.window
        w.received([job(3)],3991,'active')
        w.received([job(2),job(3,'done')],3991,'*')
        self.assertEqual(set(w.session()['batches']),{'*'})
        self.assertEqual(w.current_job['id'],'2')
        self.assertEqual(w.session()['loaded_state'],'*')
        w.states.setCurrentIndex(w.states.findData('done'))
        self.assertEqual(w.current_job['id'],'3')

    def test_cached_state_cancels_queued_history_request(self):
        w=self.window
        w.received([job(3)],3991,'active')
        w.api_token='placeholder'
        ControlledLoader.created=[]
        with patch.object(appmod,'Loader',ControlledLoader):
            w.load_jobs();first=w.worker
            w.states.setCurrentIndex(w.states.findData('done'))
            self.assertEqual(w.pending_request,(3991,'done'))
            w.states.setCurrentIndex(w.states.findData('active'))
            self.assertIsNone(w.pending_request)
            first.finish()
        self.assertEqual(len(ControlledLoader.created),1)
        self.assertEqual(w.current_job['id'],'3')
        self.assertIsNone(w.worker)

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

    def test_native_fonts_have_positive_point_sizes(self):
        w=self.window
        for widget in (w,w.search,w.api_status,w.table,w.states):
            self.assertGreater(widget.font().pointSizeF(),0)

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

    def test_server_filter_uses_textual_status_and_paginates_filtered_total(self):
        for wid in (3991,4156,4157):
            records=[dict(id=i,workflow_id=wid,name=str(i),state=state) for i,state in
                     [(5,'active'),(4,'done'),(3,'active'),(2,'failed'),(1,'active')]]
            calls=[]
            class Session:
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def post(self,url,data,**kwargs):
                    calls.append(data.copy())
                    filtered=[r for r in records if r['state']==data['status']]
                    page=data['page_id']
                    obj=dict(code=1,page=page,total_items=len(filtered),items_per_page=2,
                             jobs=filtered[page*2:page*2+2])
                    return SimpleNamespace(raise_for_status=lambda:None,json=lambda:obj)
            with patch.object(appmod.requests,'Session',Session):
                rows=appmod.fetch_jobs('placeholder',wid,lambda:False,lambda _:None,state='active')
            self.assertEqual([j['id'] for j in rows],['5','3','1'])
            self.assertEqual([c['page_id'] for c in calls],[0,1])
            self.assertTrue(all(c['status']=='active' and 'state' not in c for c in calls))

    def test_ignored_server_state_filter_is_rejected(self):
        class Session:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def post(self,url,data,**kwargs):
                obj=dict(code=1,page=0,total_items=1,items_per_page=100,
                    jobs=[dict(id=1,workflow_id=3991,name='history',state='done')])
                return SimpleNamespace(raise_for_status=lambda:None,json=lambda:obj)
        with patch.object(appmod.requests,'Session',Session),self.assertRaisesRegex(RuntimeError,'bộ lọc trạng thái'):
            appmod.fetch_jobs('placeholder',3991,lambda:False,lambda _:None,state='active')

    def test_empty_server_filtered_page_is_valid_without_history_fallback(self):
        calls=[]
        class Session:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def post(self,url,data,**kwargs):
                calls.append(data.copy())
                obj=dict(code=1,page=0,total_items=0,items_per_page=100,jobs=[])
                return SimpleNamespace(raise_for_status=lambda:None,json=lambda:obj)
        with patch.object(appmod.requests,'Session',Session):
            rows=appmod.fetch_jobs('placeholder',3991,lambda:False,lambda _:None,state='active')
        self.assertEqual(rows,[])
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['status'],'active')

    def test_only_specific_website_warnings_are_classified(self):
        fresh="Failed to execute 'postMessage' on 'DOMWindow': The target origin provided ('https://wchat.freshchat.com') does not match the recipient window's origin ('https://workflow.base.vn')."
        autoplay="Uncaught (in promise) NotAllowedError: play() failed because the user didn't interact with the document first."
        self.assertEqual(appmod.console_notice(fresh),'freshchat_origin')
        self.assertEqual(appmod.console_notice(autoplay),'autoplay_blocked')
        for other in ('Uncaught TypeError: cannot read property',
                      "Failed to execute 'postMessage': target origin other.example",
                      'NotAllowedError: camera permission denied'):
            self.assertIsNone(appmod.console_notice(other))

    def test_repeated_known_warnings_are_explained_once(self):
        page=SimpleNamespace(notices=set())
        fresh="Failed to execute 'postMessage': wchat.freshchat.com target origin mismatch"
        autoplay="NotAllowedError: play() failed because the user didn't interact"
        output=io.StringIO()
        with patch('sys.stderr',output):
            for _ in range(5):
                appmod.BrowserPage.javaScriptConsoleMessage(page,None,fresh,0,'')
                appmod.BrowserPage.javaScriptConsoleMessage(page,None,autoplay,0,'')
        self.assertEqual(len(output.getvalue().splitlines()),2)
        self.assertEqual(page.notices,{'freshchat_origin','autoplay_blocked'})

    def test_po_recognition(self):
        self.assertEqual(appmod.po_candidates('PO 4500000003 | PR 1000000001'),['4500000003'])
        self.assertEqual(appmod.po_candidates('Đường trắng - 4500000001'),['4500000001'])
        self.assertEqual(appmod.po_candidates('4500000001 / 4500000002'),['4500000001','4500000002'])
        self.assertEqual(appmod.po_candidates('PR 1000000001'),[])
        self.assertEqual(appmod.po_candidates('145000000010'),[])


if __name__=='__main__':unittest.main(verbosity=2)
