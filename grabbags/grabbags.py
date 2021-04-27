import abc
import argparse
import gettext
import logging
import os
import re
import sys
import typing
import warnings

import bagit

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
        '--version', "-v",
        action='version',
        version=grabbags.utils.current_version()
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
    command_group = parser.add_mutually_exclusive_group()
    command_group.add_argument(
        "--clean",
        dest="action_type",
        action="store_const",
        const="clean",
        help=_(
            "Remove remove any system files not in manifest of a bag."
            " The following files will be deleted: .DS_Store, Thumbs.db, "
            " Appledoubles (._*), Icon files"
        ),
    )
    command_group.add_argument(
        "--validate",
        dest="action_type",
        action="store_const",
        const="validate",
        help=_(
            "Validate existing bags in the provided directories instead of"
            " creating new ones"
        ),
    )
    parser.set_defaults(action_type='create')
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
    warnings.warn(
        "Use GrabbagsRunner.validate_bag() instead", DeprecationWarning
    )
    if not is_bag(bag_dir.path):
        LOGGER.warning(_("%s is not a bag. Skipped."), bag_dir.path)
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
    warnings.warn(
        "Use GrabbagsRunner.clean_bag() instead",
        DeprecationWarning
    )
    if not is_bag(bag_dir.path):
        LOGGER.warning(_("%s is not a bag. Not cleaning."), bag_dir.path)
        return

    bag = bagit.Bag(bag_dir.path)
    if bag.compare_manifests_with_fs()[1]:
        for payload_file in bag.compare_manifests_with_fs()[1]:
            if grabbags.utils.is_system_file(payload_file):
                LOGGER.info(
                    "Removing system files from {}".format(bag_dir.path)
                )
                os.remove(os.path.join(bag_dir.path, payload_file))
            else:
                LOGGER.warning(
                    "Found file not in manifest: {}".format(payload_file)
                )
    else:
        LOGGER.info(
            "No system files located in {}".format(bag_dir.path))


def make_bag(bag_dir: "os.DirEntry[str]", args):
    warnings.warn(
        "Use GrabbagsRunner.make_bag() instead",
        DeprecationWarning
    )
    if len(os.listdir(bag_dir.path)) == 0:
        LOGGER.warning(_("%s is an empty directory. Skipped."), bag_dir.path)
        return

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


class GrabbagsRunner:

    def __init__(self) -> None:
        self.successes: typing.List[str] = []
        self.failures: typing.List[str] = []
        self.not_a_bag: typing.List[str] = []
        self.skipped: typing.List[str] = []

    @staticmethod
    def find_bag_dirs(search_root: str) -> "typing.Iterable[os.DirEntry[str]]":
        yield from filter(lambda i: i.is_dir(), os.scandir(search_root))

    def _run_action(self,
                    action_type: str,
                    bag_dir: 'os.DirEntry[str]',
                    args: argparse.Namespace) -> None:

        actions: typing.Dict[str, AbsAction] = {
            "validate": ValidateBag(args, LOGGER),
            "clean": CleanBag(args, LOGGER),
            "create": MakeBag(args, LOGGER)

        }

        action: AbsAction = actions[action_type]
        try:
            action.execute(bag_dir=bag_dir.path)
        except bagit.BagError as error:
            if action_type == "validate":
                LOGGER.error(
                    _("%(bag)s is invalid: %(error)s"),
                    {"bag": bag_dir.path, "error": error}
                )
            elif action_type == "clean":
                LOGGER.error(
                    _("%(bag)s cannot be cleaned: %(error)s"),
                    {"bag": bag_dir.path, "error": error}
                )
            elif action_type == "create":
                LOGGER.error(
                    _("%(bag)s could not be bagged: %(error)s"),
                    {"bag": bag_dir.path, "error": error}
                )
            else:
                raise ValueError(
                    f"args contain invalid action_type: {args.action_type}"
                )
        finally:
            self.successes += action.successes
            self.failures += action.failures
            self.not_a_bag += action.not_a_bag
            self.skipped += action.skipped

    def run(self, args: argparse.Namespace) -> None:
        """Run the grabbags jobs based on the given user arguments.

        Args:
            args: Parsed user arguments.

        """
        for bag_parent in args.directories:
            for bag_dir in self.find_bag_dirs(bag_parent):

                self._run_action(action_type=args.action_type,
                                 bag_dir=bag_dir,
                                 args=args)


def run2(args: argparse.Namespace) -> None:
    """Run grabbags process with the parsed arguments provided.

    Args:
        args: Parsed arguments

    """
    runner = GrabbagsRunner()
    runner.run(args)

    action: str = {
        'validate': 'validated',
        'clean': 'cleaned',
        'create': 'created'
    }.get(args.action_type, "")

    LOGGER.info(
        _("%(count)s bags %(action)s successfully"),
        {"count": len(runner.successes), "action": action}
    )
    if runner.failures and len(runner.failures) > 0:
        LOGGER.warning(
            _("%(count)s bags not %(action)s"),
            {"count": len(runner.failures), "action": action}
        )
        LOGGER.warning(
            _("Failed for the following folders: %s"),
            ", ".join(runner.failures)
        )
    if runner.not_a_bag and len(runner.not_a_bag) > 0:
        LOGGER.warning(
            _("%(count)s folders are not bags"),
            {"count": len(runner.not_a_bag)}
        )
        LOGGER.warning(
            _("The following folders are not bags: %s"),
            ", ".join(runner.not_a_bag)
        )


def run(args: argparse.Namespace):
    for bag_parent in args.directories:
        for bag_dir in filter(lambda i: i.is_dir(), os.scandir(bag_parent)):
            if args.action_type == "validate":
                try:
                    validate_bag(bag_dir, args)
                except bagit.BagError as error:
                    LOGGER.error(
                        _("%(bag)s is invalid: %(error)s"),
                        {"bag": bag_dir.path, "error": error}
                    )
                    failures.append(bag_dir.path)
            elif args.action_type == "clean":
                try:
                    clean_bag(bag_dir)
                    successes.append(bag_dir.path)
                except bagit.BagError as error:
                    LOGGER.error(
                        _("%(bag)s cannot be cleaned: %(error)s"),
                        {"bag": bag_dir.path, "error": error}
                    )
                    failures.append(bag_dir.path)
            elif args.action_type == "create":
                try:
                    make_bag(bag_dir, args)
                    # successes.append(bag_dir.path)
                except bagit.BagError as error:
                    LOGGER.error(
                        _("%(bag)s could not be bagged: %(error)s"),
                        {"bag": bag_dir.path, "error": error}
                    )
                    failures.append(bag_dir.path)
            else:
                raise ValueError(
                    f"args contain invalid action_type: {args.action_type}"
                )

    action: str = {
        'validate': 'validated',
        'clean': 'cleaned',
        'create': 'created'
    }.get(args.action_type, "")

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


class AbsAction(abc.ABC):
    def __init__(self, args: argparse.Namespace, logger: logging.Logger):
        self.logger = logger
        self.args = args
        self.successes = []
        self.failures = []

        # skipped is used in the context of new bag creation
        # ex. i'm makin' new bags but i'm skippin' empty directories and
        # things that are already bags-
        self.skipped = []

        # not a bag is used in the context when you expect that bags are
        # already present
        # ex. i'm validating bags and i want to skip things that aren't bags
        # AND i want a count of directories that are not bags and their paths
        self.not_a_bag = []

    @abc.abstractmethod
    def execute(self, bag_dir: str):
        """Run the command."""


class ValidateBag(AbsAction):

    def execute(self, bag_dir: str):
        if not is_bag(bag_dir):
            self.logger.warning(_("%s is not a bag. Skipped."), bag_dir)
            self.not_a_bag.append(bag_dir)
            return

        bag = bagit.Bag(bag_dir)
        # validate throws a BagError or BagValidationError
        bag.validate(
            processes=self.args.processes,
            fast=self.args.fast,
            completeness_only=self.args.no_checksums,
        )
        self.successes.append(bag_dir)
        if self.args.fast:
            self.logger.info(_("%s valid according to Payload-Oxum"), bag_dir)
        elif self.args.no_checksums:
            self.logger.info(
                _("%s valid according to Payload-Oxum and file manifest"),
                bag_dir
            )
        else:
            self.logger.info(_("%s is valid"), bag_dir)


class CleanBag(AbsAction):

    def execute(self, bag_dir: str):
        """Clean bag at given directory.

        Args:
            bag_dir: File path to a directory

        """
        if not is_bag(bag_dir):
            self.logger.warning(_("%s is not a bag. Not cleaning."), bag_dir)
            self.not_a_bag.append(bag_dir)
            return

        bag = bagit.Bag(bag_dir)
        if bag.compare_manifests_with_fs()[1]:
            for payload_file in bag.compare_manifests_with_fs()[1]:
                if grabbags.utils.is_system_file(payload_file):
                    self.logger.info(
                        "Removing system files from %s", bag_dir
                    )
                    os.remove(os.path.join(bag_dir, payload_file))
                else:
                    self.logger.warning(
                        "Found file not in manifest: %s", payload_file
                    )
        else:
            self.logger.info("No system files located in %s", bag_dir)


class MakeBag(AbsAction):

    def execute(self, bag_dir: str):
        """Generate a bag for the given directory.

        Args:
            bag_dir: File path to a directory

        """
        if len(os.listdir(bag_dir)) == 0:
            self.logger.warning(
                _("%s is an empty directory. Skipped."), bag_dir)
            self.skipped.append(bag_dir)
            return

        if is_bag(bag_dir):
            self.logger.warning(_("%s is already a bag. Skipped."), bag_dir)
            self.skipped.append(bag_dir)
            return

        if self.args.no_system_files is True:
            self.logger.info(_("Cleaning %s of system files"), bag_dir)
            grabbags.utils.remove_system_files(root=bag_dir)

        bag = bagit.make_bag(
            bag_dir,
            bag_info=self.args.bag_info,
            processes=self.args.processes,
            checksums=self.args.checksums
        )
        self.successes.append(bag_dir)
        self.logger.info(_("Bagged %s"), bag.path)


def main(
        argv: typing.List[str] = None,
        runner: typing.Callable[[argparse.Namespace], None] = None
) -> None:
    """Run the main command line entry point.

    Args:
        argv: command line arguments
        runner: Callback function for processing after the cli args are parsed.

    """
    argv = argv or sys.argv[1:]
    parser: argparse.ArgumentParser = _make_parser()
    args: argparse.Namespace = parser.parse_args(args=argv)

    if args.processes < 0:
        parser.error(_("The number of processes must be 0 or greater"))

    if args.no_checksums and args.action_type != "validate":
        parser.error(
            _("--no-checksums is only allowed as an option with --validate")
        )
    if args.action_type == "clean" and args.no_system_files:
        parser.error(
            _("Can't run --clean and --no-system-files at the same time")
        )
    if args.action_type == "validate" and args.checksums is not None:
        parser.error(_("Can't specify a checksum algorithm and "
                       "run --validate at the same time"))

    if args.action_type == "clean" and args.checksums is not None:
        parser.error(_("Can't specify a checksum algorithm and "
                       "run --clean at the same time"))

    if args.fast and args.action_type != "validate":
        parser.error(_("--fast is only allowed as an option with --validate"))

    _configure_logging(args)

    runner = runner or run2
    runner(args)


if __name__ == "__main__":
    main()
