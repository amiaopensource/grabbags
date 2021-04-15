import argparse
import logging
import os
import sys
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


@pytest.mark.parametrize("system_file",
                         [
                             'Thumbs.db',
                             '.DS_Store',
                             '._test'
                         ])
def test_clean_bags_system_files(tmpdir, system_file):
    from grabbags import grabbags

    (tmpdir / "bag" / "text.txt").ensure()
    grabbags.main([tmpdir.strpath])
    (tmpdir / "bag" / "data" / system_file).ensure()
    grabbags.main([tmpdir.strpath, "--clean"])
    assert (tmpdir / "bag" / "data" / system_file).exists() is False
    assert (tmpdir / "bag" / "data" / "text.txt").exists()


def test_clean_bags_no_system_files(tmpdir):
    from grabbags import grabbags

    (tmpdir / "bag" / "text.txt").ensure()
    grabbags.main([tmpdir.strpath])
    grabbags.main([tmpdir.strpath, "--clean"])
    assert (tmpdir / "bag" / "data" / "text.txt").exists()


@pytest.mark.parametrize(
    "arguments",
    [
        ["--fast", "fakepath"],
        ['--no-checksums', "fakepath"],
        ['--no-checksums', '--no-system-files', "fakepath"],
        ['--validate', '--clean', "fakepath"],
        ['--clean', '--no-checksums', "fakepath"],
        ['--processes', 'j', "fakepath"],
        ['--validate', '--sha256', "fakepath"],
        ['--clean', '--no-system-files', "fakepath"],
        ['--clean', '--md5', "fakepath"],
        ['--clean'],
    ])
def test_invalid_cli_args(arguments):
    from grabbags import grabbags
    with pytest.raises(SystemExit):
        run = Mock()
        grabbags.main(arguments, runner=run)
        run.assert_not_called()


@pytest.mark.parametrize("arguments", [
    ['--validate', 'fakepath'],
    ['--validate', '--fast', 'fakepath'],
    ["fakepath"],
])
def test_valid_cli_args(tmpdir, arguments):
    from grabbags import grabbags
    run = Mock()
    grabbags.main(arguments, runner=run)
    run.assert_called()


@pytest.fixture()
def fake_bag_path(monkeypatch):
    fake_path_name = "fakepath"

    def scandir(path):
        if path == fake_path_name:
            for b in [
                Mock(is_dir=Mock(return_value=True),
                     path=os.path.join(path, "bag")
                     )
            ]:
                yield b
    monkeypatch.setattr(os, "scandir", scandir)
    return fake_path_name


def test_run_validate(monkeypatch, fake_bag_path):
    from grabbags import grabbags
    from argparse import Namespace
    args = Namespace(
        action_type='validate',
        directories=[
            fake_bag_path
        ]
    )
    validate_bag = Mock()
    monkeypatch.setattr(grabbags, "validate_bag", validate_bag)
    grabbags.run(args)
    validate_bag.assert_called()


def test_run_cleaned(monkeypatch, fake_bag_path):
    from grabbags import grabbags
    from argparse import Namespace
    args = Namespace(
        action_type='clean',
        directories=[
            fake_bag_path
        ]
    )
    clean_bag = Mock()
    monkeypatch.setattr(grabbags, "clean_bag", clean_bag)
    grabbags.run(args)
    clean_bag.assert_called()


def test_run_create(monkeypatch, fake_bag_path):
    from grabbags import grabbags
    from argparse import Namespace
    args = Namespace(
        action_type='create',
        directories=[
            fake_bag_path
        ]
    )
    make_bag = Mock()
    monkeypatch.setattr(grabbags, "make_bag", make_bag)
    grabbags.run(args)
    make_bag.assert_called()


def test_run_create_invalid_bag_error(monkeypatch, fake_bag_path, caplog):
    from grabbags import grabbags
    from bagit import BagError
    from argparse import Namespace
    make_bag = Mock(side_effect=BagError)
    monkeypatch.setattr(grabbags, "make_bag", make_bag)
    args = Namespace(
        action_type='create',
        directories=[
            fake_bag_path
        ]
    )
    grabbags.run(args)
    assert any("could not be bagged" in m for m in caplog.messages)


def test_run_validate_invalid_bag_error(monkeypatch, fake_bag_path, caplog):
    from grabbags import grabbags
    from bagit import BagError
    from argparse import Namespace
    validate_bag = Mock(side_effect=BagError)
    monkeypatch.setattr(grabbags, "validate_bag", validate_bag)
    args = Namespace(
        action_type='validate',
        directories=[
            fake_bag_path
        ]
    )
    grabbags.run(args)
    assert any("is invalid" in m for m in caplog.messages)


def test_run_clean_invalid_bag_error(monkeypatch, fake_bag_path, caplog):
    from grabbags import grabbags
    from bagit import BagError
    from argparse import Namespace
    clean_bag = Mock(side_effect=BagError)
    monkeypatch.setattr(grabbags, "clean_bag", clean_bag)
    args = Namespace(
        action_type='clean',
        directories=[
            fake_bag_path
        ]
    )
    grabbags.run(args)
    assert any("cannot be cleaned" in m for m in caplog.messages)


def test_run_create_empty_bag(monkeypatch, tmpdir, caplog):
    from argparse import Namespace
    from grabbags import grabbags

    (tmpdir / "empty_bag").ensure_dir()

    args = Namespace(
        action_type='create',
        no_system_files=True,
        bag_info={},
        processes=1,
        checksums=[],
        directories=[
            tmpdir.strpath
        ]
    )

    grabbags.run(args)
    assert (tmpdir / "empty_bag" / "data").exists() is False
    assert any("is an empty directory" in m for m in caplog.messages)



#
# @pytest.fixture()
# def fake_bag_path_with_no_system_file(tmpdir):
#     fake_path_name = "fakepath"
#
#     # def scandir(path):
#     #     if path == fake_path_name:
#     #         for b in [
#     #             Mock(is_dir=Mock(return_value=True),
#     #                  path=os.path.join(path, "bag")
#     #                  )
#     #         ]:
#     #             yield b
#     # monkeypatch.setattr(os, "scandir", scandir)
#     return fake_path_name
#

def test_run_clean_no_system_files_message(monkeypatch, tmpdir, caplog):

    from grabbags import grabbags
    from argparse import Namespace
    caplog.set_level(logging.INFO)

    (tmpdir / "bag" / "text.txt").ensure()
    run_args = Namespace(
        action_type='create',
        no_system_files=True,
        bag_info={},
        processes=1,
        checksums=["md5"],
        directories=[
            tmpdir
        ]
    )
    grabbags.run(run_args)

    args = Namespace(
        action_type='clean',
        directories=[
            tmpdir
        ]
    )
    grabbags.run(args)
    assert any("No system files located" in m for m in caplog.messages)


def test_run_clean_not_found(monkeypatch, tmpdir, caplog):

    from grabbags import grabbags
    from argparse import Namespace

    (tmpdir / "bag" / "text.txt").ensure()
    run_args = Namespace(
        action_type='create',
        no_system_files=True,
        bag_info={},
        processes=1,
        checksums=["md5"],
        directories=[
            tmpdir
        ]
    )

    grabbags.run(run_args)
    (tmpdir / "bag" / "data" / "unexpected_file.txt").ensure()
    args = Namespace(
        action_type='clean',
        directories=[
            tmpdir
        ]
    )
    grabbags.run(args)
    assert any("Found file not in manifest" in m for m in caplog.messages)

