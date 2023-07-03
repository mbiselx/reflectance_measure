import logging

from nidaqmx import Task
from nidaqmx.system import System, Device, PhysicalChannel


class DAQ:
    def __init__(self) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)

        self._task: Task | None = None

        self._device: Device | None = None
        self._channel: PhysicalChannel | None = None

    @property
    def task(self) -> Task | None:
        '''the currently running task'''
        return self._task

    @staticmethod
    def list_available_devices() -> list[str]:
        '''list all devices on the local system'''
        local_sys = System.local()
        return list(d.name for d in local_sys.devices)

    @property
    def device(self) -> Device | None:
        '''the device on which the DAQ is located'''
        return self._device

    def set_device(self, device_name: str):
        '''set the device (expects sth like `Dev1`)'''
        # close old task
        if self._task is not None:
            self._task.close()
            self._task = None
        self._channel = None

        self._device = Device(device_name)

    def list_analog_input_channels(self) -> list[str]:
        '''list all analog input channels on the current device'''
        if self._device is None:
            raise ConnectionError("Cannot connect to the device")
        return list(c.name for c in self._device.ai_physical_chans)

    @property
    def channel(self) -> PhysicalChannel | None:
        '''the analog input channel to use for this DAQ'''
        return self._channel

    def set_channel(self, channel_name: str):
        '''set the channel (expects sth like `ai0` or `Dev1/ai0`)'''
        if self.device is None:
            if "/" not in channel_name:
                raise RuntimeError("no device specified")

            device_name, channel_name = channel_name.split('/')
            self.set_device(device_name)

        self._channel = self.device.ai_physical_chans[channel_name]

        # close old task
        if self._task is not None:
            self._task.close()
        self._task = Task()

        # add the new channel
        self._task.ai_channels.add_ai_voltage_chan(
            self._channel.name,
            min_val=-10,
            max_val=10
        )

        # self.task.start()

    def read_channel(self) -> float:
        if self.task is None:
            raise RuntimeError("No channel set")
        return self.task.read(timeout=.1)

    def close(self):
        '''gracefully shut down the connection to the current device'''
        self._logger.debug("closing DAQ")
        if self._task is not None:
            self._task.close()
            self._task = None

    def __enter__(self):
        '''context manager to make sure connection is properly closed'''
        return self

    def __exit__(self, *args):
        self.close()

    def interactive_setup(self):

        # find out which devices are available :
        print("The following DAQ devices have been detected : ")
        devices = self.list_available_devices()
        if len(devices):
            print(*devices, sep='\n')
        else:
            raise RuntimeError(
                "No devices detected -- make sure your device is connected and powered on")

        # open connection to device
        device_name = input("which device would you like to use ? (str) ")
        if not device_name.isalnum():
            raise ValueError("expected a device name")
        self.set_device(device_name)

        # find out which channels are available
        ai_channels = self.list_analog_input_channels()
        if len(ai_channels):
            print(*ai_channels, sep='\n')
        else:
            raise RuntimeError("No analog input channels detected")

        # select the input channel
        channel_number = input(
            "which analong input channel would you like to use ? (int) ")
        if not channel_number.isnumeric():
            raise TypeError("expected a channel number")
        self.set_channel(f'ai{channel_number}')


def main():
    import time

    with DAQ() as daq:
        # do setup
        daq.interactive_setup()

        # sanity check
        assert daq.channel is not None
        assert daq.task is not None

        while True:
            time.sleep(0.2)

            # output current channel value
            v = daq.read_channel()
            print(f"current voltage level : {v:.3f}V")


if __name__ == "__main__":
    main()
