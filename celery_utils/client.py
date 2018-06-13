import os
import sys
app_dir = os.path.dirname(os.path.realpath(__file__ + "/../../"))
sys.path.append(app_dir)

from celery import Celery
from . import celeryconfig

celery = Celery(__name__)
celery.config_from_object(celeryconfig)
