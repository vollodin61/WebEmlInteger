import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


class ProgressBarConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        async_to_sync(self.channel_layer.group_add)(
            "progress_group",
            self.channel_name
        )

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            "progress_group",
            self.channel_name
        )

    def send_progress(self, event):
        progress = event['progress']
        self.send(text_data=json.dumps({
            'progress': progress
        }))

    def send_message(self, event):
        message = event['message']
        self.send(text_data=json.dumps({
            'message': message
        }))
