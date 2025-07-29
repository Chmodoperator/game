from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from game.models import Empire, Territory, Building, Army
import random


class Command(BaseCommand):
    help = 'Give admin 10 million resources and create fake players for testing'

    def handle(self, *args, **options):
        # Give admin massive resources
        try:
            admin_user = User.objects.get(username='admin')
            admin_empire = admin_user.empire
            
            admin_empire.energy = 10000000
            admin_empire.minerals = 10000000
            admin_empire.food = 10000000
            admin_empire.technology = 10000000
            admin_empire.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully gave admin 10 million of each resource!')
            )
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Admin user not found. Please create admin user first.')
            )
            return
        except Empire.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Admin empire not found. Please create admin empire first.')
            )
            return

        # Create fake players for testing
        fake_players = [
            {'username': 'bot_warrior', 'empire_name': 'Iron Legion', 'color': '#ff4444'},
            {'username': 'bot_merchant', 'empire_name': 'Trade Federation', 'color': '#44ff44'},
            {'username': 'bot_tech', 'empire_name': 'Cyber Collective', 'color': '#4444ff'},
            {'username': 'bot_explorer', 'empire_name': 'Star Wanderers', 'color': '#ffaa00'},
            {'username': 'bot_defender', 'empire_name': 'Shield Guard', 'color': '#aa44ff'},
        ]

        for player_data in fake_players:
            # Create user if doesn't exist
            user, created = User.objects.get_or_create(
                username=player_data['username'],
                defaults={
                    'email': f"{player_data['username']}@fake.com",
                    'password': 'fake_password_hash'
                }
            )
            
            if created:
                self.stdout.write(f"Created fake user: {player_data['username']}")
            
            # Create empire if doesn't exist
            empire, empire_created = Empire.objects.get_or_create(
                user=user,
                defaults={
                    'name': player_data['empire_name'],
                    'color': player_data['color'],
                    'energy': 50000,
                    'minerals': 30000,
                    'food': 20000,
                    'technology': 5000
                }
            )
            
            if empire_created:
                self.stdout.write(f"Created fake empire: {player_data['empire_name']}")
                
                # Assign random territories to fake players
                available_territories = Territory.objects.filter(owner=None)[:random.randint(3, 8)]
                
                for territory in available_territories:
                    territory.owner = empire
                    territory.save()
                    
                    # Add some buildings
                    if random.random() < 0.7:  # 70% chance
                        Building.objects.create(
                            empire=empire,
                            territory=territory,
                            building_type=random.choice(['power_plant', 'mine', 'farm', 'barracks']),
                            level=random.randint(1, 5)
                        )
                    
                    # Add some armies
                    if random.random() < 0.5:  # 50% chance
                        Army.objects.create(
                            empire=empire,
                            territory=territory,
                            unit_type=random.choice(['infantry', 'archers', 'spearmen']),
                            size=random.randint(100, 1000),
                
                        )
                
                self.stdout.write(f"Assigned {available_territories.count()} territories to {empire.name}")
            
            # Calculate empire power
            empire.calculate_power()

        self.stdout.write(
            self.style.SUCCESS('Successfully created fake players for testing!')
        ) 