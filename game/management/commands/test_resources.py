from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from game.models import Empire
from django.utils import timezone


class Command(BaseCommand):
    help = 'Test resource generation for user yassiro'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username='yassiro')
            empire = user.empire
            
            self.stdout.write(f"Testing resource generation for {empire.name}")
            
            # Show current resources
            self.stdout.write(f"BEFORE: Energy: {empire.energy}, Minerals: {empire.minerals}, Food: {empire.food}")
            self.stdout.write(f"Production: Energy: +{empire.energy_production}/h, Minerals: +{empire.mineral_production}/h, Food: +{empire.food_production}/h")
            
            # Set last update to 2 minutes ago to trigger generation
            empire.last_resource_update = timezone.now() - timezone.timedelta(minutes=2)
            empire.save()
            
            # Trigger resource generation
            result = empire.generate_resources()
            
            self.stdout.write(f"Generation result: {result}")
            self.stdout.write(f"AFTER: Energy: {empire.energy}, Minerals: {empire.minerals}, Food: {empire.food}")
            
            if result['generated']:
                self.stdout.write(self.style.SUCCESS(f"✅ Resources generated successfully!"))
                self.stdout.write(f"Generated: Energy: +{result['energy_generated']}, Minerals: +{result['minerals_generated']}, Food: +{result['food_generated']}")
            else:
                self.stdout.write(self.style.WARNING(f"⏱️ Not enough time passed. Time until next: {result['time_until_next']:.1f} seconds"))
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('User yassiro not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}')) 