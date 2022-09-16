# This ensures that the unittests can by run from the command line (fixes module import issues)
import os
import sys
PROJECT_PATH = os.getcwd()
SOURCE_PATH = os.path.join(
    PROJECT_PATH,"PyQT5_fbs/src/main/python"
)
sys.path.append(SOURCE_PATH)