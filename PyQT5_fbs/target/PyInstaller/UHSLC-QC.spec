# -*- mode: python -*-

block_cipher = None


a = Analysis(['../../src/main/python/main.py'],
             pathex=['/Users/nemanjakomar/Dropbox/UHSLC/QCSoft/PyQT5_fbs/target/PyInstaller'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='UHSLC-QC',
          debug=False,
          strip=False,
          upx=False,
          console=False , icon='/Users/nemanjakomar/Dropbox/UHSLC/QCSoft/PyQT5_fbs/target/Icon.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='UHSLC-QC')
app = BUNDLE(coll,
             name='UHSLC-QC.app',
             icon='/Users/nemanjakomar/Dropbox/UHSLC/QCSoft/PyQT5_fbs/target/Icon.icns',
             bundle_identifier='com.uhslc.qcsoft')
