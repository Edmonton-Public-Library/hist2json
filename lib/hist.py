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
###
# Class to read SirsiDynix Symphony history (log) files. 
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
        self.line_no        = 0
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
    
    # Reads the command codes file from the Unicorn directory.  
    def readConfiguredCommandCodes(self):
        if not path.exists(self.cmd_code_path):
            msg = f"The file {self.cmd_code_path} was not found."
            raise FileNotFoundError(msg)
        with open(self.cmd_code_path, mode='r', encoding=self.encoding) as f:
            for line in f:
                self.add_to_dictionary(line, self.cmd_codes, underscore=False)

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

    # Helper function that, given a string of a Symphony command code or 
    # data code, and its english translation separated by a pipe, loads 
    # the code as the key and definition as the values. 
    # param: line:str line of code|definition. 
    # param: dictionary:dict destination storage of the key value pair. 
    # param: underscore:bool by default all spaces will also be converted 
    #   to underscores. False will turn off this feature. 
    def add_to_dictionary(self, line:str, dictionary:dict, underscore:bool, debug:bool=False):
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