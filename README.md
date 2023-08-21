# aerpawRESTAPI
A simple REST API for tracking AERPAW's ongoing experiments. This repository will also update airstrik.py with code to interface with this API

## Experiment Data

|Name|Type|Description|Is Required|
|-|-|-|-|
|`start_time`|int|The epoch time (in seconds) when the experiment began or will begin.|Yes|
|`end_by`|int|The epoch time (in seconds) when the experiment will end.|No|
|`long_name`|str|The human-readable name of the experiment.|No|
|`id`|str|The id of the experiment. This must be unique.|Yes|
|`description`|str|The description of what the experiment will do|No|
|`websocket_ip`|str|The ip to connect to (over websocket)|Yes|
|`websocket_credentials`|list[str, str|The username/password to connect with using websocket|Yes|
|`last_updated`|int|The time when the data was last updated. This is updated by the server, and cannot be changed by PUT/POST requests.|NA|



## Endpoints

### GET /experiments

Returns the current experiments running in JSON format.


### POST /experiments

You must supply a dictionary of the data listed under Experiment Data (at least the required data).

Returns:

|Key|Description|
|-|-|
|`success`|Whether the POST request succeeded.|
|`error`|A description of the error (if `success` is `false`)|
|`auth_hash`|A 128-digit number which is required to update this experiment with PUT requests later on. (if `success` is `true`)|



### PUT /experiments

You need to supply the parameters to update (for example, if you only wanted to update the `description`, you could just pass the description in the JSON. Also required is the `auth_hash` key, with the hash received from the POST request or another PUT request.

Returns:
|Key|Description|
|-|-|
|`success`|Whether the POST request succeeded.|
|`error`|A description of the error (if `success` is `false`)|
|`auth_hash`|A updated 128-digit number that is required to update this experiment with PUT requests later on. (if `success` is `true`)|

### TODO's

* Make start_time actually cancel/delete experiments (this is currently only done when AUTO_END is exceeded)
* Add config file with options like the automatic deletion of experiments, authorized IP addresses, database information, and other things.
* MongoDB integration for historical plots of experiments running.
* Potentially a better hash than the current one of just 128 digits.
* The other two components, namely integration with https://github.com/quantumbagel/airstrik.py and integration with the experiments themselves.

More to come!
