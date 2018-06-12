#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, datetime


RTMP_SERVER = 'rtmp://13.57.222.238/live'

class Config(object):
    DEBUG = False
    TESTING = False

    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    MONGODB_SETTINGS = {'DB': 'camera_cloud',
                        'HOST': '127.0.0.1',
                        'PORT': 27017
        }

    @staticmethod
    def init_app(app):
        pass

class DevConfig(Config):
    DEBUG = True

class PrdConfig(Config):
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    MONGODB_SETTINGS = {
            'DB': os.environ.get('DB_NAME') or 'camera_cloud',
            'HOST': os.environ.get('MONGO_HOST') or '127.0.0.1',
            'PORT': 27017
        }

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    MONGODB_SETTINGS = {'DB': 'OctBlogTest'}
    WTF_CSRF_ENABLED = False

config = {
    'dev': DevConfig,
    'prd': PrdConfig,
    'testing': TestingConfig,
    'default': DevConfig,
}
