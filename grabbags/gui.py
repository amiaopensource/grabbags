"""Contains the code for running grabbags with a Qt based user interface."""
import abc
import logging
import os
import traceback
import typing
import sys

from PySide2 import QtCore, QtWidgets, QtUiTools, QtGui
import bagit
from grabbags import grabbags

__all__ = ['MainWindow', 'main']

# ignored because an issue with mypy producing false positives
# see here https://github.com/python/mypy/issues/1153
try:
    from importlib.resources import as_file  # type: ignore
except ImportError:
    from importlib_resources import as_file  # type: ignore

try:
    from importlib.resources import files  # type: ignore
except ImportError:
    from importlib_resources import files  # type: ignore


class OptionsPanel(QtWidgets.QWidget):

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)

        # Using importlib.resources.as_file and importlib.resources.files so
        # that this can be run from a zip file.
        with as_file(files('grabbags').joinpath('options.ui')) as ui_file_name:
            ui_file = QtCore.QFile(str(ui_file_name))
            try:
                ui_file.open(QtCore.QFile.ReadOnly)
                self.ui = QtUiTools.QUiLoader().load(
                    ui_file, parentWidget=self)

            finally:
                ui_file.close()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ui)
        self.setLayout(layout)

    def get_settings(self) -> typing.Dict[str, bool]:
        return {
            user_option.objectName(): user_option.isChecked()
            for user_option in self.ui.findChildren(QtWidgets.QCheckBox)
        }


class Console(QtWidgets.QWidget):
    directories_entered = QtCore.Signal(list)

    def __init__(
            self,
            parent: typing.Optional[QtWidgets.QWidget] = None
    ) -> None:

        super().__init__(parent)
        self.setAcceptDrops(True)
        with as_file(
                files('grabbags').joinpath('console.ui')
        ) as ui_file_name:

            ui_file = QtCore.QFile(str(ui_file_name))
            try:
                ui_file.open(QtCore.QFile.ReadOnly)
                loader = QtUiTools.QUiLoader()
                self.ui = loader.load(ui_file, self)
            finally:
                ui_file.close()

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ui)
        self.setLayout(layout)
        self._document = QtGui.QTextDocument(self)

        self.ui.consoleText = typing.cast(
            QtWidgets.QTextBrowser, self.ui.consoleText
        )
        self.ui.consoleText.setDocument(self._document)
        self.info_text_layout = QtWidgets.QVBoxLayout()
        self.info_text = QtWidgets.QLabel()
        self.ui.consoleText.setLayout(self.info_text_layout)
        self.info_text_layout.addWidget(self.info_text, alignment=QtCore.Qt.AlignCenter)

    def refresh(self):
        self.ui.consoleText.setDocument(self._document)
        self.info_text.clear()
        QtCore.QCoreApplication.processEvents()

    @staticmethod
    def check_valid_dragged_data(sources: typing.List[str]) -> bool:
        for source in sources:
            if not os.path.exists(source):
                return False
            if not os.path.isdir(source):
                return False
        return True

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        dirs = [u.path() for u in event.mimeData().urls()]
        if not self.check_valid_dragged_data(dirs):
            self.pop_alert("Input accepts only folders")
            event.ignore()
            return

        paths = "".join(
            f"{s.path()}" for s in event.mimeData().urls()
        )

        self.pop_alert(f"Do you want to bag the following directories? :\n"
                       f"{paths}"
                       )
        event.accept()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        self.write("Starting")
        self.refresh()
        event.accept()
        self.directories_entered.emit([
                s.path() for s in event.mimeData().urls()
        ])

    def clear(self) -> None:
        self._document.clear()
        # Force the gui to redraw
        QtCore.QCoreApplication.processEvents()

    def text(self) -> str:
        return self._document.toPlainText().strip()

    def write(self, text: str) -> None:
        cursor = QtGui.QTextCursor(self._document)
        cursor.movePosition(cursor.End)
        cursor.insertBlock()
        cursor.insertHtml(text)
        self.ui.consoleText.setTextCursor(cursor)
        QtCore.QCoreApplication.processEvents()

    def pop_alert(self, text: str) -> None:
        """Provide information to user that is not log information.

        For example, provide a user with the message that a configuration is
            not valid.

        Args:
            text:

        """
        self.info_text.setText(text)
        self.ui.consoleText.clear()
        QtCore.QCoreApplication.processEvents()


class AbsState(abc.ABC):

    def __init__(self, context: "MainWindow") -> None:
        super().__init__()
        self.context = context

    @abc.abstractmethod
    def run(self, paths: typing.List[str]) -> None:
        """Run the bags process."""


class WorkingState(AbsState):

    def run(self, paths: typing.List[str]) -> None:
        self.context.console.setAcceptDrops(False)
        self.context.worker_thread = QtCore.QThread()
        worker = Worker()
        self.context.console.refresh()
        worker.moveToThread(self.context.worker_thread)

        self.context.worker_thread.started.connect(
            lambda paths_=paths: self._run(worker, paths_)
        )

        worker.finished.connect(self.context.worker_thread.quit)
        worker.finished.connect(self.context.worker_thread.deleteLater)

        self.context.worker_thread.finished.connect(
            self.context.worker_thread.deleteLater
        )

        worker.finished.connect(self.on_finished)

        self.context.console.refresh()
        self.context.worker_thread.start()

    def on_finished(self):
        self.context.console.write("Done")
        self.context.current_state = IdleState(context=self.context)

    def _run(self, worker: "Worker", paths: typing.List[str]) -> None:
        try:
            worker.run(paths, self.context.options.get_settings())
        except Exception as error:
            traceback.print_exc(file=sys.stderr)
            error_dialog_box = QtWidgets.QErrorMessage(parent=self.context)
            error_dialog_box.setWindowModality(QtCore.Qt.WindowModal)

            error_dialog_box.setWindowTitle(
                f"{type(error).__name__} Exception Thrown"
            )
            error_dialog_box.showMessage(str(error))
            error_dialog_box.exec_()
            if self.context.worker_thread is not None:
                self.context.worker_thread.quit()
            QtGui.QGuiApplication.exit(1)


class IdleState(AbsState):

    def __init__(self, context: "MainWindow") -> None:
        super().__init__(context)
        self.context.console.setAcceptDrops(True)

    def run(self, paths: typing.List[str]) -> None:
        self.context.current_state = WorkingState(self.context)
        self.context.current_state.run(paths)


class MainWindow(QtWidgets.QMainWindow):
    """Main GUI window for the application."""

    def __init__(self) -> None:
        """Open the tool's main window."""
        super().__init__()

        main_widget = QtWidgets.QWidget(self)
        self._layout = QtWidgets.QVBoxLayout()
        main_widget.setLayout(self._layout)

        self.options = OptionsPanel(parent=main_widget)
        self.options.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        )

        self.console = Console(parent=main_widget)
        self.console.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )

        self._layout.addWidget(self.options)
        self._layout.addWidget(self.console)
        self.buttons_layout = QtWidgets.QHBoxLayout()
        self._layout.addLayout(self.buttons_layout)
        self.clearLogButton = QtWidgets.QPushButton(text="Clear Console")
        self.clearLogButton.clicked.connect(self.console.clear)
        self.buttons_layout.addItem(
            QtWidgets.QSpacerItem(
                0,
                0,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Minimum
            )
        )
        self.buttons_layout.addWidget(self.clearLogButton)

        self.buttons_layout.addItem(
            QtWidgets.QSpacerItem(
                0,
                0,
                QtWidgets.QSizePolicy.Expanding,
                QtWidgets.QSizePolicy.Minimum
            )
        )
        self.setCentralWidget(main_widget)
        # ==================
        self.worker_thread: typing.Optional[QtCore.QThread] = None

        # Set state to idle
        self.current_state: AbsState = IdleState(self)
        self.console.directories_entered.connect(
            lambda paths: self.current_state.run(paths)
        )

    def run(self, paths: typing.List[str]) -> None:
        """Run baggit on the paths given."""
        self.current_state.run(paths)


class Worker(QtCore.QObject):
    finished = QtCore.Signal()
    progress = QtCore.Signal(int)

    # OPTIONS_CLI are from "options.ui" in the optionGroupBox widgets
    OPTIONS_CLI: typing.Dict[str, str] = {
        'optionValidate': '--validate',
        'optionNoChecksum': '--no-checksums',
        'optionFast': '--fast',
        'optionNoSystemFiles': '--no-system-files'
    }

    def run(
            self,
            paths: typing.Iterable[str] = None,
            options: typing.Dict[str, bool] = None
    ) -> None:
        options = options or {}
        paths = paths or []

        for i, path in enumerate(paths):
            args = self.get_matching_cli_args(path, options)

            QtCore.QCoreApplication.processEvents()
            grabbags_args = grabbags._make_parser().parse_args(args)

            starting_message = \
                f"Looking in the following directories: " \
                f"{', '.join(grabbags_args.directories)}"

            grabbags.LOGGER.info(starting_message)
            grabbags.run(args=grabbags_args)
            self.progress.emit(i + 1)
        self.finished.emit()

    def get_matching_cli_args(
            self, path: str, options: typing.Dict[str, bool]
    ) -> typing.List[str]:
        """Match the gui options to the CLI version of args.

        Args:
            path:
            options:

        Returns:
            Return the CLI version of the args.

        """
        args = [path]
        for key, value in options.items():
            if key in self.OPTIONS_CLI and value is True:
                args.append(self.OPTIONS_CLI[key])
        return args


class ConsoleLogHandler(logging.Handler):
    def __init__(self,
                 widget: Console,
                 level: int = logging.NOTSET) -> None:

        super().__init__(level)
        self.formatter = QtHtmlFormatter()
        self.widget = widget

    def emit(self, record: logging.LogRecord) -> None:
        if self.formatter is not None:
            self.widget.write(self.formatter.format(record))


class QtHtmlFormatter(logging.Formatter):

    def format(self, record):
        message_text = super().format(record)
        level_styles = {
            "WARNING": "color:yellow",
            "ERROR": "color:red",
        }
        return f"<div style='{level_styles.get(record.levelname)}'>" \
               f"<p>{message_text}<p>" \
               f"</div>"


def main(argv: typing.Optional[typing.List[str]] = None) -> None:
    """Start the main entry point for the gui."""
    argv = argv or sys.argv

    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    app = QtWidgets.QApplication(argv)
    main_window = MainWindow()
    console_log_handler = ConsoleLogHandler(main_window.console)
    grabbags.LOGGER.setLevel(logging.INFO)
    grabbags.LOGGER.addHandler(console_log_handler)
    bagit.LOGGER.addHandler(console_log_handler)
    bagit.LOGGER.setLevel(logging.INFO)
    main_window.setWindowTitle("Grabbags GUI Demo")
    main_window.resize(640, 480)
    main_window.show()
    main_window.console.pop_alert("Drag folders over here")
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
