from typing import TYPE_CHECKING

import csv
import time
import logging

import winsound
import numpy as np
if TYPE_CHECKING:  # use the PyQt6 stubs for typechecking,
    # as they are the nicest
    from PyQt6.QtCore import QObject, QThread, pyqtSignal as Signal
    from PyQt6.QtWidgets import (QWidget, QFrame, QBoxLayout, QGroupBox,
                                 QFormLayout, QDoubleSpinBox, QSpinBox,
                                 QVBoxLayout, QCheckBox, QPushButton,
                                 QErrorMessage, QFileDialog)
else:
    from pyqtgraph.Qt.QtCore import QObject, QThread, Signal
    from pyqtgraph.Qt.QtWidgets import (QWidget, QFrame, QBoxLayout, QGroupBox,
                                        QFormLayout, QDoubleSpinBox, QSpinBox,
                                        QVBoxLayout, QCheckBox, QPushButton,
                                        QErrorMessage, QFileDialog)

from reflectance_measure.stage.stage_utils import Stage
from reflectance_measure.daq.daq_utils import DAQ


class ExperimentAutomation(QObject):
    sig_measurement_finished = Signal()
    sig_measurement_failed = Signal(Exception)
    sig_measurement_added = Signal(tuple)

    def __init__(self, parent: QObject | None = None,
                 stage: Stage | None = None, daq: DAQ | None = None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(self.__class__.__name__)

        self._stage = stage or Stage()
        self._daq = daq or DAQ()

        self.start_angle = 0.
        self.end_angle = 90.
        self.increment_angle = 1.

        self.nb_measurements: int = 1
        self.measurement_interval = 1.

        self.save_file: str | None = None

        self._measurements = []

    @property
    def measurements(self) -> list[tuple[float, float]]:
        '''last measurements taken'''
        return self._measurements

    def set_start_angle(self, value: float):
        self.start_angle = value

    def set_end_angle(self, value: float):
        self.end_angle = value

    def set_increment_angle(self, value: float):
        self.increment_angle = value

    def set_nb_measurements(self, value: int):
        self.nb_measurements = value

    def set_measurement_interval(self, value: float):
        self.measurement_interval = value

    def set_save_file(self, filename: str):
        self.save_file = filename

    @staticmethod
    def catch_exception(func):
        def _func(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                self._logger.exception(e)
                self.sig_measurement_failed.emit(e)
        return _func

    @catch_exception
    def do_measurement(self, homing: bool = True):
        '''
        blocking routine to perform the measurements, and save
        them in the `measurements` property.
        emits the `sig_measurement_finished` signal when it is done.
        '''
        self._logger.debug("starting measurement routine")

        # enable motor if required
        if not self._stage.enabled():
            self._logger.debug("enabling motor")
            self._stage.enable()

        # do homing if required
        if homing:
            self._logger.debug("initiating homeing")
            self._stage.goto_home()
        # make sure the stage is stationary before continuing
        self._stage.wait_until_done()

        # reset the list to contain measurements
        self._measurements = []

        # prepare measurement angles list
        angles = np.arange(
            self.start_angle,
            self.end_angle + self.increment_angle/10,
            self.increment_angle
        )

        # do measurements at each angle
        last_save_time = time.time()
        for angle in angles:
            self._logger.debug(f"{angle=}°deg")
            self._stage.goto_position(-angle)
            self._stage.wait_until_done()
            # time.sleep(min(1, self.increment_angle*5))

            for i in range(self.nb_measurements):
                self._logger.debug(f"measurement {i}")
                value = self._daq.read_channel()
                self._measurements.append((angle, value))
                self.sig_measurement_added.emit((angle, value))

                if i + 1 < self.nb_measurements:
                    time.sleep(self.measurement_interval)

            if self.save_file and (time.time() - last_save_time > 1):
                with open(self.save_file, 'w') as file:
                    writer = csv.writer(file, lineterminator='\n')
                    writer.writerow(["angle [deg]", "intensity [V]"])
                    writer.writerows(self.measurements)

        self.sig_measurement_finished.emit()


class ExperimentAutomationWidget(QFrame):
    sig_experiment_started = Signal()
    sig_experiment_finished = Signal()
    sig_measurement_added: Signal

    def __init__(self, parent: QWidget | None = None,
                 stage: Stage | None = None, daq: DAQ | None = None):
        super().__init__(parent)
        self._logger = logging.getLogger(self.__class__.__name__)

        self._t = QThread(self)

        self._ea = ExperimentAutomation(stage=stage, daq=daq)
        self._ea.moveToThread(self._t)
        self._ea.sig_measurement_finished.connect(self._measurement_done)
        self._ea.sig_measurement_failed.connect(self._measurement_failed)
        self.sig_measurement_added = self._ea.sig_measurement_added

        # layout
        self._layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.setLayout(self._layout)

        # layout - parameter box
        self._params_box = QGroupBox("Parameters", self)
        self._params_box.setLayout(QFormLayout())
        self._layout.addWidget(self._params_box)

        self._start_angle = QDoubleSpinBox(self._params_box)
        self._start_angle.setRange(0., 90.)
        self._start_angle.setValue(self._ea.start_angle)
        self._params_box.layout().addRow("start angle", self._start_angle)
        self._start_angle.valueChanged.connect(self._ea.set_start_angle)

        self._end_angle = QDoubleSpinBox(self._params_box)
        self._end_angle.setRange(0., 90.)
        self._end_angle.setValue(self._ea.end_angle)
        self._params_box.layout().addRow("end angle", self._end_angle)
        self._end_angle.valueChanged.connect(self._ea.set_end_angle)

        self._angle_increment = QDoubleSpinBox(self._params_box)
        self._angle_increment.setRange(0.01, 90.)
        self._angle_increment.setValue(self._ea.increment_angle)
        self._params_box.layout().addRow("angle increment",
                                         self._angle_increment)
        self._angle_increment.valueChanged.connect(
            self._ea.set_increment_angle)

        self._nb_measurements = QSpinBox(self._params_box)
        self._nb_measurements.setValue(self._ea.nb_measurements)
        self._params_box.layout().addRow("nb measurements",
                                         self._nb_measurements)
        self._nb_measurements.valueChanged.connect(
            self._ea.set_nb_measurements)

        self._measurement_interval = QDoubleSpinBox(self._params_box)
        self._measurement_interval.setValue(self._ea.measurement_interval)
        self._params_box.layout().addRow("measurement interval",
                                         self._measurement_interval)
        self._measurement_interval.valueChanged.connect(
            self._ea.set_measurement_interval)

        # layout - startbutton
        self._startbutton_box = QFrame(self)
        self._startbutton_box.setLayout(QVBoxLayout())
        self._layout.addWidget(self._startbutton_box)

        self._save_file_checkbox = QCheckBox(
            "save to file", self._startbutton_box)
        self._startbutton_box.layout().addWidget(self._save_file_checkbox)
        self._save_file_checkbox.setChecked(self._ea.save_file is not None)
        self._save_file_checkbox.toggled.connect(self._set_save_file)

        self._play_sound_checkbox = QCheckBox(
            "play sound when done", self._startbutton_box)
        self._startbutton_box.layout().addWidget(self._play_sound_checkbox)
        self._play_sound_checkbox.setChecked(True)

        self._start_button = QPushButton("start", self._startbutton_box)
        self._startbutton_box.layout().addWidget(self._start_button)
        self._start_button.pressed.connect(self._measurement_started)
        self._start_button.pressed.connect(self._ea.do_measurement)

        self._cancel_button = QPushButton("cancel", self._startbutton_box)
        self._startbutton_box.layout().addWidget(self._cancel_button)
        self._cancel_button.pressed.connect(self._cancel_measurement)
        self._cancel_button.setDisabled(True)

        # error msg
        self._error_handler = QErrorMessage(self)

    def _measurement_started(self):
        self._logger.info("starting measurement")
        self._t.start()
        self._params_box.setDisabled(True)
        self._start_button.setDisabled(True)
        self._cancel_button.setEnabled(True)
        self._save_file_checkbox.setDisabled(True)
        self.sig_experiment_started.emit()

    def _measurement_done(self):
        self._logger.info("measurement finished")
        self._t.terminate()
        self._params_box.setEnabled(True)
        self._start_button.setEnabled(True)
        self._cancel_button.setDisabled(True)
        self._save_file_checkbox.setEnabled(True)
        self._save_file_checkbox.setChecked(False)

        if self._play_sound_checkbox.isChecked():
            winsound.Beep(1320, 500)

        self.sig_experiment_finished.emit()

    def _cancel_measurement(self):
        self._t.terminate()
        try:
            self._ea._stage.stop()
            self._logger.info("measurement cancelled")
        except Exception as e:
            ermsg = f"Failed to stop the motor. {e.__class__.__name__} : {e}"
            self._error_handler.showMessage(ermsg)
            self._logger.error(ermsg)

        self._measurement_done()

    def _measurement_failed(self, reason: Exception):
        ermsg = "Failed to run experiment. " +\
            f"{reason.__class__.__name__} : {reason}"
        self._error_handler.showMessage(ermsg)
        self._logger.error(ermsg)

        self._measurement_done()

    def _set_save_file(self, *args):
        if self._save_file_checkbox.isChecked():

            self._ea.save_file, _ = QFileDialog.getSaveFileName(
                self,
                "set measurement save destination",
                filter="CSV(*.csv)",
            )
            if self._ea.save_file in ("", None):
                self._ea.save_file = None
                self._save_file_checkbox.setChecked(False)
        else:
            self._ea.save_file = None

    def close(self) -> None:
        self._t.terminate()
        return super().close()
