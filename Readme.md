# History to JSON

The purpose of `hist2json` is to convert SirsiDynix's Symphony history log files into `JSON` for analysis, diagnostics, or forensic analysis tools. The Edmonton Public Library uses it to add logging data to their data warehouse, while the systems administrators load the data into a no-sql database for foresic and diagnostic reports.

The Symphony ILS records transactions in log files that can be found in the `Unicorn/Hist` directory. The files are compressed at the end of the month to save space. The current month's logs are found in two different files, the month up to yesterday midnight in one, and a daily log of today's events in the other. Neither are compressed. At the end of the day, today's log is concatinated onto the month-to-date log file and a new daily log is started.

### How it Works

This script takes the path of a log file, compressed or otherwise, and converts it into one of two types of JSON. The first type is true JSON that would pass inspection of any JSON LINTer. The second writes each record as a separate dictionary for loading into `MongoDB` (see '`-m`' flag for more information).

A set of typical history transactions looks like this.

```
E202301180000153066R ^S05IYFWOVERDRIVE^FEEPLMNA^FFSIPCHK^FcNONE^FDSIPCHK^dC6^UO21221025878486^UK1/18/2023^OAY^^O
E202301180000233066R ^S05IYFWOVERDRIVE^FEEPLMNA^FFSIPCHK^FcNONE^FDSIPCHK^dC6^UO21221028747001^UK1/18/2023^OAY^^O
E202301180001403066R ^S01JZFFBIBLIOCOMM^FcNONE^FEEPLWHP^UO21221027661047^Uf[some user password]^NQ31221108836540^HB01/18/2024^HKTITLE^HOEPLLHL^dC5^^O00121
```

The fields are separated by the caret character '^'. The first field is the timestamp of the event. The next field describes type of logged event, like 'Find Hold Part B'. The remaining fields are data codes that describe relivant details of the event, like the device and branch where the event occured.


These transactions are translated like so.
```json
[
  {
    "timestamp": "2023-01-18 00:00:15",
    "command_code": "Edit User Part B",
    "station_library": "MNA",
    "station_login_user_access": "SIPCHK",
    "station_login_clearance": "NONE",
    "station": "SIPCHK",
    "client_type": "CLIENT_SIP2",
    "user_id": "21221025878486",
    "user_last_activity": "2023-01-18",
    "user_edit_override": "Y"
  },
  {
    "timestamp": "2023-01-18 00:00:23",
    "command_code": "Edit User Part B",
    "station_library": "MNA",
    "station_login_user_access": "SIPCHK",
    "station_login_clearance": "NONE",
    "station": "SIPCHK",
    "client_type": "CLIENT_SIP2",
    "user_id": "21221028747001",
    "user_last_activity": "2023-01-18",
    "user_edit_override": "Y"
  },
  {
    "timestamp": "2023-01-18 00:01:40",
    "command_code": "Create Hold",
    "station_login_clearance": "NONE",
    "station_library": "WHP",
    "user_id": "21221027661047",
    "user_pin": "xxxxx",
    "item_id": "31221108836540",
    "date_hold_expires": "2024-01-18",
    "hold_type": "TITLE",
    "hold_pickup_library": "LHL",
    "client_type": "CLIENT_ONLINE_CATALOG"
  }
]
```

Note that timestamps are converted from ANSI (yyyymmddhhmmss) to SQL timestamps where possible and 'yyyy-mm-dd' format otherwise.

Edmonton's branches all start with 'EPL' and that is removed to save space and improve readability. 

Client types are converted from integers to human-readable form.

Passwords are redacted.

When a data code is not defined in the `datacodes` file, a warning is issued and the entry `"data_code_[code]": "[value]"` is added to the JSON record.

## Configuration

The script is stand-alone application that uses standard Python libraries found in Python 3.7.4 and above. It may work in lower versions as well but is not tested.

## Installation

Drop the `hist2json.py` file into a directory and call it as you would any other python file. For example:
```bash
python hist2python [options]
```
For options [see below](#operation_instructions).

## Operating instructions


`-c`, `--hold_client="/foo/clients.txt"`: Path to hold client table (JSON) file.
    If the script is running on the ILS this switch is optional.  
`-C`, `--CmdCodes="/foo/cmdcodes"`: Path of the command code definitions.  
    If the script is running on the ILS this switch is optional.  
`-D`, `--DataCodes="/foo/datacodes"`: Path of the data code definitions.  
    If the script is running on the ILS this switch is optional.  
`-H`, `--HistFile="/foo/bar/[date].hist.Z"`: REQUIRED. Path of the history log file to convert.  
`-h`: Prints this help message.  
`-m`: Output as MongoDB JSON (each record as a separate object).  
`-v`: Turns on verbose messaging which reports data code errors. If a data code cannot be identified, an entry of `'data_code_[unknown data code]':'[data code value]'` is output to file and the record entry, line number, and data code are written to stdout.  


## Copyright and licensing

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Contact information

Developed by Andrew Nisbet at Dev-ILS (andrew(at)dev-ils.com).

## Known Bugs

* Not all data codes recorded to history logs have documentation, so a work around was made to record the data code as is with `'data_code_'` prefix and the recorded value.

## Troubleshooting

Turning on the `'-v'` flag will display information about unidentified data codes and other errors encountered while processing a history log.

```
* warning on line 40062:
*   ['E202301181231142905R ', 'S05EVFWRIVCIRC', 'FFCIRC', 'FEEPLRIV', 'FcNONE', 'dC19', 'NQ31221118489124', 'POY', 'rsY', 'YPN', 'jz1', 'C0Y', 'Fv2147483647', '', 'O']
*   'C0' is an unrecognized data code and will be recorded as 'data_code_C0': 'Y'.
Total cmd codes read:    533
Total data codes read:   2086
Total history records:   40083
Unidentified data codes: 45, (any missing codes have been recorded as 'data_code_[data code value]':'[read value]')
```

## Credits and Acknowledgments

The author would like to thank the Edmonton Public Library and its staff for their generous support and contributions to communities and public libraries around the world.

## Changelog

Version 1.02.00 - initial release.

## What's New

### Version 1.02.00
* Support for MongoDB JSON record ingestion requirements.
* Support for converting hold client types.
* Redacted customer passwords.
* Five different date and time reporting styles found in Symphony logs are supported.