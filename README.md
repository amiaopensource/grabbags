# Grabbags

[![Build Status](https://travis-ci.org/amiaopensource/grabbags.svg?branch=master)](https://travis-ci.org/amiaopensource/grabbags)

## Introduction

Grabbags is an enhanced implementation of the Library of Congress's BagIt Library. Grabbags allows users to do bulk creation and validation of bags. Grabbags can also elminate system files before bagging. 

## Installing grabbags
For installation, see getting_started.md

## Using grabbags

To run grabbags, use the command:
` $ grabbags (optional flags) (target directory path)`

By default, grabbags will do bulk creation of bags. It assumes that a target directory contains many other subdirectories inside of it that will be turned into bags. So set up your directories accordingly. You can also give the command multiple target directories
` $ grabbags (optional flags) (target directory path 1) (target directory path 2)

Since grabbags uses the bagit Python library, all the functionality of bagit (including adding metadata fields and choosing checksum algorithms) should be available for bag creation.

### Elinating System Files Before Bag Creation
Using the `--no-system-files` flag when creating bags will find and remove any system files before bagging. The current system files that the script can find are:
* .DS_Store
* Thumbs.db
* ._ files (AppleDoubles)
* Icon files (Apple custom icons)

Please send a pull request or issue if you have additional information about new system files that users would want to delete

### Validate Flags
Validation of bags has two possible options:

The default behavior of `$ grabbags --validate` is to validate the bag by comparing the checksums of all files with the checksums contained in the manifest.
Users can optionally use the flags `--validate --no--checksums`. This only validates the Oxsum of the bag, the number of files, and the proper files according to the bagit specification. Using the --no-checksums flag is equivalent to running `--validate --completeness-only`

## Enhanced Logging
At the end of the 

Just as in bagit python, users can use the `--log (path to place log file)` flag to create a log when creating or validating bags. At the end of the output grabbags will display summary data about the numbers of bags created or validated.

