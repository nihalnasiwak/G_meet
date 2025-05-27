from channels.generic.websocket import AsyncWebsocketConsumer
import json

class CallNotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if user.is_authenticated:
            self.group_name = f'call_{user.id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def call_ring(self, event):
        await self.send(text_data=json.dumps({
            'type': 'call_ring',
            'message': event['message'],
            'meet_link': event['meet_link'],
            'sender_id': event['sender_id'],
            'receiver_id': event['receiver_id'],
        }))

    async def call_initiated(self, event):
        await self.send(text_data=json.dumps({
            'type': 'call_initiated',
            'sender_id': event['sender_id'],
            
            'meet_link': event['meet_link'],
            'is_group': event['is_group']
        }))


class CallStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = f'call_status_{self.scope["user"].id}'
        print(f"[✅] Receiver connected to {self.group_name}")
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        print(f"[WS CONNECTED] call_status_{self.scope['user'].id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        print("[WS RECEIVE] data:", data)
        msg_type = data.get('type')
        sender_id = data.get('sender_id')
        recipient_id = data.get('recipient_id')
        meet_link = data.get('meet_link')

        if msg_type == 'call_accepted':
            sender_id = data['sender_id']
            recipient_id = data['recipient_id']
            meet_link = data.get('meet_link')

            # Send to the sender (who is watching this group)
            await self.channel_layer.group_send(
                f'call_status_{sender_id}',  # ✅ this is the **sender's** group!
                {
                    'type': 'call_accepted',
                    'sender_id': sender_id,
                    'recipient_id': recipient_id,
                    'meet_link': meet_link,
                }
            )
        
        elif msg_type == 'call_ignored':
            await self.channel_layer.group_send(
                f'call_status_{sender_id}',
                {
                    'type': 'call_ignored',
                    'sender_id': sender_id,
                    'recipient_id': recipient_id,
                }
            )

        elif msg_type == 'call_timeout':
            await self.channel_layer.group_send(
                f'call_status_{sender_id}',
                {
                    'type': 'call_timeout',
                    'sender_id': sender_id,
                    'recipient_id': recipient_id,
                }
            )

        elif msg_type == 'call_cancelled':
            print("[WS CALL CANCELLED] sender_id:", sender_id)
            print("📥 Received call_cancelled from:", data['sender_id'])
            print("📤 Broadcasting to group: call_status_", data['recipient_id'])
            await self.channel_layer.group_send(
                f'call_status_{data["recipient_id"]}',
                {
                    'type': 'call_cancelled',
                    'sender_id': sender_id,
                    'recipient_id': recipient_id,
                }
            )

    async def call_accepted(self, event):
        print("[WS CALL ACCEPTED] event:", event)
        await self.send(text_data=json.dumps({
            'type': 'call_accepted',
            'sender_id': event['sender_id'],
            'recipient_id': event['recipient_id'],
            'meet_link': event['meet_link'],
        }))

    async def call_ignored(self, event):
        print("[📡 CALL IGNORED]", event)
        await self.send(text_data=json.dumps({
            'type': 'call_ignored',
            'sender_id': event['sender_id'],
            'recipient_id': event['recipient_id'],
        }))

    async def call_timeout(self, event):
        print("[📡 CALL TIMEOUT]", event)
        await self.send(text_data=json.dumps({
            'type': 'call_timeout',
            'sender_id': event['sender_id'],
            'recipient_id': event['recipient_id'],
        }))
    
    async def call_cancelled(self, event):
       
        print("📡 Sending call_cancelled to browser socket for:", event["recipient_id"])
        await self.send(text_data=json.dumps({
            'type': 'call_cancelled',
            'sender_id': event['sender_id'],
            'recipient_id': event['recipient_id'],
        }))