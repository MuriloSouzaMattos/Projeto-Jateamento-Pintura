# MedicaoCamadas.spec
# Gerado para PyInstaller 6.x
# Coloque este arquivo na raiz do projeto (mesma pasta do main.py)
# e rode:  pyinstaller MedicaoCamadas.spec

import sys
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    # Inclui a pasta Images e todos os arquivos de dados locais
    datas=[
        ('Images',       'Images'),   # pasta inteira de imagens
        ('ble.py',       '.'),        # módulo BLE local
        ('repo.py',      '.'),        # módulo de repositório
        ('exporter.py',  '.'),        # módulo de exportação
    ],
    hiddenimports=[
        # qasync / asyncio
        'qasync',
        # bleak (BLE) — importa muita coisa dinamicamente
        'bleak',
        'bleak.backends.winrt.client',
        'bleak.backends.winrt.scanner',
        'bleak.backends.winrt.util',
        # PySide6
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        # openpyxl / xlsxwriter (dependendo do exporter.py)
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MedicaoCamadas',          # nome do .exe gerado
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                  # False = sem janela de terminal
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='Images\\icone.ico',     # descomente e ajuste se tiver um ícone .ico
)
