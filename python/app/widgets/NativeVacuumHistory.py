"""Native offscreen history image composited below CST's gauge text.

QOpenGLWidget children always sit above parent painting. A private offscreen
context lets the original gauge keep its correct history/needle/readout order.
Python only manages context lifetime and hands the C++ result to Qt for display.
"""
from PySide6.QtCore import QObject
from PySide6.QtGui import QOpenGLContext,QOffscreenSurface,QSurfaceFormat
from PySide6.QtOpenGL import QOpenGLFramebufferObject,QOpenGLFramebufferObjectFormat
from shiboken6 import getCppPointer
import CombinationCharts as native


class NativeChartSurface(QObject):
    def __init__(self,parent):
        super().__init__(parent)
        self.surface=None
        self.context=None
        self.framebuffer=None
        self.plot=native.CstTrendPlot()
        self.ready=False
        self.error=""
        parent.destroyed.connect(self.close)

    def render_frame(self,width,height,ratio,draw):
        previous=QOpenGLContext.currentContext()
        previous_surface=previous.surface() if previous else None
        if self.context is None:
            fmt=QSurfaceFormat()
            fmt.setVersion(4,6)
            fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
            self.surface=QOffscreenSurface()
            self.surface.setFormat(fmt)
            self.surface.create()
            self.context=QOpenGLContext(self)
            self.context.setFormat(fmt)
            if not self.context.create():raise RuntimeError("Cannot create native vacuum history context")
        if not self.context.makeCurrent(self.surface):raise RuntimeError("Cannot activate native vacuum history context")
        try:
            native.set_current_render_context(getCppPointer(self.context)[0])
            if not self.ready:
                native.load_opengl(lambda name:int(self.context.getProcAddress(name.encode("ascii")) or 0))
                self.ready=True
            pixel_width,pixel_height=max(1,round(width*ratio)),max(1,round(height*ratio))
            if self.framebuffer is None or self.framebuffer.width()!=pixel_width or self.framebuffer.height()!=pixel_height:
                self.framebuffer=None
                fmt=QOpenGLFramebufferObjectFormat()
                fmt.setSamples(4)
                self.framebuffer=QOpenGLFramebufferObject(pixel_width,pixel_height,fmt)
                if not self.framebuffer.isValid():raise RuntimeError("Cannot allocate native vacuum history framebuffer")
            self.framebuffer.bind()
            native.set_render_viewport(pixel_width,pixel_height)
            native.clear_transparent_frame()
            draw(self.plot)
            image=self.framebuffer.toImage()
            image.setDevicePixelRatio(ratio)
            return image
        except Exception as exc:
            self.error=str(exc)
            raise
        finally:
            self.context.doneCurrent()
            if previous is not None:
                previous.makeCurrent(previous_surface)
                native.set_current_render_context(getCppPointer(previous)[0])
            else:native.set_current_render_context(0)

    def close(self,*_args):
        if self.context is None:return
        previous=QOpenGLContext.currentContext()
        previous_surface=previous.surface() if previous else None
        if self.context.makeCurrent(self.surface):
            native.set_current_render_context(getCppPointer(self.context)[0])
            self.plot.release_resources()
            self.framebuffer=None
            native.set_current_render_context(0)
            self.context.doneCurrent()
        if previous is not None and previous!=self.context:
            previous.makeCurrent(previous_surface)
            native.set_current_render_context(getCppPointer(previous)[0])
        self.context=None
        if self.surface is not None:self.surface.destroy()
        self.surface=None
        self.ready=False


class NativeVacuumHistory(NativeChartSurface):
    def render(self,width,height,ratio,values,color,seconds):
        def draw(plot):
            plot.actual_color=native.Color(color.redF(),color.greenF(),color.blueF())
            plot.set_vacuum_data(list(values))
            plot.render_vacuum(width,height,ratio,True,0.,1.,240,0.,seconds)
        return self.render_frame(width,height,ratio,draw)
