import json

from channels.generic.websocket import AsyncWebsocketConsumer


class ProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'progress'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def progress_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))

    async def new_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({'new_message': message}))
