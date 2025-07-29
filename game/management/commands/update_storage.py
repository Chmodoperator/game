from django.core.management.base import BaseCommand
from game.models import Empire


class Command(BaseCommand):
    help = 'Update all empires with the new storage capacity system'

    def handle(self, *args, **options):
        empires = Empire.objects.all()
        updated_count = 0
        
        for empire in empires:
            # Calculate and set storage capacity
            old_storage = getattr(empire, 'energy_storage', 0)
            empire.calculate_storage_capacity()
            
            self.stdout.write(f"Empire: {empire.name}")
            self.stdout.write(f"  Storage: {old_storage} → {empire.energy_storage}")
            self.stdout.write(f"  Resources: ⚡{empire.energy}/{empire.energy_storage} ⛏{empire.minerals}/{empire.mineral_storage} 🌾{empire.food}/{empire.food_storage}")
            
            # Check if any resources exceed storage and cap them
            resources_capped = False
            if empire.energy > empire.energy_storage:
                empire.energy = empire.energy_storage
                resources_capped = True
            if empire.minerals > empire.mineral_storage:
                empire.minerals = empire.mineral_storage
                resources_capped = True
            if empire.food > empire.food_storage:
                empire.food = empire.food_storage
                resources_capped = True
            
            if resources_capped:
                empire.save()
                self.stdout.write(f"  ⚠️ Resources capped to storage limit")
            
            self.stdout.write("---")
            updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} empires with storage capacity!')
        )
        self.stdout.write(
            self.style.SUCCESS('💾 STORAGE SYSTEM ACTIVATED!')
        )
        self.stdout.write(
            self.style.SUCCESS('📦 Base storage: 6,000 each resource')
        )
        self.stdout.write(
            self.style.SUCCESS('🏗️ Building bonuses: Command Center (+500/level), Factory (+300/level), Defense System (+200/level)')
        )
        self.stdout.write(
            self.style.SUCCESS('🗺️ Territory bonus: +100 per territory')
        ) 