from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ProgressConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('progress', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('progress', self.channel_name)

    async def progress_update(self, event):
        await self.send_json(event['message'])
