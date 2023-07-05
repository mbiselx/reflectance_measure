from typing import TYPE_CHECKING

import logging
import pyqtgraph as pg
if TYPE_CHECKING:  # use the PyQt6 stubs for typechecking, as they are the nicest
    try:
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtWidgets import *
    except ImportError:
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtWidgets import *
else:
    from pyqtgraph.Qt.QtCore import Qt, QTimer
    from pyqtgraph.Qt.QtWidgets import *

from reflectance_measure.stage.stage_utils import Stage


class StageSelector(QGroupBox):

    def __init__(self, parent: QWidget | None = None, stage: Stage | None = None) -> None:
        super().__init__("Connection", parent)
        self._logger = logging.getLogger(self.__class__.__name__)

        self._stage = stage or Stage()

        self._layout = QFormLayout(self)

        self._connection_selector = QComboBox(self)
        self._connection_selector.activated.connect(self._open_connection)
        self._layout.addRow("Port :", self._connection_selector)

        self._axis_selector = QComboBox(self)
        self._axis_selector.setEnabled(False)
        self._axis_selector.activated.connect(self._open_axis)
        self._layout.addRow("Axis :", self._axis_selector)

        # update the listed ports
        self._update_com_ports()

    @property
    def stage(self) -> Stage:
        '''the Stage instance belonging to this widget'''
        return self._stage

    def _update_com_ports(self):
        '''update the connection drop-down selector'''
        self._logger.debug("updating COM ports")
        self._connection_selector.clear()
        ports = self.stage.list_available_ports()
        self._connection_selector.addItem("rescan")
        self._connection_selector.addItems(ports)

    def _open_connection(self, *args):
        '''open a new connection'''
        port = self._connection_selector.currentText()

        if port.casefold() == "rescan":
            self._update_com_ports()

        else:
            self._logger.info(f"opening connection to {port}")
            self.stage.open_connection(port)
            self._axis_selector.setEnabled(True)
            self._update_axis_list()

    def _update_axis_list(self):
        '''update the axis drop-down selector'''
        self._logger.debug("updating axes list")
        self._axis_selector.clear()
        axis_list = self.stage.list_available_axes()
        self._axis_selector.addItem("rescan")
        self._axis_selector.addItems(axis_list)

    def _open_axis(self, *args):
        '''open a device an the current connection'''

        axis = self._axis_selector.currentText()

        if axis.casefold() == "rescan":
            self._update_axis_list()
        else:
            self._logger.info(f"setting axis to {axis}")
            axis_number = int(axis.split(':')[0].strip())
            self.stage.set_axis(axis_number)


class StageMonitor(QGroupBox):
    def __init__(self, parent: QWidget | None = None, stage: Stage | None = None) -> None:
        super().__init__("Axis Info", parent)
        self._logger = logging.getLogger(self.__class__.__name__)

        self._stage = stage or Stage()

        self._layout = QFormLayout(self)

        self._error_log = QListWidget(self)
        self._error_log.setMaximumHeight(
            4*self.fontMetrics().height())
        # self._error_log.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._layout.addRow(self._error_log)

        self._axis_busy = QLabel(" - ", self)
        self._layout.addRow("State", self._axis_busy)

        self._axis_position = QLabel(" N/A ° ", self)
        self._layout.addRow("Position", self._axis_position)

        # initally disabled bc no axis is connected
        self.setEnabled(False)

        # data refresh
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._update_axis_info)
        self._refresh_timer.start()

    def close(self) -> bool:
        self._refresh_timer.stop()
        return super().close()

    @property
    def stage(self) -> Stage:
        '''the Stage instance belonging to this widget'''
        return self._stage

    def _update_axis_info(self, *args):
        '''update the information pertaining to the given axis'''
        # self._logger.debug("updating axis info")

        axis_present = self.stage.axis is not None

        self.setEnabled(axis_present)

        if axis_present:
            err_code, err_msg = self.stage.error_status()
            if err_code != 0:
                self._error_log.addItem(err_msg)
                self._error_log.scrollToBottom()

            # axis is inverted --> add a '-' sign here
            position = -self.stage.get_position()
            self._axis_position.setText(f"{position}°")

            busy = self.stage.is_busy()
            self._axis_busy.setText('busy' if busy else 'idle')


class StageControl(QGroupBox):

    def __init__(self, parent: QWidget | None = None, stage: Stage | None = None) -> None:
        super().__init__("Axis Control", parent)
        self._logger = logging.getLogger(self.__class__.__name__)

        self._stage = stage or Stage()

        self._layout = QFormLayout(self)

        self._axis_enable_btn = QPushButton("Enable", self)
        self._axis_enable_btn.clicked.connect(self._enable_stage)
        self._layout.addRow("Enable", self._axis_enable_btn)
        self._axis_enable_btn.setCheckable(True)
        self._axis_enable_btn.setChecked(False)

        self._axis_home_btn = QPushButton("Home", self)
        self._axis_home_btn.pressed.connect(self._home)
        self._layout.addRow("Homing", self._axis_home_btn)

        self._axis_target_slider = QSlider(
            Qt.Orientation.Horizontal, self)
        self._axis_target_slider.setRange(0, 90)
        self._layout.addRow("Target", self._axis_target_slider)

        self._axis_move_btn = QPushButton("Move", self)
        self._axis_move_btn.pressed.connect(self._move)
        self._layout.addRow("Move", self._axis_move_btn)

        self._axis_stop_btn = QPushButton("STOP", self)
        self._axis_stop_btn.pressed.connect(self._stop)
        self._layout.addRow("", self._axis_stop_btn)
        self._axis_stop_btn.setDisabled(True)

        self._axis_target_slider.valueChanged.connect(
            lambda v: self._axis_move_btn.setText(f"Move to {v}°"))

        # initally disabled bc no axis is connected
        self.setEnabled(False)

        # data refresh
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._update_axis_info)
        self._refresh_timer.start()

        # error messages
        self._err_handler = QErrorMessage(self)

    def close(self) -> bool:
        self._refresh_timer.stop()
        return super().close()

    @property
    def stage(self) -> Stage:
        '''the Stage instance belonging to this widget'''
        return self._stage

    def _update_axis_info(self, *args):
        '''update the information pertaining to the given axis'''
        # self._logger.debug("updating axis info")

        axis_present = self.stage.axis is not None

        self.setEnabled(axis_present)

        if axis_present:
            self._axis_enable_btn.setChecked(self.stage.enabled())

            busy = self.stage.is_busy()
            self._axis_enable_btn.setDisabled(busy)
            self._axis_home_btn.setDisabled(busy)
            self._axis_move_btn.setDisabled(busy)
            self._axis_stop_btn.setDisabled(not busy)

    def _home(self, *args):
        if self.stage.axis is None:
            ermsg = "Cannot home. No axis set"
            self._err_handler.showMessage(ermsg)
            self._logger.error(ermsg)
            return

        self._logger.debug("initiating homing procedure")
        self.stage.goto_home()
        self.setDisabled(True)

    def _move(self, *args):
        if self.stage.axis is None:
            ermsg = "Cannot move. No axis set"
            self._err_handler.showMessage(ermsg)
            self._logger.error(ermsg)
            return

        self._logger.debug("initiating motion procedure")
        self.stage.goto_position(
            # axis is inverted --> add a '-' sign here
            -float(self._axis_target_slider.value())
        )
        self._axis_move_btn.setText("Move")
        self.setDisabled(True)

    def _stop(self, *args):
        if self.stage.axis is None:
            ermsg = "Cannot stop. No axis set"
            self._err_handler.showMessage(ermsg)
            self._logger.error(ermsg)
            return
        self._logger.debug("stopping motion!")
        self.stage.stop()

    def _enable_stage(self, enable: bool):
        self.stage.enable(enable)
