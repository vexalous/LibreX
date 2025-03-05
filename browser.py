from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QLineEdit, QTabWidget, QPushButton
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QIcon
import sys

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LibreX Web Browser")
        self.setWindowIcon(QIcon('browser/assets/icons/favicons/favicon.ico'))

        self.default_search_engine_url = "https://duckduckgo.com"
        self.default_search_engine_search_path = "/?q="
        
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
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_current_tab)
        self.tab_widget.currentChanged.connect(self.current_tab_changed)
        
        self.plus_button = QPushButton("+")
        self.plus_button.setFixedSize(24, 24)
        self.plus_button.clicked.connect(lambda: self.new_tab())
        self.tab_widget.setCornerWidget(self.plus_button, Qt.TopRightCorner)
        
        self.new_tab()
        
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.url_bar)
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
    
    def new_tab(self, url=None, label="New Tab", switch=True):
        browser = QWebEngineView()
        if url is None:
            url_obj = QUrl(self.default_search_engine_url)
        else:
            url_obj = QUrl(url)
        browser.setUrl(url_obj)
        
        index = self.tab_widget.addTab(browser, label)
        if switch:
            self.tab_widget.setCurrentIndex(index)
        
        browser.urlChanged.connect(lambda qurl, browser=browser: self.update_url_bar(qurl, browser))
        browser.loadFinished.connect(lambda ok, browser=browser: self.update_tab_title(browser))
    
    def close_current_tab(self, index):
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
    
    def change_browser_url(self):
        user_input = self.url_bar.text().strip()
        
        if not user_input:
            return
        
        if not user_input.lower().startswith("http://") and not user_input.lower().startswith("https://"):
            if '.' in user_input:
                user_input = "https://" + user_input
            else:
                user_input = self.default_search_engine_url + self.default_search_engine_search_path + user_input
                
        current_browser = self.tab_widget.currentWidget()
        if current_browser:
            current_browser.setUrl(QUrl(user_input))
    
    def update_url_bar(self, qurl, browser):
        if self.tab_widget.currentWidget() == browser:
            self.url_bar.setText(qurl.toString())
    
    def current_tab_changed(self, index):
        current_browser = self.tab_widget.widget(index)
        if current_browser:
            self.url_bar.setText(current_browser.url().toString())
    
    def update_tab_title(self, browser):
        index = self.tab_widget.indexOf(browser)
        if index != -1:
            title = browser.page().title()
            if title:
                self.tab_widget.setTabText(index, title)
            else:
                self.tab_widget.setTabText(index, browser.url().toString())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Browser()
    window.show()
    sys.exit(app.exec())
