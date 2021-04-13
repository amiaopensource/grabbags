import argparse
import os
from unittest.mock import Mock

import grabbags.utils
import pytest


def test_batch_validate():
    # provide a directory
    pass


def test_bulk_creation():
    pass


def test_delete_annoying_files():
    sample_file = os.path.join(os.getcwd(), "dummy.txt")

    assert grabbags.utils.is_system_file(sample_file) is False


@pytest.mark.parametrize("entry,", [
        "._somethingsomething",
        "._f",
        "._~",
        "._something",
    ])
def test_apple_doubles_valid(entry):
    assert grabbags.utils.is_system_file(entry) is True


@pytest.mark.parametrize("entry,", [
    ".s",
    "asdfa.yes",
    "_.fdjlkdfj",
    "something._something",
    "fdjklfj ._ dklj",
    ".dj_djfklj"
])
def test_not_apple_doubles(entry):
    assert grabbags.utils.is_system_file(entry) is False


class TestCliArgs:

    @pytest.mark.parametrize("cli_args", [
        ["--help"],
        ["-h"],
        ['--version'],
        ['-v'],
    ])
    def test_single_shot_commands(self, cli_args):
        # Test commands that don't actually run bags but quit with return code
        # of zero before, such as help
        from grabbags import grabbags

        with pytest.raises(SystemExit) as e:
            grabbags.main(cli_args, runner=Mock())

        assert \
            e.value.args[0] == 0, \
            "if system exit is called with anything other than zero, the " \
            "grabbags did not close successfully"

    def test_invalid_processes(self):
        from grabbags import grabbags
        with pytest.raises(SystemExit) as e:
            grabbags.main(['somedir', '--processes=-1'])
        assert e.value.args[0] != 0

    def test_invalid_fast_without_valid(self):
        from grabbags import grabbags
        with pytest.raises(SystemExit) as e:
            grabbags.main(['somedir', '--fast'])
        assert e.value.args[0] != 0

    def test_main_calls_callback(self):
        from grabbags import grabbags
        run = Mock()
        grabbags.main(['somedir'], runner=run)
        assert run.called is True


