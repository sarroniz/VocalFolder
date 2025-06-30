# app/main.py
import os
import sys
from PyQt6.QtWidgets import QApplication
from app.gui.main_window import MainWindow
from PyQt6.QtGui import QIcon

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # compute the same path you know exists
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    icon_path = os.path.join(base_dir, "assets", "icons", "vocalfolder_icon.png")

    # this changes the Dock icon (and will be used as the default
    # window icon on platforms that show one)
    app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if "--debug" in sys.argv:
    print("🛠️ Running in DEBUG MODE")