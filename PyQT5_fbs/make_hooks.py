## This is only used for CircleCI to ensure thata a hook for utide is created
import os
import site

def main():
    fname = 'hook-utide.py'

    data =\
"""
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_data_files
hiddenimports = collect_submodules('utide')

datas = collect_data_files('utide')
"""



    for path in site.getsitepackages():
        print("Writing to",path)
        destination = os.path.join(path, 'PyInstaller', 'hooks')
        if os.path.exists(destination):
            with open(os.path.join(destination, fname), 'w') as f:
                f.write('{}'.format(data).strip())


if __name__ == '__main__':
    main()