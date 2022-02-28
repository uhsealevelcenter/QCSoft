# Sea Level Data Quality Control Software 

This is a GUI software developed by the University of Hawaii Sea Level Center.  

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Python 3.5 or 3.6 

[fbs - the packaging tool](https://github.com/mherrmann/fbs-tutorial), which produces standalone executibles on Windows, Mac, and Linux. For more 
details visit the project's [GitHub page ](https://github.com/mherrmann/fbs-tutorial) or the manual on the creator's 
[website](https://build-system.fman.io/manual/).

### Setup

Create a virtual environment:

```
python -m venv [your_env_name]
```

Activate the virtual environment:

```
# On Mac/Linux:
source [your_env_name]/bin/activate
# On Windows:
call [your_env_name]\scripts\activate.bat
```

### Prerequisites

The remainder of the tutorial assumes that the virtual environment is active.

Install the requirements using pip based on the OS you are working on:

```
# If working on a Mac
pip install -r requirements/mac.txt

# Similarly, on Windows:
pip install -r requirements/windows.txt
```

If you ever decide to add additional dependencies that are platform specific, you would add a dependency into the 
appropriate requirements/*.txt file. The platform independent dependencies should be added to base.txt. The base.txt 
file is referenced in each of the platform specific .txt files and thus pip install does not have to performed on it. 

### Running the software

The python source code is located in [src/main/python/](PyQT5_fbs/src/main/python/)

Run main.py to initiate GUI. Once started press F1 to bring the Help/Instructions menu.

### Changing the GUI

The GUI was designed using QT Designer. The designer produces a .ui file that is that converted to python code. The .ui
file is located at [src/main/python/stacked_design.ui](PyQT5_fbs/src/main/python/). 
The resulting .py file is located [uhslsdesign.py](PyQT5_fbs/src/main/python)

<strong>Important notes:</strong> 
QT Designer uses a custom matplotlib widget which was written to allow for dropping a graphing matplotlib widget in the ui. 
The matplotlib widget code is at QCSoft/PyQT5_fbs/src/main/python/MyQTDesignerPlugins/.

So far the custom widget only works on Windows. [See here](https://github.com/altendky/pyqt-tools/issues/12) for the status on other platforms.
To start the designer you must use pyqt5-tools and must start the designer from Your_Virt_Env\Scripts\pyqt5designer.exe. 
You might also have to run Your_Virt_Env\Scripts\pyqt5toolsinstalluic.exe to be able to display custom widgets in the QT Designer Widget Box tool.
And one last thing, you will have to tell QT Designer where the widget python files reside by setting up the PYQTDESIGNERPATH system variable 
to the folder where the widget files are located. For more info you can check out [this stackoverflow](https://stackoverflow.com/questions/47364804/qt5-matplotlib-designer-plugin)
answer. If everything is set up correctly, you will be able to see the custom plugin by clicking on Help > About Plugins. 

Once you have finished modifying UI changes saved the .ui file. To convert the .ui file to python, simply run pyuic5.exe your_file_name.ui -o output_name.py
Make sure output_name.py is importing the widget plugin as well, in our case this should be at the bottom of the
generated .py file:

from MyQTDesignerPlugins.matplotlibwidget import MatplotlibWidget


## Authors

* **Nemanja Komar** - *Initial work* - [Nems808](https://github.com/nems808)

See also the list of [contributors](https://github.com/nems808/QCSoft/contributors) who participated in this project.

## License



## Acknowledgments


