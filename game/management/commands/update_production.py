from django.core.management.base import BaseCommand
from game.models import Empire

class Command(BaseCommand):
    help = 'Update production rates for all existing empires'

    def handle(self, *args, **options):
        empires = Empire.objects.all()
        
        for empire in empires:
            empire.calculate_production_rates()
            self.stdout.write(f'Updated production for {empire.name}: {empire.energy_production}⚡ {empire.mineral_production}⛏ {empire.food_production}🌾 per hour')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated production rates for {empires.count()} empires')
        ) 