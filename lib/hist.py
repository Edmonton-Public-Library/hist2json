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
import re
from os import path
import sys
import json
import gzip
from pathlib import Path
from datetime import datetime
###
# Class to read SirsiDynix Symphony history (log) files. 
# The parameters of commandCodes, dataCodes, and barCodes
# are expected to be dictionaries, or a string-path to
# a file that contains the list. For example: 
# 
# hF|Receive From Transit 
# 
# The dictionaries commandCodes, dataCodes are keys of 
# two character codes, and their definition counterparts. 
# barCodes are made up of 4 pipe-delimited fields made of
# the cat key, sequence number, item id and finally the 
# item ID. The first 3 are the key, as in item key, the last
# the barcode. For example:
# 
# 12345|34|9|31221012345678 
###

class Hist:

    # Constructor 
    # param: histFile:str - name of the history file to parse. See debug switch for exceptions. 
    # param: encoding:str - encoding to be used when reading and writing to files. 
    #   The default is 'ISO-8859-1' but 'UTF-8' is acceptable as well. 
    # param: unicornPath:str - unicorn directory on the ILS. See debug switch for exceptions. 
    # param: commandCodes - a dictionary or path to the cmdcode file. See debug switch for exceptions. 
    #   By default the application will look in the unicorn directory where Symphony normally keeps it.  
    # param: dataCodes 
    def __init__(self, encoding:str='ISO-8859-1', unicornPath:str='..', 
      commandCodes=None, dataCodes=None, barCodes=None, debug:bool=False):
        if debug:
            cus_dir = path.join(unicornPath, 'test')
            bin_dir = path.join(unicornPath, 'test')
            log_dir = path.join(unicornPath, 'test')
        else:
            cus_dir = path.join(unicornPath, 'Custom')
            bin_dir = path.join(unicornPath, 'Bin')
            log_dir = path.join(unicornPath, 'Log')
        self.cmd_code_path  = path.join(cus_dir, 'cmdcode')
        self.data_code_path = path.join(cus_dir, 'datacode')
        self.translate_cmd  = path.join(bin_dir, 'translate')
        self.encoding       = encoding
        self.cmd_codes      = {}
        if isinstance(commandCodes, dict):
            self.cmd_codes  = commandCodes
        else:
            self.readConfiguredCommandCodes()
        self.data_codes     = {}
        if isinstance(dataCodes, dict):
            self.data_codes = dataCodes
        else:
            self.readConfiguredDataCodes()
        self.bar_codes      = {}
        # Can specify a dict of IDs and barcodes for testing
        if isinstance(barCodes, dict):
            self.bar_codes = barCodes
        # More commonly specify a path to the selitem -oIB output file. 
        elif isinstance(barCodes, str):
            self.readBarCodes(barCodes)
        else:
            print(f"WARNING: item IDs will not be converted into item barcodes.")
        self.hold_client_table = {
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
        
        if debug:
            print(f"cmd_code_path :{self.cmd_code_path }")
            print(f"data_code_path:{self.data_code_path}")
            print(f"translate_cmd :{self.translate_cmd }")
            print(f"encoding      :{self.encoding      }")
            print(f"cmd_codes len :{len(self.cmd_codes)}")
            print(f"data_codes len:{len(self.data_codes)}")
            print(f"barCode file  :{barCodes}")
            print(f"bar_codes read:{len(self.bar_codes)}")
    
    # Given an item key will lookup the associated barcode. 
    # param: item key. Pipe seperated cat key, call sequence, item copy. 
    # param: dictionary of item keys, and barcode values. 
    # return: barcode or None if lookup fails.
    def lookupItemId(self, item_key:str) -> str:
        # Given an item id as: f"{_item_key_}|" or '12345|55|1|' get the item id '31221012345678'
        if self.bar_codes:
            if item_key in self.bar_codes.keys():
                return self.bar_codes[item_key]

    # Translates command, data, and client codes into human-readable form. 
    # For example 'CV' command code will translate into 'Charge Item'. 
    # param: rawCode:str - command, data, or client code string. 
    def translateCode(self, rawCode:str, whichDict:str='datacode', verbose:bool=False, asValue:bool=False, lineNumber:int=1) ->str:
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
                if verbose:
                    sys.stderr.write(f"* warning: on line {lineNumber}, '{rawCode}' is an unrecognized data code.\n")
        elif whichDict == 'clientcode':
            translated_code = self.hold_client_table.get(rawCode)
        else:
            if verbose:
                sys.stderr.write(f"* warning: on line {lineNumber}, invalid lookup for {rawCode} in table {whichDict}\n")
        if asValue:
            return value
        # If get failed on any of the above dictionaries send back a cleaned version of the code.
        if not translated_code:
            return rawCode
        return translated_code

    # Converts a single line of a hist file into JSON. 
    # param: data:list - string fields from the line of hist. 
    # param: line_no:int - the current line of the hist file. 
    # param: verbose:bool - True will output warnings about missing data code translations. 
    #   False will output fewer messages.  
    def convertLogEntry(self, data:list, line_no:int, verbose=False):
        # E202303231010243024R ^S00hEFWCALCIRC^FFCIRC^FEEPLCAL^FcNONE^dC19^**tJ2371230**^**tL55**^**IS1**^**HH41224719**^nuEPLRIV^nxHOLD^nrY^Fv2147483647^^O
        # Where the following fields are                                       cat_key     seq_no   copy_no   hold_key  
        record = {}
        record['timestamp'] = self.toDate(data[0])  # 'E202301180024483003R' => '20230118002448'
        err_count = 0
        record['command_code'] = self.translateCode(data[1], whichDict='commandcode', verbose=verbose, lineNumber=line_no)
        if not record.get('command_code'):
            err_count += 1
            sys.stderr.write(f"*error on line {line_no}, missing command_code!\n")
            return (err_count, record)
        # Capture 'hE' transit item data codes for cat key, call seq, and copy number. 
        item_key = []
        # Convert all data codes, or report those that are not defined.
        for field in data[2:]:
            data_code = self.translateCode(field, verbose=verbose, lineNumber=line_no)
            # Don't process empty data fields '^^' or EOL '0' or 'O0'.
            if len(data_code) < 2 or data_code == 'O0':
                continue
            value = self.translateCode(field, verbose=verbose, asValue=True, lineNumber=line_no)
            if len(data_code) == 2:
                data_code = f"data_code_{data_code}"
                record[data_code] = value
                continue
            if re.match(r'(.+)?date', data_code) or data_code == 'user_last_activity':
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
                if item_key:
                    item_key.append(value)
                    _item_key_ = '|'.join(item_key)
                    barcode = self.lookupItemId(f"{_item_key_}|")
                    if barcode:
                        data_code = "item_id"
                        value = barcode
            # Get rid of this tags leading '|a' in customer in this specific data code.
            elif re.match(r'entry_or_tag_data', data_code):
                value = value[2:]
            elif re.match(r'client_type', data_code):
                value = self.translateCode(value, whichDict='clientcode', verbose=verbose, lineNumber=line_no)
            record[data_code] = value
        if record['command_code'] == "Discharge Item" and not record.get('date_of_discharge'):
            # Discharge item with no 'CO', 'date_of_discharge'.
            record['date_of_discharge'] = self.toDate(data[0], justDate=True)
        return (err_count, record)

    # Converts and writes the JSON hist file contents to file.
    def toJson(self, histFile:str=None, outFile:str=None, mongoDb:bool=False):
        if not histFile:
            return
        # TODO: remove tricky path handling for hist files.
        # hist_file     = path.join(log_dir, 'Hist', histFile)
        hist_file = histFile
        is_compressed_hist = True
        if not path.isfile(hist_file):
            sys.stderr.write(f"**error, no such file {hist_file}.\n")
            sys.exit()
        print(f"hist_file     :{self.hist_file      }")
        # test if the file is a zipped history file. They are named '*.Z'.
        if not hist_file.endswith('.Z'):
            is_compressed_hist = False
        hist_log_list = []
        if not outFile:
            json_file = Path(self.hist_file).with_suffix('')
            json_file = f"{self.hist_file}.json"
        else:
            json_file = outFile
        ## Process the history log into JSON.
        # Open the json file ready for output.
        j = open(json_file, mode='w', encoding=self.encoding)
        # History file handle; either gzipped or regular text.
        if is_compressed_hist:
            f = gzip.open(self.hist_file, mode='rt', encoding=self.encoding)
        else: # Not a zipped history file
            f = open(self.hist_file, mode='r', encoding=self.encoding)
        # Process each of the lines.
        line_no = 0
        missing_data_codes = 0
        for line in f:
            line_no += 1
            fields = line.strip().split('^')
            (errors, record) = self.convertLogEntry(fields, line_no)
            missing_data_codes += errors
            # Append to list if output JSON proper
            if not mongoDb:
                hist_log_list.append(record)
            else: # else add each record to file a-la-MongoDB.
                json.dump(record, j, ensure_ascii=False, indent=2)
        if not mongoDb:
            json.dump(hist_log_list, j, ensure_ascii=False, indent=2)
        j.close()

    # Reads the command codes file from the Unicorn directory. 
    # unless the constructor included debug=True, in which
    # case the ../test directory will be searched for command
    # code, data code, and item lists. The application will 
    # then expect to find the test hist file in ../test/Hist.   
    def readConfiguredCommandCodes(self):
        if not path.exists(self.cmd_code_path):
            msg = f"The file {self.cmd_code_path} was not found."
            raise FileNotFoundError(msg)
        with open(self.cmd_code_path, mode='r', encoding=self.encoding) as f:
            for line in f:
                self.addToDictionary(line, self.cmd_codes, underscore=False)

    # Reads the data codes from the system datacode file in the Unicorn 
    # directory, or if debug is used in the constructor, from the datacode
    # file in the test directory.  
    def readConfiguredDataCodes(self):
        if not path.exists(self.data_code_path):
            msg = f"The file {self.data_code_path} was not found."
            raise FileNotFoundError(msg)
        with open(self.data_code_path, mode='r', encoding=self.encoding) as f:
            for line in f:
                self.addToDictionary(line, self.data_codes, underscore=True)

    # Converts 'selitem -oIB' output to a dictionary where the key is the item ID 
    # and the stored value is the associated bar code for the item.  
    # param: line:str - output line from selitem -oIB untouched. 
    # return: 1 
    def readBarCodes(self, barCodeFile:str):
        if not path.exists(barCodeFile):
            msg = f"The file {barCodeFile} was not found."
            raise FileNotFoundError(msg)
        with open(barCodeFile, mode='r', encoding=self.encoding) as f:
            for line in f:
                # Input line should look like '12345|55|1|31221012345678|' Straight from selitem -oIB
                ck_cs_cn_bc = line.split('|')
                if len(ck_cs_cn_bc) < 4:
                    errors += 1
                # clean the definition of special characters.
                item_key = f"{ck_cs_cn_bc[0]}|{ck_cs_cn_bc[1]}|{ck_cs_cn_bc[2]}|"
                item_id = ck_cs_cn_bc[3].rstrip()
                self.bar_codes[item_key] = item_id

    # Reads the client code table. The table contains the definitions 
    # used by Symphony for translating client codes into human-readable 
    # client type values, like 'BC_MOBILE', 'BC_CIRC' etc. This method 
    # is typically called from the constructor when the calling application
    # starts. 
    # param: clientFile:str - path to the client file. 
    def readClientCodes(self, clientFile:str):
        if path.isfile(clientFile) == False:
            sys.stderr.write(f"**error, no such client file {clientFile}.\n")
            sys.exit()
        try:
            with open(clientFile, mode='r') as j_clients:
                self.hold_client_table = json.load(j_clients)
        except:
            sys.stderr.write(f"**error while reading JSON from {clientFile}.\n")
            sys.exit()
        

    # Some data codes don't have definitions in the vendor-supplied datacode file. 
    # This method allows you to add or update better definitions or translations. 
    # param: dataCodes:dict|str - new data code definitions to add to, and or clobber existing
    # codes. Can be a dict in which case all the items are added to the datacodes, but
    # if dataCodes is a string, it will be assumed to be a pipe-delimited data code 
    # definition pair, which will be added as a single entry. 
    def updateDataCodes(self, dataCodes):
        if dataCodes:
            if isinstance(dataCodes, dict):
                for key, value in dataCodes.items():
                    entry = f"{key}|{value}"
                    self.addToDictionary(entry, self.data_codes, underscore=True)
            elif isinstance(dataCodes, str):
                entry = dataCodes
                self.addToDictionary(entry, self.data_codes, underscore=True)

    # Helper function that, given a string of a Symphony command code or 
    # data code, and its english translation separated by a pipe, loads 
    # the code as the key and definition as the values. 
    # param: line:str line of code|definition. 
    # param: dictionary:dict destination storage of the key value pair. 
    # param: underscore:bool by default all spaces will also be converted 
    #   to underscores. False will turn off this feature. 
    def addToDictionary(self, line:str, dictionary:dict, underscore:bool):
        key_value = line.split('|')
        # clean the definition of special characters.
        key = key_value[0]
        value = key_value[1]
        # Make sure dict keys don't include special chars and if they are 
        # datacodes, replace spaces with underscores. 
        value = self.cleanString(value, underscore=underscore)
        dictionary[key] = value

    # Cleans a standard set of special characters from a string. 
    # param: string to clean. 
    # param: underscore:bool - True will remove all special characters 
    #   and replace any spaces with underscores. Default False, leave spaces intact.  
    def cleanString(self, s:str, underscore:bool=False) -> str:
        # Remove any weird characters. This should cover it, they're pretty clean.
        for ch in ['\\','/','`','*','_','{','}','[',']','(',')','<','>','!','$',',','\'']:
            if ch in s:
                s = s.replace(ch, "")
        # The command code is a s, not an identifier, so don't convert it into snake case.
        if underscore:
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

if __name__ == "__main__":
    import doctest
    doctest.testfile("hist.tst")