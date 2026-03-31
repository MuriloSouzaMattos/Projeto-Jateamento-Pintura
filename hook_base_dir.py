# hook_base_dir.py
# PyInstaller runtime hook — corrige o base_dir quando rodando como .exe
# O PyInstaller extrai os arquivos em sys._MEIPASS, não no diretório do .exe
# Este hook é aplicado automaticamente pelo .spec (runtime_hooks)

import sys
import os

if getattr(sys, 'frozen', False):
    # Rodando como executável PyInstaller
    # sys._MEIPASS = pasta temporária onde os dados são extraídos
    os.environ['APP_BASE_DIR'] = sys._MEIPASS
else:
    # Rodando normalmente como script Python
    os.environ['APP_BASE_DIR'] = os.path.dirname(os.path.abspath(__file__))
