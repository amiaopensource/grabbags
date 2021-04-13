import os

import pytest
import shutil
import grabbags.bags
import pathlib

@pytest.fixture()
def sample_bags(tmpdir_factory):
    data_dir = tmpdir_factory.mktemp("data")
    bags = {
        "valid": [
            {
                "root": "1",
                "dirs": [

                    ["data"],
                    ["data", "preservation"],
                    ["data", "service"],
                ],
                "files": [
                    ["bagit.txt"],
                    ["data", "preservation","napl0154.mov"],
                    ["data", "service", "napl0154.mp4"],
                    ["manifest-sha256.txt"],
                    ["manifest-sha512.txt"],
                    ["tagmanifest-sha256.txt"],
                    ["tagmanifest-sha512.txt"],
                ]
            },
        ],
        "invalid": [
            {
                "root": "b1",
                "dirs": [
                    ["sample"]
                ],
                "files":[
                    ["sample", "dummy.txt"]
                ]
            }
        ]
    }
    for bag in (bags['valid'] + bags['invalid']):
        os.mkdir(os.path.join(data_dir, bag["root"]))
        for dir_ in bag['dirs']:
            os.mkdir(os.path.join(data_dir, bag["root"], *dir_))

        for file_path in bag['files']:
            sample_file_path = os.path.join(data_dir, bag["root"], *file_path)
            pathlib.Path(sample_file_path).touch()

    yield data_dir, bags
    shutil.rmtree(data_dir)


def test_validate_bag(sample_bags):
    data_dir, bags = sample_bags

    for valid in bags["valid"]:
        bag_dir = os.path.join(data_dir, valid['root'])
        assert os.path.exists(bag_dir)
        assert grabbags.bags.is_bag(bag_dir) is True

    for invalid in bags["invalid"]:
        bag_dir = os.path.join(data_dir, invalid['root'])
        assert os.path.exists(bag_dir)
        assert grabbags.bags.is_bag(bag_dir) is False
