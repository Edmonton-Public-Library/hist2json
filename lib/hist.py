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

    def __init__(self, histFile:str, encoding:str='ISO-8859-1', unicornPath:str='..', 
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
        self.hist_dir       = path.join(log_dir, 'Hist')
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
        self.hist_file      = histFile
        self.hist_log_list       = []
        self.isCompressed   = histFile.endswith('.Z')
        
        if debug:
            print(f"cmd_code_path :{self.cmd_code_path }")
            print(f"data_code_path:{self.data_code_path}")
            print(f"translate_cmd :{self.translate_cmd }")
            print(f"hist_dir      :{self.hist_dir      }")
            print(f"encoding      :{self.encoding      }")
            print(f"cmd_codes len :{len(self.cmd_codes)}")
            print(f"data_codes len:{len(self.data_codes)}")
            print(f"barCode file  :{barCodes}")
            print(f"bar_codes read:{len(self.bar_codes)}")
    
    # Given an item key will lookup the associated barcode. 
    # param: item key. Pipe seperated cat key, call sequence, item copy. 
    # param: dictionary of item keys, and barcode values. 
    # return: barcode or None if lookup fails.
    def lookup_item_id(self, item_key:str) -> str:
        # Given an item id as: f"{_item_key_}|" or '12345|55|1|' get the item id '31221012345678'
        if self.bar_codes:
            if item_key in self.bar_codes.keys():
                return self.bar_codes[item_key]

    # TODO: Test
    def get_log_entry(self, data:list, line_no:int, verbose=False):
        # E202303231010243024R ^S00hEFWCALCIRC^FFCIRC^FEEPLCAL^FcNONE^dC19^**tJ2371230**^**tL55**^**IS1**^**HH41224719**^nuEPLRIV^nxHOLD^nrY^Fv2147483647^^O
        # Where the following fields are                                       cat_key     seq_no   copy_no   hold_key  
        record = {}
        record['timestamp'] = self.to_date(data[0][1:15])  # 'E202301180024483003R' => '20230118002448'
        # convert command code.
        cmd = data[1][3:5]
        err_count = 0
        record['command_code'] = self.cmd_codes[cmd]
        # Capture 'hE' transit item data codes for cat key, call seq, and copy number. 
        item_key = []
        # Convert all data codes, or report those that are not defined.
        for field in data[2:]:
            dc = field.strip()[0:2]
            # Don't process empty data fields '^^' or EOL '0' or 'O0'.
            if len(dc) < 2 or dc == 'O0':
                continue
            try:
                data_code = self.data_codes[dc]
                value = field[2:]
                if re.match(r'(.+)?date', data_code) or data_code == 'user_last_activity':
                    value = self.to_date(value)
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
                        barcode = self.lookup_item_id(f"{_item_key_}|")
                        if barcode:
                            data_code = "item_id"
                            value = barcode
                # Get rid of this tags leading '|a' in customer in this specific data code.
                elif re.match(r'entry_or_tag_data', data_code):
                    value = value[2:]
                elif re.match(r'client_type', data_code):
                    try:
                        temp = HOLD_CLIENT_TABLE[value]
                        value = temp
                    except KeyError:
                        err_count += 1
                        sys.stderr.write(f"* warning on line {line_no}:\n*   missing hold client type: {value}\n")
                record[data_code] = value
            except KeyError:
                err_count += 1
                dc = self.clean_string(dc)
                data_code = f"data_code_{dc}"
                self.data_codes[dc] = data_code
                if err_count == 1:
                    sys.stderr.write(f"* warning on line {line_no}:\n*   {data}\n")
                print(f"*   '{dc}' is an unrecognized data code and will be recorded as 'data_code_{dc}': '{field[2:]}'.")
        return (err_count, record)

    # Converts and writes the JSON hist file contents to file.
    # TODO: test
    def toJson(self, outFile:str=None, mongoDb:bool=False):
        json_file = outFile
        if not json_file:
            json_file = f"{Path(self.hist_file).with_suffix('')}"
            json_file = f"{self.hist_file}.json"
        ## Process the history log into JSON.
        # Open the json file ready for output.
        j = open(json_file, mode='w', encoding='ISO-8859-1')
        # History file handle; either gzipped or regular text.
        if self.isCompressed == True:
            f = gzip.open(self.hist_file, mode='rt', encoding='ISO-8859-1')
        else: # Not a zipped history file
            f = open(self.hist_file, mode='r', encoding='ISO-8859-1')
        # Process each of the lines.
        line_no = 0
        missing_data_codes = 0
        for line in f:
            line_no += 1
            fields = line.strip().split('^')
            (errors, record) = self.get_log_entry(fields, line_no)
            missing_data_codes += errors
            # Append to list if output JSON proper
            if not mongoDb:
                self.hist_log_list.append(record)
            else: # else add each record to file a-la-MongoDB.
                json.dump(record, j, ensure_ascii=False, indent=2)
        if not mongoDb:
            json.dump(self.hist_log_list, j, ensure_ascii=False, indent=2)
        j.close()

    # Reads the command codes file from the Unicorn directory.  
    def readConfiguredCommandCodes(self):
        if not path.exists(self.cmd_code_path):
            msg = f"The file {self.cmd_code_path} was not found."
            raise FileNotFoundError(msg)
        with open(self.cmd_code_path, mode='r', encoding=self.encoding) as f:
            for line in f:
                self.add_to_dictionary(line, self.cmd_codes, underscore=False)

    # Reads the data codes from the system datacode file in the Unicorn 
    # directory, or if debug is used in the constructor, from the datacode
    # file in the test directory.  
    def readConfiguredDataCodes(self):
        if not path.exists(self.data_code_path):
            msg = f"The file {self.data_code_path} was not found."
            raise FileNotFoundError(msg)
        with open(self.data_code_path, mode='r', encoding=self.encoding) as f:
            for line in f:
                self.add_to_dictionary(line, self.data_codes, underscore=True)

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

    # Some data codes don't have definitions in the vendor-supplied datacode file. 
    # This allows you to add new ones, or add better definitions or different languages. 
    # param: dataCodes:dict|str - new data code definitions to add to, and or clobber existing
    # codes. Can be a dict in which case all the items are added to the datacodes, but
    # if dataCodes is a string, it will be assumed to be a pipe-delimited data code 
    # definition pair, which will be added as a single entry. 
    def updateDataCodes(self, dataCodes):
        if dataCodes:
            if isinstance(dataCodes, dict):
                for key, value in dataCodes.items():
                    entry = f"{key}|{value}"
                    self.add_to_dictionary(entry, self.data_codes, underscore=True)
            elif isinstance(dataCodes, str):
                entry = dataCodes
                self.add_to_dictionary(entry, self.data_codes, underscore=True)

    # Helper function that, given a string of a Symphony command code or 
    # data code, and its english translation separated by a pipe, loads 
    # the code as the key and definition as the values. 
    # param: line:str line of code|definition. 
    # param: dictionary:dict destination storage of the key value pair. 
    # param: underscore:bool by default all spaces will also be converted 
    #   to underscores. False will turn off this feature. 
    def add_to_dictionary(self, line:str, dictionary:dict, underscore:bool):
        key_value = line.split('|')
        # clean the definition of special characters.
        key = key_value[0]
        value = key_value[1]
        # Make sure dict keys don't include special chars and if they are 
        # datacodes, replace spaces with underscores. 
        value = self.clean_string(value, underscore=underscore)
        dictionary[key] = value

    
    # Cleans a standard set of special characters from a string. 
    # param: string to clean. 
    # param: underscore:bool - True will remove all special characters 
    #   and replace any spaces with underscores. Default False, leave spaces intact.  
    def clean_string(self, s:str, underscore:bool=False) -> str:
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
    def to_date(self, data:str) -> str:
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

if __name__ == "__main__":
    import doctest
    doctest.testfile("hist.tst")