from django.urls import path
from django.shortcuts import render
from . import views

app_name = 'game'

urlpatterns = [
    # Main game views
    path('', views.dashboard_view, name='dashboard'),
    path('map/', views.map_view, name='map'),
    path('buildings/', views.buildings_view, name='buildings'),
    path('building/<int:building_id>/', views.building_detail_view, name='building_detail'),
    path('research/', views.research_view, name='research'),
    path('research/<str:research_type>/', views.research_detail_view, name='research_detail'),
    path('military/', views.military_view, name='military'),
    path('diplomacy/', views.diplomacy_view, name='diplomacy'),
    path('rankings/', views.rankings_view, name='rankings'),
    path('events/', views.events_view, name='events'),
    path('reports/', views.reports_view, name='reports'),
    path('reports/battle/<int:battle_id>/', views.battle_report_detail_view, name='battle_report_detail'),
    
    # Enhanced features
    path('trading/', views.trading_view, name='trading'),
    path('tournaments/', views.tournaments_view, name='tournaments'),
    path('achievements/', views.achievements_view, name='achievements'),
    path('leaderboards/', views.leaderboards_view, name='leaderboards'),
    path('enhanced-diplomacy/', views.enhanced_diplomacy_view, name='enhanced_diplomacy'),
    path('alliance-warfare/', views.alliance_warfare_view, name='alliance_warfare'),
    path('cached-rankings/', views.cached_rankings_view, name='cached_rankings'),
    
    # Territory and unit views
    path('territory/<int:x>/<int:y>/', views.territory_view, name='territory_view'),
    path('unit-stats/', views.unit_stats_view, name='unit_stats'),
    path('master-players/', views.master_players_view, name='master_players'),
    
    # Original API endpoints
    path('api/build/', views.build_api, name='build_api'),
    path('api/upgrade-building/', views.upgrade_building_api, name='upgrade_building_api'),
    path('api/building-status/', views.building_status_api, name='building_status_api'),
    path('api/research/', views.research_api, name='research_api'),
    path('api/attack/', views.attack_api, name='attack'),
    path('api/launch-attack/', views.launch_attack_api, name='launch_attack'),
    path('api/map-attack/', views.map_attack_api, name='map_attack_api'),
    path('api/battle-status/', views.battle_status_api, name='battle_status_api'),
    path('api/send-message/', views.send_message_api, name='send_message_api'),
    path('api/create-alliance/', views.create_alliance_api, name='create_alliance_api'),
    path('api/join-alliance/', views.join_alliance_api, name='join_alliance_api'),
    path('api/generate-resources/', views.generate_resources_api, name='generate_resources_api'),
    path('api/convert-resources/', views.convert_resources_api, name='convert_resources_api'),
    path('api/recruit/', views.recruit_api, name='recruit_api'),
    path('api/instant-recruit/', views.instant_recruit_api, name='instant_recruit_api'),
    path('api/update-recruitment/', views.update_recruitment_api, name='update_recruitment_api'),
    path('api/attack-monster/', views.attack_monster_api, name='attack_monster'),
    path('api/attack-player/', views.attack_player_api, name='attack_player'),
    path('api/territory-info/', views.territory_info_api, name='territory_info'),
    path('api/dashboard-data/', views.dashboard_data_api, name='dashboard_data_api'),
    path('api/get-armies/', views.get_armies_api, name='get_armies'),
    path('api/get-territory-id/', views.get_territory_id_api, name='get_territory_id'),
    path('api/populate-master-players/', views.populate_master_players_api, name='populate_master_players_api'),
    
    # Enhanced API endpoints
    path('api/create-trade-offer/', views.create_trade_offer_api, name='create_trade_offer_api'),
    path('api/respond-trade-offer/', views.respond_trade_offer_api, name='respond_trade_offer_api'),
    path('api/register-tournament/', views.register_tournament_api, name='register_tournament_api'),
    path('api/declare-war/', views.declare_war_api, name='declare_war_api'),
    path('api/set-diplomatic-relation/', views.set_diplomatic_relation_api, name='set_diplomatic_relation_api'),
    path('api/check-achievements/', views.check_achievements_api, name='check_achievements_api'),
    path('api/send-chat-message/', views.send_chat_message_api, name='send_chat_message_api'),
    path('api/get-chat-messages/', views.get_chat_messages_api, name='get_chat_messages_api'),
    path('api/bulk-update/', views.bulk_update_api, name='bulk_update_api'),
    
    # Diplomacy & Alliance API endpoints
    path('api/get-invitations/', views.get_invitations_api, name='get_invitations_api'),
    path('api/respond-invitation/', views.respond_invitation_api, name='respond_invitation_api'),
    path('api/get-available-players/', views.get_available_players_api, name='get_available_players_api'),
    path('api/invite-player/', views.invite_player_api, name='invite_player_api'),
    path('api/request-join/', views.request_join_api, name='request_join_api'),
    path('api/leave-alliance/', views.leave_alliance_api, name='leave_alliance_api'),
    path('api/remove-member/', views.remove_member_api, name='remove_member_api'),
    path('api/toggle-alliance-open/', views.toggle_alliance_open_api, name='toggle_alliance_open_api'),
    
    # Test pages
    path('test-integers/', lambda request: render(request, 'test_integers.html'), name='test_integers'),
] 