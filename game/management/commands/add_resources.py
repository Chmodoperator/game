from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from game.models import Empire
from django.db import transaction

class Command(BaseCommand):
    help = 'Add resources to a specific user empire safely'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the empire to add resources to')
        parser.add_argument('--energy', type=int, default=0, help='Energy to add (default: 0)')
        parser.add_argument('--minerals', type=int, default=0, help='Minerals to add (default: 0)')
        parser.add_argument('--food', type=int, default=0, help='Food to add (default: 0)')
        parser.add_argument('--technology', type=int, default=0, help='Technology to add (default: 0)')
        parser.add_argument('--all', type=int, help='Add this amount to all resources (overrides individual values)')
        parser.add_argument('--confirm', action='store_true', help='Confirm the operation (required for safety)')

    def handle(self, *args, **options):
        username = options['username']
        energy = options['energy']
        minerals = options['minerals']
        food = options['food']
        technology = options['technology']
        all_resources = options.get('all')
        confirm = options['confirm']

        # Override individual values if --all is specified
        if all_resources:
            energy = minerals = food = technology = all_resources

        # Safety check - require confirmation
        if not confirm:
            self.stdout.write(
                self.style.ERROR(
                    'ERROR: You must use --confirm flag to proceed with resource addition. '
                    'This is a safety measure to prevent accidental resource manipulation.'
                )
            )
            return

        # Check if at least one resource is specified
        if energy == 0 and minerals == 0 and food == 0 and technology == 0:
            self.stdout.write(
                self.style.ERROR(
                    'ERROR: You must specify at least one resource to add. '
                    'Use --energy, --minerals, --food, --technology, or --all arguments.'
                )
            )
            return

        try:
            # Get the user and empire
            user = User.objects.get(username=username)
            empire = user.empire
            
            # Store original values for reporting
            original_energy = empire.energy
            original_minerals = empire.minerals
            original_food = empire.food
            original_technology = empire.technology
            
            # Use transaction for safety
            with transaction.atomic():
                # Add resources
                empire.energy += energy
                empire.minerals += minerals
                empire.food += food
                empire.technology += technology
                
                # Ensure resources don't go below 0
                empire.energy = max(0, empire.energy)
                empire.minerals = max(0, empire.minerals)
                empire.food = max(0, empire.food)
                empire.technology = max(0, empire.technology)
                
                # Ensure resources don't exceed storage capacity
                empire.enforce_storage_limits()
                
                # Save the empire
                empire.save()
                
                # Update production rates and storage capacity
                empire.calculate_production_rates()
                empire.calculate_storage_capacity()

            # Success message
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Successfully added resources to empire "{empire.name}" (User: {username})'
                )
            )
            
            # Show details
            self.stdout.write('\n📊 RESOURCE CHANGES:')
            if energy != 0:
                self.stdout.write(f'  ⚡ Energy: {original_energy:,} → {empire.energy:,} (+{energy:,})')
            if minerals != 0:
                self.stdout.write(f'  ⛏ Minerals: {original_minerals:,} → {empire.minerals:,} (+{minerals:,})')
            if food != 0:
                self.stdout.write(f'  🌾 Food: {original_food:,} → {empire.food:,} (+{food:,})')
            if technology != 0:
                self.stdout.write(f'  🔬 Technology: {original_technology:,} → {empire.technology:,} (+{technology:,})')
            
            # Show current totals
            self.stdout.write('\n💰 CURRENT TOTALS:')
            self.stdout.write(f'  ⚡ Energy: {empire.energy:,}/{empire.energy_storage:,}')
            self.stdout.write(f'  ⛏ Minerals: {empire.minerals:,}/{empire.mineral_storage:,}')
            self.stdout.write(f'  🌾 Food: {empire.food:,}/{empire.food_storage:,}')
            self.stdout.write(f'  🔬 Technology: {empire.technology:,}')
            
            # Show production rates
            self.stdout.write('\n📈 PRODUCTION RATES:')
            self.stdout.write(f'  ⚡ Energy: +{empire.energy_production}/hour')
            self.stdout.write(f'  ⛏ Minerals: +{empire.mineral_production}/hour')
            self.stdout.write(f'  🌾 Food: +{empire.food_production}/hour')
            
            # Storage warnings
            if empire.energy >= empire.energy_storage * 0.9:
                self.stdout.write(self.style.WARNING('⚠️  Energy storage is nearly full!'))
            if empire.minerals >= empire.mineral_storage * 0.9:
                self.stdout.write(self.style.WARNING('⚠️  Mineral storage is nearly full!'))
            if empire.food >= empire.food_storage * 0.9:
                self.stdout.write(self.style.WARNING('⚠️  Food storage is nearly full!'))

        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist.')
        except Exception as e:
            raise CommandError(f'Error adding resources: {str(e)}')

    def style_number(self, number):
        """Format numbers with commas for better readability"""
        return f"{number:,}" 