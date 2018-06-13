import os


celeryconfig_filename = 'celery_config'
CELERYCONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    celeryconfig_filename)

try:
    exec(open(CELERYCONFIG_FILE).read(), globals(), locals())
except Exception as error:
    raise error
