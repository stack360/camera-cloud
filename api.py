import functools
import simplejson as json
import ast
import exception_handler
import mongoengine
import re
import time

from datetime import datetime

from flask import Blueprint, Flask, redirect, url_for, session, jsonify, current_app, make_response, render_template, request, session, abort

from flask_principal import Identity, AnonymousIdentity, identity_changed

from models import models
from camera_notifier.notifier import CameraNotifier
from invoker import ActionInvoker, AlgorithmInvoker
import utils
# import exception_handler
import random
import werkzeug
from werkzeug.exceptions import BadRequest, NotFound, Conflict
from config import *
import requests
from bson import ObjectId
import urllib, hashlib

api = Blueprint('api', __name__, template_folder='templates')
CREATE_CAMERA_FIELDS = ['actions', 'name']
UPDATE_CAMERA_FIELDS = ['actions', 'name', 'description']
CREATE_ALGORITHM_FIELDS = ['name', 'options', 'description']
UPDATE_ALGORITHM_FIELDS = ['name', 'options', 'description']
CREATE_ACTION_FIELDS = ['name', 'params', 'description']
UPDATE_ACTION_FIELDS = ['name', 'params', 'description']

def _build_error(error_code, message):
    return {"status_code": error_code, "data": message}

def _get_request_args(**kwargs):
    args = dict(request.args)
    for key, value in args.items():
        if key in kwargs:
            converter = kwargs[key]
            if isinstance(value, list):
                args[key] = [converter(item) for item in value]
            else:
                args[key] = converter(value)
    return args

def _validate_camera_actions(actions):
    if actions == {}:
        return {}, None

    all_algorithm_objs = models.Algorithm.objects.all()
    all_action_objs = models.Action.objects.all()
    all_algorithms = [a.name for a in all_algorithm_objs]
    all_actions = [a.name for a in all_action_objs]
    all_options = ['else']
    for algo_obj in all_algorithm_objs:
        all_options.extend(algo_obj.options)

    invalid_algos = list(
        filter(lambda x: not(x in all_algorithms), actions.keys())
    )
    if invalid_algos:
        return None, "Algorithms not found: " + ", ".join(invalid_algos)

    invalid_options = list(
        filter(lambda x: not(set(x.keys())<=set(all_options)), actions.values())
    )
    if invalid_options:
        return None, "These options are invalid: " + str(invalid_options)

    invalid_actions = []
    invalid_keys = []
    invalid_params = []
    missing_params = []
    for _, v in actions.items():
        for _, a in v.items():
            for f in a:
                invalid_keys.extend(
                    list(set(f.keys()) - set(['action', 'params']))
                )
                if f['action'] not in all_actions:
                    invalid_actions.append(f['action'])
                    continue
                else:
                    this_action_params = list(
                        filter(
                            lambda x: x.name==f['action'], all_action_objs
                        )
                    )[0].params
                    required_action_params = {
                        k:v for k, v in this_action_params.items() if
                            v['required']=='true'
                    }
                    try:
                        invalid_params.extend(
                            list(set(f['params']) - set(this_action_params))
                        )
                        missing_params.extend(
                            list(set(required_action_params) - set(f['params']))
                        )
                    except:
                        pass

    action_error_message = ""
    if invalid_actions:
        action_error_message += "These actions are not available: " \
            + ", ".join(invalid_actions) + ";"
    if invalid_keys:
        action_error_message += "\nInvalid keys: " + ", ".join(invalid_keys) \
            + ". Only [action, params] are allowed;\n"
    if invalid_params:
        action_error_message += "\nInvalid action params: " \
            + ", ".join(invalid_params) + ". Please check the actions;"
    if missing_params:
        action_error_message += "\nThese required action params are missing: " \
            + ", ".join(missing_params) + ";"
    if action_error_message:
        return None, action_error_message
    for algorithm_name in actions.keys():
        if 'else' not in actions[algorithm_name].keys():
            actions[algorithm_name]['else'] = []
    return actions, None

def _validate_action_params(params):
    if params == {}:
        return
    invalid_params = list(filter(
        lambda x: set(x.keys()) != set(['type', 'required']), params.values()
    ))
    if invalid_params:
        return "Invalid parameters: " + str(invalid_params)
    return

def _get_camera_by_id(camera_id):
    try:
        camera = models.Camera.objects.get(id=camera_id)
    except mongoengine.errors.ValidationError as e:
        return None, _build_error(400, e.__str__())
    except models.Camera.DoesNotExist as e:
        return None, _build_error(404, e.__str__())
    return camera, None

def _get_algorithm_by_id(algorithm_id):
    try:
        algorithm = models.Algorithm.objects.get(id=algorithm_id)
    except mongoengine.errors.ValidationError as e:
        return None, _build_error(400, e.__str__())
    except models.Algorithm.DoesNotExist as e:
        return None, _build_error(400, e.__str__())
    return algorithm, None

def _get_action_by_id(action_id):
    try:
        action = models.Action.objects.get(id=action_id)
    except mongoengine.errors.ValidationError as e:
        return None, _build_error(400, e.__str__())
    except models.Algorithm.DoesNotExist as e:
        return None, _build_error(400, e.__str__())
    return action, None

@api.route('/api/cameras', methods=['GET'])
def list_cameras():
    cameras = models.Camera.objects.order_by('-last_updated')
    cameras = [c.to_dict() for c in cameras]
    return utils.make_json_response(
        200,
        cameras
        )

@api.route('/api/cameras', methods=['POST'])
def register_camera():
    data = utils.get_request_data()

    camera = models.Camera()
    camera.name = data['name']
    actions, errors = _validate_camera_actions(data['actions'])
    if not errors:
        camera.action_dict = actions
    else:
        return utils.make_json_response(
            400,
            errors
        )
    camera.streaming_url = RTMP_SERVER + '/' + data['name']
    camera.last_updated = datetime.datetime.now()
    camera.save()
    notifier = CameraNotifier(camera.id, camera.streaming_url)
    notifier.notify_agent_start()
    return utils.make_json_response(
        200,
        camera.to_dict()
    )

@api.route('/api/cameras/<string:camera_id>', methods=['GET'])
def get_camera(camera_id):
    camera, error = _get_camera_by_id(camera_id)
    if error:
        return utils.make_json_response(**error)
    return utils.make_json_response(
        200,
        camera.to_dict()
    )

@api.route('/api/cameras/<string:camera_id>', methods=['PUT'])
def update_camera(camera_id):
    data = utils.get_request_data()
    if not (set(data.keys()) <= set(UPDATE_CAMERA_FIELDS)):
        return utils.make_json_response(
            400,
            "Invalid parameter keys: %s" %
                str(set(data.keys()) - set(UPDATE_CAMERA_FIELDS))
        )
    camera, error = _get_camera_by_id(camera_id)
    if error:
        return utils.make_json_response(**error)
    if 'name' in data.keys():
        url = camera.streaming_url
        camera.streaming_url = url.replace(url.split('/')[-1], data['name'])
    if 'actions' in data.keys():
        actions, errors = _validate_camera_actions(data['actions'])
        if errors:
            return utils.make_json_response(
                400,
                errors
            )
        data['action_dict'] = actions
        data.pop('actions', None)
    for k, v in data.items():
        setattr(camera, k, v)
    camera.save()
    camera.last_updated = datetime.datetime.now()
    return utils.make_json_response(
        200,
        camera.to_dict()
    )

@api.route('/api/cameras/<string:camera_id>', methods=['DELETE'])
def unregister_camera(camera_id):
    camera, error = _get_camera_by_id(camera_id)
    if error:
        return utils.make_json_response(**error)
    camera_name = camera.name
    camera.delete()
    return utils.make_json_response(
        200,
        {
            "name": camera_name,
            "status": "deleted"
        }
    )

@api.route('/api/cameras/<string:camera_id>/trigger', methods=['POST'])
def trigger_camera_algorithm(camera_id):
    camera, error = _get_camera_by_id(camera_id)
    if error:
        return utils.make_json_response(**error)
    algorithm_status = camera.algorithm_status
    action_dict = camera.action_dict
    if action_dict == {}:
        return utils.make_json_response(
            200,
            {
                'status': 'No algorithm specified.'
            }
        )
    available_action_dict = {
        k:v for k, v in action_dict.items() if algorithm_status[k] == 'idle'
    }
    algorithm_invoker = AlgorithmInvoker(
        camera_id
    )
    algorithm_invoker.invoke_current_algorithms(
            available_action_dict,
            camera.streaming_url
    )
    for algorithm_name in available_action_dict.keys():
        algorithm_status[algorithm_name] = 'running'
    camera.algorithm_status = algorithm_status
    camera.save()
    return utils.make_json_response(
        200,
        {
            'status': 'triggered'
        }
    )

@api.route('/api/cameras/<string:camera_id>/agent_start', methods=['POST'])
def trigger_agent_start(camera_id):
    camera, error = _get_camera_by_id(camera_id)
    if error:
        utils.make_json_response(**error)
    notifier = CameraNotifier(camera.id, camera.streaming_url)
    notifier.notify_agent_start()
    return utils.make_json_response(
        200,
        {'status': 'Agent start message sent.'}
    )

@api.route('/api/cameras/<string:camera_id>/result', methods=['POST'])
def update_algorithm_result(camera_id):
    camera, error = _get_camera_by_id(camera_id)
    if error:
        return utils.make_json_response(**error)
    data = utils.get_request_data()
    for algorithm, result in data.items():
        camera.algorithm_status[algorithm] = 'idle'
        try:
            action_list = camera.action_dict[algorithm][result]
        except KeyError:
            action_list = camera.action_dict[algorithm]['else']
        for action in action_list:
            if not action:
                pass
            action_invoker = ActionInvoker(
                camera_id
            )
            action_invoker.invoke_action(
                action['params'],
                action['action']
            )

        # Algorithms cooldown time: 15 seconds.
        time.sleep(15)
        algorithm_invoker = AlgorithmInvoker(camera_id)
        algorithm_invoker.reactivate_algorithms([algorithm])
    camera.save()
    return utils.make_json_response(
        200,
        {
            "status": "complete"
        }
    )


@api.route('/api/algorithms', methods=['GET'])
def list_algorithms():
    algorithms = models.Algorithm.objects.all()
    algorithms = [a.to_dict() for a in algorithms]
    return utils.make_json_response(
        200,
        algorithms
    )

@api.route('/api/algorithms', methods=['POST'])
def create_algorithm():
    data = utils.get_request_data()
    if not (set(data.keys()) <= set(CREATE_ALGORITHM_FIELDS)):
        return utils.make_json_response(
            400,
            "Invalid parameter keys: %s" %
                str(set(data.keys()) - set(CREATE_ALGORITHM_FIELDS))
        )
    algorithm = models.Algorithm()
    for k, v in data.items():
        setattr(algorithm, k, v)
    try:
        algorithm.save()
    except mongoengine.errors.NotUniqueError as e:
        return utils.make_json_response(
            409,
            e.__str__()
        )
    return utils.make_json_response(
        200,
        algorithm.to_dict()
    )

@api.route('/api/algorithms/<string:algorithm_id>', methods=['GET'])
def get_algorithm(algorithm_id):
    algorithm, error = _get_algorithm_by_id(algorithm_id)
    if error:
        return utils.make_json_response(**error)
    return utils.make_json_response(
        200,
        algorithm.to_dict()
    )

@api.route('/api/algorithms/<string:algorithm_id>', methods=['PUT'])
def update_algorithm(algorithm_id):
    data = utils.get_request_data()

    if not (set(data.keys()) <= set(UPDATE_ALGORITHM_FIELDS)):
        return utils.make_json_response(
            400,
            "Invalid parameter keys: %s" %
                str(set(data.keys()) - set(UPDATE_ALGORITHM_FIELDS))
        )
    algorithm, error = _get_algorithm_by_id(algorithm_id)
    if error:
        return utils.make_json_response(**error)
    for k, v in data.items():
        setattr(algorithm, k, v)
    algorithm.save()
    return utils.make_json_response(
        200,
        algorithm.to_dict()
    )

@api.route('/api/algorithms/<string:algorithm_id>', methods=['DELETE'])
def delete_algorithm(algorithm_id):
    algorithm, error = _get_algorithm_by_id(algorithm_id)
    if error:
        return utils.make_json_response(**error)
    algorithm_name = algorithm.name
    algorithm.delete()
    return utils.make_json_response(
        200,
        {
            "name": algorithm_name,
            "status": "deleted"
        }
    )

@api.route('/api/actions', methods=['GET'])
def list_actions():
    actions = models.Action.objects.all()
    actions = [a.to_dict() for a in actions]
    return utils.make_json_response(
        200,
        actions
    )

@api.route('/api/actions', methods=['POST'])
def create_action():
    data = utils.get_request_data()
    if not (set(data.keys()) <= set(CREATE_ACTION_FIELDS)):
        return utils.make_json_response(
            400,
            "Invalid parameter keys: %s" %
                str(set(data.keys()) - set(CREATE_ACTION_FIELDS))
        )
    errors = _validate_action_params(data['params'])
    if errors:
        return utils.make_json_response(
            400,
            errors
        )
    action = models.Action()
    for k, v in data.items():
        setattr(action, k, v)
    try:
        action.save()
    except mongoengine.errors.NotUniqueError as e:
        return utils.make_json_response(
            409,
            e.__str__()
        )
    return utils.make_json_response(
        200,
        action.to_dict()
    )

@api.route('/api/actions/<string:action_id>', methods=['GET'])
def get_action(action_id):
    action, error = _get_action_by_id(action_id)
    if error:
        return utils.make_json_response(**error)
    return utils.make_json_response(
        200,
        action.to_dict()
    )

@api.route('/api/actions/<string:action_id>', methods=['PUT'])
def update_action(action_id):
    data = utils.get_request_data()

    if not (set(data.keys()) <= set(UPDATE_ACTION_FIELDS)):
        return utils.make_json_response(
            400,
            "Invalid parameter keys: %s" %
                str(set(data.keys()) - set(UPDATE_ACTION_FIELDS))
        )
    action, error = _get_action_by_id(action_id)
    if error:
        return utils.make_json_response(**error)
    for k, v in data.items():
        setattr(action, k, v)
    action.save()
    return utils.make_json_response(
        200,
        action.to_dict()
    )

@api.route('/api/actions/<string:action_id>', methods=['DELETE'])
def delete_action(action_id):
    action, error = _get_action_by_id(action_id)
    if error:
        return utils.make_json_response(**error)
    action_name = action.name
    action.delete()
    return utils.make_json_response(
        200,
        {
            "name": action_name,
            "status": "deleted"
        }
    )
