import os

from flask import Flask

from flask_principal import Principal

from config import *

from api import api
from models.models import db


principals = Principal()



def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    config[config_name].init_app(app)

    db.init_app(app)
    principals.init_app(app)

    return app

app = create_app(os.getenv('config') or 'default')

app.register_blueprint(api)

if __name__ == '__main__':
    app.run(threaded=True)
