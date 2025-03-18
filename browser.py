#!/usr/bin/env python3
"""
LibreXWebBrowser implementation using PySide6.
"""

import sys
import logging

from PySide6.QtCore import (
    QUrl, Qt, QObject, Signal, QRunnable, QThreadPool, QTimer
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLineEdit, QTabWidget,
    QPushButton, QProgressBar
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QIcon, QKeySequence, QShortcut

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%H:%M:%S"
)

# Global constants (all in UPPER_CASE)
DEFAULT_SEARCH_ENGINE = "https://duckduckgo.com"
DEFAULT_SEARCH_ENGINE_SEARCH_PATH = "/?q="

SHORTCUTS = {
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
    Signals to be used with worker threads.
    """
    def __init__(self):
        super().__init__()

    result = Signal(QUrl, int)
    error = Signal(str, int)

    def emit_result(self, url: QUrl, nav_id: int):
        """Emit the result signal with a URL and navigation ID."""
        self.result.emit(url, nav_id)

    def emit_error(self, message: str, nav_id: int):
        """Emit the error signal with an error message and navigation ID."""
        self.error.emit(message, nav_id)


class NavigationTask(QRunnable):
    """
    Task to process a navigation request.
    Validates and adjusts a URL; emits either a result or an error.
    """
    def __init__(self, url_str: str, nav_id: int):
        super().__init__()
        self.url_str = url_str
        self.nav_id = nav_id
        self.signals = WorkerSignals()

    def run(self):
        """Run the navigation task to validate and adjust the URL."""
        try:
            try:
                url = QUrl(self.url_str)
            except Exception as e:
                logging.error(
                    "Failed to create QUrl from '%s': %s", self.url_str, e
                )
                error_msg = f"Invalid URL format: {e}"
                self.signals.emit_error(error_msg, self.nav_id)
                return

            if not url.isValid() or url.scheme() == "":
                try:
                    url = QUrl("".join([
                        DEFAULT_SEARCH_ENGINE,
                        DEFAULT_SEARCH_ENGINE_SEARCH_PATH,
                        self.url_str
                    ]))
                except Exception as e:
                    logging.error("Failed to create search URL: %s", e)
                    error_msg = f"Search URL creation error: {e}"
                    self.signals.emit_error(error_msg, self.nav_id)
                    return

            self.signals.emit_result(url, self.nav_id)
        except Exception as e:
            logging.exception(
                "NavigationTask encountered a critical error in run method."
            )
            error_msg = f"Navigation task critical failure: {e}"
            self.signals.emit_error(error_msg, self.nav_id)


class Browser(QMainWindow):
    """
    Main browser window with tabs, a URL bar, a progress bar, and navigation.
    """
    def __init__(self):
        """Initialize the browser window and set up its components."""
        super().__init__()
        try:
            # Group the keyboard shortcuts together in a list
            self.shortcuts = []
            self.current_navigation_id = 0
            self.threadpool = QThreadPool.globalInstance()

            self.setup_shortcuts()
            self.setup_ui()
        except Exception as e:
            logging.exception("Error in Browser window initialization: %s", e)

    def setup_shortcuts(self):
        """Set up the keyboard shortcuts and store them in self.shortcuts."""
        new_tab_sc = QShortcut(
            QKeySequence(SHORTCUTS.get("new_tab", "Ctrl+T")), self
        )
        new_tab_sc.activated.connect(self.new_tab)
        self.shortcuts.append(new_tab_sc)

        close_tab_sc = QShortcut(
            QKeySequence(SHORTCUTS.get("close_tab", "Ctrl+W")), self
        )
        close_tab_sc.activated.connect(self.close_current_tab_index)
        self.shortcuts.append(close_tab_sc)

        close_browser_sc = QShortcut(
            QKeySequence(SHORTCUTS.get("close_browser", "Ctrl+Shift+W")), self
        )
        close_browser_sc.activated.connect(self.close_browser)
        self.shortcuts.append(close_browser_sc)

    def setup_ui(self):
        """Set up the user interface elements of the browser."""
        self.setWindowTitle("LibreXWebBrowser")
        icon = QIcon("browser/assets/icons/favicons/favicon.ico")
        self.setWindowIcon(icon)

        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or search query")
        self.url_bar.returnPressed.connect(self.on_url_entered)
        self.load_stylesheet("browser/styles/stylesheets/qss/styles.qss")

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.hide()

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_current_tab)
        self.tab_widget.currentChanged.connect(self.current_tab_changed)

        # Plus button for new tabs
        self.plus_button = QPushButton("+")
        qt_app = QApplication.instance()
        if qt_app is None:
            raise RuntimeError("No QApplication instance available")
        screen_geom = qt_app.primaryScreen().geometry()
        screen_width = screen_geom.width()
        screen_height = screen_geom.height()
        min_width = int(screen_width * 0.0175)
        min_height = int(screen_height * 0.0175)
        max_width = int(screen_width * 0.025)
        max_height = int(screen_height * 0.025)
        self.plus_button.setMinimumSize(min_width, min_height)
        self.plus_button.setMaximumSize(max_width, max_height)
        self.plus_button.clicked.connect(self.new_tab)
        self.tab_widget.setCornerWidget(self.plus_button, Qt.TopRightCorner)

        # Open an initial tab.
        self.new_tab()

        # Set main layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.url_bar)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def close_browser(self):
        """Close the browser window."""
        self.close()

    def read_csp_header(self, file_path):
        """
        Read the Content Security Policy header from the provided file path.
        Returns the header string (or empty string on failure).
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
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
                    "Content-Security-Policy", csp_header.encode("utf-8")
                )
        except Exception as e:
            logging.exception("Error setting CSP header: %s", e)

    def load_stylesheet(self, path):
        """
        Load a stylesheet from the given file path and apply it.
        """
        try:
            with open(path, "r", encoding="utf-8") as file:
                stylesheet = file.read()
            self.setStyleSheet(stylesheet)
        except Exception as e:
            logging.error("Failed to load stylesheet from %s: %s", path, e)

    def new_tab(self, url: str = None, label: str = "New Tab",
                switch: bool = True):
        """
        Open a new tab with an optional URL and label.
        
        :param url: URL to load (defaults to DEFAULT_SEARCH_ENGINE)
        :param label: Label for the tab
        :param switch: Whether to immediately switch to the new tab
        """
        web_view = None
        try:
            web_view = QWebEngineView()
            web_view.loadStarted.connect(self.on_load_started)
            web_view.loadProgress.connect(self.on_load_progress)
            web_view.loadFinished.connect(self.on_load_finished)
            url_obj = QUrl(url) if url else QUrl(DEFAULT_SEARCH_ENGINE)
            web_view.setUrl(url_obj)
            index = self.tab_widget.addTab(web_view, label)
            if switch:
                self.tab_widget.setCurrentIndex(index)
            web_view.urlChanged.connect(
                lambda qurl, wv=web_view: self.safe_update_url_bar(qurl, wv)
            )
            web_view.loadFinished.connect(
                lambda _, wv=web_view: self.safe_update_tab_title(wv)
            )
        except Exception as e:
            logging.exception("Error creating a new tab: %s", e)
            if web_view is not None:
                try:
                    web_view.deleteLater()
                except Exception as cleanup_error:
                    logging.warning(
                        "Failed to clean up partially created browser view: %s",
                        cleanup_error
                    )

    def close_current_tab_index(self):
        """Close the currently active tab."""
        try:
            current_tab_index = self.tab_widget.currentIndex()
            self.close_current_tab(current_tab_index)
        except Exception as e:
            logging.exception("Error occurred in close_current_tab_index: %s", e)

    def safe_update_url_bar(self, qurl: QUrl, browser: QWebEngineView):
        """Safely update the URL bar for the specified browser view."""
        try:
            self.update_url_bar(qurl, browser)
        except Exception as e:
            logging.exception("Error in safe_update_url_bar: %s", e)

    def safe_update_tab_title(self, browser: QWebEngineView):
        """Safely update the tab title for the specified browser view."""
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
                    logging.exception(
                        "Error while attempting to close browser (no tabs left): %s", e
                    )
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
                    logging.warning("Failed to clear URL bar (no browser): %s", e)
        except Exception as e:
            logging.exception("Error handling tab change: %s", e)

    def on_url_entered(self):
        """
        Process the URL entered in the URL bar and initiate navigation.
        """
        try:
            try:
                user_input = self.url_bar.text().strip()
            except Exception as e_get_url_text:
                logging.warning("Failed to get text from URL bar: %s", e_get_url_text)
                return

            if not user_input:
                return

            self.current_navigation_id += 1
            current_id = self.current_navigation_id

            user_input_lower = user_input.lower()
            if (not user_input_lower.startswith(("http://", "https://"))
                    and "." in user_input):
                user_input = "".join(["https://", user_input])

            try:
                task = NavigationTask(user_input, current_id)
                task.signals.result.connect(self.on_navigation_result)
                task.signals.error.connect(self.on_navigation_error)
                self.threadpool.start(task)
                logging.debug(
                    "Started navigation task for '%s' with id %s.",
                    user_input,
                    current_id
                )
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

            logging.debug(
                "Navigation result received: %s (id %s).",
                url.toString(),
                nav_id
            )
            try:
                current_browser = self.tab_widget.currentWidget()
            except Exception as e_get_current_browser:
                logging.warning("Failed to get current browser widget: %s",
                                e_get_current_browser)
                return

            if current_browser:
                try:
                    current_browser.stop()
                except Exception as ex_stop_load:
                    logging.warning("Error stopping current browser load: %s",
                                    ex_stop_load)
                try:
                    current_browser.setUrl(url)
                except Exception as e_set_browser_url:
                    logging.error("Failed to set URL for current browser: %s",
                                  e_set_browser_url)
            else:
                logging.error("No active browser tab available to load the URL.")
        except Exception as e_nav_result:
            logging.exception("Error processing navigation result: %s", e_nav_result)

    def on_navigation_error(self, error_message: str, nav_id: int):
        """Log navigation errors."""
        logging.error("Navigation error (id %s): %s", nav_id, error_message)

    def update_url_bar(self, qurl: QUrl, browser: QWebEngineView):
        """
        Update the URL bar if the given browser view is active.
        """
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
            if len(title) <= max_length:
                return title
            else:
                return "".join([title[:max_length], "..."])
        except Exception as e:
            logging.exception("Error truncating title: %s", e)
            return title

    def update_tab_title(self, browser: QWebEngineView):
        """
        Update the tab title based on the browser view's title or URL.
        """
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
                logging.warning("Failed to set progress bar value to %s: %s",
                                progress, e)

    def on_load_finished(self):
        """
        Finish the page load by setting progress to 100 and hiding the progress bar.
        """
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
        qt_app = QApplication(sys.argv)
        window = Browser()
        window.showMaximized()
        sys.exit(qt_app.exec())
    except Exception as e_app_initialization:
        logging.critical(
            "An error occurred while initializing the application: %s",
            e_app_initialization
        )
        sys.exit(1)
