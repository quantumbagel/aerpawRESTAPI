import json
import random
import time

import falcon
import pymongo
import ruamel.yaml

type_specification = {  # (type, required, must_be_unique)
    "start_time": [int, True, False],
    "end_by": [int, False, False],
    "id": [str, True, True],
    "long_name": [str, False, False],
    "description": [str, False, False],
    "websocket_ip": [str, True, True],
    "websocket_credentials": [list, True, False]
}
sensitive_param = ['auth_hash']
allowed_addresses = ["127.0.0.1"]
y = ruamel.yaml.YAML()
config = y.load(open('config.yaml'))
experiment_file = config['experiment_file']
with open(experiment_file) as exp:
    experiments_info = json.load(exp)
unique = [i for i in type_specification.keys() if type_specification[i][2]]
api = falcon.App()
auto_end = config['auto_kill_experiments']  # two hours in seconds
if config['mongodb']['use']:
    print("[server] connecting to mongodb server...")
    mongo_server = pymongo.MongoClient(config['mongodb']['connection_string'])
    print('[server] done connecting')
else:
    print("[server] mongodb disabled, continuing")
    mongo_server = None
db = mongo_server.get_database(config['mongodb']['database'])


def check_for_value(name, value):
    """
    Check if any experiment has the value 'value' for key 'name'
    :param name: The key
    :param value: The value
    :return: True or False, and the experiment that contains the data
    """
    for experiment in range(len(experiments_info['experiments'])):
        if experiments_info['experiments'][experiment][name] == value:
            return True, experiments_info['experiments'][experiment]['id'], experiment
    return False, None, None


def update_experiments():
    with open(experiment_file, 'w') as exp:
        json.dump(experiments_info, exp)

class ExperimentInfo(object):
    """
    ExperimentInfo: The API wrapper for get/post/putting experiments
    """

    def check_for_late(self):
        for i, experiment in enumerate(experiments_info['experiments']):
            if time.time() - experiment['last_updated'] > auto_end:
                experiments_info['experiments'].pop(i)
                update_experiments()

    def on_post(self, req: falcon.Request, resp: falcon.Response):
        self.check_for_late()
        data = req.media  # get json from request because this can only be done once.
        if data == {'teapot': True}:  # teapot check
            resp.status = falcon.HTTP_418  # teapot code
            resp.text = json.dumps({"success": True, "teapot": False})  # we aren't a teapot :/
            return
        if req.remote_addr not in allowed_addresses:  # if we haven't whitelisted this ip
            resp.status = falcon.HTTP_403  # throw da 403
            resp.text = json.dumps(
                {"success": False, "error": f"Your IP has not been whitelisted! ip: {req.remote_addr}"})
            return
        resp.status = falcon.HTTP_201
        failed = []
        add_dict = {}
        for item in type_specification.keys():
            if type_specification[item][1] and item not in data.keys():  # We don't have required data
                failed.append(item + " is required")
                continue
            if item in data.keys() and type(data[item]) != type_specification[item][0]:  # incorrect type for a piece
                # of data
                failed.append(
                    item + f' is the wrong type. Expected {type_specification[item][0]} got {type(data[item])}')
                continue
            if item not in data.keys() and not type_specification[item][1]:  # We don't have a non-required data
                # point, fill with None
                add_dict.update({item: None})
                continue
            add_dict.update({item: data[item]})  # If we made it here, we're fine
        if len(failed):  # we have failed criterion, tell the user and return a 400
            resp.text = json.dumps({"success": False, "error": ", ".join(failed)})
            resp.status = falcon.HTTP_400
            return
        for potential_match in unique:  # the unique identification
            c = check_for_value(potential_match, data[potential_match])  # if we are already storing this data, fail
            if c[0]:
                resp.status = falcon.HTTP_400
                resp.text = json.dumps({"success": False, "error": f"experiment with"
                                                                   f" {potential_match} {data[potential_match]}"
                                                                   f" already exists!"})
                return
        rand_hash = random.getrandbits(128)
        add_dict.update({"auth_hash": rand_hash, "last_updated": time.time()})
        experiments_info['experiments'].append(add_dict)
        update_experiments()
        resp.text = json.dumps({"success": True, "auth_hash": rand_hash})
        print('[server] added experiment', add_dict['id'], 'from', req.remote_addr)

    def on_get(self, req, resp):  # simple get, just return the experiment info
        self.check_for_late()
        if req.remote_addr not in allowed_addresses:
            resp.status = falcon.HTTP_403
            resp.text = json.dumps({"success": False, "error": "invalid_ip"})
            return
        resp.status = falcon.HTTP_201
        send_experiments = [{j: i[j] for j in i.keys() if j not in sensitive_param}
                            for i in experiments_info['experiments']]
        resp.text = json.dumps(send_experiments)
        print('[server] sent experiments to', req.remote_addr)

    def on_put(self, req, resp):
        self.check_for_late()
        data = req.media
        resp.status = falcon.HTTP_201
        if 'auth_hash' not in data.keys():
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"success": False,
                                    "error": "You must supply the auth_hash to update the experiment!"})
            return
        c = check_for_value('id', data['id'])
        if not c[0]:
            resp.status = falcon.HTTP_400
            resp.text = json.dumps({"success": False,
                                    "error": "You are referencing a experiment with a non-existent id!"})
            return
        elif data['auth_hash'] != experiments_info['experiments'][c[2]]['auth_hash']:
            resp.status = falcon.HTTP_403
            resp.text = json.dumps(
                {"success": False, "error": "You are using an invalid hash for this experiment!"})
            return
        update_dict = experiments_info['experiments'][c[2]]
        failed = []
        for item in data.keys():
            if item in ['auth_hash', 'last_updated']:
                continue
            if item in type_specification.keys() and type(data[item]) == type_specification[item][0]:
                update_dict[item] = data[item]
                continue
            if type(data[item]) != type_specification[item][0]:
                failed.append(
                        item + f' is the wrong type. Expected {type_specification[item][0]} got {type(data[item])}')
        if len(failed):
            resp.status = falcon.HTTP_401
            resp.text = json.dumps({"success": False, "error": ", ".join(failed)})
            return

        rand_hash = random.getrandbits(128)
        update_dict.update({"auth_hash": rand_hash, "last_updated": time.time()})
        experiments_info['experiments'][c[2]] = update_dict
        resp.text = json.dumps({"success": True, "auth_hash": rand_hash})
        print('[server] updated experiment', update_dict['id'], 'from', req.remote_addr)


set_experiment_endpoint = ExperimentInfo()
api.add_route('/experiments', set_experiment_endpoint)
