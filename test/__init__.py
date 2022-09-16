# This ensures that the unittests can by run from the command line (fixes module import issues)
import os
import sys

import matplotlib

PROJECT_PATH = os.getcwd()
SOURCE_PATH = os.path.join(
    PROJECT_PATH,"PyQT5_fbs/src/main/python"
)
sys.path.append(SOURCE_PATH)

if os.environ.get('DISPLAY', '') == '':
    print('No display found. Using non-interactive Agg backend.')
    matplotlib.use('Agg')