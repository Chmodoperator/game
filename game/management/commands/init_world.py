from django.core.management.base import BaseCommand
from django.conf import settings
from game.models import Territory, WorldEvent, GameStats
import random
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Initialize the Nova Terra world with territories and basic game data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all existing world data',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Resetting world data...'))
            Territory.objects.all().delete()
            WorldEvent.objects.all().delete()
            GameStats.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('Initializing Nova Terra world...'))
        
        # Create world territories
        self.create_territories()
        
        # Create initial world events
        self.create_world_events()
        
        # Initialize game stats
        self.create_game_stats()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully initialized Nova Terra world!')
        )

    def create_territories(self):
        """Create the 50x50 world map"""
        self.stdout.write('Creating world territories...')
        
        territories_created = 0
        
        for x in range(settings.WORLD_SIZE):
            for y in range(settings.WORLD_SIZE):
                if not Territory.objects.filter(x=x, y=y).exists():
                    # Determine terrain type based on position and randomness
                    terrain_type = self.determine_terrain(x, y)
                    
                    # Determine resource bonus
                    resource_bonus = self.determine_resource_bonus(terrain_type)
                    
                    # Calculate defense bonus
                    defense_bonus = self.calculate_defense_bonus(terrain_type)
                    
                    Territory.objects.create(
                        x=x,
                        y=y,
                        terrain_type=terrain_type,
                        resource_bonus=resource_bonus,
                        defense_bonus=defense_bonus
                    )
                    territories_created += 1

        self.stdout.write(f'Created {territories_created} new territories')

    def determine_terrain(self, x, y):
        """Determine terrain type based on position and patterns"""
        # Create more realistic terrain distribution
        
        # Distance from center
        center_x, center_y = settings.WORLD_SIZE // 2, settings.WORLD_SIZE // 2
        distance_from_center = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
        
        # Add some randomness
        rand = random.random()
        
        # Water bodies near edges
        if (x < 3 or x > settings.WORLD_SIZE - 4 or 
            y < 3 or y > settings.WORLD_SIZE - 4) and rand < 0.3:
            return 'water'
        
        # Mountains in clusters
        if distance_from_center > 15 and rand < 0.2:
            return 'mountains'
        
        # Volcanic areas (rare)
        if rand < 0.05:
            return 'volcanic'
        
        # Desert in certain regions
        if (x > settings.WORLD_SIZE * 0.6 and y < settings.WORLD_SIZE * 0.4) and rand < 0.4:
            return 'desert'
        
        # Forest clusters
        if distance_from_center < 20 and rand < 0.25:
            return 'forest'
        
        # Default to plains
        return 'plains'

    def determine_resource_bonus(self, terrain_type):
        """Determine resource bonus based on terrain"""
        terrain_bonuses = {
            'plains': ['food', 'none', 'none'],
            'mountains': ['minerals', 'minerals', 'energy'],
            'desert': ['energy', 'none', 'none'],
            'forest': ['food', 'food', 'none'],
            'water': ['none', 'none', 'none'],
            'volcanic': ['energy', 'minerals', 'none'],
        }
        
        return random.choice(terrain_bonuses.get(terrain_type, ['none']))

    def calculate_defense_bonus(self, terrain_type):
        """Calculate defense bonus based on terrain"""
        terrain_defense = {
            'plains': (0, 2),
            'mountains': (5, 15),
            'desert': (1, 5),
            'forest': (2, 8),
            'water': (0, 0),
            'volcanic': (3, 10),
        }
        
        min_def, max_def = terrain_defense.get(terrain_type, (0, 2))
        return random.randint(min_def, max_def)

    def create_world_events(self):
        """Create initial world events"""
        self.stdout.write('Creating world events...')
        
        events = [
            {
                'title': 'Solar Storm Activity',
                'description': 'Increased solar activity is affecting energy production across the galaxy. Energy generation reduced by 20% for all empires.',
                'event_type': 'natural_disaster',
                'effects': {'energy_modifier': -0.2},
                'duration_hours': 24
            },
            {
                'title': 'Mineral Discovery',
                'description': 'New mineral deposits have been discovered in mountainous regions. Mineral production increased by 50% in mountain territories.',
                'event_type': 'resource_discovery',
                'effects': {'mineral_bonus_mountains': 0.5},
                'duration_hours': 72
            },
            {
                'title': 'Trade Winds',
                'description': 'Favorable cosmic currents are boosting food production in agricultural regions. Food production increased by 30%.',
                'event_type': 'technological_breakthrough',
                'effects': {'food_modifier': 0.3},
                'duration_hours': 48
            }
        ]
        
        for event_data in events:
            # Random chance to create each event
            if random.random() < 0.3:
                WorldEvent.objects.create(
                    title=event_data['title'],
                    description=event_data['description'],
                    event_type=event_data['event_type'],
                    effects=event_data['effects'],
                    ends_at=timezone.now() + timedelta(hours=event_data['duration_hours']),
                    is_active=True
                )

    def create_game_stats(self):
        """Initialize game statistics"""
        self.stdout.write('Initializing game statistics...')
        
        if not GameStats.objects.exists():
            GameStats.objects.create(
                total_players=0,
                total_battles=0,
                total_territories_conquered=0
            ) 