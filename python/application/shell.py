"""CST launcher composition: keep its visuals and route views to one backend."""
from queue import Queue
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QMessageBox
from python.application.simulation import SimulationControllerWindow


def create_embedded_controller(control_queue,target_values,plot_config,data_queue=None):
    """Constructor boundary used by CST's unchanged portrait tab layout."""
    return SimulationControllerWindow(bridge=control_queue,target_values=target_values,
                                      plot_config=plot_config,data_queue=data_queue)


# The portrait module imports only the factory above during shell migration.
from python.app.shell.main_control_gui import MainControlWindow, BeamRangeDialog, SNAPSHOT_XLSX
from python.app.controls.cst.SmallScreenMagneticBeam import SmallScreenMagneticBeamWindow
from python.app.configuration.SettingsDialog import SettingsDialog
from python.app.configuration.ScaleCalWindow import ScaleCalWindow
from python.app.history.snapshot_recall_qt import SnapshotRecallDialog
from source.Python.Services.scaling import get_scaler
from python.adapters.background_tasks import BackgroundTasks
from python.app.history.snapshot_save_qt import SnapshotSaveDialog,_scale_signals_if_possible
from python.application.snapshot_recall import AsyncSnapshotRecallDialog


class _SharedTargets:
    def __init__(self,values):
        self.values = values

    def targets_snapshot(self):
        return list(self.values)


class _PortraitWindow(SmallScreenMagneticBeamWindow):
    def shutdown(self):
        self.mag_controller.shutdown()

    def closeEvent(self,event):
        self.shutdown()
        super().closeEvent(event)


class LauncherWindow(MainControlWindow):
    def __init__(self,session):
        self.session = session
        self.bridge = session.bridge
        self._closed = False
        self._mailbox = self.bridge.subscribe()
        targets = [0.0]*14
        self.shared_targets = _SharedTargets(targets)
        super().__init__(self._mailbox,targets,self.bridge,
                         {"channels":[False]*14,"duration":2,"rate":240})
        self.setWindowTitle(self.windowTitle()+" — SIMULATION")
        # CST used vac_queue for both views. A transport view must not consume
        # a vacuum view's packet; preserve the same averaging for both queues.
        self.transport_queue = Queue(maxsize=200)
        self._last_range_follow = None
        self._range_dialogs = []
        self.tasks=BackgroundTasks(self,cancel_on_close=False)
        self.tasks.completed.connect(self._file_complete)
        self._save_count=0

    def _put_drop_oldest(self,mailbox,packet):
        super()._put_drop_oldest(mailbox,packet)
        if mailbox is self.vac_queue:
            super()._put_drop_oldest(self.transport_queue,dict(packet))

    def _maybe_follow_range(self,packet):
        # Retain CST's follow policy, avoiding repeated identical JSON writes.
        key=tuple(packet.get(name) for name in ("bitmask","bitmask_u64","bitmask_double","beam_range_idx","range_idx"))
        if key!=self._last_range_follow:
            super()._maybe_follow_range(packet)
            self._last_range_follow=key
        # New windows still need the last confirmed range even when its value
        # has not changed. Only repeated persistence/logging is suppressed.
        from source.Python.Services.beam_range import RangeCodec
        index=packet.get("beam_range_idx",packet.get("range_idx"))
        for dialog in list(self._range_dialogs):
            dialog.pad.set_base_bitmask(self._bitmask_u64)
            dialog.pad.follow_from_u64(self._bitmask_u64,explicit_idx=index)
        if self.field_controller is not None:
            confirmed=index if index is not None else RangeCodec.parse(self._bitmask_u64)
            self.field_controller.request_beam_range_change(int(confirmed),self._bitmask_u64)

    def _register(self,window):
        self.session.register(window)
        return window

    def show_magnetic_field_monitoring(self):
        from python.application.magnetic_monitor import SimulationMagneticWindow
        self._safe_show_window("mag_monitor",lambda:self._register(
            SimulationMagneticWindow(self.bridge,self.shared_targets,self.mag_queue)))

    def show_source_extraction_monitoring(self):
        from python.application.source_monitor import SimulationSourceWindow
        self._safe_show_window("_src_monitor",lambda:self._register(
            SimulationSourceWindow(self.bridge,self.src_queue)))

    def show_beam_transport_monitoring(self):
        from python.application.transport_monitor import SimulationTransportWindow
        self._safe_show_window("_transport_monitor",lambda:self._register(
            SimulationTransportWindow(self.bridge,self.transport_queue)))

    def show_magnetic_field_controller(self):
        self._safe_show_window("field_controller",lambda:self._register(
            _PortraitWindow(self.bridge,self.target_values,self.plot_config,
                                         mag_data_queue=self.mag_ctrl_queue)))

    def show_vacuum_beam_monitoring(self):
        from python.application.vacuum_monitor import SimulationVacuumWindow
        self._safe_show_window("_vac_monitor",lambda:self._register(
            SimulationVacuumWindow(self.bridge,self.vac_queue)))

    def show_sqlite_viewer(self):
        from python.application.history import HistoryWindow
        self._safe_show_window("_sqlite_viewer",lambda:self._register(HistoryWindow(self.db_path)))

    def show_scaling_window(self):
        self._safe_show_window("_scale_window",lambda:self._register(ScaleCalWindow(scaler=get_scaler())))

    def show_settings_dialog(self):
        dialog=SettingsDialog(self)
        dialog.exec()
        self.bridge.configure_calibration()
        for window in self.session.windows:
            if hasattr(window,"apply_plot_settings"):
                window.apply_plot_settings()

    def show_beam_range_dialog(self):
        dialog=BeamRangeDialog(self,self._bitmask_u64)
        self._range_dialog=dialog
        dialog.pad.rangeSelected.connect(lambda index,mask:self.bridge.put(
            {"cmd":"set_beam_range","beam_range_idx":index,"bitmask_u64":mask}))
        self._range_dialogs.append(dialog)
        dialog.destroyed.connect(lambda *_:self._forget_range_dialog(dialog))
        if self.bridge.last_packet is not None:self._maybe_follow_range(self.bridge.last_packet)
        dialog.show()

    def _forget_range_dialog(self,dialog):
        if self._range_dialog is dialog:self._range_dialog=None
        if dialog in self._range_dialogs:self._range_dialogs.remove(dialog)

    def show_recall_dialog(self):
        dialog=AsyncSnapshotRecallDialog(self,snapshot_path=SNAPSHOT_XLSX,apply_callback=self.apply_magnetic_snapshot)
        dialog.exec()

    def snapshot_save_all(self):
        packet=getattr(self,"_latest_pkt",None)
        if not packet:
            QMessageBox.warning(self,"No data available","No live data has been received yet.\nWait for the system to start streaming before taking a snapshot.")
            return
        signals=dict(packet)
        dialog=SnapshotSaveDialog(self,filepath=SNAPSHOT_XLSX)
        if dialog.exec()!=dialog.DialogCode.Accepted:return
        self.save_snapshot(dialog.note or "",signals)

    def save_snapshot(self,note,packet=None):
        import time
        from source.Python.Data.snapshot_store import save_snapshot
        signals=_scale_signals_if_possible(dict(packet or self._latest_pkt))
        self._save_count+=1
        return self.tasks.submit(f"save-snapshot-{self._save_count}",save_snapshot,SNAPSHOT_XLSX,signals,note,time.time())

    def toggle_alarm(self):
        from source.Python.Services.alarm import alarm_manager
        alarm_manager.set_active(not alarm_manager.active)

    def _file_complete(self,key,token,result,error):
        if not self.tasks.current(key,token) or self._closed:return
        self.tasks.pending.pop(key,None)
        self.tasks.tokens.pop(key,None)
        if error:QMessageBox.critical(self,"Snapshot FAILED",f"Snapshot could not be saved.\n\n{error}")
        else:QMessageBox.information(self,"Snapshot saved",f"Snapshot successfully saved.\n\nFile:\n{result}")

    def apply_magnetic_snapshot(self,payload):
        # CST recall UI explicitly applies TC1..TC12 only. Do not reset the two
        # untouched actuator targets via main_control_gui's zero fallbacks.
        updates={i:float(payload[f"ch{i+1}"]) for i in range(12) if f"ch{i+1}" in payload}
        wrapper=self.field_controller
        controller=getattr(wrapper,"mag_controller",None) if wrapper else None
        if controller is not None:
            controller.context.set_targets(updates)
        else:
            for index,value in updates.items():
                self.target_values[index]=value

    def shutdown(self):
        if self._closed:
            return
        self._closed=True
        for timer in self.findChildren(QTimer):
            timer.stop()
        self._video_player.stop()
        self._video_player2.stop()
        self.bridge.unsubscribe(self._mailbox)
        self.tasks.close()

    def closeEvent(self,event):
        self.session.shutdown()
        for window in list(self.session.windows):
            if window is not self:
                window.close()
        super().closeEvent(event)
