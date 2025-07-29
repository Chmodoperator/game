from django.core.management.base import BaseCommand
from game.models import Territory, TerrainMonster
import random


class Command(BaseCommand):
    help = 'Create random monsters for unoccupied territories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--percentage',
            type=int,
            default=30,
            help='Percentage of unoccupied territories to populate with monsters (default: 30%)',
        )

    def handle(self, *args, **options):
        percentage = options['percentage']
        
        # Get all unoccupied territories
        unoccupied_territories = Territory.objects.filter(owner=None)
        total_unoccupied = unoccupied_territories.count()
        
        if total_unoccupied == 0:
            self.stdout.write(self.style.WARNING('No unoccupied territories found.'))
            return
        
        # Calculate how many territories to populate
        territories_to_populate = int(total_unoccupied * percentage / 100)
        
        # Randomly select territories
        selected_territories = random.sample(list(unoccupied_territories), territories_to_populate)
        
        # Terrain to monster mapping
        terrain_to_monster = {
            'plains': 'plains_wolves',
            'mountains': 'mountain_giants',
            'desert': 'desert_scorpions',
            'forest': 'forest_treants',
            'water': 'water_krakens',
            'volcanic': 'volcanic_dragons',
        }
        
        monsters_created = 0
        
        for territory in selected_territories:
            # Skip if monsters already exist
            if territory.monsters.exists():
                continue
            
            # Determine monster type based on terrain
            monster_type = terrain_to_monster.get(territory.terrain_type, 'plains_wolves')
            
            # Random monster characteristics
            monster_size = random.randint(50, 200)  # 50-200 creatures
            monster_level = random.randint(1, 5)    # Level 1-5
            
            # Create monster
            monster = TerrainMonster.objects.create(
                territory=territory,
                monster_type=monster_type,
                size=monster_size,
                level=monster_level
            )
            
            monsters_created += 1
            
            self.stdout.write(
                f'Created {monster.get_monster_type_display()} Lv.{monster.level} '
                f'({monster.size} creatures) at ({territory.x}, {territory.y})'
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {monsters_created} monster groups in '
                f'{territories_to_populate} territories ({percentage}% of {total_unoccupied} unoccupied territories)'
            )
        ) 