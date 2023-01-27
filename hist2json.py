#!/usr/bin/env python3
##############################################################
#
# Purpose: Transform Symphony history records into JSON.
#          See specification below.
# Date:    Wed 18 Jan 2023 07:03:49 PM EST
# Copyright 2023 Andrew Nisbet
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
##############################################################
import os
from pathlib import Path
import re
import sys
import getopt
import json
from datetime import datetime
import gzip
import socket
# TODO: Add switch to over-ride client type table.
# There are 3 tasks: 
# 1) Parse and load cmd codes and data codes into dictionaries.
# 2) Parse and translate hist files records into JSON.
#
# Example: data code document (cmd codes are similar)
# 0C|item category five|
# 0D|List of user categories|
# 0E|User Email|
#
# Example: hist document.
# E202301180000592981R ^S01FZFFBIBLIOCOMM^FcNONE^FEEPLLON^UO21221026894110^Uf1984^HKTITLE^HH40789246^NQ31221118073159^IS1^^O00101
# E202301180001313066R ^S32IYFWOVERDRIVE^FEEPLMNA^FFSIPCHK^FcNONE^FDSIPCHK^dC6^UO21221013616708^UK1/18/2023^OAY^^O
# E202301180001403066R ^S01JZFFBIBLIOCOMM^FcNONE^FEEPLWHP^UO21221027661047^UfIlovebigb00ks^NQ31221108836540^HB01/18/2024^HKTITLE^HOEPLLHL^dC5^^O00121
# 
# When reading data codes and command codes, assume the default location on the ILS,
# otherwise the user must enter the path on the command line. -d = datacodes, -c commandcodes.
# Turning this to True will run all doctests.
TEST_MODE  = False
ILS_NAME   = 'edpl.sirsidynix.net'
ILS_CC_PATH= '/software/EDPL/Unicorn/Custom/cmdcode'
ILS_DC_PATH= '/software/EDPL/Unicorn/Custom/datacode'
HIST_DIR   = '/software/EDPL/Unicorn/Logs/Hist'
APP        = 'h2j'
NEVER      = '2040-01-01'  # Some date in the far future.
HOSTNAME   = socket.gethostname()
VERSION    = "1.02.00" # Added hostname detection for data and cmd code files.
HOLD_CLIENT_TABLE = {
    '0': 'CLIENT_UNKNOWN',
    '1': 'CLIENT_WEBCAT',
    '2': 'CLIENT_3MSERVER',
    '3': 'CLIENT_WORKFLOWS',
    '4': 'CLIENT_INFOVIEW',
    '5': 'CLIENT_ONLINE_CATALOG',
    '6': 'CLIENT_SIP2',
    '7': 'CLIENT_NCIP',
    '8': 'CLIENT_SVA',
    '9': 'CLIENT_WEB_STAFF',
    '10': 'CLIENT_POCKET_CIRC',
    '11': 'CLIENT_WS_PATRON',
    '12': 'CLIENT_WS_BOOKMYNE',
    '13': 'CLIENT_WS_DS',
    '14': 'CLIENT_WS_STAFF',
    '15': 'BC_PAC',
    '16': 'BC_CAT',
    '17': 'BOOKMYNE_P',
    '18': 'SOCIAL_LIB',
    '19': 'MOBLCIRC_S',
    '20': 'BC_CIRC',
    '21': 'BC_ACQ',
    '22': 'BC_MOBILE'
}

def usage():
    usage_text = f"""
    Usage: python {APP}.py [options]

    Converts SirsiDynix History logs into JSON. See enclosed license
    for distribution restrictions.

    If the script is running on the ILS you do not need to use the 
    '-D' or '-C' switches (see below). The system cmdcode and datacode
    files will be used. Make sure ILS_NAME is set correctly for your
    ILS, currently it's '{ILS_NAME}'.

    The script will automatically handle log file compression if required.

    Date handling: SirsiDynix records dates in a number of 
    ways in the log files. {APP} converts them to 'yyyy-mm-dd' format.
    
    User PINs are redacted during conversion.

    Cmd and data code definition files are read from the 'Unicorn/Custom' 
    directory. See '-C' and '-D' flags for more information. 

    -c --hold_client="/foo/clients.txt": Path to hold client table
       (JSON) file.
       If the script is running on the ILS this switch is optional.
    -C --CmdCodes="/foo/cmd.codes": Path of the command code definitions.
       If the script is running on the ILS this switch is optional.
    -D --DataCodes="/foo/data.codes": Path of the data code definitions.
       If the script is running on the ILS this switch is optional.
    -H --HistFile="/foo/bar.hist": REQUIRED. Path of the history log 
       file to convert.
    -h: Prints this help message.
    -m: Output as MongoDB JSON (each record as a separate object).
    -v: Turns on verbose messaging which reports data code errors. 
       If a data code cannot be identified, an entry of 
         'data_code_[unknown data code]':'[data code value]' 
       is output to file and the record entry, line number, and
       data code are written to stdout.

    Version: {VERSION} Copyright (c) 2023.
    """
    sys.stderr.write(usage_text)
    sys.exit()

# Converts the many types of date strings stored in History logs into 'yyyy-mm-dd' database-ready format.
def to_date(data:str):
    """
    >>> to_date('01/13/2023')
    '2023-01-13'
    >>> to_date('E202301180024483003R ')
    '2023-01-18 00:24:48'
    >>> to_date('1/3/2023')
    '2023-01-03'
    >>> to_date('20230118002448')
    '2023-01-18 00:24:48'
    >>> to_date('01/13/2023,5:33 PM')
    '2023-01-13'
    """
    # And some dates have 1/18/2023,5:40 (sigh)
    # And some dates have 'E202301180024483003R '
    my_date = data.split(',')[0]
    new_date = []
    if len(my_date) >= 14: # Timestamp argument
        new_time = []
        if re.match(r'^E', my_date): # User sent entire first field
            my_date = my_date[1:]
        # Year
        new_date.append(my_date[:4])
        # Month
        new_date.append(my_date[4:6])
        # Day
        new_date.append(my_date[6:8])
        d = '-'.join(new_date)
        # Hour
        new_time.append(my_date[8:10])
        # minute
        new_time.append(my_date[10:12])
        # Second
        new_time.append(my_date[12:14])
        t = ':'.join(new_time)
        return f"{d} {t}"
    else:
        arr  = my_date.split('/')
        try:
            new_date.append("{:4d}".format(int(arr[2],base=10)))
            new_date.append("{:02d}".format(int(arr[0],base=10)))
            new_date.append("{:02d}".format(int(arr[1],base=10)))
        except IndexError:
            if data == 'TODAY':
                return datetime.today().strftime('%Y-%m-%d')
            if data == 'NEVER':
                return NEVER
            return "1900-01-01"
        return '-'.join(new_date)


def _clean_string_(s:str,spc_to_underscore=False):
    # Remove any weird characters. This should cover it, they're pretty clean.
    for ch in ['\\','/','`','*','_','{','}','[',']','(',')','<','>','!','$',',','\'']:
        if ch in s:
            s = s.replace(ch, "")
    # The command code is a s, not an identifier, so don't convert it into snake case.
    if spc_to_underscore == True:
        s = s.replace(' ', '_').lower()
    return s

def get_log_entry(data:list, command_codes:dict, data_codes:dict, line_no:int, verbose=False):
    """
    >>> c = {}
    >>> count = add_to_dictionary('IY|Cancel Hold-bob|', c, False)
    >>> d = {}
    >>> count = add_to_dictionary('FE|Station Library|', d, True)
    >>> count = add_to_dictionary('FF|Library Station|', d, True)
    >>> count = add_to_dictionary('FG|Library|', d, True)
    >>> data = 'E202301180024493003R ^S59IYFWCLOUDLIBRARY^FEEPLMNA^FGEPLHVY^FFEPLCPL^O'.strip().split('^')
    >>> print(get_log_entry(data,c,d,1))
    (0, {'timestamp': '2023-01-18 00:24:49', 'command_code': 'Cancel Hold-bob', 'station_library': 'MNA', 'library': 'HVY', 'library_station': 'CPL'})
    """
    record = {}
    record['timestamp'] = to_date(data[0][1:15])  # 'E202301180024483003R' => '20230118002448'
    # convert command code.
    cmd = data[1][3:5]
    err_count = 0
    record['command_code'] = command_codes[cmd]
    # Convert all data codes, or report those that are not defined.
    for field in data[2:]:
        dc = field.strip()[0:2]
        # Don't process empty data fields '^^' or EOL '0' or 'O0'.
        if len(dc) < 2 or dc == 'O0':
            continue
        try:
            data_code = data_codes[dc]
            value = field[2:]
            if re.match(r'(.+)?date', data_code) or data_code == 'user_last_activity':
                value = to_date(value)
            # Get the 3-char branch code by removing the initial 'EPL'.
            elif re.match(r'(.+)?library', data_code) or re.match(r'transit_to', data_code) or re.match(r'transit_from', data_code):
                value = value[3:]
            # Add fake user pin.
            elif re.match(r'user_pin', data_code):
                value = 'xxxxx'
            # Get rid of this tags leading '|a' in customer in this specific data code.
            elif re.match(r'entry_or_tag_data', data_code):
                value = value[2:]
            elif re.match(r'client_type', data_code):
                try:
                    temp = HOLD_CLIENT_TABLE[value]
                    value = temp
                except KeyError:
                    err_count += 1
                    print(f"* warning on line {line_no}:\n*   missing hold client type: {value}")
            record[data_code] = value
        except KeyError:
            err_count += 1
            dc = _clean_string_(dc)
            data_code = f"data_code_{dc}"
            data_codes[dc] = data_code
            if verbose == True:
                if err_count == 1:
                    print(f"* warning on line {line_no}:\n*   {data}")
                print(f"*   '{dc}' is an unrecognized data code and will be recorded as 'data_code_{dc}': '{field[2:]}'.")
    return (err_count, record)

def add_to_dictionary(line:str, dictionary:dict, is_data_code=True):
    """
    >>> c={}
    >>> add_to_dictionary('cw|ATHS (thesaurus) description|', c, False)
    1
    >>> print(f"{c}")
    {'cw': 'ATHS thesaurus description'}
    >>> c={}
    >>> add_to_dictionary('cw|AT.HS [z/39]|', c, True)
    1
    >>> print(f"{c}")
    {'cw': 'at.hs_z39'}
    """
    count = 0
    cmd_array = line.split('|')
    # clean the definition of special characters.
    command = cmd_array[0]
    definition = cmd_array[1]
    # Remove any weird characters. This should cover it, they're pretty clean.
    definition = _clean_string_(definition, is_data_code)
    dictionary[command] = definition
    count += 1
    return count

#  Take valid command line arguments.
def main(argv):
    is_verbose = False
    is_mongo_json = False  # Output in proper JSON, not one dict per line as required for MongoDB.
    json_file = ''
    hist_log  = ''
    # Dictionary of command code (key) and definition (value)
    cmd_codes = {}
    # Dictionary of data code (key) and definition (value)
    data_codes= {}
    c_count = 0
    d_count = 0
    is_compressed_hist = False
    # Where all the history data will be stored.
    hist_log = []
    data_codes_file = ''
    cmd_codes_file = ''
    try:
        opts, args = getopt.getopt(argv, "c:C:D:H:hmv", ["hold_client=", "CmdCodes=", "DataCodes=", "HistFile="])
    except getopt.GetoptError:
        usage()
    for opt, arg in opts:
        if opt in ("-c", "--hold_client"):
            assert isinstance(arg, str)
            if os.path.isfile(arg) == False:
                sys.stderr.write(f"**error, no such file {arg}.\n")
                sys.exit()
            try:
                with open(arg, 'r') as j:
                    HOLD_CLIENT_TABLE = json.load(j)
            except:
                sys.stderr.write(f"**error while reading JSON from {arg}.\n")
                sys.exit()
        if opt in ("-C", "--CmdCodes"):
            assert isinstance(arg, str)
            if os.path.isfile(arg) == False:
                sys.stderr.write(f"**error, no such file {arg}.\n")
                sys.exit()
            cmd_codes_file = arg
            # c_count = add_to_dictionary(arg, cmd_codes, False)
        if opt in ("-D", "--DataCodes"):
            assert isinstance(arg, str)
            if os.path.isfile(arg) == False:
                sys.stderr.write(f"**error, no such file {arg}.\n")
                sys.exit()
            data_codes_file = arg
        if opt in ("-H", "--HistFile"):
            assert isinstance(arg, str)
            hist_log_file = arg
            if os.path.isfile(hist_log_file) == False:
                sys.stderr.write(f"**error, no such file {hist_log_file}.\n")
                sys.exit()
            # test if the file is a zipped history file. They are named '*.Z'.
            extension = Path(hist_log_file).suffix
            if re.match(r'^\.Z', extension):
                is_compressed_hist = True
                json_file = Path(hist_log_file).with_suffix('')
            else:
                is_compressed_hist = False
                # The output JSON file is the same as the history log with '.hist' replaced with '.json'.
                json_file = f"{Path(hist_log_file)}"
            json_file = f"{json_file}.json"
        elif opt in "-h":
            usage()
        elif opt in "-m":
            is_mongo_json = True
        elif opt in "-v":
            is_verbose = True
    # Can be empty because they aren't required if the script is running on the ILS.
    if data_codes_file == '':
        if HOSTNAME == ILS_NAME:
            data_codes_file = ILS_DC_PATH
        else:
            print(f"*error, '-D' requires a valid data code file name except if run on the ILS.")
            sys.exit()
    if cmd_codes_file == '':
        if HOSTNAME == ILS_NAME:
            cmd_codes_file = ILS_CC_PATH
        else:
            print(f"*error, '-C' requires a valid cmd code file name except if run on the ILS.")
            sys.exit()
    ## Load Codes and Definitions
    # data codes
    with open(data_codes_file, encoding='utf8') as f:
        for line in f:
            d_count += add_to_dictionary(line, data_codes, True)
    f.close()
    # Add data codes that don't seem to be in this file.
    # Some codes missing and location on ILS is unknow (at this time).
    data_codes['uF'] = "user_first_name"
    data_codes['uL'] = "user_last_name"
    data_codes['uU'] = "user_prefered_name"
    data_codes['P7'] = "circ_rule"
    # Load Cmd Codes
    with open(cmd_codes_file, encoding='utf8') as f:
        for line in f:
            c_count += add_to_dictionary(line, cmd_codes, False)
    f.close()
    ## Process the history log into JSON.
    # Open the json file ready for output.
    j = open(json_file, 'w', encoding='utf8')
    # History file handle; either gzipped or regular text.
    f = ''
    if is_compressed_hist == True:
        f = gzip.open(hist_log_file, 'rt')
    else: # Not a zipped history file
        f = open(hist_log_file, encoding='utf8')
    # Process each of the lines.
    line_no = 0
    missing_data_codes = 0
    for line in f:
        line_no += 1
        fields = line.strip().split('^')
        (errors, record) = get_log_entry(fields, cmd_codes, data_codes, line_no, is_verbose)
        missing_data_codes += errors
        # Append to list if output JSON proper
        if is_mongo_json == False:
            hist_log.append(record)
        else: # else add each record to file a-la-MongoDB.
            json.dump(record, j, ensure_ascii=False, indent=2)
    if is_mongo_json == False:
        json.dump(hist_log, j, ensure_ascii=False, indent=2)
    j.close()
    # Output report.
    print(f"Total cmd codes read:    {c_count}\nTotal data codes read:   {d_count}\nTotal history records:   {line_no}")
    explain = ''
    if missing_data_codes > 0:
        explain = f", (any missing codes have been recorded as 'data_code_[data code value]':'[read value]')"
    print(f"Unidentified data codes: {missing_data_codes}{explain}\n")

if __name__ == "__main__":
    if TEST_MODE == True:
        import doctest
        doctest.testmod()
    else:
        main(sys.argv[1:])
# EOF