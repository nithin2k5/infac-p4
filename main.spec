# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('core', 'core'),
        ('ui', 'ui'),
    ],
    hiddenimports=[
        # OpenCV
        'cv2',
        # Pillow
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'PIL._imaging',
        # Networking
        'requests',
        'requests.adapters',
        'requests.auth',
        'urllib3',
        'urllib3.util.retry',
        'certifi',
        'charset_normalizer',
        'idna',
        # Numpy
        'numpy',
        'numpy.core',
        # Standard library (sometimes missed)
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        # Local packages
        'core',
        'core.camera',
        'core.inference',
        'core.inspection',
        'core.plc',
        'ui',
        'ui.theme',
        'ui.components',
        # pymodbus (Delta PLC Modbus TCP)
        'pymodbus',
        'pymodbus.client',
        'pymodbus.client.tcp',
        'pymodbus.framer',
        'pymodbus.pdu',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy ML libs — app uses Roboflow hosted API, no local model
        'torch',
        'torchvision',
        'tensorflow',
        'keras',
        'ultralytics',
        'sklearn',
        'scipy',
        'matplotlib',
        'pandas',
        'jupyter',
        'IPython',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='InfacP4',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed — no black console box on launch
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
