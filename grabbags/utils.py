import os
import re

SYSTEM_FILES = [
    ".DS_Store",
    "Thumbs.db"
]

APPLE_DOUBLE_REGEX = re.compile(r"^\._.*$")


def is_system_file(file_path) -> bool:
    """Check if a given file is a system file

    This should be helpful for iterating over files and determine if a file in
    a packing can be removed.

    Returns:
        True if the file a system file,
        False if it's not

    """

    if os.path.isdir(file_path):
        return False

    root_path, filename = os.path.split(file_path)

    if filename in SYSTEM_FILES:
        return True

    res = APPLE_DOUBLE_REGEX.findall(file_path)
    if len(res) > 0:
        return True

    # TODO: Validate if Apple Icon file

    return False


def remove_system_files(root) -> None:
    for root, dirs, files in os.walk(root):
        for file_ in files:
            full_path = os.path.join(root, file_)

            if is_system_file(full_path):
                print("Removing {}".format(full_path))
                os.remove(full_path)