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

If you ever decide to add additional dependencies that are platform specific, you would add a dependency into the , 
appropriate requirements/*.txt file. The platform independent dependencies should be added to base.txt. The base.txt 
file is referenced in each of the platform specific .txt files and thus pip install does not have to performed on it. 

### Running the sowtware

The python source code is located in [src/main/python/](PyQT5_fbs/src/main/python/)

Run main.py to initiate GUI. Once started press F1 to bring the Help/Instructions menu. 

## Authors

* **Nemanja Komar** - *Initial work* - [Nems808](https://github.com/nems808)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License



## Acknowledgments



