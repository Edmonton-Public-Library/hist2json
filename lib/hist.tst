Provides tests for hist.py


>>> from hist import Hist
>>> hist = Hist('test.hist', dataCodes={'A':'bee'}, commandCodes={'C':'dee'}, debug=True)
WARNING: item IDs will not be converted into item barcodes.
cmd_code_path :../test/cmdcode
data_code_path:../test/datacode
translate_cmd :../test/translate
hist_dir      :../test/Hist
encoding      :ISO-8859-1
cmd_codes len :1
data_codes len:1
barCode file  :None
bar_codes read:0
>>> hist.updateDataCodes({'B':'sea'})
>>> print(f"{hist.data_codes}")
{'A': 'bee', 'B': 'sea'}


>>> hist = Hist('test.hist', commandCodes={'A':'bee'}, debug=True)
WARNING: item IDs will not be converted into item barcodes.
cmd_code_path :../test/cmdcode
data_code_path:../test/datacode
translate_cmd :../test/translate
hist_dir      :../test/Hist
encoding      :ISO-8859-1
cmd_codes len :1
data_codes len:1881
barCode file  :None
bar_codes read:0

Test data codes read from file.
------------------------------

>>> hist = Hist('test.hist', dataCodes={'A':'bee'}, debug=True)
WARNING: item IDs will not be converted into item barcodes.
cmd_code_path :../test/cmdcode
data_code_path:../test/datacode
translate_cmd :../test/translate
hist_dir      :../test/Hist
encoding      :ISO-8859-1
cmd_codes len :533
data_codes len:1
barCode file  :None
bar_codes read:0

Test reading bar codes from a file 
----------------------------------

>>> hist = Hist('test.hist', barCodes='../test/items.lst', debug=True)
cmd_code_path :../test/cmdcode
data_code_path:../test/datacode
translate_cmd :../test/translate
hist_dir      :../test/Hist
encoding      :ISO-8859-1
cmd_codes len :533
data_codes len:1881
barCode file  :../test/items.lst
bar_codes read:1630964

>>> hist = Hist('test.hist', barCodes='../test/items1.lst', debug=True)
cmd_code_path :../test/cmdcode
data_code_path:../test/datacode
translate_cmd :../test/translate
hist_dir      :../test/Hist
encoding      :ISO-8859-1
cmd_codes len :533
data_codes len:1881
barCode file  :../test/items1.lst
bar_codes read:10


Test string cleaning.
---------------------

Cleans a standard set of special characters from a string. 
param: string to clean. 
param: spc_to_underscore as boolean, True will remove all special characters and replace any spaces with underscores.

>>> s = """This [isn't] a \$tring th*t i've (liked) until_now} """
>>> print(f"{hist.clean_string(s)}")
This isnt a tring tht ive liked untilnow 


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

Test translateCode()
--------------------
>>> hist.translateCode('EV', whichDict='commandcode')
'Discharge Item'
>>> hist.translateCode('NQ')
'item_id'
>>> hist.translateCode('6', whichDict='clientcode')
'CLIENT_SIP2'
>>> hist.translateCode('99', whichDict='clientcode')
'99'
>>> hist.translateCode('99', whichDict='clientcode', verbose=True)
'99'
>>> hist.translateCode('S61EVFWSMTCHTLHL1', whichDict='commandcode')
'Discharge Item'
>>> hist.translateCode('NQ31221120423970')
'item_id'
>>> hist.translateCode('NQ31221120423970', asValue=True)
'31221120423970'
>>> hist.translateCode('zZ12345678')
'zZ'

Test convertLogEntry()
----------------------
>>> data = "E202310100510083031R ^S01EVFFADMIN^FEEPLRIV^FcNONE^NQ31221112079020^^O00049".split('^')
>>> hist.convertLogEntry(data, 1)
(0, {'timestamp': '2023-10-10 05:10:08', 'command_code': 'Discharge Item', 'station_library': 'RIV', 'station_login_clearance': 'NONE', 'item_id': '31221112079020', 'date_of_discharge': '2023-10-10'})