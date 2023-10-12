Provides tests for hist.py


>>> from hist import Hist
>>> hist = Hist('test.hist', commandCodes={'A':'bee'}, debug=True)
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


Test to_date() method
---------------------

>>> hist.to_date('01/13/2023')
'2023-01-13'
>>> hist.to_date('E202301180024483003R ')
'2023-01-18 00:24:48'
>>> hist.to_date('1/3/2023')
'2023-01-03'
>>> hist.to_date('20230118002448')
'2023-01-18 00:24:48'
>>> hist.to_date('01/13/2023,5:33 PM')
'2023-01-13'

