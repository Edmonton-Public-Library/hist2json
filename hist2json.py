#!/usr/bin/env python3
##############################################################
#
# Purpose: Transform Symphony history records into JSON.
#          See specification below.
# Date:    Wed 18 Jan 2023 07:03:49 PM EST
# Copyright (c) 2023 Andrew Nisbet
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

import sys
import getopt
from lib.hist import Hist

# Tasks: 
# * Parse and load cmd codes into dictionary. Optional.
# * Parse and load data codes into dictionary. Optional.
# * Load bar codes so lookups can be done by barcode instead of item key. Optional.
# * Parse and translate hist files records into JSON.
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
# Added hostname detection for data and cmd code files.
VERSION    = "2.00.00_dev"
# When reading data codes and command codes, assume the default location on the ILS,
# otherwise the user must enter the path on the command line. -d = datacodes, -c commandcodes.
# Turning this to True will run all doctests.
TEST_MODE    = False
UNICORN_PATH = f"/software/EDPL/Unicorn"
APP          = 'h2j'
# A replacement date Symphony's deep time 'NEVER' which won't do as a timestamp.
NEVER        = '2040-01-01'

def usage():
    usage_text = f"""
    Usage: python {APP}.py [options]

    Converts SirsiDynix History logs into JSON. See enclosed license
    for distribution restrictions.

    The script will automatically handle log file compression if required.

    Date handling: SirsiDynix records dates in a number of 
    ways in the log files. {APP} converts them to 'yyyy-mm-dd' format.
    
    User PINs are redacted during conversion.

    Cmd and data code definition files are read from the 'Unicorn/Custom' 
    directory. See '-C' and '-D' flags for more information. 

    -c --clientCodes="/foo/clients.txt": Path to hold client table
       (JSON) file.
       If the script is running on the ILS this switch is optional.
    -C --CmdCodes="/foo/cmd.codes": Path of the command code definitions.
       If the script is running on the ILS this switch is optional.
    -d: Turns on debug information.
    -D --DataCodes="/foo/data.codes": Path of the data code definitions.
       If the script is running on the ILS this switch is optional.
    -H --HistFile="/foo/bar.hist": REQUIRED. Hist log file to convert.
       If --UnicornPath is used, full path is not required.
    -I --ItemKeyBarcodes="/foo/bar/items.lst": Optional. Path to the 
       list of all item key / barcodes in 'c_key|call_seq|copy_num|item_id'
       form. Use 'selitem -oIB'.
    -h: Prints this help message.
    -m: Output as MongoDB JSON (each record as a separate object).
    -U --UnicornPath="/home/sirsi/Unicorn": Optional, sets the Unicorn directory.
       Default = '{UNICORN_PATH}'. If not set the following files are 
       required: items, hold clients, command codes, and data codes. For 
       testing purposes a relative path can be used as long as the hist,
       command codes, data codes, and items barcodes are found in directories
       typically found on a Symphony system. For example using '.' if there
       is a directory called ./Logs/Hist that contains log file to transform.
       Similarly there should be ./
    -v: Outputs version to stdout.

    Version: {VERSION} Copyright (c) 2023.
    """
    sys.stderr.write(usage_text)
    sys.exit()

#  Take valid command line arguments.
def main(argv):
    hist_files = []
    # Output in proper JSON, not one dict per line as required for MongoDB.
    use_mongo_json = False
    debug       = False
    unicorn     = ''
    barcodes    = ''
    cmdcodes    = ''
    datacodes   = ''
    clientcodes = ''
    items       = ''
    # Translate command codes and data codes if required, and iff translate available.
    
    try:
        opts, args = getopt.getopt(argv, "c:C:dD:H:hI:mU:v", ["clientCodes=", "CmdCodes=", "DataCodes=", "HistFile=", "ItemKeyBarcodes=", "UnicornPath="])
    except getopt.GetoptError:
        usage()
    for opt, arg in opts:
        if opt in ("-c", "--clientCodes"):
            clientcodes = arg
        elif opt in ("-C", "--CmdCodes"):
            cmdcodes = arg
        elif opt in "-d":
            debug = True
        elif opt in ("-D", "--DataCodes"):
            datacodes = arg
        elif opt in ("-H", "--HistFile"):
            hist_files.append(arg)
        elif opt in "-h":
            usage()
        elif opt in ("-I", "--ItemKeyBarcodes"):
            items = arg
        elif opt in "-m":
            use_mongo_json = True
        elif opt in ("-U", "--UnicornPath"):
            UNICORN_PATH = arg
        elif opt in "-v":
            print(f"{APP} version: {VERSION}.")
            sys.exit(0)
        else:
            print(f"invalid option {arg}")
        
    hist = Hist(unicornPath=UNICORN_PATH, 
      commandCodes=cmdcodes, dataCodes=datacodes, barCodes=barcodes, 
      clientCodes=clientcodes, debug=debug)
    ## Load Codes and Definitions
    # Add data codes that don't seem to be in the default Symphony file on our ILS.
    # Some codes missing and location on ILS is unknow (at this time).
    data_code_extras= {}
    data_code_extras['uF'] = "user_first_name"
    data_code_extras['uL'] = "user_last_name"
    data_code_extras['uU'] = "user_prefered_name"
    data_code_extras['P7'] = "circ_rule"
    hist.setDataCodes(dataCodes=data_code_extras)
    # Convert hist file to JSON
    for hist_file in hist_files:
        hist.toJson(hist_file, mongoDb=use_mongo_json)
    # Output report.
    print(f"Total cmd codes read:    {hist.getCommandCodeCount()}\nTotal data codes read:   {hist.getDataCodeCount()}\nTotal history records:   {hist.getLineCount()}")
    print(f"Total items read:     {hist.getBarCodeCount()}")
    print(f"Total errors:     {hist.getErrorCount()}")
    missing_data_codes = hist.getMissingDataCodes()
    if missing_data_codes:
        print(f"Data codes without definitions have been recorded as 'data_code_[data code value]':'[read value]'")
        for (line, code) in missing_data_codes:
            print(f" * on line {line} => {code}")

if __name__ == "__main__":
    if TEST_MODE == True:
        import doctest
        doctest.testmod()
        doctest.testfile("hist2json.tst")
    else:
        main(sys.argv[1:])
# EOF