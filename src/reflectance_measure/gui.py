import logging
from typing import TYPE_CHECKING

import pyqtgraph as pg
if TYPE_CHECKING:  # use the PyQt6 stubs for typechecking, as they are the most complete
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtWidgets import *
else:
    from pyqtgraph.Qt.QtCore import Qt, QTimer
    from pyqtgraph.Qt.QtWidgets import *

from reflectance_measure.stage.stage_gui import StageSelector, StageMonitor, StageControl
from reflectance_measure.daq.daq_gui import DAQSelector, DAQMonitor


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

        # scatterplot as central widget
        self._scatter = pg.ScatterPlotItem()
        self._plot = pg.PlotWidget(self)
        self._plot.addItem(self._scatter)
        self.setCentralWidget(self._plot)

        # add stage control widgets on the left
        self._stage_info = StageMonitor(self)
        self._stage_info_dock = QDockWidget(
            "stage info", self)
        self._stage_info_dock.setWidget(self._stage_info)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,
                           self._stage_info_dock)

        self._stage_selector = StageSelector(self, self._stage_info.stage)
        self._stage_selector_dock = QDockWidget(
            "stage selector", self)
        self._stage_selector_dock.setWidget(self._stage_selector)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,
                           self._stage_selector_dock)

        self._stage_control = StageControl(self, self._stage_info.stage)
        self._stage_control_dock = QDockWidget(
            "stage control", self)
        self._stage_control_dock.setWidget(self._stage_control)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,
                           self._stage_control_dock)

        self.tabifyDockWidget(self._stage_control_dock,
                              self._stage_selector_dock)

        # add photodiode control widgets on the right
        self._daq_info = DAQMonitor(self)
        self._daq_info_dock = QDockWidget(
            "daq info", self)
        self._daq_info_dock.setWidget(self._daq_info)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,
                           self._daq_info_dock)

        self._daq_selector = DAQSelector(self, self._daq_info.daq)
        self._daq_selector_dock = QDockWidget(
            "daq selector", self)
        self._daq_selector_dock.setWidget(self._daq_selector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,
                           self._daq_selector_dock)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)

    app = pg.mkQApp("reflectance measure")

    mw = MyMainWindow()
    mw.show()

    sys.exit(app.exec())
