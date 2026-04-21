"""
Infac P4 — Industrial Inspection System
Entry point for the desktop application.

Requirements:
    pip install opencv-python Pillow requests numpy pymodbus
"""

import sys


def check_dependencies():
    """Verify required packages are installed."""
    missing = []
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
    try:
        from PIL import Image, ImageTk
    except ImportError:
        missing.append("Pillow")
    try:
        import requests
    except ImportError:
        missing.append("requests")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    try:
        import pymodbus
    except ImportError:
        missing.append("pymodbus")

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        sys.exit(1)


def main():
    check_dependencies()
    from app import InfacApp
    app = InfacApp()
    app.mainloop()


if __name__ == "__main__":
    main()
