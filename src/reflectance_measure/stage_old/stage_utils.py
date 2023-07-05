import typing
import logging

from serial.tools.list_ports import comports

from zaber_motion import Units
from zaber_motion.ascii import Connection, Device, Axis

__all__ = [
    "Stage",
    "Units"
]


class Stage:
    def __init__(self, port: str | None = None, device_address: int | None = None, axis_number: int | None = None) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._connection: Connection | None = None
        self._device: Device | None = None
        self._axis: Axis | None = None

        if port is not None:
            self.open_connection(port)
        if device_address is not None:
            self.set_device(device_address)
        if axis_number is not None:
            self.set_axis(axis_number)

    @staticmethod
    def list_available_ports() -> list[str]:
        '''return a list of all available COM ports on this PC'''
        return list(p.name for p in comports())

        ...

    @typing.overload
    def list_available_devices(self) -> list[str]:
        '''return a list of all available devices on the same COM port as this device'''
        ...

    @typing.overload
    @staticmethod
    def list_available_devices(port: str) -> list[str]:
        '''return a list of all available devices on the selected COM port'''

    def list_available_devices(self_or_port: 'Stage | str') -> list[str]:
        if isinstance(self_or_port, Stage):
            con = self_or_port._connection
        elif isinstance(self_or_port, str):
            con = Connection.open_serial_port(self_or_port)
        else:
            con = None

        if con is None:
            raise ConnectionError("Cannot get a connection to list devices on")

        return list(f"{d.name} : {d.device_address}" for d in con.detect_devices())

    @typing.overload
    def list_available_axes(self) -> list[str]:
        '''return a list of all available axes on this device'''
        ...

    @typing.overload
    @staticmethod
    def list_available_axes(port: str, device_address: int) -> list[str]:
        '''return a list of all available axes on the selected device'''
        ...

    def list_available_axes(self_or_port: 'Stage | str', device_address: int | None = None) -> list[str]:
        if isinstance(self_or_port, Stage):
            dev = self_or_port._device
            if device_address is not None:
                raise ValueError(
                    "cannot specify device when calling as instance method")
        elif isinstance(self_or_port, str):
            if not isinstance(device_address, int):
                raise ValueError(
                    "must specify device_address as (int) when calling as static method")
            con = Connection.open_serial_port(self_or_port)
            dev = con.get_device(device_address)
        else:
            dev = None

        if dev is None:
            raise ConnectionError("Cannot connect to the device")

        return list(f"{a} : {dev.get_axis(a).axis_type}" for a in range(dev.axis_count))

    def close(self):
        '''gracefully shut down the connection to the current device'''
        self._logger.debug("closing stage")
        if self._axis:
            self._axis = None
        if self._device:
            self._device = None
        if self._connection:
            self._connection.close()

    @property
    def connection(self) -> Connection | None:
        '''the connection used to communicate with the stage device'''
        return self._connection

    def open_connection(self, port: str):
        '''open the COM port on which the stage is located'''
        self.close()
        self._logger.debug(f"opening connection to {port}")
        self._connection = Connection.open_serial_port(port)

    @property
    def device(self) -> Device | None:
        '''the device on which the stage is located'''
        return self._device

    def set_device(self, device_address: int):
        '''set the device address of the stage'''
        self._axis = None
        self._device = None
        self._logger.debug(f"setting device to {device_address}")
        if self._connection is None:
            raise RuntimeError(
                "no connection open. cannot get the requested device")
        self._device = self._connection.get_device(device_address)

    @property
    def axis(self) -> Axis | None:
        '''the axis of the stage'''
        return self._axis

    def set_axis(self, axis_number: int):
        '''set the axis of the stage'''
        self._axis = None
        self._logger.debug(f"setting axis to {axis_number}")
        if self._device is None:
            raise RuntimeError(
                "no device set. cannot get the requested axis")
        self._axis = self._device.get_axis(axis_number)

    def __enter__(self):
        '''context manager to make sure connection is properly closed'''
        return self

    def __exit__(self, *args):
        self.close()

    def interactive_setup(self):
        '''interactively set up a Stage object, using command-line prompts for input'''

        # find out which COM port are available
        print("The following COM ports have been detected : ")
        ports = self.list_available_ports()
        if len(ports):
            print(*ports, sep='\n')
        else:
            raise RuntimeError(
                "No COM ports detected -- make sure your device is connected and powered on")

        # open connection to stage
        port = input("which COM port would you like to use ? (int) ")
        if not port.isnumeric():
            raise TypeError("expected a COM port number")
        self.open_connection(f"COM{port}")

        # find out which devices are available
        devices = self.list_available_devices()
        if len(devices):
            print(*devices, sep='\n')
        else:
            raise RuntimeError("No devices detected")

        # open connection to device
        device_address = input(
            "which device address would you like to use ? (int) ")
        if not device_address.isnumeric():
            raise TypeError("expected a device address number")
        self.set_device(int(device_address))

        # find out which axes are available
        axes = self.list_available_axes()
        if len(axes):
            print(*axes, sep='\n')
        else:
            raise RuntimeError("No axes detected")

        # open connection to axis
        axis_number = input(
            "which axis would you like to use ? (int) ")
        if not axis_number.isnumeric():
            raise TypeError("expected an axis number")
        self.set_axis(int(axis_number))


def main():
    import time

    with Stage() as stage:
        # do setup
        stage.interactive_setup()

        # sanity check
        assert stage.axis is not None

        # output current position
        position = stage.axis.get_position(Units.ANGLE_DEGREES)
        print(f"current axis position : {position}°")

        # should we home the axis ?
        goto_home = input("initiate homeing ? (Y/N) ")
        if goto_home == "Y":
            stage.axis.home(wait_until_idle=True)

        while True:
            time.sleep(0.2)

            # output current position again
            position = stage.axis.get_position(Units.ANGLE_DEGREES)
            print(f"current axis position : {position}°")

            # check if the axis is currently in use
            if stage.axis.is_busy():
                continue

            # lets move the axis, if we can
            goto_where = input("move where ? (deg) ")

            if goto_where.isnumeric():  # destination
                stage.axis.move_absolute(
                    float(goto_where),
                    Units.ANGLE_DEGREES,
                    wait_until_idle=False
                )

            elif goto_where == "H":  # home
                stage.axis.home(wait_until_idle=False)

            elif goto_where == "Q":  # quit
                break


if __name__ == "__main__":
    main()
