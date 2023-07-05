import time

from reflectance_measure.stage_old.stage_utils import Stage
from reflectance_measure.daq.daq_utils import DAQ


with DAQ() as daq, Stage() as stage:
    try:
        stage.interactive_setup()
    except RuntimeError as e:
        print(e)
        print("skipping stage setup")

    try:
        daq.interactive_setup()
    except RuntimeError as e:
        print(e)
        print("skipping stage setup")

    # while stage.axis or daq.channel:
    while True:
        try:
            exec(input(">>> "))
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(e)
        time.sleep(.1)
