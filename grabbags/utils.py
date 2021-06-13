import os
import re
import logging
import abc
import shutil
import typing
import subprocess
try:
    from importlib import metadata
except ImportError:
    import importlib_metadata as metadata  # type: ignore

MODULE_NAME = "grabbags" if __name__ == "__main__" else __name__

LOGGER = logging.getLogger(MODULE_NAME)

SYSTEM_FILES = [
    ".DS_Store",
    "Thumbs.db",
    "Icon\r"
]

APPLE_DOUBLE_REGEX = re.compile(r"^\._.*$")


def is_system_file(file_path) -> bool:
    """Check if a given file is a system file

    This should be helpful for iterating over files and determine if a file in
    a packing can be removed.

    Note:
        Files that are identified as a system file are:

            * .DS_Store
            * Thumbs.db
            * `AppleDouble files <https://en.wikipedia.org/wiki/AppleSingle_and_AppleDouble_formats>`_
            * `Icon resource forks <https://superuser.com/questions/298785/icon-file-on-os-x-desktop/298798#298798>`_

    Returns:
        True if the file a system file,
        False if it's not

    """  # noqa

    if os.path.isdir(file_path):
        return False

    root_path, filename = os.path.split(file_path)

    if filename in SYSTEM_FILES:
        return True

    res = APPLE_DOUBLE_REGEX.findall(filename)
    if len(res) > 0:
        return True

    return False


def remove_system_files(root) -> None:
    """
    Remove system nested within a directory. Files such as DS_Store & Thumbs.db

    Note:

        This function works recursively.

    Args:
        root: path to a folder

    """
    for root, dirs, files in os.walk(root):
        for file_ in files:
            full_path = os.path.join(root, file_)

            if is_system_file(full_path):
                LOGGER.warn("Removing {}".format(full_path))
                os.remove(full_path)


class InvalidStrategy(Exception):
    """Invalid strategy for the current situation."""


class VersionStrategy(abc.ABC):
    """Base class for determining version information."""

    @abc.abstractmethod
    def get_version(self) -> str:
        """Get version information.

        If unable to do so, an InvalidStrategy exception is raised.

        Returns:
            Version info as a string.
        """


class VersionFromMetadata(VersionStrategy):
    """Gets version info from the package metadata"""
    def get_version(self) -> str:
        try:
            return metadata.version(__package__)
        except metadata.PackageNotFoundError as error:
            raise InvalidStrategy from error


class VersionFromGitCommit(VersionStrategy):
    """Gets version info from git commit."""

    def get_version(self) -> str:
        git_exec = shutil.which('git')
        if git_exec is None:
            raise InvalidStrategy("Git not available")
        try:
            git_commit_hash_command = [
                git_exec,
                'rev-parse', '--short', 'HEAD'
            ]
            git_hash = subprocess.check_output(git_commit_hash_command)
        except subprocess.CalledProcessError as error:
            raise InvalidStrategy(
                f"Unable to determine git hash, reason: {error}"
            ) from error
        return f"git: {git_hash.decode('ascii')}"


def current_version(strategies: typing.List[VersionStrategy] = None) -> str:
    """Get the current version number of Grabbags.

    This runs through the various strategies to determine grabbags's version.
    The first strategy to produce a value is used.

    By default the strategies order is as follows:

        1) Check if there is package metadata (usually .egg-info)
            file which is generated when grabbags is installed.

        2) Check if the current version is a git repo and if so, get the short
            commit hash value for the HEAD.

    When all else fails. The return value is 'Unknown'

    Args:
        strategies: List of strategies to determine the version.

    Returns:
        Returns the version number as a string or "Unknown"

    """
    strategies = strategies if strategies is not None else [
        VersionFromMetadata(),
        VersionFromGitCommit()
    ]
    for strategy in strategies:
        try:
            return strategy.get_version()
        except InvalidStrategy:
            continue
    return "Unknown"
