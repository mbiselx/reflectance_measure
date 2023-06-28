from typing import TYPE_CHECKING

import logging
import pyqtgraph as pg
if TYPE_CHECKING:  # use the PyQt6 stubs for typechecking, as they are the nicest
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtWidgets import *
else:
    from pyqtgraph.Qt.QtCore import Qt, QTimer
    from pyqtgraph.Qt.QtWidgets import *

from reflectance_measure.stage.stage_utils import Stage, Units


class StageSelector(QFrame):

    def __init__(self, parent: QWidget | None = None, stage: Stage | None = None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(self.__class__.__name__)

        self._stage = stage or Stage()

        self._layout = QBoxLayout(QBoxLayout.Direction.TopToBottom, self)
        self.setLayout(self._layout)

        # create connection selection box
        self._connection_box = QGroupBox("Connection", self)
        self._layout.addWidget(self._connection_box)
        self._connection_layout = QFormLayout(self._connection_box)

        self._connection_selector = QComboBox(self._connection_box)
        self._connection_selector.activated.connect(self._open_connection)
        self._connection_layout.addRow("Port :", self._connection_selector)

        self._device_selector = QComboBox(self._connection_box)
        self._device_selector.setEnabled(False)
        self._device_selector.activated.connect(self._open_device)
        self._connection_layout.addRow("Device :", self._device_selector)

        self._axis_selector = QComboBox(self._connection_box)
        self._axis_selector.setEnabled(False)
        self._axis_selector.activated.connect(self._open_axis)
        self._connection_layout.addRow("Axis :", self._axis_selector)

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
        self._connection_selector.addItems(ports)
        self._connection_selector.addItem("rescan")

    def _open_connection(self, *args):
        '''open a new connection'''
        port = self._connection_selector.currentText()

        if port.casefold() == "rescan":
            self._update_com_ports()

        else:
            self._logger.info(f"opening connection to {port}")
            self.stage.open_connection(port)
            self._device_selector.setEnabled(True)
            self._update_device_list()

    def _update_device_list(self):
        '''update the device drop-down selector'''
        self._logger.debug("updating device list")
        self._device_selector.clear()
        device_list = self.stage.list_available_devices()
        self._device_selector.addItems(device_list)
        self._device_selector.addItem("rescan")

    def _open_device(self, *args):
        '''open a device an the current connection'''
        device = self._device_selector.currentText()

        if device.casefold() == "rescan":
            self._update_device_list()
        else:
            self._logger.info(f"setting device to {device}")
            device_address = int(device.split(':')[-1].strip())
            self.stage.set_device(device_address)
            self._axis_selector.setEnabled(True)
            self._update_axis_list()

    def _update_axis_list(self):
        '''update the axis drop-down selector'''
        self._logger.debug("updating axes list")
        self._axis_selector.clear()
        axis_list = self.stage.list_available_axes()
        self._axis_selector.addItems(axis_list)
        self._axis_selector.addItem("rescan")

    def _open_axis(self, *args):
        '''open a device an the current connection'''

        axis = self._axis_selector.currentText()

        if axis.casefold() == "rescan":
            self._update_axis_list()
        else:
            self._logger.info(f"setting axis to {axis}")
            axis_number = int(axis.split(':')[0].strip())
            self.stage.set_axis(axis_number)


class StageControl(QFrame):

    def __init__(self, parent: QWidget | None = None, stage: Stage | None = None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(self.__class__.__name__)

        self._stage = stage or Stage()

        self._layout = QBoxLayout(QBoxLayout.Direction.TopToBottom, self)
        self.setLayout(self._layout)

        # create axis data visualizer box
        self._axis_info_box = QGroupBox("Axis Info", self)
        self._axis_info_box.setEnabled(False)
        self._layout.addWidget(self._axis_info_box)
        self._axis_info_layout = QFormLayout(self._axis_info_box)

        self._axis_homed = QLabel(" - ", self._axis_info_box)
        self._axis_info_layout.addRow("Homed", self._axis_homed)

        self._axis_busy = QLabel(" - ", self._axis_info_box)
        self._axis_info_layout.addRow("State", self._axis_busy)

        self._axis_position = QLabel(" N/A ° ", self._axis_info_box)
        self._axis_info_layout.addRow("Position", self._axis_position)

        # create axis control box
        self._axis_ctrl_box = QGroupBox("Axis Info", self)
        # self._axis_ctrl_box.setEnabled(False)
        self._layout.addWidget(self._axis_ctrl_box)
        self._axis_ctrl_layout = QFormLayout(self._axis_ctrl_box)

        self._axis_home_btn = QPushButton("Home", self._axis_ctrl_box)
        self._axis_home_btn.pressed.connect(self._home)
        self._axis_ctrl_layout.addRow("Homing", self._axis_home_btn)

        self._axis_target_slider = QSlider(
            Qt.Orientation.Horizontal, self._axis_ctrl_box)
        self._axis_target_slider.setRange(-180, 180)
        self._axis_ctrl_layout.addRow("Target", self._axis_target_slider)

        self._axis_move_btn = QPushButton("Move", self._axis_ctrl_box)
        self._axis_move_btn.pressed.connect(self._move)
        self._axis_ctrl_layout.addRow("Move", self._axis_move_btn)

        self._axis_target_slider.valueChanged.connect(
            lambda v: self._axis_move_btn.setText(f"Move to {v}°"))

        # data refresh
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._update_axis_info)
        # self._refresh_timer.start()

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
        self._logger.debug("updating axis info")

        axis_present = self.stage.axis is not None

        self._axis_info_box.setEnabled(axis_present)
        self._axis_ctrl_box.setEnabled(axis_present)

        if axis_present:
            position = self.stage.axis.get_position(Units.ANGLE_DEGREES)
            self._axis_position.setText(f"{position}°")

            self._axis_homed.setText(
                "homed" if self.stage.axis.is_homed() else "not homed")

            busy = self.stage.axis.is_busy()
            self._axis_busy.setText('busy' if busy else 'idle')

            self._axis_home_btn.setDisabled(busy)
            self._axis_move_btn.setDisabled(busy)

    def _home(self, *args):
        if self.stage.axis is None:
            ermsg = "Cannot home. No axis set"
            self._err_handler.showMessage(ermsg)
            self._logger.error(ermsg)
            return

        self._logger.debug("initiating homing procedure")
        self.stage.axis.home(wait_until_idle=False)
        self._axis_ctrl_box.setDisabled(True)

    def _move(self, *args):
        if self.stage.axis is None:
            ermsg = "Cannot move. No axis set"
            self._err_handler.showMessage(ermsg)
            self._logger.error(ermsg)
            return

        self._logger.debug("initiating motion procedure")
        self.stage.axis.move_absolute(
            float(self._axis_target_slider.value()),
            Units.ANGLE_DEGREES,
            wait_until_idle=False
        )
        self._axis_move_btn.setText("Move")
        self._axis_ctrl_box.setDisabled(True)
