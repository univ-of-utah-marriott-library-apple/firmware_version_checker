#!/usr/bin/env python

import argparse
import re
import subprocess
import sys

attributes = {
    'long_name': "Firmware Update Checker",
    'name':      "check_firmware",
    'version':   "1.0.0"
}

# Check that management_tools is installed on this computer.
try:
    from management_tools import loggers
    from management_tools.plist_editor import PlistEditor
except ImportError as e:
    print("You need version 1.6.0 or greater of the 'Management Tools' module to be installed first.")
    print("https://github.com/univ-of-utah-marriott-library-apple/management_tools")
    raise e

def main(logger, verbose):
    """
    Attempts to find any available firmware updates for this computer. Output
    is logged according to 'logger', and verbosity can be increased by setting
    'verbose' to true.

    :param logger: a management_tools.loggers logger for outputting/saving info
    :param verbose: whether or not to output extra information
    """
    # Get the hardware data.
    hw_data = get_system_hardware_profile()

    #----------------------------------------------#
    # Pull out relevant info from System Profiler. #
    #----------------------------------------------#
    try:
        model_id = hw_data['Model Identifier']
        logger.debug("Model ID: {}".format(model_id))
    except KeyError:
        logger.critical("Invalid key in SPHardwareData: 'Model Identifier'")
        sys.exit(2)

    try:
        serial = hw_data['Serial Number (system)']
        logger.debug("Serial Number: {}".format(serial))
    except KeyError:
        logger.critical("Invalid key in SPHardwareData: 'Serial Number (system)'")
        sys.exit(2)

    try:
        current_firmware = hw_data['SMC Version (system)']
        logger.debug("Current SMC Version: {}".format(current_firmware))
    except KeyError:
        logger.critical("Invalid key in SPHardwareData: 'SMC Version (system)'")
        sys.exit(2)

    # Check software update.
    sw_update_firmware = check_software_update()
    sw_update_firmware_available = len(sw_update_firmware) != 0

    # Get the computer name.
    computer_name = get_computer_name(serial)
    # Check the Apple support website for updates.
    if computer_name:
        logger.debug("Computer Name: {}".format(computer_name))
        website_firmware = get_website_firmware(model_id, computer_name, logger)
    else:
        logger.warn("Unable to look up website firmware information.")
        website_firmware = None

    # Determine whether any firmware updates are available from above info.
    website_firmware_available = not (website_firmware is None or website_firmware == '' or website_firmware == current_firmware)

    # Determine whether there are any updates available at all and report.
    if not (website_firmware_available or sw_update_firmware_available):
        logger.info("No new firmware version identified.")
        sys.exit(0)
    else:
        # Generate output regarding updates.
        output = "Firmware updates found:"
        if website_firmware_available:
            output += "\n    Apple support site: {}".format(website_firmware)
        if sw_update_firmware_available:
            for update in sw_update_firmware:
                output += "\n    softwareupdate: {}".format(update)

        logger.info(output)
        # Having a different exit code makes it easy to tell programmatically
        # whether an update is available.
        sys.exit(10)

def check_software_update():
    """
    Runs /usr/sbin/softwareupdate to check for any available updates, and then
    returns any updates found with "firm" or "efi" in their names.

    :return: a list containing available firmware updates (an empty list if none are available)
    """
    # Find all available updates.
    available_updates = subprocess.check_output([
        '/usr/sbin/softwareupdate', '-l'
    ]).split('\n')

    if (available_updates[4] == ''):
        # No updates were found at all, so return an empty list.
        return []

    # The available updates are everything from line 5 onward.
    available_updates = available_updates[5:]
    # Only include the update names - not their descriptions.
    available_updates = [item[5:] for item in available_updates if item.startswith('   * ')]
    # Only include updates with "firm" or "efi" in their names; these are
    # firmware updates.
    firmware_updates = [item for item in available_updates if ("firm" in item.lower() or "efi" in item.lower())]

    return firmware_updates

def get_website_firmware(model_id, computer_name, logger):
    """
    Contacts the Apple Support website http://support.apple.com/en-us/HT201518.
    This site contains a table with a list of potential firmware updates that
    may not appear in Software Update.

    :param model_id: the Apple-given model identifier of the computer (e.g. "iMac14,1")
    :param computer_name: the name of the computer (e.g. "iMac (21.5-inch, Late 2013)")
    :param logger: a management_tools.loggers logger to output information
    :return: a string representing the firmware version available
    """
    # Get the table from the Apple site.
    table = get_firmware_table()
    # Only look at lines where the model identifier matches this computer.
    matches = [line for line in table if line[1] == model_id]

    # Check how many matches.
    if len(matches) == 0:
        # No matching model was found.
        logger.warn("No such model ID found: {}".format(model_id))
        return None
    elif len(matches) > 1:
        # In the event of multiple matches, the 'computer_name' is used as a
        # cross-reference.
        logger.warn("Multiple matches found. Using name: '{}'".format(computer_name))
        match = [line for line in matches if line[0] == computer_name]
    else:
        # Only one match was found, so use that.
        match = matches[0]

    # No matches were found. Sadness ensues.
    if len(match) == 0:
        logger.error("No match between model ID ({}) and computer name ({})".format(model_id, computer_name))
        return None

    # Return the SMC version from that row of the table. Remove any extra
    # information from its value (only include the firmware number).
    return match[2].split(' ', 1)[0]

def get_firmware_table():
    """
    Parses the Apple site http://support.apple.com/en-us/HT201518 for the table
    containing firmware update information.

    :return: a list with rows of (computer name, model ID, SMC version)
    """
    # Get the contents of the web page.
    curl_command = [
        '/usr/bin/curl',
        '-Lks',
        'http://support.apple.com/en-us/HT201518'
    ]
    page = subprocess.check_output(curl_command).split('\n')

    # Grab the table from the larger page.
    table_section = None
    grab_it = False
    for line in page:
        if grab_it:
            table_section = line
            break
        if line == '<div id="sections" itemprop="articleBody">':
            grab_it = True

    #------------------------------------------------#
    # The next section removes cruft from the table. #
    #------------------------------------------------#
    # Remove newlines.
    table_section = re.sub(
        r"&NewLine;",
        "",
        table_section
    )
    # Remove tabs.
    table_section = re.sub(
        r"&Tab;",
        "",
        table_section
    )
    # Remove blank space.
    table_section = re.sub(
        r"&nbsp;",
        "",
        table_section
    )
    # Substitute left parentheses...
    table_section = re.sub(
        r"&lpar;",
        "(",
        table_section
    )
    # and right ones, too.
    table_section = re.sub(
        r"&rpar;",
        ")",
        table_section
    )
    # Remove the headings.
    table_section = re.sub(
        r".*<tbody><tr><th><strong>Computer</strong></th><th><strong>Model identifier</strong></th><th><strong>EFI Boot ROM version</strong></th><th><strong>SMC version</strong></th></tr>",
        "",
        table_section
    )
    # Remove the end of the table.
    table_section = re.sub(
        r"</tbody>.*",
        "",
        table_section
    )
    # Remove subheadings (e.g. "iMac").
    table_section = re.sub(
        r"<tr><td colspan.*?</tr>",
        "",
        table_section
    )
    # Remove row tags.
    table_section = re.sub(
        r"</tr>",
        "</tr>\n",
        table_section
    ).split('\n')

    # Create list to store result.
    result = []

    # Iterate over the lines of the table, taking each line and splitting it up
    # for its relevant information.
    for line in table_section:
        search = re.search(r"<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>", line)
        if search:
            computer    = search.group(1)
            model_id    = search.group(2)
            smc_version = search.group(4)

            computer    = re.sub(r"<.*?>", "", computer)
            model_id    = re.sub(r"<.*?>", "", model_id)
            smc_version = re.sub(r"<.*?>", "", smc_version)

            # Model IDs should have no interior whitespace, so remove it.
            model_id = ''.join(model_id.split())

            result.append( (computer, model_id, smc_version) )

    return result

def get_computer_name(serial):
    """
    Contacts the Apple warranty support page https://selfsolve.apple.com/ and
    attempts to get a human-readable name from a serial number.

    :param serial: the serial number of the computer
    :return: the name of the computer
    """
    # Get the warranty support page back.
    curl_command = [
        '/usr/bin/curl',
        '-Lks',
        'https://selfsolve.apple.com/RegisterProduct.do?productRegister=Y&country=USA&id={serial_number}'.format(serial_number = serial)
    ]
    page = subprocess.check_output(curl_command).split('\n')

    # Find the appropriate line in the page.
    result = None
    for line in page:
        line = line.strip()
        if "productname" in line:
            result = line

    # If we got something back, clean it up (remove tags).
    if result:
        result = re.sub(r"<.*?>", "", result)

    return result

def get_system_hardware_profile():
    """
    Parses the output of '/usr/sbin/system_profiler SPHardwareDataType' and
    stores it into a dictionary (the values are split on the first colon).

    :return: a dictionary containing keys and values from system profiler
    """
    # Get the raw output from system_profiler.
    full_output = subprocess.check_output([
        '/usr/sbin/system_profiler',
        'SPHardwareDataType'
    ])

    # Split the output into lines, remove the extra lines at top, and remove
    # any whitespace.
    output = full_output.split('\n')[5:]
    output = [line.strip() for line in output if line != '']

    # Split the resulting lines on their first colon and store them as a key
    # and value pair.
    result = {}
    for line in output:
        key, value = line.split(':', 1)
        result[key] = value.strip()

    return result

def version():
    """
    :return: the version of this program
    """
    return "check_firmware, version {}".format(attributes['version'])

def usage():
    """
    Prints out relevant usage information.
    """
    print(version())

    print("""\
usage: {name} [-hvnV] [-l log]

Check if there are any firmware updates available for this computer. Consults
both /usr/sbin/softwareupdate and the Apple Support website located at:
    http://support.apple.com/en-us/HT201518

    -h, --help
        Prints this help message and quits.
    -v, --version
        Prints the version information and quits.
    -n, --no-log
        Prevent logs from being written to files.
        (All information that would be logged is redirected to stdio.)
    -V, --verbose
        Activate debug mode; extra information is displayed during runtime.

    -l log, --log-dest log
        Redirect log output to 'log'.\
""".format(name=attributes['name']))

#---------------------#
# Program Entry Point #
#---------------------#
if __name__ == '__main__':
    # Create a simple argument parser.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-h', '--help', action='store_true')
    parser.add_argument('-v', '--version', action='store_true')
    parser.add_argument('-V', '--verbose', action='store_true')
    parser.add_argument('-n', '--no-log', action='store_true')
    parser.add_argument('-l', '--log-dest')

    # Parse the arguments.
    args = parser.parse_args()

    # Just print the help information and quit.
    if args.help:
        usage()
        sys.exit(0)

    # Just print the version information and quit.
    if args.version:
        print(version())
        sys.exit(0)

    # Set the logging level.
    level = 20
    if args.verbose:
        level = 10

    # Create the logger (very useful).
    logger = loggers.get_logger(
        name  = "check_firmware",
        log   = not args.no_log,
        level = level,
        path  = args.log_dest
    )

    # Call the program to action.
    main(logger, args.verbose)
