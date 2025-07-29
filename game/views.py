from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from .models import (
    Empire, Territory, Building, Research, Army, Battle, Alliance, Message, 
    WorldEvent, GameStats, TerrainMonster, TradeOffer, Tournament, Achievement,
    EmpireAchievement, ResearchPrerequisite, DiplomaticRelation, ChatMessage,
    RecruitmentBatch
)
import json
import random
from django.views.decorators.http import require_POST
from datetime import timedelta


@login_required
def dashboard_view(request):
    """Main dashboard view"""
    empire = request.user.empire
    
    # Generate resources if time has passed
    empire.generate_resources()
    
    # Get recent activity
    recent_battles = Battle.objects.filter(
        Q(attacker=empire) | Q(defender=empire)
    ).order_by('-started_at')[:5]
    
    recent_messages = Message.objects.filter(receiver=empire).order_by('-sent_at')[:5]
    
    # Get active world events
    active_events = WorldEvent.objects.filter(
        is_active=True,
        ends_at__gt=timezone.now()
    )
    
    # Get building counts by type
    energy_buildings = empire.buildings.filter(building_type='power_plant')
    mineral_buildings = empire.buildings.filter(building_type='mine')
    food_buildings = empire.buildings.filter(building_type='farm')
    research_buildings = empire.buildings.filter(building_type='research_lab')
    
    # Get ongoing attacks
    ongoing_attacks = Battle.objects.filter(
        attacker=empire,
        status__in=['traveling', 'fighting', 'returning']
    ).order_by('battle_occurs')
    
    # Get incoming attacks
    incoming_attacks = Battle.objects.filter(
        defender=empire,
        status__in=['traveling', 'fighting']
    ).order_by('battle_occurs')
    
    context = {
        'empire': empire,
        'recent_battles': recent_battles,
        'recent_messages': recent_messages,
        'active_events': active_events,
        'energy_buildings': energy_buildings,
        'mineral_buildings': mineral_buildings,
        'food_buildings': food_buildings,
        'research_buildings': research_buildings,
        'ongoing_attacks': ongoing_attacks,
        'incoming_attacks': incoming_attacks,
    }
    
    return render(request, 'game/dashboard.html', context)


@login_required
def map_view(request):
    """World map view - Full 50x50 world"""
    empire = request.user.empire
    
    # Generate complete 50x50 map data
    map_data = []
    
    for y in range(50):
        row = []
        for x in range(50):
            try:
                territory = Territory.objects.get(x=x, y=y)
            except Territory.DoesNotExist:
                # Only create new territories if they don't exist
                # Use balanced terrain distribution for new territories
                remaining_territories = 2500 - Territory.objects.count()
                if remaining_territories > 100:
                    # Still have room for special terrains
                    terrain_type = random.choices(
                        ['plains', 'mountains', 'desert', 'forest', 'water', 'volcanic'],
                        weights=[85, 3, 3, 3, 3, 3]
                    )[0]
                else:
                    # Mostly plains for remaining spots
                    terrain_type = 'plains'
                
                resource_bonus = random.choice(['energy', 'minerals', 'food', 'none', 'none', 'none'])
                defense_bonus = random.randint(0, 10)
                
                territory = Territory.objects.create(
                    x=x, y=y,
                    terrain_type=terrain_type,
                    resource_bonus=resource_bonus,
                    defense_bonus=defense_bonus
                )
                
                # Create monsters for unoccupied territories (25% chance)
                if not territory.owner and random.random() < 0.25:
                    create_territory_monsters(territory)
            
            row.append(territory)
        map_data.append(row)
    
    context = {
        'empire': empire,
        'map_data': map_data,
    }
    
    return render(request, 'game/map.html', context)


@login_required
def buildings_view(request):
    """Buildings management"""
    empire = request.user.empire
    
    # Complete any finished building upgrades
    for building in empire.buildings.all():
        building.complete_upgrade()
    
    # Update empire population and power
    empire.calculate_power()  # This will update population as well
    
    buildings = empire.buildings.all().order_by('territory__x', 'territory__y')
    territories = empire.territories.all()
    
    # Add empty slots data for each territory
    territories_with_slots = []
    for territory in territories:
        building_count = territory.buildings.count()
        empty_slots_count = max(0, 7 - building_count)  # Max 7 buildings per territory
        territory.empty_slots = list(range(empty_slots_count))  # Add empty slots as a list
        territories_with_slots.append(territory)
    
    # Calculate upgrade costs for display
    upgrade_costs = {}
    for building in buildings:
        # Use the same calculation function used by the API for consistency
        upgrade_cost = calculate_building_cost(building.building_type, building.level + 1)
        upgrade_costs[building.id] = upgrade_cost
    
    return render(request, 'game/buildings.html', {
        'empire': empire,
        'buildings': buildings,
        'territories': territories_with_slots,
        'upgrade_costs': upgrade_costs,
    })


@login_required
def building_detail_view(request, building_id):
    """Individual building management page"""
    empire = request.user.empire
    
    try:
        building = Building.objects.get(id=building_id, empire=empire)
    except Building.DoesNotExist:
        messages.error(request, 'Building not found or access denied.')
        return redirect('game:buildings')
    
    # Complete any finished upgrades
    building.complete_upgrade()
    
    # Calculate upgrade cost
    upgrade_cost = calculate_building_cost(building.building_type, building.level + 1)
    can_afford_upgrade = can_afford(empire, upgrade_cost)
    
    # Get specific data based on building type
    context_data = {
        'empire': empire,
        'building': building,
        'upgrade_cost': upgrade_cost,
        'can_afford': can_afford_upgrade,
    }
    
    # Add building-specific data
    if building.building_type == 'barracks':
        # For barracks, add military recruitment capabilities
        armies = empire.armies.filter(territory=building.territory)
        context_data.update({
            'armies': armies,
            'can_recruit': True,
        })
    elif building.building_type == 'research_lab':
        # For research lab, add research capabilities
        research_list = Research.objects.filter(empire=empire)
        context_data.update({
            'research_list': research_list,
        })
    elif building.building_type == 'spy_network':
        # For spy network, add intelligence data
        range_territories = building.level * 2
        context_data.update({
            'intelligence_range': range_territories,
        })
    
    # Choose template based on building type
    if building.building_type == 'barracks':
        template = 'game/building/barracks_detail.html'
    else:
        template = 'game/building/default_detail.html'
    
    return render(request, template, context_data)


@login_required
def research_view(request):
    """Research management"""
    empire = request.user.empire
    
    # Get or create research entries with new medieval types
    research_types = [
        'warfare_tactics', 'fortification_arts', 'resource_alchemy',
        'agricultural_mastery', 'mining_expertise', 'royal_engineering', 
        'diplomatic_arts'
    ]
    
    research_list = []
    for research_type in research_types:
        research, created = Research.objects.get_or_create(
            empire=empire,
            research_type=research_type
        )
        # Check if research is complete and needs to be finished
        if research.research_started and research.research_complete:
            research.complete_research()
        research_list.append(research)
    
    context = {
        'empire': empire,
        'research_list': research_list,
    }
    
    return render(request, 'game/research.html', context)


@login_required
def research_detail_view(request, research_type):
    """Research detail page"""
    empire = request.user.empire
    
    # Get or create research
    research, created = Research.objects.get_or_create(
        empire=empire,
        research_type=research_type
    )
    
    # Check if research is complete
    if research.research_started and research.research_complete:
        research.complete_research()
    
    # Get research benefits and costs
    benefits = research.get_research_benefits()
    cost = research.get_research_cost()
    
    context = {
        'empire': empire,
        'research': research,
        'benefits': benefits,
        'cost': cost,
    }
    
    return render(request, 'game/research_detail.html', context)


@login_required
def military_view(request):
    """Military management"""
    empire = request.user.empire
    
    # Update recruitment progress for all batches
    for batch in empire.recruitment_batches.filter(is_completed=False):
        batch.update_progress()
    
    # Show armies that are present in territories (available for attack/defense)
    territories = empire.territories.all()
    available_armies_by_territory = {}
    for territory in territories:
        armies = territory.get_available_armies()
        # Add combat strength per unit to each army
        for army in armies:
            army.combat_per_unit = army.get_combat_strength_per_unit()
        available_armies_by_territory[territory.id] = armies
    
    # Get active recruitment batches for the recruitment section
    recruiting_batches = empire.recruitment_batches.filter(is_completed=False).order_by('recruitment_started')
    
    # Get ongoing attacks
    ongoing_attacks = Battle.objects.filter(
        attacker=empire,
        status__in=['traveling', 'fighting', 'returning']
    ).order_by('battle_occurs')
    
    # Get unit combat stats for dynamic recruitment UI
    unit_stats = Army.get_unit_combat_stats()
    unit_data = []
    for unit_type, stats in unit_stats.items():
        unit_info = {
            'type': unit_type,
            'display_name': unit_type.replace('_', ' ').title(),
            'attack': stats['attack'],
            'def_infantry': stats.get('def_infantry', 0),
            'def_archer': stats.get('def_archer', 0),
            'def_spearmen': stats.get('def_spearmen', 0),
            'def_heavy_knights': stats.get('def_heavy_knights', 0),
            'def_royal_knights': stats.get('def_royal_knights', 0),
            'def_spies': stats.get('def_spies', 0),
            'storage': stats['storage'],
            'speed': stats['speed'],
            'description': stats['description'],
            'training_cost': stats['training_cost'],
            'training_time': stats['training_time'],
            'special': stats.get('special', ''),
        }
        unit_data.append(unit_info)
    
    context = {
        'empire': empire,
        'available_armies_by_territory': available_armies_by_territory,  # Dict of territory_id -> available armies
        'recruiting_batches': recruiting_batches,  # Active recruitment batches
        'territories': territories,
        'ongoing_attacks': ongoing_attacks,
        'unit_data': unit_data,
    }
    
    return render(request, 'game/military.html', context)


@login_required
def diplomacy_view(request):
    """Diplomacy and alliances"""
    empire = request.user.empire
    
    # Get messages
    received_messages = empire.received_messages.order_by('-sent_at')[:20]
    sent_messages = empire.sent_messages.order_by('-sent_at')[:20]
    
    # Get alliances
    alliances = Alliance.objects.all()
    empire_alliances = empire.alliances.all()
    
    # Get available empires for messaging (exclude self and bots)
    available_empires = Empire.objects.exclude(
        Q(id=empire.id) | Q(is_master_player=True)
    ).order_by('name')
    
    context = {
        'empire': empire,
        'received_messages': received_messages,
        'sent_messages': sent_messages,
        'alliances': alliances,
        'empire_alliances': empire_alliances,
        'available_empires': available_empires,
    }
    
    return render(request, 'game/diplomacy.html', context)


@login_required
@csrf_exempt
def get_invitations_api(request):
    """API for getting alliance invitations"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    
    try:
        # Get pending alliance invitations
        invitations = empire.received_messages.filter(
            message_type='alliance_invite',
            subject__startswith='Alliance Invitation:'
        ).order_by('-sent_at')
        
        invitation_list = []
        for msg in invitations:
            # Parse alliance info from message content
            try:
                alliance_name = msg.subject.replace('Alliance Invitation: ', '')
                sender_alliance = msg.sender.alliances.first()
                
                if sender_alliance and sender_alliance.name == alliance_name:
                    invitation_list.append({
                        'id': msg.id,
                        'alliance_name': alliance_name,
                        'sender_name': msg.sender.name,
                        'member_count': sender_alliance.members.count(),
                        'message': msg.content,
                        'sent_at': msg.sent_at.isoformat()
                    })
            except:
                continue
        
        return JsonResponse({
            'success': True,
            'invitations': invitation_list
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def respond_invitation_api(request):
    """API for responding to alliance invitations"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    invitation_id = data.get('invitation_id')
    action = data.get('action')  # 'accept' or 'decline'
    
    try:
        # Get the invitation message
        invitation = Message.objects.get(
            id=invitation_id,
            receiver=empire,
            message_type='alliance_invite'
        )
        
        # Parse alliance name from subject
        alliance_name = invitation.subject.replace('Alliance Invitation: ', '')
        sender_alliance = invitation.sender.alliances.first()
        
        if not sender_alliance or sender_alliance.name != alliance_name:
            return JsonResponse({'error': 'Alliance no longer exists'})
        
        if action == 'accept':
            # Check if alliance is full
            if sender_alliance.members.count() >= 10:
                return JsonResponse({'error': 'Alliance is full (max 10 members)'})
            
            # Check if player is already in an alliance
            if empire.alliances.exists():
                return JsonResponse({'error': 'You are already in an alliance. Leave your current alliance first.'})
            
            # Add player to alliance
            sender_alliance.members.add(empire)
            
            # Send confirmation message to alliance leader
            Message.objects.create(
                sender=empire,
                receiver=invitation.sender,
                subject=f'Alliance Invitation Accepted: {alliance_name}',
                content=f'{empire.name} has accepted the invitation to join {alliance_name}!',
                message_type='alliance_invite'
            )
            
            # Delete the invitation
            invitation.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully joined {alliance_name}!'
            })
            
        elif action == 'decline':
            # Send decline message to alliance leader
            Message.objects.create(
                sender=empire,
                receiver=invitation.sender,
                subject=f'Alliance Invitation Declined: {alliance_name}',
                content=f'{empire.name} has declined the invitation to join {alliance_name}.',
                message_type='alliance_invite'
            )
            
            # Delete the invitation
            invitation.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Declined invitation to {alliance_name}'
            })
        
        else:
            return JsonResponse({'error': 'Invalid action'})
        
    except Message.DoesNotExist:
        return JsonResponse({'error': 'Invitation not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def get_available_players_api(request):
    """API for getting players available to invite to alliance"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    
    try:
        # Check if player is an alliance leader
        current_alliance = empire.alliances.filter(leader=empire).first()
        if not current_alliance:
            return JsonResponse({'error': 'You must be an alliance leader to invite players'})
        
        # Get players not in any alliance (excluding bots)
        independent_players = Empire.objects.filter(
            is_master_player=False
        ).exclude(
            Q(id=empire.id) | Q(alliances__isnull=False)
        ).order_by('-power_level')
        
        # Also get players in other alliances (they can be poached)
        other_alliance_players = Empire.objects.filter(
            is_master_player=False,
            alliances__isnull=False
        ).exclude(
            Q(id=empire.id) | Q(alliances=current_alliance)
        ).order_by('-power_level')
        
        player_list = []
        
        # Add independent players first
        for player in independent_players:
            player_list.append({
                'id': player.id,
                'name': player.name,
                'power_level': player.power_level,
                'territories_count': player.territories.count(),
                'current_alliance': None
            })
        
        # Add players from other alliances
        for player in other_alliance_players:
            current_ally = player.alliances.first()
            player_list.append({
                'id': player.id,
                'name': player.name,
                'power_level': player.power_level,
                'territories_count': player.territories.count(),
                'current_alliance': current_ally.name if current_ally else None
            })
        
        return JsonResponse({
            'success': True,
            'players': player_list[:50]  # Limit to 50 players for performance
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def invite_player_api(request):
    """API for inviting a player to alliance"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    player_id = data.get('player_id')
    alliance_id = data.get('alliance_id')
    
    try:
        # Verify alliance leadership
        alliance = Alliance.objects.get(id=alliance_id, leader=empire)
        target_player = Empire.objects.get(id=player_id, is_master_player=False)
        
        # Check if alliance is full
        if alliance.members.count() >= 10:
            return JsonResponse({'error': 'Alliance is full (max 10 members)'})
        
        # Check if player is already in this alliance
        if target_player in alliance.members.all():
            return JsonResponse({'error': f'{target_player.name} is already in your alliance'})
        
        # Check if invitation already exists
        existing_invitation = Message.objects.filter(
            sender=empire,
            receiver=target_player,
            message_type='alliance_invite',
            subject=f'Alliance Invitation: {alliance.name}'
        ).exists()
        
        if existing_invitation:
            return JsonResponse({'error': f'Invitation already sent to {target_player.name}'})
        
        # Send invitation message
        Message.objects.create(
            sender=empire,
            receiver=target_player,
            subject=f'Alliance Invitation: {alliance.name}',
            content=f"""You have been invited to join the alliance "{alliance.name}"!

Alliance Leader: {empire.name}
Current Members: {alliance.members.count()}/10
Alliance Description: {alliance.description or 'No description provided.'}

Alliance Benefits:
• +10% Attack Power in all battles
• +5% Defense when defending allied territories
• Shared intelligence networks
• Coordinated military campaigns
• Resource sharing opportunities

Use the Diplomacy page to accept or decline this invitation.""",
            message_type='alliance_invite'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Invitation sent to {target_player.name}!'
        })
        
    except Alliance.DoesNotExist:
        return JsonResponse({'error': 'Alliance not found or you are not the leader'})
    except Empire.DoesNotExist:
        return JsonResponse({'error': 'Player not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def request_join_api(request):
    """API for requesting to join an open alliance"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    alliance_id = data.get('alliance_id')
    
    try:
        alliance = Alliance.objects.get(id=alliance_id)
        
        # Check if alliance is open
        if not alliance.is_open:
            return JsonResponse({'error': 'This alliance is not accepting public requests'})
        
        # Check if alliance is full
        if alliance.members.count() >= 10:
            return JsonResponse({'error': 'Alliance is full (max 10 members)'})
        
        # Check if player is already in an alliance
        if empire.alliances.exists():
            return JsonResponse({'error': 'You are already in an alliance. Leave your current alliance first.'})
        
        # Check if player is already in this alliance
        if empire in alliance.members.all():
            return JsonResponse({'error': 'You are already in this alliance'})
        
        # Add player to alliance immediately (since it's open)
        alliance.members.add(empire)
        
        # Send notification to alliance leader
        Message.objects.create(
            sender=empire,
            receiver=alliance.leader,
            subject=f'New Member Joined: {alliance.name}',
            content=f'{empire.name} has joined the alliance {alliance.name}!',
            message_type='alliance_invite'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully joined {alliance.name}!'
        })
        
    except Alliance.DoesNotExist:
        return JsonResponse({'error': 'Alliance not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def leave_alliance_api(request):
    """API for leaving an alliance"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    alliance_id = data.get('alliance_id')
    
    try:
        alliance = Alliance.objects.get(id=alliance_id)
        
        # Check if player is in this alliance
        if empire not in alliance.members.all():
            return JsonResponse({'error': 'You are not in this alliance'})
        
        # Remove player from alliance
        alliance.members.remove(empire)
        
        # If this was the leader leaving, transfer leadership or delete alliance
        if alliance.leader == empire:
            remaining_members = alliance.members.all()
            if remaining_members.exists():
                # Transfer leadership to first remaining member
                new_leader = remaining_members.first()
                alliance.leader = new_leader
                alliance.save()
                
                # Notify new leader
                Message.objects.create(
                    sender=empire,
                    receiver=new_leader,
                    subject=f'Alliance Leadership Transferred: {alliance.name}',
                    content=f'You have been appointed as the new leader of {alliance.name} after {empire.name} left the alliance.',
                    message_type='alliance_invite'
                )
            else:
                # No members left, delete alliance
                alliance.delete()
                return JsonResponse({
                    'success': True,
                    'message': f'Left alliance {alliance.name}. Alliance disbanded due to no remaining members.'
                })
        
        # Notify remaining members
        for member in alliance.members.all():
            Message.objects.create(
                sender=empire,
                receiver=member,
                subject=f'Member Left Alliance: {alliance.name}',
                content=f'{empire.name} has left the alliance {alliance.name}.',
                message_type='alliance_invite'
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully left {alliance.name}'
        })
        
    except Alliance.DoesNotExist:
        return JsonResponse({'error': 'Alliance not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def remove_member_api(request):
    """API for removing a member from alliance (leaders only)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    member_id = data.get('member_id')
    alliance_id = data.get('alliance_id')
    
    try:
        alliance = Alliance.objects.get(id=alliance_id, leader=empire)
        member_to_remove = Empire.objects.get(id=member_id)
        
        # Check if member is in this alliance
        if member_to_remove not in alliance.members.all():
            return JsonResponse({'error': 'Player is not in this alliance'})
        
        # Can't remove self
        if member_to_remove == empire:
            return JsonResponse({'error': 'Cannot remove yourself. Use leave alliance instead.'})
        
        # Remove member
        alliance.members.remove(member_to_remove)
        
        # Send notification to removed member
        Message.objects.create(
            sender=empire,
            receiver=member_to_remove,
            subject=f'Removed from Alliance: {alliance.name}',
            content=f'You have been removed from the alliance {alliance.name} by {empire.name}.',
            message_type='alliance_invite'
        )
        
        # Notify other members
        for member in alliance.members.all():
            if member != empire:  # Don't notify the leader who performed the action
                Message.objects.create(
                    sender=empire,
                    receiver=member,
                    subject=f'Member Removed: {alliance.name}',
                    content=f'{member_to_remove.name} has been removed from the alliance by {empire.name}.',
                    message_type='alliance_invite'
                )
        
        return JsonResponse({
            'success': True,
            'message': f'Removed {member_to_remove.name} from the alliance'
        })
        
    except Alliance.DoesNotExist:
        return JsonResponse({'error': 'Alliance not found or you are not the leader'})
    except Empire.DoesNotExist:
        return JsonResponse({'error': 'Member not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def toggle_alliance_open_api(request):
    """API for toggling alliance open/closed status (leaders only)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    alliance_id = data.get('alliance_id')
    
    try:
        alliance = Alliance.objects.get(id=alliance_id, leader=empire)
        
        # Toggle the status
        alliance.is_open = not alliance.is_open
        alliance.save()
        
        status_text = "open for public recruitment" if alliance.is_open else "invite-only"
        
        return JsonResponse({
            'success': True,
            'message': f'Alliance is now {status_text}',
            'is_open': alliance.is_open
        })
        
    except Alliance.DoesNotExist:
        return JsonResponse({'error': 'Alliance not found or you are not the leader'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def rankings_view(request):
    """Global rankings"""
    empire = request.user.empire
    
    # Update all empire power levels
    for emp in Empire.objects.all():
        emp.calculate_power()
    
    # Get top empires by power
    top_empires = Empire.objects.order_by('-power_level')[:50]
    
    # Update ranks
    for rank, emp in enumerate(top_empires, 1):
        emp.rank = rank
        emp.save()
    
    context = {
        'empire': empire,
        'top_empires': top_empires,
    }
    
    return render(request, 'game/rankings.html', context)


@login_required
def events_view(request):
    """World events"""
    empire = request.user.empire
    
    active_events = WorldEvent.objects.filter(
        is_active=True,
        ends_at__gt=timezone.now()
    ).order_by('-started_at')
    
    past_events = WorldEvent.objects.filter(
        is_active=False
    ).order_by('-started_at')[:10]
    
    context = {
        'empire': empire,
        'active_events': active_events,
        'past_events': past_events,
    }
    
    return render(request, 'game/events.html', context)


@login_required
def reports_view(request):
    """Attack reports and battle history"""
    empire = request.user.empire
    
    # Get all battles involving this empire
    battles = Battle.objects.filter(
        Q(attacker=empire) | Q(defender=empire)
    ).order_by('-started_at')[:50]
    
    # Get ongoing attacks
    ongoing_attacks = Battle.objects.filter(
        attacker=empire,
        status__in=['traveling', 'fighting', 'returning']
    ).order_by('battle_occurs')
    
    # Get incoming attacks
    incoming_attacks = Battle.objects.filter(
        defender=empire,
        status__in=['traveling', 'fighting']
    ).order_by('battle_occurs')
    
    context = {
        'empire': empire,
        'battles': battles,
        'ongoing_attacks': ongoing_attacks,
        'incoming_attacks': incoming_attacks,
    }
    
    return render(request, 'game/reports.html', context)


@login_required
def battle_report_detail_view(request, battle_id):
    """Detailed view of a single battle report"""
    empire = request.user.empire
    
    try:
        battle = Battle.objects.filter(
            id=battle_id
        ).filter(
            Q(attacker=empire) | Q(defender=empire)
        ).get()
    except Battle.DoesNotExist:
        messages.error(request, 'Battle report not found.')
        return redirect('game:reports')
    
    # Prepare unit data for the template
    attacker_units = {}
    attacker_casualties = {}
    defender_units = {}
    defender_casualties = {}
    
    # Process attacking armies
    for army_data in battle.attacking_armies.values():
        unit_type = army_data['unit_type']
        # Normalize unit type names
        if 'Infantry' in unit_type:
            key = 'Infantry'
        elif 'Archers' in unit_type:
            key = 'Archers'
        elif 'Spearmen' in unit_type:
            key = 'Spearmen'
        elif 'Heavy Knights' in unit_type:
            key = 'Cavalry'
        elif 'Royal Knights' in unit_type:
            key = 'Cavalry'
        elif 'Spies' in unit_type:
            key = 'Spies'
        else:
            key = 'Other'
        
        attacker_units[key] = attacker_units.get(key, 0) + army_data.get('size', 0)
        attacker_casualties[key] = attacker_casualties.get(key, 0) + army_data.get('losses', 0)
    
    # Process defending armies
    for army_data in battle.defending_armies.values():
        unit_type = army_data['unit_type']
        # Normalize unit type names
        if 'Infantry' in unit_type:
            key = 'Infantry'
        elif 'Archers' in unit_type:
            key = 'Archers'
        elif 'Spearmen' in unit_type:
            key = 'Spearmen'
        elif 'Heavy Knights' in unit_type:
            key = 'Cavalry'
        elif 'Royal Knights' in unit_type:
            key = 'Cavalry'
        elif 'Spies' in unit_type:
            key = 'Spies'
        elif 'Monster' in unit_type or 'Wolf' in unit_type or 'Giant' in unit_type or 'Scorpion' in unit_type or 'Treant' in unit_type or 'Kraken' in unit_type or 'Dragon' in unit_type:
            key = 'Monsters'
        else:
            key = 'Other'
        
        defender_units[key] = defender_units.get(key, 0) + army_data.get('size', 0)
        defender_casualties[key] = defender_casualties.get(key, 0) + army_data.get('losses', 0)
    
    # Calculate attack and defense bonuses
    attacker_attack_bonus = 0
    attacker_barracks_bonus = 0
    attacker_research_bonus = 0
    
    if battle.attacker:
        # Military tactics research bonus
        military_research = battle.attacker.research.filter(research_type='military_tactics').first()
        if military_research:
            attacker_research_bonus = military_research.level * 10
        
        # Alliance bonus
        if battle.attacker.alliances.exists():
            attacker_attack_bonus += 10
        
        # Barracks bonus (if attacker has barracks)
        barracks = Building.objects.filter(empire=battle.attacker, building_type='barracks').first()
        if barracks:
            attacker_barracks_bonus = barracks.level * 5
    
    defender_defense_bonus = 0
    defender_walls_bonus = 0
    defender_research_bonus = 0
    
    if battle.defender:
        # Defense systems research bonus
        defense_research = battle.defender.research.filter(research_type='defense_systems').first()
        if defense_research:
            defender_research_bonus = defense_research.level * 8
        
        # Defense system building bonus
        defense_system = Building.objects.filter(empire=battle.defender, building_type='defense_system').first()
        if defense_system:
            defender_walls_bonus = defense_system.level * 5
        
        # Territory defense bonus
        if battle.territory:
            defender_defense_bonus = battle.territory.defense_bonus
    
    context = {
        'empire': empire,
        'battle': battle,
        'attacker_units': attacker_units,
        'attacker_casualties': attacker_casualties,
        'defender_units': defender_units,
        'defender_casualties': defender_casualties,
        'attacker_attack_bonus': attacker_attack_bonus,
        'attacker_barracks_bonus': attacker_barracks_bonus,
        'attacker_research_bonus': attacker_research_bonus,
        'defender_defense_bonus': defender_defense_bonus,
        'defender_walls_bonus': defender_walls_bonus,
        'defender_research_bonus': defender_research_bonus,
    }
    
    return render(request, 'game/battle_report_detail.html', context)


# API Views for game actions

@login_required
@csrf_exempt
def build_api(request):
    """API for building construction"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    building_type = data.get('building_type')
    territory_id = data.get('territory_id')
    
    try:
        territory = Territory.objects.get(id=territory_id, owner=empire)
        
        # Check if building already exists
        existing = Building.objects.filter(
            territory=territory,
            building_type=building_type
        ).first()
        
        if existing:
            # Upgrade existing building
            if existing.level >= 100:
                return JsonResponse({'error': f'{existing.get_building_type_display()} is already at maximum level (100)!'})
            
            if existing.can_upgrade():
                cost = calculate_building_cost(building_type, existing.level + 1)
                if can_afford(empire, cost):
                    deduct_resources(empire, cost)
                    existing.start_upgrade()
                    # Recalculate production rates after upgrade starts
                    empire.calculate_production_rates()
                    return JsonResponse({
                        'success': True,
                        'message': f'{existing.get_building_type_display()} upgrade to Lv.{existing.level + 1} started!'
                    })
                else:
                    return JsonResponse({'error': 'Insufficient resources for upgrade'})
            else:
                return JsonResponse({'error': 'Building is already upgrading'})
        else:
            # Check building limit per territory
            building_count = territory.buildings.count()
            max_buildings = Building.max_buildings_per_territory()
            
            if building_count >= max_buildings:
                return JsonResponse({'error': f'Territory can only have {max_buildings} buildings maximum!'})
            
            # Build new building
            cost = calculate_building_cost(building_type, 1)
            if can_afford(empire, cost):
                deduct_resources(empire, cost)
                Building.objects.create(
                    empire=empire,
                    territory=territory,
                    building_type=building_type
                )
                # Recalculate production rates after new building
                empire.calculate_production_rates()
                return JsonResponse({
                    'success': True,
                    'message': f'{building_type.replace("_", " ").title()} built successfully!'
                })
            else:
                return JsonResponse({'error': 'Insufficient resources to build'})
    
    except Territory.DoesNotExist:
        return JsonResponse({'error': 'Territory not found or not owned by you'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def research_api(request):
    """API for starting research"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    research_type = data.get('research_type')
    
    try:
        research = Research.objects.get(empire=empire, research_type=research_type)
        
        # Check if research is already complete
        if research.research_started and research.research_complete:
            if research.complete_research():
                return JsonResponse({
                    'success': True,
                    'message': f'{research.get_research_type_display()} research completed! Now Level {research.level}!'
                })
        
        if research.can_research():
            cost = research.get_research_cost()
            if can_afford(empire, cost):
                deduct_resources(empire, cost)
                research.start_research()
                return JsonResponse({
                    'success': True,
                    'message': f'{research.get_research_type_display()} research started! Will complete in {30 + (research.level * 30)} minutes.'
                })
            else:
                return JsonResponse({'error': 'Insufficient resources'})
        else:
            if research.level >= 100:
                return JsonResponse({'error': 'Research already mastered (Level 100)'})
            else:
                return JsonResponse({'error': 'Research already in progress'})
    
    except Research.DoesNotExist:
        return JsonResponse({'error': 'Research not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def attack_api(request):
    """API for attacking territories with enhanced battle system"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    target_x = data.get('x')
    target_y = data.get('y')
    source_x = data.get('source_x')
    source_y = data.get('source_y')
    army_ids = data.get('army_ids', [])
    
    try:
        with transaction.atomic():
            # Get target territory
            target_territory = Territory.objects.get(x=target_x, y=target_y)
            source_territory = Territory.objects.get(x=source_x, y=source_y, owner=empire)
            
            if target_territory.owner == empire:
                return JsonResponse({'error': 'Cannot attack your own territory'})
            
            # Check if armies are available (not in other battles)
            busy_armies = check_army_availability(army_ids)
            
            if busy_armies:
                busy_army_objects = Army.objects.filter(id__in=busy_armies)
                busy_army_names = [f"{army.get_unit_type_display()} at ({army.territory.x}, {army.territory.y})" 
                                 for army in busy_army_objects]
                return JsonResponse({
                    'error': f'Some armies are already in battle: {", ".join(busy_army_names)}'
                })
            
            # Get attacking armies from the source territory with lock
            attacking_armies = Army.objects.select_for_update().filter(
                id__in=army_ids,
                empire=empire,
                territory=source_territory,
                size__gt=0  # Only armies with units
            )
            
            if not attacking_armies.exists():
                return JsonResponse({'error': 'No valid armies selected from source territory'})
        
            # Create battle record
            battle = Battle.objects.create(
                attacker=empire,
                defender=target_territory.owner,
                territory=target_territory,
                source_territory=source_territory
            )
            
            # Store army data in battle
            battle.attacking_armies = {}
            for army in attacking_armies:
                battle.attacking_armies[str(army.id)] = {
                    'unit_type': army.get_unit_type_display(),
                    'size': army.size,
                    'combat_strength': army.get_combat_strength()
                }
            
            # Store defending army data
            battle.defending_armies = {}
            if target_territory.owner:
                defending_armies = target_territory.owner.armies.filter(territory=target_territory)
                for army in defending_armies:
                    battle.defending_armies[str(army.id)] = {
                        'unit_type': army.get_unit_type_display(),
                        'size': army.size,
                        'combat_strength': army.get_combat_strength()
                    }
            
            battle.save()
            
            # Start the attack sequence
            battle.start_attack()
            
            return JsonResponse({
                'success': True,
                'message': f'Attack launched! Travel time: {battle.travel_time_minutes} minutes.',
                'battle_id': battle.id,
                'distance': battle.distance,
                'travel_time': battle.travel_time_minutes,
                'arrival_time': battle.battle_occurs.isoformat(),
                'return_time': battle.armies_return.isoformat()
            })
    
    except Territory.DoesNotExist:
        return JsonResponse({'error': 'Target territory or source territory not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def map_attack_api(request):
    """API for attacking from map view"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    target_x = data.get('target_x')
    target_y = data.get('target_y')
    
    try:
        target_territory = Territory.objects.get(x=target_x, y=target_y)
        
        if target_territory.owner == empire:
            return JsonResponse({'error': 'Cannot attack your own territory'})
        
        # Find closest empire territory with armies
        empire_territories_with_armies = []
        for territory in empire.territories.all():
            if territory.get_present_armies().exists():
                empire_territories_with_armies.append(territory)
        
        if not empire_territories_with_armies:
            return JsonResponse({'error': 'No territories with available armies for attack'})
        
        # Find closest territory
        closest_territory = None
        min_distance = float('inf')
        
        for territory in empire_territories_with_armies:
            distance = territory.calculate_distance(target_territory)
            if distance < min_distance:
                min_distance = distance
                closest_territory = territory
        
        # Get armies from closest territory
        available_armies = closest_territory.get_present_armies()
        
        return JsonResponse({
            'success': True,
            'source_territory': {
                'id': closest_territory.id,
                'x': closest_territory.x,
                'y': closest_territory.y,
                'distance': min_distance
            },
            'armies': [
                {
                    'id': army.id,
                    'unit_type': army.get_unit_type_display(),
                    'size': army.size,
                    'combat_strength': army.get_combat_strength()
                }
                for army in available_armies
            ]
        })
    
    except Territory.DoesNotExist:
        return JsonResponse({'error': 'Territory not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def battle_status_api(request):
    """API for checking battle status and processing battles"""
    empire = request.user.empire
    
    # Process battles that are ready to execute
    with transaction.atomic():
        # Get battles that need to be executed (with lock to prevent race conditions)
        battles_to_execute = Battle.objects.select_for_update().filter(
            status='traveling',
            battle_occurs__lte=timezone.now()
        )
        
        for battle in battles_to_execute:
            # Double-check status after lock to prevent duplicate execution
            if battle.status == 'traveling':
                battle.execute_battle()
    
    # Process battles that are ready to complete
    with transaction.atomic():
        # Get battles that are ready to complete (with lock)
        battles_to_complete = Battle.objects.select_for_update().filter(
            status='returning',
            armies_return__lte=timezone.now()
        )
        
        for battle in battles_to_complete:
            # Double-check status after lock to prevent duplicate completion
            if battle.status == 'returning':
                battle.complete_attack()
    
    # Get user's battles for display
    user_battles = Battle.objects.filter(
        Q(attacker=empire) | Q(defender=empire)
    ).exclude(status='completed').order_by('-started_at')
    
    # Get incoming attacks with full details
    incoming_attacks = Battle.objects.filter(
        defender=empire,
        status__in=['traveling', 'fighting']
    ).order_by('battle_occurs')
    
    # Get outgoing attacks with full details
    outgoing_attacks = Battle.objects.filter(
        attacker=empire,
        status__in=['traveling', 'fighting', 'returning']
    ).order_by('battle_occurs')
    
    # Convert to serializable format
    incoming_data = []
    for battle in incoming_attacks:
        incoming_data.append({
            'id': battle.id,
            'status': battle.status,
            'attacker': battle.attacker.name,
            'defender': battle.defender.name if battle.defender else 'Neutral',
            'territory': f"({battle.territory.x}, {battle.territory.y})",
            'battle_occurs': battle.battle_occurs.isoformat() if battle.battle_occurs else None,
            'distance': battle.distance,
            'travel_time': battle.travel_time_minutes
        })
    
    outgoing_data = []
    for battle in outgoing_attacks:
        # Calculate total attacking units
        total_units = 0
        if battle.attacking_armies:
            for army_id, army_data in battle.attacking_armies.items():
                if isinstance(army_data, dict) and 'size' in army_data:
                    total_units += army_data.get('size', 0)
        
        # Determine attack type and target
        if battle.target_monster:
            attack_type = "🗡️ Monster Hunt"
            target_name = battle.target_monster.monster_type.replace('_', ' ').title()
        elif battle.defender:
            attack_type = "⚔️ Player Raid"
            target_name = battle.defender.name
        else:
            attack_type = "⚔️ Territory Raid"
            target_name = "Neutral Territory"
        
        outgoing_data.append({
            'id': battle.id,
            'status': battle.status,
            'attacker': battle.attacker.name,
            'defender': battle.defender.name if battle.defender else 'Neutral',
            'territory': f"({battle.territory.x}, {battle.territory.y})",
            'battle_occurs': battle.battle_occurs.isoformat() if battle.battle_occurs else None,
            'armies_return': battle.armies_return.isoformat() if battle.armies_return else None,
            'distance': battle.distance,
            'travel_time': battle.travel_time_minutes,
            'attack_type': attack_type,
            'target_name': target_name,
            'total_units': total_units
        })
    
    return JsonResponse({
        'success': True,
        'battles': user_battles.count(),  # Keep for backward compatibility
        'incoming': incoming_data,
        'outgoing': outgoing_data,
        'processed_battles': len(battles_to_execute) + len(battles_to_complete)
    })


@login_required
@csrf_exempt
def send_message_api(request):
    """API for sending diplomatic messages"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    receiver_id = data.get('receiver_id')
    subject = data.get('subject')
    content = data.get('content')
    message_type = data.get('message_type', 'diplomatic')
    
    try:
        receiver = Empire.objects.get(id=receiver_id)
        
        Message.objects.create(
            sender=empire,
            receiver=receiver,
            subject=subject,
            content=content,
            message_type=message_type
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Message sent successfully!'
        })
    
    except Empire.DoesNotExist:
        return JsonResponse({'error': 'Receiver not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def create_alliance_api(request):
    """API for creating alliances"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    alliance_name = data.get('name')
    description = data.get('description', '')
    
    try:
        alliance = Alliance.objects.create(
            name=alliance_name,
            leader=empire,
            description=description
        )
        alliance.members.add(empire)
        
        return JsonResponse({
            'success': True,
            'message': f'Alliance "{alliance_name}" created successfully!'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def join_alliance_api(request):
    """API for joining alliances"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    alliance_id = data.get('alliance_id')
    
    try:
        alliance = Alliance.objects.get(id=alliance_id)
        
        if empire in alliance.members.all():
            return JsonResponse({'error': 'Already a member of this alliance'})
        
        if alliance.is_open:
            alliance.members.add(empire)
            return JsonResponse({
                'success': True,
                'message': f'Joined alliance "{alliance.name}"!'
            })
        else:
            return JsonResponse({'error': 'Alliance is not open for new members'})
    
    except Alliance.DoesNotExist:
        return JsonResponse({'error': 'Alliance not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def generate_resources_api(request):
    """API for generating resources and updating production rates"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    
    try:
        # Always recalculate production rates first
        empire.calculate_production_rates()
        empire.calculate_storage_capacity()
        
        # Generate resources and get detailed result
        result = empire.generate_resources()
        
        # Add debug information
        debug_info = {
            'last_update': empire.last_resource_update.isoformat(),
            'current_time': timezone.now().isoformat(),
            'production_rates': {
                'energy': empire.energy_production,
                'minerals': empire.mineral_production,
                'food': empire.food_production
            },
            'storage_capacity': {
                'energy': empire.energy_storage,
                'minerals': empire.mineral_storage,
                'food': empire.food_storage
            }
        }
        
        return JsonResponse({
            'success': True,
            'energy': int(empire.energy),  # Ensure integer
            'minerals': int(empire.minerals),  # Ensure integer
            'food': int(empire.food),  # Ensure integer
            'population': int(empire.population),  # Ensure integer
            'energy_production': int(empire.energy_production),  # Ensure integer
            'mineral_production': int(empire.mineral_production),  # Ensure integer
            'food_production': int(empire.food_production),  # Ensure integer
            'energy_storage': int(empire.energy_storage),  # Ensure integer
            'mineral_storage': int(empire.mineral_storage),  # Ensure integer
            'food_storage': int(empire.food_storage),  # Ensure integer
            'generation_result': result,
            'debug': debug_info,
            'timestamp': timezone.now().isoformat()
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e), 'debug': 'Exception in generate_resources_api'})


@login_required
@csrf_exempt
def recruit_api(request):
    """API for recruiting military units - supports multiple batches with queue system"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    territory_id = data.get('territory_id')
    unit_type = data.get('unit_type')
    size = data.get('size', 100)
    
    try:
        territory = Territory.objects.get(id=territory_id, owner=empire)
        
        # Check if we have barracks in this territory
        barracks = empire.buildings.filter(territory=territory, building_type='barracks').first()
        if not barracks:
            return JsonResponse({'error': 'No barracks found in this territory. Build barracks first!'})
        
        # Special check for spies - require Intelligence Hub
        if unit_type == 'spies':
            intelligence_hub = empire.buildings.filter(building_type='intelligence_hub').first()
            if not intelligence_hub:
                return JsonResponse({'error': 'Intelligence Hub required to recruit spies! Build an Intelligence Hub first.'})
        
        # Map old unit type names to new ones for backward compatibility
        unit_type_mapping = {
            'tanks': 'archers',
            'aircraft': 'spearmen', 
            'naval': 'heavy_knights',
            'cyber': 'royal_knights'
        }
        
        # Convert old unit type to new unit type if needed
        mapped_unit_type = unit_type_mapping.get(unit_type, unit_type)
        
        # Calculate recruitment cost
        unit_costs = Army.get_unit_costs()
        if mapped_unit_type not in unit_costs:
            return JsonResponse({'error': 'Invalid unit type'})
        
        cost_per_batch = unit_costs[mapped_unit_type]
        units_per_batch = cost_per_batch['units_per_batch']
        batches = max(1, size / units_per_batch)
        
        total_cost = {
            'energy': int(cost_per_batch['energy'] * batches),
            'minerals': int(cost_per_batch['minerals'] * batches),
            'food': int(cost_per_batch['food'] * batches),
        }
        
        # Check if empire can afford it
        if not can_afford(empire, total_cost):
            return JsonResponse({
                'error': f'Insufficient resources. Need: ⚡{total_cost["energy"]} ⛏{total_cost["minerals"]} 🌾{total_cost["food"]}'
            })
        
        # Deduct resources
        deduct_resources(empire, total_cost)
        
        # Create new recruitment batch using the queue system
        recruitment_batch = RecruitmentBatch.create_new_batch(
            empire=empire,
            territory=territory,
            unit_type=mapped_unit_type,
            target_size=size
        )
        
        # Calculate estimated total time including queue wait
        estimated_time = recruitment_batch.get_estimated_total_time()
        
        # Get queue status
        queue_position = recruitment_batch.queue_position
        total_in_queue = RecruitmentBatch.objects.filter(
            empire=empire,
            territory=territory,
            unit_type=mapped_unit_type,
            status__in=['queued', 'active']
        ).count()
        
        status_message = f'Recruiting {size} {recruitment_batch.get_unit_type_display()} units'
        if queue_position > 0:
            status_message += f' (Position {queue_position + 1} in queue)'
        
        return JsonResponse({
            'success': True,
            'message': status_message,
            'recruitment_time': estimated_time / 60,  # Return in minutes for display
            'batch_id': recruitment_batch.id,
            'queue_position': queue_position,
            'total_in_queue': total_in_queue,
            'status': recruitment_batch.status
        })
    
    except Territory.DoesNotExist:
        return JsonResponse({'error': 'Territory not found or not owned by you'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def update_recruitment_api(request):
    """API for getting recruitment progress updates with queue system"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    
    try:
        recruitment_status = []
        
        # Update and get all recruitment batches (active and queued)
        for batch in empire.recruitment_batches.filter(is_completed=False).order_by('unit_type', 'queue_position'):
            # Update batch progress first
            batch.update_progress()
            
            if not batch.is_completed:
                # Calculate progress and time remaining
                if batch.status == 'active':
                    progress = batch.get_recruitment_progress()
                    time_remaining = batch.get_time_remaining()
                    units_remaining = batch.get_units_remaining()
                    status_display = 'Active'
                elif batch.status == 'queued':
                    progress = 0
                    time_remaining = batch.get_estimated_total_time()
                    units_remaining = batch.target_size
                    status_display = f'Queued (Position {batch.queue_position + 1})'
                else:
                    continue
                
                recruitment_status.append({
                    'batch_id': batch.id,
                    'unit_type': batch.get_unit_type_display(),
                    'target_size': batch.target_size,
                    'progress': round(progress, 1),
                    'territory': f"({batch.territory.x}, {batch.territory.y})",
                    'time_remaining': int(time_remaining),
                    'is_complete': batch.is_completed,
                    'units_remaining': units_remaining,
                    'units_completed': batch.get_units_completed(),
                    'status': batch.status,
                    'status_display': status_display,
                    'queue_position': batch.queue_position,
                    'estimated_total_time': int(batch.get_estimated_total_time())
                })
        
        return JsonResponse({
            'success': True,
            'recruiting_batches': recruitment_status,
            'timestamp': timezone.now().isoformat()
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)})


# Helper functions

def check_army_availability(army_ids):
    """Check if armies are available (not in active battles)"""
    busy_armies = []
    
    if not army_ids:
        return []
    
    # Get all active battles in one query
    active_battles = Battle.objects.filter(
        status__in=['traveling', 'fighting', 'returning']
    ).values('attacking_armies', 'defending_armies')
    
    # Check each army ID
    for army_id in army_ids:
        army_id_str = str(army_id)
        
        for battle in active_battles:
            # Check if army is in attacking armies
            if army_id_str in battle['attacking_armies']:
                busy_armies.append(army_id)
                break
            # Check if army is in defending armies
            if army_id_str in battle['defending_armies']:
                busy_armies.append(army_id)
                break
    
    return busy_armies

def calculate_building_cost(building_type, level):
    """Calculate building cost based on type and level"""
    base_costs = {
        'command_center': {'energy': 200, 'minerals': 100, 'food': 50},
        'power_plant': {'energy': 100, 'minerals': 200, 'food': 0},
        'mine': {'energy': 150, 'minerals': 50, 'food': 100},
        'farm': {'energy': 100, 'minerals': 50, 'food': 150},
        'research_lab': {'energy': 300, 'minerals': 200, 'food': 100},
        'barracks': {'energy': 200, 'minerals': 150, 'food': 200},
        'defense_system': {'energy': 250, 'minerals': 300, 'food': 50},
        'spy_network': {'energy': 200, 'minerals': 100, 'food': 150},
        'intelligence_hub': {'energy': 400, 'minerals': 300, 'food': 200},
        'factory': {'energy': 300, 'minerals': 250, 'food': 100},
        'warehouse': {'energy': 150, 'minerals': 400, 'food': 50},
    }
    
    base = base_costs.get(building_type, {'energy': 100, 'minerals': 100, 'food': 100})
    
    # Cost increases with level
    multiplier = level ** 1.5
    
    return {
        'energy': int(base['energy'] * multiplier),
        'minerals': int(base['minerals'] * multiplier),
        'food': int(base['food'] * multiplier),
    }


def calculate_research_cost(research_type, level):
    """Calculate research cost based on type and level"""
    base_cost = 500
    multiplier = (level ** 2) * 1.5
    
    return {
        'energy': int(base_cost * multiplier),
        'minerals': int(base_cost * multiplier * 0.5),
        'food': int(base_cost * multiplier * 0.3),
        'technology': int(base_cost * multiplier * 0.1),
    }


def can_afford(empire, cost):
    """Check if empire can afford the cost"""
    return (empire.energy >= cost.get('energy', 0) and
            empire.minerals >= cost.get('minerals', 0) and
            empire.food >= cost.get('food', 0) and
            empire.technology >= cost.get('technology', 0))


def deduct_resources(empire, cost):
    """Deduct resources from empire"""
    empire.energy -= cost.get('energy', 0)
    empire.minerals -= cost.get('minerals', 0) 
    empire.food -= cost.get('food', 0)
    empire.technology -= cost.get('technology', 0)
    empire.save()


@login_required
def territory_view(request, x, y):
    """View territory details - village view from outside"""
    try:
        territory = Territory.objects.get(x=x, y=y)
    except Territory.DoesNotExist:
        messages.error(request, "Territory not found.")
        return redirect('game:map')
    
    # Get empire if any
    empire = request.user.empire
    
    # Check if this is the player's own territory
    is_own_territory = territory.owner == empire if territory.owner else False
    
    # Get territory information
    buildings = territory.buildings.all() if territory.owner else []
    # Only show armies that are present in the territory (not away on missions)
    armies = territory.get_present_armies() if territory.owner else []
    
    # Get or create monsters for this territory
    monsters = territory.monsters.all()
    if not monsters and not territory.owner:
        # Create random monsters for unoccupied territories
        create_territory_monsters(territory)
        monsters = territory.monsters.all()
    
    # Respawn monsters if needed
    for monster in monsters:
        monster.respawn_if_needed()
    
    # Calculate distances from player's territories
    distances = []
    if empire:
        for player_territory in empire.territories.all():
            distance = territory.calculate_distance(player_territory)
            distances.append({
                'territory': player_territory,
                'distance': distance,
                'travel_time': max(1, min(30, int(distance * 2)))
            })
        distances.sort(key=lambda x: x['distance'])
    
    context = {
        'territory': territory,
        'empire': empire,
        'is_own_territory': is_own_territory,
        'buildings': buildings,
        'armies': armies,
        'monsters': monsters,
        'distances': distances,
        'monster_stats': TerrainMonster.get_monster_combat_stats() if monsters else {},
    }
    
    return render(request, 'game/territory_view.html', context)


def create_territory_monsters(territory):
    """Create monsters for a territory based on terrain type"""
    terrain_to_monster = {
        'plains': 'plains_wolves',
        'mountains': 'mountain_giants',
        'desert': 'desert_scorpions',
        'forest': 'forest_treants',
        'water': 'water_krakens',
        'volcanic': 'volcanic_dragons',
    }
    
    monster_type = terrain_to_monster.get(territory.terrain_type, 'plains_wolves')
    monster_size = random.randint(50, 150)  # Random monster group size
    monster_level = random.randint(1, 3)    # Initial level 1-3
    
    TerrainMonster.objects.create(
        territory=territory,
        monster_type=monster_type,
        size=monster_size,
        level=monster_level
    )


@login_required
@require_POST
def attack_monster_api(request):
    """API endpoint to attack monsters with specific unit counts"""
    try:
        data = json.loads(request.body)
        territory_id = data.get('territory_id')
        attack_units = data.get('attack_units', {})  # New format: {unit_type: count}
        army_ids = data.get('army_ids', [])  # Legacy format support
        
        with transaction.atomic():
            territory = Territory.objects.get(id=territory_id)
            empire = request.user.empire
            
            # Check if monsters exist and lock them
            monsters = territory.monsters.select_for_update().filter(size__gt=0)
            if not monsters:
                return JsonResponse({'success': False, 'error': 'No monsters to attack'})
            
            monster = monsters.first()
            
            # Handle new attack_units format
            if attack_units:
                # Use the new unit-based system (similar to launch_attack_api)
                total_units_sent = 0
                armies_with_units = []
                
                # Use the same logic as get_armies_api to get available armies
                available_armies = empire.get_present_armies()
                
                # Group available armies by unit type
                available_units = {}
                for army in available_armies:
                    if army.unit_type not in available_units:
                        available_units[army.unit_type] = []
                    available_units[army.unit_type].append(army)
                
                # Validate and collect armies to use
                for unit_type, units_to_send in attack_units.items():
                    if units_to_send <= 0:
                        continue
                        
                    if unit_type not in available_units:
                        return JsonResponse({'success': False, 'error': f'No {unit_type} available'})
                    
                    # Check if we have enough units of this type
                    total_available = sum(army.size for army in available_units[unit_type])
                    
                    if units_to_send > total_available:
                        return JsonResponse({'success': False, 'error': f'Not enough {unit_type}: requested {units_to_send}, available {total_available}'})
                    
                    # Collect armies to use for this unit type
                    remaining_to_send = units_to_send
                    for army in available_units[unit_type]:
                        if remaining_to_send <= 0:
                            break
                            
                        units_from_this_army = min(remaining_to_send, army.size)
                        armies_with_units.append({
                            'army': army,
                            'units_to_send': units_from_this_army
                        })
                        remaining_to_send -= units_from_this_army
                        total_units_sent += units_from_this_army
                
                if total_units_sent == 0:
                    return JsonResponse({'success': False, 'error': 'No valid units to send'})
                
                # Find the source territory (closest to target with armies)
                source_territory = None
                min_distance = float('inf')
                
                for army_data in armies_with_units:
                    army = army_data['army']
                    distance = army.territory.calculate_distance(territory)
                    if distance < min_distance:
                        min_distance = distance
                        source_territory = army.territory
                
                if not source_territory:
                    return JsonResponse({'success': False, 'error': 'No valid source territory found'})
                
                # Create battle
                battle = Battle.objects.create(
                    attacker=empire,
                    territory=territory,
                    source_territory=source_territory,
                    target_monster=monster,
                    started_at=timezone.now()
                )
                
                # Store attacking army data in JSON field
                attacking_armies_data = {}
                for army_data in armies_with_units:
                    original_army = army_data['army']
                    units_to_send = army_data['units_to_send']
                    
                    # Create a new temporary army for the attacking units
                    attacking_army = Army.objects.create(
                        empire=empire,
                        territory=original_army.territory,
                        unit_type=original_army.unit_type,
                        size=units_to_send
                    )
                    
                    # Store the NEW army's data in the battle
                    attacking_armies_data[str(attacking_army.id)] = {
                        'unit_type': attacking_army.get_unit_type_display(),
                        'size': units_to_send,
                        'combat_strength': attacking_army.get_combat_strength()
                    }
                    
                    # Reduce the original army size (keeping the original army for remaining units)
                    original_army.size -= units_to_send
                    original_army.save()
                    
                    # Only delete the original army if it becomes empty
                    if original_army.size <= 0:
                        original_army.delete()
                
                # Store attacking armies data
                battle.attacking_armies = attacking_armies_data
                
                # Start the attack
                battle.start_attack()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Monster hunt launched! {total_units_sent} units are marching to hunt {monster}.',
                    'battle_id': battle.id,
                    'total_units': total_units_sent
                })
            
            else:
                # Legacy army_ids format support
                # Check if armies are available (not in other battles)
                busy_armies = check_army_availability(army_ids)
                
                if busy_armies:
                    busy_army_objects = Army.objects.filter(id__in=busy_armies)
                    busy_army_names = [f"{army.get_unit_type_display()} at ({army.territory.x}, {army.territory.y})" 
                                     for army in busy_army_objects]
                    return JsonResponse({
                        'success': False, 
                        'error': f'Some armies are already in battle: {", ".join(busy_army_names)}'
                    })
                
                # Validate armies belong to player and have units
                armies = Army.objects.select_for_update().filter(
                    id__in=army_ids, 
                    empire=empire,
                    size__gt=0
                )
                if len(armies) != len(army_ids):
                    return JsonResponse({'success': False, 'error': 'Invalid armies selected'})
                
                # Find source territory (closest to target)
                source_territory = None
                min_distance = float('inf')
                for army in armies:
                    distance = army.territory.calculate_distance(territory)
                    if distance < min_distance:
                        min_distance = distance
                        source_territory = army.territory
                
                if not source_territory:
                    return JsonResponse({'success': False, 'error': 'No valid source territory found'})
                
                # Create battle
                battle = Battle.objects.create(
                    attacker=empire,
                    territory=territory,
                    source_territory=source_territory,
                    target_monster=monster
                )
                
                # Store army data
                attacking_armies = {}
                for army in armies:
                    attacking_armies[str(army.id)] = {
                        'unit_type': army.get_unit_type_display(),
                        'size': army.size
                    }
                
                battle.attacking_armies = attacking_armies
                battle.save()
                
                # Start the attack
                battle.start_attack()
                
                return JsonResponse({
                    'success': True,
                    'battle_id': battle.id,
                    'travel_time': battle.travel_time_minutes,
                    'message': f'Your armies are traveling to attack {monster}!'
                })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def attack_player_api(request):
    """API endpoint to attack player territories"""
    try:
        data = json.loads(request.body)
        territory_id = data.get('territory_id')
        army_ids = data.get('army_ids', [])
        
        with transaction.atomic():
            territory = Territory.objects.get(id=territory_id)
            empire = request.user.empire
            
            # Can't attack your own territory
            if territory.owner == empire:
                return JsonResponse({'success': False, 'error': 'Cannot attack your own territory'})
            
            # Check if armies are available (not in other battles)
            busy_armies = check_army_availability(army_ids)
            
            if busy_armies:
                busy_army_objects = Army.objects.filter(id__in=busy_armies)
                busy_army_names = [f"{army.get_unit_type_display()} at ({army.territory.x}, {army.territory.y})" 
                                 for army in busy_army_objects]
                return JsonResponse({
                    'success': False, 
                    'error': f'Some armies are already in battle: {", ".join(busy_army_names)}'
                })
            
            # Validate armies belong to player and have units
            armies = Army.objects.select_for_update().filter(
                id__in=army_ids, 
                empire=empire,
                size__gt=0
            )
            if len(armies) != len(army_ids):
                return JsonResponse({'success': False, 'error': 'Invalid armies selected'})
            
            # Find source territory (closest to target)
            source_territory = None
            min_distance = float('inf')
            for army in armies:
                distance = army.territory.calculate_distance(territory)
                if distance < min_distance:
                    min_distance = distance
                    source_territory = army.territory
            
            if not source_territory:
                return JsonResponse({'success': False, 'error': 'No valid source territory found'})
            
            # Create battle
            battle = Battle.objects.create(
                attacker=empire,
                defender=territory.owner,
                territory=territory,
                source_territory=source_territory
            )
            
            # Store attacking army data
            attacking_armies = {}
            for army in armies:
                attacking_armies[str(army.id)] = {
                    'unit_type': army.get_unit_type_display(),
                    'size': army.size
                }
            
            # Store defending army data
            defending_armies = {}
            if territory.owner:
                for army in territory.armies.all():
                    defending_armies[str(army.id)] = {
                        'unit_type': army.get_unit_type_display(),
                        'size': army.size
                    }
            
            battle.attacking_armies = attacking_armies
            battle.defending_armies = defending_armies
            battle.save()
            
            # Start the attack
            battle.start_attack()
            
            target_name = territory.owner.name if territory.owner else 'Neutral Territory'
            
            return JsonResponse({
                'success': True,
                'battle_id': battle.id,
                'travel_time': battle.travel_time_minutes,
                'message': f'Your armies are traveling to attack {target_name}!'
            })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
def territory_info_api(request):
    """API for getting territory details"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    data = json.loads(request.body)
    x = data.get('x')
    y = data.get('y')
    
    try:
        territory = Territory.objects.get(x=x, y=y)
        empire = request.user.empire
        
        # Get basic territory info
        territory_data = {
            'x': territory.x,
            'y': territory.y,
            'terrain_type': territory.get_terrain_type_display(),
            'owner': territory.owner.name if territory.owner else 'Unclaimed',
            'owner_color': territory.owner.color if territory.owner else '#666',
            'defense_bonus': territory.defense_bonus,
            'resource_bonus': territory.get_resource_bonus_display(),
        }
        
        # Calculate distance from player's closest territory
        distance_info = None
        if empire.territories.exists():
            closest_distance = float('inf')
            closest_territory = None
            
            for player_territory in empire.territories.all():
                distance = territory.calculate_distance(player_territory)
                if distance < closest_distance:
                    closest_distance = distance
                    closest_territory = player_territory
            
            if closest_territory:
                travel_time = max(1, min(30, int(closest_distance * 2)))
                distance_info = {
                    'closest_territory': f"({closest_territory.x}, {closest_territory.y})",
                    'distance': round(closest_distance, 1),
                    'travel_time': travel_time
                }
        
        # Get buildings
        buildings = []
        if territory.owner:
            for building in territory.buildings.all():
                buildings.append({
                    'type': building.get_building_type_display(),
                    'level': building.level
                })
        
        # Get armies
        armies = []
        if territory.owner:
            # Only show armies that are present in the territory (not away on missions)
            for army in territory.get_present_armies():
                armies.append({
                    'type': army.get_unit_type_display(),
                    'size': army.size
                })
        
        # Get monsters with individual army breakdown
        monsters = []
        for monster in territory.monsters.all():
            if monster.size > 0:  # Only show active monsters
                monster.respawn_if_needed()  # Check if monster should respawn
                if monster.size > 0:  # Check again after potential respawn
                    # Create individual monster armies based on size
                    monster_armies = generate_monster_armies(monster)
                    monsters.append({
                        'type': monster.get_monster_type_display(),
                        'total_size': monster.size,
                        'level': monster.level,
                        'combat_strength': monster.get_combat_strength(),
                        'armies': monster_armies,
                        'loot': monster.get_loot_rewards()
                    })
        
        return JsonResponse({
            'success': True,
            'territory': territory_data,
            'distance_info': distance_info,
            'buildings': buildings,
            'armies': armies,
            'monsters': monsters
        })
    
    except Territory.DoesNotExist:
        return JsonResponse({'error': 'Territory not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


def generate_monster_armies(monster):
    """Generate individual monster armies from total monster size"""
    monster_types = {
        'plains_wolves': ['🐺 Alpha Wolf', '🐺 Wolf Pack', '🐺 Scout Wolf'],
        'mountain_giants': ['🏔️ Stone Giant', '🏔️ Boulder Titan', '🏔️ Rock Crusher'],
        'desert_scorpions': ['🦂 Sand Scorpion', '🦂 Venom Stinger', '🦂 Desert Hunter'],
        'forest_treants': ['🌳 Ancient Treant', '🌳 Forest Guardian', '🌳 Branch Walker'],
        'water_krakens': ['🐙 Kraken Tentacle', '🐙 Sea Monster', '🐙 Deep Dweller'],
        'volcanic_dragons': ['🐲 Fire Dragon', '🐲 Lava Wyrm', '🐲 Flame Beast'],
    }
    
    base_types = monster_types.get(monster.monster_type, ['👹 Unknown Creature'])
    total_size = monster.size
    armies = []
    
    # Distribute the total size among different army types
    remaining_size = total_size
    num_army_types = len(base_types)
    
    for i, army_type in enumerate(base_types):
        if i == num_army_types - 1:  # Last army gets remaining size
            army_size = remaining_size
        else:
            # Random distribution but ensure each army has at least some units
            min_size = max(1, total_size // (num_army_types * 3))
            max_size = min(remaining_size - (num_army_types - i - 1), total_size // 2)
            army_size = random.randint(min_size, max_size)
        
        if army_size > 0:
            armies.append({
                'type': army_type,
                'size': army_size,
                'strength': int(army_size * (monster.get_combat_strength() / total_size))
            })
            remaining_size -= army_size
        
        if remaining_size <= 0:
            break
    
    return armies


@login_required
@csrf_exempt
@require_POST
def dashboard_data_api(request):
    """API endpoint for dashboard data"""
    empire = request.user.empire
    
    # Get buildings in progress
    buildings_in_progress = []
    for building in empire.buildings.all():
        if building.upgrade_started and building.upgrade_complete:
            buildings_in_progress.append({
                'id': building.id,
                'type': building.get_building_type_display(),
                'level': building.level,
                'upgrade_started': building.upgrade_started.isoformat(),
                'upgrade_complete': building.upgrade_complete.isoformat(),
                'territory': f"({building.territory.x}, {building.territory.y})"
            })
    
    # Get research in progress
    research_in_progress = []
    for research in empire.research.all():
        if research.research_started and research.research_complete:
            research_in_progress.append({
                'id': research.id,
                'type': research.get_research_type_display(),
                'level': research.level,
                'research_started': research.research_started.isoformat(),
                'research_complete': research.research_complete.isoformat()
            })
    
    # Get armies
    armies = []
    for army in empire.armies.all():
        armies.append({
            'id': army.id,
            'unit_type': army.get_unit_type_display(),
            'size': army.size,
            'is_recruiting': army.is_recruiting(),
            'territory': f"({army.territory.x}, {army.territory.y})"
        })
    
    return JsonResponse({
        'success': True,
        'buildings_in_progress': buildings_in_progress,
        'research_in_progress': research_in_progress,
        'armies': armies,
        'empire': {
            'name': empire.name,
            'power_level': empire.power_level,
            'rank': empire.rank,
            'territories_count': empire.territories.count(),
            'buildings_count': empire.buildings.count()
        }
    })


@login_required
@csrf_exempt
@require_POST
def get_armies_api(request):
    """API endpoint to get player's armies for attack selection"""
    try:
        empire = request.user.empire
        
        armies = []
        # Only show armies that are actually present and available for attack
        for army in empire.get_present_armies():
            armies.append({
                'id': army.id,
                'unit_type': army.unit_type,  # Use the raw unit_type for consistency with attack system
                'unit_type_display': army.get_unit_type_display(),  # Keep display name for UI
                'size': army.size,
                'combat_strength': army.get_combat_strength(),
                'territory_x': army.territory.x,
                'territory_y': army.territory.y,
                'territory_name': f"({army.territory.x}, {army.territory.y})"
            })
        
        return JsonResponse({
            'success': True,
            'armies': armies
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
@require_POST
def get_territory_id_api(request):
    """API endpoint to get territory coordinates from ID or vice versa"""
    try:
        data = json.loads(request.body)
        x = data.get('x')
        y = data.get('y')
        territory_id = data.get('territory_id')
        
        if territory_id:
            # Get coordinates from territory ID
            territory = Territory.objects.get(id=territory_id)
            return JsonResponse({
                'success': True,
                'x': territory.x,
                'y': territory.y,
                'territory_id': territory.id
            })
        elif x is not None and y is not None:
            # Get territory ID from coordinates
            territory = Territory.objects.get(x=x, y=y)
            return JsonResponse({
                'success': True,
                'territory_id': territory.id
            })
        else:
            return JsonResponse({'success': False, 'error': 'Must provide either territory_id or x,y coordinates'})
        
    except Territory.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Territory not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def unit_stats_view(request):
    """Display unit combat statistics in table format"""
    empire = request.user.empire
    
    # Get unit combat stats
    unit_stats = Army.get_unit_combat_stats()
    
    # Prepare data for template
    unit_data = []
    for unit_type, stats in unit_stats.items():
        unit_info = {
            'type': unit_type,
            'display_name': unit_type.replace('_', ' ').title(),
            'attack': stats['attack'],
            'def_infantry': stats.get('def_infantry', 0),
            'def_cavalry': stats.get('def_cavalry', 0),
            'def_archer': stats.get('def_archer', 0),
            'storage': stats['storage'],
            'speed': stats['speed'],
            'description': stats['description'],
            'training_cost': stats['training_cost'],
            'training_time': stats['training_time']
        }
        unit_data.append(unit_info)
    
    context = {
        'empire': empire,
        'unit_data': unit_data,
        'unit_stats': unit_stats
    }
    
    return render(request, 'game/unit_stats.html', context)


@login_required
@csrf_exempt
def populate_master_players_api(request):
    """API to populate empty territories with master players (bots)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    # Only allow admin or specific empires to create master players
    if not empire.user.is_staff:
        return JsonResponse({'error': 'Permission denied'})
    
    try:
        count = data.get('count', 10)  # Number of master players to create
        level_range = data.get('level_range', [1, 5])  # Level range for bots
        
        # Find empty territories
        empty_territories = Territory.objects.filter(owner=None)[:count]
        
        created_count = 0
        for territory in empty_territories:
            level = random.randint(level_range[0], level_range[1])
            master_empire = Empire.create_master_player(territory, level)
            created_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Created {created_count} master players',
            'created_count': created_count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def master_players_view(request):
    """View to manage master players"""
    empire = request.user.empire
    
    # Get all master players
    master_players = Empire.objects.filter(is_master_player=True).order_by('-power_level')
    
    # Get statistics
    total_masters = master_players.count()
    total_human_players = Empire.objects.filter(is_master_player=False).count()
    average_level = master_players.aggregate(avg_level=Avg('master_level'))['avg_level'] or 0
    
    context = {
        'empire': empire,
        'master_players': master_players,
        'total_masters': total_masters,
        'total_human_players': total_human_players,
        'average_level': round(average_level, 1),
    }
    
    return render(request, 'game/master_players.html', context)


@login_required
def trading_view(request):
    """Trading system view"""
    empire = request.user.empire
    
    # Get active trade offers
    sent_trades = empire.sent_trades.exclude(status='completed').order_by('-created_at')
    received_trades = empire.received_trades.exclude(status='completed').order_by('-created_at')
    
    # Get market data (all empires for potential trading)
    all_empires = Empire.objects.exclude(id=empire.id).filter(is_master_player=False)
    
    # Get diplomatic relations
    diplomatic_relations = DiplomaticRelation.objects.filter(
        Q(empire_a=empire) | Q(empire_b=empire)
    )
    
    context = {
        'empire': empire,
        'sent_trades': sent_trades,
        'received_trades': received_trades,
        'all_empires': all_empires,
        'diplomatic_relations': diplomatic_relations,
    }
    
    return render(request, 'game/trading.html', context)


@login_required
def tournaments_view(request):
    """Tournaments view"""
    empire = request.user.empire
    
    # Get current tournaments
    current_tournaments = Tournament.objects.filter(
        is_active=True,
        tournament_end__gt=timezone.now()
    ).order_by('tournament_start')
    
    # Get empire's tournament history
    empire_tournaments = empire.tournaments.all().order_by('-tournament_start')
    
    context = {
        'empire': empire,
        'current_tournaments': current_tournaments,
        'empire_tournaments': empire_tournaments,
    }
    
    return render(request, 'game/tournaments.html', context)


@login_required
def achievements_view(request):
    """Achievements view"""
    empire = request.user.empire
    
    # Get all achievements
    all_achievements = Achievement.objects.all().order_by('difficulty', 'achievement_type')
    
    # Get empire's earned achievements
    earned_achievements = empire.achievements.all().order_by('-earned_at')
    
    # Calculate achievement progress
    achievement_progress = []
    for achievement in all_achievements:
        is_earned = achievement in [ea.achievement for ea in earned_achievements]
        progress = {
            'achievement': achievement,
            'is_earned': is_earned,
            'meets_criteria': achievement.check_criteria(empire) if not is_earned else True
        }
        achievement_progress.append(progress)
    
    context = {
        'empire': empire,
        'achievement_progress': achievement_progress,
        'earned_achievements': earned_achievements,
        'total_achievements': all_achievements.count(),
        'earned_count': earned_achievements.count(),
    }
    
    return render(request, 'game/achievements.html', context)


@login_required
def leaderboards_view(request):
    """Enhanced leaderboards view"""
    empire = request.user.empire
    
    # Get top empires by different categories
    top_power = Empire.objects.filter(is_master_player=False).order_by('-power_level')[:20]
    top_territories = Empire.objects.filter(is_master_player=False).annotate(
        territory_count=Count('territories')
    ).order_by('-territory_count')[:20]
    
    top_battles = Empire.objects.filter(is_master_player=False).annotate(
        battles_won=Count('attacks', filter=Q(attacks__result='attacker_victory'))
    ).order_by('-battles_won')[:20]
    
    # Alliance rankings
    top_alliances = Alliance.objects.annotate(
        member_count=Count('members'),
        avg_power=Avg('members__power_level')
    ).order_by('-avg_power')[:10]
    
    context = {
        'empire': empire,
        'top_power': top_power,
        'top_territories': top_territories,
        'top_battles': top_battles,
        'top_alliances': top_alliances,
    }
    
    return render(request, 'game/leaderboards.html', context)


@login_required
def enhanced_diplomacy_view(request):
    """Enhanced diplomacy view"""
    empire = request.user.empire
    
    # Get diplomatic relations
    diplomatic_relations = DiplomaticRelation.objects.filter(
        Q(empire_a=empire) | Q(empire_b=empire)
    ).order_by('-last_updated')
    
    # Get all empires for potential diplomacy
    all_empires = Empire.objects.exclude(id=empire.id).filter(is_master_player=False)
    
    # Get recent diplomatic messages
    recent_messages = empire.received_messages.filter(
        message_type__in=['diplomatic', 'alliance_invite', 'declaration_of_war', 'peace_treaty']
    ).order_by('-sent_at')[:10]
    
    context = {
        'empire': empire,
        'diplomatic_relations': diplomatic_relations,
        'all_empires': all_empires,
        'recent_messages': recent_messages,
    }
    
    return render(request, 'game/enhanced_diplomacy.html', context)


@login_required
def alliance_warfare_view(request):
    """Alliance warfare management"""
    empire = request.user.empire
    
    # Get empire's alliances
    empire_alliances = empire.alliances.all()
    
    # Get alliance wars
    alliance_wars = []
    for alliance in empire_alliances:
        wars = alliance.war_declarations.all()
        for war in wars:
            alliance_wars.append({
                'our_alliance': alliance,
                'enemy_alliance': war,
                'war_started': alliance.created_at,  # Simplified
            })
    
    # Get recent alliance battles
    alliance_battles = Battle.objects.filter(
        Q(attacker__alliances__in=empire_alliances) | 
        Q(defender__alliances__in=empire_alliances)
    ).order_by('-started_at')[:20]
    
    context = {
        'empire': empire,
        'empire_alliances': empire_alliances,
        'alliance_wars': alliance_wars,
        'alliance_battles': alliance_battles,
    }
    
    return render(request, 'game/alliance_warfare.html', context)


# Enhanced API Endpoints

@login_required
@csrf_exempt
def create_trade_offer_api(request):
    """API for creating trade offers"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    try:
        receiver = Empire.objects.get(id=data.get('receiver_id'))
        
        # Check diplomatic relations
        relation = DiplomaticRelation.objects.filter(
            Q(empire_a=empire, empire_b=receiver) | Q(empire_a=receiver, empire_b=empire)
        ).first()
        
        trade_modifier = 1.0
        if relation:
            trade_modifier = relation.get_trade_cost_modifier()
        
        # Create trade offer
        trade_offer = TradeOffer.objects.create(
            sender=empire,
            receiver=receiver,
            offer_energy=data.get('offer_energy', 0),
            offer_minerals=data.get('offer_minerals', 0),
            offer_food=data.get('offer_food', 0),
            request_energy=int(data.get('request_energy', 0) * trade_modifier),
            request_minerals=int(data.get('request_minerals', 0) * trade_modifier),
            request_food=int(data.get('request_food', 0) * trade_modifier),
            message=data.get('message', ''),
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Trade offer created successfully',
            'trade_id': trade_offer.id
        })
        
    except Empire.DoesNotExist:
        return JsonResponse({'error': 'Receiver not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def respond_trade_offer_api(request):
    """API for responding to trade offers"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    try:
        trade_offer = TradeOffer.objects.get(
            id=data.get('trade_id'),
            receiver=empire,
            status='pending'
        )
        
        if trade_offer.is_expired():
            return JsonResponse({'error': 'Trade offer has expired'})
        
        action = data.get('action')  # 'accept' or 'reject'
        
        if action == 'accept':
            if trade_offer.can_complete():
                success, message = trade_offer.execute_trade()
                if success:
                    return JsonResponse({
                        'success': True,
                        'message': message
                    })
                else:
                    return JsonResponse({'error': message})
            else:
                return JsonResponse({'error': 'Insufficient resources to complete trade'})
        
        elif action == 'reject':
            trade_offer.status = 'rejected'
            trade_offer.responded_at = timezone.now()
            trade_offer.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Trade offer rejected'
            })
        
        else:
            return JsonResponse({'error': 'Invalid action'})
        
    except TradeOffer.DoesNotExist:
        return JsonResponse({'error': 'Trade offer not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def register_tournament_api(request):
    """API for tournament registration"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    try:
        tournament = Tournament.objects.get(id=data.get('tournament_id'))
        
        success, message = tournament.register_participant(empire)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message
            })
        else:
            return JsonResponse({'error': message})
        
    except Tournament.DoesNotExist:
        return JsonResponse({'error': 'Tournament not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def declare_war_api(request):
    """API for declaring war between alliances"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    try:
        # Check if empire is an alliance leader
        alliance = Alliance.objects.get(id=data.get('alliance_id'), leader=empire)
        target_alliance = Alliance.objects.get(id=data.get('target_alliance_id'))
        
        if alliance == target_alliance:
            return JsonResponse({'error': 'Cannot declare war on your own alliance'})
        
        # Check if already at war
        if alliance.is_at_war_with(target_alliance):
            return JsonResponse({'error': 'Already at war with this alliance'})
        
        # Declare war
        alliance.war_declarations.add(target_alliance)
        target_alliance.war_declarations.add(alliance)
        
        # Create diplomatic message
        Message.objects.create(
            sender=empire,
            receiver=target_alliance.leader,
            subject="Declaration of War",
            content=f"{alliance.name} declares war on {target_alliance.name}!",
            message_type='declaration_of_war'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'War declared on {target_alliance.name}'
        })
        
    except Alliance.DoesNotExist:
        return JsonResponse({'error': 'Alliance not found or permission denied'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def set_diplomatic_relation_api(request):
    """API for setting diplomatic relations"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    try:
        target_empire = Empire.objects.get(id=data.get('target_empire_id'))
        relation_type = data.get('relation_type')
        
        # Get or create diplomatic relation
        relation, created = DiplomaticRelation.objects.get_or_create(
            empire_a=empire,
            empire_b=target_empire,
            defaults={
                'relation_type': relation_type,
                'expires_at': timezone.now() + timedelta(days=30)
            }
        )
        
        if not created:
            relation.relation_type = relation_type
            relation.last_updated = timezone.now()
            relation.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Diplomatic relation set to {relation_type}'
        })
        
    except Empire.DoesNotExist:
        return JsonResponse({'error': 'Target empire not found'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def check_achievements_api(request):
    """API for checking and awarding achievements"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    
    try:
        # Get all achievements not yet earned
        earned_achievement_ids = empire.achievements.values_list('achievement_id', flat=True)
        available_achievements = Achievement.objects.exclude(id__in=earned_achievement_ids)
        
        newly_earned = []
        for achievement in available_achievements:
            if achievement.check_criteria(empire):
                achievement.award_to_empire(empire)
                newly_earned.append({
                    'name': achievement.name,
                    'description': achievement.description,
                    'icon': achievement.icon,
                    'rewards': {
                        'energy': achievement.reward_energy,
                        'minerals': achievement.reward_minerals,
                        'food': achievement.reward_food,
                        'technology': achievement.reward_technology,
                    }
                })
        
        return JsonResponse({
            'success': True,
            'newly_earned': newly_earned,
            'count': len(newly_earned)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def send_chat_message_api(request):
    """API for sending chat messages"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    try:
        channel_type = data.get('channel_type')
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return JsonResponse({'error': 'Message cannot be empty'})
        
        if len(message_text) > 500:
            return JsonResponse({'error': 'Message too long (max 500 characters)'})
        
        # Create chat message
        chat_message = ChatMessage.objects.create(
            sender=empire,
            channel_type=channel_type,
            message=message_text
        )
        
        # Set additional fields based on channel type
        if channel_type == 'alliance':
            alliance_id = data.get('alliance_id')
            if alliance_id:
                alliance = Alliance.objects.get(id=alliance_id)
                if empire in alliance.members.all():
                    chat_message.alliance = alliance
                    chat_message.save()
                else:
                    return JsonResponse({'error': 'Not a member of this alliance'})
        
        elif channel_type == 'private':
            recipient_id = data.get('recipient_id')
            if recipient_id:
                recipient = Empire.objects.get(id=recipient_id)
                chat_message.private_recipient = recipient
                chat_message.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Message sent successfully',
            'chat_message': {
                'id': chat_message.id,
                'sender': chat_message.sender.name,
                'message': chat_message.message,
                'sent_at': chat_message.sent_at.isoformat(),
                'channel_type': chat_message.channel_type
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def get_chat_messages_api(request):
    """API for getting chat messages"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    try:
        channel_type = data.get('channel_type')
        limit = min(int(data.get('limit', 50)), 100)  # Max 100 messages
        
        # Base query
        messages = ChatMessage.objects.filter(channel_type=channel_type)
        
        # Filter by channel specifics
        if channel_type == 'alliance':
            alliance_id = data.get('alliance_id')
            if alliance_id:
                alliance = Alliance.objects.get(id=alliance_id)
                if empire in alliance.members.all():
                    messages = messages.filter(alliance=alliance)
                else:
                    return JsonResponse({'error': 'Not a member of this alliance'})
        
        elif channel_type == 'private':
            recipient_id = data.get('recipient_id')
            if recipient_id:
                recipient = Empire.objects.get(id=recipient_id)
                messages = messages.filter(
                    Q(sender=empire, private_recipient=recipient) |
                    Q(sender=recipient, private_recipient=empire)
                )
        
        # Get recent messages
        messages = messages.order_by('-sent_at')[:limit]
        
        # Format messages
        message_list = []
        for msg in reversed(messages):  # Show oldest first
            message_list.append({
                'id': msg.id,
                'sender': msg.sender.name,
                'message': msg.message,
                'sent_at': msg.sent_at.isoformat(),
                'is_system': msg.is_system_message,
                'is_announcement': msg.is_announcement
            })
        
        return JsonResponse({
            'success': True,
            'messages': message_list,
            'count': len(message_list)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)})


# Performance optimized views with caching

@login_required
def cached_rankings_view(request):
    """Cached rankings view for performance"""
    empire = request.user.empire
    
    # Use cache for expensive queries
    cache_key = 'rankings_data'
    cached_data = cache.get(cache_key)
    
    if not cached_data:
        # Expensive database operations
        top_empires = Empire.objects.filter(is_master_player=False).order_by('-power_level')[:50]
        top_alliances = Alliance.objects.annotate(
            member_count=Count('members'),
            total_power=Sum('members__power_level')
        ).order_by('-total_power')[:20]
        
        cached_data = {
            'top_empires': list(top_empires.values('id', 'name', 'power_level', 'rank')),
            'top_alliances': list(top_alliances.values('id', 'name', 'member_count', 'total_power')),
            'last_updated': timezone.now().isoformat()
        }
        
        # Cache for 10 minutes
        cache.set(cache_key, cached_data, 600)
    
    context = {
        'empire': empire,
        'cached_data': cached_data,
    }
    
    return render(request, 'game/cached_rankings.html', context)


@login_required
@csrf_exempt
def bulk_update_api(request):
    """Bulk update API for performance"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    
    try:
        # Update multiple things at once to reduce database calls
        empire.generate_resources()
        
        # Update building progress
        buildings_updated = 0
        for building in empire.buildings.all():
            if building.complete_upgrade():
                buildings_updated += 1
        
        # Update army recruitment
        armies_updated = 0
        for army in empire.armies.all():
            if army.update_recruitment():
                armies_updated += 1
        
        # Check for achievements
        achievements_earned = 0
        earned_achievement_ids = empire.achievements.values_list('achievement_id', flat=True)
        available_achievements = Achievement.objects.exclude(id__in=earned_achievement_ids)
        
        for achievement in available_achievements:
            if achievement.check_criteria(empire):
                achievement.award_to_empire(empire)
                achievements_earned += 1
        
        return JsonResponse({
            'success': True,
            'updates': {
                'buildings_completed': buildings_updated,
                'armies_completed': armies_updated,
                'achievements_earned': achievements_earned,
                'resources': {
                    'energy': int(empire.energy),  # Ensure integer
                    'minerals': int(empire.minerals),  # Ensure integer
                    'food': int(empire.food),  # Ensure integer
                    'technology': int(empire.technology)  # Ensure integer
                }
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def upgrade_building_api(request):
    """API for upgrading individual buildings"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    building_id = data.get('building_id')
    
    try:
        building = Building.objects.get(id=building_id, empire=empire)
        
        # Check if building can be upgraded
        if building.level >= 100:
            return JsonResponse({'error': 'Building is already at maximum level (100)'})
        
        if not building.can_upgrade():
            return JsonResponse({'error': 'Building is already upgrading'})
        
        # Calculate upgrade cost
        cost = calculate_building_cost(building.building_type, building.level + 1)
        
        if not can_afford(empire, cost):
            return JsonResponse({
                'error': f'Insufficient resources! Need: ⚡{cost["energy"]} ⛏{cost["minerals"]} 🌾{cost["food"]}'
            })
        
        # Deduct resources and start upgrade
        deduct_resources(empire, cost)
        building.start_upgrade()
        
        # Recalculate production rates and storage capacity
        empire.calculate_production_rates()
        empire.calculate_storage_capacity()
        
        # Calculate upgrade time in minutes
        upgrade_time_minutes = building.level * settings.BUILDING_TIME_MULTIPLIER
        
        # Calculate the actual end time for the upgrade
        upgrade_end_time = timezone.now() + timedelta(minutes=upgrade_time_minutes)
        
        return JsonResponse({
            'success': True,
            'message': f'{building.get_building_type_display()} upgrade to Lv.{building.level + 1} started!',
            'upgrade_time_minutes': upgrade_time_minutes,
            'upgrade_end_time': upgrade_end_time.isoformat(),  # Add end time for JavaScript
            'empire': {
                'energy': int(empire.energy),  # Ensure integer
                'minerals': int(empire.minerals),  # Ensure integer
                'food': int(empire.food),  # Ensure integer
                'energy_storage': int(empire.energy_storage),  # Ensure integer
                'mineral_storage': int(empire.mineral_storage),  # Ensure integer
                'food_storage': int(empire.food_storage),  # Ensure integer
                'energy_production': int(empire.energy_production),  # Ensure integer
                'mineral_production': int(empire.mineral_production),  # Ensure integer
                'food_production': int(empire.food_production)  # Ensure integer
            }
        })
    
    except Building.DoesNotExist:
        return JsonResponse({'error': 'Building not found or access denied'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def building_status_api(request):
    """API for getting building upgrade status"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    building_id = data.get('building_id')
    
    try:
        building = Building.objects.get(id=building_id, empire=empire)
        
        # Check if building is currently upgrading
        is_upgrading = (building.upgrade_started and 
                       building.upgrade_complete and 
                       timezone.now() < building.upgrade_complete)
        
        response_data = {
            'success': True,
            'building_id': building.id,
            'building_type': building.building_type,
            'level': building.level,
            'is_upgrading': is_upgrading,
        }
        
        if is_upgrading:
            response_data.update({
                'upgrade_started': building.upgrade_started.isoformat(),
                'upgrade_end_time': building.upgrade_complete.isoformat(),
                'time_remaining_seconds': int((building.upgrade_complete - timezone.now()).total_seconds())
            })
        
        return JsonResponse(response_data)
        
    except Building.DoesNotExist:
        return JsonResponse({'error': 'Building not found or access denied'})
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
@csrf_exempt
def convert_resources_api(request):
    """API for converting resources using Resource Alchemy research"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    
    try:
        data = json.loads(request.body)
        from_resource = data.get('from_resource')
        to_resource = data.get('to_resource')
        amount = int(data.get('amount', 0))
        
        # Validate inputs
        if not from_resource or not to_resource or amount <= 0:
            return JsonResponse({'error': 'Invalid conversion parameters'})
        
        valid_resources = ['energy', 'minerals', 'food']
        if from_resource not in valid_resources or to_resource not in valid_resources:
            return JsonResponse({'error': 'Invalid resource type'})
        
        if from_resource == to_resource:
            return JsonResponse({'error': 'Cannot convert resource to itself'})
        
        # Check if Resource Alchemy is researched
        try:
            alchemy_research = Research.objects.get(empire=empire, research_type='resource_alchemy')
            if alchemy_research.level == 0:
                return JsonResponse({'error': 'Resource Alchemy must be researched to convert resources'})
        except Research.DoesNotExist:
            return JsonResponse({'error': 'Resource Alchemy research not found'})
        
        # Calculate conversion efficiency (5% per level)
        efficiency = min(95, alchemy_research.level * 5)  # Max 95% efficiency
        conversion_rate = efficiency / 100.0
        
        # Check if empire has enough of the source resource
        current_amount = getattr(empire, from_resource)
        if current_amount < amount:
            return JsonResponse({'error': f'Not enough {from_resource}. You have {current_amount:,}, need {amount:,}'})
        
        # Calculate converted amount (with efficiency loss)
        converted_amount = int(amount * conversion_rate)
        if converted_amount == 0:
            return JsonResponse({'error': 'Amount too small to convert'})
        
        # Check storage capacity for target resource
        storage_capacity = getattr(empire, f'{to_resource}_storage')
        current_target = getattr(empire, to_resource)
        
        if current_target + converted_amount > storage_capacity:
            max_convertible = storage_capacity - current_target
            return JsonResponse({'error': f'Not enough storage space. Can only convert {max_convertible:,} more {to_resource}'})
        
        # Perform the conversion
        setattr(empire, from_resource, current_amount - amount)
        setattr(empire, to_resource, current_target + converted_amount)
        empire.save()
        
        # Calculate loss for display
        loss_amount = amount - converted_amount
        loss_percentage = ((amount - converted_amount) / amount) * 100
        
        return JsonResponse({
            'success': True,
            'message': f'Converted {amount:,} {from_resource} → {converted_amount:,} {to_resource} (Efficiency: {efficiency}%)',
            'conversion_details': {
                'from_resource': from_resource,
                'to_resource': to_resource,
                'amount_converted': amount,
                'amount_received': converted_amount,
                'amount_lost': loss_amount,
                'efficiency_percentage': efficiency,
                'loss_percentage': round(loss_percentage, 1)
            },
            'new_resources': {
                'energy': int(empire.energy),
                'minerals': int(empire.minerals),
                'food': int(empire.food)
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'})
    except ValueError:
        return JsonResponse({'error': 'Invalid amount specified'})
    except Exception as e:
        return JsonResponse({'error': f'Conversion failed: {str(e)}'})


@csrf_exempt
@login_required
def launch_attack_api(request):
    """Launch attack with specific unit counts (Travian-style)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    try:
        data = json.loads(request.body)
        target_x = data.get('target_x')
        target_y = data.get('target_y')
        attack_units = data.get('attack_units', {})  # Dict of unit_type: count
        
        empire = request.user.empire
        
        # Debug logging
        print(f"DEBUG: Attack units requested: {attack_units}")
        
        # Map frontend unit names to database unit names (case conversion)
        unit_name_mapping = {
            'Infantry': 'infantry',
            'Archers': 'archers', 
            'Spearmen': 'spearmen',
            'Heavy Knights': 'heavy_knights',
            'Royal Knights': 'royal_knights',
            'Spies': 'spies',
            # Also handle if they're already lowercase
            'infantry': 'infantry',
            'archers': 'archers',
            'spearmen': 'spearmen',
            'heavy_knights': 'heavy_knights',
            'royal_knights': 'royal_knights',
            'spies': 'spies'
        }
        
        # Convert frontend unit names to database unit names
        normalized_attack_units = {}
        for frontend_name, count in attack_units.items():
            db_name = unit_name_mapping.get(frontend_name)
            if db_name:
                normalized_attack_units[db_name] = count
            else:
                return JsonResponse({'success': False, 'error': f'Unknown unit type: {frontend_name}'})
        
        print(f"DEBUG: Normalized attack units: {normalized_attack_units}")
        
        # Validate coordinates
        if not (0 <= target_x <= 49 and 0 <= target_y <= 49):
            return JsonResponse({'success': False, 'error': 'Invalid coordinates'})
        
        # Get target territory
        try:
            target_territory = Territory.objects.get(x=target_x, y=target_y)
        except Territory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Territory not found'})
        
        # Check if attacking own territory
        if target_territory.owner == empire:
            return JsonResponse({'success': False, 'error': 'Cannot attack your own territory'})
        
        # Validate attack units
        if not normalized_attack_units:
            return JsonResponse({'success': False, 'error': 'No units selected for attack'})
        
        # Get ALL armies with size > 0, then filter for those not in battle
        all_armies = empire.armies.filter(size__gt=0)
        
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
        
        # Get available armies (not in battle)
        available_armies = all_armies.exclude(id__in=armies_in_battle)
        
        print(f"DEBUG: Available armies: {[(army.unit_type, army.size) for army in available_armies]}")
        
        # Group available armies by unit type
        available_units = {}
        for army in available_armies:
            if army.unit_type not in available_units:
                available_units[army.unit_type] = []
            available_units[army.unit_type].append(army)
        
        print(f"DEBUG: Available units by type: {[(unit_type, sum(army.size for army in armies)) for unit_type, armies in available_units.items()]}")
        
        # Validate and collect armies to use
        armies_with_units = []
        total_units_sent = 0
        
        # Use normalized_attack_units instead of attack_units
        for unit_type, units_to_send in normalized_attack_units.items():
            if units_to_send <= 0:
                continue
                
            print(f"DEBUG: Checking {unit_type}, want to send {units_to_send}")
            
            if unit_type not in available_units:
                return JsonResponse({'success': False, 'error': f'No {unit_type} available'})
            
            # Check if we have enough units of this type
            total_available = sum(army.size for army in available_units[unit_type])
            print(f"DEBUG: {unit_type} - available: {total_available}, requested: {units_to_send}")
            
            if units_to_send > total_available:
                return JsonResponse({'success': False, 'error': f'Not enough {unit_type}: requested {units_to_send}, available {total_available}'})
            
            # Collect armies to use for this unit type
            remaining_to_send = units_to_send
            for army in available_units[unit_type]:
                if remaining_to_send <= 0:
                    break
                    
                units_from_this_army = min(remaining_to_send, army.size)
                armies_with_units.append({
                    'army': army,
                    'units_to_send': units_from_this_army
                })
                remaining_to_send -= units_from_this_army
                total_units_sent += units_from_this_army
        
        if total_units_sent == 0:
            return JsonResponse({'success': False, 'error': 'No valid units to send'})
        
        # Find the source territory (closest to target with armies)
        source_territory = None
        min_distance = float('inf')
        
        for army_data in armies_with_units:
            army = army_data['army']
            distance = army.territory.calculate_distance(target_territory)
            if distance < min_distance:
                min_distance = distance
                source_territory = army.territory
        
        if not source_territory:
            return JsonResponse({'success': False, 'error': 'No valid source territory found'})
        
        # Create battle
        battle = Battle.objects.create(
            attacker=empire,
            defender=target_territory.owner,
            territory=target_territory,
            source_territory=source_territory,
            started_at=timezone.now()
        )
        
        # Store attacking army data in JSON field
        attacking_armies_data = {}
        for army_data in armies_with_units:
            original_army = army_data['army']
            units_to_send = army_data['units_to_send']
            
            # Create a new temporary army for the attacking units
            attacking_army = Army.objects.create(
                empire=empire,
                territory=original_army.territory,
                unit_type=original_army.unit_type,
                size=units_to_send
            )
            
            # Store the NEW army's data in the battle (not the original army)
            attacking_armies_data[str(attacking_army.id)] = {
                'unit_type': attacking_army.get_unit_type_display(),
                'size': units_to_send,
                'combat_strength': attacking_army.get_combat_strength()
            }
            
            # Reduce the original army size (keeping the original army for remaining units)
            original_army.size -= units_to_send
            original_army.save()
            
            # Only delete the original army if it becomes empty
            if original_army.size <= 0:
                original_army.delete()
        
        # Store attacking armies data
        battle.attacking_armies = attacking_armies_data
        
        # Add defending forces if territory is occupied
        defending_armies_data = {}
        if target_territory.owner:
            defending_armies = target_territory.armies.filter(size__gt=0)
            # Apply the same logic for defending armies
            defending_armies_in_battle = set()
            for battle_check in active_battles:
                if battle_check.defending_armies:
                    for army_id_str in battle_check.defending_armies.keys():
                        try:
                            defending_armies_in_battle.add(int(army_id_str))
                        except (ValueError, TypeError):
                            continue
            
            present_defending_armies = defending_armies.exclude(id__in=defending_armies_in_battle)
            
            for army in present_defending_armies:
                defending_armies_data[str(army.id)] = {
                    'unit_type': army.get_unit_type_display(),
                    'size': army.size,
                    'combat_strength': army.get_combat_strength()
                }
        
        # Store defending armies data
        battle.defending_armies = defending_armies_data
        
        # Start the attack
        battle.start_attack()
        
        # Save battle with updated JSON data
        battle.save()
        
        # Create battle log entry
        target_name = target_territory.owner.name if target_territory.owner else "unclaimed territory"
        battle_message = f'Attack launched against {target_name} at ({target_x}|{target_y}) with {total_units_sent} units.'
        
        if target_territory.owner:
            # Send message to defender about incoming attack
            Message.objects.create(
                sender=empire,
                receiver=target_territory.owner,
                subject='Incoming Attack!',
                content=f'Your territory at ({target_x}|{target_y}) is under attack from {empire.name} with {total_units_sent} units!',
                message_type='battle_report'
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Attack launched! {total_units_sent} units are marching to ({target_x}|{target_y}). Battle will occur in 2 minutes.',
            'battle_id': battle.id,
            'total_units': total_units_sent
        })
        
    except Exception as e:
        print(f"DEBUG: Exception in launch_attack_api: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@csrf_exempt
def instant_recruit_api(request):
    """API for instant recruitment of military units - bypasses time requirement for premium cost and costs 10 gold"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'})
    
    empire = request.user.empire
    data = json.loads(request.body)
    
    territory_id = data.get('territory_id')
    unit_type = data.get('unit_type')
    size = data.get('size', 100)
    
    try:
        territory = Territory.objects.get(id=territory_id, owner=empire)
        
        # Check if we have barracks in this territory
        barracks = empire.buildings.filter(territory=territory, building_type='barracks').first()
        if not barracks:
            return JsonResponse({'error': 'No barracks found in this territory. Build barracks first!'})
        
        # Special check for spies - require Intelligence Hub
        if unit_type == 'spies':
            intelligence_hub = empire.buildings.filter(building_type='intelligence_hub').first()
            if not intelligence_hub:
                return JsonResponse({'error': 'Intelligence Hub required to recruit spies! Build an Intelligence Hub first.'})
        
        # Map old unit type names to new ones for backward compatibility
        unit_type_mapping = {
            'tanks': 'archers',
            'aircraft': 'spearmen', 
            'naval': 'heavy_knights',
            'cyber': 'royal_knights'
        }
        
        # Convert old unit type to new unit type if needed
        mapped_unit_type = unit_type_mapping.get(unit_type, unit_type)
        
        # Calculate instant recruitment cost (3x normal cost for instant recruitment)
        unit_costs = Army.get_unit_costs()
        if mapped_unit_type not in unit_costs:
            return JsonResponse({'error': 'Invalid unit type'})
        
        cost_per_batch = unit_costs[mapped_unit_type]
        units_per_batch = cost_per_batch['units_per_batch']
        batches = max(1, size / units_per_batch)
        
        # Instant recruitment costs 3x the normal cost
        instant_cost = {
            'energy': int(cost_per_batch['energy'] * batches * 3),
            'minerals': int(cost_per_batch['minerals'] * batches * 3),
            'food': int(cost_per_batch['food'] * batches * 3),
        }
        
        # Require 10 gold for instant recruitment
        gold_cost = 10
        if empire.gold < gold_cost:
            return JsonResponse({'error': f'You need at least {gold_cost} gold for instant recruitment!'} )
        
        # Check if empire can afford resources
        if not can_afford(empire, instant_cost):
            return JsonResponse({
                'error': f'Insufficient resources for instant recruitment. Need: ⚡{instant_cost["energy"]} ⛏{instant_cost["minerals"]} 🌾{instant_cost["food"]}'
            })
        
        # Deduct resources and gold
        deduct_resources(empire, instant_cost)
        empire.gold -= gold_cost
        empire.save()
        
        # Find or create the main army for this unit type
        main_army = Army.objects.filter(
            empire=empire,
            territory=territory,
            unit_type=mapped_unit_type
        ).first()
        
        if not main_army:
            main_army = Army.objects.create(
                empire=empire,
                territory=territory,
                unit_type=mapped_unit_type,
                size=0
            )
        
        # Add units immediately to the army
        main_army.size += size
        main_army.save()
        
        # Get unit display name
        unit_display_name = main_army.get_unit_type_display()
        
        return JsonResponse({
            'success': True,
            'message': f'Instantly recruited {size} {unit_display_name} units! (-10 gold)',
            'army_id': main_army.id,
            'new_size': main_army.size,
            'cost_paid': instant_cost,
            'gold_paid': gold_cost,
            'gold_remaining': empire.gold
        })
    
    except Territory.DoesNotExist:
        return JsonResponse({'error': 'Territory not found or not owned by you'})
    except Exception as e:
        return JsonResponse({'error': str(e)})
