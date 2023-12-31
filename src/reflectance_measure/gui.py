import csv
import math
import time
import logging
from collections import deque
from typing import TYPE_CHECKING

import pyqtgraph as pg
if TYPE_CHECKING:  # use the PyQt6 stubs for typechecking, as they
    # are the most complete
    from PyQt6.QtCore import Qt, QTimer, QRectF
    from PyQt6.QtGui import QKeySequence, QAction
    from PyQt6.QtWidgets import (QWidget, QMainWindow, QTabWidget,
                                 QBoxLayout, QDockWidget, QFileDialog)
else:
    from pyqtgraph.Qt.QtCore import Qt, QTimer, QRectF
    from pyqtgraph.Qt.QtGui import QKeySequence, QAction
    from pyqtgraph.Qt.QtWidgets import (QWidget, QMainWindow, QTabWidget,
                                        QBoxLayout, QDockWidget, QFileDialog)

from reflectance_measure.stage.stage_gui import (Stage, StageSelector,
                                                 StageMonitor, StageControl)
from reflectance_measure.daq.daq_gui import DAQ, DAQSelector, DAQMonitor
from reflectance_measure.automation import ExperimentAutomationWidget


class DynamicLayoutDockWidget(QDockWidget):
    '''
    dockwidget which dynamically adapts its layout depending
    on the dock it is placed in
    '''

    def update_layout(self, dock_area: Qt.DockWidgetArea):
        widget = self.widget()
        layout = widget.layout()

        if not isinstance(layout, QBoxLayout):
            return

        if dock_area & (Qt.DockWidgetArea.LeftDockWidgetArea |
                        Qt.DockWidgetArea.RightDockWidgetArea):
            layout.setDirection(QBoxLayout.Direction.TopToBottom)
        elif dock_area & (Qt.DockWidgetArea.TopDockWidgetArea |
                          Qt.DockWidgetArea.BottomDockWidgetArea):
            layout.setDirection(QBoxLayout.Direction.LeftToRight)


class MyMainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._stage = Stage()
        self._daq = DAQ()
        self._points: list[tuple(float, float)] = list()

        # scatterplot as central widget
        self._plot = pg.PlotWidget(self)
        r = QRectF(0, 0, 10, 10)
        self._plot.setRange(r)
        self._plot.setAspectLocked(True)
        self._plot.setMinimumWidth(300)

        self._timeline_plot = pg.PlotWidget(self)
        self._timeline = deque(maxlen=500), deque(maxlen=500)

        # polar grid lines
        self._plot.addLine(x=0, pen=0.2)
        self._plot.addLine(y=0, pen=0.2)
        for r in range(1, 10, 1):
            circle = pg.CircleROI((-r, -r), radius=r,
                                  movable=False, handlePen=0.0)
            circle.setPen(pg.mkPen(0.2))
            self._plot.addItem(circle)

        self._scatter = pg.ScatterPlotItem()
        self._plot.addItem(self._scatter)

        self._avg = pg.PlotCurveItem(pen=pg.mkPen('red'))
        self._plot.addItem(self._avg)

        self._motor_angle_line = pg.InfiniteLine(angle=0)
        self._plot.addItem(self._motor_angle_line)

        self._photodiode_value = pg.ScatterPlotItem(brush=pg.mkBrush('red'))
        self._plot.addItem(self._photodiode_value)

        self._tabs = QTabWidget(self)
        self._tabs.addTab(self._plot, "polar plot")
        self._tabs.addTab(self._timeline_plot, "timeline")
        self._tabs.setCurrentIndex(0)

        self.setCentralWidget(self._tabs)

        # add actions & keyboard shortcuts
        self.tb = self.addToolBar("action")

        self._avg_action = QAction("avg", self)
        self._avg_action.setCheckable(True)
        self._avg_action.triggered.connect(self.calculate_averages)
        self.tb.addAction(self._avg_action)

        self._measure_action = QAction("measure", self)
        self._measure_action.setShortcut(QKeySequence('Ctrl+M'))
        self._measure_action.triggered.connect(self.measure_single_point)
        self.tb.addAction(self._measure_action)

        self._clear_action = QAction("clear", self)
        self._clear_action.setShortcut(QKeySequence('Ctrl+R'))
        self._clear_action.triggered.connect(self.clear)
        self.tb.addAction(self._clear_action)

        self._save_action = QAction("save", self)
        self._save_action.setShortcut(QKeySequence('Ctrl+S'))
        self._save_action.triggered.connect(self.save_to_file)
        self.tb.addAction(self._save_action)

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

        # add automation widget on the bottom
        self._automation_widget = ExperimentAutomationWidget(
            self, stage=self._stage, daq=self._daq)
        self._automation_widget.sig_measurement_added.connect(
            self.add_single_point)
        self._automation_widget_dock = DynamicLayoutDockWidget(
            "automation", self)
        self._automation_widget_dock.setWidget(self._automation_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea,
                           self._automation_widget_dock)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(100)
        self._refresh_timer.timeout.connect(self._update_current_value)
        self._refresh_timer.start()

    def _update_current_value(self, *args):

        if self._daq.channel:
            v = self._daq.read_channel()
        else:
            v = float('nan')
        self._timeline[0].append(time.time())
        self._timeline[1].append(v)
        self._timeline_plot.plotItem.plot(
            *self._timeline,
            clear=True
        )

        if self._stage.axis:
            a = -self._stage.get_position()
            self._motor_angle_line.setAngle(a)

        if self._daq.channel and self._stage.axis:
            a *= (math.pi/180)
            x, y = v*math.cos(a), v*math.sin(a)
            self._photodiode_value.setData([x], [y])

    def save_to_file(self, *args):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            filter="CSV(*.csv)"
        )

        if filename in (None, ""):
            return

        if not filename.lower().endswith(".csv"):
            filename += ".csv"

        with open(filename, 'w') as file:

            writer = csv.writer(file, lineterminator='\n')
            writer.writerow(["angle [deg]", "intensity [V]"])
            writer.writerows(self._points)

    def measure_single_point(self, *args):
        print("measure")
        v = self._daq.read_channel()
        a = -self._stage.get_position()  # angle is inverted
        self.add_single_point((a, v))

    def add_single_point(self, point: tuple[float, float]):
        self._points.append(point)
        a, v = point
        a *= (math.pi/180)
        self._scatter.addPoints([math.cos(a)*v], [math.sin(a)*v])
        if self._avg_action.isChecked():
            self.calculate_averages()

    def calculate_averages(self, enabled=True):
        if not enabled:
            self._avg.clear()
            self._plot.plotItem.replot()
            return

        avg_x, avg_y = [], []
        unique_a = sorted(set(tuple(zip(*self._points))[0]))
        for a_a in unique_a:
            v_a = [v for a, v in self._points if a == a_a]
            avg_v = sum(v_a)/len(v_a)
            a_a *= (math.pi/180)
            avg_x.append(math.cos(a_a)*avg_v)
            avg_y.append(math.sin(a_a)*avg_v)

        self._avg.setData(avg_x, avg_y)

    def clear(self):
        self._scatter.clear()
        self._avg.clear()
        self._points = list()
        self._plot.plotItem.replot()

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

    try:
        import qdarktheme
        qdarktheme.setup_theme()
    except ImportError:
        logging.warning(
            "Failed to set dark theme. "
            "Please install pyqtdarktheme for dark theme enable ( pip install pyqtdarktheme )"
        )
    except Exception as e:
        logging.error(
            "Failed to set dark theme for the following reason : \n" + str(e))

    mw = MyMainWindow()
    mw.show()

    sys.exit(app.exec())
