import pytest
from unittest.mock import Mock

from grabbags import utils


class TestVersionStrategies:
    def test_importlib_metadata_success(self, monkeypatch):
        version = Mock()
        monkeypatch.setattr(utils.metadata, 'version',  version)
        utils.VersionFromMetadata().get_version()
        assert version.called is True

    def test_importlib_metadata_not_found(self, monkeypatch):
        try:
            from importlib import metadata
        except ImportError:
            import importlib_metadata as metadata

        monkeypatch.setattr(
            utils.metadata, 'version',
            Mock(side_effect=metadata.PackageNotFoundError)
        )
        with pytest.raises(utils.InvalidStrategy):
            utils.VersionFromMetadata().get_version()

    def test_version_from_git_commit_no_git(self, monkeypatch):
        import shutil
        which = Mock(return_value=None)
        monkeypatch.setattr(shutil, 'which', which)
        with pytest.raises(utils.InvalidStrategy):
            utils.VersionFromGitCommit().get_version()

    def test_version_from_git_commit_subprocess_error(self, monkeypatch):
        import shutil
        import subprocess
        monkeypatch.setattr(shutil, 'which', lambda x: 'git')
        check_output = Mock(
            side_effect=subprocess.CalledProcessError(
                returncode=1,
                cmd=['git', 'rev-parse', '--short', 'HEAD']
            )
        )
        monkeypatch.setattr(subprocess, 'check_output', check_output)
        with pytest.raises(utils.InvalidStrategy):
            utils.VersionFromGitCommit().get_version()

    def test_version_from_git_commit_success(self, monkeypatch):
        import shutil
        import subprocess
        monkeypatch.setattr(shutil, 'which', lambda x: 'git')
        check_output = Mock(return_value=b'0bdfa12')
        monkeypatch.setattr(subprocess, 'check_output', check_output)

        assert utils.VersionFromGitCommit().get_version() == 'git: 0bdfa12'

    def test_current_version_no_strategies(self):
        assert utils.current_version(strategies=[]) == "Unknown"

    def test_current_version_no_valid_strategies(self):
        # This test checks that when running out of version getting strategies,
        # it returns with the string 'Unknown' and not an exception or None

        class NotValidStrategy(utils.VersionStrategy):
            def get_version(self) -> str:
                raise utils.InvalidStrategy

        assert utils.current_version(
            strategies=[NotValidStrategy()]
        ) == "Unknown"
