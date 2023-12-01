Provides tests for hist.py
==========================
Why a hist_prod.tst file? Because the hold_client_table.lst currently 
is found in the project directory, not in `getpathname custom` so it 
is specifically called on production, but not on the dev machine.

>>> from hist2json import Hist



>>> hist = Hist(clientCodes='hold_client_table.lst', debug=True)
WARNING: item IDs will not be converted into item barcodes.
encoding        :ISO-8859-1
cmd_codes len   :533
data_codes len  :1881
hold_clients len:23
bar_codes read  :0


>>> print(f"{hist.cmd_codes['AQ']}")
Activate Location
>>> print(f"{hist.data_codes['0A']}")
item_category_three
>>> hist.updateDataCodes({'0A':'See me changed'})
>>> print(f"{hist.data_codes['0A']}")
see_me_changed

Test reading bar codes from a file 
----------------------------------
>>> hist = Hist(barCodes='test/items.lst', clientCodes='hold_client_table.lst', debug=True)
encoding        :ISO-8859-1
cmd_codes len   :533
data_codes len  :1881
hold_clients len:23
bar_codes read  :1630964
>>> hist = Hist(barCodes='test/items1.lst', clientCodes='hold_client_table.lst', debug=True)
encoding        :ISO-8859-1
cmd_codes len   :533
data_codes len  :1881
hold_clients len:23
bar_codes read  :10


Test convertLogEntry()
----------------------
>>> data = "E202310100510083031R ^S01EVFFADMIN^FEEPLRIV^FcNONE^NQ31221112079020^^O00049".split('^')
>>> hist.convertLogEntry(data, 1)
(0, {'timestamp': '2023-10-10 05:10:08', 'command_code': 'Discharge Item', 'station_library': 'RIV', 'station_login_clearance': 'NONE', 'item_id': '31221112079020', 'date_of_discharge': '2023-10-10'})
>>> h = [
... "E202304110001112995R ^S05IYFWOVERDRIVE^FEEPLMNA^FFSIPCHK^FcNONE^FDSIPCHK^dC6^UO21221020087836^UK4/11/2023^OAY^^O^O0",
... "E202304110001162995R ^S01JZFFBIBLIOCOMM^FcNONE^FEEPLRIV^UO21221023395855^Uf0490^NQ31221059760525^HB04/11/2024^HKTITLE^HOEPLRIV^dC5^^O00112^zZProblem^O0"
... ]
>>> line_no = 1
>>> for h_line in h:
...     (err, rec) = hist.convertLogEntry(h_line.split('^'), line_no)
...     print(f"{rec}")
...     line_no += 1
{'timestamp': '2023-04-11 00:01:11', 'command_code': 'Edit User Part B', 'station_library': 'MNA', 'station_login_user_access': 'SIPCHK', 'station_login_clearance': 'NONE', 'station': 'SIPCHK', 'client_type': 'CLIENT_SIP2', 'user_id': '21221020087836', 'user_last_activity': '2023-04-11', 'user_edit_override': 'Y'}
{'timestamp': '2023-04-11 00:01:16', 'command_code': 'Create Hold', 'station_login_clearance': 'NONE', 'station_library': 'RIV', 'user_id': '21221023395855', 'user_pin': 'xxxxx', 'item_id': '31221059760525', 'date_hold_expires': '2024-04-11', 'hold_type': 'TITLE', 'hold_pickup_library': 'RIV', 'client_type': 'CLIENT_ONLINE_CATALOG', 'data_code_zZ': 'Problem'}
>>> hist.getMissingDataCodes()
{1: 'O0', 2: 'O0,zZ'}



Test string cleaning.
---------------------
Cleans a standard set of special characters from a string. 
param: string to clean. 
param: spc_to_underscore as boolean, True will remove all special characters and replace any spaces with underscores.
>>> s = """This [isn't] a \$tring th*t i've (liked) until_now} """
>>> print(f"{hist.cleanString(s)}")
This isnt a tring tht ive liked until_now


Test toDate() method
---------------------
>>> hist.toDate('01/13/2023')
'2023-01-13'
>>> hist.toDate('E202301180024483003R ')
'2023-01-18 00:24:48'
>>> hist.toDate('1/3/2023')
'2023-01-03'
>>> hist.toDate('20230118002448')
'2023-01-18 00:24:48'
>>> hist.toDate('01/13/2023,5:33 PM')
'2023-01-13'


Test getTranslation()
--------------------
>>> hist.getTranslation('EV', whichDict='commandcode')
'Discharge Item'
>>> hist.getTranslation('NQ')
'item_id'
>>> hist.getTranslation('6', whichDict='clientcode')
'CLIENT_SIP2'
>>> hist.getTranslation('99', whichDict='clientcode')
'99'
>>> hist.getTranslation('99', whichDict='clientcode')
'99'
>>> hist.getTranslation('S61EVFWSMTCHTLHL1', whichDict='commandcode')
'Discharge Item'
>>> hist.getTranslation('NQ31221120423970')
'item_id'
>>> hist.getTranslation('NQ31221120423970', asValue=True)
'31221120423970'
>>> hist.getTranslation('zZ12345678')
'zZ'


Test readClientCodes method
---------------------------
>>> hist = Hist(barCodes='test/items1.lst', clientCodes='hold_client_table.lst', debug=True)
encoding        :ISO-8859-1
cmd_codes len   :533
data_codes len  :1881
hold_clients len:23
bar_codes read  :10
>>> hist.hold_clients.keys()
dict_keys(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22'])



Test the hist.convertLogEntry() method.
------------------------------------

>>> hist.data_codes['FF']
'station_login_user_access'
>>> d = {'Xy': 'Station Library', 'Gg': 'Library', 'FF': 'Library Station'}
>>> hist.updateDataCodes(d)
>>> data = 'E202301180024493003R ^S05BYFWCLOUDLIBRARY^XyEPLMNA^GgEPLHVY^FFEPLCPL^O'.strip().split('^')
>>> print(hist.convertLogEntry(data,1))
(0, {'timestamp': '2023-01-18 00:24:49', 'command_code': 'Bill User', 'station_library': 'MNA', 'library': 'HVY', 'library_station': 'CPL'})
>>> data = 'E202303231010243024R ^S00hEFWCALCIRC^FFCIRC^FEEPLCAL^FcNONE^dC19^tJ2371230^tL55^IS1^HH41224719^nuEPLRIV^nxHOLD^nrY^Fv300000^^O'.strip().split('^')
>>> print(hist.convertLogEntry(data,2))
(0, {'timestamp': '2023-03-23 10:10:24', 'command_code': 'Transit Item', 'library_station': 'C', 'station_library': 'CAL', 'station_login_clearance': 'NONE', 'client_type': 'MOBLCIRC_S', 'catalog_key_number': '2371230', 'call_sequence_code': '55', 'copy_number': '1', 'hold_number': '41224719', 'transit_to': 'RIV', 'transit_reason': 'HOLD', 'data_code_nr': 'Y', 'max_length_of_transaction_response': '300000'})


Test that item discharge without dates get dates
------------------------------------------------

>>> hist = Hist(barCodes='test/items1.lst', clientCodes='hold_client_table.lst', debug=True)
encoding        :ISO-8859-1
cmd_codes len   :533
data_codes len  :1881
hold_clients len:23
bar_codes read  :10

With a discharge date.
>>> data = 'E202310100148422967R ^S61EVFWSMTCHTLHL1^FEEPLLHL^FFSMTCHT^FcNONE^FDSIPCHK^dC6^NQ31221120423970^CO10/10/2023,1:48^^O'.split('^')
>>> print(hist.convertLogEntry(data,1))
(0, {'timestamp': '2023-10-10 01:48:42', 'command_code': 'Discharge Item', 'station_library': 'LHL', 'station_login_user_access': 'SMTCHT', 'station_login_clearance': 'NONE', 'station': 'SIPCHK', 'client_type': 'CLIENT_SIP2', 'item_id': '31221120423970', 'date_of_discharge': '2023-10-10'})

Here is a discharge without a discharge date.
>>> data = 'E202310100510083031R ^S01EVFFADMIN^FEEPLRIV^FcNONE^NQ31221112079020^^O00049'.split('^')
>>> print(hist.convertLogEntry(data,2))
(0, {'timestamp': '2023-10-10 05:10:08', 'command_code': 'Discharge Item', 'station_library': 'RIV', 'station_login_clearance': 'NONE', 'item_id': '31221112079020', 'date_of_discharge': '2023-10-10'})


Test that items table (-I) is working
--------------------------------------

Add copy number and item id.
>>> data = 'E202304110918372988R ^S41hEFWJPLCIRC^FFCIRC^FEEPLJPL^FcNONE^dC19^tJ2161659^tL47^IS2^HH41326972^nuEPLLHL^nxHOLD^nrY^Fv2147483647^^O'.split('^')
>>> print(hist.convertLogEntry(data, 3))
(0, {'timestamp': '2023-04-11 09:18:37', 'command_code': 'Transit Item', 'station_login_user_access': 'CIRC', 'station_library': 'JPL', 'station_login_clearance': 'NONE', 'client_type': 'MOBLCIRC_S', 'catalog_key_number': '2161659', 'call_sequence_code': '47', 'copy_number': '2', 'item_id': '31221023069607', 'hold_number': '41326972', 'transit_to': 'LHL', 'transit_reason': 'HOLD', 'data_code_nr': 'Y', 'max_length_of_transaction_response': '2147483647'})

Fail lookup still writes all data, but without item_id.
>>> data = 'E202304110919010005R ^S93hEFWJPLCIRC^FFCIRC^FEEPLJPL^FcNONE^dC19^tJ278595^tL304^IS1^HH41327870^nuEPLLHL^nxHOLD^nrY^Fv2147483647^^O'.split('^')
>>> print(hist.convertLogEntry(data, 3))
(0, {'timestamp': '2023-04-11 09:19:01', 'command_code': 'Transit Item', 'station_login_user_access': 'CIRC', 'station_library': 'JPL', 'station_login_clearance': 'NONE', 'client_type': 'MOBLCIRC_S', 'catalog_key_number': '278595', 'call_sequence_code': '304', 'copy_number': '1', 'hold_number': '41327870', 'transit_to': 'LHL', 'transit_reason': 'HOLD', 'data_code_nr': 'Y', 'max_length_of_transaction_response': '2147483647'})


Test -c hold client table change works.
---------------------------------------

>>> data = 'E202304110006452995R ^S17IYFWOVERDRIVE^FEEPLMNA^FFSIPCHK^FcNONE^FDSIPCHK^dC6^UO21221027804613^UK4/11/2023^OAY^^O'.split('^')
>>> print(hist.convertLogEntry(data, 4))
(0, {'timestamp': '2023-04-11 00:06:45', 'command_code': 'Edit User Part B', 'station_library': 'MNA', 'station_login_user_access': 'SIPCHK', 'station_login_clearance': 'NONE', 'station': 'SIPCHK', 'client_type': 'CLIENT_SIP2', 'user_id': '21221027804613', 'user_last_activity': '2023-04-11', 'user_edit_override': 'Y'})
>>> hist = Hist(barCodes='test/items1.lst', clientCodes='test/hold_client_table.lst', debug=True)
encoding        :ISO-8859-1
cmd_codes len   :533
data_codes len  :1881
hold_clients len:24
bar_codes read  :10
>>> data = 'E202304110006462936R ^S18IYFWCLOUDLIBRARY^FEEPLMNA^FFSIPCHK^FcNONE^FDSIPCHK^dC6^UO21221029670244^UK4/11/2023^OAY^^O'.split('^')
>>> print(hist.convertLogEntry(data, 4))
(0, {'timestamp': '2023-04-11 00:06:46', 'command_code': 'Edit User Part B', 'station_library': 'MNA', 'station_login_user_access': 'SIPCHK', 'station_login_clearance': 'NONE', 'station': 'SIPCHK', 'client_type': 'CLIENT_SLAPPER', 'user_id': '21221029670244', 'user_last_activity': '2023-04-11', 'user_edit_override': 'Y'})

Test that birth_year gets converted
-----------------------------------
>>> data = 'E202304122237183071R ^S01JYFFADMIN^FbADMIN^FEEPLMNA^UO21221900070767^uFLinda^uLSpeer^uUSPEER , LINDA^uV0^UMEPLMNA^PEEPL_ADULT^P5ECONSENT^0D5:ECONSENT^UZ4/5/1971^UD4/12/2023^IbENGLISH^P7CIRCRULE^jlY^^O00179'.split('^')
>>> print(hist.convertLogEntry(data, 4))
(0, {'timestamp': '2023-04-12 22:37:18', 'command_code': 'Create User Part B', 'station_login_environment': 'ADMIN', 'station_library': 'MNA', 'user_id': '21221900070767', 'data_code_uF': 'Linda', 'data_code_uL': 'Speer', 'data_code_uU': 'SPEER , LINDA', 'data_code_uV': '0', 'user_library': 'MNA', 'user_profile_name': 'EPL_ADULT', 'user_category_5': 'ECONSENT', 'list_of_user_categories': '5:ECONSENT', 'birth_year': '1971-04-05', 'date_privilege_granted': '2023-04-12', 'language': 'ENGLISH', 'data_code_P7': 'CIRCRULE', 'data_code_jl': 'Y'})


Test start and end date range
-----------------------------

>>> hist = Hist(barCodes='test/items1.lst', clientCodes='hold_client_table.lst', debug=True)
encoding        :ISO-8859-1
cmd_codes len   :533
data_codes len  :1881
hold_clients len:23
bar_codes read  :10
>>> hist.toJson('test/test01.hist', start='20230412', end='20230413')
[
  {
    "timestamp": "2023-04-12 00:00:02",
    "command_code": "Edit User Part B",
    "station_library": "MNA",
    "station_login_user_access": "SIPCHK",
    "station_login_clearance": "NONE",
    "station": "SIPCHK",
    "client_type": "CLIENT_SIP2",
    "user_id": "21221021970238",
    "user_last_activity": "2023-04-11",
    "user_edit_override": "Y"
  },
  {
    "timestamp": "2023-04-12 00:00:02",
    "command_code": "Edit User Part B",
    "station_library": "MNA",
    "station_login_user_access": "SIPCHK",
    "station_login_clearance": "NONE",
    "station": "SIPCHK",
    "client_type": "CLIENT_SIP2",
    "user_id": "21221900064153",
    "user_last_activity": "2023-04-11",
    "user_edit_override": "Y"
  }
]

Test if toJson works with file
------------------------------
>>> testFile = 'test01.deleteme.json'
>>> hist.toJson('test/test01.hist', outFile=testFile, start='20230412', end='20230413')
>>> from os.path import exists
>>> import os, json
>>> if exists(testFile):
...     print(os.stat(testFile).st_size != 0)
True
>>> lines = []
>>> with open(testFile, 'rt') as f:
...     lines = json.load(f)
...     f.close()
>>> print(lines)
[{'timestamp': '2023-04-12 00:00:02', 'command_code': 'Edit User Part B', 'station_library': 'MNA', 'station_login_user_access': 'SIPCHK', 'station_login_clearance': 'NONE', 'station': 'SIPCHK', 'client_type': 'CLIENT_SIP2', 'user_id': '21221021970238', 'user_last_activity': '2023-04-11', 'user_edit_override': 'Y'}, {'timestamp': '2023-04-12 00:00:02', 'command_code': 'Edit User Part B', 'station_library': 'MNA', 'station_login_user_access': 'SIPCHK', 'station_login_clearance': 'NONE', 'station': 'SIPCHK', 'client_type': 'CLIENT_SIP2', 'user_id': '21221900064153', 'user_last_activity': '2023-04-11', 'user_edit_override': 'Y'}]
>>> os.unlink(testFile)


Test selection of specific minute in log
----------------------------------------
>>> hist.toJson('test/test01.hist', start='202304120002', end='202304130003')
[
  {
    "timestamp": "2023-04-12 00:00:02",
    "command_code": "Edit User Part B",
    "station_library": "MNA",
    "station_login_user_access": "SIPCHK",
    "station_login_clearance": "NONE",
    "station": "SIPCHK",
    "client_type": "CLIENT_SIP2",
    "user_id": "21221021970238",
    "user_last_activity": "2023-04-11",
    "user_edit_override": "Y"
  },
  {
    "timestamp": "2023-04-12 00:00:02",
    "command_code": "Edit User Part B",
    "station_library": "MNA",
    "station_login_user_access": "SIPCHK",
    "station_login_clearance": "NONE",
    "station": "SIPCHK",
    "client_type": "CLIENT_SIP2",
    "user_id": "21221900064153",
    "user_last_activity": "2023-04-11",
    "user_edit_override": "Y"
  }
]

Test just end time specified
----------------------------
>>> hist.toJson('test/test01.hist', end='20230411')
[
  {
    "timestamp": "2023-04-10 00:00:10",
    "command_code": "Edit User Part B",
    "station_library": "MNA",
    "station_login_user_access": "SIPCHK",
    "station_login_clearance": "NONE",
    "station": "SIPCHK",
    "client_type": "CLIENT_SIP2",
    "user_id": "21221030297904",
    "user_last_activity": "2023-03-23",
    "user_edit_override": "Y"
  },
  {
    "timestamp": "2023-04-10 00:00:10",
    "command_code": "Transit Item",
    "station_login_user_access": "CIRC",
    "station_library": "CAL",
    "station_login_clearance": "NONE",
    "client_type": "MOBLCIRC_S",
    "catalog_key_number": "2371230",
    "call_sequence_code": "55",
    "copy_number": "1",
    "hold_number": "41224719",
    "transit_to": "RIV",
    "transit_reason": "HOLD",
    "data_code_nr": "Y",
    "max_length_of_transaction_response": "2147483647"
  }
]

>>> hist.toJson('test/test01.hist', start='20230414')
[
  {
    "timestamp": "2023-04-14 00:03:59",
    "command_code": "Edit User Part B",
    "station_library": "MNA",
    "station_login_user_access": "SIPCHK",
    "station_login_clearance": "NONE",
    "station": "SIPCHK",
    "client_type": "CLIENT_SIP2",
    "user_id": "21221015619395",
    "user_last_activity": "2023-03-23",
    "user_edit_override": "Y"
  }
]
>>> hist.toJson('test/test01.hist', outFile='test/test01.hist.json')

Test the inDateRange()
----------------------
>>> data = 'E202304122237183071R ^S01JYFFADMIN^FbADMIN^FEEPLMNA^UO21221900070767'.split('^')
>>> hist.inDateRange(data, '20230412', '20230413')
True

>>> data = 'E202304122237183071R ^S01JYFFADMIN^FbADMIN^FEEPLMNA^UO21221900070767'.split('^')
>>> hist.inDateRange(data, '20230411', '20230413')
True
>>> data = 'E202304140003592977R ^S01JYFFADMIN^FbADMIN^FEEPLMNA^UO21221900070767'.split('^')
>>> hist.inDateRange(data, start='20230414', end='1234')
True

>>> data = 'E202304140003592977R ^S01JYFFADMIN^FbADMIN^FEEPLMNA^UO21221900070767'.split('^')
>>> hist.inDateRange(data, start='20230414')
True

>>> data = 'E202304140003592977R ^S01JYFFADMIN^FbADMIN^FEEPLMNA^UO21221900070767'.split('^')
>>> hist.inDateRange(data, end='20230413')
False

>>> data = 'E202304140003592977R ^S01JYFFADMIN^FbADMIN^FEEPLMNA^UO21221900070767'.split('^')
>>> hist.inDateRange(data, end='20230415')
True

>>> data = 'E202304140003592977R ^S01JYFFADMIN^FbADMIN^FEEPLMNA^UO21221900070767'.split('^')
>>> hist.inDateRange(data)
True

>>> data = 'E202304140003592977R ^S01JYFFADMIN^FbADMIN^FEEPLMNA^UO21221900070767'.split('^')
>>> hist.inDateRange(data, start='AndrewAndrew')
True