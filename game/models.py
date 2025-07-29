from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.db import transaction
import random
import json
import math


class Empire(models.Model):
    """Player's empire/civilization"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    
    # Master Player System
    is_master_player = models.BooleanField(default=False)  # True for bot empires
    master_level = models.IntegerField(default=1)  # Bot difficulty level 1-10
    
    # Resources - MASSIVELY INCREASED starting resources
    energy = models.IntegerField(default=5000)    # Was 1000, now 5000
    minerals = models.IntegerField(default=3000)  # Was 500, now 3000  
    food = models.IntegerField(default=2000)      # Was 300, now 2000
    technology = models.IntegerField(default=0)
    gold = models.IntegerField(default=20)  # Premium currency for instant actions
    
    # Production rates per hour - INCREASED starting production
    energy_production = models.IntegerField(default=100)    # Was 10, now 100
    mineral_production = models.IntegerField(default=100)   # Was 5, now 100
    food_production = models.IntegerField(default=100)      # Was 8, now 100
    
    # Last resource generation time
    last_resource_update = models.DateTimeField(default=timezone.now)
    
    # Fractional resource accumulation for precise calculation
    energy_fraction = models.FloatField(default=0.0)  # Accumulated fractional energy
    mineral_fraction = models.FloatField(default=0.0)  # Accumulated fractional minerals  
    food_fraction = models.FloatField(default=0.0)    # Accumulated fractional food
    
    # Storage capacity system - NEW FEATURE
    energy_storage = models.IntegerField(default=6000)    # Base storage capacity
    mineral_storage = models.IntegerField(default=6000)   # Base storage capacity
    food_storage = models.IntegerField(default=6000)      # Base storage capacity
    
    # Stats
    population = models.IntegerField(default=1000)
    power_level = models.IntegerField(default=100)
    rank = models.IntegerField(default=0)
    
    # Empire attributes
    color = models.CharField(max_length=7, default="#00FF00")  # Hex color
    motto = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    def calculate_power(self):
        """Calculate empire's total power level"""
        territories = self.territories.count()
        buildings = sum(building.level for building in self.buildings.all())
        research = sum(research.level for research in self.research.all())
        armies = sum(army.size for army in self.armies.all())
        
        # Update population based on buildings
        self.population = self.calculate_population()
        
        # Update storage capacity based on buildings
        self.calculate_storage_capacity()
        
        self.power_level = territories * 10 + buildings * 5 + research * 20 + armies
        self.save()
        return self.power_level
    
    def calculate_population(self):
        """Calculate empire's total population based on buildings"""
        total_population = 1000  # Base population
        
        for building in self.buildings.all():
            # Each building adds population based on type and level
            building_population = self.get_building_population(building.building_type, building.level)
            total_population += building_population
        
        return total_population
    
    def get_building_population(self, building_type, level):
        """Calculate population contribution of a building"""
        # Base population per building type
        base_population = {
            'command_center': 5,   # High command = more administrators
            'power_plant': 2,      # Few technicians needed
            'mine': 3,             # Miners and operators
            'farm': 4,             # Agricultural workers
            'research_lab': 3,     # Scientists and researchers
            'barracks': 2,         # Military personnel (counted separately from armies)
            'defense_system': 1,   # Automated systems, few operators
            'spy_network': 2,      # Intelligence operatives
            'intelligence_hub': 4, # Elite intelligence operatives and analysts
            'factory': 4,          # Factory workers
            'warehouse': 3,        # Storage and logistics workers
        }
        
        base = base_population.get(building_type, 2)
        
        # Each level adds 1-5 population based on building cost/complexity
        level_multiplier = {
            'command_center': 5,   # Expensive, adds lots of admin staff
            'power_plant': 2,      # Automated, fewer people per level
            'mine': 3,             # More miners per level
            'farm': 4,             # More agricultural workers
            'research_lab': 4,     # More scientists
            'barracks': 2,         # Military infrastructure
            'defense_system': 1,   # Mostly automated
            'spy_network': 3,      # More operatives
            'intelligence_hub': 5, # Elite intelligence facility, high-value personnel
            'factory': 4,          # More workers
            'warehouse': 3,        # More storage workers
        }
        
        multiplier = level_multiplier.get(building_type, 2)
        
        # Total: base + (level * multiplier)
        return base + (level * multiplier)
    
    def calculate_production_rates(self):
        """Calculate current production rates based on buildings and research"""
        # MASSIVELY INCREASED base production - start with 100/hour each
        energy_rate = 100  # Was 10, now 100 (10x increase)
        mineral_rate = 100  # Was 5, now 100 (20x increase) 
        food_rate = 100    # Was 8, now 100 (12.5x increase)
        
        # DRAMATICALLY INCREASED building bonuses
        for building in self.buildings.all():
            if building.building_type == 'power_plant':
                energy_rate += building.level * 50  # Was 5, now 50 per level (10x)
            elif building.building_type == 'mine':
                mineral_rate += building.level * 30  # Was 3, now 30 per level (10x)
            elif building.building_type == 'farm':
                food_rate += building.level * 40     # Was 4, now 40 per level (10x)
        
        # INCREASED territory bonuses
        territory_bonus = self.territories.count() * 20  # Was 2, now 20 per territory (10x)
        energy_rate += territory_bonus
        mineral_rate += territory_bonus
        food_rate += territory_bonus
        
        # Research bonuses (keeping same multipliers but applying to much higher base)
        energy_research = self.research.filter(research_type='energy_efficiency').first()
        if energy_research:
            energy_rate = int(energy_rate * (1 + energy_research.level * 0.1))
        
        mining_research = self.research.filter(research_type='mining_technology').first()
        if mining_research:
            mineral_rate = int(mineral_rate * (1 + mining_research.level * 0.15))
        
        agriculture_research = self.research.filter(research_type='agriculture').first()
        if agriculture_research:
            food_rate = int(food_rate * (1 + agriculture_research.level * 0.12))
        
        # Update production rates
        self.energy_production = energy_rate
        self.mineral_production = mineral_rate
        self.food_production = food_rate
        self.save()
        
        return energy_rate, mineral_rate, food_rate
    
    @transaction.atomic
    def generate_resources(self):
        """Generate resources based on time passed and production rates with fractional accumulation"""
        # Refresh from database with lock to prevent race conditions
        empire = Empire.objects.select_for_update().get(id=self.id)
        
        now = timezone.now()
        time_passed = (now - empire.last_resource_update).total_seconds()
        
        # Generate resources every 5 seconds instead of 10 for even more responsive updates
        if time_passed >= 5:  # Generate resources every 5 seconds
            # Calculate current production rates and storage capacity
            empire.calculate_production_rates()
            empire.calculate_storage_capacity()
            
            # Generate resources for the time that passed
            hours_passed = time_passed / 3600  # Convert seconds to hours
            
            # Calculate resource generation with fractional accumulation
            energy_generated_raw = empire.energy_production * hours_passed + empire.energy_fraction
            minerals_generated_raw = empire.mineral_production * hours_passed + empire.mineral_fraction
            food_generated_raw = empire.food_production * hours_passed + empire.food_fraction
            
            # Extract integer parts for adding to resources
            energy_generated = int(energy_generated_raw)
            minerals_generated = int(minerals_generated_raw)
            food_generated = int(food_generated_raw)
            
            # Keep fractional parts for next calculation
            empire.energy_fraction = energy_generated_raw - energy_generated
            empire.mineral_fraction = minerals_generated_raw - minerals_generated
            empire.food_fraction = food_generated_raw - food_generated
            
            # Store old values for debugging
            old_energy = int(empire.energy)  # Ensure integer
            old_minerals = int(empire.minerals)  # Ensure integer
            old_food = int(empire.food)  # Ensure integer
            
            # Add generated resources and ensure integers
            empire.energy = int(empire.energy + energy_generated)
            empire.minerals = int(empire.minerals + minerals_generated)
            empire.food = int(empire.food + food_generated)
            
            # Enforce storage limits - resources can't exceed storage capacity
            empire.enforce_storage_limits()
            
            # Update last generation time
            empire.last_resource_update = now
            empire.save()
            
            # Update self with new values (all integers)
            self.energy = int(empire.energy)
            self.minerals = int(empire.minerals)
            self.food = int(empire.food)
            self.energy_production = int(empire.energy_production)
            self.mineral_production = int(empire.mineral_production)
            self.food_production = int(empire.food_production)
            self.energy_storage = int(empire.energy_storage)
            self.mineral_storage = int(empire.mineral_storage)
            self.food_storage = int(empire.food_storage)
            self.energy_fraction = empire.energy_fraction
            self.mineral_fraction = empire.mineral_fraction
            self.food_fraction = empire.food_fraction
            self.last_resource_update = empire.last_resource_update
            
            return {
                'generated': True,
                'energy_generated': energy_generated,
                'minerals_generated': minerals_generated,
                'food_generated': food_generated,
                'time_passed_seconds': time_passed,
                'hours_passed': hours_passed,
                'raw_generation': {
                    'energy': energy_generated_raw,
                    'minerals': minerals_generated_raw,
                    'food': food_generated_raw
                },
                'fractional_accumulation': {
                    'energy': empire.energy_fraction,
                    'minerals': empire.mineral_fraction,
                    'food': empire.food_fraction
                },
                'old_values': {
                    'energy': old_energy,
                    'minerals': old_minerals,
                    'food': old_food
                },
                'new_values': {
                    'energy': int(empire.energy),
                    'minerals': int(empire.minerals),
                    'food': int(empire.food)
                }
            }
        
        return {
            'generated': False,
            'time_until_next': 5 - time_passed,
            'time_passed_seconds': time_passed
        }
    
    @classmethod
    def create_master_player(cls, territory, level=None):
        """Create a master player (bot) empire for a territory"""
        if level is None:
            level = random.randint(1, 5)  # Random bot level
        
        # Generate bot name
        bot_names = [
            'Master Khan', 'Lord Vex', 'Commander Steel', 'Baron Nexus',
            'General Storm', 'Admiral Frost', 'Captain Blaze', 'Colonel Shadow',
            'Overlord Titan', 'Marshal Iron', 'Chief Quantum', 'Duke Void'
        ]
        
        # Create user account for bot
        from django.contrib.auth.models import User
        username = f"master_{territory.x}_{territory.y}"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': random.choice(bot_names),
                'is_active': False  # Bots don't need login
            }
        )
        
        # Create bot empire
        empire, created = cls.objects.get_or_create(
            user=user,
            defaults={
                'name': user.first_name,
                'is_master_player': True,
                'master_level': level,
                'energy': 2500 + (level * 1000),    # Was 500 + (level * 200), now much higher
                'minerals': 1500 + (level * 500),   # Was 300 + (level * 100), now much higher  
                'food': 1000 + (level * 250),       # Was 200 + (level * 50), now much higher
                'color': f"#{random.randint(100, 255):02x}{random.randint(100, 255):02x}{random.randint(100, 255):02x}"
            }
        )
        
        if created:
            # Assign territory to bot
            territory.owner = empire
            territory.save()
            
            # Create initial buildings for bot
            empire._create_master_player_buildings(territory, level)
            
            # Create initial armies for bot
            empire._create_master_player_armies(territory, level)
        
        return empire
    
    def _create_master_player_buildings(self, territory, level):
        """Create initial buildings for master player"""
        # Basic buildings based on level
        buildings_to_create = [
            'command_center',
            'power_plant',
            'mine',
            'farm',
            'barracks'
        ]
        
        if level >= 3:
            buildings_to_create.extend(['defense_system', 'research_lab'])
        if level >= 5:
            buildings_to_create.extend(['spy_network', 'factory'])
        if level >= 7:
            buildings_to_create.extend(['intelligence_hub', 'warehouse'])
        
        for building_type in buildings_to_create:
            building_level = min(level + random.randint(0, 2), 10)
            Building.objects.create(
                empire=self,
                territory=territory,
                building_type=building_type,
                level=building_level
            )
        
        # Recalculate production after building creation
        self.calculate_production_rates()
    
    def _create_master_player_armies(self, territory, level):
        """Create armies for master player based on level"""
        # Base army types available by level
        army_types = ['infantry', 'archers']  # Start with basic units
        
        if level >= 3:
            army_types.append('spearmen')
        if level >= 5:
            army_types.extend(['heavy_knights', 'spies'])
        if level >= 7:
            army_types.append('royal_knights')
        
        # Create armies with sizes based on level
        for army_type in army_types:
            base_sizes = {
                'infantry': 200,
                'archers': 100,
                'spearmen': 50,
                'heavy_knights': 80,
                'royal_knights': 30,
                'spies': 20
            }
            
            base_size = base_sizes.get(army_type, 100)
            army_size = int(base_size * (level / 2))  # Scale with level
            
            if army_size > 0:
                Army.objects.create(
                    empire=self,
                    territory=territory,
                    unit_type=army_type,
                    size=army_size,
        
                )
    
    def is_bot(self):
        """Check if this empire is a bot (master player)"""
        return self.is_master_player
    
    def get_master_difficulty(self):
        """Get bot difficulty description"""
        if not self.is_master_player:
            return "Human Player"
        
        difficulty_names = {
            1: "Novice",
            2: "Easy", 
            3: "Normal",
            4: "Hard",
            5: "Expert",
            6: "Master",
            7: "Elite",
            8: "Champion",
            9: "Legendary",
            10: "Godlike"
        }
        return difficulty_names.get(self.master_level, "Unknown")
    
    def calculate_storage_capacity(self):
        """Calculate storage capacity based on buildings"""
        # Base storage
        base_storage = 6000
        
        # Storage bonuses from buildings
        storage_bonus = 0
        for building in self.buildings.all():
            if building.building_type == 'command_center':
                storage_bonus += building.level * 500   # Command centers add 500 per level
            elif building.building_type == 'factory':
                storage_bonus += building.level * 300   # Factories add 300 per level  
            elif building.building_type == 'defense_system':
                storage_bonus += building.level * 200   # Defense systems add 200 per level
            elif building.building_type == 'warehouse':
                storage_bonus += building.level * 800   # Warehouses add 800 per level (highest bonus!)
        
        # Territory bonuses (more territories = more storage infrastructure)
        territory_bonus = self.territories.count() * 100  # 100 storage per territory
        
        # Calculate total storage for each resource type
        total_storage = base_storage + storage_bonus + territory_bonus
        
        # Update storage capacity
        self.energy_storage = total_storage
        self.mineral_storage = total_storage
        self.food_storage = total_storage
        self.save()
        
        return total_storage
    
    def enforce_storage_limits(self):
        """Ensure resources don't exceed storage capacity"""
        resources_capped = False
        overflow_amounts = {}
        
        # Cap energy at storage limit
        if self.energy > self.energy_storage:
            overflow_amounts['energy'] = int(self.energy - self.energy_storage)
            self.energy = int(self.energy_storage)
            resources_capped = True
        else:
            self.energy = int(self.energy)  # Ensure integer even if not capped
        
        # Cap minerals at storage limit
        if self.minerals > self.mineral_storage:
            overflow_amounts['minerals'] = int(self.minerals - self.mineral_storage)
            self.minerals = int(self.mineral_storage)
            resources_capped = True
        else:
            self.minerals = int(self.minerals)  # Ensure integer even if not capped
        
        # Cap food at storage limit
        if self.food > self.food_storage:
            overflow_amounts['food'] = int(self.food - self.food_storage)
            self.food = int(self.food_storage)
            resources_capped = True
        else:
            self.food = int(self.food)  # Ensure integer even if not capped
        
        # Save if any resources were capped
        if resources_capped:
            self.save()
            
            # Log the overflow for debugging (optional)
            print(f"🚨 Storage overflow for {self.name}: {overflow_amounts}")
            
        return resources_capped, overflow_amounts
    
    def get_present_armies(self):
        """Get all armies that are currently present in their territories (not away on missions)"""
        # Get all armies with size > 0
        all_armies = self.armies.filter(size__gt=0)
        
        # Get armies that are currently in active battles
        active_battles = Battle.objects.filter(
            status__in=['traveling', 'fighting', 'returning']
        )
        
        armies_in_battle = set()
        for battle in active_battles:
            # Check attacking armies
            if battle.attacking_armies:
                for army_id_str in battle.attacking_armies.keys():
                    try:
                        armies_in_battle.add(int(army_id_str))
                    except (ValueError, TypeError):
                        continue
            
            # Check defending armies  
            if battle.defending_armies:
                for army_id_str in battle.defending_armies.keys():
                    try:
                        armies_in_battle.add(int(army_id_str))
                    except (ValueError, TypeError):
                        continue
        
        # Return armies not in battle
        return all_armies.exclude(id__in=armies_in_battle)
    
    def get_total_present_army_strength(self):
        """Get total combat strength of all present armies"""
        return sum(army.get_combat_strength() for army in self.get_present_armies())


class Territory(models.Model):
    """World map territories (50x50 grid)"""
    x = models.IntegerField()
    y = models.IntegerField()
    owner = models.ForeignKey(Empire, on_delete=models.SET_NULL, null=True, blank=True, related_name='territories')
    
    # Territory attributes
    terrain_type = models.CharField(max_length=20, choices=[
        ('plains', 'Plains'),
        ('mountains', 'Mountains'),
        ('desert', 'Desert'),
        ('forest', 'Forest'),
        ('water', 'Water'),
        ('volcanic', 'Volcanic'),
    ], default='plains')
    
    resource_bonus = models.CharField(max_length=20, choices=[
        ('energy', 'Energy Rich'),
        ('minerals', 'Mineral Rich'),
        ('food', 'Fertile'),
        ('none', 'None'),
    ], default='none')
    
    defense_bonus = models.IntegerField(default=0)
    occupied_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('x', 'y')
    
    def __str__(self):
        return f"Territory ({self.x}, {self.y})"
    
    def get_ascii_symbol(self):
        """Return ASCII symbol for this territory"""
        symbols = {
            'plains': '.',
            'mountains': '^',
            'desert': '~',
            'forest': '#',
            'water': '≈',
            'volcanic': '*',
        }
        return symbols.get(self.terrain_type, '.')
    
    def calculate_distance(self, other_territory):
        """Calculate distance to another territory using Euclidean distance"""
        dx = abs(self.x - other_territory.x)
        dy = abs(self.y - other_territory.y)
        return math.sqrt(dx * dx + dy * dy)
    
    def get_present_armies(self):
        """Get armies that are currently present in this territory (not away on missions)"""
        # Get all armies with size > 0 in this territory
        all_armies = self.armies.filter(size__gt=0)
        
        # Get armies that are currently in active battles
        active_battles = Battle.objects.filter(
            status__in=['traveling', 'fighting', 'returning']
        )
        
        armies_in_battle = set()
        for battle in active_battles:
            # Check attacking armies
            if battle.attacking_armies:
                for army_id_str in battle.attacking_armies.keys():
                    try:
                        armies_in_battle.add(int(army_id_str))
                    except (ValueError, TypeError):
                        continue
            
            # Check defending armies  
            if battle.defending_armies:
                for army_id_str in battle.defending_armies.keys():
                    try:
                        armies_in_battle.add(int(army_id_str))
                    except (ValueError, TypeError):
                        continue
        
        # Return armies not in battle
        return all_armies.exclude(id__in=armies_in_battle)
    
    def get_total_present_army_strength(self):
        """Get total combat strength of all present armies"""
        return sum(army.get_combat_strength() for army in self.get_present_armies())

    def get_available_armies(self):
        """Get all armies with their available units (including newly recruited units)"""
        all_armies = self.armies.filter(size__gt=0)
        available_armies = []
        for army in all_armies:
            available_units = army.get_available_units()
            if available_units > 0:
                army.available_size = available_units  # Attach available_size for display
                available_armies.append(army)
        return available_armies


class Building(models.Model):
    """Buildings in player's empire"""
    empire = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='buildings')
    territory = models.ForeignKey(Territory, on_delete=models.CASCADE, related_name='buildings')
    
    building_type = models.CharField(max_length=30, choices=[
        ('command_center', 'Command Center'),
        ('power_plant', 'Power Plant'),
        ('mine', 'Mine'),
        ('farm', 'Farm'),
        ('research_lab', 'Research Lab'),
        ('barracks', 'Barracks'),
        ('defense_system', 'Defense System'),
        ('spy_network', 'Spy Network'),
        ('intelligence_hub', 'Intelligence Hub'),
        ('factory', 'Factory'),
        ('warehouse', 'Warehouse'),
    ])
    
    level = models.IntegerField(default=1)
    built_at = models.DateTimeField(auto_now_add=True)
    upgrade_started = models.DateTimeField(null=True, blank=True)
    upgrade_complete = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('territory', 'building_type')  # Only one building type per territory
    
    def __str__(self):
        return f"{self.get_building_type_display()} Lv.{self.level}"
    
    def can_upgrade(self):
        """Check if building can be upgraded"""
        if self.level >= 100:  # Maximum level cap
            return False
        if self.upgrade_started and timezone.now() < self.upgrade_complete:
            return False
        return True
    
    def start_upgrade(self):
        """Start building upgrade"""
        if not self.can_upgrade():
            return False
        
        upgrade_time = self.level * settings.BUILDING_TIME_MULTIPLIER
        self.upgrade_started = timezone.now()
        self.upgrade_complete = timezone.now() + timezone.timedelta(minutes=upgrade_time)
        self.save()
        return True
    
    def complete_upgrade(self):
        """Complete building upgrade if time has passed"""
        if (self.upgrade_started and 
            self.upgrade_complete and 
            timezone.now() >= self.upgrade_complete):
            self.level += 1
            self.upgrade_started = None
            self.upgrade_complete = None
            self.save()
            # Recalculate empire production rates after upgrade completion
            self.empire.calculate_production_rates()
            return True
        return False
    
    @staticmethod
    def max_buildings_per_territory():
        """Maximum number of buildings allowed per territory"""
        return 7
    
    @staticmethod
    def get_building_icons():
        """Get icons for each building type"""
        return {
            'command_center': '🏛️',
            'power_plant': '⚡',
            'mine': '⛏️',
            'farm': '🌾',
            'research_lab': '🔬',
            'barracks': '🪖',
            'defense_system': '🛡️',
            'spy_network': '🕵️',
            'intelligence_hub': '🎯',
            'factory': '🏭',
            'warehouse': '📦',
        }
    
    @staticmethod
    def get_building_names():
        """Get display names for each building type"""
        return {
            'command_center': 'Command Center',
            'power_plant': 'Power Plant',
            'mine': 'Mine',
            'farm': 'Farm',
            'research_lab': 'Research Lab',
            'barracks': 'Barracks',
            'defense_system': 'Defense System',
            'spy_network': 'Spy Network',
            'intelligence_hub': 'Intelligence Hub',
            'factory': 'Factory',
            'warehouse': 'Warehouse',
        }


class Research(models.Model):
    """Research technologies"""
    empire = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='research')
    
    research_type = models.CharField(max_length=30, choices=[
        ('warfare_tactics', 'Warfare Tactics'),
        ('fortification_arts', 'Fortification Arts'),
        ('resource_alchemy', 'Resource Alchemy'),
        ('agricultural_mastery', 'Agricultural Mastery'),
        ('mining_expertise', 'Mining Expertise'),
        ('royal_engineering', 'Royal Engineering'),
        ('diplomatic_arts', 'Diplomatic Arts'),
    ])
    
    level = models.IntegerField(default=0)
    research_started = models.DateTimeField(null=True, blank=True)
    research_complete = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('empire', 'research_type')
    
    def __str__(self):
        return f"{self.get_research_type_display()} Lv.{self.level}"
    
    def can_research(self):
        """Check if research can be started"""
        if self.level >= 100:  # Maximum level cap
            return False
        if self.research_started and timezone.now() < self.research_complete:
            return False
        return True
    
    def start_research(self):
        """Start research"""
        if not self.can_research():
            return False
        
        # Research time increases with level: 30 minutes base, +30 minutes per level
        research_time_minutes = 30 + (self.level * 30)  # Level 1: 30min, Level 10: 330min, etc.
        
        self.research_started = timezone.now()
        self.research_complete = timezone.now() + timezone.timedelta(minutes=research_time_minutes)
        self.save()
        return True
    
    def complete_research(self):
        """Complete research if time has passed"""
        if (self.research_started and 
            self.research_complete and 
            timezone.now() >= self.research_complete):
            self.level += 1
            self.research_started = None
            self.research_complete = None
            self.save()
            # Recalculate empire production rates after research completion
            self.empire.calculate_production_rates()
            return True
        return False
    
    def get_research_benefits(self):
        """Get the benefits this research provides"""
        benefits = {
            'warfare_tactics': {
                'name': 'Army Attack Power',
                'value': f'+{self.level * 2}%',
                'description': 'Increases attack power of all military units'
            },
            'fortification_arts': {
                'name': 'Army Defense Power', 
                'value': f'+{self.level * 2}%',
                'description': 'Increases defense power of all military units'
            },
            'resource_alchemy': {
                'name': 'Resource Conversion Efficiency',
                'value': f'{self.level * 5}%',
                'description': 'Enables converting resources with reduced losses'
            },
            'agricultural_mastery': {
                'name': 'Food Production',
                'value': f'+{self.level * 3}%',
                'description': 'Increases food production from all farms'
            },
            'mining_expertise': {
                'name': 'Mineral Extraction',
                'value': f'+{self.level * 3}%',
                'description': 'Increases mineral production from all mines'
            },
            'royal_engineering': {
                'name': 'Building Construction Speed',
                'value': f'+{self.level * 4}%',
                'description': 'Reduces building upgrade time and costs'
            },
            'diplomatic_arts': {
                'name': 'Diplomatic Relations',
                'value': f'+{self.level * 2}%',
                'description': 'Improves trade deals and alliance benefits'
            }
        }
        return benefits.get(self.research_type, {})
    
    def get_research_cost(self):
        """Calculate cost for next level"""
        next_level = self.level + 1
        base_cost = 500
        
        # Exponential cost scaling
        multiplier = (next_level ** 1.5) * 1.2
        
        return {
            'energy': int(base_cost * multiplier),
            'minerals': int(base_cost * multiplier * 0.6),
            'food': int(base_cost * multiplier * 0.4),
        }


class Army(models.Model):
    """Military units"""
    empire = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='armies')
    territory = models.ForeignKey(Territory, on_delete=models.CASCADE, related_name='armies')
    
    unit_type = models.CharField(max_length=20, choices=[
        ('infantry', 'Infantry'),
        ('archers', 'Archers'),
        ('spearmen', 'Spearmen'),
        ('heavy_knights', 'Heavy Knights'),
        ('royal_knights', 'Royal Knights'),
        ('spies', 'Spies'),
        ('catapult', 'Catapult'),
        ('ram', 'Ram'),
        ('hero', 'Hero'),
        ('healer', 'Healer'),
        ('scout_hawk', 'Scout Hawk'),
    ], default='infantry')
    
    size = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Recruitment fields
    recruitment_started = models.DateTimeField(null=True, blank=True)
    recruitment_complete = models.DateTimeField(null=True, blank=True)
    target_size = models.IntegerField(default=0)  # Size when recruitment completes
    recruitment_rate = models.FloatField(default=1.0)  # Units per second
    
    def __str__(self):
        return f"{self.size} {self.get_unit_type_display()}"
    
    def get_combat_strength(self):
        """Calculate army combat strength using new sophisticated system"""
        stats = self.get_unit_combat_stats()
        unit_key = self.unit_type.lower()
        
        if unit_key not in stats:
            return self.size  # Fallback to simple size
        
        unit_stats = stats[unit_key]
        base_attack = unit_stats['attack']
        
        # Include research bonuses
        military_research = self.empire.research.filter(research_type='military_tactics').first()
        research_bonus = 1 + (military_research.level * 0.1 if military_research else 0)
        
        # Include alliance bonuses (10% attack bonus for alliance members)
        alliance_bonus = 1.0
        if self.empire.alliances.exists():
            alliance_bonus = 1.1  # 10% attack bonus for alliance members
        
        # Total combat strength = size × base_attack × bonuses
        return int(self.size * base_attack * research_bonus * alliance_bonus)
    
    def get_combat_strength_per_unit(self):
        """Calculate combat strength per individual unit"""
        stats = self.get_unit_combat_stats()
        unit_key = self.unit_type.lower()
        
        if unit_key not in stats:
            return 1  # Fallback to simple value
        
        unit_stats = stats[unit_key]
        base_attack = unit_stats['attack']
        
        # Include research bonuses
        military_research = self.empire.research.filter(research_type='military_tactics').first()
        research_bonus = 1 + (military_research.level * 0.1 if military_research else 0)
        
        # Include alliance bonuses (10% attack bonus for alliance members)
        alliance_bonus = 1.0
        if self.empire.alliances.exists():
            alliance_bonus = 1.1  # 10% attack bonus for alliance members
        
        # Combat strength per unit = base_attack × bonuses
        return base_attack * research_bonus * alliance_bonus
    
    def is_recruiting(self):
        """Check if army is currently recruiting"""
        if not self.recruitment_started or not self.recruitment_complete:
            return False
        return timezone.now() < self.recruitment_complete
    
    def is_in_battle(self):
        """Check if army is currently in battle (traveling, fighting, or returning)"""
        # Check if this army is involved in any active battles
        active_battles = Battle.objects.filter(
            status__in=['traveling', 'fighting', 'returning']
        )
        
        army_id_str = str(self.id)
        for battle in active_battles:
            # Check if army is in attacking armies (JSON field stores dict with army IDs as keys)
            if battle.attacking_armies and army_id_str in battle.attacking_armies:
                return True
            # Check if army is in defending armies (JSON field stores dict with army IDs as keys)
            if battle.defending_armies and army_id_str in battle.defending_armies:
                return True
        
        return False
    
    def get_traveling_units(self):
        """Get number of units currently traveling in battle"""
        active_battles = Battle.objects.filter(
            status__in=['traveling', 'fighting', 'returning']
        )
        
        army_id_str = str(self.id)
        traveling_units = 0
        
        for battle in active_battles:
            # Check if army is in attacking armies
            if battle.attacking_armies and army_id_str in battle.attacking_armies:
                army_data = battle.attacking_armies[army_id_str]
                traveling_units += army_data.get('size', 0)
            # Check if army is in defending armies
            if battle.defending_armies and army_id_str in battle.defending_armies:
                army_data = battle.defending_armies[army_id_str]
                traveling_units += army_data.get('size', 0)
        
        return traveling_units
    
    def get_available_units(self):
        """Get number of units available for battle (not traveling)"""
        traveling_units = self.get_traveling_units()
        return max(0, self.size - traveling_units)
    
    def is_present_in_territory(self):
        """Check if army is currently present in its territory (not away on missions)"""
        return not self.is_in_battle()
    
    def start_recruitment(self, target_size, recruitment_time_minutes):
        """Start recruiting units"""
        self.target_size = target_size
        self.recruitment_started = timezone.now()
        self.recruitment_complete = timezone.now() + timezone.timedelta(minutes=recruitment_time_minutes)
        self.recruitment_rate = max(0.1, (target_size - self.size) / (recruitment_time_minutes * 60))  # Units per second
        self.save()
    
    def update_recruitment(self):
        """Update recruitment progress and size"""
        if not self.is_recruiting():
            return False
        
        now = timezone.now()
        time_passed = (now - self.recruitment_started).total_seconds()
        new_size = min(self.target_size, self.size + int(time_passed * self.recruitment_rate))
        
        if new_size != self.size:
            self.size = new_size
            self.save()
        
        # Check if recruitment is complete
        if now >= self.recruitment_complete:
            self.size = self.target_size
            self.recruitment_started = None
            self.recruitment_complete = None
            self.target_size = 0
            self.recruitment_rate = 0
            self.save()
            return True
        
        return False
    
    def get_recruitment_progress(self):
        """Get recruitment progress percentage"""
        if not self.is_recruiting():
            return 100
        
        total_to_recruit = self.target_size - (self.size if self.recruitment_started else 0)
        if total_to_recruit <= 0:
            return 100
        
        time_passed = (timezone.now() - self.recruitment_started).total_seconds()
        recruited_so_far = min(total_to_recruit, time_passed * self.recruitment_rate)
        
        return min(100, (recruited_so_far / total_to_recruit) * 100)
    
    def get_units_remaining_to_recruit(self):
        """Get number of units remaining to recruit"""
        if not self.is_recruiting():
            return 0
        return max(0, self.target_size - self.size)
    
    @staticmethod
    def get_unit_costs():
        """Get recruitment costs for each unit type - Updated for strategic system"""
        return {
            'infantry': {'energy': 3, 'minerals': 2, 'food': 1, 'units_per_batch': 1},      # Infantry: 3⚡ 2⛏ 1🌾 per unit
            'archers': {'energy': 4, 'minerals': 3, 'food': 2, 'units_per_batch': 1},       # Archers: 4⚡ 3⛏ 2🌾 per unit
            'spearmen': {'energy': 3, 'minerals': 4, 'food': 2, 'units_per_batch': 1},      # Spearmen: 3⚡ 4⛏ 2🌾 per unit
            'heavy_knights': {'energy': 8, 'minerals': 6, 'food': 4, 'units_per_batch': 1}, # Heavy Knights: 8⚡ 6⛏ 4🌾 per unit
            'royal_knights': {'energy': 15, 'minerals': 12, 'food': 8, 'units_per_batch': 1}, # Royal Knights: 15⚡ 12⛏ 8🌾 per unit
            'spies': {'energy': 10, 'minerals': 5, 'food': 15, 'units_per_batch': 1},        # Spies: 10⚡ 5⛏ 15🌾 per unit
            'catapult': {'energy': 20, 'minerals': 25, 'food': 10, 'units_per_batch': 1},   # Catapult: 20⚡ 25⛏ 10🌾 per unit
            'ram': {'energy': 18, 'minerals': 20, 'food': 8, 'units_per_batch': 1},         # Ram: 18⚡ 20⛏ 8🌾 per unit
            'hero': {'energy': 50, 'minerals': 40, 'food': 30, 'units_per_batch': 1},       # Hero: 50⚡ 40⛏ 30🌾 per unit
            'healer': {'energy': 6, 'minerals': 4, 'food': 8, 'units_per_batch': 1},        # Healer: 6⚡ 4⛏ 8🌾 per unit
            'scout_hawk': {'energy': 8, 'minerals': 3, 'food': 12, 'units_per_batch': 1},   # Scout Hawk: 8⚡ 3⛏ 12🌾 per unit
        }
    
    @staticmethod
    def get_unit_combat_stats():
        """Get comprehensive combat statistics for all units with balanced stats"""
        return {
            'infantry': {
                'attack': 12,
                'def_infantry': 15,
                'def_archers': 8,
                'def_spearmen': 12,
                'def_heavy_knights': 6,
                'def_royal_knights': 4,
                'def_spies': 10,
                'storage': 40,
                'speed': 6,
                'training_cost': {'energy': 3, 'minerals': 2, 'food': 1},
                'training_time': 45,  # 45 seconds per unit
                'description': 'Versatile frontline fighters. Good against infantry, weak vs cavalry.',
                'special': 'Balanced unit - jack of all trades, master of none'
            },
            'archers': {
                'attack': 18,
                'def_infantry': 6,
                'def_archers': 12,
                'def_spearmen': 8,
                'def_heavy_knights': 4,
                'def_royal_knights': 3,
                'def_spies': 8,
                'storage': 35,
                'speed': 7,
                'training_cost': {'energy': 4, 'minerals': 3, 'food': 2},
                'training_time': 60,  # 1 minute per unit
                'description': 'Ranged attackers with high damage. Fragile but deadly.',
                'special': 'High attack power, weak defense - keep them protected'
            },
            'spearmen': {
                'attack': 10,
                'def_infantry': 14,
                'def_archers': 10,
                'def_spearmen': 16,
                'def_heavy_knights': 20,
                'def_royal_knights': 18,
                'def_spies': 12,
                'storage': 45,
                'speed': 5,
                'training_cost': {'energy': 3, 'minerals': 4, 'food': 2},
                'training_time': 75,  # 1.25 minutes per unit
                'description': 'Anti-cavalry specialists. Excellent vs knights, slow movement.',
                'special': 'Cavalry killers - essential for defending against mounted units'
            },
            'heavy_knights': {
                'attack': 25,
                'def_infantry': 8,
                'def_archers': 6,
                'def_spearmen': 4,
                'def_heavy_knights': 12,
                'def_royal_knights': 8,
                'def_spies': 6,
                'storage': 80,
                'speed': 9,
                'training_cost': {'energy': 8, 'minerals': 6, 'food': 4},
                'training_time': 120,  # 2 minutes per unit
                'description': 'Fast, powerful cavalry. Dominates infantry and archers.',
                'special': 'High mobility and attack - perfect for raiding and flanking'
            },
            'royal_knights': {
                'attack': 35,
                'def_infantry': 10,
                'def_archers': 8,
                'def_spearmen': 6,
                'def_heavy_knights': 15,
                'def_royal_knights': 20,
                'def_spies': 8,
                'storage': 100,
                'speed': 10,
                'training_cost': {'energy': 15, 'minerals': 12, 'food': 8},
                'training_time': 180,  # 3 minutes per unit
                'description': 'Elite cavalry with highest stats. End-game powerhouse.',
                'special': 'Ultimate offensive unit - expensive but devastating'
            },
            'spies': {
                'attack': 0,
                'def_infantry': 2,
                'def_archers': 2,
                'def_spearmen': 2,
                'def_heavy_knights': 2,
                'def_royal_knights': 2,
                'def_spies': 5,
                'storage': 20,
                'speed': 12,
                'training_cost': {'energy': 10, 'minerals': 5, 'food': 15},
                'training_time': 300,  # 5 minutes per unit
                'description': 'Intelligence units. No combat power, gather information.',
                'special': 'Invisible to regular units - only other spies can detect them'
            },
            'catapult': {
                'attack': 8,
                'def_infantry': 3,
                'def_archers': 3,
                'def_spearmen': 3,
                'def_heavy_knights': 3,
                'def_royal_knights': 3,
                'def_spies': 1,
                'storage': 60,
                'speed': 2,
                'training_cost': {'energy': 20, 'minerals': 25, 'food': 10},
                'training_time': 600,  # 10 minutes per unit
                'description': 'Siege engine. Destroys buildings, weak in combat.',
                'special': 'Building destroyer - essential for late-game conquest'
            },
            'ram': {
                'attack': 15,
                'def_infantry': 5,
                'def_archers': 4,
                'def_spearmen': 6,
                'def_heavy_knights': 4,
                'def_royal_knights': 4,
                'def_spies': 2,
                'storage': 70,
                'speed': 3,
                'training_cost': {'energy': 18, 'minerals': 20, 'food': 8},
                'training_time': 480,  # 8 minutes per unit
                'description': 'Wall-breaker. High defense, targets fortifications.',
                'special': 'Tanky siege unit - breaks walls and gates efficiently'
            },
            'hero': {
                'attack': 20,
                'def_infantry': 12,
                'def_archers': 10,
                'def_spearmen': 14,
                'def_heavy_knights': 10,
                'def_royal_knights': 12,
                'def_spies': 8,
                'storage': 50,
                'speed': 8,
                'training_cost': {'energy': 50, 'minerals': 40, 'food': 30},
                'training_time': 900,  # 15 minutes per unit
                'description': 'Unique leader unit. Gains XP, boosts army morale.',
                'special': 'One per player - levels up and provides army bonuses'
            },
            'healer': {
                'attack': 0,
                'def_infantry': 8,
                'def_archers': 6,
                'def_spearmen': 8,
                'def_heavy_knights': 5,
                'def_royal_knights': 5,
                'def_spies': 6,
                'storage': 30,
                'speed': 6,
                'training_cost': {'energy': 6, 'minerals': 4, 'food': 8},
                'training_time': 120,  # 2 minutes per unit
                'description': 'Non-combat support. Revives fallen troops after battle.',
                'special': 'No attack power - revives 20% of casualties after combat'
            },
            'scout_hawk': {
                'attack': 0,
                'def_infantry': 0,
                'def_archers': 0,
                'def_spearmen': 0,
                'def_heavy_knights': 0,
                'def_royal_knights': 0,
                'def_spies': 0,
                'storage': 15,
                'speed': 15,
                'training_cost': {'energy': 8, 'minerals': 3, 'food': 12},
                'training_time': 90,  # 1.5 minutes per unit
                'description': 'Flying scout. Bypasses all ground units and spies.',
                'special': 'Cannot be attacked - provides deep reconnaissance'
            }
        }
    
    def calculate_travian_combat_strength(self, target_unit_type='infantry'):
        """Calculate combat strength using Travian-style mechanics"""
        stats = self.get_unit_combat_stats()
        unit_stats = stats.get(self.unit_type, stats['infantry'])
        
        # For spies, use special spy attack/defense
        if self.unit_type == 'spy':
            if target_unit_type == 'spy':
                return self.size * unit_stats.get('spy_attack', 5)
            else:
                return 0  # Spies don't fight normal units
        
        # Normal unit attack
        base_attack = unit_stats['attack']
        
        # Research bonuses
        research_bonus = 1.0
        if hasattr(self, 'empire') and self.empire:
            military_research = self.empire.research.filter(research_type='military_tactics').first()
            if military_research:
                research_bonus = 1 + (military_research.level * 0.1)
        
        # Alliance bonuses (10% attack bonus for alliance members)
        alliance_bonus = 1.0
        if hasattr(self, 'empire') and self.empire and self.empire.alliances.exists():
            alliance_bonus = 1.1  # 10% attack bonus for alliance members
        
        return int(self.size * base_attack * research_bonus * alliance_bonus)
    
    def calculate_travian_defense_strength(self, attacker_unit_type='infantry'):
        """Calculate defense strength using Travian-style mechanics"""
        stats = self.get_unit_combat_stats()
        unit_stats = stats.get(self.unit_type, stats['infantry'])
        
        # For spies defending against spies
        if self.unit_type == 'spy' and attacker_unit_type == 'spy':
            return self.size * unit_stats.get('spy_defense', 5)
        elif self.unit_type == 'spy':
            return 0  # Spies don't defend against normal units
        
        # Determine defense type based on attacker
        defense_key = self._get_defense_key(attacker_unit_type)
        base_defense = unit_stats.get(defense_key, unit_stats.get('def_infantry', 30))
        
        # Research bonuses
        research_bonus = 1.0
        if hasattr(self, 'empire') and self.empire:
            defense_research = self.empire.research.filter(research_type='defense_systems').first()
            if defense_research:
                research_bonus = 1 + (defense_research.level * 0.08)
        
        return int(self.size * base_defense * research_bonus)
    
    def _get_defense_key(self, attacker_unit_type):
        """Map attacker unit type to defense key"""
        defense_mapping = {
            'infantry': 'def_infantry',
            'archers': 'def_archer',
            'spearmen': 'def_spearmen',
            'heavy_knights': 'def_heavy_knights',
            'royal_knights': 'def_royal_knights',
            'spies': 'def_spies',
        }
        return defense_mapping.get(attacker_unit_type, 'def_infantry')
    
    def get_unit_attack_vs_target(self, target_unit_type):
        """Calculate this unit's attack effectiveness against target unit type"""
        stats = self.get_unit_combat_stats()
        unit_key = self.unit_type.lower()
        target_key = target_unit_type.lower()
        
        if unit_key not in stats:
            return 40  # Default attack
        
        unit_stats = stats[unit_key]
        base_attack = unit_stats['attack']
        
        # Get effectiveness multiplier
        effectiveness_key = f'vs_{target_key}'
        effectiveness = unit_stats.get(effectiveness_key, 1.0)
        
        # Include research bonuses
        military_research = self.empire.research.filter(research_type='military_tactics').first()
        research_bonus = 1 + (military_research.level * 0.1 if military_research else 0)
        
        return int(base_attack * effectiveness * research_bonus)
    
    def get_unit_defense(self):
        """Calculate this unit's defense value"""
        stats = self.get_unit_combat_stats()
        unit_key = self.unit_type.lower()
        
        if unit_key not in stats:
            return 30  # Default defense
        
        # Get base defense (average of all defense types)
        unit_stats = stats[unit_key]
        base_defense = (unit_stats.get('def_infantry', 0) + 
                       unit_stats.get('def_cavalry', 0) + 
                       unit_stats.get('def_archer', 0)) / 3
        
        # Research bonuses
        research_bonus = 1.0
        if hasattr(self, 'empire') and self.empire:
            defense_research = self.empire.research.filter(research_type='defense_systems').first()
            if defense_research:
                research_bonus = 1 + (defense_research.level * 0.08)
        
        defense_power = base_defense * research_bonus
        
        # Add terrain bonus for defenders
        if hasattr(self, 'territory'):
            defense_power += self.territory.defense_bonus
        
        return defense_power
    
    def get_storage_capacity(self):
        """Get total storage capacity for this army"""
        stats = self.get_unit_combat_stats()
        unit_key = self.unit_type.lower()
        
        if unit_key not in stats:
            return self.size * 50  # Default 50 per unit
        
        per_unit_storage = stats[unit_key]['storage']
        return self.size * per_unit_storage
    
    @staticmethod
    def get_recruitment_time(unit_type, size):
        """Get recruitment time in seconds for unit type and size"""
        # Get time per unit from combat stats
        stats = Army.get_unit_combat_stats()
        if unit_type not in stats:
            return size * 60  # Default 1 minute per unit
        
        time_per_unit = stats[unit_type]['training_time']  # Already in seconds
        return int(size * time_per_unit)


class TerrainMonster(models.Model):
    """Special creatures that guard terrain types"""
    territory = models.ForeignKey(Territory, on_delete=models.CASCADE, related_name='monsters')
    
    monster_type = models.CharField(max_length=30, choices=[
        ('plains_wolves', 'Plains Wolves'),
        ('mountain_giants', 'Mountain Giants'),
        ('desert_scorpions', 'Desert Scorpions'),
        ('forest_treants', 'Forest Treants'),
        ('water_krakens', 'Water Krakens'),
        ('volcanic_dragons', 'Volcanic Dragons'),
    ])
    
    size = models.IntegerField(default=100)  # Number of creatures
    level = models.IntegerField(default=1)   # Monster level affects stats
    respawn_time = models.DateTimeField(null=True, blank=True)  # When monsters respawn
    last_defeated = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.size} {self.get_monster_type_display()} Lv.{self.level}"
    
    @staticmethod
    def get_monster_combat_stats():
        """Get combat statistics for each monster type"""
        return {
            'plains_wolves': {
                'attack': 35,
                'defense': 25,
                'loot_energy': 200,
                'loot_minerals': 100,
                'loot_food': 300,
                'icon': '🐺',
                'description': 'Swift pack hunters that roam the plains',
                # Defense against specific unit types
                'def_vs_infantry': 30,      # 25 * 1.2
                'def_vs_archers': 18,       # 25 * 0.72 (weak vs ranged)
                'def_vs_spearmen': 30,      # 25 * 1.2
                'def_vs_heavy_knights': 20, # 25 * 0.8
                'def_vs_royal_knights': 20, # 25 * 0.8
                'def_vs_spies': 30,         # 25 * 1.2
            },
            'mountain_giants': {
                'attack': 100,
                'defense': 120,
                'loot_energy': 500,
                'loot_minerals': 800,
                'loot_food': 200,
                'icon': '🏔️',
                'description': 'Massive stone beings guarding mineral deposits',
                'def_vs_infantry': 180,      # 120 * 1.5
                'def_vs_archers': 48,        # 120 * 0.4 (very weak vs ranged)
                'def_vs_spearmen': 180,      # 120 * 1.5
                'def_vs_heavy_knights': 156, # 120 * 1.3
                'def_vs_royal_knights': 156, # 120 * 1.3
                'def_vs_spies': 180,         # 120 * 1.5
            },
            'desert_scorpions': {
                'attack': 60,
                'defense': 40,
                'loot_energy': 300,
                'loot_minerals': 600,
                'loot_food': 150,
                'icon': '🦂',
                'description': 'Venomous desert dwellers protecting rare minerals',
                'def_vs_infantry': 56,       # 40 * 1.4
                'def_vs_archers': 24,        # 40 * 0.6 (weak vs ranged)
                'def_vs_spearmen': 56,       # 40 * 1.4
                'def_vs_heavy_knights': 32,  # 40 * 0.8
                'def_vs_royal_knights': 32,  # 40 * 0.8
                'def_vs_spies': 56,          # 40 * 1.4
            },
            'forest_treants': {
                'attack': 70,
                'defense': 90,
                'loot_energy': 400,
                'loot_minerals': 200,
                'loot_food': 700,
                'icon': '🌳',
                'description': 'Ancient tree guardians of the forest',
                'def_vs_infantry': 117,      # 90 * 1.3
                'def_vs_archers': 63,        # 90 * 0.7
                'def_vs_spearmen': 117,      # 90 * 1.3
                'def_vs_heavy_knights': 90,  # 90 * 1.0
                'def_vs_royal_knights': 90,  # 90 * 1.0
                'def_vs_spies': 117,         # 90 * 1.3
            },
            'water_krakens': {
                'attack': 110,
                'defense': 80,
                'loot_energy': 600,
                'loot_minerals': 400,
                'loot_food': 500,
                'icon': '🐙',
                'description': 'Legendary sea beasts ruling the depths',
                'def_vs_infantry': 88,       # 80 * 1.1
                'def_vs_archers': 64,        # 80 * 0.8
                'def_vs_spearmen': 88,       # 80 * 1.1
                'def_vs_heavy_knights': 72,  # 80 * 0.9
                'def_vs_royal_knights': 72,  # 80 * 0.9
                'def_vs_spies': 88,          # 80 * 1.1
            },
            'volcanic_dragons': {
                'attack': 150,
                'defense': 130,
                'loot_energy': 1000,
                'loot_minerals': 600,
                'loot_food': 400,
                'icon': '🐲',
                'description': 'Fearsome dragons of fire and molten rock',
                'def_vs_infantry': 182,      # 130 * 1.4
                'def_vs_archers': 169,       # 130 * 1.3
                'def_vs_spearmen': 182,      # 130 * 1.4
                'def_vs_heavy_knights': 143, # 130 * 1.1
                'def_vs_royal_knights': 143, # 130 * 1.1
                'def_vs_spies': 182,         # 130 * 1.4
            }
        }
    
    def get_combat_strength(self):
        """Calculate monster combat strength"""
        stats = self.get_monster_combat_stats()
        monster_key = self.monster_type
        
        if monster_key not in stats:
            return self.size * 50  # Fallback
        
        monster_stats = stats[monster_key]
        base_attack = monster_stats['attack']
        
        # Level bonus: +10% attack/defense per level
        level_bonus = 1 + (self.level - 1) * 0.1
        
        return int(self.size * base_attack * level_bonus)
    
    def get_defense_strength(self, attacker_unit_type='infantry'):
        """Calculate monster defense strength against specific unit type"""
        stats = self.get_monster_combat_stats()
        monster_key = self.monster_type
        
        if monster_key not in stats:
            return self.size * 40  # Fallback
        
        monster_stats = stats[monster_key]
        
        # Get specific defense value against attacker unit type
        defense_key = f'def_vs_{attacker_unit_type}'
        if defense_key in monster_stats:
            base_defense = monster_stats[defense_key]
        else:
            # Fallback to base defense if specific defense not found
            base_defense = monster_stats['defense']
        
        # Level bonus
        level_bonus = 1 + (self.level - 1) * 0.1
        
        return int(self.size * base_defense * level_bonus)
    
    def get_loot_rewards(self):
        """Calculate loot rewards for defeating these monsters"""
        stats = self.get_monster_combat_stats()
        monster_key = self.monster_type
        
        if monster_key not in stats:
            return {'energy': 0, 'minerals': 0, 'food': 0}
        
        monster_stats = stats[monster_key]
        loot_multiplier = self.size / 100  # Base loot is per 100 monsters
        level_multiplier = 1 + (self.level - 1) * 0.2  # +20% loot per level
        
        return {
            'energy': int(monster_stats['loot_energy'] * loot_multiplier * level_multiplier),
            'minerals': int(monster_stats['loot_minerals'] * loot_multiplier * level_multiplier),
            'food': int(monster_stats['loot_food'] * loot_multiplier * level_multiplier),
        }
    
    def respawn_if_needed(self):
        """Respawn monsters if enough time has passed"""
        if not self.last_defeated or not self.respawn_time:
            return False
        
        if timezone.now() >= self.respawn_time:
            # Respawn with slightly higher level and size variation
            self.size = random.randint(80, 120)  # 80-120 creatures
            if random.random() < 0.3:  # 30% chance to level up
                self.level = min(10, self.level + 1)
            
            self.last_defeated = None
            self.respawn_time = None
            self.save()
            return True
        
        return False


class Battle(models.Model):
    """Battle records with enhanced travel and resource mechanics"""
    attacker = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='attacks')
    defender = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='defenses', null=True, blank=True)
    territory = models.ForeignKey(Territory, on_delete=models.CASCADE, related_name='battles')
    source_territory = models.ForeignKey(Territory, on_delete=models.CASCADE, related_name='outgoing_attacks', null=True, blank=True)
    
    # Monster battle support
    target_monster = models.ForeignKey(TerrainMonster, on_delete=models.CASCADE, null=True, blank=True, related_name='battles')
    
    # Battle timing
    started_at = models.DateTimeField(auto_now_add=True)
    armies_depart = models.DateTimeField(null=True, blank=True)  # When armies leave source
    battle_occurs = models.DateTimeField(null=True, blank=True)  # When battle happens
    armies_return = models.DateTimeField(null=True, blank=True)  # When armies return with loot
    
    # Battle state
    status = models.CharField(max_length=20, choices=[
        ('preparing', 'Preparing'),
        ('traveling', 'Traveling'),
        ('fighting', 'Fighting'),
        ('returning', 'Returning'),
        ('completed', 'Completed'),
    ], default='preparing')
    
    # Battle results
    result = models.CharField(max_length=20, choices=[
        ('attacker_victory', 'Attacker Victory'),
        ('defender_victory', 'Defender Victory'),
        ('draw', 'Draw'),
    ], null=True, blank=True)
    
    # Army data
    attacking_armies = models.JSONField(default=dict)  # Stores army data
    defending_armies = models.JSONField(default=dict)  # Stores defender army data or monster data
    
    # Battle outcomes
    battle_log = models.TextField(blank=True)
    attacker_losses = models.JSONField(default=dict)
    defender_losses = models.JSONField(default=dict)
    resources_captured = models.JSONField(default=dict)  # Resources stolen from defender or monster loot
    
    # Distance and travel time
    distance = models.FloatField(default=0.0)
    travel_time_minutes = models.IntegerField(default=0)
    
    def __str__(self):
        if self.target_monster:
            return f"Battle: {self.attacker.name} vs {self.target_monster} at ({self.territory.x}, {self.territory.y})"
        else:
            return f"Battle: {self.attacker.name} vs {self.defender.name if self.defender else 'Neutral'} at ({self.territory.x}, {self.territory.y})"
    
    def calculate_travel_time(self):
        """Calculate travel time based on distance"""
        if not self.source_territory:
            return 0
        
        self.distance = self.source_territory.calculate_distance(self.territory)
        # Travel time: 1 minute per distance unit, minimum 1 minute, maximum 30 minutes
        self.travel_time_minutes = max(1, min(30, int(self.distance * 2)))
        self.save()
        return self.travel_time_minutes
    
    @transaction.atomic
    def start_attack(self):
        """Initiate the attack sequence"""
        if self.status != 'preparing':
            return False
        
        # Calculate travel time
        travel_time = self.calculate_travel_time()
        
        # Set timing
        now = timezone.now()
        self.armies_depart = now
        self.battle_occurs = now + timezone.timedelta(minutes=travel_time)
        self.armies_return = self.battle_occurs + timezone.timedelta(minutes=travel_time)
        
        self.status = 'traveling'
        self.save()
        return True
    
    @transaction.atomic
    def execute_battle(self):
        """Execute the battle when armies arrive"""
        # Lock the battle record to prevent concurrent execution
        battle = Battle.objects.select_for_update().get(id=self.id)
        
        # Double-check status after lock acquisition
        if battle.status != 'traveling' or timezone.now() < battle.battle_occurs:
            return False
        
        battle.status = 'fighting'
        battle.save()
        
        # Check if this is a monster battle
        if battle.target_monster:
            return battle.execute_monster_battle()
        
        # Regular player vs player battle
        return battle.execute_player_battle()
    
    def _prepare_army_units(self, army_data, empire):
        """Common method to prepare army units for battle calculation"""
        units = []
        for army_id, data in army_data.items():
            unit_type = self._normalize_unit_type(data['unit_type'])
            units.append({
                'id': army_id,
                'type': unit_type,
                'size': data['size'],
                'empire': empire
            })
        return units
    
    def _normalize_unit_type(self, unit_type):
        """Normalize unit type string for combat calculations"""
        unit_type = unit_type.lower().replace(' units', '').replace(' ', '_')
        return unit_type
    
    def _calculate_unit_combat_power(self, unit, target_type=None):
        """Calculate combat power for a unit against a target"""
        combat_stats = Army.get_unit_combat_stats()
        unit_stats = combat_stats.get(unit['type'], combat_stats['infantry'])
        
        # Base attack
        base_attack = unit_stats['attack']
        
        # Effectiveness against target
        effectiveness = 1.0
        if target_type:
            effectiveness = unit_stats.get(f'vs_{target_type}', 1.0)
        
        # Research bonuses
        research_bonus = 1.0
        if unit['empire']:
            military_research = unit['empire'].research.filter(research_type='military_tactics').first()
            if military_research:
                research_bonus = 1 + (military_research.level * 0.1)
        
        # Alliance bonuses (10% attack bonus for alliance members)
        alliance_bonus = 1.0
        if unit['empire'] and unit['empire'].alliances.exists():
            alliance_bonus = 1.1  # 10% attack bonus for alliance members
        
        return base_attack * effectiveness * research_bonus * alliance_bonus
    
    def _calculate_unit_defense_power(self, unit):
        """Calculate defense power for a unit"""
        combat_stats = Army.get_unit_combat_stats()
        unit_stats = combat_stats.get(unit['type'], combat_stats['infantry'])
        
        # Base defense
        base_defense = unit_stats['defense']
        
        # Research bonuses
        research_bonus = 1.0
        if unit['empire']:
            defense_research = unit['empire'].research.filter(research_type='defense_systems').first()
            if defense_research:
                research_bonus = 1 + (defense_research.level * 0.08)
        
        defense_power = base_defense * research_bonus
        
        # Add terrain bonus for defenders
        if hasattr(self, 'territory'):
            defense_power += self.territory.defense_bonus
        
        return defense_power
    
    def _apply_battle_casualties(self, units, casualties):
        """Apply casualties to units and update army data"""
        for unit in units:
            unit_id = unit['id']
            if unit_id in casualties:
                casualty_count = casualties[unit_id]
                unit['size'] -= casualty_count
                
                # Update the corresponding army data
                if unit_id in self.attacking_armies:
                    self.attacking_armies[unit_id]['losses'] = casualty_count
                    self.attacking_armies[unit_id]['survivors'] = max(0, unit['size'])
                elif unit_id in self.defending_armies:
                    self.defending_armies[unit_id]['losses'] = casualty_count
                    self.defending_armies[unit_id]['survivors'] = max(0, unit['size'])
    
    @transaction.atomic
    def execute_monster_battle(self):
        """Execute battle against terrain monsters"""
        # Prepare attacking forces
        attacking_units = self._prepare_army_units(self.attacking_armies, self.attacker)
        
        # Lock and refresh monster data to prevent concurrent modifications
        monster = TerrainMonster.objects.select_for_update().get(id=self.target_monster.id)
        
        # Check if monster is still alive (might have been defeated by another battle)
        if monster.size <= 0:
            self.result = 'defender_victory'  # Monster already defeated
            self.resources_captured = {'energy': 0, 'minerals': 0, 'food': 0}
            self.battle_log = "The monster was already defeated by another player!"
            self.status = 'returning'
            self.save()
            return True
        
        # Prepare monster data
        monster_data = {
            'type': monster.monster_type,
            'size': monster.size,
            'level': monster.level,
            'attack': monster.get_combat_strength(),
            'defense': monster.get_defense_strength()
        }
        
        # Store monster data in defending_armies for report generation
        self.defending_armies = {
            'monster': {
                'unit_type': monster.get_monster_type_display(),
                'size': monster.size,
                'combat_strength': monster_data['attack'],
                'level': monster.level
            }
        }
        
        # Execute monster combat
        battle_result = self.calculate_monster_combat(attacking_units, monster_data)
        
        # Apply results
        self.result = battle_result['result']
        self._apply_battle_casualties(attacking_units, battle_result['attacker_casualties'])
        
        # Update monster data
        if 'monster' in battle_result['defender_casualties']:
            monster_casualties = battle_result['defender_casualties']['monster']
            self.defending_armies['monster']['losses'] = monster_casualties
            self.defending_armies['monster']['survivors'] = max(0, monster_data['size'] - monster_casualties)
        
        # Calculate loss percentages
        self._calculate_loss_percentages()
        
        # Handle monster defeat and loot
        if self.result == 'attacker_victory':
            self.resources_captured = monster.get_loot_rewards()
            self._defeat_monster(monster)
        else:
            self.resources_captured = {'energy': 0, 'minerals': 0, 'food': 0}
        
        # Generate battle log
        self.battle_log = self.generate_battle_report_html()
        
        self.status = 'returning'
        self.save()
        return True
    
    def _defeat_monster(self, monster=None):
        """Handle monster defeat"""
        if monster is None:
            monster = self.target_monster
        
        respawn_hours = random.randint(2, 6)
        monster.last_defeated = timezone.now()
        monster.respawn_time = timezone.now() + timezone.timedelta(hours=respawn_hours)
        monster.size = 0  # Monster is defeated
        monster.save()
    
    def _calculate_loss_percentages(self):
        """Calculate loss percentages for display"""
        # Attacker losses
        total_attacker_units = sum(army['size'] for army in self.attacking_armies.values())
        total_attacker_losses = sum(army.get('losses', 0) for army in self.attacking_armies.values())
        attacker_loss_rate = (total_attacker_losses / total_attacker_units * 100) if total_attacker_units > 0 else 0
        
        # Defender losses
        total_defender_units = sum(army['size'] for army in self.defending_armies.values()) if self.defending_armies else 0
        total_defender_losses = sum(army.get('losses', 0) for army in self.defending_armies.values()) if self.defending_armies else 0
        defender_loss_rate = (total_defender_losses / total_defender_units * 100) if total_defender_units > 0 else 0
        
        self.attacker_losses = {'percentage': int(attacker_loss_rate)}
        self.defender_losses = {'percentage': int(defender_loss_rate)}
    
    @transaction.atomic
    def execute_player_battle(self):
        """Execute battle between players"""
        # Lock territory to prevent concurrent ownership changes
        territory = Territory.objects.select_for_update().get(id=self.territory.id)
        
        # Verify territory ownership hasn't changed during travel time
        if self.defender and territory.owner != self.defender:
            self.result = 'defender_victory'  # Territory changed hands during travel
            self.resources_captured = {'energy': 0, 'minerals': 0, 'food': 0}
            self.battle_log = "Territory ownership changed during travel - attack failed!"
            self.status = 'returning'
            self.save()
            return True
        
        # Prepare forces
        attacking_units = self._prepare_army_units(self.attacking_armies, self.attacker)
        defending_units = self._prepare_army_units(self.defending_armies, self.defender)
        
        # Execute combat
        battle_result = self.calculate_travian_style_combat(attacking_units, defending_units)
        
        # Apply results
        self.result = battle_result['result']
        self._apply_battle_casualties(attacking_units, battle_result['attacker_casualties'])
        self._apply_battle_casualties(defending_units, battle_result['defender_casualties'])
        
        # Calculate loss percentages
        self._calculate_loss_percentages()
        
        # Handle resource raiding (no territory capture)
        if self.result == 'attacker_victory':
            # Capture resources but do NOT change territory ownership
            self.resources_captured = self.calculate_storage_based_capture()
            
            # Safely deduct resources from defender
            if self.defender and sum(self.resources_captured.values()) > 0:
                self._safely_deduct_resources()
        else:
            self.resources_captured = {'energy': 0, 'minerals': 0, 'food': 0}
        
        # Generate battle log
        self.battle_log = self.generate_battle_report_html()
        
        self.status = 'returning'
        self.save()
        return True
    
    def _safely_deduct_resources(self):
        """Safely deduct resources from defender with validation"""
        defender = Empire.objects.select_for_update().get(id=self.defender.id)
        
        # Ensure we don't deduct more than the defender has
        energy_to_deduct = min(self.resources_captured.get('energy', 0), defender.energy)
        minerals_to_deduct = min(self.resources_captured.get('minerals', 0), defender.minerals)
        food_to_deduct = min(self.resources_captured.get('food', 0), defender.food)
        
        # Update captured resources to reflect what was actually taken
        self.resources_captured = {
            'energy': energy_to_deduct,
            'minerals': minerals_to_deduct,
            'food': food_to_deduct
        }
        
        # Deduct resources
        defender.energy = max(0, defender.energy - energy_to_deduct)
        defender.minerals = max(0, defender.minerals - minerals_to_deduct)
        defender.food = max(0, defender.food - food_to_deduct)
        defender.save()
    
    def calculate_travian_style_combat(self, attacking_units, defending_units):
        """Calculate combat using exact Travian mechanics"""
        
        # Separate spies from normal units
        attacking_spies = [unit for unit in attacking_units if unit['type'] == 'spy']
        attacking_normal = [unit for unit in attacking_units if unit['type'] != 'spy']
        defending_spies = [unit for unit in defending_units if unit['type'] == 'spy']
        defending_normal = [unit for unit in defending_units if unit['type'] != 'spy']
        
        # Handle spy battle first (if any spies are involved)
        spy_battle_result = None
        if attacking_spies:
            spy_battle_result = self._handle_spy_battle(attacking_spies, defending_spies)
        
        # Skip normal combat if only spies attacked and defender had no spies
        if not attacking_normal and attacking_spies and not defending_spies:
            # Pure spy mission - no normal combat
            return {
                'result': 'attacker_victory' if spy_battle_result and spy_battle_result['attacker_wins'] else 'defender_victory',
                'attacker_casualties': spy_battle_result['attacker_casualties'] if spy_battle_result else {},
                'defender_casualties': spy_battle_result['defender_casualties'] if spy_battle_result else {},
                'spy_battle': spy_battle_result,
                'is_spy_mission': True
            }
        
        # Normal combat calculation (Travian style)
        attacker_casualties = {}
        defender_casualties = {}
        
        # Calculate total attack and defense strength
        total_attack_strength = 0
        total_defense_strength = 0
        
        # Calculate attacking strength
        for unit in attacking_normal:
            if unit['size'] > 0:
                attack_power = 0
                for defending_unit in defending_normal:
                    if defending_unit['size'] > 0:
                        unit_attack = self._calculate_unit_attack_strength(unit)
                        attack_power += unit_attack
                total_attack_strength += attack_power
        
        # Calculate defending strength
        for unit in defending_normal:
            if unit['size'] > 0:
                defense_power = 0
                for attacking_unit in attacking_normal:
                    if attacking_unit['size'] > 0:
                        unit_defense = self._calculate_unit_defense_strength(unit, attacking_unit['type'])
                        defense_power += unit_defense
                total_defense_strength += defense_power
        
        # Add territory defense bonus
        if hasattr(self, 'territory') and self.territory:
            territory_bonus = self.territory.defense_bonus * 10  # Scale territory bonus
            total_defense_strength += territory_bonus
        
        # Determine battle outcome using Travian formula
        if total_attack_strength > total_defense_strength:
            # Attacker wins
            result = 'attacker_victory'
            
            # Calculate casualties based on strength ratio
            defense_ratio = total_defense_strength / total_attack_strength if total_attack_strength > 0 else 0
            attacker_loss_rate = defense_ratio * 0.5  # Attackers lose based on defense strength
            defender_loss_rate = 1.0  # Defenders lose everything when they lose
            
        elif total_defense_strength > total_attack_strength:
            # Defender wins
            result = 'defender_victory'
            
            # Calculate casualties
            attack_ratio = total_attack_strength / total_defense_strength if total_defense_strength > 0 else 0
            attacker_loss_rate = 1.0  # Attackers lose everything when they lose
            defender_loss_rate = attack_ratio * 0.5  # Defenders lose based on attack strength
            
        else:
            # Draw (very rare)
            result = 'draw'
            attacker_loss_rate = 0.8
            defender_loss_rate = 0.8
        
        # Apply casualties proportionally to each unit
        for unit in attacking_normal:
            if unit['size'] > 0:
                casualties = int(unit['size'] * attacker_loss_rate)
                attacker_casualties[unit['id']] = casualties
                unit['size'] -= casualties
        
        for unit in defending_normal:
            if unit['size'] > 0:
                casualties = int(unit['size'] * defender_loss_rate)
                defender_casualties[unit['id']] = casualties
                unit['size'] -= casualties
        
        # Merge spy casualties if there was a spy battle
        if spy_battle_result:
            attacker_casualties.update(spy_battle_result['attacker_casualties'])
            defender_casualties.update(spy_battle_result['defender_casualties'])
        
        return {
            'result': result,
            'attacker_casualties': attacker_casualties,
            'defender_casualties': defender_casualties,
            'total_attack_strength': total_attack_strength,
            'total_defense_strength': total_defense_strength,
            'spy_battle': spy_battle_result,
            'is_spy_mission': False
        }
    
    def _handle_spy_battle(self, attacking_spies, defending_spies):
        """Handle spy vs spy combat"""
        if not defending_spies:
            # No defending spies - attacking spies succeed automatically
            return {
                'attacker_wins': True,
                'attacker_casualties': {},
                'defender_casualties': {},
                'intelligence_gathered': True,
                'detected': False
            }
        
        # Calculate spy strengths
        attack_spy_strength = sum(spy['size'] * 5 for spy in attacking_spies)  # spy_attack = 5
        defense_spy_strength = sum(spy['size'] * 5 for spy in defending_spies)  # spy_defense = 5
        
        attacker_wins = attack_spy_strength > defense_spy_strength
        
        # Calculate spy casualties (spies always fight to the death)
        spy_attacker_casualties = {}
        spy_defender_casualties = {}
        
        if attacker_wins:
            # Attacking spies win - defending spies die, attackers take some losses
            for spy in defending_spies:
                spy_defender_casualties[spy['id']] = spy['size']
                spy['size'] = 0
            
            # Attacking spies take proportional losses
            loss_rate = min(0.8, defense_spy_strength / attack_spy_strength)
            for spy in attacking_spies:
                casualties = int(spy['size'] * loss_rate)
                spy_attacker_casualties[spy['id']] = casualties
                spy['size'] -= casualties
        else:
            # Defending spies win - attacking spies die, defenders take some losses
            for spy in attacking_spies:
                spy_attacker_casualties[spy['id']] = spy['size']
                spy['size'] = 0
            
            # Defending spies take proportional losses
            loss_rate = min(0.8, attack_spy_strength / defense_spy_strength)
            for spy in defending_spies:
                casualties = int(spy['size'] * loss_rate)
                spy_defender_casualties[spy['id']] = casualties
                spy['size'] -= casualties
        
        return {
            'attacker_wins': attacker_wins,
            'attacker_casualties': spy_attacker_casualties,
            'defender_casualties': spy_defender_casualties,
            'intelligence_gathered': attacker_wins,
            'detected': True,  # Spy battle always reveals the attack
            'attack_spy_strength': attack_spy_strength,
            'defense_spy_strength': defense_spy_strength
        }
    
    def _calculate_unit_attack_strength(self, unit):
        """Calculate a unit's attack strength"""
        stats = Army.get_unit_combat_stats()
        unit_stats = stats.get(unit['type'], stats['infantry'])
        
        base_attack = unit_stats['attack']
        
        research_bonus = 1.0
        if unit['empire']:
            military_research = unit['empire'].research.filter(research_type='military_tactics').first()
            if military_research:
                research_bonus = 1 + (military_research.level * 0.1)
        
        # Alliance bonuses (10% attack bonus for alliance members)
        alliance_bonus = 1.0
        if unit['empire'] and unit['empire'].alliances.exists():
            alliance_bonus = 1.1  # 10% attack bonus for alliance members
        
        return unit['size'] * base_attack * research_bonus * alliance_bonus
    
    def _calculate_unit_defense_strength(self, unit, attacker_type):
        """Calculate a unit's defense strength against specific attacker type"""
        stats = Army.get_unit_combat_stats()
        unit_stats = stats.get(unit['type'], stats['infantry'])
        
        # Get appropriate defense value
        defense_key = self._get_defense_key_for_unit(attacker_type)
        base_defense = unit_stats.get(defense_key, unit_stats.get('def_infantry', 30))
        
        research_bonus = 1.0
        if unit['empire']:
            defense_research = unit['empire'].research.filter(research_type='defense_systems').first()
            if defense_research:
                research_bonus = 1 + (defense_research.level * 0.08)
        
        return unit['size'] * base_defense * research_bonus
    
    def _get_defense_key_for_unit(self, attacker_unit_type):
        """Map attacker unit type to defense key"""
        defense_mapping = {
            'infantry': 'def_infantry',
            'tanks': 'def_cavalry',
            'aircraft': 'def_archer',
            'naval': 'def_cavalry',
            'cyber': 'def_archer',
            'mechs': 'def_cavalry',
            'spy': 'def_infantry'
        }
        return defense_mapping.get(attacker_unit_type, 'def_infantry')
    
    def calculate_storage_based_capture(self):
        """Calculate resource capture based on surviving army storage capacity"""
        if self.result != 'attacker_victory' or not self.defender:
            return {'energy': 0, 'minerals': 0, 'food': 0}
        
        
        # Calculate total storage capacity of surviving attacking armies
        total_storage = 0
        combat_stats = Army.get_unit_combat_stats()
        
        for army_data in self.attacking_armies.values():
            survivors = army_data.get('survivors', 0)
            unit_type = army_data['unit_type'].lower().replace(' units', '').replace(' ', '_')
            
            unit_stats = combat_stats.get(unit_type, {'storage': 50})
            storage_per_unit = unit_stats['storage']
            total_storage += survivors * storage_per_unit
        
        if total_storage <= 0:
            return {'energy': 0, 'minerals': 0, 'food': 0}
        
        # Calculate maximum resources that can be captured (based on storage)
        defender_resources = {
            'energy': self.defender.energy,
            'minerals': self.defender.minerals,
            'food': self.defender.food
        }
        
        # Capture rate: 15-40% of defender's resources, limited by storage
        capture_rate = random.randint(15, 40) / 100
        
        captured = {}
        for resource_type, available in defender_resources.items():
            # Calculate base capture amount
            base_capture = int(available * capture_rate)
            
            # Limit by storage capacity (assume even distribution across resource types)
            storage_limit = total_storage // 3  # Divide storage among 3 resource types
            
            # Take the minimum of what we want to capture and what we can carry
            final_capture = min(base_capture, storage_limit, available)  # Can't capture more than defender has
            captured[resource_type] = max(0, final_capture)  # Ensure non-negative
        
        return captured
    
    @transaction.atomic
    def complete_attack(self):
        """Complete the attack when armies return"""
        # Lock battle to prevent concurrent completion
        battle = Battle.objects.select_for_update().get(id=self.id)
        
        if battle.status != 'returning' or timezone.now() < battle.armies_return:
            return False
        
        # Apply losses to actual Army objects
        for army_id, army_data in battle.attacking_armies.items():
            try:
                army = Army.objects.select_for_update().get(id=army_id)
                army.size = army_data.get('survivors', army.size)
                army.save()
            except Army.DoesNotExist:
                # Skip if army doesn't exist
                pass
        
        # Apply losses to defending armies
        for army_id, army_data in battle.defending_armies.items():
            if army_id == 'monster':  # Skip monster entries
                continue
            try:
                army = Army.objects.select_for_update().get(id=army_id)
                army.size = army_data.get('survivors', army.size)
                army.save()
            except Army.DoesNotExist:
                # Skip if army doesn't exist
                pass
        
        # Give captured resources to attacker
        if battle.result == 'attacker_victory' and battle.resources_captured:
            attacker = Empire.objects.select_for_update().get(id=battle.attacker.id)
            attacker.energy += battle.resources_captured.get('energy', 0)
            attacker.minerals += battle.resources_captured.get('minerals', 0)
            attacker.food += battle.resources_captured.get('food', 0)
            # Ensure resources don't exceed storage capacity
            attacker.enforce_storage_limits()
            attacker.save()
        
        battle.status = 'completed'
        battle.save()
        return True
    
    def generate_battle_report(self):
        """Generate detailed battle report"""
        report = f"""
═══════════════════════════════════════════
        🚀 ATTACK REPORT 🚀
═══════════════════════════════════════════

📍 Target: Territory ({self.territory.x}, {self.territory.y})
🗡️ Attacker: {self.attacker.name}
🛡️ Defender: {self.defender.name if self.defender else 'Unoccupied Territory'}
📏 Distance: {self.distance:.1f} units
⏱️ Travel Time: {self.travel_time_minutes} minutes each way

═══════════════════════════════════════════
        ⚔️ BATTLE OUTCOME ⚔️
═══════════════════════════════════════════

🏆 Result: {self.get_result_display()}

📊 ATTACKING FORCES:
"""
        
        for army_data in self.attacking_armies.values():
            report += f"   • {army_data['unit_type']}: {army_data['size']} units → {army_data['survivors']} survived ({army_data['losses']} casualties)\n"
        
        if self.defending_armies:
            report += "\n📊 DEFENDING FORCES:\n"
            for army_data in self.defending_armies.values():
                report += f"   • {army_data['unit_type']}: {army_data['size']} units → {army_data['survivors']} survived ({army_data['losses']} casualties)\n"
        
        if self.resources_captured and sum(self.resources_captured.values()) > 0:
            report += f"""
═══════════════════════════════════════════
        💰 RESOURCES CAPTURED 💰
═══════════════════════════════════════════

⚡ Energy: {self.resources_captured.get('energy', 0):,}
⛏ Minerals: {self.resources_captured.get('minerals', 0):,}
🌾 Food: {self.resources_captured.get('food', 0):,}

Total Value: {sum(self.resources_captured.values()):,} resources
"""
        
        report += f"""
═══════════════════════════════════════════
        📈 STATISTICS 📈
═══════════════════════════════════════════

🔥 Attacker Losses: {self.attacker_losses.get('percentage', 0)}%
🛡️ Defender Losses: {self.defender_losses.get('percentage', 0)}%

Battle completed at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
═══════════════════════════════════════════
"""
        return report
    
    def generate_battle_report_html(self):
        """Generate HTML battle report like Travian with tables and spy information"""
        unit_icons = {
            'infantry': '🪖',
            'archers': '🏹',
            'spearmen': '🔱',
            'heavy_knights': '🐎',
            'royal_knights': '👑',
            'spies': '🕵️',
            'catapult': '🏰',
            'ram': '🛡️',
            'hero': '🧙',
            'healer': '🧑‍⚕️',
            'scout_hawk': '🦅'
        }
        
        result_color = '#44ff44' if self.result == 'attacker_victory' else '#ff4444' if self.result == 'defender_victory' else '#ffaa00'
        result_icon = '🏆' if self.result == 'attacker_victory' else '🛡️' if self.result == 'defender_victory' else '⚔️'
        
        # Check if this was a spy mission
        is_spy_mission = hasattr(self, 'spy_battle_info') and self.spy_battle_info.get('is_spy_mission', False)
        
        html = f"""
        <div style="font-family: monospace; background: linear-gradient(145deg, #1a1a1a, #2a2a2a); border: 2px solid {result_color}; border-radius: 10px; padding: 20px; margin: 10px 0; max-width: 800px;">
            <!-- Header -->
            <div style="text-align: center; margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 15px;">
                <h2 style="color: {result_color}; margin: 0; font-size: 18px;">{result_icon} {'SPY REPORT' if is_spy_mission else 'BATTLE REPORT'} {result_icon}</h2>
                <div style="color: #aaa; font-size: 12px; margin-top: 5px;">
                    Territory ({self.territory.x}, {self.territory.y}) • {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
                {f'<div style="color: #ff8800; font-size: 11px; margin-top: 3px;">🕵️ INTELLIGENCE OPERATION</div>' if is_spy_mission else ''}
            </div>
            
            <!-- Battle Info -->
            <table style="width: 100%; margin-bottom: 20px; border-collapse: collapse; background: rgba(255,255,255,0.05); border: 1px solid #666;">
                <tr>
                    <td style="border: 1px solid #666; padding: 8px; color: #ffaa00; font-weight: bold;">🗡️ Attacker:</td>
                    <td style="border: 1px solid #666; padding: 8px; color: #fff;">{self.attacker.name}{' 🤖' if self.attacker.is_master_player else ''}</td>
                    <td style="border: 1px solid #666; padding: 8px; color: #ffaa00; font-weight: bold;">📏 Distance:</td>
                    <td style="border: 1px solid #666; padding: 8px; color: #fff;">{self.distance:.1f} units</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #666; padding: 8px; color: #ffaa00; font-weight: bold;">🛡️ Defender:</td>
                    <td style="border: 1px solid #666; padding: 8px; color: #fff;">{self.defender.name if self.defender else 'Unoccupied Territory'}{' 🤖' if self.defender and self.defender.is_master_player else ''}</td>
                    <td style="border: 1px solid #666; padding: 8px; color: #ffaa00; font-weight: bold;">🏆 Result:</td>
                    <td style="border: 1px solid #666; padding: 8px; color: {result_color}; font-weight: bold;">{self.get_result_display()}</td>
                </tr>
            </table>
        """
        
        # Add spy battle information if present
        if hasattr(self, 'spy_battle_info') and self.spy_battle_info:
            spy_info = self.spy_battle_info
            html += f"""
            <!-- Spy Battle Results -->
            <div style="margin-bottom: 20px;">
                <h3 style="color: #ff8800; margin-bottom: 10px; font-size: 14px; text-align: center; background: rgba(255,136,0,0.2); padding: 8px; border: 1px solid #ff8800;">🕵️ ESPIONAGE RESULTS</h3>
                <table style="width: 100%; border-collapse: collapse; border: 2px solid #ff8800;">
                    <tr style="background: rgba(255,136,0,0.3);">
                        <td style="border: 1px solid #ff8800; padding: 10px; color: #ff8800; font-weight: bold;">Intelligence Gathered:</td>
                        <td style="border: 1px solid #ff8800; padding: 10px; color: {'#44ff44' if spy_info.get('intelligence_gathered') else '#ff4444'}; font-weight: bold;">
                            {'✅ SUCCESS' if spy_info.get('intelligence_gathered') else '❌ FAILED'}
                        </td>
                    </tr>
                    <tr style="background: rgba(255,136,0,0.1);">
                        <td style="border: 1px solid #ff8800; padding: 10px; color: #ff8800; font-weight: bold;">Mission Detected:</td>
                        <td style="border: 1px solid #ff8800; padding: 10px; color: {'#ff4444' if spy_info.get('detected') else '#44ff44'}; font-weight: bold;">
                            {'🚨 DETECTED' if spy_info.get('detected') else '🤫 STEALTHY'}
                        </td>
                    </tr>
                </table>
            </div>
            """
            
            # Show intelligence data if gathered successfully
            if spy_info.get('intelligence_gathered') and spy_info.get('enemy_intelligence'):
                intel = spy_info['enemy_intelligence']
                html += f"""
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #44ff44; margin-bottom: 10px; font-size: 14px; text-align: center; background: rgba(68,255,68,0.2); padding: 8px; border: 1px solid #44ff44;">📊 ENEMY INTELLIGENCE</h3>
                    <table style="width: 100%; border-collapse: collapse; border: 2px solid #44ff44;">
                        <tr style="background: rgba(68,255,68,0.2);">
                            <th style="border: 1px solid #44ff44; padding: 8px; color: #44ff44;">Resources</th>
                            <th style="border: 1px solid #44ff44; padding: 8px; color: #44ff44;">Military Forces</th>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #44ff44; padding: 10px; color: #fff; vertical-align: top;">
                                ⚡ Energy: {intel.get('energy', 'Unknown'):,}<br>
                                ⛏ Minerals: {intel.get('minerals', 'Unknown'):,}<br>
                                🌾 Food: {intel.get('food', 'Unknown'):,}
                            </td>
                            <td style="border: 1px solid #44ff44; padding: 10px; color: #fff; vertical-align: top;">
                """
                
                if intel.get('armies'):
                    for army_info in intel['armies']:
                        unit_icon = unit_icons.get(army_info['type'].lower(), '⚔️')
                        html += f"{unit_icon} {army_info['type']}: {army_info['size']:,}<br>"
                else:
                    html += "No military intelligence gathered"
                
                html += """
                            </td>
                        </tr>
                    </table>
                </div>
                """
        
        # Continue with normal battle forces display...
        if not is_spy_mission:
            # Show attacking forces
            html += f"""
            <!-- Attacker Forces Table -->
            <div style="margin-bottom: 20px;">
                <h3 style="color: #ff4444; margin-bottom: 10px; font-size: 14px; text-align: center; background: rgba(255,68,68,0.2); padding: 8px; border: 1px solid #ff4444;">⚔️ ATTACKER FORCES</h3>
                <table style="width: 100%; border-collapse: collapse; border: 2px solid #ff4444;">
                    <thead>
                        <tr style="background: rgba(255,68,68,0.3);">
                            <th style="border: 1px solid #ff4444; padding: 10px; color: #ff4444; text-align: left; font-weight: bold;">Unit Type</th>
                            <th style="border: 1px solid #ff4444; padding: 10px; color: #ff4444; text-align: center; font-weight: bold;">Initial</th>
                            <th style="border: 1px solid #ff4444; padding: 10px; color: #ff4444; text-align: center; font-weight: bold;">Losses</th>
                            <th style="border: 1px solid #ff4444; padding: 10px; color: #ff4444; text-align: center; font-weight: bold;">Survivors</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            # Show attacker forces
            if self.attacking_armies:
                for army_data in self.attacking_armies.values():
                    unit_type = army_data['unit_type']
                    unit_key = unit_type.lower().replace(' units', '').replace(' ', '_')
                    icon = unit_icons.get(unit_key, '⚔️')
                    html += f"""
                            <tr style="background: rgba(255,68,68,0.1);">
                                <td style="border: 1px solid #ff4444; padding: 10px; color: #fff; font-weight: bold;">{icon} {unit_type}</td>
                                <td style="border: 1px solid #ff4444; padding: 10px; color: #fff; text-align: center; font-size: 14px;">{army_data['size']:,}</td>
                                <td style="border: 1px solid #ff4444; padding: 10px; color: #ff4444; text-align: center; font-weight: bold; font-size: 14px;">{army_data.get('losses', 0):,}</td>
                                <td style="border: 1px solid #ff4444; padding: 10px; color: #44ff44; text-align: center; font-weight: bold; font-size: 14px;">{army_data.get('survivors', 0):,}</td>
                            </tr>
                    """
            
            html += """
                    </tbody>
                </table>
            </div>
            """
            
            # Show defending forces (if any)
            if self.defending_armies:
                html += f"""
                <div style="margin-bottom: 20px;">
                    <h3 style="color: #44ff44; margin-bottom: 10px; font-size: 14px; text-align: center; background: rgba(68,255,68,0.2); padding: 8px; border: 1px solid #44ff44;">🛡️ DEFENDER FORCES</h3>
                    <table style="width: 100%; border-collapse: collapse; border: 2px solid #44ff44;">
                        <thead>
                            <tr style="background: rgba(68,255,68,0.3);">
                                <th style="border: 1px solid #44ff44; padding: 10px; color: #44ff44; text-align: left; font-weight: bold;">Unit Type</th>
                                <th style="border: 1px solid #44ff44; padding: 10px; color: #44ff44; text-align: center; font-weight: bold;">Initial</th>
                                <th style="border: 1px solid #44ff44; padding: 10px; color: #44ff44; text-align: center; font-weight: bold;">Losses</th>
                                <th style="border: 1px solid #44ff44; padding: 10px; color: #44ff44; text-align: center; font-weight: bold;">Survivors</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                for army_data in self.defending_armies.values():
                    unit_type = army_data['unit_type']
                    unit_key = unit_type.lower().replace(' units', '').replace(' ', '_')
                    icon = unit_icons.get(unit_key, '🛡️')
                    html += f"""
                            <tr style="background: rgba(68,255,68,0.1);">
                                <td style="border: 1px solid #44ff44; padding: 10px; color: #fff; font-weight: bold;">{icon} {unit_type}</td>
                                <td style="border: 1px solid #44ff44; padding: 10px; color: #fff; text-align: center; font-size: 14px;">{army_data['size']:,}</td>
                                <td style="border: 1px solid #44ff44; padding: 10px; color: #ff4444; text-align: center; font-weight: bold; font-size: 14px;">{army_data.get('losses', 0):,}</td>
                                <td style="border: 1px solid #44ff44; padding: 10px; color: #44ff44; text-align: center; font-weight: bold; font-size: 14px;">{army_data.get('survivors', 0):,}</td>
                            </tr>
                """
                
                html += """
                        </tbody>
                    </table>
                </div>
                """
        
        # Resources captured section (only for successful attacks)
        if self.resources_captured and sum(self.resources_captured.values()) > 0:
            total_captured = sum(self.resources_captured.values())
            html += f"""
            <div style="margin-bottom: 20px;">
                <h3 style="color: #ffaa00; margin-bottom: 10px; font-size: 16px; text-align: center; background: rgba(255,170,0,0.3); padding: 12px; border: 2px solid #ffaa00; border-radius: 5px;">💰 RESOURCES CAPTURED 💰</h3>
                <table style="width: 100%; border-collapse: collapse; border: 2px solid #ffaa00;">
                    <thead>
                        <tr style="background: rgba(255,170,0,0.3);">
                            <th style="border: 1px solid #ffaa00; padding: 12px; color: #ffaa00; text-align: center; font-weight: bold; font-size: 14px;">⚡ Energy</th>
                            <th style="border: 1px solid #ffaa00; padding: 12px; color: #ffaa00; text-align: center; font-weight: bold; font-size: 14px;">⛏ Minerals</th>
                            <th style="border: 1px solid #ffaa00; padding: 12px; color: #ffaa00; text-align: center; font-weight: bold; font-size: 14px;">🌾 Food</th>
                            <th style="border: 1px solid #ffaa00; padding: 12px; color: #ffaa00; text-align: center; font-weight: bold; font-size: 14px;">💎 Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="background: rgba(255,170,0,0.1);">
                            <td style="border: 1px solid #ffaa00; padding: 15px; color: #44ff44; text-align: center; font-weight: bold; font-size: 18px;">{self.resources_captured.get('energy', 0):,}</td>
                            <td style="border: 1px solid #ffaa00; padding: 15px; color: #44ff44; text-align: center; font-weight: bold; font-size: 18px;">{self.resources_captured.get('minerals', 0):,}</td>
                            <td style="border: 1px solid #ffaa00; padding: 15px; color: #44ff44; text-align: center; font-weight: bold; font-size: 18px;">{self.resources_captured.get('food', 0):,}</td>
                            <td style="border: 1px solid #ffaa00; padding: 15px; color: #ffaa00; text-align: center; font-weight: bold; font-size: 20px; background: rgba(255,170,0,0.2);">{total_captured:,}</td>
                        </tr>
                    </tbody>
                </table>
                <div style="text-align: center; margin-top: 10px; color: #44ff44; font-weight: bold; font-size: 14px;">
                    🎉 Successfully captured {total_captured:,} resources! 🎉
                </div>
            </div>
            """
        
        # Battle statistics (only for normal battles)
        if not is_spy_mission:
            html += f"""
            <div style="margin-bottom: 10px;">
                <h3 style="color: #00aaff; margin-bottom: 10px; font-size: 14px; text-align: center; background: rgba(0,170,255,0.2); padding: 8px; border: 1px solid #00aaff;">📊 BATTLE STATISTICS</h3>
                <table style="width: 100%; border-collapse: collapse; border: 2px solid #00aaff;">
                    <thead>
                        <tr style="background: rgba(0,170,255,0.3);">
                            <th style="border: 1px solid #00aaff; padding: 10px; color: #00aaff; text-align: center; font-weight: bold;">🔥 Attacker Losses</th>
                            <th style="border: 1px solid #00aaff; padding: 10px; color: #00aaff; text-align: center; font-weight: bold;">🛡️ Defender Losses</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr style="background: rgba(0,170,255,0.1);">
                            <td style="border: 1px solid #00aaff; padding: 10px; color: #ff4444; text-align: center; font-weight: bold; font-size: 16px;">{self.attacker_losses.get('percentage', 0)}%</td>
                            <td style="border: 1px solid #00aaff; padding: 10px; color: #44ff44; text-align: center; font-weight: bold; font-size: 16px;">{self.defender_losses.get('percentage', 0)}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            """
        
        html += """
        </div>
        """
        
        return html

    def calculate_monster_combat(self, attacking_units, monster_data):
        """Calculate combat between players and terrain monsters"""
        # Initialize casualties
        attacker_casualties = {}
        
        # Get combat stats and monster stats
        combat_stats = Army.get_unit_combat_stats()
        monster_stats = TerrainMonster.get_monster_combat_stats()
        monster_type = monster_data['type']
        monster_info = monster_stats.get(monster_type, monster_stats['plains_wolves'])
        
        # Monster combat is different - monsters are tough but predictable
        total_attacker_strength = 0
        for attacker in attacking_units:
            if attacker['size'] <= 0:
                continue
            
            attacker_type = attacker['type']
            attacker_stats = combat_stats.get(attacker_type, combat_stats['infantry'])
            
            # Calculate this unit's contribution
            base_attack = attacker_stats['attack']
            
            # Research bonuses
            military_research = attacker['empire'].research.filter(research_type='military_tactics').first() if attacker['empire'] else None
            research_bonus = 1 + (military_research.level * 0.1 if military_research else 0)
            
            unit_strength = base_attack * research_bonus * attacker['size']
            total_attacker_strength += unit_strength
        
        # Monster defense calculation - use specific defense against each unit type
        total_monster_defense = 0
        for attacker in attacking_units:
            if attacker['size'] <= 0:
                continue
            
            attacker_type = attacker['type']
            # Get specific defense value against this unit type
            defense_key = f'def_vs_{attacker_type}'
            if defense_key in monster_info:
                unit_defense = monster_info[defense_key]
            else:
                # Fallback to base defense
                unit_defense = monster_info['defense']
            
            # Calculate defense against this specific unit type
            unit_monster_defense = unit_defense * attacker['size']
            total_monster_defense += unit_monster_defense
        
        # Level bonus for monsters
        level_bonus = 1 + (monster_data['level'] - 1) * 0.15  # Monsters get stronger per level
        total_monster_defense *= level_bonus
        
        # Add terrain bonus for monsters (they know their home)
        terrain_bonus = {'plains': 1.0, 'mountains': 1.3, 'desert': 1.1, 'forest': 1.2, 'water': 1.4, 'volcanic': 1.5}
        terrain_type = self.territory.terrain_type
        total_monster_defense *= terrain_bonus.get(terrain_type, 1.0)
        
        # Battle resolution - monsters fight differently than players
        attack_roll = random.uniform(0.8, 1.2)  # 80-120% variance
        defense_roll = random.uniform(0.9, 1.1)  # Monsters more consistent
        
        final_attack = total_attacker_strength * attack_roll
        final_defense = total_monster_defense * defense_roll
        
        # Determine winner
        if final_attack > final_defense:
            result = 'attacker_victory'
            # Monster defeated - calculate player casualties (10-40%)
            casualty_rate = random.uniform(0.1, 0.4)
            # Monster completely defeated
            monster_casualties = monster_data['size']
        else:
            result = 'defender_victory'
            # Players defeated - heavy casualties (40-80%)
            casualty_rate = random.uniform(0.4, 0.8)
            # Monster takes light damage (10-30%)
            monster_casualties = int(monster_data['size'] * random.uniform(0.1, 0.3))
        
        # Apply casualties to attacking armies proportionally
        for attacker in attacking_units:
            if attacker['size'] <= 0:
                continue
            
            casualties = int(attacker['size'] * casualty_rate)
            attacker_casualties[attacker['id']] = casualties
            attacker['size'] -= casualties
        
        # Calculate remaining forces
        attacker_remaining = sum(unit['size'] for unit in attacking_units)
        monster_remaining = monster_data['size'] - monster_casualties
        
        return {
            'result': result,
            'attacker_casualties': attacker_casualties,
            'defender_casualties': {'monster': monster_casualties},
            'attacker_remaining': attacker_remaining,
            'defender_remaining': monster_remaining,
            'total_attack_strength': total_attacker_strength,
            'monster_defense_strength': total_monster_defense
        }


class Alliance(models.Model):
    """Player alliances with enhanced warfare capabilities"""
    name = models.CharField(max_length=100)
    leader = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='led_alliances')
    members = models.ManyToManyField(Empire, related_name='alliances', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    description = models.TextField(blank=True)
    is_open = models.BooleanField(default=True)
    
    # Alliance warfare enhancements
    treasury_energy = models.IntegerField(default=0)
    treasury_minerals = models.IntegerField(default=0)
    treasury_food = models.IntegerField(default=0)
    
    # Alliance perks
    defense_bonus = models.IntegerField(default=0)  # % defense bonus for all members
    production_bonus = models.IntegerField(default=0)  # % production bonus
    research_bonus = models.IntegerField(default=0)  # % research speed bonus
    
    # Alliance warfare status
    war_declarations = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='at_war_with')
    non_aggression_pacts = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='peace_with')
    
    # Alliance statistics
    total_power = models.IntegerField(default=0)
    total_territories = models.IntegerField(default=0)
    total_battles_won = models.IntegerField(default=0)
    total_battles_lost = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name
    
    def calculate_total_power(self):
        """Calculate total alliance power"""
        self.total_power = sum(member.power_level for member in self.members.all())
        self.total_territories = sum(member.territories.count() for member in self.members.all())
        self.save()
        return self.total_power
    
    def is_at_war_with(self, other_alliance):
        """Check if alliance is at war with another"""
        return other_alliance in self.war_declarations.all()
    
    def has_non_aggression_pact_with(self, other_alliance):
        """Check if alliance has non-aggression pact"""
        return other_alliance in self.non_aggression_pacts.all()
    
    def can_attack_empire(self, attacker_empire, target_empire):
        """Check if alliance member can attack target based on alliance rules"""
        attacker_alliances = attacker_empire.alliances.all()
        target_alliances = target_empire.alliances.all()
        
        # Check for non-aggression pacts
        for attacker_alliance in attacker_alliances:
            for target_alliance in target_alliances:
                if attacker_alliance.has_non_aggression_pact_with(target_alliance):
                    return False, "Non-aggression pact prevents attack"
        
        # Check for war declarations
        for attacker_alliance in attacker_alliances:
            for target_alliance in target_alliances:
                if attacker_alliance.is_at_war_with(target_alliance):
                    return True, "War declaration allows attack"
        
        return True, "No restrictions"
    
    def add_to_treasury(self, energy=0, minerals=0, food=0):
        """Add resources to alliance treasury"""
        self.treasury_energy += energy
        self.treasury_minerals += minerals
        self.treasury_food += food
        self.save()
    
    def distribute_bonus_resources(self):
        """Distribute treasury resources to members"""
        if self.members.count() == 0:
            return
        
        energy_per_member = self.treasury_energy // self.members.count()
        minerals_per_member = self.treasury_minerals // self.members.count()
        food_per_member = self.treasury_food // self.members.count()
        
        for member in self.members.all():
            member.energy += energy_per_member
            member.minerals += minerals_per_member
            member.food += food_per_member
            member.save()
        
        self.treasury_energy = 0
        self.treasury_minerals = 0
        self.treasury_food = 0
        self.save()


class TradeOffer(models.Model):
    """Trading system between players"""
    sender = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='sent_trades')
    receiver = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='received_trades')
    
    # What sender is offering
    offer_energy = models.IntegerField(default=0)
    offer_minerals = models.IntegerField(default=0)
    offer_food = models.IntegerField(default=0)
    
    # What sender wants in return
    request_energy = models.IntegerField(default=0)
    request_minerals = models.IntegerField(default=0)
    request_food = models.IntegerField(default=0)
    
    # Trade status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ], default='pending')
    
    # Trade details
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"Trade: {self.sender.name} → {self.receiver.name}"
    
    def is_expired(self):
        """Check if trade offer has expired"""
        return timezone.now() > self.expires_at
    
    def can_complete(self):
        """Check if both parties can complete the trade"""
        sender_can_afford = (
            self.sender.energy >= self.offer_energy and
            self.sender.minerals >= self.offer_minerals and
            self.sender.food >= self.offer_food
        )
        
        receiver_can_afford = (
            self.receiver.energy >= self.request_energy and
            self.receiver.minerals >= self.request_minerals and
            self.receiver.food >= self.request_food
        )
        
        return sender_can_afford and receiver_can_afford
    
    @transaction.atomic
    def execute_trade(self):
        """Execute the trade between parties"""
        if not self.can_complete():
            return False, "Insufficient resources"
        
        # Lock both empires
        sender = Empire.objects.select_for_update().get(id=self.sender.id)
        receiver = Empire.objects.select_for_update().get(id=self.receiver.id)
        
        # Deduct from sender
        sender.energy -= self.offer_energy
        sender.minerals -= self.offer_minerals
        sender.food -= self.offer_food
        
        # Deduct from receiver
        receiver.energy -= self.request_energy
        receiver.minerals -= self.request_minerals
        receiver.food -= self.request_food
        
        # Add to receiver
        receiver.energy += self.offer_energy
        receiver.minerals += self.offer_minerals
        receiver.food += self.offer_food
        
        # Add to sender
        sender.energy += self.request_energy
        sender.minerals += self.request_minerals
        sender.food += self.request_food
        
        # Save both empires
        sender.save()
        receiver.save()
        
        # Update trade status
        self.status = 'completed'
        self.responded_at = timezone.now()
        self.save()
        
        return True, "Trade completed successfully"


class Tournament(models.Model):
    """Competitive tournaments"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    tournament_type = models.CharField(max_length=20, choices=[
        ('power_ranking', 'Power Ranking'),
        ('resource_gathering', 'Resource Gathering'),
        ('battle_royale', 'Battle Royale'),
        ('alliance_war', 'Alliance War'),
    ])
    
    # Tournament timing
    registration_start = models.DateTimeField()
    registration_end = models.DateTimeField()
    tournament_start = models.DateTimeField()
    tournament_end = models.DateTimeField()
    
    # Tournament settings
    max_participants = models.IntegerField(default=100)
    entry_fee_energy = models.IntegerField(default=0)
    entry_fee_minerals = models.IntegerField(default=0)
    entry_fee_food = models.IntegerField(default=0)
    
    # Rewards
    first_place_energy = models.IntegerField(default=0)
    first_place_minerals = models.IntegerField(default=0)
    first_place_food = models.IntegerField(default=0)
    
    second_place_energy = models.IntegerField(default=0)
    second_place_minerals = models.IntegerField(default=0)
    second_place_food = models.IntegerField(default=0)
    
    third_place_energy = models.IntegerField(default=0)
    third_place_minerals = models.IntegerField(default=0)
    third_place_food = models.IntegerField(default=0)
    
    # Tournament status
    is_active = models.BooleanField(default=True)
    participants = models.ManyToManyField(Empire, related_name='tournaments', blank=True)
    
    def __str__(self):
        return self.name
    
    def can_register(self, empire):
        """Check if empire can register for tournament"""
        now = timezone.now()
        
        if now < self.registration_start or now > self.registration_end:
            return False, "Registration period closed"
        
        if self.participants.count() >= self.max_participants:
            return False, "Tournament full"
        
        if empire in self.participants.all():
            return False, "Already registered"
        
        # Check entry fee
        if (empire.energy < self.entry_fee_energy or 
            empire.minerals < self.entry_fee_minerals or 
            empire.food < self.entry_fee_food):
            return False, "Cannot afford entry fee"
        
        return True, "Can register"
    
    def register_participant(self, empire):
        """Register empire for tournament"""
        can_register, message = self.can_register(empire)
        if not can_register:
            return False, message
        
        # Deduct entry fee
        empire.energy -= self.entry_fee_energy
        empire.minerals -= self.entry_fee_minerals
        empire.food -= self.entry_fee_food
        empire.save()
        
        self.participants.add(empire)
        return True, "Registration successful"


class Achievement(models.Model):
    """Achievement system"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    achievement_type = models.CharField(max_length=20, choices=[
        ('territory', 'Territory'),
        ('battle', 'Battle'),
        ('building', 'Building'),
        ('research', 'Research'),
        ('alliance', 'Alliance'),
        ('economy', 'Economy'),
        ('special', 'Special'),
    ])
    
    # Achievement criteria
    criteria_json = models.JSONField(default=dict)  # Flexible criteria storage
    
    # Rewards
    reward_energy = models.IntegerField(default=0)
    reward_minerals = models.IntegerField(default=0)
    reward_food = models.IntegerField(default=0)
    reward_technology = models.IntegerField(default=0)
    
    # Achievement properties
    is_secret = models.BooleanField(default=False)
    is_repeatable = models.BooleanField(default=False)
    difficulty = models.CharField(max_length=10, choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('legendary', 'Legendary'),
    ], default='medium')
    
    # Achievement icon and display
    icon = models.CharField(max_length=10, default='🏆')
    
    def __str__(self):
        return self.name
    
    def check_criteria(self, empire):
        """Check if empire meets achievement criteria"""
        criteria = self.criteria_json
        
        if self.achievement_type == 'territory':
            territory_count = empire.territories.count()
            if criteria.get('min_territories', 0) <= territory_count:
                return True
        
        elif self.achievement_type == 'battle':
            battles_won = Battle.objects.filter(
                attacker=empire,
                result='attacker_victory'
            ).count()
            if criteria.get('min_battles_won', 0) <= battles_won:
                return True
        
        elif self.achievement_type == 'building':
            buildings_count = empire.buildings.count()
            if criteria.get('min_buildings', 0) <= buildings_count:
                return True
        
        elif self.achievement_type == 'research':
            research_levels = sum(r.level for r in empire.research.all())
            if criteria.get('min_research_levels', 0) <= research_levels:
                return True
        
        elif self.achievement_type == 'alliance':
            alliance_count = empire.alliances.count()
            if criteria.get('min_alliances', 0) <= alliance_count:
                return True
        
        elif self.achievement_type == 'economy':
            total_resources = empire.energy + empire.minerals + empire.food
            if criteria.get('min_resources', 0) <= total_resources:
                return True
        
        return False
    
    def award_to_empire(self, empire):
        """Award achievement to empire"""
        # Create achievement record
        EmpireAchievement.objects.get_or_create(
            empire=empire,
            achievement=self,
            defaults={'earned_at': timezone.now()}
        )
        
        # Award rewards
        empire.energy += self.reward_energy
        empire.minerals += self.reward_minerals
        empire.food += self.reward_food
        empire.technology += self.reward_technology
        # Ensure resources don't exceed storage capacity
        empire.enforce_storage_limits()
        empire.save()


class EmpireAchievement(models.Model):
    """Track which achievements empires have earned"""
    empire = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('empire', 'achievement')
    
    def __str__(self):
        return f"{self.empire.name} - {self.achievement.name}"


class ResearchPrerequisite(models.Model):
    """Research prerequisites system"""
    research_type = models.CharField(max_length=30, choices=[
        ('energy_efficiency', 'Energy Efficiency'),
        ('mining_technology', 'Mining Technology'),
        ('agriculture', 'Agriculture'),
        ('military_tactics', 'Military Tactics'),
        ('defense_systems', 'Defense Systems'),
        ('espionage', 'Espionage'),
        ('space_travel', 'Space Travel'),
        ('artificial_intelligence', 'Artificial Intelligence'),
        ('quantum_computing', 'Quantum Computing'),
        ('advanced_materials', 'Advanced Materials'),
        ('fusion_power', 'Fusion Power'),
        ('nanotechnology', 'Nanotechnology'),
        ('biotechnology', 'Biotechnology'),
        ('cybernetics', 'Cybernetics'),
    ])
    
    prerequisite_research = models.CharField(max_length=30, choices=[
        ('energy_efficiency', 'Energy Efficiency'),
        ('mining_technology', 'Mining Technology'),
        ('agriculture', 'Agriculture'),
        ('military_tactics', 'Military Tactics'),
        ('defense_systems', 'Defense Systems'),
        ('espionage', 'Espionage'),
        ('space_travel', 'Space Travel'),
        ('artificial_intelligence', 'Artificial Intelligence'),
        ('quantum_computing', 'Quantum Computing'),
        ('advanced_materials', 'Advanced Materials'),
        ('fusion_power', 'Fusion Power'),
        ('nanotechnology', 'Nanotechnology'),
        ('biotechnology', 'Biotechnology'),
        ('cybernetics', 'Cybernetics'),
    ])
    
    required_level = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.research_type} requires {self.prerequisite_research} Lv.{self.required_level}"
    
    @staticmethod
    def check_prerequisites(empire, research_type):
        """Check if empire meets prerequisites for research"""
        prerequisites = ResearchPrerequisite.objects.filter(research_type=research_type)
        
        for prereq in prerequisites:
            empire_research = empire.research.filter(
                research_type=prereq.prerequisite_research
            ).first()
            
            if not empire_research or empire_research.level < prereq.required_level:
                return False, f"Requires {prereq.prerequisite_research} Lv.{prereq.required_level}"
        
        return True, "Prerequisites met"


class DiplomaticRelation(models.Model):
    """Enhanced diplomatic relations between empires"""
    empire_a = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='diplomatic_relations_a')
    empire_b = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='diplomatic_relations_b')
    
    relation_type = models.CharField(max_length=20, choices=[
        ('neutral', 'Neutral'),
        ('friendly', 'Friendly'),
        ('allied', 'Allied'),
        ('hostile', 'Hostile'),
        ('at_war', 'At War'),
        ('non_aggression', 'Non-Aggression Pact'),
        ('trade_agreement', 'Trade Agreement'),
    ], default='neutral')
    
    # Diplomatic modifiers
    trust_level = models.IntegerField(default=0)  # -100 to +100
    trade_modifier = models.FloatField(default=1.0)  # Trade cost multiplier
    
    # Diplomatic history
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Automatic expiration
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('empire_a', 'empire_b')
    
    def __str__(self):
        return f"{self.empire_a.name} - {self.empire_b.name}: {self.relation_type}"
    
    def can_attack(self):
        """Check if empires can attack each other"""
        if self.relation_type in ['allied', 'non_aggression', 'trade_agreement']:
            return False
        return True
    
    def get_trade_cost_modifier(self):
        """Get trade cost modifier based on relationship"""
        modifiers = {
            'allied': 0.8,  # 20% discount
            'friendly': 0.9,  # 10% discount
            'neutral': 1.0,  # Normal cost
            'hostile': 1.2,  # 20% markup
            'at_war': 2.0,  # 100% markup (if trading allowed)
            'trade_agreement': 0.7,  # 30% discount
        }
        return modifiers.get(self.relation_type, 1.0)


class ChatMessage(models.Model):
    """Enhanced chat system"""
    sender = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='sent_chat_messages')
    
    # Chat channel
    channel_type = models.CharField(max_length=20, choices=[
        ('global', 'Global'),
        ('alliance', 'Alliance'),
        ('private', 'Private'),
        ('system', 'System'),
    ])
    
    # Channel targets
    alliance = models.ForeignKey(Alliance, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_messages')
    private_recipient = models.ForeignKey(Empire, on_delete=models.CASCADE, null=True, blank=True, related_name='received_private_messages')
    
    # Message content
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    
    # Message properties
    is_system_message = models.BooleanField(default=False)
    is_announcement = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.sender.name} ({self.channel_type}): {self.message[:50]}..."


class Message(models.Model):
    """Diplomatic messages between players"""
    sender = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='received_messages')
    alliance = models.ForeignKey(Alliance, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    
    subject = models.CharField(max_length=200)
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    message_type = models.CharField(max_length=20, choices=[
        ('diplomatic', 'Diplomatic'),
        ('alliance_invite', 'Alliance Invite'),
        ('declaration_of_war', 'Declaration of War'),
        ('peace_treaty', 'Peace Treaty'),
        ('attack_report', 'Attack Report'),
    ], default='diplomatic')
    
    def __str__(self):
        return f"Message: {self.subject}"


class WorldEvent(models.Model):
    """Global events affecting the game world"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_type = models.CharField(max_length=30, choices=[
        ('natural_disaster', 'Natural Disaster'),
        ('alien_invasion', 'Alien Invasion'),
        ('economic_crisis', 'Economic Crisis'),
        ('technological_breakthrough', 'Technological Breakthrough'),
        ('resource_discovery', 'Resource Discovery'),
        ('rebellion', 'Rebellion'),
    ])
    
    started_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Event effects (JSON)
    effects = models.JSONField(default=dict)
    affected_territories = models.ManyToManyField(Territory, blank=True)
    
    def __str__(self):
        return self.title


class GameStats(models.Model):
    """Global game statistics"""
    total_players = models.IntegerField(default=0)
    total_battles = models.IntegerField(default=0)
    total_territories_conquered = models.IntegerField(default=0)
    current_top_empire = models.ForeignKey(Empire, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Updated daily
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Game Stats"

    @staticmethod
    def get_building_icons():
        """Get icons for each building type"""
        return {
            'command_center': '🏛️',
            'power_plant': '⚡',
            'mine': '⛏️',
            'farm': '🌾',
            'research_lab': '🔬',
            'barracks': '🪖',
            'defense_system': '🛡️',
            'spy_network': '🕵️',
            'intelligence_hub': '🎯',
            'factory': '🏭',
            'warehouse': '📦',
        }
    
    @staticmethod
    def get_building_names():
        """Get display names for each building type"""
        return {
            'command_center': 'Command Center',
            'power_plant': 'Power Plant',
            'mine': 'Mine',
            'farm': 'Farm',
            'research_lab': 'Research Lab',
            'barracks': 'Barracks',
            'defense_system': 'Defense System',
            'spy_network': 'Spy Network',
            'factory': 'Factory',
        }


class RecruitmentBatch(models.Model):
    """Individual recruitment batches - allows multiple recruitment orders for the same unit type"""
    empire = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='recruitment_batches')
    territory = models.ForeignKey(Territory, on_delete=models.CASCADE, related_name='recruitment_batches')
    
    unit_type = models.CharField(max_length=20, choices=[
        ('infantry', 'Infantry'),
        ('archers', 'Archers'),
        ('spearmen', 'Spearmen'),
        ('heavy_knights', 'Heavy Knights'),
        ('royal_knights', 'Royal Knights'),
        ('spies', 'Spies'),
        ('catapult', 'Catapult'),
        ('ram', 'Ram'),
        ('hero', 'Hero'),
        ('healer', 'Healer'),
        ('scout_hawk', 'Scout Hawk'),
    ], default='infantry')
    
    # Recruitment details
    target_size = models.IntegerField(default=0)  # How many units to recruit in this batch
    recruitment_started = models.DateTimeField(null=True, blank=True)  # When this batch actually started
    recruitment_complete = models.DateTimeField(null=True, blank=True)
    recruitment_rate = models.FloatField(default=1.0)  # Units per second
    
    # Queue system
    status = models.CharField(max_length=20, choices=[
        ('queued', 'Queued'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ], default='queued')
    queue_position = models.IntegerField(default=0)  # Position in queue (0 = first/active)
    created_at = models.DateTimeField(auto_now_add=True)  # When batch was created/queued
    
    # Real-time recruitment tracking
    units_added_to_army = models.IntegerField(default=0)  # Track how many units have been added to army
    
    # Batch status
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['queue_position', 'created_at']
    
    def __str__(self):
        return f"Batch: {self.target_size} {self.get_unit_type_display()} for {self.empire.name} ({self.status})"
    
    def get_recruitment_progress(self):
        """Get recruitment progress percentage"""
        if self.is_completed or self.status == 'completed':
            return 100
        
        if self.status == 'queued':
            return 0
        
        if not self.recruitment_started or not self.recruitment_complete:
            return 0
        
        time_passed = (timezone.now() - self.recruitment_started).total_seconds()
        total_time = (self.recruitment_complete - self.recruitment_started).total_seconds()
        
        if total_time <= 0:
            return 100
        
        progress = min(100, (time_passed / total_time) * 100)
        return progress
    
    def get_units_remaining(self):
        """Get number of units remaining to recruit"""
        if self.is_completed or self.status == 'completed':
            return 0
        
        if self.status == 'queued':
            return self.target_size
        
        # For active batches, return units not yet added to army
        return max(0, self.target_size - self.units_added_to_army)
    
    def get_units_completed(self):
        """Get number of units that have been completed and added to army"""
        if self.is_completed or self.status == 'completed':
            return self.target_size
        
        if self.status == 'queued':
            return 0
        
        # For active batches, return units already added to army
        return self.units_added_to_army
    
    def get_time_remaining(self):
        """Get time remaining in seconds"""
        if self.is_completed or self.status == 'completed':
            return 0
        
        if self.status == 'queued':
            return 0  # Will be calculated differently for queued items
        
        if not self.recruitment_complete:
            return 0
        
        return max(0, (self.recruitment_complete - timezone.now()).total_seconds())
    
    def get_estimated_total_time(self):
        """Get estimated total time for this batch including queue wait"""
        if self.is_completed or self.status == 'completed':
            return 0
        
        # Base recruitment time for this batch
        base_time = Army.get_recruitment_time(self.unit_type, self.target_size)
        
        if self.status == 'active':
            return self.get_time_remaining()
        
        # For queued batches, add time from all batches ahead in queue
        queue_time = 0
        earlier_batches = RecruitmentBatch.objects.filter(
            empire=self.empire,
            territory=self.territory,
            unit_type=self.unit_type,
            status__in=['active', 'queued'],
            queue_position__lt=self.queue_position
        )
        
        for batch in earlier_batches:
            if batch.status == 'active':
                queue_time += batch.get_time_remaining()
            else:
                queue_time += Army.get_recruitment_time(batch.unit_type, batch.target_size)
        
        return queue_time + base_time
    
    def start_recruitment(self):
        """Start this specific batch (called when it's this batch's turn)"""
        if self.status != 'queued':
            return False
        
        recruitment_time_seconds = Army.get_recruitment_time(self.unit_type, self.target_size)
        
        self.status = 'active'
        self.recruitment_started = timezone.now()
        self.recruitment_complete = timezone.now() + timezone.timedelta(seconds=recruitment_time_seconds)
        self.recruitment_rate = self.target_size / recruitment_time_seconds if recruitment_time_seconds > 0 else 1.0
        self.save()
        
        return True
    
    def update_progress(self):
        """Update recruitment progress and add completed units to army in real-time"""
        if self.is_completed or self.status == 'completed':
            return False
        
        # If this batch is queued, check if it should become active
        if self.status == 'queued':
            # Check if there are any active batches of the same type in the same territory
            active_batch = RecruitmentBatch.objects.filter(
                empire=self.empire,
                territory=self.territory,
                unit_type=self.unit_type,
                status='active'
            ).first()
            
            if not active_batch and self.queue_position == 0:
                # This batch should start now
                self.start_recruitment()
                return False
            
            # Still queued, nothing to update
            return False
        
        # For active batches, calculate how many units should be completed by now
        if self.status == 'active' and self.recruitment_started and self.recruitment_complete:
            # Calculate progress
            time_passed = (timezone.now() - self.recruitment_started).total_seconds()
            total_time = (self.recruitment_complete - self.recruitment_started).total_seconds()
            
            if total_time <= 0:
                # Recruitment should complete immediately
                self.complete_recruitment()
                self._start_next_batch_in_queue()
                return True
            
            # Calculate how many units should be completed by now
            progress = min(1.0, time_passed / total_time)
            units_completed_now = int(progress * self.target_size)
            
            # Find the main army for this unit type (not temporary attack armies)
            # Strategy: Find the army that's not currently in battle, or the largest one
            armies = Army.objects.filter(
                empire=self.empire,
                territory=self.territory,
                unit_type=self.unit_type
            )
            
            # Find the main army (not in battle, or largest)
            main_army = None
            for army in armies:
                if not army.is_in_battle():
                    main_army = army
                    break
            
            # If all armies are in battle, use the largest one (most likely the main army)
            if not main_army:
                main_army = armies.order_by('-size').first()
            
            # If no army exists, create one
            if not main_army:
                main_army = Army.objects.create(
                    empire=self.empire,
                    territory=self.territory,
                    unit_type=self.unit_type,
                    size=0
                )
            
            # Calculate how many new units to add
            units_to_add = units_completed_now - self.units_added_to_army
            
            if units_to_add > 0:
                # Add the new units to the main army
                main_army.size += units_to_add
                main_army.save()
                
                # Update our tracking
                self.units_added_to_army = units_completed_now
                self.save()
            
            # Check if recruitment is complete
            if timezone.now() >= self.recruitment_complete:
                # Ensure all units are added (in case of rounding issues)
                remaining_units = self.target_size - self.units_added_to_army
                if remaining_units > 0:
                    main_army.size += remaining_units
                    main_army.save()
                    self.units_added_to_army = self.target_size
                
                # Mark batch as completed
                self.status = 'completed'
                self.is_completed = True
                self.save()
                
                # Start the next batch in queue
                self._start_next_batch_in_queue()
                
                return True
        
        return False
    
    def complete_recruitment(self):
        """Complete this recruitment batch and add units to army"""
        if self.is_completed or self.status == 'completed':
            return
        
        # Find the main army for this unit type (not temporary attack armies)
        armies = Army.objects.filter(
            empire=self.empire,
            territory=self.territory,
            unit_type=self.unit_type
        )
        
        # Find the main army (not in battle, or largest)
        main_army = None
        for army in armies:
            if not army.is_in_battle():
                main_army = army
                break
        
        # If all armies are in battle, use the largest one (most likely the main army)
        if not main_army:
            main_army = armies.order_by('-size').first()
        
        # If no army exists, create one
        if not main_army:
            main_army = Army.objects.create(
                empire=self.empire,
                territory=self.territory,
                unit_type=self.unit_type,
                size=0
            )
        
        # Add the recruited units to the main army
        main_army.size += self.target_size
        main_army.save()
        
        # Mark this batch as completed
        self.status = 'completed'
        self.is_completed = True
        self.save()
    
    def _start_next_batch_in_queue(self):
        """Start the next batch in queue for the same unit type and territory"""
        # Update queue positions for remaining batches
        remaining_batches = RecruitmentBatch.objects.filter(
            empire=self.empire,
            territory=self.territory,
            unit_type=self.unit_type,
            status='queued'
        ).order_by('queue_position', 'created_at')
        
        # Reorder queue positions
        for i, batch in enumerate(remaining_batches):
            batch.queue_position = i
            batch.save()
        
        # Start the first batch in queue
        next_batch = remaining_batches.first()
        if next_batch:
            next_batch.start_recruitment()
    
    @staticmethod
    def create_new_batch(empire, territory, unit_type, target_size):
        """Create a new recruitment batch and add it to the queue"""
        # Get the next queue position for this unit type in this territory
        last_batch = RecruitmentBatch.objects.filter(
            empire=empire,
            territory=territory,
            unit_type=unit_type,
            status__in=['queued', 'active']
        ).order_by('-queue_position').first()
        
        next_position = (last_batch.queue_position + 1) if last_batch else 0
        
        # Create the new batch
        batch = RecruitmentBatch.objects.create(
            empire=empire,
            territory=territory,
            unit_type=unit_type,
            target_size=target_size,
            status='queued',
            queue_position=next_position
        )
        
        # If this is the first batch (position 0), start it immediately
        if next_position == 0:
            batch.start_recruitment()
        
        return batch
    
    def get_estimated_total_time_minutes(self):
        """Get estimated total time in minutes for display"""
        total_seconds = self.get_estimated_total_time()
        return int(total_seconds / 60) if total_seconds > 0 else 0
    
    def get_estimated_total_time(self):
        """Get estimated total time for this batch including queue wait"""
        if self.is_completed or self.status == 'completed':
            return 0
        
        # Base recruitment time for this batch
        base_time = Army.get_recruitment_time(self.unit_type, self.target_size)
        
        if self.status == 'active':
            return self.get_time_remaining()
        
        # For queued batches, add time from all batches ahead in queue
        queue_time = 0
        earlier_batches = RecruitmentBatch.objects.filter(
            empire=self.empire,
            territory=self.territory,
            unit_type=self.unit_type,
            status__in=['active', 'queued'],
            queue_position__lt=self.queue_position
        )
        
        for batch in earlier_batches:
            if batch.status == 'active':
                queue_time += batch.get_time_remaining()
            else:
                queue_time += Army.get_recruitment_time(batch.unit_type, batch.target_size)
        
        return queue_time + base_time


class AllianceInvitation(models.Model):
    """Alliance invitation system"""
    alliance = models.ForeignKey(Alliance, on_delete=models.CASCADE, related_name='invitations')
    inviter = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='sent_invitations')
    invited = models.ForeignKey(Empire, on_delete=models.CASCADE, related_name='received_invitations')
    
    # Invitation details
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    # Invitation status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ], default='pending')
    
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('alliance', 'invited')
    
    def __str__(self):
        return f"{self.alliance.name} invitation to {self.invited.name}"
    
    def is_expired(self):
        """Check if invitation has expired"""
        return timezone.now() > self.expires_at
    
    def accept(self):
        """Accept the alliance invitation"""
        if self.status != 'pending' or self.is_expired():
            return False
        
        # Check if alliance has space (max 10 members)
        if self.alliance.members.count() >= 10:
            return False
        
        # Add to alliance
        self.alliance.members.add(self.invited)
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        
        return True
    
    def decline(self):
        """Decline the alliance invitation"""
        if self.status != 'pending':
            return False
        
        self.status = 'declined'
        self.responded_at = timezone.now()
        self.save()
        
        return True
