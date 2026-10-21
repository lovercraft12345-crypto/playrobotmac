"""Shared type and color choices; use a scalable native font on each platform."""
import sys
from pathlib import Path


def load_private_fonts():
    """Make the included display font available only to this Windows process."""
    if sys.platform == 'win32':
        try:
            import ctypes
            font = Path(__file__).resolve().parent / 'assets/fonts/LilitaOne-Regular.ttf'
            if font.exists():
                ctypes.windll.gdi32.AddFontResourceExW(str(font), 0x10, None)
        except (OSError, AttributeError):
            pass


load_private_fonts()

UI_FONT = 'Segoe UI' if sys.platform == 'win32' else 'Helvetica'
