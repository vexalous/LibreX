from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLineEdit
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon
import sys

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LibreX Web Browser")
        self.setWindowIcon(QIcon('browser/assets/icons/favicons/favicon.ico'))
        
        self.browser = QWebEngineView()
        self.default_search_engine_url = "https://duckduckgo.com"
        self.default_search_engine_search_path = "/?q="
        self.browser.setUrl(QUrl(self.default_search_engine_url))
        
        self.url_bar = QLineEdit()
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 10px;
                padding: 5px 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
        """)
        self.url_bar.returnPressed.connect(self.change_browser_url)
        
        layout = QVBoxLayout()
        layout.addWidget(self.url_bar)
        layout.addWidget(self.browser)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
    def change_browser_url(self):
        url = self.url_bar.text()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = self.default_search_engine_url + self.default_search_engine_search_path + url
        self.browser.setUrl(QUrl(url))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Browser()
    window.show()
    sys.exit(app.exec())
