import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Empire, Alliance, Message, Territory, Building, Research
from django.utils import timezone


class GameConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time game updates"""
    
    async def connect(self):
        self.empire_id = self.scope['url_route']['kwargs']['empire_id']
        self.room_group_name = f'empire_{self.empire_id}'
        
        # Join empire group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Join global updates group
        await self.channel_layer.group_add(
            'global_updates',
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial game state
        await self.send_game_state()
    
    async def disconnect(self, close_code):
        # Leave groups
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.channel_layer.group_discard(
            'global_updates',
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'command':
            await self.handle_command(data.get('command', ''))
        elif message_type == 'get_map':
            await self.send_map_data(data.get('x', 0), data.get('y', 0))
        elif message_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
    
    async def handle_command(self, command):
        """Process game commands"""
        parts = command.strip().split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        
        try:
            if cmd == 'status':
                await self.send_game_state()
            elif cmd == 'map':
                x = int(parts[1]) if len(parts) > 1 else 25
                y = int(parts[2]) if len(parts) > 2 else 25
                await self.send_map_data(x, y)
            elif cmd == 'build':
                await self.handle_build_command(parts[1:])
            elif cmd == 'research':
                await self.handle_research_command(parts[1:])
            elif cmd == 'attack':
                await self.handle_attack_command(parts[1:])
            elif cmd == 'help':
                await self.send_help()
            else:
                await self.send_error(f"Unknown command: {cmd}")
        except Exception as e:
            await self.send_error(f"Error: {str(e)}")
    
    @database_sync_to_async
    def get_empire(self):
        """Get empire data"""
        try:
            return Empire.objects.get(id=self.empire_id)
        except Empire.DoesNotExist:
            return None
    
    async def send_game_state(self):
        """Send current empire state"""
        empire = await self.get_empire()
        if not empire:
            return
        
        # Get buildings and research
        buildings = await self.get_empire_buildings(empire)
        research = await self.get_empire_research(empire)
        territories = await self.get_empire_territories(empire)
        
        await self.send(text_data=json.dumps({
            'type': 'game_state',
            'empire': {
                'name': empire.name,
                'energy': empire.energy,
                'minerals': empire.minerals,
                'food': empire.food,
                'population': empire.population,
                'power_level': empire.power_level,
                'rank': empire.rank,
            },
            'buildings': buildings,
            'research': research,
            'territories': territories,
            'timestamp': timezone.now().isoformat()
        }))
    
    @database_sync_to_async
    def get_empire_buildings(self, empire):
        """Get empire buildings"""
        buildings = []
        for building in empire.buildings.all():
            buildings.append({
                'type': building.building_type,
                'level': building.level,
                'territory': f"({building.territory.x}, {building.territory.y})",
                'upgrading': bool(building.upgrade_started and building.upgrade_complete and 
                                 timezone.now() < building.upgrade_complete)
            })
        return buildings
    
    @database_sync_to_async
    def get_empire_research(self, empire):
        """Get empire research"""
        research = []
        for r in empire.research.all():
            research.append({
                'type': r.research_type,
                'level': r.level,
                'researching': bool(r.research_started and r.research_complete and 
                                   timezone.now() < r.research_complete)
            })
        return research
    
    @database_sync_to_async
    def get_empire_territories(self, empire):
        """Get empire territories"""
        return [(t.x, t.y) for t in empire.territories.all()]
    
    async def send_map_data(self, center_x, center_y):
        """Send map data around specified coordinates"""
        map_data = await self.get_map_data(center_x, center_y)
        await self.send(text_data=json.dumps({
            'type': 'map_data',
            'map': map_data,
            'center_x': center_x,
            'center_y': center_y
        }))
    
    @database_sync_to_async
    def get_map_data(self, center_x, center_y, radius=10):
        """Get map data for rendering"""
        from django.conf import settings
        
        map_grid = []
        for y in range(max(0, center_y - radius), min(settings.WORLD_SIZE, center_y + radius + 1)):
            row = []
            for x in range(max(0, center_x - radius), min(settings.WORLD_SIZE, center_x + radius + 1)):
                try:
                    territory = Territory.objects.get(x=x, y=y)
                    cell = {
                        'x': x,
                        'y': y,
                        'terrain': territory.terrain_type,
                        'symbol': territory.get_ascii_symbol(),
                        'owner': territory.owner.name if territory.owner else None,
                        'color': territory.owner.color if territory.owner else '#888888'
                    }
                except Territory.DoesNotExist:
                    cell = {
                        'x': x,
                        'y': y,
                        'terrain': 'unknown',
                        'symbol': '?',
                        'owner': None,
                        'color': '#888888'
                    }
                row.append(cell)
            map_grid.append(row)
        return map_grid
    
    async def send_help(self):
        """Send help information"""
        help_text = """
╔═══════════════════════════════════════════╗
║             NOVA TERRA COMMANDS           ║
╠═══════════════════════════════════════════╣
║ status          - Show empire status      ║
║ map [x] [y]     - Show world map          ║
║ build [type]    - Build structure         ║
║ research [type] - Start research          ║
║ attack [x] [y]  - Attack territory        ║
║ help            - Show this help          ║
╚═══════════════════════════════════════════╝
        """
        await self.send(text_data=json.dumps({
            'type': 'message',
            'content': help_text
        }))
    
    async def send_error(self, message):
        """Send error message"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    # Group message handlers
    async def game_update(self, event):
        """Handle game update events"""
        await self.send(text_data=json.dumps(event))
    
    async def resource_update(self, event):
        """Handle resource update events"""
        await self.send(text_data=json.dumps(event))
    
    async def battle_notification(self, event):
        """Handle battle notifications"""
        await self.send(text_data=json.dumps(event))


class GlobalChatConsumer(AsyncWebsocketConsumer):
    """Global chat consumer"""
    
    async def connect(self):
        self.room_group_name = 'global_chat'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        username = data['username']
        
        # Broadcast message to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))


class AllianceChatConsumer(AsyncWebsocketConsumer):
    """Alliance-specific chat consumer"""
    
    async def connect(self):
        self.alliance_id = self.scope['url_route']['kwargs']['alliance_id']
        self.room_group_name = f'alliance_chat_{self.alliance_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        username = data['username']
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'alliance_message',
                'message': message,
                'username': username,
                'timestamp': timezone.now().isoformat()
            }
        )
    
    async def alliance_message(self, event):
        await self.send(text_data=json.dumps(event)) 