from typing import TYPE_CHECKING

import logging
import pyqtgraph as pg
if TYPE_CHECKING:  # use the PyQt6 stubs for typechecking, as they are the nicest
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtWidgets import *
else:
    from pyqtgraph.Qt.QtCore import Qt, QTimer
    from pyqtgraph.Qt.QtWidgets import *

from reflectance_measure.daq.daq_utils import DAQ


class DAQSelector(QGroupBox):
    def __init__(self, parent: QWidget | None = None, daq: DAQ | None = None) -> None:
        super().__init__("Connection", parent)
        self._logger = logging.getLogger(self.__class__.__name__)

        self._daq = daq or DAQ()

        self._layout = QFormLayout(self)

        self._device_selector = QComboBox(self)
        self._device_selector.activated.connect(self._set_device)
        self._layout.addRow("Device :", self._device_selector)

        self._channel_selector = QComboBox(self)
        self._channel_selector.setEnabled(False)
        self._channel_selector.activated.connect(self._set_channel)
        self._layout.addRow("Channel :", self._channel_selector)

        # update the listed devices
        self._update_device_list()

    @property
    def daq(self) -> DAQ:
        '''the DAQ instance belonging to this widget'''
        return self._daq

    def _update_device_list(self):
        '''update the device drop-down selector'''
        self._logger.debug("updating device list")
        self._device_selector.clear()
        device_list = self.daq.list_available_devices()
        self._device_selector.addItems(device_list)
        self._device_selector.addItem("rescan")

    def _set_device(self, *args):
        '''open a device'''
        device = self._device_selector.currentText()

        if device.casefold() == "rescan":
            self._update_device_list()
        else:
            self._logger.info(f"setting device to {device}")
            self.daq.set_device(device)
            self._channel_selector.setEnabled(True)
            self._update_channel_list()

    def _update_channel_list(self):
        '''update the channel drop-down selector'''
        self._logger.debug("updating channel list")
        self._channel_selector.clear()
        device_list = self.daq.list_analog_input_channels()
        self._channel_selector.addItems(device_list)
        self._channel_selector.addItem("rescan")

    def _set_channel(self, *args):
        channel = self._channel_selector.currentText()

        if channel.casefold() == "rescan":
            self._update_channel_list()
        else:
            self._logger.info(f"setting axis to {channel}")
            self.daq.set_channel(channel)


class DAQMonitor(QGroupBox):
    def __init__(self, parent: QWidget | None = None, daq: DAQ | None = None) -> None:
        super().__init__("Channel Info", parent)
        self._logger = logging.getLogger(self.__class__.__name__)

        self._daq = daq or DAQ()

        self._layout = QFormLayout(self)

        self._channel_voltage = QLabel(" - ", self)
        self._layout.addRow("Voltage", self._channel_voltage)

        # initally disabled bc no channel is connected
        self.setEnabled(False)

        # data refresh
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(500)
        self._refresh_timer.timeout.connect(self._update_channel_info)

    @property
    def daq(self) -> DAQ:
        '''the DAQ instance belonging to this widget'''
        return self._daq

    def close(self) -> bool:
        self._refresh_timer.stop()
        return super().close()

    def _update_channel_info(self, *args):
        '''update the information pertaining to the given channel'''
        self._logger.debug("updating channel info")

        channel_present = self.daq.channel is not None
        self.setEnabled(channel_present)

        if channel_present:
            voltage = self.daq.read_channel()
            self._channel_voltage.setText(f"{voltage:.2f} V")
