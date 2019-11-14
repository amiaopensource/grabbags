import argparse
import bagit
import gettext
import logging
import os
import re
import sys
from grabbags.bags import is_bag
import grabbags.utils


def find_locale_dir():
    for prefix in (os.path.dirname(__file__), sys.prefix):
        locale_dir = os.path.join(prefix, "locale")
        if os.path.isdir(locale_dir):
            return locale_dir

TRANSLATION_CATALOG = gettext.translation(
    "bagit-python", localedir=find_locale_dir(), fallback=True
)
if sys.version_info < (3,):
    _ = TRANSLATION_CATALOG.ugettext
else:
    _ = TRANSLATION_CATALOG.gettext

__doc__ = (
    _(
        """
grabbag.py is an enhancement on the bagit-python for dealing with lots of bags.
Command-Line Usage:
Basic usage is to give bagit.py a directory to bag up:
    $ grabbag.py my_directory
This does a bag-in-place operation for each sub-folder of my_directory.
You can bag sub-folders from multiple directories if you wish:
    $ grabbag.py directory1 directory2
Optionally you can provide metadata which will be stored in bag-info.txt:
    $ grabbag.py --source-organization "Library of Congress" directory
You can also select which manifest algorithms will be used:
    $ grabbag.py --sha1 --md5 --sha256 --sha512 directory
"""
    )
    % globals()
)

class BagArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        argparse.ArgumentParser.__init__(self, *args, **kwargs)
        self.set_defaults(bag_info={})

def _make_parser():
    parser = BagArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="grabbags!!!",
    )
    parser.add_argument(
        "--processes",
        type=int,
        dest="processes",
        default=1,
        help=_(
            "Use multiple processes to calculate checksums faster (default: %(default)s)"
        ),
    )
    parser.add_argument("--log", help=_("The name of the log file (default: stdout)"))
    parser.add_argument(
        "--quiet",
        action="store_true",
        help=_("Suppress all progress information other than errors"),
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help=_(
            "Validate existing bags in the provided directories instead of"
            " creating new ones"
        ),
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help=_(
            "Modify --validate behaviour to only test whether the bag directory"
            " has the number of files and total size specified in Payload-Oxum"
            " without performing checksum validation to detect corruption."
        ),
    )
    parser.add_argument(
        "--no-checksums",
        "--completeness-only",
        action="store_true",
        help=_(
            "Modify --validate behaviour to test whether the bag directory"
            " has the expected payload specified in the checksum manifests"
            " without performing checksum validation to detect corruption."
        ),
    )

    parser.add_argument(
        "--no-system-files",
        action="store_true",
        help=_(
            "Modify bag creation to delete any system files before bagging"
            " The following files will be deleted: .DS_Store, Thumbs.db, "
            " Appledoubles (._*), Icon files"
        ),
    )

    checksum_args = parser.add_argument_group(
        _("Checksum Algorithms"),
        _(
            "Select the manifest algorithms to be used when creating bags"
            " (default=%s)"
        )
        % ", ".join(bagit.DEFAULT_CHECKSUMS),
    )

    for i in bagit.CHECKSUM_ALGOS:
        alg_name = re.sub(r"^([A-Z]+)(\d+)$", r"\1-\2", i.upper())
        checksum_args.add_argument(
            "--%s" % i,
            action="append_const",
            dest="checksums",
            const=i,
            help=_("Generate %s manifest when creating a bag") % alg_name,
        )

    metadata_args = parser.add_argument_group(_("Optional Bag Metadata"))
    for header in bagit.STANDARD_BAG_INFO_HEADERS:
        metadata_args.add_argument(
            "--%s" % header.lower(), type=str, action=bagit.BagHeaderAction, default=argparse.SUPPRESS
        )

    parser.add_argument(
        "directories",
        nargs="+",
        help=_(
            "Parent directory of directory which will be converted"
            " into a bag in place by moving any existing files into"
            " the BagIt structure and creating the manifests and"
            " other metadata."
        ),
    )

    return parser


def _configure_logging(opts):
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    if opts.quiet:
        level = logging.ERROR
    else:
        level = logging.INFO
    if opts.log:
        logging.basicConfig(filename=opts.log, level=level, format=log_format)
    else:
        logging.basicConfig(level=level, format=log_format)


def main():

    parser = _make_parser()
    args = parser.parse_args()

    if args.processes < 0:
        parser.error(_("The number of processes must be 0 or greater"))

    if args.fast and not args.validate:
        parser.error(_("--fast is only allowed as an option for --validate!"))

    _configure_logging(args)
    for bag_parent in args.directories:
        for bag_dir in filter(lambda i: i.is_dir(), os.scandir(bag_parent)):
            print(bag_dir.path)

            if is_bag(bag_dir.path):
                print("{} is already a bag".format(bag_dir.path))
                continue

            if args.no_system_files is True:
                print("Cleaning {} of system files".format(bag_dir.path))
                grabbags.utils.remove_system_files(root=bag_dir.path)

            bag = bagit.make_bag(
                bag_dir.path,
                bag_info=args.bag_info,
                processes=args.processes,
                checksums=args.checksums)

            print(bag)


if __name__ == "__main__":
    main()
