"""CST history UI with worker-owned read connections and native plot panes."""
from pathlib import Path
from contextlib import closing
import math
import os
import sqlite3
import pandas as pd
from PySide6 import QtCore,QtWidgets
from python.adapters.background_tasks import BackgroundTasks
from python.app.history.sqlite_viewer_qt import SQLiteLogViewer,display_channel_labels,LV_OFFSET
from python.app.widgets.CstTrendWidget import CstTrendWidget


def read_metadata(path):
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+"?mode=ro",uri=True,timeout=2)) as connection:
        columns=[row[1] for row in connection.execute("PRAGMA table_info(channel_data)")]
        minimum,maximum=connection.execute("SELECT MIN(timestamp),MAX(timestamp) FROM channel_data").fetchone()
    return dict(path=path,columns=columns,latest=maximum,epoch="labview" if minimum is not None and float(minimum)>3e9 else "unix")


def read_history(path,columns,start,end):
    metadata=read_metadata(path)
    if metadata["epoch"]=="labview": start+=LV_OFFSET;end+=LV_OFFSET
    allowed=set(metadata["columns"])
    selected=[name for name in columns if name in allowed]
    if "timestamp" not in selected: raise ValueError("Database has no timestamp column")
    quoted=",".join('"'+name.replace('"','""')+'"' for name in selected)
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+"?mode=ro",uri=True,timeout=2)) as connection:
        frame=pd.read_sql_query(f"SELECT {quoted} FROM channel_data WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp ASC",connection,params=(start,end))
    return metadata,frame


def check_history(path,start,end):
    metadata=read_metadata(path)
    if metadata["epoch"]=="labview": start+=LV_OFFSET;end+=LV_OFFSET
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+"?mode=ro",uri=True,timeout=2)) as connection:
        count=connection.execute("SELECT COUNT(*) FROM channel_data WHERE timestamp BETWEEN ? AND ?",(start,end)).fetchone()[0]
    return metadata,count


class HistoryWindow(SQLiteLogViewer):
    def __init__(self,db_path=None,parent=None):
        self._defer_initial=True
        self._closed=False
        self._metadata={"epoch":"unix","latest":None}
        super().__init__(db_path,parent)
        self.tasks=BackgroundTasks(self)
        self.tasks.completed.connect(self._complete)
        self._defer_initial=False
        self.load_columns()

    def _connect(self):
        raise RuntimeError("History SQL belongs to its reader worker, not the GUI thread")

    def _detect_db_epoch(self): return self._metadata["epoch"]
    def _latest_timestamp(self): return self._metadata["latest"]

    def load_columns(self,autofit_window=True):
        if self._defer_initial or self._closed: return
        self._autofit_window=autofit_window
        self.status.setText("Loading database columns…")
        self.tasks.submit("metadata",read_metadata,self.db_edit.text().strip())

    def jump_to_latest(self,safety_window_s=300):
        if self._closed:return
        self._autofit_window=True
        self._safety_window_s=safety_window_s
        self.tasks.submit("metadata",read_metadata,self.db_edit.text().strip())

    def run_query(self):
        if self._defer_initial or self._closed:return
        series=self.p1.series+self.p2.series+self.p3.series
        if not series:
            self.tasks.invalidate("query")
            self.status.setText("Drag variables to plots to load data")
            self._last_df=pd.DataFrame()
            self._last_df_shown=pd.DataFrame()
            return
        columns=self._expand_needed_cols(series)
        self.status.setText("Loading recorded samples…")
        self.tasks.submit("query",read_history,self.db_edit.text().strip(),columns,
                          self.start_dt.dateTime().toSecsSinceEpoch(),self.end_dt.dateTime().toSecsSinceEpoch())

    def _check_window(self):
        self.tasks.submit("check",check_history,self.db_edit.text().strip(),
                          self.start_dt.dateTime().toSecsSinceEpoch(),self.end_dt.dateTime().toSecsSinceEpoch())

    def _save_pdf(self,path,panes,**options):
        from python.app.history.native_pdf import export_native_pdf
        from python.app.history.sqlite_viewer_report import ReportInfo
        info=ReportInfo(self._loaded_db_path,self._format_marker_time(0),
                        self._format_marker_time(len(self._last_df_shown)-1),len(self._last_df_shown),
                        len(self._last_df),"Scaling ON" if self._scaling_enabled else "Scaling OFF")
        return export_native_pdf(path,panes,info,**options)

    def _complete(self,key,token,result,error):
        if not self.tasks.current(key,token):return
        if error:
            self.status.setText(f"History {key} failed: {error}")
            return
        metadata=result if key=="metadata" else result[0]
        if os.path.abspath(metadata["path"])!=os.path.abspath(self.db_edit.text().strip()):return
        self._metadata=metadata
        if key=="metadata":
            self._db_cols=set(metadata["columns"])
            self.col_list.clear()
            for name in metadata["columns"]:
                item=QtWidgets.QListWidgetItem(display_channel_labels(name))
                item.setData(QtCore.Qt.ItemDataRole.UserRole,name)
                item.setToolTip(f"SQLite column: {name}")
                item.setFlags(item.flags()|QtCore.Qt.ItemFlag.ItemIsDragEnabled)
                self.col_list.addItem(item)
            self.status.setText(f"Loaded {len(self._db_cols)} columns. Drag variables to plots.")
            if self._autofit_window and metadata["latest"] is not None:
                latest=float(metadata["latest"])-(LV_OFFSET if metadata["epoch"]=="labview" else 0)
                for widget,stamp in ((self.start_dt,latest-getattr(self,"_safety_window_s",300)),(self.end_dt,latest)):
                    widget.blockSignals(True)
                    widget.setDateTime(QtCore.QDateTime.fromSecsSinceEpoch(int(stamp)))
                    widget.blockSignals(False)
                self.run_query()
        elif key=="query":
            self._loaded_db_path=os.path.abspath(metadata["path"])
            self._loaded_epoch=metadata["epoch"]
            self._last_df=result[1]
            self._last_df_shown=self._decimate_uniform(self._last_df,int(self.points_n.value())).copy()
            self._render_current_data()
            if self._last_df.empty:self.status.setText("No rows in window. Use 'Check' or 'Jump to Latest'.")
        elif key=="check":
            QtWidgets.QMessageBox.information(self,"Window check",f"Rows in window: {result[1]}\nEpoch mode: {metadata['epoch']}\nLatest row: {metadata['latest']}")

    def shutdown(self):
        if self._closed:return
        self._closed=True
        self.tasks.close()
        for chart in self.findChildren(CstTrendWidget):chart.release_native_resources()

    def closeEvent(self,event):
        self.shutdown()
        super().closeEvent(event)
