import sys
import time
import logging
import traceback
import os

from PySide6.QtCore import QUrl, Qt, QObject, Signal, QRunnable, QThreadPool, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QLineEdit, QTabWidget, QPushButton, QProgressBar
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon, QKeySequence, QShortcut

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)-8s] %(message)s',
    datefmt='%H:%M:%S'
)

def global_exception_hook(exctype, value, tb):
    logging.exception("Unhandled exception", exc_info=(exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)
sys.excepthook = global_exception_hook

def load_search_engine_config(file_path):
    search_engine_config = {}
    
    if not os.path.exists(file_path):
        logging.error(f"Search engine config file not found: {file_path}")
        return search_engine_config
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            line_number = 0
            for line in f:
                line_number += 1
                cleaned_line = line.strip()
                if not cleaned_line or cleaned_line.startswith('#'):
                    continue
                if '=' not in cleaned_line:
                    logging.warning(f"Line {line_number} in {file_path} does not contain '=': {cleaned_line}")
                    continue
                try:
                    key, value = cleaned_line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        search_engine_config[key] = value
                    else:
                        logging.warning(f"Line {line_number} in {file_path} has an empty key or value: {cleaned_line}")
                except Exception as parse_exception:
                    logging.error(f"Error parsing line {line_number} in {file_path}: {cleaned_line}. Exception: {parse_exception}")
    except Exception as e:
        logging.exception(f"Failed to load config from file: {file_path}. Exception: {e}")
    return search_engine_config
def set_favicon(file_path):
    favicon = {}
    
    if not os.path.exists(file_path):
        logging.error(f"Favicon config file not found: {file_path}")
        return favicon
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            line_number = 0
            for line in f:
                line_number += 1
                cleaned_line = line.strip()
                if not cleaned_line or cleaned_line.startswith('#'):
                    continue
                if '=' not in cleaned_line:
                    logging.warning(f"Line {line_number} in {file_path} does not contain '=': {cleaned_line}")
                    continue
                try:
                    key, value = cleaned_line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        favicon[key] = value
                    else:
                        logging.warning(f"Line {line_number} in {file_path} has an empty key or value: {cleaned_line}")
                except Exception as parse_exception:
                    logging.error(f"Error parsing line {line_number} in {file_path}: {cleaned_line}. Exception: {parse_exception}")
    except Exception as e:
        logging.exception(f"Failed to load favicon config from file: {file_path}. Exception: {e}")
    return favicon
def load_shortcuts(file_path):
    shortcuts = {}
    
    if not os.path.exists(file_path):
        logging.error(f"Shortcuts file not found: {file_path}")
        return shortcuts
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            line_number = 0
            for line in f:
                line_number += 1
                cleaned_line = line.strip()
                if not cleaned_line or cleaned_line.startswith('#'):
                    continue
                if '=' not in cleaned_line:
                    logging.warning(f"Line {line_number} in {file_path} does not contain '=': {cleaned_line}")
                    continue
                try:
                    key, value = cleaned_line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        shortcuts[key] = value
                    else:
                        logging.warning(f"Line {line_number} in {file_path} has an empty key or value: {cleaned_line}")
                except Exception as parse_exception:
                    logging.error(f"Error parsing line {line_number} in {file_path}: {cleaned_line}. Exception: {parse_exception}")
    except Exception as e:
        logging.exception(f"Failed to load shortcuts from file: {file_path}. Exception: {e}")
    return shortcuts

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
            try:
                url = QUrl(self.url_str)
            except Exception as e_url_creation:
                logging.error(f"Failed to create QUrl from '{self.url_str}': {e_url_creation}")
                self.signals.error.emit(f"Invalid URL format: {e_url_creation}", self.nav_id)
                return

            if not url.isValid() or url.scheme() == "":
                try:
                    url = QUrl(''.join([default_search_engine, default_search_engine_search_path, self.url_str]))
                except Exception as e_search_url_creation:
                    logging.error(f"Failed to create search URL: {e_search_url_creation}")
                    self.signals.error.emit(f"Search URL creation error: {e_search_url_creation}", self.nav_id)
                    return

            self.signals.result.emit(url, self.nav_id)

        except Exception as e_run:
            logging.exception("NavigationTask encountered a critical error in run method.")
            self.signals.error.emit(f"Navigation task critical failure: {str(e_run)}", self.nav_id)
try:
    browser_favicon_path = set_favicon("browser/config/favicon/favicon.txt").get("favicon", "browser/assets/icons/favicons/favicon.ico")
except Exception as e_load_favicon_config:
    logging.error(f"Failed to load favicon config: {e_load_favicon_config}")
    browser_favicon_path = "browser/assets/icons/favicons/favicon.ico"
try:
    default_search_engine = load_search_engine_config("browser/config/search_engine/search_engine.txt").get("default_search_engine", "https://duckduckgo.com")
except Exception as e_search_engine_config:
    logging.error(f"Failed to load search engine config: {e_search_engine_config}")
    default_search_engine = "https://duckduckgo.com"
try:
    default_search_engine_search_path = load_search_engine_config("browser/config/search_engine/search_engine.txt").get("default_search_engine_search_path", "/?q=")
except Exception as e_search_engine_config:
    logging.error(f"Failed to load search engine config: {e_search_engine_config}")
    default_search_engine_search_path = "/?q="
try:
    shortcuts = load_shortcuts("browser/config/shortcuts/shortcuts.txt")
except Exception as e_shortcuts:
    logging.error(f"Failed to load shortcuts: {e_shortcuts}")
    shortcuts = {}
class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        try:
            try:
                self.new_tab_shortcut = QShortcut(QKeySequence(shortcuts.get("new_tab", "Ctrl+T")), self)
                self.new_tab_shortcut.activated.connect(self.new_tab)
            except Exception as e_new_tab_shortcut:
                logging.exception(f"Error while calling new tab shortcut: {e_new_tab_shortcut}")
            try:
                self.close_tab_shortcut = QShortcut(QKeySequence(shortcuts.get("close_tab", "Ctrl+W")), self)
                self.close_tab_shortcut.activated.connect(self.close_current_tab_index)
            except Exception as e_close_tab_shortcut:
                logging.exception(f"Error while calling close tab shortcut: {e_close_tab_shortcut}")
            try:
                self.close_browser_shortcut = QShortcut(QKeySequence(shortcuts.get("close_browser", "Ctrl+Shift+W")), self)
                self.close_browser_shortcut.activated.connect(self.close_browser)
            except Exception as e_close_browser_shortcut:
                logging.exception(f"Error while calling close browser shortcut: {e_close_browser_shortcut}")
            try:
                self.setWindowTitle("LibreX Web Browser")
            except Exception as e_set_title:
                logging.error(f"Failed to set window title: {e_set_title}")

            try:
                icon = QIcon(browser_favicon_path)
                if icon.isNull():
                    logging.warning("Browser icon could not be loaded (isNull).")
                self.setWindowIcon(icon)
            except Exception as e_set_icon:
                logging.exception(f"Error setting window icon: {e_set_icon}")

            try:
                self.threadpool = QThreadPool.globalInstance()
            except Exception as e_threadpool:
                logging.critical(f"Failed to initialize thread pool: {e_threadpool}")

            self.current_navigation_id = 0

            self.default_search_engine_url = "https://duckduckgo.com"

            try:
                self.url_bar = QLineEdit()
                self.url_bar.setPlaceholderText("Enter URL or search query")
                self.load_stylesheet('browser/styles/stylesheets/urlbar/urlbar.qss')
                self.url_bar.returnPressed.connect(self.on_url_entered)
            except Exception as e_url_bar_setup:
                logging.exception(f"Error setting up URL bar: {e_url_bar_setup}")

            try:
                self.progress_bar = QProgressBar()
                self.progress_bar.setMaximum(100)
                self.progress_bar.hide()
            except Exception as e_progress_bar_setup:
                logging.exception(f"Error setting up progress bar: {e_progress_bar_setup}")

            try:
                self.tab_widget = QTabWidget()
                self.tab_widget.setTabsClosable(True)
                self.tab_widget.setMovable(True)
                self.tab_widget.tabCloseRequested.connect(self.close_current_tab)
                self.tab_widget.currentChanged.connect(self.current_tab_changed)
            except Exception as e_tab_widget_setup:
                logging.exception(f"Error setting up tab widget: {e_tab_widget_setup}")

            try:
                self.plus_button = QPushButton("+")
                self.plus_button.setFixedSize(24, 24)
                self.plus_button.clicked.connect(lambda: self.new_tab())
                self.tab_widget.setCornerWidget(self.plus_button, Qt.TopRightCorner)
            except Exception as e_plus_button_setup:
                logging.exception(f"Error setting up plus button: {e_plus_button_setup}")

            try:
                self.new_tab()
            except Exception as e_initial_tab:
                logging.exception(f"Error creating initial tab: {e_initial_tab}")

            try:
                central_widget = QWidget()
                layout = QVBoxLayout()
                layout.addWidget(self.url_bar)
                layout.addWidget(self.progress_bar)
                layout.addWidget(self.tab_widget)
                central_widget.setLayout(layout)
                self.setCentralWidget(central_widget)
            except Exception as e_layout_setup:
                logging.exception(f"Error setting up main layout: {e_layout_setup}")

        except Exception as e_init:
            logging.exception(f"Critical error during Browser initialization: {e_init}")
    def close_browser(self):
        self.close()
    def read_csp_header(file_path):
        try:
            with open(file_path, 'r') as file:
                return file.read().strip()
        except Exception as e_file:
            logging.exception(f"Error reading CSP header file: {e_file}")
            return
    def set_csp_header(self):
        try:
            csp_header = read_csp_header("browser/config/csp/csp_header.txt")
            if csp_header:
                self.web_view.page().profile().setHttpUserAgent(csp_header)
                self.web_view.page().profile().setHttpHeader("Content-Security-Policy", csp_header.encode('utf-8'))
        except Exception as e_csp:
            logging.exception(f"Error setting CSP header: {e_csp}")
    def load_stylesheet(self, path):
        try:
            with open(path, 'r') as file:
                self.setStyleSheet(file.read())
        except Exception as e:
            logging.error(f"Failed to load stylesheet from {path}: {e}")
    def new_tab(self, url: str = None, label: str = "New Tab", switch: bool = True):
        browser = None
        try:
            try:
                browser = QWebEngineView()
            except Exception as e_webengine_view:
                logging.error(f"Failed to create QWebEngineView: {e_webengine_view}")
                return

            try:
                browser.loadStarted.connect(self.on_load_started)
                browser.loadProgress.connect(self.on_load_progress)
                browser.loadFinished.connect(self.on_load_finished)
            except Exception as e_signal_connect:
                logging.warning(f"Failed to connect browser signals: {e_signal_connect}")

            try:
                if url is None:
                    url_obj = QUrl(self.default_search_engine_url)
                else:
                    url_obj = QUrl(url)
                browser.setUrl(url_obj)
            except Exception as e_set_url:
                logging.error(f"Failed to set URL for new tab: {e_set_url}")

            try:
                index = self.tab_widget.addTab(browser, label)
                if switch:
                    self.tab_widget.setCurrentIndex(index)
            except Exception as e_add_tab:
                logging.error(f"Failed to add tab to tab widget: {e_add_tab}")
                return

            try:
                browser.urlChanged.connect(lambda qurl, browser=browser: self.safe_update_url_bar(qurl, browser))
                browser.loadFinished.connect(lambda ok, browser=browser: self.safe_update_tab_title(ok, browser))
            except Exception as e_browser_signals:
                logging.warning(f"Failed to connect browser-specific signals: {e_browser_signals}")

        except Exception as e_new_tab:
            logging.exception("Error creating a new tab.")
            if browser:
                try:
                    browser.deleteLater()
                except:
                    logging.warning("Failed to cleanup partially created browser view.")

    def close_current_tab_index(self):
        try:
            current_tab_index = self.tab_widget.currentIndex()
            self.close_current_tab(current_tab_index)
        except Exception as e_close_tab_index:
            logging.exception(f"Error occured in close_current_tab_index: {e_close_tab_index}")
    def safe_update_url_bar(self, qurl: QUrl, browser: QWebEngineView):
        try:
            self.update_url_bar(qurl, browser)
        except Exception as e:
            logging.exception("Error in safe_update_url_bar: %s", e)

    def safe_update_tab_title(self, ok: bool, browser: QWebEngineView):
        try:
            self.update_tab_title(browser)
        except Exception as e:
            logging.exception("Error in safe_update_tab_title: %s", e)

    def close_current_tab(self, index: int):
        try:
            if self.tab_widget.count() > 1:
                try:
                    self.tab_widget.removeTab(index)
                except Exception as e_remove_tab:
                    logging.error(f"Failed to remove tab at index {index}: {e_remove_tab}")
            else:
                try:
                    self.close_browser()
                except Exception as e_close_browser_no_tabs_left:
                    logging.exception(f"Error occured while attempting to close browser, no tabs left: {e_close_browser_no_tabs_left}")
        except Exception as e_close_tab:
            logging.exception("Error closing current tab.")

    def current_tab_changed(self, index: int):
        try:
            try:
                current_browser = self.tab_widget.widget(index)
            except Exception as e_get_widget:
                logging.warning(f"Failed to get widget for tab index {index}: {e_get_widget}")
                return

            if current_browser:
                try:
                    self.url_bar.setText(current_browser.url().toString())
                except Exception as e_set_url_bar:
                    logging.warning(f"Failed to set URL bar text on tab change: {e_set_url_bar}")
            else:
                try:
                    self.url_bar.clear()
                except Exception as e_clear_url_bar:
                    logging.warning(f"Failed to clear URL bar on tab change (no browser): {e_clear_url_bar}")
        except Exception as e_tab_changed:
            logging.exception("Error handling tab change.")

    def on_url_entered(self):
        try:
            try:
                user_input = self.url_bar.text().strip()
            except Exception as e_get_url_text:
                logging.warning(f"Failed to get text from URL bar: {e_get_url_text}")
                return

            if not user_input:
                return

            self.current_navigation_id += 1
            current_id = self.current_navigation_id

            user_input_lower = user_input.lower()
            if not user_input_lower.startswith(("http://", "https://")) and '.' in user_input:
                user_input = ''.join(['https://', user_input])


            try:
                task = NavigationTask(user_input, current_id)
                task.signals.result.connect(self.on_navigation_result)
                task.signals.error.connect(self.on_navigation_error)
                self.threadpool.start(task)
                logging.debug(f"Started navigation task for '{user_input}' with id {current_id}.")
            except Exception as e_start_nav_task:
                logging.error(f"Failed to start navigation task: {e_start_nav_task}")

        except Exception as e_url_entered:
            logging.exception("Error processing URL on entry.")

    def on_navigation_result(self, url: QUrl, nav_id: int):
        try:
            if nav_id != self.current_navigation_id:
                logging.debug(f"Ignoring outdated navigation (id {nav_id}).")
                return

            logging.debug(f"Navigation result received: {url.toString()} (id {nav_id}).")
            try:
                current_browser = self.tab_widget.currentWidget()
            except Exception as e_get_current_browser:
                logging.warning(f"Failed to get current browser widget: {e_get_current_browser}")
                return

            if current_browser:
                try:
                    current_browser.stop()
                except Exception as ex_stop_load:
                    logging.warning("Error stopping current browser load: %s", ex_stop_load)
                try:
                    current_browser.setUrl(url)
                except Exception as e_set_browser_url:
                    logging.error(f"Failed to set URL for current browser: {e_set_browser_url}")
            else:
                logging.error("No active browser tab available to load the URL.")
        except Exception as e_nav_result:
            logging.exception("Error processing navigation result.")

    def on_navigation_error(self, error_message: str, nav_id: int):
        logging.error(f"Navigation error (id {nav_id}): {error_message}")

    def update_url_bar(self, qurl: QUrl, browser: QWebEngineView):
        try:
            try:
                if self.tab_widget.currentWidget() == browser:
                    try:
                        self.url_bar.setText(qurl.toString())
                    except Exception as e_set_url_bar_text:
                        logging.warning(f"Failed to set URL bar text in update_url_bar: {e_set_url_bar_text}")
            except Exception as e_get_current_widget:
                logging.warning(f"Failed to get current tab widget in update_url_bar: {e_get_current_widget}")
        except Exception as e_update_url_bar:
            logging.exception("Error updating URL bar.")

    def truncate_title(self, title, max_length=15):
        try:
            return title if len(title) <= max_length else ''.join([title[:max_length], '...'])
        except Exception as e_truncate_title:
            logging.exception("Error truncating title.")
            return title

    def update_tab_title(self, browser: QWebEngineView):
        try:
            try:
                index = self.tab_widget.indexOf(browser)
            except Exception as e_get_tab_index:
                logging.warning(f"Failed to get tab index for browser: {e_get_tab_index}")
                return

            if index != -1:
                try:
                    title = browser.page().title()
                except Exception as e_get_page_title:
                    logging.warning(f"Failed to get page title from browser: {e_get_page_title}")
                    title = None

                if title:
                    try:
                        truncated_title = self.truncate_title(title)
                        self.tab_widget.setTabText(index, truncated_title)
                    except Exception as e_set_tab_text_truncated:
                        logging.warning(f"Failed to set tab text with truncated title: {e_set_tab_text_truncated}")
                        try:
                            self.tab_widget.setTabText(index, browser.url().toString())
                        except:
                            logging.warning("Failed to set tab text even with URL as fallback after truncation error.")
                else:
                    try:
                        self.tab_widget.setTabText(index, browser.url().toString())
                    except Exception as e_set_tab_text_url:
                        logging.warning(f"Failed to set tab text with URL: {e_set_tab_text_url}")
        except Exception as e_update_tab_title:
            logging.exception("Error updating tab title.")

    def on_load_started(self):
        try:
            try:
                if self.sender() == self.tab_widget.currentWidget():
                    try:
                        self.progress_bar.show()
                    except Exception as e_show_progress_bar:
                        logging.warning(f"Failed to show progress bar on load start: {e_show_progress_bar}")
                    try:
                        self.progress_bar.setValue(0)
                    except Exception as e_set_progress_value_start:
                        logging.warning(f"Failed to set progress bar value to 0 on load start: {e_set_progress_value_start}")
            except Exception as e_get_current_widget:
                logging.warning(f"Failed to get current tab widget in on_load_started: {e_get_current_widget}")
        except Exception as e_load_started:
            logging.exception("Error in on_load_started.")

    def on_load_progress(self, progress: int):
        try:
            try:
                if self.sender() == self.tab_widget.currentWidget():
                    try:
                        self.progress_bar.setValue(progress)
                    except Exception as e_set_progress_value:
                        logging.warning(f"Failed to set progress bar value to {progress}: {e_set_progress_value}")
            except Exception as e_get_current_widget:
                logging.warning(f"Failed to get current tab widget in on_load_progress: {e_get_current_widget}")
        except Exception as e_load_progress:
            logging.exception("Error in on_load_progress.")

    def on_load_finished(self, ok: bool):
        try:
            try:
                if self.sender() == self.tab_widget.currentWidget():
                    try:
                        self.progress_bar.setValue(100)
                    except Exception as e_set_progress_value_finish:
                        logging.warning(f"Failed to set progress bar value to 100 on load finish: {e_set_progress_value_finish}")
                    try:
                        QTimer.singleShot(500, self.progress_bar.hide)
                    except Exception as e_timer_hide_progress:
                        logging.warning(f"Failed to start timer to hide progress bar: {e_timer_hide_progress}")
            except Exception as e_get_current_widget:
                logging.warning(f"Failed to get current tab widget in on_load_finished: {e_get_current_widget}")

        except Exception as e_load_finished:
            logging.exception("Error in on_load_finished.")

if __name__ == "__main__":
    try:
        try:
            app = QApplication(sys.argv)
        except Exception as e_app_init:
            logging.critical(f"Failed to initialize QApplication: {e_app_init}")
            sys.exit(1)

        try:
            window = Browser()
        except Exception as e_browser_init:
            logging.critical(f"Failed to initialize Browser window: {e_browser_init}")
            sys.exit(1)

        try:
            window.showMaximized()
        except Exception as e_show_maximized:
            logging.warning(f"Failed to maximize window: {e_show_maximized}")

        try:
            sys.exit(app.exec())
        except Exception as e_app_exec:
            logging.critical(f"Application execution failed: {e_app_exec}")
            sys.exit(1)

    except Exception as e_main:
        logging.exception("Fatal error during application execution in main block.")
        sys.exit(1)
