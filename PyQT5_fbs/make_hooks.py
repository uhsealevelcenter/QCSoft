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
        destination = os.path.join(path, 'PyInstaller', 'hooks')
        if os.path.exists(destination):
            print("Writing to", destination)
            with open(os.path.join(destination, fname), 'w') as f:
                f.write('{}'.format(data).strip())

            assert os.path.exists(os.path.join(destination, fname))
        else:
            print("This path does not exist", destination)

if __name__ == '__main__':
    main()