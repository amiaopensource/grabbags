import argparse
import logging
import os
from unittest.mock import Mock, ANY, call

import grabbags.utils
import pytest
import bagit

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


@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
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


@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
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


@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
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


@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
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


@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
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


@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
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


@pytest.mark.filterwarnings("ignore::DeprecationWarning",
                            "ignore::PendingDeprecationWarning"
                            )
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


@pytest.mark.filterwarnings("ignore::DeprecationWarning",
                            "ignore::PendingDeprecationWarning"
                            )
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


@pytest.mark.filterwarnings("ignore::DeprecationWarning",
                            "ignore::PendingDeprecationWarning"
                            )
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


class TestGrabbagsRunner:
    def test_run_validate(self, fake_bag_path, monkeypatch):
        from grabbags import grabbags
        from argparse import Namespace
        args = Namespace(
            action_type='validate',
            directories=[
                fake_bag_path
            ]
        )
        runner = grabbags.GrabbagsRunner()
        execute = Mock()
        monkeypatch.setattr(grabbags.ValidateBag, "execute", execute)
        runner.run(args)
        execute.assert_called()

    def test_run_cleaned(self, fake_bag_path, monkeypatch):
        from grabbags import grabbags
        from argparse import Namespace
        args = Namespace(
            action_type='clean',
            directories=[
                fake_bag_path
            ]
        )
        runner = grabbags.GrabbagsRunner()
        execute = Mock()
        monkeypatch.setattr(grabbags.CleanBag, "execute", execute)
        runner.run(args)
        execute.assert_called()

    def test_run_create(self, fake_bag_path, monkeypatch):
        from grabbags import grabbags
        from argparse import Namespace
        args = Namespace(
            action_type='create',
            directories=[
                fake_bag_path
            ]
        )
        runner = grabbags.GrabbagsRunner()
        execute = Mock()
        monkeypatch.setattr(grabbags.MakeBag, "execute", execute)
        runner.run(args)
        execute.assert_called()

    def test_run_create_invalid_bag_error(self, fake_bag_path, caplog, monkeypatch):
        from grabbags import grabbags
        from bagit import BagError
        from argparse import Namespace
        runner = grabbags.GrabbagsRunner()
        execute = Mock(side_effect=BagError)
        monkeypatch.setattr(grabbags.MakeBag, "execute", execute)
        args = Namespace(
            action_type='create',
            directories=[
                fake_bag_path
            ]
        )
        runner.run(args)
        assert any("could not be bagged" in m for m in caplog.messages)

    def test_run_validate_invalid_bag_error(self, fake_bag_path, caplog, monkeypatch):
        from grabbags import grabbags
        from bagit import BagError
        from argparse import Namespace
        runner = grabbags.GrabbagsRunner()
        execute = Mock(side_effect=BagError)
        monkeypatch.setattr(grabbags, "is_bag", lambda x: True)
        monkeypatch.setattr(grabbags.bagit.Bag, "_open", Mock())
        monkeypatch.setattr(grabbags.bagit.Bag, "validate", execute)
        args = Namespace(
            processes=1,
            fast=False,
            no_checksums=False,
            action_type='validate',
            directories=[
                fake_bag_path
            ]
        )
        runner.run(args)
        assert any("is invalid" in m for m in caplog.messages)

    def test_run_clean_invalid_bag_error(self, fake_bag_path, caplog,
                                         monkeypatch):
        from grabbags import grabbags
        from bagit import BagError
        from argparse import Namespace
        runner = grabbags.GrabbagsRunner()
        execute = Mock(side_effect=BagError)
        monkeypatch.setattr(grabbags.CleanBag, "execute", execute)
        args = Namespace(
            action_type='clean',
            directories=[
                fake_bag_path
            ]
        )

        runner.run(args)
        assert any("cannot be cleaned" in m for m in caplog.messages)

    def test_run_create_empty_bag(self, tmpdir, caplog):
        from argparse import Namespace
        from grabbags import grabbags
        # .ensure() for files .ensure_dir for directories (makes a new file or dir if none exists)
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
        runner = grabbags.GrabbagsRunner()
        runner.run(args)
        assert (tmpdir / "empty_bag" / "data").exists() is False
        assert any("is an empty directory" in m for m in caplog.messages)

    def test_run_clean_no_system_files_message(self, tmpdir, caplog):
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
        runner = grabbags.GrabbagsRunner()
        runner.run(run_args)

        args = Namespace(
            action_type='clean',
            directories=[
                tmpdir
            ]
        )
        runner.run(args)
        assert any("No system files located" in m for m in caplog.messages)

    def test_run_clean_not_found(self, tmpdir, caplog):
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
        runner = grabbags.GrabbagsRunner()
        runner.run(run_args)
        (tmpdir / "bag" / "data" / "unexpected_file.txt").ensure()
        args = Namespace(
            action_type='clean',
            directories=[
                tmpdir
            ]
        )
        runner.run(args)
        assert any("Found file not in manifest" in m for m in caplog.messages)

    def test_run_clean_counting(self, monkeypatch, tmpdir, caplog):

        from grabbags import grabbags
        from argparse import Namespace
        caplog.set_level(logging.INFO)

        (tmpdir / "valid_bag" / "text.txt").ensure()
        (tmpdir / "empty_bag").ensure_dir()

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
        create_runner = grabbags.GrabbagsRunner()
        create_runner.run(run_args)
        assert \
            len(create_runner.successes) == 1 and \
            len(create_runner.skipped) == 1

        files = [
            "sdadfasdfdsaf.mp4",
            "asdfasdfasdffasdfasdf.mp4",
            "still_image_1.jpg",
            "still_image_2.jpg",
            "is_this_an_evil_confusing_access_copy.mp4"
        ]
        for f in files:
            (tmpdir / "skipped" / f).ensure()

        for num in range(20):
            (tmpdir / "skipped" / f"evil_file{num}.mp4").ensure()

        args = Namespace(
            action_type='clean',
            directories=[
                tmpdir
            ]
        )
        cleaning_runner = grabbags.GrabbagsRunner()
        cleaning_runner.run(args)

        assert any("No system files located" in m for m in caplog.messages)
        assert len(cleaning_runner.successes) == 0, "wrong successes"
        assert len(cleaning_runner.skipped) == 0, "wrong skipped"
        assert len(cleaning_runner.not_a_bag) == 2

    def test_run_clean_counting_only(self, monkeypatch, tmpdir):

        from grabbags import grabbags
        from argparse import Namespace

        (tmpdir / "valid_bag" / "text.txt").ensure()
        (tmpdir / "empty_bag").ensure_dir()

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
        create_runner = grabbags.GrabbagsRunner()
        create_runner.run(run_args)
        assert \
            len(create_runner.successes) == 1 and \
            len(create_runner.skipped) == 1

    def test_run_clean_only(self, monkeypatch, tmpdir):
        from grabbags import grabbags
        from argparse import Namespace

        for f in [
            "sdadfasdfdsaf.mp4",
            "asdfasdfasdffasdfasdf.mp4",
            "still_image_1.jpg",
            "still_image_2.jpg",
            "is_this_an_evil_confusing_access_copy.mp4"
        ]:
            (tmpdir / "skipped" / f).ensure()

        for num in range(20):
            (tmpdir / "skipped" / f"evil_file{num}.mp4").ensure()

        args = Namespace(
            action_type='clean',
            directories=[
                tmpdir
            ]
        )
        cleaning_runner = grabbags.GrabbagsRunner()
        cleaning_runner.run(args)

        assert len(cleaning_runner.successes) == 0, "wrong successes"
        assert len(cleaning_runner.skipped) == 0, "wrong skipped"
        assert len(cleaning_runner.not_a_bag) == 1


class TestValidateBag:
    def test_fails_is_bag(self, monkeypatch):
        from grabbags import grabbags
        args = argparse.Namespace()

        logger = logging.getLogger(__name__)
        runner = grabbags.ValidateBag(args, logger)
        some_directory = "something"

        with monkeypatch.context() as mp:
            mp.setattr(grabbags, "is_bag", lambda x: False)
            runner.execute(some_directory)

        assert len(runner.not_a_bag) == 1 and \
               runner.not_a_bag[0] == some_directory
        assert len(runner.successes) == 0

    def test_success(self, monkeypatch):
        from grabbags import grabbags
        some_directory = "something"
        run_args = argparse.Namespace(
            action_type='validate',
            no_system_files=True,
            bag_info={},
            processes=1,
            checksums=[],
            fast=False,
            no_checksums=False,
            directories=[
                some_directory
            ]
        )

        logger = logging.getLogger(__name__)
        runner = grabbags.ValidateBag(run_args, logger)

        with monkeypatch.context() as mp:
            mp.setattr(grabbags, "is_bag", lambda x: True)

            bag = Mock()
            mp.setattr(grabbags.bagit, "Bag", bag)

            runner.execute(some_directory)

        assert len(runner.successes) == 1 and \
               runner.successes[0] == some_directory

    @pytest.mark.parametrize(
        "exception_type, exception_message",
        [
            (bagit.BagValidationError, "somethings is wrong with your bag"),
            (bagit.ChecksumMismatch, "somethings is wrong with your checksum"),
            (bagit.FileMissing, "a file missing YO!!!"),
            (bagit.UnexpectedFile, "You have an unexpected file"),
        ]
    )
    def test_bag_validation_failure(self, monkeypatch,
                                    exception_type,
                                    exception_message):
        from grabbags import grabbags
        some_directory = "something"
        run_args = argparse.Namespace(
            action_type='validate',
            no_system_files=True,
            bag_info={},
            processes=1,
            checksums=[],
            fast=False,
            no_checksums=False,
            directories=[
                some_directory
            ]
        )

        logger = logging.getLogger(__name__)
        runner = grabbags.ValidateBag(run_args, logger)

        with monkeypatch.context() as mp:
            mp.setattr(grabbags, "is_bag", lambda x: True)

            mp.setattr(grabbags.bagit.Bag, "_open", Mock())
            mp.setattr(
                grabbags.bagit.Bag, "validate",
                Mock(
                    side_effect=exception_type(exception_message)
                )
            )

            runner.execute(some_directory)

        assert len(runner.successes) == 0 and \
               len(runner.failures) == 1

    def test_no_checks_completeness_only(self, monkeypatch):
        from grabbags import grabbags
        some_directory = "something"
        run_args = argparse.Namespace(
            action_type='validate',
            no_system_files=True,
            bag_info={},
            processes=1,
            checksums=[],
            fast=False,
            no_checksums=True,
            directories=[
                some_directory
            ]
        )

        logger = logging.getLogger(__name__)

        with monkeypatch.context() as mp:
            runner = grabbags.ValidateBag(run_args, logger)
            mp.setattr(grabbags, "is_bag", lambda x: True)

            bag = Mock(validate=Mock())

            def mock_bag(*args, **kwargs):
                return bag

            mp.setattr(grabbags.bagit, "Bag", mock_bag)

            runner.execute(some_directory)

            bag.validate.assert_any_call(
                processes=ANY,
                fast=ANY,
                completeness_only=True
            )

        assert len(runner.successes) == 1 and \
               runner.successes[0] == some_directory


class TestClean:

    @pytest.fixture()
    def empty_bag_path(self, tmpdir):
        source_dir = tmpdir.ensure_dir()

        (tmpdir / "bag-info.txt").write_text(
            """Bag-Software-Agent: bagit.py v1.8.1 <https://github.com/LibraryOfCongress/bagit-python>
Bagging-Date: 2021-05-04
Payload-Oxum: 13864945.6
""",
            encoding="utf-8")

        (tmpdir / "bagit.txt").write_text(
            """BagIt-Version: 0.97
Tag-File-Character-Encoding: UTF-8
""",
            encoding="utf-8")

        (tmpdir / "manifest-md5.txt").ensure()
        (tmpdir / "tagmanifest-md5.txt").ensure()
        (tmpdir / "data").ensure_dir()

        return source_dir

    def test_empty_clean(self, empty_bag_path):
        from grabbags import grabbags
        some_directory = empty_bag_path.strpath
        run_args = argparse.Namespace(
            action_type='clean',
            no_system_files=True,
            bag_info={},
            processes=1,
            checksums=[],
            fast=False,
            no_checksums=True,
            directories=[
                some_directory
            ]
        )

        runner = grabbags.CleanBag(run_args)
        runner.execute(some_directory)
        assert runner.successful is True

    def test_clean_manifest_includes_hidden_file(self, empty_bag_path):
        # skips a directory that is not a bag and contains hidden files
        # skips a directory that is not a bag and contains NO hidden files
        # creates a test bag that contains a manifest file that INCLUDES hidden
        # files
        from grabbags import grabbags
        new_bag_path = empty_bag_path
        some_directory = new_bag_path.strpath
        run_args = argparse.Namespace(
            action_type='clean',
            no_system_files=True,
            bag_info={},
            processes=1,
            checksums=[],
            fast=False,
            no_checksums=True,
            directories=[
                some_directory
            ]
        )

        (new_bag_path / "manifest-md5.txt").write_text(
            """4990c459b26dd57fc4aac9d918ac61b4  data/DSC_0068.JPG
4990c459b26dd57fc4aac9d918ac61b4  data/.DS_Store
            """,
            encoding="utf-8"
        )

        (new_bag_path / "data" / "DSC_0068.JPG").ensure()
        (new_bag_path / "data" / ".DS_Store").ensure()

        runner = grabbags.CleanBag(run_args)
        runner.execute(some_directory)
        assert runner.successful is True and \
               (new_bag_path / "data" / ".DS_Store").exists() and \
               (new_bag_path / "data" / "DSC_0068.JPG").exists()

    def test_clean_manifest_does_not_include_hidden_file(self, empty_bag_path):
        # creates a test bag that contains a manifest with NO hidden files, but
        # hidden files are present in the data folder
        from grabbags import grabbags
        new_bag_path = empty_bag_path
        some_directory = new_bag_path.strpath
        run_args = argparse.Namespace(
            action_type='clean',
            no_system_files=True,
            bag_info={},
            processes=1,
            checksums=[],
            fast=False,
            no_checksums=True,
            directories=[
                some_directory
            ]
        )

        (new_bag_path / "manifest-md5.txt").write_text(
            """4990c459b26dd57fc4aac9d918ac61b4  data/DSC_0068.JPG
            """,
            encoding="utf-8"
        )

        (new_bag_path / "data" / "DSC_0068.JPG").ensure()
        (new_bag_path / "data" / ".DS_Store").ensure()

        runner = grabbags.CleanBag(run_args)
        runner.execute(some_directory)
        assert runner.successful is True and \
               not (new_bag_path / "data" / ".DS_Store").exists() and \
               (new_bag_path / "data" / "DSC_0068.JPG").exists()

    def test_clean_manifest_includes_hidden_file_and_extra_hidden_file(
            self, empty_bag_path):

        # EDGE CASE creates a test bag that contains a manifest file that
        # INCLUDES hidden files in the manifest AND additional hidden files NOT
        # in the manifest.
        from grabbags import grabbags
        new_bag_path = empty_bag_path
        some_directory = new_bag_path.strpath
        run_args = argparse.Namespace(
            action_type='clean',
            no_system_files=True,
            bag_info={},
            processes=1,
            checksums=[],
            fast=False,
            no_checksums=True,
            directories=[
                some_directory
            ]
        )

        (new_bag_path / "manifest-md5.txt").write_text(
            """4990c459b26dd57fc4aac9d918ac61b4  data/DSC_0068.JPG
4990c459b26dd57fc4aac9d918ac61b4  data/.DS_Store
            """,
            encoding="utf-8"
        )

        (new_bag_path / "data" / "DSC_0068.JPG").ensure()
        (new_bag_path / "data" / ".DS_Store").ensure()
        (new_bag_path / "data" / "images" / ".DS_Store").ensure()

        runner = grabbags.CleanBag(run_args)
        runner.execute(some_directory)
        assert runner.successful is True and \
               (new_bag_path / "data" / ".DS_Store").exists() and \
               (new_bag_path / "data" / "DSC_0068.JPG").exists() and \
               not (new_bag_path / "data" / "images" / ".DS_Store").exists()
