"""Helper script to run the Flet app in web mode for testing."""
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import flet as ft
from main import main

if __name__ == "__main__":
    ft.app(
        target=main,
        view=ft.AppView.WEB_BROWSER,
        port=8550,
    )
