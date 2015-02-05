#!/usr/bin/env python

import re
import subprocess
import sys

def main():
    # Get the hardware data.
    hw_data = get_system_hardware_profile()

    # Pull out relevant info from System Profiler.
    try:
        model_id = hw_data['Model Identifier']
    except KeyError:
        print("Invalid key: 'Model Identifier'")
        sys.exit(2)

    try:
        serial = hw_data['Serial Number (system)']
    except KeyError:
        print("Invalid key: 'Serial Number (system)'")
        sys.exit(2)

    try:
        current_firmware = hw_data['SMC Version (system)']
    except KeyError:
        print("Invalid key: 'SMC Version (system)'")
        sys.exit(2)

    computer_name      = get_computer_name(serial)
    website_firmware   = get_website_firmware(model_id, computer_name)
    sw_update_firmware = check_software_update()

    website_firmware_available   = not (website_firmware is None or website_firmware == '' or website_firmware == current_firmware)
    sw_update_firmware_available = len(sw_update_firmware) != 0

    if not (website_firmware_available or sw_update_firmware_available):
        print("No new firmware version identified.")
        sys.exit(0)
    else:
        output = "Firmware updates found:"

        if website_firmware_available:
            output += "\n    Apple support site: {}".format(website_firmware)

        if sw_update_firmware_avilable:
            output += "\n    softwareupdate: {}".format(sw_update_firmware)

        print(output)
        sys.exit(10)

def check_software_update():
    available_updates = subprocess.check_output([
        '/usr/sbin/softwareupdate', '-l'
    ]).split('\n')

    if (available_updates[4] == ''):
        # No updates were found at all.
        return False

    available_updates = available_updates[5:]

    available_updates = [item[5:] for item in available_updates if item.startswith('   * ')]

    firmware_updates = [item for item in available_updates if ("firm" in item.lower() or "efi" in item.lower())]

    return firmware_updates

def get_website_firmware(model_id, computer_name):
    result = None

    table = get_firmware_table()

    matches = [line for line in table if line[1] == model_id]

    # Check how many matches.
    if len(matches) == 0:
        print("No such model ID found: {}".format(model_id))
    elif len(matches) > 1:
        print("Multiple matches found. Using name: '{}'".format(computer_name))
        match = [line for line in matches if line[0] == computer_name]
    else:
        match = matches[0]

    if len(match) == 0:
        print("No match between model ID ({}) and computer name ({})".format(model_id, computer_name))
        sys.exit(5)

    return match[2].split(' ', 1)[0]

def get_firmware_table():
    curl_command = [
        '/usr/bin/curl',
        '-Lks',
        'http://support.apple.com/en-us/HT201518'
    ]
    page = subprocess.check_output(curl_command).split('\n')
    table_section = None
    grab_it = False
    for line in page:
        if grab_it:
            table_section = line
            break
        if line == '<div id="sections" itemprop="articleBody">':
            grab_it = True

    table_section = re.sub(
        r"&NewLine;",
        "",
        table_section
    )
    table_section = re.sub(
        r"&Tab;",
        "",
        table_section
    )
    table_section = re.sub(
        r"&nbsp;",
        "",
        table_section
    )
    table_section = re.sub(
        r"&lpar;",
        "(",
        table_section
    )
    table_section = re.sub(
        r"&rpar;",
        ")",
        table_section
    )
    table_section = re.sub(
        r".*<tbody><tr><th><strong>Computer</strong></th><th><strong>Model identifier</strong></th><th><strong>EFI Boot ROM version</strong></th><th><strong>SMC version</strong></th></tr>",
        "",
        table_section
    )
    table_section = re.sub(
        r"</tbody>.*",
        "",
        table_section
    )
    table_section = re.sub(
        r"<tr><td colspan.*?</tr>",
        "",
        table_section
    )
    table_section = re.sub(
        r"</tr>",
        "</tr>\n",
        table_section
    ).split('\n')

    result = []

    for line in table_section:
        search = re.search(r"<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>", line)
        if search:
            computer    = search.group(1)
            model_id    = search.group(2)
            smc_version = search.group(4)

            computer    = re.sub(r"<.*?>", "", computer)
            model_id    = re.sub(r"<.*?>", "", model_id)
            smc_version = re.sub(r"<.*?>", "", smc_version)

            result.append( (computer, model_id, smc_version) )

    # for item in result:
    #     print("Computer: {}".format(item[0]))
    #     print("  Model:  {}".format(item[1]))
    #     print("  SMC:    {}".format(item[2]))

    return result

def get_computer_name(serial):
    curl_command = [
        '/usr/bin/curl',
        '-Lks',
        'https://selfsolve.apple.com/wcResults.do?sn={serial_number}&Continue=Continue&num=0'.format(serial_number = serial)
    ]
    page = subprocess.check_output(curl_command).split('\n')
    result = None
    for line in page:
        line = line.strip()
        if line.startswith('warrantyPage.warrantycheck.displayProductInfo'):
            result = line

    if result:
        parts = result.split(', ', 1)
        result = parts[1][1:].split("'", 1)[0]

    return result

def get_system_hardware_profile():
    result = {}
    full_output = subprocess.check_output([
        '/usr/sbin/system_profiler',
        'SPHardwareDataType'
    ])

    output = full_output.split('\n')[5:]
    output = [line.strip() for line in output if line != '']

    for line in output:
        key, value = line.split(':', 1)
        result[key] = value.strip()

    # for key, value in result.iteritems():
    #     print("{}: {}".format(key, value))

    return result

if __name__ == '__main__':
    main()
