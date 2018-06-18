import os, sys
app_dir = os.path.dirname(os.path.realpath(__file__ + "/../"))
sys.path.append(app_dir)

from celery_utils import client as celery_client

class CameraNotifier(object):
    def __init__(self, camera_id, streaming_url):
        self.camera_id = camera_id
        self.streaming_url = streaming_url

    def notify_agent_start(self):
        celery_client.celery.send_task(
            'notify_agent_start',
            (self.streaming_url, self.camera_id),
            queue=str(self.camera_id)
        )
        return "task sent."
