# Reflectance Measure

The following is a small app for running reflectance measurements on a sample, using the **NI USB-6002 Data Acquisition (DAQ)** device and the ~~**Zaber X-RSW60C Motorized rotary stage**~~ **Newpoert ESP301 Motion Controller + URS150BPP**. 

**IMPORTANT NOTE**: all angles are reversed with respect to the device's reference. This means that a command of 45° will send the device to -45°.

## Usage
The app has two interfaces : 
 1. [GUI](./src/reflectance_measure/gui.py) : can be launched with `python -m reflectance_measure.gui`
 2. [CLI](./src/reflectance_measure/headless.py) : can be launched with `python -m reflectance_measure.headless`

![Screenshot 2023-08-21 172938](https://github.com/mbiselx/reflectance_measure/assets/62802642/8ce9c5b7-2363-4e5b-910a-bf02e38fd8c5)


## Installation
The app has only been tested on Windows, it seems unlikely that it will work on another operating system. 

To install and run the app, the following prerequisites must be met: 
 - A Python version >= 3.10 must be installed
 - A Qt binding for Python should be installed (ideally PyQt6: `pip install PyQt6`)

If you want the app to be in Dark-Mode, you'll need the QDarkTheme package (`pip install pyqtdarktheme`). 

Then, clone this repo and install it to your Python path. Use the `-e` option to make the install "editable", so you can change the code in the repo and re-run it without having to reinstall it: 
```
git clone https://github.com/mbiselx/reflectance_measure.git
pip install -e .\reflectance_measure\
```
