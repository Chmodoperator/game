from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from django import forms
from .models import (
    Empire, Territory, Building, Research, Army, Battle, Alliance, Message, 
    WorldEvent, GameStats, TerrainMonster, TradeOffer, Tournament, Achievement,
    EmpireAchievement, ResearchPrerequisite, DiplomaticRelation, ChatMessage
)

# Custom forms for admin actions
class ResourceForm(forms.Form):
    energy = forms.IntegerField(min_value=0, required=False, initial=0, help_text="Energy to add (0 = no change)")
    minerals = forms.IntegerField(min_value=0, required=False, initial=0, help_text="Minerals to add (0 = no change)")
    food = forms.IntegerField(min_value=0, required=False, initial=0, help_text="Food to add (0 = no change)")
    technology = forms.IntegerField(min_value=0, required=False, initial=0, help_text="Technology to add (0 = no change)")
    gold = forms.IntegerField(min_value=0, required=False, initial=0, help_text="Gold to add (0 = no change)")
    
    # Option to set absolute values instead of adding
    set_absolute = forms.BooleanField(required=False, help_text="Set absolute values instead of adding to current amounts")

class BulkResourceForm(forms.Form):
    energy = forms.IntegerField(min_value=0, initial=1000, help_text="Energy to add to selected empires")
    minerals = forms.IntegerField(min_value=0, initial=1000, help_text="Minerals to add")
    food = forms.IntegerField(min_value=0, initial=1000, help_text="Food to add")
    technology = forms.IntegerField(min_value=0, initial=0, help_text="Technology to add")
    gold = forms.IntegerField(min_value=0, initial=0, help_text="Gold to add")
    set_absolute = forms.BooleanField(required=False, help_text="Set absolute values instead of adding")
    confirm = forms.BooleanField(required=True, help_text="I confirm this bulk operation")

class QuickResourceForm(forms.Form):
    """Quick presets for common resource additions"""
    PRESET_CHOICES = [
        ('small', 'Small Package (1K each)'),
        ('medium', 'Medium Package (5K each)'),
        ('large', 'Large Package (10K each)'),
        ('mega', 'Mega Package (50K each)'),
        ('custom', 'Custom Amount'),
    ]
    
    preset = forms.ChoiceField(choices=PRESET_CHOICES, initial='medium')
    custom_energy = forms.IntegerField(min_value=0, required=False, initial=0)
    custom_minerals = forms.IntegerField(min_value=0, required=False, initial=0)
    custom_food = forms.IntegerField(min_value=0, required=False, initial=0)
    custom_technology = forms.IntegerField(min_value=0, required=False, initial=0)
    custom_gold = forms.IntegerField(min_value=0, required=False, initial=0)

# Custom admin actions
def add_resources_to_empire(modeladmin, request, queryset):
    """Safe action to add resources to selected empires"""
    if 'apply' in request.POST:
        form = BulkResourceForm(request.POST)
        if form.is_valid():
            energy = form.cleaned_data['energy']
            minerals = form.cleaned_data['minerals']
            food = form.cleaned_data['food']
            technology = form.cleaned_data['technology']
            gold = form.cleaned_data['gold']
            set_absolute = form.cleaned_data['set_absolute']
            
            updated_count = 0
            for empire in queryset:
                if set_absolute:
                    # Set absolute values
                    empire.energy = energy
                    empire.minerals = minerals
                    empire.food = food
                    empire.technology = technology
                    empire.gold = gold
                else:
                    # Add to current values
                    empire.energy += energy
                    empire.minerals += minerals
                    empire.food += food
                    empire.technology += technology
                    empire.gold += gold
                
                # Ensure resources don't exceed storage capacity
                empire.enforce_storage_limits()
                empire.save()
                updated_count += 1
            
            action_type = "Set" if set_absolute else "Added"
            messages.success(request, f'{action_type} resources for {updated_count} empires!')
            return HttpResponseRedirect(request.get_full_path())
    else:
        form = BulkResourceForm()
    
    return render(request, 'admin/bulk_resource_form.html', {
        'form': form,
        'empires': queryset,
        'title': 'Add/Set Resources for Selected Empires'
    })

add_resources_to_empire.short_description = "Add/Set resources for selected empires"

def reset_empire_resources(modeladmin, request, queryset):
    """Reset empires to starting resources"""
    if 'apply' in request.POST:
        for empire in queryset:
            empire.energy = 5000  # Starting energy
            empire.minerals = 3000  # Starting minerals
            empire.food = 2000  # Starting food
            empire.technology = 0
            empire.save()
        
        messages.success(request, f'Reset {queryset.count()} empires to starting resources!')
        return HttpResponseRedirect(request.get_full_path())
    
    return render(request, 'admin/confirm_action.html', {
        'queryset': queryset,
        'title': 'Reset Empire Resources',
        'message': 'This will reset selected empires to starting resource values. Are you sure?'
    })

reset_empire_resources.short_description = "Reset to starting resources"

def recalculate_empire_stats(modeladmin, request, queryset):
    """Recalculate power levels and production for selected empires"""
    for empire in queryset:
        empire.calculate_power()
        empire.calculate_production_rates()
        empire.calculate_storage_capacity()
    
    messages.success(request, f'Recalculated stats for {queryset.count()} empires!')

recalculate_empire_stats.short_description = "Recalculate empire stats"

def quick_resource_boost(modeladmin, request, queryset):
    """Quick resource boost with presets"""
    if 'apply' in request.POST:
        form = QuickResourceForm(request.POST)
        if form.is_valid():
            preset = form.cleaned_data['preset']
            
            # Determine amounts based on preset
            if preset == 'small':
                energy = minerals = food = 1000
                technology = 0
                gold = 10
            elif preset == 'medium':
                energy = minerals = food = 5000
                technology = 100
                gold = 50
            elif preset == 'large':
                energy = minerals = food = 10000
                technology = 500
                gold = 100
            elif preset == 'mega':
                energy = minerals = food = 50000
                technology = 2000
                gold = 500
            elif preset == 'custom':
                energy = form.cleaned_data['custom_energy']
                minerals = form.cleaned_data['custom_minerals']
                food = form.cleaned_data['custom_food']
                technology = form.cleaned_data['custom_technology']
                gold = form.cleaned_data['custom_gold']
            
            updated_count = 0
            for empire in queryset:
                empire.energy += energy
                empire.minerals += minerals
                empire.food += food
                empire.technology += technology
                empire.gold += gold
                empire.enforce_storage_limits()
                empire.save()
                updated_count += 1
            
            messages.success(request, f'Applied {preset} resource boost to {updated_count} empires!')
            return HttpResponseRedirect(request.get_full_path())
    else:
        form = QuickResourceForm()
    
    return render(request, 'admin/quick_resource_form.html', {
        'form': form,
        'empires': queryset,
        'title': 'Quick Resource Boost'
    })

quick_resource_boost.short_description = "Quick resource boost (presets)"

@admin.register(Empire)
class EmpireAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'power_level', 'rank', 'resource_summary', 'production_summary', 'add_resources_link', 'is_master_player', 'territories_count', 'buildings_count', 'armies_count', 'created_at')
    list_filter = ('created_at', 'rank', 'is_master_player', 'master_level')
    search_fields = ('name', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'last_active', 'power_level', 'population')
    actions = [add_resources_to_empire, reset_empire_resources, recalculate_empire_stats, quick_resource_boost]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'name', 'motto', 'color')
        }),
        ('Master Player System', {
            'fields': ('is_master_player', 'master_level'),
            'classes': ('collapse',)
        }),
        ('Resources', {
            'fields': ('energy', 'minerals', 'food', 'technology', 'gold'),
            'description': 'Current resource amounts'
        }),
        ('Production', {
            'fields': ('energy_production', 'mineral_production', 'food_production'),
            'classes': ('collapse',)
        }),
        ('Storage', {
            'fields': ('energy_storage', 'mineral_storage', 'food_storage'),
            'classes': ('collapse',)
        }),
        ('Stats', {
            'fields': ('population', 'power_level', 'rank'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_active', 'last_resource_update'),
            'classes': ('collapse',)
        })
    )
    
    def resource_summary(self, obj):
        energy_pct = (obj.energy / obj.energy_storage * 100) if obj.energy_storage > 0 else 0
        minerals_pct = (obj.minerals / obj.mineral_storage * 100) if obj.mineral_storage > 0 else 0
        food_pct = (obj.food / obj.food_storage * 100) if obj.food_storage > 0 else 0
        
        # Format numbers and build HTML string directly
        energy_str = f"{int(obj.energy):,}"
        minerals_str = f"{int(obj.minerals):,}"
        food_str = f"{int(obj.food):,}"
        
        html = f'⚡{energy_str} ({energy_pct:.0f}%) | ⛏{minerals_str} ({minerals_pct:.0f}%) | 🌾{food_str} ({food_pct:.0f}%)'
        return mark_safe(html)
    resource_summary.short_description = 'Resources (Storage %)'
    
    def add_resources_link(self, obj):
        """Quick link to add resources to this empire"""
        url = reverse('admin:empire_add_resources', args=[obj.id])
        return format_html(
            '<a href="{}" class="button" style="background: #28a745; color: white; padding: 4px 8px; '
            'text-decoration: none; border-radius: 3px; font-size: 11px;">💰 Add Resources</a>',
            url
        )
    add_resources_link.short_description = 'Quick Actions'
    add_resources_link.allow_tags = True
    
    def production_summary(self, obj):
        return format_html(
            '⚡+{}/h | ⛏+{}/h | 🌾+{}/h',
            obj.energy_production, obj.mineral_production, obj.food_production
        )
    production_summary.short_description = 'Production/Hour'
    
    def territories_count(self, obj):
        return obj.territories.count()
    territories_count.short_description = 'Territories'
    
    def buildings_count(self, obj):
        return obj.buildings.count()
    buildings_count.short_description = 'Buildings'
    
    def armies_count(self, obj):
        present_armies = obj.get_present_armies().count()
        total_armies = obj.armies.count()
        if present_armies != total_armies:
            return format_html(
                '<span style="color: #44ff44;">{}</span> / <span style="color: #aaa;">{}</span>',
                present_armies, total_armies
            )
        return total_armies
    armies_count.short_description = 'Armies (Present/Total)'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add-resources/<int:empire_id>/', self.admin_site.admin_view(self.add_resources_view), name='empire_add_resources'),
            path('game-statistics/', self.admin_site.admin_view(self.game_statistics_view), name='game_statistics'),
        ]
        return custom_urls + urls
    
    def add_resources_view(self, request, empire_id):
        empire = Empire.objects.get(id=empire_id)
        
        if request.method == 'POST':
            form = ResourceForm(request.POST)
            if form.is_valid():
                energy = form.cleaned_data['energy'] or 0
                minerals = form.cleaned_data['minerals'] or 0
                food = form.cleaned_data['food'] or 0
                technology = form.cleaned_data['technology'] or 0
                gold = form.cleaned_data['gold'] or 0
                set_absolute = form.cleaned_data['set_absolute']
                
                # Store old values for logging
                old_energy = empire.energy
                old_minerals = empire.minerals
                old_food = empire.food
                old_technology = empire.technology
                old_gold = empire.gold
                
                if set_absolute:
                    # Set absolute values
                    empire.energy = energy
                    empire.minerals = minerals
                    empire.food = food
                    empire.technology = technology
                    empire.gold = gold
                    action = "Set"
                else:
                    # Add to current values
                    empire.energy += energy
                    empire.minerals += minerals
                    empire.food += food
                    empire.technology += technology
                    empire.gold += gold
                    action = "Added"
                
                # Ensure resources don't exceed storage capacity
                empire.enforce_storage_limits()
                empire.save()
                
                # Create detailed success message
                changes = []
                if energy > 0:
                    if set_absolute:
                        changes.append(f"Energy: {old_energy:,} → {empire.energy:,}")
                    else:
                        changes.append(f"Energy: +{energy:,} (now {empire.energy:,})")
                if minerals > 0:
                    if set_absolute:
                        changes.append(f"Minerals: {old_minerals:,} → {empire.minerals:,}")
                    else:
                        changes.append(f"Minerals: +{minerals:,} (now {empire.minerals:,})")
                if food > 0:
                    if set_absolute:
                        changes.append(f"Food: {old_food:,} → {empire.food:,}")
                    else:
                        changes.append(f"Food: +{food:,} (now {empire.food:,})")
                if technology > 0:
                    if set_absolute:
                        changes.append(f"Technology: {old_technology:,} → {empire.technology:,}")
                    else:
                        changes.append(f"Technology: +{technology:,} (now {empire.technology:,})")
                
                if gold > 0:
                    if set_absolute:
                        changes.append(f"Gold: {old_gold:,} → {empire.gold:,}")
                    else:
                        changes.append(f"Gold: +{gold:,} (now {empire.gold:,})")
                
                if changes:
                    messages.success(request, f'{action} resources for {empire.name}: {", ".join(changes)}')
                else:
                    messages.info(request, f'No changes made to {empire.name}')
                
                return redirect('admin:game_empire_changelist')
        else:
            form = ResourceForm()
        
        return render(request, 'admin/add_resources.html', {
            'form': form,
            'empire': empire,
            'title': f'Add/Set Resources for {empire.name}',
            'current_resources': {
                'energy': empire.energy,
                'minerals': empire.minerals,
                'food': empire.food,
                'technology': empire.technology,
                'gold': empire.gold,
                'energy_storage': empire.energy_storage,
                'mineral_storage': empire.mineral_storage,
                'food_storage': empire.food_storage,
            }
        })
    
    def game_statistics_view(self, request):
        # Comprehensive game statistics
        stats = {
            'total_empires': Empire.objects.count(),
            'human_players': Empire.objects.filter(is_master_player=False).count(),
            'master_players': Empire.objects.filter(is_master_player=True).count(),
            'total_territories': Territory.objects.count(),
            'occupied_territories': Territory.objects.filter(owner__isnull=False).count(),
            'total_buildings': Building.objects.count(),
            'total_armies': Army.objects.count(),
            'total_battles': Battle.objects.count(),
            'active_battles': Battle.objects.filter(status__in=['traveling', 'fighting', 'returning']).count(),
            'alliances': Alliance.objects.count(),
            'achievements_earned': EmpireAchievement.objects.count(),
            'resource_totals': Empire.objects.aggregate(
                total_energy=Sum('energy'),
                total_minerals=Sum('minerals'),
                total_food=Sum('food')
            ),
            'avg_power': Empire.objects.aggregate(avg_power=Avg('power_level'))['avg_power'] or 0,
            'top_empires': Empire.objects.order_by('-power_level')[:10],
        }
        
        return render(request, 'admin/game_statistics.html', {
            'stats': stats,
            'title': 'Game Statistics Dashboard'
        })


@admin.register(Territory)
class TerritoryAdmin(admin.ModelAdmin):
    list_display = ('coordinates', 'terrain_type', 'resource_bonus', 'owner', 'defense_bonus', 'buildings_count', 'armies_count', 'monsters_count')
    list_filter = ('terrain_type', 'resource_bonus', 'owner', 'defense_bonus')
    search_fields = ('owner__name', 'x', 'y')
    
    def coordinates(self, obj):
        return format_html('<strong>({}, {})</strong>', obj.x, obj.y)
    coordinates.short_description = 'Coordinates'
    
    def buildings_count(self, obj):
        return obj.buildings.count()
    buildings_count.short_description = 'Buildings'
    
    def armies_count(self, obj):
        present_armies = obj.get_present_armies().count()
        total_armies = obj.armies.count()
        if present_armies != total_armies:
            return format_html(
                '<span style="color: #44ff44;">{}</span> / <span style="color: #aaa;">{}</span>',
                present_armies, total_armies
            )
        return total_armies
    armies_count.short_description = 'Armies (Present/Total)'
    
    def monsters_count(self, obj):
        return obj.monsters.count()
    monsters_count.short_description = 'Monsters'


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('empire', 'building_type', 'level', 'territory_coordinates', 'upgrade_status', 'built_at')
    list_filter = ('building_type', 'level', 'empire', 'built_at')
    search_fields = ('empire__name', 'territory__x', 'territory__y')
    readonly_fields = ('built_at',)
    
    def territory_coordinates(self, obj):
        return format_html('({}, {})', obj.territory.x, obj.territory.y)
    territory_coordinates.short_description = 'Territory'
    
    def upgrade_status(self, obj):
        if obj.upgrade_started and obj.upgrade_complete:
            if timezone.now() < obj.upgrade_complete:
                return format_html('<span style="color: orange;">⏱️ Upgrading</span>')
            else:
                return format_html('<span style="color: red;">⚠️ Needs Completion</span>')
        return format_html('<span style="color: green;">✅ Ready</span>')
    upgrade_status.short_description = 'Status'


@admin.register(Research)
class ResearchAdmin(admin.ModelAdmin):
    list_display = ('empire', 'research_type', 'level', 'research_status', 'progress_bar')
    list_filter = ('research_type', 'level', 'empire')
    search_fields = ('empire__name',)
    
    def research_status(self, obj):
        if obj.research_started and obj.research_complete:
            if timezone.now() < obj.research_complete:
                return format_html('<span style="color: orange;">🔬 Researching</span>')
            else:
                return format_html('<span style="color: red;">⚠️ Needs Completion</span>')
        return format_html('<span style="color: green;">✅ Ready</span>')
    research_status.short_description = 'Status'
    
    def progress_bar(self, obj):
        if obj.research_started and obj.research_complete:
            now = timezone.now()
            if now < obj.research_complete:
                total_time = (obj.research_complete - obj.research_started).total_seconds()
                elapsed = (now - obj.research_started).total_seconds()
                progress = min(100, (elapsed / total_time) * 100)
                return format_html(
                    '<div style="background: #ddd; border-radius: 3px; overflow: hidden; height: 10px; width: 100px;">'
                    '<div style="background: #4CAF50; height: 100%; width: {}%;"></div>'
                    '</div>',
                    progress
                )
        return '-'
    progress_bar.short_description = 'Progress'


@admin.register(Army)
class ArmyAdmin(admin.ModelAdmin):
    list_display = ('empire', 'unit_type', 'size', 'territory_coordinates', 'recruitment_status', 'battle_status', 'combat_strength')
    list_filter = ('unit_type', 'empire', 'created_at')
    search_fields = ('empire__name',)
    readonly_fields = ('created_at',)
    
    def territory_coordinates(self, obj):
        return format_html('({}, {})', obj.territory.x, obj.territory.y)
    territory_coordinates.short_description = 'Territory'
    
    def recruitment_status(self, obj):
        if obj.is_recruiting():
            return format_html('<span style="color: orange;">🏗️ Recruiting</span>')
        return format_html('<span style="color: green;">✅ Ready</span>')
    recruitment_status.short_description = 'Status'
    
    def battle_status(self, obj):
        if obj.is_in_battle():
            return format_html('<span style="color: red;">⚔️ In Battle</span>')
        return format_html('<span style="color: green;">🏠 Present</span>')
    battle_status.short_description = 'Location'
    
    def combat_strength(self, obj):
        return f"{obj.get_combat_strength():,}"
    combat_strength.short_description = 'Combat Power'


@admin.register(Battle)
class BattleAdmin(admin.ModelAdmin):
    list_display = ('battle_id', 'attacker', 'defender', 'territory_coordinates', 'result', 'status', 'battle_time', 'started_at')
    list_filter = ('result', 'status', 'started_at')
    search_fields = ('attacker__name', 'defender__name')
    readonly_fields = ('started_at', 'battle_log')
    
    def battle_id(self, obj):
        return f"Battle #{obj.id}"
    battle_id.short_description = 'ID'
    
    def territory_coordinates(self, obj):
        return format_html('({}, {})', obj.territory.x, obj.territory.y)
    territory_coordinates.short_description = 'Territory'
    
    def battle_time(self, obj):
        if obj.battle_occurs:
            if timezone.now() < obj.battle_occurs:
                return format_html('<span style="color: orange;">⏱️ Pending</span>')
            else:
                return format_html('<span style="color: green;">⚔️ Occurred</span>')
        return '-'
    battle_time.short_description = 'Battle Time'


@admin.register(Alliance)
class AllianceAdmin(admin.ModelAdmin):
    list_display = ('name', 'leader', 'member_count', 'total_power', 'treasury_summary', 'is_open', 'created_at')
    list_filter = ('is_open', 'created_at')
    search_fields = ('name', 'leader__name')
    filter_horizontal = ('members', 'war_declarations', 'non_aggression_pacts')
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'
    
    def treasury_summary(self, obj):
        # Format numbers and build HTML string directly
        energy_str = f"{int(obj.treasury_energy):,}"
        minerals_str = f"{int(obj.treasury_minerals):,}"
        food_str = f"{int(obj.treasury_food):,}"
        
        html = f'⚡{energy_str} | ⛏{minerals_str} | 🌾{food_str}'
        return mark_safe(html)
    treasury_summary.short_description = 'Treasury'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'subject', 'message_type', 'sent_at', 'read_status')
    list_filter = ('message_type', 'sent_at', 'read_at')
    search_fields = ('sender__name', 'receiver__name', 'subject')
    readonly_fields = ('sent_at',)
    
    def read_status(self, obj):
        if obj.read_at:
            return format_html('<span style="color: green;">✅ Read</span>')
        return format_html('<span style="color: orange;">📩 Unread</span>')
    read_status.short_description = 'Status'


@admin.register(TradeOffer)
class TradeOfferAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'status', 'offer_summary', 'request_summary', 'created_at', 'expires_at', 'is_expired')
    list_filter = ('status', 'created_at')
    search_fields = ('sender__name', 'receiver__name')
    readonly_fields = ('created_at', 'responded_at')
    
    def offer_summary(self, obj):
        # Format numbers and build HTML string directly
        energy_str = f"{int(obj.offer_energy):,}"
        minerals_str = f"{int(obj.offer_minerals):,}"
        food_str = f"{int(obj.offer_food):,}"
        
        html = f'⚡{energy_str} | ⛏{minerals_str} | 🌾{food_str}'
        return mark_safe(html)
    offer_summary.short_description = 'Offering'
    
    def request_summary(self, obj):
        # Format numbers and build HTML string directly
        energy_str = f"{int(obj.request_energy):,}"
        minerals_str = f"{int(obj.request_minerals):,}"
        food_str = f"{int(obj.request_food):,}"
        
        html = f'⚡{energy_str} | ⛏{minerals_str} | 🌾{food_str}'
        return mark_safe(html)
    request_summary.short_description = 'Requesting'
    
    def is_expired(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">⏰ Expired</span>')
        return format_html('<span style="color: green;">✅ Active</span>')
    is_expired.short_description = 'Expiry Status'


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'tournament_type', 'participant_count', 'max_participants', 'is_active', 'tournament_start', 'registration_status')
    list_filter = ('tournament_type', 'is_active', 'tournament_start')
    search_fields = ('name', 'description')
    filter_horizontal = ('participants',)
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participants'
    
    def registration_status(self, obj):
        now = timezone.now()
        if now < obj.registration_start:
            return format_html('<span style="color: gray;">⏳ Not Started</span>')
        elif now <= obj.registration_end:
            return format_html('<span style="color: green;">📝 Open</span>')
        else:
            return format_html('<span style="color: red;">🚫 Closed</span>')
    registration_status.short_description = 'Registration'


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'achievement_type', 'difficulty', 'is_secret', 'is_repeatable', 'icon', 'earned_count', 'reward_summary')
    list_filter = ('achievement_type', 'difficulty', 'is_secret', 'is_repeatable')
    search_fields = ('name', 'description')
    
    def earned_count(self, obj):
        return obj.empireachievement_set.count()
    earned_count.short_description = 'Times Earned'
    
    def reward_summary(self, obj):
        # Format numbers and build HTML string directly
        energy_str = f"{int(obj.reward_energy):,}"
        minerals_str = f"{int(obj.reward_minerals):,}"
        food_str = f"{int(obj.reward_food):,}"
        technology_str = f"{int(obj.reward_technology):,}"
        
        html = f'⚡{energy_str} | ⛏{minerals_str} | 🌾{food_str} | 🔬{technology_str}'
        return mark_safe(html)
    reward_summary.short_description = 'Rewards'


@admin.register(EmpireAchievement)
class EmpireAchievementAdmin(admin.ModelAdmin):
    list_display = ('empire', 'achievement', 'earned_at')
    list_filter = ('achievement', 'earned_at', 'achievement__difficulty')
    search_fields = ('empire__name', 'achievement__name')
    readonly_fields = ('earned_at',)


@admin.register(ResearchPrerequisite)
class ResearchPrerequisiteAdmin(admin.ModelAdmin):
    list_display = ('research_type', 'prerequisite_research', 'required_level')
    list_filter = ('research_type', 'prerequisite_research')


@admin.register(DiplomaticRelation)
class DiplomaticRelationAdmin(admin.ModelAdmin):
    list_display = ('empire_a', 'empire_b', 'relation_type', 'trust_level', 'trade_modifier', 'created_at', 'expires_at', 'is_expired')
    list_filter = ('relation_type', 'created_at')
    search_fields = ('empire_a__name', 'empire_b__name')
    readonly_fields = ('created_at', 'last_updated')
    
    def is_expired(self, obj):
        if obj.expires_at and timezone.now() > obj.expires_at:
            return format_html('<span style="color: red;">⏰ Expired</span>')
        return format_html('<span style="color: green;">✅ Active</span>')
    is_expired.short_description = 'Status'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'channel_type', 'message_preview', 'sent_at', 'is_system_message', 'target_info')
    list_filter = ('channel_type', 'sent_at', 'is_system_message', 'is_announcement')
    search_fields = ('sender__name', 'message')
    readonly_fields = ('sent_at',)
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
    
    def target_info(self, obj):
        if obj.alliance:
            return format_html('Alliance: {}', obj.alliance.name)
        elif obj.private_recipient:
            return format_html('Private: {}', obj.private_recipient.name)
        return 'Global'
    target_info.short_description = 'Target'


@admin.register(TerrainMonster)
class TerrainMonsterAdmin(admin.ModelAdmin):
    list_display = ('monster_type', 'size', 'level', 'territory_coordinates', 'combat_strength', 'loot_summary', 'status', 'last_defeated')
    list_filter = ('monster_type', 'level', 'last_defeated')
    search_fields = ('territory__x', 'territory__y')
    
    def territory_coordinates(self, obj):
        return format_html('({}, {})', obj.territory.x, obj.territory.y)
    territory_coordinates.short_description = 'Territory'
    
    def combat_strength(self, obj):
        return f"{obj.get_combat_strength():,}"
    combat_strength.short_description = 'Combat Power'
    
    def loot_summary(self, obj):
        loot = obj.get_loot_rewards()
        # Format numbers and build HTML string directly
        energy_str = f"{int(loot['energy']):,}"
        minerals_str = f"{int(loot['minerals']):,}"
        food_str = f"{int(loot['food']):,}"
        
        html = f'⚡{energy_str} | ⛏{minerals_str} | 🌾{food_str}'
        return mark_safe(html)
    loot_summary.short_description = 'Loot'
    
    def status(self, obj):
        if obj.size <= 0:
            if obj.respawn_time and timezone.now() < obj.respawn_time:
                return format_html('<span style="color: orange;">💀 Respawning</span>')
            else:
                return format_html('<span style="color: red;">💀 Defeated</span>')
        return format_html('<span style="color: green;">👹 Alive</span>')
    status.short_description = 'Status'


@admin.register(WorldEvent)
class WorldEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'is_active', 'started_at', 'ends_at', 'affected_count', 'time_remaining')
    list_filter = ('event_type', 'is_active', 'started_at')
    search_fields = ('title', 'description')
    readonly_fields = ('started_at',)
    filter_horizontal = ('affected_territories',)
    
    def affected_count(self, obj):
        return obj.affected_territories.count()
    affected_count.short_description = 'Affected Territories'
    
    def time_remaining(self, obj):
        if obj.is_active and obj.ends_at:
            remaining = obj.ends_at - timezone.now()
            if remaining.total_seconds() > 0:
                days = remaining.days
                hours = remaining.seconds // 3600
                return f"{days}d {hours}h"
            else:
                return format_html('<span style="color: red;">Ended</span>')
        return '-'
    time_remaining.short_description = 'Time Left'


@admin.register(GameStats)
class GameStatsAdmin(admin.ModelAdmin):
    list_display = ('total_players', 'total_battles', 'total_territories_conquered', 'current_top_empire', 'updated_at')
    readonly_fields = ('updated_at',)
    
    def has_add_permission(self, request):
        # Only allow one GameStats instance
        return not GameStats.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of GameStats
        return False

# Customize admin site
admin.site.site_header = "Nova Terra: Kingdoms War - Admin Dashboard"
admin.site.site_title = "Nova Terra Admin"
admin.site.index_title = "Game Management Dashboard"
