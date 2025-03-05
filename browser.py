import sys
import time
import logging

from PySide6.QtCore import QUrl, Qt, QObject, Signal, QRunnable, QThreadPool, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QLineEdit, QTabWidget, QPushButton, QProgressBar
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)-8s] %(message)s',
    datefmt='%H:%M:%S'
)

class WorkerSignals(QObject):
    result = Signal(QUrl, int)
    error = Signal(str, int)

class NavigationTask(QRunnable):
    def __init__(self, url_str: str, nav_id: int):
        super().__init__()
        self.url_str = url_str
        self.nav_id = nav_id
        self.signals = WorkerSignals()

    def run(self):
        try:
            time.sleep(0.05)
            url = QUrl(self.url_str)
            if not url.isValid() or url.scheme() == "":
                search_engine = "https://duckduckgo.com"
                search_path = "/?q="
                url = QUrl(search_engine + search_path + self.url_str)
            self.signals.result.emit(url, self.nav_id)
        except Exception as e:
            logging.exception("NavigationTask encountered an error.")
            self.signals.error.emit(str(e), self.nav_id)

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LibreX Web Browser")
        try:
            icon = QIcon('browser/assets/icons/favicons/favicon.ico')
            if icon.isNull():
                logging.warning("Browser icon could not be loaded.")
            self.setWindowIcon(icon)
        except Exception as e:
            logging.exception("Error setting window icon.")

        self.threadpool = QThreadPool.globalInstance()
        self.current_navigation_id = 0

        self.default_search_engine_url = "https://duckduckgo.com"
        self.default_search_engine_search_path = "/?q="

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or search query")
        self.url_bar.setStyleSheet(
            """
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
            """
        )
        self.url_bar.returnPressed.connect(self.on_url_entered)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.hide()

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
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def new_tab(self, url: str = None, label: str = "New Tab", switch: bool = True):
        try:
            browser = QWebEngineView()
            browser.loadStarted.connect(self.on_load_started)
            browser.loadProgress.connect(self.on_load_progress)
            browser.loadFinished.connect(self.on_load_finished)
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
        except Exception as e:
            logging.exception("Error creating a new tab.")

    def close_current_tab(self, index: int):
        try:
            if self.tab_widget.count() > 1:
                self.tab_widget.removeTab(index)
            else:
                logging.info("Attempted to close the last remaining tab; operation skipped.")
        except Exception as e:
            logging.exception("Error closing current tab.")

    def current_tab_changed(self, index: int):
        try:
            current_browser = self.tab_widget.widget(index)
            if current_browser:
                self.url_bar.setText(current_browser.url().toString())
            else:
                self.url_bar.clear()
        except Exception as e:
            logging.exception("Error handling tab change.")

    def on_url_entered(self):
        try:
            user_input = self.url_bar.text().strip()
            if not user_input:
                return

            self.current_navigation_id += 1
            current_id = self.current_navigation_id

            if not user_input.lower().startswith("http://") and not user_input.lower().startswith("https://"):
                if '.' in user_input:
                    user_input = "https://" + user_input

            task = NavigationTask(user_input, current_id)
            task.signals.result.connect(self.on_navigation_result)
            task.signals.error.connect(self.on_navigation_error)
            self.threadpool.start(task)
            logging.debug(f"Started navigation task for '{user_input}' with id {current_id}.")
        except Exception as e:
            logging.exception("Error processing URL on entry.")

    def on_navigation_result(self, url: QUrl, nav_id: int):
        try:
            if nav_id != self.current_navigation_id:
                logging.debug(f"Ignoring outdated navigation (id {nav_id}).")
                return

            logging.debug(f"Navigation result received: {url.toString()} (id {nav_id}).")
            current_browser = self.tab_widget.currentWidget()
            if current_browser:
                current_browser.stop()
                current_browser.setUrl(url)
            else:
                logging.error("No active browser tab available to load the URL.")
        except Exception as e:
            logging.exception("Error processing navigation result.")

    def on_navigation_error(self, error_message: str, nav_id: int):
        logging.error(f"Navigation error (id {nav_id}): {error_message}")

    def update_url_bar(self, qurl: QUrl, browser: QWebEngineView):
        try:
            if self.tab_widget.currentWidget() == browser:
                self.url_bar.setText(qurl.toString())
        except Exception as e:
            logging.exception("Error updating URL bar.")

    def update_tab_title(self, browser: QWebEngineView):
        try:
            index = self.tab_widget.indexOf(browser)
            if index != -1:
                title = browser.page().title()
                if title:
                    self.tab_widget.setTabText(index, title)
                else:
                    self.tab_widget.setTabText(index, browser.url().toString())
        except Exception as e:
            logging.exception("Error updating tab title.")

    def on_load_started(self):
        if self.sender() == self.tab_widget.currentWidget():
            self.progress_bar.show()
            self.progress_bar.setValue(0)

    def on_load_progress(self, progress: int):
        if self.sender() == self.tab_widget.currentWidget():
            self.progress_bar.setValue(progress)

    def on_load_finished(self, ok: bool):
        if self.sender() == self.tab_widget.currentWidget():
            self.progress_bar.setValue(100)
            QTimer.singleShot(500, self.progress_bar.hide)

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = Browser()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.exception("Fatal error during application execution.")
        sys.exit(1)
