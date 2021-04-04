import argparse
import bagit
import gettext
import logging
import os
import re
import sys
from grabbags.bags import is_bag
import grabbags.utils
successes = []
failures = []
not_a_bag = []

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

MODULE_NAME = "grabbags" if __name__ == "__main__" else __name__

LOGGER = logging.getLogger(MODULE_NAME)

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
            "Use multiple processes to calculate checksums faster"
            " (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--log",
        help=_("The name of the log file (default: stdout)")
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help=_("Suppress all progress information other than errors"),
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help=_(
            "Remove remove any system files not in manifest of a bag."
            " The following files will be deleted: .DS_Store, Thumbs.db, "
            " Appledoubles (._*), Icon files"
        ),
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
            "Modify --validate behaviour to only test if the bag directory"
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
            "--%s" % header.lower(), type=str,
            action=bagit.BagHeaderAction, default=argparse.SUPPRESS
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
        level = logging.WARN
    else:
        level = logging.INFO
    if opts.log:
        logging.basicConfig(filename=opts.log, level=level, format=log_format)
    else:
        logging.basicConfig(level=level, format=log_format)


def validate_bag(bag_dir, args):
    if not is_bag(bag_dir.path):
        LOGGER.warn(_("%s is not a bag. Skipped."), bag_dir.path)
        not_a_bag.append(bag_dir.path)
        return 

    bag = bagit.Bag(bag_dir.path)
    # validate throws a BagError or BagValidationError
    bag.validate(
        processes=args.processes,
        fast=args.fast,
        completeness_only=args.no_checksums,
    )
    successes.append(bag_dir.path)
    if args.fast:
        LOGGER.info(_("%s valid according to Payload-Oxum"), bag_dir.path)
    elif args.no_checksums:
        LOGGER.info(
            _("%s valid according to Payload-Oxum and file manifest"),
            bag_dir.path
        )
    else:
        LOGGER.info(_("%s is valid"), bag_dir.path) 


def clean_bag(bag_dir):
    if not is_bag(bag_dir.path):
        LOGGER.warning(_("%s is not a bag. Not cleaning."), bag_dir.path)
        return

    bag = bagit.Bag(bag_dir.path)
    if bag.compare_manifests_with_fs()[1]:
        for payload_file in bag.compare_manifests_with_fs()[1]:
            if grabbags.utils.is_system_file(payload_file):
                LOGGER.info("Removing {}".format(bag_dir.path))
                os.remove(payload_file)
            else:
                LOGGER.warning("Not removing {}".format(bag_dir.path))


def make_bag(bag_dir, args):
    if is_bag(bag_dir.path):
        LOGGER.warning(_("%s is already a bag. Skipped."), bag_dir.path)
        return

    if args.no_system_files is True:
        LOGGER.info(_("Cleaning %s of system files"), bag_dir.path)
        grabbags.utils.remove_system_files(root=bag_dir.path)

    bag = bagit.make_bag(
            bag_dir.path,
            bag_info=args.bag_info,
            processes=args.processes,
            checksums=args.checksums
        )
    successes.append(bag_dir.path)
    LOGGER.info(_("Bagged %s"), bag.path)


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
            if args.validate:
                action = 'validated'
                try:
                    validate_bag(bag_dir, args)
                except bagit.BagError as e:
                    LOGGER.error(
                        _("%(bag)s is invalid: %(error)s"),
                        {"bag": bag_dir.path, "error": e}
                    )
                    failures.append(bag_dir.path)
            elif args.clean:
                action = 'cleaned'
                try:
                    clean_bag(bag_dir)
                    successes.append(bag_dir.path)
                except bagit.BagError as e:
                    LOGGER.error(
                        _("%(bag)s cannot be cleaned: %(error)s"),
                        {"bag": bag_dir.path, "error": e}
                    )
                    failures.append(bag_dir.path)
            else:
                action = 'created'
                try:
                    make_bag(bag_dir, args)
                    #successes.append(bag_dir.path)
                except bagit.BagError as e:
                    LOGGER.error(
                        _("%(bag)s could not be bagged: %(error)s"),
                        {"bag": bag_dir.path, "error": e}
                    )
                    failures.append(bag_dir.path)

    LOGGER.info(
        _("%(count)s bags %(action)s successfully"),
        {"count": len(successes), "action": action}
    )
    if failures and len(failures) > 0:
        LOGGER.warning(
            _("%(count)s bags not %(action)s"),
            {"count": len(failures), "action": action}
        )
        LOGGER.warning(
            _("Failed for the following folders: %s"),
            ", ".join(failures)
        )
    if not_a_bag and len(not_a_bag) > 0:
        LOGGER.warning(
            _("%(count)s folders are not bags"),
            {"count": len(not_a_bag)}
        )
        LOGGER.warning(
            _("The following folders are not bags: %s"),
            ", ".join(not_a_bag)
        )

if __name__ == "__main__":
    main()