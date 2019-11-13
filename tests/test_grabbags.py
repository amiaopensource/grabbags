import os

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
        "._/something",
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
