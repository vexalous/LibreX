"""
LibreXWebBrowser implementation using PySide6.
"""

import sys
import logging
import os

from PySide6.QtCore import QUrl, Qt, QObject, Signal, QRunnable, QThreadPool, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLineEdit,
    QTabWidget, QPushButton, QProgressBar, QHBoxLayout
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon, QKeySequence, QShortcut

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)-8s] %(message)s',
    datefmt='%H:%M:%S'
)

# Global configuration variables
default_search_engine = "https://duckduckgo.com"
default_search_engine_search_path = "/?q="

shortcuts = {
    "new_tab": "Ctrl+T",
    "close_tab": "Ctrl+W",
    "close_browser": "Ctrl+Shift+W"
}


def global_exception_hook(exctype, value, tb):
    """Global hook for unhandled exceptions."""
    logging.exception("Unhandled exception", exc_info=(exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)


sys.excepthook = global_exception_hook


class WorkerSignals(QObject):
    """
    Signals for worker threads.
    """
    result = Signal(QUrl, int)
    error = Signal(str, int)


class NavigationTask(QRunnable):
    """
    Task to process a navigation request.
    """
    def __init__(self, url_str: str, nav_id: int):
        """Initialize a NavigationTask with a URL string and a navigation id."""
        super().__init__()
        self.url_str = url_str
        self.nav_id = nav_id
        self.signals = WorkerSignals()

    def run(self):
        """Run the navigation task to process the URL and emit a result or error."""
        try:
            try:
                url = QUrl(self.url_str)
            except Exception as e:
                logging.error("Failed to create QUrl from '%s': %s", self.url_str, e)
                self.signals.error.emit("Invalid URL format: %s" % e, self.nav_id)
                return

            if not url.isValid() or url.scheme() == "":
                try:
                    url = QUrl(''.join([
                        default_search_engine,
                        default_search_engine_search_path,
                        self.url_str
                    ]))
                except Exception as e:
                    logging.error("Failed to create search URL: %s", e)
                    self.signals.error.emit("Search URL creation error: %s" % e, self.nav_id)
                    return

            self.signals.result.emit(url, self.nav_id)

        except Exception as e:
            logging.exception("NavigationTask encountered a critical error in run method.")
            self.signals.error.emit("Navigation task critical failure: %s" % e, self.nav_id)


class Browser(QMainWindow):
    """
    Main browser window with tabs, a URL bar, and navigation tasks.
    """
    def __init__(self):
        """Initialize the browser window and its components."""
        super().__init__()
        try:
            # Set up keyboard shortcuts
            self.new_tab_shortcut = QShortcut(
                QKeySequence(shortcuts.get("new_tab", "Ctrl+T")), self
            )
            self.new_tab_shortcut.activated.connect(self.new_tab)
            self.close_tab_shortcut = QShortcut(
                QKeySequence(shortcuts.get("close_tab", "Ctrl+W")), self
            )
            self.close_tab_shortcut.activated.connect(self.close_current_tab_index)
            self.close_browser_shortcut = QShortcut(
                QKeySequence(shortcuts.get("close_browser", "Ctrl+Shift+W")), self
            )
            self.close_browser_shortcut.activated.connect(self.close_browser)

            self.setWindowTitle("LibreXWebBrowser")
            icon = QIcon("browser/assets/icons/favicons/favicon.ico")
            self.setWindowIcon(icon)

            self.threadpool = QThreadPool.globalInstance()
            self.current_navigation_id = 0
            self.default_search_engine_url = "https://duckduckgo.com"

            # Set up URL bar
            self.url_bar = QLineEdit()
            self.url_bar.setPlaceholderText("Enter URL or search query")
            self.url_bar.returnPressed.connect(self.on_url_entered)
            self.load_stylesheet('browser/styles/stylesheets/qss/styles.qss')

            # Set up progress bar
            self.progress_bar = QProgressBar()
            self.progress_bar.setMaximum(100)
            self.progress_bar.hide()

            # Set up tab widget
            self.tab_widget = QTabWidget()
            self.tab_widget.setTabsClosable(True)
            self.tab_widget.setMovable(True)
            self.tab_widget.tabCloseRequested.connect(self.close_current_tab)
            self.tab_widget.currentChanged.connect(self.current_tab_changed)

            # Set up plus button for new tabs
            self.plus_button = QPushButton("+")
            app = QApplication.instance()
            if app is None:
                raise RuntimeError("No QApplication instance available")
            screen_geometry = app.primaryScreen().geometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            plus_button_scrn_min_width = int(screen_width * 0.0175)
            plus_button_scrn_min_height = int(screen_height * 0.0175)
            plus_button_scrn_max_width = int(screen_width * 0.025)
            plus_button_scrn_max_height = int(screen_height * 0.025)
            self.plus_button.setMinimumSize(plus_button_scrn_min_width, plus_button_scrn_min_height)
            self.plus_button.setMaximumSize(plus_button_scrn_max_width, plus_button_scrn_max_height)
            self.plus_button.clicked.connect(self.new_tab)
            self.tab_widget.setCornerWidget(self.plus_button, Qt.TopRightCorner)

            # Open an initial tab.
            self.new_tab()

            # Set up layout
            central_widget = QWidget()
            layout = QVBoxLayout()
            layout.addWidget(self.url_bar)
            layout.addWidget(self.progress_bar)
            layout.addWidget(self.tab_widget)
            central_widget.setLayout(layout)
            self.setCentralWidget(central_widget)
        except Exception as e:
            logging.exception("Error in Browser window initialization: %s", e)

    def close_browser(self):
        """Close the browser window."""
        self.close()

    def read_csp_header(self, file_path):
        """
        Read the Content Security Policy header from the specified file.
        Returns the header string.
        """
        try:
            with open(file_path, 'r', encoding="utf-8") as file:
                return file.read().strip()
        except Exception as e:
            logging.exception("Error reading CSP header file: %s", e)
            return ""

    def set_csp_header(self):
        """
        Set the Content Security Policy header for the current web view.
        (Assumes that self.web_view exists.)
        """
        try:
            csp_header = self.read_csp_header("browser/config/csp/csp_header.txt")
            if csp_header:
                self.web_view.page().profile().setHttpUserAgent(csp_header)
                self.web_view.page().profile().setHttpHeader(
                    "Content-Security-Policy", csp_header.encode('utf-8')
                )
        except Exception as e:
            logging.exception("Error setting CSP header: %s", e)

    def load_stylesheet(self, path):
        """
        Load and apply a stylesheet from the given file path.
        """
        try:
            with open(path, 'r', encoding="utf-8") as file:
                stylesheet = file.read()
                self.setStyleSheet(stylesheet)
        except Exception as e:
            logging.error("Failed to load stylesheet from %s: %s", path, e)

    def new_tab(self, url: str = None, label: str = "New Tab", switch: bool = True):
        """
        Open a new tab in the browser.
        :param url: URL to load (defaults to the default search engine).
        :param label: Label for the tab.
        :param switch: Whether to switch immediately to the new tab.
        """
        web_view = None
        try:
            web_view = QWebEngineView()
            web_view.loadStarted.connect(self.on_load_started)
            web_view.loadProgress.connect(self.on_load_progress)
            web_view.loadFinished.connect(self.on_load_finished)
            url_obj = QUrl(url) if url else QUrl(self.default_search_engine_url)
            web_view.setUrl(url_obj)
            index = self.tab_widget.addTab(web_view, label)
            if switch:
                self.tab_widget.setCurrentIndex(index)
            web_view.urlChanged.connect(lambda qurl: self.safe_update_url_bar(qurl, web_view))
            web_view.loadFinished.connect(lambda _: self.safe_update_tab_title(web_view))
        except Exception as e:
            logging.exception("Error creating a new tab: %s", e)
            if web_view is not None:
                try:
                    web_view.deleteLater()
                except Exception as cleanup_error:
                    logging.warning("Failed to clean up partially created browser view: %s", cleanup_error)

    def close_current_tab_index(self):
        """Close the currently active tab."""
        try:
            current_tab_index = self.tab_widget.currentIndex()
            self.close_current_tab(current_tab_index)
        except Exception as e:
            logging.exception("Error occurred in close_current_tab_index: %s", e)

    def safe_update_url_bar(self, qurl: QUrl, browser: QWebEngineView):
        """Safely update the URL bar for the given browser view."""
        try:
            self.update_url_bar(qurl, browser)
        except Exception as e:
            logging.exception("Error in safe_update_url_bar: %s", e)

    def safe_update_tab_title(self, browser: QWebEngineView):
        """Safely update the tab title for the given browser view."""
        try:
            self.update_tab_title(browser)
        except Exception as e:
            logging.exception("Error in safe_update_tab_title: %s", e)

    def close_current_tab(self, index: int):
        """Close the tab at the specified index."""
        try:
            if self.tab_widget.count() > 1:
                try:
                    self.tab_widget.removeTab(index)
                except Exception as e:
                    logging.error("Failed to remove tab at index %s: %s", index, e)
            else:
                try:
                    self.close_browser()
                except Exception as e:
                    logging.exception("Error occurred while attempting to close browser (no tabs left): %s", e)
        except Exception as e:
            logging.exception("Error closing current tab: %s", e)

    def current_tab_changed(self, index: int):
        """Update the URL bar when the current tab changes."""
        try:
            current_browser = self.tab_widget.widget(index)
            if current_browser:
                try:
                    self.url_bar.setText(current_browser.url().toString())
                except Exception as e:
                    logging.warning("Failed to set URL bar text on tab change: %s", e)
            else:
                try:
                    self.url_bar.clear()
                except Exception as e:
                    logging.warning("Failed to clear URL bar on tab change (no browser): %s", e)
        except Exception as e:
            logging.exception("Error handling tab change: %s", e)

    def on_url_entered(self):
        """Process the entered URL and initiate navigation."""
        try:
            try:
                user_input = self.url_bar.text().strip()
            except Exception as e_get_url_text:
                logging.warning("Failed to get text from URL bar: %s", e_get_url_text)
                return

            if not user_input:
                return

            current_id = self.current_navigation_id + 1
            self.current_navigation_id = current_id

            user_input_lower = user_input.lower()
            if not user_input_lower.startswith(("http://", "https://")) and "." in user_input:
                user_input = "".join(["https://", user_input])

            try:
                task = NavigationTask(user_input, current_id)
                task.signals.result.connect(self.on_navigation_result)
                task.signals.error.connect(self.on_navigation_error)
                self.threadpool.start(task)
                logging.debug("Started navigation task for '%s' with id %s.", user_input, current_id)
            except Exception as e_start_nav_task:
                logging.error("Failed to start navigation task: %s", e_start_nav_task)

        except Exception as e_url_entered:
            logging.exception("Error processing URL on entry: %s", e_url_entered)

    def on_navigation_result(self, url: QUrl, nav_id: int):
        """Handle a successful navigation result."""
        try:
            if nav_id != self.current_navigation_id:
                logging.debug("Ignoring outdated navigation (id %s).", nav_id)
                return

            logging.debug("Navigation result received: %s (id %s).", url.toString(), nav_id)
            try:
                current_browser = self.tab_widget.currentWidget()
            except Exception as e_get_current_browser:
                logging.warning("Failed to get current browser widget: %s", e_get_current_browser)
                return

            if current_browser:
                try:
                    current_browser.stop()
                except Exception as ex_stop_load:
                    logging.warning("Error stopping current browser load: %s", ex_stop_load)
                try:
                    current_browser.setUrl(url)
                except Exception as e_set_browser_url:
                    logging.error("Failed to set URL for current browser: %s", e_set_browser_url)
            else:
                logging.error("No active browser tab available to load the URL.")
        except Exception as e_nav_result:
            logging.exception("Error processing navigation result: %s", e_nav_result)

    def on_navigation_error(self, error_message: str, nav_id: int):
        """Log navigation errors."""
        logging.error("Navigation error (id %s): %s", nav_id, error_message)

    def update_url_bar(self, qurl: QUrl, browser: QWebEngineView):
        """Update the URL bar if the given browser view is active."""
        try:
            if self.tab_widget.currentWidget() == browser:
                self.url_bar.setText(qurl.toString())
        except Exception as e:
            logging.exception("Error updating URL bar: %s", e)

    def truncate_title(self, title, max_length=15):
        """
        Truncate a title to the specified maximum length.
        Returns the original title if shorter than max_length.
        """
        try:
            return title if len(title) <= max_length else "".join([title[:max_length], "..."])
        except Exception as e:
            logging.exception("Error truncating title: %s", e)
            return title

    def update_tab_title(self, browser: QWebEngineView):
        """Update the tab title based on the browser view's title or URL."""
        try:
            index = self.tab_widget.indexOf(browser)
            if index == -1:
                return
            title = browser.page().title()
            if title:
                truncated_title = self.truncate_title(title)
                self.tab_widget.setTabText(index, truncated_title)
            else:
                self.tab_widget.setTabText(index, browser.url().toString())
        except Exception as e:
            logging.exception("Error updating tab title: %s", e)

    def on_load_started(self):
        """Show the progress bar when a page starts loading."""
        if self.sender() == self.tab_widget.currentWidget():
            try:
                self.progress_bar.show()
            except Exception as e:
                logging.warning("Failed to show progress bar on load start: %s", e)

    def on_load_progress(self, progress: int):
        """Update the progress bar as the page loads."""
        if self.sender() == self.tab_widget.currentWidget():
            try:
                self.progress_bar.setValue(progress)
            except Exception as e:
                logging.warning("Failed to set progress bar value to %s: %s", progress, e)

    def on_load_finished(self):
        """Finish the page load by hiding the progress bar."""
        try:
            if self.sender() == self.tab_widget.currentWidget():
                try:
                    self.progress_bar.setValue(100)
                    QTimer.singleShot(500, self.progress_bar.hide)
                except Exception as e:
                    logging.warning("Error while updating progress bar: %s", e)
        except Exception as e:
            logging.exception("Error in on_load_finished: %s", e)


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = Browser()
        window.showMaximized()
        sys.exit(app.exec())
    except Exception as e_app_initialization:
        logging.critical("An error occurred while initializing the application: %s", e_app_initialization)
        sys.exit(1)
