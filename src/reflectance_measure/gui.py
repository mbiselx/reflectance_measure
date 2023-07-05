import math
import logging
from typing import TYPE_CHECKING

import pyqtgraph as pg
if TYPE_CHECKING:  # use the PyQt6 stubs for typechecking, as they are the most complete
    try:
        from PyQt6.QtCore import Qt, QTimer, QRectF
        from PyQt6.QtGui import QKeySequence
        from PyQt6.QtWidgets import *
    except ImportError:
        from PyQt5.QtCore import Qt, QTimer, QRectF
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import *
else:
    from pyqtgraph.Qt.QtCore import Qt, QTimer, QRectF
    from pyqtgraph.Qt.QtGui import QKeySequence
    from pyqtgraph.Qt.QtWidgets import *

from reflectance_measure.stage.stage_gui import Stage, StageSelector, StageMonitor, StageControl
from reflectance_measure.daq.daq_gui import DAQ, DAQSelector, DAQMonitor


class DynamicLayoutDockWidget(QDockWidget):
    '''dockwidget which dynamically adapts its layout depending on the dock it is placed in'''

    def update_layout(self, dock_area: Qt.DockWidgetArea):
        widget = self.widget()
        layout = widget.layout()

        if not isinstance(layout, QBoxLayout):
            return

        if dock_area & (Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea):
            layout.setDirection(QBoxLayout.Direction.TopToBottom)
        elif dock_area & (Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea):
            layout.setDirection(QBoxLayout.Direction.LeftToRight)


class MyMainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._stage = Stage()
        self._daq = DAQ()

        # scatterplot as central widget
        self._plot = pg.PlotWidget(self)
        r = QRectF(0, 0, 20, 20)
        self._plot.setRange(r)

        # polar grid lines
        self._plot.addLine(x=0, pen=0.2)
        self._plot.addLine(y=0, pen=0.2)
        for r in range(2, 20, 2):
            circle = pg.CircleROI((-r, -r), radius=r,
                                  movable=False, handlePen=0.0)
            circle.setPen(pg.mkPen(0.2))
            self._plot.addItem(circle)

        self._motor_angle_line = pg.InfiniteLine()
        self._plot.addItem(self._motor_angle_line)

        self._scatter = pg.ScatterPlotItem()
        self._plot.addItem(self._scatter)

        self.setCentralWidget(self._plot)

        #
        self.tb = self.addToolBar("action")

        self._measure_action = QAction("measure", self)
        self._measure_action.setShortcut(QKeySequence('Ctrl+M'))
        self._measure_action.triggered.connect(self.measure_single_point)
        self.tb.addAction(self._measure_action)

        self._clear_action = QAction("clear", self)
        self._clear_action.setShortcut(QKeySequence('Ctrl+R'))
        self._clear_action.triggered.connect(self._scatter.clear)
        self.tb.addAction(self._clear_action)

        # add stage control widgets on the left
        self._stage_info = StageMonitor(self, self._stage)
        self._stage_info_dock = QDockWidget(
            "stage info", self)
        self._stage_info_dock.setWidget(self._stage_info)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,
                           self._stage_info_dock)

        self._stage_selector = StageSelector(self, self._stage)
        self._stage_selector_dock = QDockWidget(
            "stage selector", self)
        self._stage_selector_dock.setWidget(self._stage_selector)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,
                           self._stage_selector_dock)

        self._stage_control = StageControl(self, self._stage)
        self._stage_control_dock = QDockWidget(
            "stage control", self)
        self._stage_control_dock.setWidget(self._stage_control)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,
                           self._stage_control_dock)

        self.tabifyDockWidget(self._stage_control_dock,
                              self._stage_selector_dock)

        # add photodiode control widgets on the right
        self._daq_info = DAQMonitor(self, self._daq)
        self._daq_info_dock = QDockWidget(
            "daq info", self)
        self._daq_info_dock.setWidget(self._daq_info)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,
                           self._daq_info_dock)

        self._daq_selector = DAQSelector(self, self._daq)
        self._daq_selector_dock = QDockWidget(
            "daq selector", self)
        self._daq_selector_dock.setWidget(self._daq_selector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,
                           self._daq_selector_dock)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(250)
        self._refresh_timer.timeout.connect(self._update_angle)
        self._refresh_timer.start()

    def _update_angle(self, *args):
        if self._stage.axis:
            a = -self._stage.get_position()
            self._motor_angle_line.setAngle(a)

    def measure_single_point(self, *args):
        print("measure")
        v = self._daq.read_channel() + 10
        a = -self._stage.get_position()/180*math.pi  # angle is inverted

        self._scatter.addPoints([math.cos(a)*v], [math.sin(a)*v])

    def closeEvent(self, *args):
        try:
            self._stage.close()
        except Exception as e:
            print(e)
        try:
            self._daq.close()
        except Exception as e:
            print(e)
        return super().closeEvent(*args)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)

    app = pg.mkQApp("reflectance measure")

    mw = MyMainWindow()
    mw.show()

    sys.exit(app.exec())
