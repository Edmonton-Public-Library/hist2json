Provides tests for hist2json


>>> from hist2json import *

Test the get_log_entry() method.
------------------------------------

>>> c = {}
>>> count = add_to_dictionary('IY|Cancel Hold-bob|', c, False)
>>> d = {}
>>> count = add_to_dictionary('FE|Station Library|', d, True)
>>> count = add_to_dictionary('FF|Library Station|', d, True)
>>> count = add_to_dictionary('FG|Library|', d, True)
>>> data = 'E202301180024493003R ^S59IYFWCLOUDLIBRARY^FEEPLMNA^FGEPLHVY^FFEPLCPL^O'.strip().split('^')
>>> print(get_log_entry(data,c,d,1))
(0, {'timestamp': '2023-01-18 00:24:49', 'command_code': 'Cancel Hold-bob', 'station_library': 'MNA', 'library': 'HVY', 'library_station': 'CPL'})
>>> count = add_to_dictionary('hE|Transit Item|', c, False)
>>> count = add_to_dictionary('tJ|Catalog Key Number|', d, True)
>>> count = add_to_dictionary('tL|Call Sequence Code|', d, True)
>>> count = add_to_dictionary('IS|Copy Number|', d, True)
>>> i = {}
>>> add_itemkey_barcode('2371230|55|1|31221012345678   |', i)
1
>>> data = 'E202303231010243024R ^S00hEFWCALCIRC^FFCIRC^FEEPLCAL^FcNONE^dC19^tJ2371230^tL55^IS1^HH41224719^nuEPLRIV^nxHOLD^nrY^Fv2147483647^^O'.strip().split('^')
>>> print(get_log_entry(data,c,d,1,item_key_barcodes=i))
(7, {'timestamp': '2023-03-23 10:10:24', 'command_code': 'Transit Item', 'library_station': 'C', 'station_library': 'CAL', 'catalog_key_number': '2371230', 'call_sequence_code': '55', 'item_id': '31221012345678'})


Test lookup_item_id() method
-------------------------------
Given an item id as: f"{_item_key_}|" or '12345|55|1|' get the item id '31221012345678'

>>> i = {}
>>> add_itemkey_barcode('12345|55|1|31221012345678', i)
1
>>> print(f"{lookup_item_id('12345|55|1|', i)}")
31221012345678
>>> lookup_item_id('11111|55|1|', i)
>>> lookup_item_id('', i)


Test string cleaning.
---------------------

Cleans a standard set of special characters from a string. 
param: string to clean. 
param: spc_to_underscore as boolean, True will remove all special characters and replace any spaces with underscores.

>>> s = """This [isn't] a \$tring th*t i've (liked) until_now} """
>>> print(f"{clean_string(s)}")
This isnt a tring tht ive liked untilnow 


Test to_date() method
---------------------

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


Test add_itemkey_barcode() method
---------------------------------


>>> i = {}
>>> add_itemkey_barcode('12345|55|1|31221012345678', i)
1
>>> print(f"{i}")
{'12345|55|1|': '31221012345678'}


Test translate()
----------------

Uses the Symphony translate command to translate the command and data code files. 
Translation will run automatically if the following conditions are met; the script is running
on the ILS, and the '-D' and / or the '-C' flag(s) were not selected. 
Requirement: the script must be running on the ILS.
param: code file string, either the command or data code path. 
param: is_data_code boolean, True the file is the data code file, False for command code file. .
return: translated file name.

This function can only be used if testing on the ILS since the translate function lives there.


Test add_to_dictionary() method. 
--------------------------------

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