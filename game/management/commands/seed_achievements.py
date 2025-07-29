from django.core.management.base import BaseCommand
from game.models import Achievement


class Command(BaseCommand):
    help = 'Seed the database with initial achievements'

    def handle(self, *args, **options):
        achievements_data = [
            # Territory Achievements
            {
                'name': 'First Settlement',
                'description': 'Establish your first territory outside your capital.',
                'achievement_type': 'territory',
                'criteria_json': {'min_territories': 1},
                'reward_energy': 500,
                'reward_minerals': 300,
                'reward_food': 200,
                'difficulty': 'easy',
                'icon': '🏠'
            },
            {
                'name': 'Growing Empire',
                'description': 'Control 5 territories across the galaxy.',
                'achievement_type': 'territory',
                'criteria_json': {'min_territories': 5},
                'reward_energy': 2000,
                'reward_minerals': 1500,
                'reward_food': 1000,
                'difficulty': 'medium',
                'icon': '🏘️'
            },
            {
                'name': 'Galactic Overlord',
                'description': 'Control 25 territories and become a major galactic power.',
                'achievement_type': 'territory',
                'criteria_json': {'min_territories': 25},
                'reward_energy': 10000,
                'reward_minerals': 7500,
                'reward_food': 5000,
                'reward_technology': 1000,
                'difficulty': 'hard',
                'icon': '👑'
            },
            {
                'name': 'Emperor of Space',
                'description': 'Control 50 territories and rule vast regions of space.',
                'achievement_type': 'territory',
                'criteria_json': {'min_territories': 50},
                'reward_energy': 50000,
                'reward_minerals': 40000,
                'reward_food': 30000,
                'reward_technology': 5000,
                'difficulty': 'legendary',
                'icon': '🌌'
            },

            # Battle Achievements
            {
                'name': 'First Victory',
                'description': 'Win your first battle against another player.',
                'achievement_type': 'battle',
                'criteria_json': {'min_battles_won': 1},
                'reward_energy': 1000,
                'reward_minerals': 500,
                'reward_food': 300,
                'difficulty': 'easy',
                'icon': '⚔️'
            },
            {
                'name': 'Veteran Commander',
                'description': 'Win 10 battles and prove your tactical skills.',
                'achievement_type': 'battle',
                'criteria_json': {'min_battles_won': 10},
                'reward_energy': 5000,
                'reward_minerals': 3000,
                'reward_food': 2000,
                'difficulty': 'medium',
                'icon': '🛡️'
            },
            {
                'name': 'War Machine',
                'description': 'Win 50 battles and become a feared warlord.',
                'achievement_type': 'battle',
                'criteria_json': {'min_battles_won': 50},
                'reward_energy': 25000,
                'reward_minerals': 15000,
                'reward_food': 10000,
                'reward_technology': 2000,
                'difficulty': 'hard',
                'icon': '💀'
            },
            {
                'name': 'Galactic Conqueror',
                'description': 'Win 100 battles and become legendary.',
                'achievement_type': 'battle',
                'criteria_json': {'min_battles_won': 100},
                'reward_energy': 100000,
                'reward_minerals': 75000,
                'reward_food': 50000,
                'reward_technology': 10000,
                'difficulty': 'legendary',
                'icon': '🏆'
            },

            # Building Achievements
            {
                'name': 'Master Builder',
                'description': 'Construct 10 buildings across your empire.',
                'achievement_type': 'building',
                'criteria_json': {'min_buildings': 10},
                'reward_energy': 2000,
                'reward_minerals': 2000,
                'reward_food': 1000,
                'difficulty': 'easy',
                'icon': '🏗️'
            },
            {
                'name': 'Industrial Complex',
                'description': 'Construct 50 buildings and industrialize your empire.',
                'achievement_type': 'building',
                'criteria_json': {'min_buildings': 50},
                'reward_energy': 10000,
                'reward_minerals': 10000,
                'reward_food': 5000,
                'reward_technology': 1000,
                'difficulty': 'medium',
                'icon': '🏭'
            },
            {
                'name': 'Mega Corporation',
                'description': 'Construct 100 buildings and dominate galactic industry.',
                'achievement_type': 'building',
                'criteria_json': {'min_buildings': 100},
                'reward_energy': 50000,
                'reward_minerals': 50000,
                'reward_food': 25000,
                'reward_technology': 5000,
                'difficulty': 'hard',
                'icon': '🏙️'
            },

            # Research Achievements
            {
                'name': 'Scientist',
                'description': 'Reach a total of 10 research levels.',
                'achievement_type': 'research',
                'criteria_json': {'min_research_levels': 10},
                'reward_energy': 1000,
                'reward_minerals': 1000,
                'reward_food': 1000,
                'reward_technology': 500,
                'difficulty': 'easy',
                'icon': '🔬'
            },
            {
                'name': 'Tech Pioneer',
                'description': 'Reach a total of 50 research levels.',
                'achievement_type': 'research',
                'criteria_json': {'min_research_levels': 50},
                'reward_energy': 5000,
                'reward_minerals': 5000,
                'reward_food': 5000,
                'reward_technology': 2500,
                'difficulty': 'medium',
                'icon': '🧪'
            },
            {
                'name': 'Galactic Genius',
                'description': 'Reach a total of 100 research levels.',
                'achievement_type': 'research',
                'criteria_json': {'min_research_levels': 100},
                'reward_energy': 25000,
                'reward_minerals': 25000,
                'reward_food': 25000,
                'reward_technology': 10000,
                'difficulty': 'hard',
                'icon': '🎓'
            },

            # Alliance Achievements
            {
                'name': 'Diplomat',
                'description': 'Join your first alliance.',
                'achievement_type': 'alliance',
                'criteria_json': {'min_alliances': 1},
                'reward_energy': 1500,
                'reward_minerals': 1000,
                'reward_food': 500,
                'difficulty': 'easy',
                'icon': '🤝'
            },

            # Economy Achievements
            {
                'name': 'Resource Hoarder',
                'description': 'Accumulate 10,000 total resources.',
                'achievement_type': 'economy',
                'criteria_json': {'min_resources': 10000},
                'reward_energy': 2000,
                'reward_minerals': 2000,
                'reward_food': 2000,
                'difficulty': 'easy',
                'icon': '💰'
            },
            {
                'name': 'Economic Powerhouse',
                'description': 'Accumulate 100,000 total resources.',
                'achievement_type': 'economy',
                'criteria_json': {'min_resources': 100000},
                'reward_energy': 10000,
                'reward_minerals': 10000,
                'reward_food': 10000,
                'reward_technology': 2000,
                'difficulty': 'medium',
                'icon': '💎'
            },
            {
                'name': 'Galactic Bank',
                'description': 'Accumulate 1,000,000 total resources.',
                'achievement_type': 'economy',
                'criteria_json': {'min_resources': 1000000},
                'reward_energy': 50000,
                'reward_minerals': 50000,
                'reward_food': 50000,
                'reward_technology': 10000,
                'difficulty': 'legendary',
                'icon': '🏦'
            },

            # Special Achievements
            {
                'name': 'Explorer',
                'description': 'Discover your first uncharted territory.',
                'achievement_type': 'special',
                'criteria_json': {'special_action': 'explore_territory'},
                'reward_energy': 500,
                'reward_minerals': 500,
                'reward_food': 500,
                'difficulty': 'easy',
                'icon': '🗺️',
                'is_secret': True
            },
            {
                'name': 'Monster Slayer',
                'description': 'Defeat your first terrain monster.',
                'achievement_type': 'special',
                'criteria_json': {'special_action': 'defeat_monster'},
                'reward_energy': 1000,
                'reward_minerals': 1000,
                'reward_food': 1000,
                'difficulty': 'medium',
                'icon': '🐉',
                'is_secret': True
            },
            {
                'name': 'Master Trader',
                'description': 'Complete 10 successful trades.',
                'achievement_type': 'special',
                'criteria_json': {'special_action': 'complete_trades', 'min_count': 10},
                'reward_energy': 5000,
                'reward_minerals': 5000,
                'reward_food': 5000,
                'difficulty': 'medium',
                'icon': '🛒'
            },
            {
                'name': 'Tournament Champion',
                'description': 'Win your first tournament.',
                'achievement_type': 'special',
                'criteria_json': {'special_action': 'win_tournament'},
                'reward_energy': 10000,
                'reward_minerals': 10000,
                'reward_food': 10000,
                'reward_technology': 5000,
                'difficulty': 'hard',
                'icon': '🥇'
            }
        ]

        created_count = 0
        for achievement_data in achievements_data:
            achievement, created = Achievement.objects.get_or_create(
                name=achievement_data['name'],
                defaults=achievement_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created achievement: {achievement.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Achievement already exists: {achievement.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully seeded {created_count} new achievements!')
        ) 