"""Actual OpenGL 4.6 offscreen render, state restoration and release/recreate."""
import ctypes
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from python.application.native_modules import configure_native_path
configure_native_path()
from PySide6.QtGui import QGuiApplication,QOffscreenSurface,QOpenGLContext,QSurfaceFormat
from PySide6.QtOpenGL import QOpenGLFramebufferObject,QOpenGLFramebufferObjectFormat
from shiboken6 import getCppPointer
import CombinationCharts as native


def main():
    app=QGuiApplication([])
    fmt=QSurfaceFormat(); fmt.setVersion(4,6); fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    surface=QOffscreenSurface(); surface.setFormat(fmt); surface.create()
    context=QOpenGLContext(); context.setFormat(fmt)
    if not context.create() or not context.makeCurrent(surface):
        raise RuntimeError("Could not create an actual offscreen GL context; no rendering parity claimed")
    get=lambda name:int(context.getProcAddress(name.encode("ascii")) or 0)
    native.load_opengl(get)
    native.set_current_render_context(getCppPointer(context)[0])
    factory=getattr(ctypes,"WINFUNCTYPE",ctypes.CFUNCTYPE)
    def function(name,result,*args):
        address=get(name)
        if not address: raise RuntimeError(f"Unavailable GL function {name}")
        return factory(result,*args)(address)
    viewport=function("glViewport",None,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int)
    enable=function("glEnable",None,ctypes.c_uint)
    enabled=function("glIsEnabled",ctypes.c_ubyte,ctypes.c_uint)
    error=function("glGetError",ctypes.c_uint)
    get_float=function("glGetFloatv",None,ctypes.c_uint,ctypes.POINTER(ctypes.c_float))
    get_int=function("glGetIntegerv",None,ctypes.c_uint,ctypes.POINTER(ctypes.c_int))
    line_width=function("glLineWidth",None,ctypes.c_float)
    version=function("glGetString",ctypes.c_char_p,ctypes.c_uint)(0x1F02).decode()
    ffmt=QOpenGLFramebufferObjectFormat(); ffmt.setSamples(4)
    fbo=QOpenGLFramebufferObject(900,320,ffmt)
    if not fbo.isValid(): raise RuntimeError("Invalid render framebuffer")
    fbo.bind(); viewport(0,0,900,320)
    plot=native.CstTrendPlot()
    x=[i*.1 for i in range(1400)]
    target=[5.0]*len(x); actual=[5+math.sin(v*.4)*.8 for v in x]
    plot.model.set_data(x,target,actual)
    output=ROOT/"docs/evidence"; output.mkdir(parents=True,exist_ok=True)
    # Host state should survive every native draw, including text batches.
    enable(0x8642)  # GL_PROGRAM_POINT_SIZE
    widths=(ctypes.c_float*2)(); get_float(0x846E,widths)
    host_width=min(3.,float(widths[1])); line_width(host_width)
    actual_host_width=ctypes.c_float(); get_float(0x0B21,ctypes.byref(actual_host_width))
    host_width=actual_host_width.value  # drivers may clamp wide native lines
    while error(): pass
    started=time.perf_counter()
    for _ in range(10): plot.render(900,320,1.)
    elapsed=(time.perf_counter()-started)*1000/10
    assert error()==0,"OpenGL error after native draws"
    assert enabled(0x8642),"Host program point-size enable was not restored"
    width=ctypes.c_float(); get_float(0x0B21,ctypes.byref(width))
    assert abs(width.value-host_width)<1e-6,"Host line width was not restored"
    src_alpha=ctypes.c_int(); get_int(0x80CB,ctypes.byref(src_alpha))
    image=fbo.toImage(); assert not image.isNull()
    assert image.pixelColor(899,319).name().lower()=="#0b1116","CST panel background"
    colored=sum(image.pixelColor(px,py).name().lower()!="#0b1116" for px in range(80,880,8) for py in range(15,272,4))
    assert colored>100,"Expected grid, text and traces in framebuffer"
    assert image.save(str(output/"cst_native_two_series.png"))
    fbo.bind(); viewport(0,0,900,320)
    plot.model.set_data(x,target,actual,[5+math.sin(v*.4)*.5 for v in x])
    plot.render(900,320,1.); assert error()==0
    assert fbo.toImage().save(str(output/"cst_native_three_series.png"))
    fbo.bind(); viewport(0,0,900,320)
    plot.model.relative_time=False
    plot.model.rolling_window=0
    plot.model.set_data(x,target,actual)
    plot.render_manual(900,320,1.)
    assert error()==0,"Native manual chart GL error"
    assert fbo.toImage().save(str(output/"cst_native_manual.png"))
    fbo.bind(); viewport(0,0,900,320)
    plot.gains=[.8,.1,.1]
    plot.render_gains(900,320,1.)
    assert error()==0,"Native gain radar GL error"
    assert fbo.toImage().save(str(output/"cst_native_gains.png"))
    fbo.bind(); viewport(0,0,900,320)
    plot.model.set_data([100,101,102,105],[2,2.1,2.2,2.3],[2,2.1,2.2,2.3])
    plot.render_beam(900,320,1.,105)
    assert error()==0,"Native embedded beam chart GL error"
    assert fbo.toImage().save(str(output/"cst_native_beam.png"))
    # Monitoring plots retain NaN gaps and use independent per-view geometry.
    monitor_x=[-120+i*.5 for i in range(241)]
    monitor_y=[5+math.sin(i*.1) for i in range(241)]
    monitor_y[80]=float("nan")
    plot.monitor_title="CST monitoring – native"
    plot.monitor_seconds=120
    plot.set_monitor_data(monitor_x,monitor_y)
    fbo.bind(); viewport(0,0,900,320)
    plot.render_transport(900,320,1.)
    assert error()==0,"Native transport rendering GL error"
    assert fbo.toImage().save(str(output/"cst_native_transport.png"))
    plot.set_monitor_series(0,monitor_x,monitor_y,native.Color(.2,.8,1),"TC 1")
    plot.set_monitor_series(1,monitor_x,[v*.5 for v in monitor_y],native.Color(1,.5,.1),"TC 2")
    for kind in (0,1,2,3):
        fbo.bind(); viewport(0,0,900,320)
        plot.render_magnetic(900,320,1.,kind)
        assert error()==0,f"Native monitoring kind {kind} GL error"
        assert enabled(0x8642),"Monitoring renderer changed host point state"
        get_float(0x0B21,ctypes.byref(width))
        assert abs(width.value-host_width)<1e-6,"Monitoring renderer changed host line width"
    try:
        plot.set_monitor_data([0,1],[1])
    except ValueError:
        pass
    else:
        raise AssertionError("Unequal monitor coordinates accepted")
    fbo.bind(); viewport(0,0,900,320)
    native.set_current_render_context(0)
    try:
        plot.render(900,320,1.)
    except RuntimeError: pass
    else: raise AssertionError("Missing native context identity was accepted")
    native.set_current_render_context(getCppPointer(context)[0])
    plot.release_resources(); plot.release_resources(); plot.render(900,320,1.)
    assert error()==0,"Release/recreate must produce valid GL resources"
    plot.release_resources()
    fbo.release()
    # Destroy framebuffer while its owning GL context remains current.
    del fbo
    native.set_current_render_context(0); context.doneCurrent()
    report={"status":"passed","gl_version":version,"mean_render_submit_ms_including_first_frame":elapsed,
            "renders":20,"host_line_width_restored":host_width,"non_background_probe_count":colored,
            "scope":"native CST controller and monitoring render/state smoke; screenshot comparison is manual, not full-app visual parity"}
    (output/"native_render.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__": main()
