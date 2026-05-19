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
python -m pip install -r requirements/mac.txt

# Similarly, on Windows:
python -m pip install -r requirements/windows.txt
```

If you ever decide to add additional dependencies that are platform specific, you would add a dependency into the 
appropriate requirements/*.txt file. The platform independent dependencies should be added to base.txt. The base.txt 
file is referenced in each of the platform specific .txt files and thus pip install does not have to performed on it. 

#### station_tools
This software is heavily dependen on our [station_tools library](https://github.com/uhsealevelcenter/station_tools). If 
you need to make changes to the station_tools library and use those changes while developing the QS software, you will 
have to install it in editable mode. To do so, uninstall the station_tools library if it is already installed and then
run the following command from the project's root folder (PyQT5_fbs):
```
python -m pip install -e path_to_station_tools_folder
```
You will of course have to replace path_to_station_tools_folder with the actual path to where you checked out the 
station_tools repo.

#### Optional TimescaleDB / DB-backed workflows

This QCSoft branch can use optional DB-backed functionality from `uhslc_station_tools`, including DB overlay reads and save-time DB reconciliation/write hooks.

The standard file-based QC workflow still depends on `uhslc_station_tools`, but DB-backed functionality additionally requires the station-tools `db` extra.

For normal QCSoft setup, this is handled through:

```bash
python -m pip install -r requirements/mac.txt
```

or:

```bash
python -m pip install -r requirements/windows.txt
```

or:

```bash
python -m pip install -r requirements/linux.txt
```

depending on your platform.

If installing the station-tools dependency directly, use the same version pinned in `PyQT5_fbs/requirements/base.txt`.

##### DB configuration for installed QCSoft

DB credentials should not be committed to git and should not be bundled inside the QCSoft installer, DMG, `.app` bundle, source repo, or Python package.

For installed QCSoft use, place the real `.env_db` file in the standard OS config location for the machine.

macOS per-user:

```text
~/Library/Application Support/UHSLC-QC/.env_db
```

macOS system-wide:

```text
/Library/Application Support/UHSLC-QC/.env_db
```

Windows per-user:

```text
%APPDATA%\UHSLC-QC\.env_db
```

Windows system-wide:

```text
%ProgramData%\UHSLC-QC\.env_db
```

Linux per-user:

```text
~/.config/uhslc-qc/.env_db
```

Linux system-wide:

```text
/etc/uhslc-qc/.env_db
```

QCSoft loads DB credentials through `uhslc_station_tools.db.envfile.load_env_db()`. The lookup order is:

1. `TSDB_ENV_FILE`, if explicitly set
2. Per-user OS config location
3. System-wide OS config location
4. Legacy package-adjacent `.env_db` next to `uhslc_station_tools/db/envfile.py`

This allows packaged QCSoft installs to use DB credentials without storing secrets inside the packaged application.

##### Installing `.env_db` on macOS

For a normal per-user Mac install:

```bash
mkdir -p "$HOME/Library/Application Support/UHSLC-QC"
cp /path/to/real/.env_db "$HOME/Library/Application Support/UHSLC-QC/.env_db"
chmod 600 "$HOME/Library/Application Support/UHSLC-QC/.env_db"
```

For a system-wide Mac install:

```bash
sudo mkdir -p "/Library/Application Support/UHSLC-QC"
sudo cp /path/to/real/.env_db "/Library/Application Support/UHSLC-QC/.env_db"
sudo chmod 600 "/Library/Application Support/UHSLC-QC/.env_db"
```

After that, launch QCSoft normally from `/Applications`.

##### Installing `.env_db` on Windows

For a normal per-user Windows install, in PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:APPDATA\UHSLC-QC"
Copy-Item "C:\path\to\real\.env_db" "$env:APPDATA\UHSLC-QC\.env_db"
```

For a system-wide Windows install, in an administrator PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:ProgramData\UHSLC-QC"
Copy-Item "C:\path\to\real\.env_db" "$env:ProgramData\UHSLC-QC\.env_db"
```

##### Installing `.env_db` on Linux

For a normal per-user Linux install:

```bash
mkdir -p "$HOME/.config/uhslc-qc"
cp /path/to/real/.env_db "$HOME/.config/uhslc-qc/.env_db"
chmod 600 "$HOME/.config/uhslc-qc/.env_db"
```

For a system-wide Linux install:

```bash
sudo mkdir -p /etc/uhslc-qc
sudo cp /path/to/real/.env_db /etc/uhslc-qc/.env_db
sudo chmod 600 /etc/uhslc-qc/.env_db
```

##### Local DB configuration for development

For local development, copy the example DB environment file to a private location.

Option 1: use the same OS config location used by installed QCSoft.

macOS:

```bash
mkdir -p "$HOME/Library/Application Support/UHSLC-QC"
cp PyQT5_fbs/.env_db.example "$HOME/Library/Application Support/UHSLC-QC/.env_db"
chmod 600 "$HOME/Library/Application Support/UHSLC-QC/.env_db"
```

Linux:

```bash
mkdir -p "$HOME/.config/uhslc-qc"
cp PyQT5_fbs/.env_db.example "$HOME/.config/uhslc-qc/.env_db"
chmod 600 "$HOME/.config/uhslc-qc/.env_db"
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:APPDATA\UHSLC-QC"
Copy-Item "PyQT5_fbs\.env_db.example" "$env:APPDATA\UHSLC-QC\.env_db"
```

Then edit the copied `.env_db` with your local credentials.

Option 2: use `TSDB_ENV_FILE` as an explicit development override.

macOS/Linux:

```bash
cp PyQT5_fbs/.env_db.example PyQT5_fbs/.env_db
export TSDB_ENV_FILE="$PWD/PyQT5_fbs/.env_db"
```

Windows PowerShell:

```powershell
Copy-Item "PyQT5_fbs\.env_db.example" "PyQT5_fbs\.env_db"
$env:TSDB_ENV_FILE = "$PWD\PyQT5_fbs\.env_db"
```

`TSDB_ENV_FILE` is useful for development, testing, CI, and special deployments. Normal installed users should not need to set it.

Supported DB-related environment variables include:

* `TSDB_HOST`
* `TSDB_PORT`
* `TSDB_NAME`
* `TSDB_USER`
* `TSDB_PASSWORD`
* `TSDB_SSLMODE`
* `TSDB_LOG_SQL`
* `TSDB_LOG_DEBUG`
* `TSDB_EXECUTE_WRITES`
* `TSDB_BACKGROUND_HF_WRITES`
* `TSDB_OVERLAY_MAX_MONTHS`
* `TSDB_SAVE_GATE_WATCHDOG_MS`

The committed `.env_db.example` intentionally uses:

```env
TSDB_EXECUTE_WRITES=0
```

Set this to `1` only in a private local `.env_db` file when DB writes are intentionally enabled.

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

## Building package
In your terminal (with the virtual environment activated) navigate to the project's root folder (PyQT5_fbs) and run (for more info [fbs - the packaging tool](https://github.com/mherrmann/fbs-tutorial)):

```
fbs clean
fbs freeze
fbs installer
```

### Package freeze and build problems

Scipy and utide might not get picked up by the PyInstaller which would crash the app freezing process (when running fbs freeze). In order to fix this, you will have to navigate to the PyInstaller folder of your python interpretter (/python3.6/site-packages/PyInstaller/hooks) and add a file for each of the libraries that need to be imported and name them hook-[package-name].py. For utide library the contents of this file would look like this:
```python
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_data_files
hiddenimports=collect_submodules('utide')

datas=collect_data_files('utide')
```
See [this](https://stackoverflow.com/questions/51267453/scipy-import-error-with-pyinstaller) and [this](https://stackoverflow.com/questions/49559770/how-do-you-resolve-hidden-imports-not-found-warnings-in-pyinstaller-for-scipy?rq=1) on stack overflow for more info.

If you are on Ubuntu and you get an error message similar to this one when running fbs freeze:
```
Unable to find "/usr/include/python3.6m/pyconfig.h" when adding binary and data files.
```
You will have to run the following command:
```
sudo apt-get install libpython3.6-dev
```

You might also have to update hidden_imports inside of your /src/build/settings/base.json by adding the following:
```
{
    ... ,
    "hidden_imports": ["scipy", "utide", "some_other_package_that_you_added"]
}
```

If you run into issues with any other packages, you might have to list them inside of the /src/build/settings/base.json file.

## Authors

* **Nemanja Komar** - *Initial work* - [Nems808](https://github.com/nems808)

See also the list of [contributors](https://github.com/nems808/QCSoft/contributors) who participated in this project.

## License



## Acknowledgments



