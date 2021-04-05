from unittest.mock import Mock, MagicMock
import pytest
from grabbags import gui, grabbags


class TestArgMatching:

    def test_path_matches(self):
        test_path = "./some/file/path"
        cli_args = gui.Worker().get_matching_cli_args(
            path=test_path, options={}
        )
        assert test_path in cli_args

    def test_validate(self):
        test_path = "./some/file/path"
        cli_args = gui.Worker().get_matching_cli_args(
            path=test_path,
            options={"optionValidate": True}
        )
        assert "--validate" in cli_args

    def test_no_checksums(self):
        test_path = "./some/file/path"
        cli_args = gui.Worker().get_matching_cli_args(
            path=test_path,
            options={"optionNoChecksum": True}
        )
        assert "--no-checksums" in cli_args

    def test_fast(self):
        test_path = "./some/file/path"
        cli_args = gui.Worker().get_matching_cli_args(
            path=test_path,
            options={"optionFast": True}
        )
        assert "--fast" in cli_args

    def test_no_system_files(self):
        test_path = "./some/file/path"
        cli_args = gui.Worker().get_matching_cli_args(
            path=test_path,
            options={"optionNoSystemFiles": True}
        )
        assert "--no-system-files" in cli_args


class TestConsole:
    def test_dragged_data_true(self, qtbot):
        console = gui.Console()
        qtbot.add_widget(console)
        event = MagicMock()
        console.pop_alert = Mock()
        console.check_valid_dragged_data = Mock(return_value=True)
        console.dragEnterEvent(event)

        assert console.pop_alert.called is True and \
               event.accept.called is True

    def test_dragged_data_false(self, qtbot):
        console = gui.Console()
        qtbot.add_widget(console)
        event = MagicMock()
        console.pop_alert = Mock()
        console.check_valid_dragged_data = Mock(return_value=False)
        console.dragEnterEvent(event)

        assert console.pop_alert.called is True and \
               event.ignore.called is True

    @pytest.mark.parametrize("exists, isdir, is_valid", [
        (True, True, True),
        (False, True, False),
        (False, False, False),
        (True, False, False),
    ])
    def test_check_valid_dragged_data(self, monkeypatch, exists, isdir, is_valid):
        fake_folders = ["spam", "bacon", "eggs"]
        import os.path
        monkeypatch.setattr(os.path, "exists", lambda x: exists)
        monkeypatch.setattr(os.path, "isdir", lambda x: isdir)
        assert gui.Console.check_valid_dragged_data(fake_folders) is is_valid

    def test_write(self, qtbot):
        console = gui.Console()
        qtbot.add_widget(console)
        console.write("blababa")
        assert console.text() == "blababa"

    def test_clear(self, qtbot):
        console = gui.Console()
        qtbot.add_widget(console)
        console.write("blababa")
        assert console.text() == "blababa"
        console.clear()
        assert console.text() == ""

    def test_pop_alert_calls_setText_directly(self, qtbot):
        console = gui.Console()
        qtbot.add_widget(console)
        console.ui.consoleText.setText = Mock()
        console.pop_alert("blababa")
        assert console.ui.consoleText.setText.called is True and \
               "blababa" in \
               console.ui.consoleText.setText.call_args_list[0][0][0]

    def test_drop_event(self, qtbot):
        console = gui.Console()
        qtbot.add_widget(console)
        drop_event = MagicMock()
        with qtbot.waitSignal(console.directories_entered) as blocker:
            console.dropEvent(drop_event)
        assert drop_event.accept.called is True


def test_exception_creates_a_dialog_box(qtbot, monkeypatch):
    def mock_main(*args, **kwargs):
        raise UnboundLocalError("some local error")
    monkeypatch.setattr(grabbags, "main", mock_main)
    from PySide2 import QtWidgets
    showMessage = Mock()
    monkeypatch.setattr(QtWidgets.QErrorMessage, "showMessage", showMessage)
    mock_exec = Mock()
    monkeypatch.setattr(QtWidgets.QErrorMessage, "exec_", mock_exec)
    app = gui.MainWindow()
    qtbot.add_widget(app)
    app.run(['./spam'])
    qtbot.waitUntil(lambda: mock_exec.called is True)
    assert showMessage.called is True
