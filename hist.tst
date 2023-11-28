Provides tests for hist.py


>>> from hist2json import Hist
>>> hist = Hist(debug=True)
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
>>> hist = Hist(barCodes='test/items.lst', debug=True)
encoding        :ISO-8859-1
cmd_codes len   :533
data_codes len  :1881
hold_clients len:23
bar_codes read  :1630964
>>> hist = Hist(barCodes='test/items1.lst', debug=True)
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


Test lookupCode()
--------------------
>>> hist.lookupCode('EV', whichDict='commandcode')
'Discharge Item'
>>> hist.lookupCode('NQ')
'item_id'
>>> hist.lookupCode('6', whichDict='clientcode')
'CLIENT_SIP2'
>>> hist.lookupCode('99', whichDict='clientcode')
'99'
>>> hist.lookupCode('99', whichDict='clientcode')
'99'
>>> hist.lookupCode('S61EVFWSMTCHTLHL1', whichDict='commandcode')
'Discharge Item'
>>> hist.lookupCode('NQ31221120423970')
'item_id'
>>> hist.lookupCode('NQ31221120423970', asValue=True)
'31221120423970'
>>> hist.lookupCode('zZ12345678')
'zZ'


Test readClientCodes method
---------------------------
>>> hist = Hist(barCodes='test/items1.lst', debug=True)
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

>>> hist = Hist(barCodes='test/items1.lst', debug=True)
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