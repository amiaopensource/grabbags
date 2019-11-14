import os


def is_bag(path) -> bool:
    """Check if the directory path given is a bag directory

    Args:
        path: path to potential bag root folder

    Returns: True if determined it's a bag directory, or False if it's not

    """

    if not os.path.exists(os.path.join(path, "bagit.txt")):
        return False

    if not os.path.exists(os.path.join(path, "data")):
        return False

    return True
