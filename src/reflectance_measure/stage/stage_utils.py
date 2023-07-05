import typing
import logging

from serial import Serial
from serial.tools.list_ports import comports


class ESP301_Connection(Serial):
    def __init__(self, port: str | None = None, timeout: float = 0.1) -> None:
        super().__init__(port=port,
                         baudrate=19200,
                         bytesize=8,
                         parity="N",
                         stopbits=1,
                         timeout=timeout,
                         rtscts=True
                         )

    def command(self, command: str):
        self.write(f"{command}\r\n".encode("ascii"))

    def response(self) -> bytes:
        response = self.readline().removesuffix(b'\r\n')
        return response


class Stage:
    def __init__(self, port: str | None = None, axis_number: int | None = None) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self._connection: ESP301_Connection | None = None
        self._axis: int | None = None

        if port is not None:
            self.open_connection(port)
        if axis_number is not None:
            self.set_axis(axis_number)

    @staticmethod
    def list_available_ports() -> list[str]:
        '''return a list of all available COM ports on this PC'''
        return list(p.name for p in comports())

    def list_available_axes(self) -> list[str]:
        '''return a list of all available axes on this connection'''
        if self._connection is None:
            raise ConnectionError("Cannot get a connection to list devices on")

        axes = []
        for i in range(1, 4):
            self.connection.command(f"{i}ID?")
            resp = self.connection.response()
            if resp.lower() != b"unknown":
                axes.append(f"{i} : {resp.decode('ascii')}")

        return axes

    def close(self):
        '''gracefully shut down the connection to the current device'''
        self._logger.debug("closing stage")
        try:
            self.stop()
            self.disable()
        except RuntimeError:
            pass
        finally:
            if self._axis:
                self._axis = None
            if self._connection:
                self.connection.close()

    @property
    def connection(self) -> ESP301_Connection | None:
        '''the connection used to communicate with the stage device'''
        return self._connection

    def open_connection(self, port: str):
        '''open the COM port on which the stage is located'''
        self.close()
        self._logger.debug(f"opening connection to {port}")
        self._connection = ESP301_Connection(port)

    @property
    def axis(self) -> int | None:
        '''the axis of the stage'''
        return self._axis

    def set_axis(self, axis_number: int):
        '''set the axis of the stage'''
        self._axis = None
        self._logger.debug(f"setting axis to {axis_number}")
        if not isinstance(axis_number, int):
            raise TypeError(
                f"axis number must be int, not {type(axis_number)}")
        if self._connection is None:
            raise RuntimeError(
                "no connection set. cannot set the requested axis")
        if not (1 <= axis_number <= 3):
            raise ValueError("axis number must be between 1 and 3")

        # check that the axis is really there
        self.connection.command(f"{axis_number}ID?")
        if self.connection.response().lower() == b"unknown":
            raise RuntimeError("No such axis available")

        self._axis = int(axis_number)

    def __enter__(self):
        '''context manager to make sure connection is properly closed'''
        return self

    def __exit__(self, *args):
        self.close()

    def _connection_check(self):
        if not self.connection:
            raise RuntimeError("No connection set")
        if not self.axis:
            raise RuntimeError("No axis set")

    def enable(self, enable: bool = True):
        self._connection_check()
        self.connection.command(f"{self._axis}M{'O' if enable else 'F'}")

    def disable(self, disable: bool = True):
        self.enable(not disable)

    def enabled(self) -> bool:
        self._connection_check()
        self.connection.command(f"{self._axis}MO?")
        return bool(int(self.connection.response()))

    def goto_home(self):
        self._connection_check()
        self.connection.command(f"{self._axis}OR")

    def is_busy(self) -> bool:
        self._connection_check()
        self.connection.command(f"TS")
        resp = int.from_bytes(self.connection.response())
        return bool((resp >> (self._axis - 1)) & 1)

    def get_position(self) -> float:
        self._connection_check()
        self.connection.command(f"{self._axis}PA?")
        return float(self.connection.response())

    def goto_position(self, pos: float):
        self._connection_check()
        self.connection.command(f"{self._axis}PA{pos:.4f}")

    def get_velocity(self) -> float:
        self._connection_check()
        self.connection.command(f"{self._axis}VA?")
        return float(self.connection.response())

    def stop(self):
        self._connection_check()
        self.connection.command(f"{self._axis}ST")

    def error_status(self) -> tuple[int, str]:
        self._connection_check()
        self.connection.command(f"TB")
        err_code, _, err_msg = self.connection.response().split(b", ")
        return int(err_code), err_msg.decode("ascii")

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

        while True:
            try:
                exec(input(">>> "))
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(e)
            time.sleep(.1)


if __name__ == "__main__":
    main()
