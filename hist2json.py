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
import re
from os import path
from os.path import exists
import json
import gzip
from pathlib import Path
from datetime import datetime
import subprocess

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
VERSION = "2.00.03"
# When reading data codes and command codes, assume the default location on the ILS,
# otherwise the datacode and cmdcode file in lib is used. This is done for testing
# purposes.
APP    = 'h2j'
# A replacement date Symphony's deep time 'NEVER' which won't do as a timestamp.
NEVER  = '2099-01-01'
HOME   = '/software/EDPL/Unicorn'

class Hist:

    # Constructor 
    # param: histFile:str - name of the history file to parse. See debug switch for exceptions. 
    # param: encoding:str - encoding to be used when reading and writing to files. 
    #   The default is 'ISO-8859-1' but 'UTF-8' is acceptable as well.  
    # param: commandCodes - a dictionary or path to the cmdcode file. See debug switch for exceptions. 
    #   By default the application will look in the unicorn directory where Symphony normally keeps it.  
    # param: dataCodes 
    def __init__(self, encoding:str='ISO-8859-1', barCodes:str=None, clientCodes:str=None, debug:bool=False):
        self.is_ils         = exists(HOME)
        self.line_count     = 0
        self.errors         = 0
        self.translate_cmd  = f"{self.gpn('bin')}/translate"
        self.encoding       = encoding
        self.cmd_codes      = self.readCodeFile(f"{self.gpn('custom')}/cmdcode")
        self.data_codes     = self.readCodeFile(f"{self.gpn('custom')}/datacode", us=True)
        # Load the dictionary of the types of services that can place holds. Preserve underscores.
        if clientCodes:
            self.hold_clients = self.readCodeFile(clientCodes)
        else:
            self.hold_clients = self.readCodeFile(f"{self.gpn('custom')}/hold_client_table.lst")
        # Can specify a dict of IDs and barcodes for testing
        if barCodes:
            self.bar_codes = self.readBarCodes(barCodes)
        else:
            print(f"WARNING: item IDs will not be converted into item barcodes.")
            self.bar_codes = {}
        self.missing_data_codes = {}
        if debug:
            print(f"encoding        :{self.encoding      }")
            print(f"cmd_codes len   :{self.getCommandCodeCount()}")
            print(f"data_codes len  :{self.getDataCodeCount()}")
            print(f"hold_clients len:{self.getHoldClientCount()}")
            print(f"bar_codes read  :{self.getBarCodeCount()}")
    
    # Acts like 'getpathname' in Symphony, that is, it attempts to resolve 
    # common fully qualified paths on the ILS given just the name of the directory
    # in lower case. For example 'bincustom' will resolve to $HOME/Unicorn/Bincustom.
    # If the application is not running on a Symphony ILS, every request resolves 
    # to the test directory in the directory above this one, that is '$(pwd)/test'.
    # param: dirName:str request named directory. For example 'hist' or 'custom'.
    def gpn(self, dirName:str) -> str:
        if self.is_ils:
            get_path_name = subprocess.Popen(["getpathname", f"{dirName}"], stdout=subprocess.PIPE)
            path = get_path_name.communicate()[0].decode().rstrip()
            if exists(path):
                return path
        # If not on the ILS OR the directory wasn't found check the local directory.
        get_path_name = subprocess.Popen(["pwd"], stdout=subprocess.PIPE)
        path = f"{get_path_name.communicate()[0].decode().rstrip()}"
        return path

    def getLineCount(self) -> int:
        return self.line_count

    def getHoldClientCount(self) -> int:
        return len(self.hold_clients)

    def getCommandCodeCount(self) -> int:
        return len(self.cmd_codes)

    def getDataCodeCount(self) -> int:
        return len(self.data_codes)

    def getBarCodeCount(self) -> int:
        return len(self.bar_codes)

    def getMissingDataCodes(self) -> dict:
        return self.missing_data_codes

    def getErrorCount(self) -> int:
        return self.errors

    # Translates command, data, and client codes into human-readable form. 
    # For example 'CV' command code will translate into 'Charge Item'. 
    # param: rawCode:str - command, data, or client code string. 
    def getTranslation(self, rawCode:str, whichDict:str='datacode', asValue:bool=False, lineNumber:int=1) ->str:
        translated_code = rawCode
        value           = ''
        if whichDict == 'commandcode':
            if len(rawCode) > 2:
                # As in 'S61EVFWSMTCHTLHL1' wanted: 'EV'
                rawCode = rawCode[3:5]
                value   = rawCode[5:]
            translated_code = self.cmd_codes.get(rawCode)
        elif whichDict == 'datacode':
            if len(rawCode) > 2:
                # As in 'NQ31221120423970' wanted: 'NQ'
                value   = rawCode[2:]
                rawCode = rawCode[0:2]
            translated_code = self.data_codes.get(rawCode)
            if not translated_code:
                translated_code = f"{rawCode}"
                if translated_code:
                    if lineNumber in self.missing_data_codes:
                        if not rawCode in self.missing_data_codes.get(lineNumber):
                            self.missing_data_codes[lineNumber] = f"{self.missing_data_codes[lineNumber]},{rawCode}"
                    else:
                        self.missing_data_codes[lineNumber] = rawCode
        elif whichDict == 'clientcode':
            translated_code = self.hold_clients.get(rawCode)
        else:
            print(f"* warning: on line {lineNumber}, invalid lookup for {rawCode} in table {whichDict}\n")
        if asValue:
            return value
        # If get failed on any of the above dictionaries send back a cleaned version of the code.
        if not translated_code:
            return rawCode
        return translated_code

    # Converts a single line of a hist file into JSON. 
    # param: data:list - string fields from the line of hist. 
    # param: line_no:int - the current line of the hist file.  
    def convertLogEntry(self, data:list, line_no:int):
        # E202303231010243024R ^S00hEFWCALCIRC^FFCIRC^FEEPLCAL^FcNONE^dC19^**tJ2371230**^**tL55**^**IS1**^**HH41224719**^nuEPLRIV^nxHOLD^nrY^Fv2147483647^^O
        # Where the following fields are                                       cat_key     seq_no   copy_no   hold_key  
        record = {}
        record['timestamp'] = self.toDate(data[0])  # 'E202301180024483003R' => '20230118002448'
        err_count = 0
        record['command_code'] = self.getTranslation(data[1], whichDict='commandcode', lineNumber=line_no)
        if not record.get('command_code'):
            err_count += 1
            print(f"*error on line {line_no}, missing command_code!")
            return (err_count, record)
        # Capture 'hE' transit item data codes for cat key, call seq, and copy number. 
        item_key = []
        # Convert all data codes, or report those that are not defined.
        for field in data[2:]:
            data_code = self.getTranslation(field, lineNumber=line_no)
            # Don't process empty data fields '^^' or EOL '0' or 'O0'.
            if len(data_code) < 2 or data_code == 'O0':
                continue
            value = self.getTranslation(field, asValue=True, lineNumber=line_no)
            if len(data_code) == 2:
                data_code = f"data_code_{data_code}"
                record[data_code] = value
                continue
            if re.match(r'(.+)?date', data_code) or data_code == 'user_last_activity' or data_code == 'birth_year':
                value = self.toDate(value)
            # Get the 3-char branch code by removing the initial 'EPL'.
            elif re.match(r'(.+)?library', data_code) or re.match(r'transit_to', data_code) or re.match(r'transit_from', data_code):
                value = value[3:]
            # Add fake user pin.
            elif re.match(r'user_pin', data_code):
                value = 'xxxxx'
            # Capture 'tJ' - catalog_key_number
            elif re.match(r'catalog_key_number', data_code):
                item_key.insert(0, value)
            # Capture 'tL' - call_sequence_code
            elif re.match(r'call_sequence_code', data_code):
                item_key.append(value)
            # Capture 'IS' - copy_number but only if catalog_key_number and call_sequence_code were found.
            elif re.match(r'copy_number', data_code):
                # Store the copy number before making they get clobbered by the item_id lookup.
                record[data_code] = value
                if item_key:
                    item_key.append(value)
                    _item_key_ = '|'.join(item_key)
                    barcode = self.bar_codes.get(f"{_item_key_}|")
                    if barcode:
                        data_code = "item_id"
                        value = barcode
            # Get rid of this tags leading '|a' in customer in this specific data code.
            elif re.match(r'entry_or_tag_data', data_code):
                value = value[2:]
            elif re.match(r'client_type', data_code):
                value = self.getTranslation(value, whichDict='clientcode', lineNumber=line_no)
            record[data_code] = value
        if record['command_code'] == "Discharge Item" and not record.get('date_of_discharge'):
            # Discharge item with no 'CO', 'date_of_discharge'.
            record['date_of_discharge'] = self.toDate(data[0], justDate=True)
        return (err_count, record)

    # Converts and writes the JSON hist file contents to file.
    def toJson(self, histFile:str=None, outFile:str=None, mongoDb:bool=False):
        if not histFile:
            return
        if not path.isfile(histFile):
            print(f"**error, no such file {histFile}.\n")
            sys.exit()
        print(f"histFile     :{histFile      }")
        # test if the file is a zipped history file. They are named '*.Z'.
        is_compressed_hist = True
        if not histFile.endswith('.Z'):
            is_compressed_hist = False
        hist_log_list = []
        if not outFile:
            json_file = Path(histFile).with_suffix('')
            json_file = f"{histFile}.json"
        else:
            json_file = outFile
        ## Process the history log into JSON.
        # Open the json file ready for output.
        j = open(json_file, mode='wt', encoding=self.encoding)
        # History file handle; either gzipped or regular text.
        if is_compressed_hist:
            f = gzip.open(histFile, mode='rt', encoding=self.encoding)
        else: # Not a zipped history file
            f = open(histFile, mode='rt', encoding=self.encoding)
        # Process each of the lines.
        for line in f:
            self.line_count += 1
            fields = line.strip().split('^')
            (errors, record) = self.convertLogEntry(fields, self.line_count)
            self.errors += errors
            # Append to list if output JSON proper
            if not mongoDb:
                hist_log_list.append(record)
            else: # else add each record to file a-la-MongoDB.
                json.dump(record, j, ensure_ascii=False, indent=2)
        if not mongoDb:
            json.dump(hist_log_list, j, ensure_ascii=False, indent=2)
        j.close()

    # Reads and translates the command codes file from the Unicorn directory on the ILS
    # but otherwise the ../test directory on this machine. If the translate command is
    # available, it will be used to translate the file's contents, otherwise an empty
    # dictionary is returned. Make sure the last line of files includes a newline. 
    # param: commandCode:str command code file. If a 'translate' app is not found the 
    #   contents will be used as is. This makes it conveinent to have a translated 
    #   version of symphony commands that can be augmented with additional or improved
    #   command names. 
    # param: us:bool replaces spaces with underscores if True. Default False,
    #   leave spaces as spaces.    
    def readCodeFile(self, codeFile:str, us:bool=False, debug:bool=False) -> dict:
        cmd_dict = {}
        if not codeFile or not exists(codeFile):
            print(f"*error, can't find code file {codeFile} required for translation.")
            print(f"  command, data, or holdclient codes. Some Results will appear untranslated.")
            return cmd_dict
        # Symphony's translate command passes previously translated material without issue.
        cat_process = subprocess.Popen(["cat", f"{codeFile}"], stdout=subprocess.PIPE)
        translate_process = subprocess.Popen([f"{self.translate_cmd}"], stdin=cat_process.stdout, stdout=subprocess.PIPE)
        for line in translate_process.stdout:
            ct = line.decode().split('|')
            if not ct or len(ct) < 2:
                continue
            code = ct[0]
            translation = self.cleanString(ct[1], us=us)
            if cmd_dict.get(code):
                if debug:
                    self.errors += 1
                    print("overwriting existing value of {code}.")
            cmd_dict[code] = translation
        # Wait and test pipe closure.
        translate_process.wait()
        if translate_process.returncode == 0:
            if debug:
                print(f"finished translation of {codeFile}")
        else:
            print(f"**error reading '{codeFile}'")
            for line in translate_process.stderr:
                print(line.strip())
        if debug:
            for key,value in cmd_dict.items():
                print(f"{key} and {value}")
        return cmd_dict

    # Converts 'selitem -oIB' output to a dictionary where the key is the item ID 
    # and the stored value is the associated bar code for the item.  
    # param: line:str - output line from selitem -oIB untouched.  
    def readBarCodes(self, barCodeFile:str):
        bar_codes = {}
        if exists(barCodeFile):
            with open(barCodeFile, mode='rt', encoding=self.encoding) as f:
                for line in f:
                    # Input line should look like '12345|55|1|31221012345678|' Straight from selitem -oIB
                    ck_cs_cn_bc = line.split('|')
                    if len(ck_cs_cn_bc) < 4:
                        errors += 1
                    # clean the definition of special characters.
                    item_key = f"{ck_cs_cn_bc[0]}|{ck_cs_cn_bc[1]}|{ck_cs_cn_bc[2]}|"
                    item_id = ck_cs_cn_bc[3].rstrip()
                    bar_codes[item_key] = item_id
        else:
            print(f"*warning: expected but couldn't find '{barCodeFile}'.")
        return bar_codes           
        
    # Some data codes don't have definitions in the vendor-supplied datacode file. 
    # This method allows you to add or update better definitions or translations. 
    # param: dataCodes:dict|str - new data code definitions to add to, and or clobber existing
    # codes. Can be a dict in which case all the items are added to the datacodes, but
    # if dataCodes is a string, it will be assumed to be a pipe-delimited data code 
    # definition pair, which will be added as a single entry. 
    def updateDataCodes(self, dataCodes:dict):
        if dataCodes:
            for key, value in dataCodes.items():
                # Make sure dict keys don't include special chars and if they are 
                # datacodes, replace spaces with underscores. 
                value = self.cleanString(value, us=True)
                self.data_codes[key] = value

    # Cleans a standard set of special characters from a string. 
    # param: string to clean. 
    # param: us:bool - True will remove all special characters 
    #   and replace any spaces with underscores. Default False, leave spaces intact.  
    def cleanString(self, s:str, us:bool=False) -> str:
        s = s.strip()
        # Remove any weird characters. This should cover it, they're pretty clean.
        for ch in ['\\','/','`','*','{','}','[',']','(',')','<','>','!','$',',','\'']:
            if ch in s:
                s = s.replace(ch, "")
        # The command code is a s, not an identifier, so don't convert it into snake case.
        if us:
            s = s.replace(' ', '_').lower()
        return s

    # Converts the many types of date strings stored in History logs into 'yyyy-mm-dd' database-ready format. 
    # param: data string which may or may not contain a date string. 
    # return: the date converted to timestamp, or '1900-01-01' if a date can't be parsed from the string.
    def toDate(self, data:str, justDate:bool=False) -> str:
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
            if justDate:
                return f"{d}"
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


def usage():
    usage_text = f"""
    Usage: python {APP}.py [options]

    Converts SirsiDynix History logs into JSON. See enclosed license
    for distribution restrictions. It uses cmdcode and datacode files 
    found in the standard Symphony directory of $HOME/Unicorn/Custom.
    If the application is not run on the ILS as is the case in testing
    it will look in the lib/ directory for translated versions of cmdcode
    and datacode.

    The script will automatically handle log file compression if required.

    Date handling: SirsiDynix records dates in a number of 
    ways in the log files. {APP} converts them to 'yyyy-mm-dd' format.
    
    User PINs are redacted during conversion. 

    -c --clientCodes="/foo/clients.txt": Path to hold client table
       A version exists in 'test/'.
    -d: Turns on debug information.
    -H --HistFile="/foo/bar.hist": REQUIRED. Hist log file or files to convert.
        Multiple files can be specified as 'file1,file2, file3, ...'.
    -h: Prints this help message.
    -I --ItemKeyBarcodes="/foo/bar/items.lst": Optional. Path to the 
       list of all item key / barcodes in 'c_key|call_seq|copy_num|item_id'
       form. Use 'selitem -oIB' >items.lst.
    -m: Output as MongoDB JSON (each record as a separate object).
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
    barcodes    = ''
    clientcodes = ''
    itemBarcodes       = ''
    # Translate command codes and data codes if required, and iff translate available.
    try:
        opts, args = getopt.getopt(argv, "c:dH:I:mv", ["clientCodes=", "HistFile=", "ItemKeyBarcodes="])
    except getopt.GetoptError:
        usage()
    for opt, arg in opts:
        if opt in ("-c", "--clientCodes"):
            clientcodes = arg
        elif opt in "-d":
            debug = True
        elif opt in ("-H", "--HistFile"):
            arg_list = arg.split(',')
            for my_arg in arg_list:
                a = my_arg.strip()
                if a:
                    hist_files.append(a)
        elif opt in "-h":
            usage()
        elif opt in ("-I", "--ItemKeyBarcodes"):
            itemBarcodes = arg
        elif opt in "-m":
            use_mongo_json = True
        elif opt in "-v":
            print(f"{APP} version: {VERSION}.")
            sys.exit(0)
        else:
            print(f"invalid option {arg}")
        
    hist = Hist(barCodes=itemBarcodes, clientCodes=clientcodes, debug=debug)
    ## Load Codes and Definitions
    # Add data codes that don't seem to be in the default Symphony file on our ILS.
    # Some codes missing and location on ILS is unknow (at this time).
    data_code_extras= {}
    data_code_extras['uF'] = "user_first_name"
    data_code_extras['uL'] = "user_last_name"
    data_code_extras['uU'] = "user_prefered_name"
    data_code_extras['P7'] = "circ_rule"
    hist.updateDataCodes(dataCodes=data_code_extras)
    # Convert hist file to JSON
    for hist_file in hist_files:
        hist.toJson(hist_file, mongoDb=use_mongo_json)
    # Output report.
    print(f"Total cmd codes read:    {hist.getCommandCodeCount()}\nTotal data codes read:   {hist.getDataCodeCount()}\nTotal history records:   {hist.getLineCount()}")
    print(f"Total items read:     {hist.getBarCodeCount()}")
    print(f"Total errors:     {hist.getErrorCount()}")
    missing_data_codes = hist.getMissingDataCodes()
    if missing_data_codes and debug:
        err_messages = 25
        err_count    = 0
        print(f"Data codes without definitions have been recorded as 'data_code_[data code value]':'[read value]'")
        for (line, code) in missing_data_codes.items():
            print(f" * on line {line} => {code}")
            err_count += 1
            if err_count >= err_messages:
                print(f" ... with {len(missing_data_codes) - err_count} additional that will not be display.")
                break

if __name__ == "__main__":
    if len(sys.argv) == 1:
        import doctest
        doctest.testfile("hist.tst")
    else:
        main(sys.argv[1:])
# EOF