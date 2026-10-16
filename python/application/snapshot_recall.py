"""Original CST recall layout and actions, with asynchronous workbook reads."""
from python.app.history.snapshot_recall_qt import SnapshotRecallDialog,_first_existing,_parse_dt,TS_CANDIDATES,NOTE_CANDIDATES
from python.adapters.background_tasks import BackgroundTasks
from source.Python.Data.snapshot_store import read_snapshots


class AsyncSnapshotRecallDialog(SnapshotRecallDialog):
    def __init__(self,*args,**kwargs):
        self._ready=False
        super().__init__(*args,**kwargs)
        self.tasks=BackgroundTasks(self)
        self.tasks.completed.connect(self._loaded)
        self._ready=True
        self._load_file()

    def _load_file(self):
        if not self._ready:return
        self._set_apply_enabled(False)
        self.info.setText(f"Loading snapshots from:\n{self.snapshot_path}")
        self.tasks.submit("snapshots",read_snapshots,self.snapshot_path)

    def _loaded(self,key,token,result,error):
        if not self.tasks.current(key,token):return
        if error:
            self.info.setText(f"Failed to read snapshot file:\n{self.snapshot_path}\n\n{error}")
            return
        self.headers,self.rows=result
        ts_col=_first_existing(self.headers,TS_CANDIDATES)
        note_col=_first_existing(self.headers,NOTE_CANDIDATES)
        self.combo.blockSignals(True)
        self.combo.clear()
        for index,row in enumerate(reversed(self.rows)):
            stamp=_parse_dt(row.get(ts_col)) if ts_col else None
            label=stamp.strftime("%Y-%m-%d %H:%M:%S") if stamp else "no-time"
            note=str(row.get(note_col) or "").strip() if note_col else ""
            self.combo.addItem(f"{label} — {note}" if note else label,len(self.rows)-1-index)
        self.combo.blockSignals(False)
        self.info.setText(f"Loaded {len(self.rows)} snapshots from:\n{self.snapshot_path}")
        self._set_apply_enabled(bool(self.rows))
        if self.rows:self._on_select(0)

    def done(self,result):
        self.tasks.close()
        super().done(result)
