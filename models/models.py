from datetime import datetime
from flask_mongoengine import MongoEngine

db = MongoEngine()


class Camera(db.Document):
    name = db.StringField(max_length=255, required=True, unique=True)
    streaming_url = db.StringField(default='')
    action_dict = db.DictField()
    algorithm_status = db.DictField()
    last_updated = db.DateTimeField()

    def save(self, *args, **kwargs):
        self.last_updated = datetime.now()
        if self.action_dict:
            for algorithm_name in action_dict.keys():
                self.algorithm_status[algorithm_name] = 'idle'
        return super(Camera, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

    def to_dict(self):
        camera_dict = {}
        camera_dict['name'] = self.name
        camera_dict['streaming_url'] = self.streaming_url
        camera_dict['action_dict'] = self.action_dict
        camera_dict['id'] = str(self.id)
        return camera_dict


class Algorithm(db.Document):
    name = db.StringField(max_length=255, required=True, unique=True)
    description = db.StringField(default='')
    options = db.ListField(default=[])
    last_updated = db.DateTimeField()

    def save(self, *args, **kwargs):
        self.last_updated = datetime.now()
        return super(Algorithm, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

    def __desc__(self):
        return self.description

    def to_dict(self):
        algorithm_dict = {}
        algorithm_dict['name'] = self.name
        algorithm_dict['description'] = self.description
        algorithm_dict['options'] = self.options
        algorithm_dict['id'] = str(self.id)
        return algorithm_dict


class Action(db.Document):
    name = db.StringField(max_length=255, required=True, unique=True)
    description = db.StringField(defualt='')
    params = db.DictField(default={})
    last_updated = db.DateTimeField()

    def save(self, *args, **kwargs):
        self.last_updated = datetime.now()
        return super(Action, self).save(*args, **kwargs)

    def to_dict(self):
        action_dict = {}
        action_dict['name'] = self.name
        action_dict['description'] = self.description
        action_dict['params'] = self.params
        action_dict['id'] = str(self.id)
        return action_dict
