from django.core.management.base import BaseCommand
from game.models import Empire


class Command(BaseCommand):
    help = 'Boost existing empires to the new powerful economy levels'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        empires = Empire.objects.all()
        updated_count = 0
        
        for empire in empires:
            old_energy = empire.energy
            old_minerals = empire.minerals
            old_food = empire.food
            old_energy_prod = empire.energy_production
            old_mineral_prod = empire.mineral_production
            old_food_prod = empire.food_production
            
            # Boost resources to new minimum levels if they're below
            new_energy = max(empire.energy, 5000)      # Ensure at least 5000 energy
            new_minerals = max(empire.minerals, 3000)  # Ensure at least 3000 minerals
            new_food = max(empire.food, 2000)         # Ensure at least 2000 food
            
            # Recalculate production with new rates
            empire.calculate_production_rates()
            
            changes_made = False
            
            if not dry_run:
                if empire.energy < new_energy:
                    empire.energy = new_energy
                    changes_made = True
                if empire.minerals < new_minerals:
                    empire.minerals = new_minerals
                    changes_made = True
                if empire.food < new_food:
                    empire.food = new_food
                    changes_made = True
                
                if changes_made:
                    empire.save()
                    updated_count += 1
            
            # Show what's happening
            if changes_made or dry_run:
                self.stdout.write(
                    f"Empire: {empire.name} ({'Bot' if empire.is_master_player else 'Player'})"
                )
                self.stdout.write(f"  Resources: ⚡{old_energy}→{new_energy} ⛏{old_minerals}→{new_minerals} 🌾{old_food}→{new_food}")
                self.stdout.write(f"  Production: ⚡{old_energy_prod}→{empire.energy_production}/h ⛏{old_mineral_prod}→{empire.mineral_production}/h 🌾{old_food_prod}→{empire.food_production}/h")
                self.stdout.write("---")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would update {len([e for e in empires if e.energy < 5000 or e.minerals < 3000 or e.food < 2000])} empires')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully boosted {updated_count} empires to new economy levels!')
            )
            self.stdout.write(
                self.style.SUCCESS('🚀 POWERFUL ECONOMY SYSTEM ACTIVATED!')
            )
            self.stdout.write(
                self.style.SUCCESS('📈 Base production: 100/hour each resource')
            )
            self.stdout.write(
                self.style.SUCCESS('🏗️ Buildings: 10x more powerful (+50/+30/+40 per level)')
            )
            self.stdout.write(
                self.style.SUCCESS('🗺️ Territories: +20/hour each for all resources')
            ) 