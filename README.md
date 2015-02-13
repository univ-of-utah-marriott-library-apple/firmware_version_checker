Firmware Version Checker
========================

A simple, standalone script to check whether your OS X computer's firmware is up-to-date.

## Contact

If you have any comments, questions, or other input, either [file an issue](../../issues) or [send us an email](mailto:mlib-its-mac-github@lists.utah.edu). Thanks!

## System Requirements

* An Intel-based Mac computer running OS X.
* Python 2.7.x (which you can download [here](https://www.python.org/download/))
* [Management Tools](https://github.com/univ-of-utah-marriott-library-apple/management_tools) - Version 1.6.0 or greater!

## Setup

Simply download the `check_firmware.py` script from the [releases page](../../releases). We distribute ours to `/usr/local/bin/check_firmware.py`, but it will function anywhere. You will need to make the file executable, of course, and then you can run it.

```bash
$ chmod +x check_firmware.py
$ ./check_firmware.py
```

## Usage

In general, you only need to execute the script without any options.

```bash
$ check_firmware.py
```

When the command runs successfully, it will either exit with a status code of `0` if there are no updates available, or `10` if there are updates. Any other exit code indicates an error during execution.

There will also be output to the console indicating either that there are no updates available, or else it will list all of the available firmware updates that were found.

### Options

| Option | Purpose |
|--------|---------|
| `-h`, `--help` | Prints help information and quits. |
| `-v`, `--version` | Prints version information and quits. |
| `-V`, `--verbose` | Provides debugging information such as the discovered computer name, serial number, etc. |
| `-n`, `--no-log` | Redirects logging to standard output (stdout, i.e. the console). |
| `-l log`, `--log-dest log` | Redirect logging to the specified `log` file. (This will be overridden by `--no`log`.) |

## Technical

To discover the availability of firmware updates, this script consults two sources: the Software Update tool and Apple's [firmware support website](http://support.apple.com/en-us/HT201518).

Unfortunately, there are many caveats to this. First: Why do we have to check a website if we have Software Update? And the answer is that apparently not all firmware updates are able to be listed in the Software Update database. I'm not sure why this is, and Apple doesn't seem to offer much explanation.

So, since we can't rely entirely on Software Update, the script has to parse over the firmware support website. On this page, Apple lists computers, their model identifiers, the available EFI boot rom version, and the available SMC updates. Again, Apple has complicated things somewhat by using nonstandard computer names and duplicate model identifiers. This means that you cannot rely on the System Profiler's model identifier to find a firmware update, as there may be other models of computers with the same identifier. Our solution was to cross-reference the matches with the computer name provided by the Apple [warranty support checker](https://selfsolve.apple.com/). This works fairly well, though there are some discrepancies that will have to be resolved manually.

## Update History

This is a reverse-chronological list of important updates to this project.

| Date | Version | Update |
|------|:-------:|--------|
| 2015-02-13 | 1.0.2 | Now supports a backup Apple support website in case the regular one doesn't return warranty information. |
| 2015-02-13 | 1.0.1 | Fixed bug where computers with no updates in Software Update would throw an error. |
| 2015-02-12 | 1.0.0 | First major release. Reports on availability of updates to local device firmware. |
