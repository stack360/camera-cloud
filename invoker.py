import rpyc
import simplejson as json

from config import *

class Invoker(object):
    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.conn = rpyc.connect(RPYC_SERVER, RPYC_PORT)
        self.result_dict = {}


class AlgorithmInvoker(Invoker):
    def invoke_current_algorithms(self, action_dict, streaming_url):
        for algorithm, action_item in action_dict.items():
            func_async = rpyc.async_(self.conn.root.run_algorithm)
            json_str = json.dumps(
                {
                    'streaming_url': streaming_url,
                    'camera_id': str(self.camera_id),
                    'result_api': CAMERA_API + str(self.camera_id) + '/result'
                }
            )
            self.result_dict[algorithm] = func_async(
                algorithm,
                json_str
            )
        return self.result_dict

    def reactivate_algorithms(self, algorithms):
        for algorithm in algorithms:
            self.conn.root.stop_and_delete_instance(algorithm)
        return


class ActionInvoker(Invoker):
    def invoke_action(self, params, action):
        params['camera_id'] = self.camera_id
        json_str = json.dumps(params)
        self.result_dict[action] = self.conn.root.run_action(action, json_str)
        return self.result_dict
