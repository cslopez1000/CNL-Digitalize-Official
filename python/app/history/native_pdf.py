"""CST report options using native chart captures, never a Python graph renderer.

Qt places native chart images and CST snapshot metadata on A4 pages. A temporary
file is committed atomically, so a rendering failure cannot truncate a report.
"""
from PySide6.QtCore import QSaveFile,QIODevice,QRectF,Qt
from PySide6.QtGui import QPdfWriter,QPainter,QPageSize,QFont,QColor
from python.app.history.sqlite_viewer_report import marker_text
from python.app.history.sqlite_viewer_report import _PAPER
from python.app.history.native_plot_pane import native_color
from python.app.widgets.NativeVacuumHistory import NativeChartSurface


def export_native_pdf(path,panes,info,*,include_markers=True,print_friendly=True,one_plot_per_page=False):
    images=[]
    snapshots=[]
    for pane in panes:
        snapshot=pane.report_snapshot()
        renderer=NativeChartSurface(pane)
        # Render at the report's aspect ratio and resolution. Stretching a
        # narrow on-screen canvas would distort fonts and marker boxes.
        render_width=900
        render_height=1050 if one_plot_per_page else max(220,1050//max(1,len(panes)))
        try:
            def draw(plot):
                plot.history_paper=print_friendly
                plot.history_log=snapshot.yscale=="log"
                plot.history_scientific=snapshot.scientific
                plot.history_x=snapshot.xlim
                plot.history_y=snapshot.ylim
                plot.history_label=snapshot.ylabel
                for index,trace in enumerate(snapshot.traces):
                    color=_PAPER["colors"][index%len(_PAPER["colors"])] if print_friendly else trace.color
                    plot.set_monitor_series(index,trace.x.tolist(),trace.y.tolist(),native_color(color),trace.label)
                if include_markers:
                    plot.set_history_markers([m.x for m in snapshot.markers],
                        [marker_text(m,snapshot.traces) for m in snapshot.markers],
                        [native_color(m.color) for m in snapshot.markers])
                plot.render_history(render_width,render_height,2.)
            images.append(renderer.render_frame(render_width,render_height,2.,draw))
            snapshots.append(snapshot)
        finally:
            renderer.close()
            renderer.deleteLater()
    destination=QSaveFile(str(path))
    if not destination.open(QIODevice.OpenModeFlag.WriteOnly): raise OSError(destination.errorString())
    writer=QPdfWriter(destination)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(120)
    writer.setTitle("CNL | Record Viewer")
    painter=QPainter(writer)
    if not painter.isActive():
        destination.cancelWriting()
        raise RuntimeError("Could not initialize the PDF writer")
    width,height=writer.width(),writer.height()
    margin=32
    ink=QColor("#171B22" if print_friendly else "#ECEFF3")
    background=QColor("white" if print_friendly else "#090A0C")
    pages=0

    def new_page():
        nonlocal pages
        if pages: writer.newPage()
        pages+=1
        painter.resetTransform()
        painter.setClipping(False)
        painter.fillRect(QRectF(0,0,width,height),background)
        painter.setPen(ink)
        painter.setFont(QFont("Segoe UI",15,QFont.Weight.DemiBold))
        painter.drawText(QRectF(margin,10,width-2*margin,30),"CNL | Record Viewer")
        painter.setFont(QFont("Segoe UI",8))
        metadata=f"{info.database}\n{info.start_time} — {info.end_time}\n{info.displayed_count} displayed / {info.loaded_count} loaded samples · {info.scaling_mode}"
        painter.drawText(QRectF(margin,44,width-2*margin,80),Qt.AlignmentFlag.AlignLeft|Qt.TextFlag.TextWordWrap,metadata)

    try:
        groups=[[i] for i in range(len(images))] if one_plot_per_page else [list(range(len(images)))]
        for group in groups:
            new_page()
            plot_height=(height-170)/max(1,len(group))
            for row,index in enumerate(group):
                y=130+row*plot_height
                painter.setFont(QFont("Segoe UI",10,QFont.Weight.DemiBold))
                painter.drawText(QRectF(margin,y,width-2*margin,24),snapshots[index].title)
                available_width=width-2*margin
                available_height=plot_height-35
                ratio=min(available_width/images[index].width(),available_height/images[index].height())
                draw_width,draw_height=images[index].width()*ratio,images[index].height()*ratio
                painter.save()
                painter.drawImage(QRectF(margin,y+25,draw_width,draw_height),images[index])
                painter.restore()
        if include_markers:
            entries=[]
            for snapshot in snapshots:
                for marker in snapshot.markers:
                    if snapshot.xlim[0]<=marker.x<=snapshot.xlim[1]:
                        entries.append(snapshot.title+"\n"+marker_text(marker,snapshot.traces))
            if entries:
                new_page()
                y=132
                painter.setFont(QFont("Segoe UI",9))
                for entry in entries:
                    needed=18*(entry.count("\n")+2)
                    if y+needed>height-30:new_page();y=132
                    painter.drawText(QRectF(margin,y,width-2*margin,needed),Qt.AlignmentFlag.AlignLeft|Qt.TextFlag.TextWordWrap,entry)
                    y+=needed
        painter.end()
        del writer
        if not destination.commit(): raise OSError(destination.errorString())
    except Exception:
        if painter.isActive(): painter.end()
        destination.cancelWriting()
        raise
    return pages
