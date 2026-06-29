"""Shared test fixtures for the MTG Tournament Dashboard test suite."""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from tournament_dashboard import (
    TournamentManager, TournamentState, ScoringMode, EventMode, app, tournament
)


@pytest.fixture
def client():
    """Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset_tournament():
    """Reset global tournament state before each test."""
    tournament.__init__()
    yield
    tournament.__init__()


def make_tournament(num_teams=8, event_mode='team', scoring_mode='western'):
    """Create a TournamentManager with sample data and run setup."""
    tournament.__init__()
    tournament.event_mode = EventMode.TEAM if event_mode == 'team' else EventMode.INDIVIDUAL
    tournament.scoring_mode = ScoringMode.WESTERN if scoring_mode == 'western' else ScoringMode.JAPANESE

    if event_mode == 'individual':
        num_players = num_teams
        tournament.create_sample_data(num_teams=max(4, num_players // 4))
        players = []
        for i in range(num_players):
            p = {'Player Name': f'Player {i+1}', 'Player ID': 1000 + i, 'Team Name': f'Player {i+1}'}
            players.append(p)
        tournament.participants = players
        tournament.teams = {p['Team Name']: [p] for p in players}
        tournament.tournament_teams = list(tournament.teams.keys())
    else:
        tournament.create_sample_data(num_teams=num_teams)

    tournament.determine_tournament_structure()
    return tournament


def setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8):
    """Setup tournament via API endpoints (mimics real user flow).

    For team mode: num_teams is team count (8, 12, or 16).
    For individual mode: num_teams is player count (16, 20, etc).
    """
    client.post('/set_event_mode', json={'mode': event_mode})
    client.post('/set_scoring_mode', json={'mode': scoring_mode})

    if event_mode == 'individual':
        # Individual mode: generate enough synthetic players
        num_fake_teams = max(4, num_teams // 4)
        _generate_sample_players(num_fake_teams, event_mode, scoring_mode)
    else:
        # Team mode: generate teams directly on the tournament object
        _generate_sample_players(num_teams, event_mode, scoring_mode)

    tournament.determine_tournament_structure()
    tournament.transition_to(TournamentState.PARTICIPANTS_LOADED, "Test data loaded")

    resp = client.post('/setup_tournament')
    return resp.get_json()


def _generate_sample_players(num_teams, event_mode, scoring_mode):
    """Generate synthetic team/player data for testing."""
    team_names = [f'Team {chr(65 + i)}' if i < 26 else f'Team {i+1}' for i in range(num_teams)]
    tournament.participants = []
    tournament.teams = {}
    tournament.tournament_teams = []
    pid = 1

    for team_name in team_names:
        players = []
        for j in range(4):
            player = {
                'Player ID': pid,
                'Player Name': f'{team_name}_P{j+1}',
                'Team Name': team_name
            }
            players.append(player)
            tournament.participants.append(player)
            pid += 1
        tournament.teams[team_name] = players
        tournament.tournament_teams.append(team_name)

    if event_mode == 'individual':
        # Restructure: each player becomes their own team
        new_teams = {}
        new_tournament_teams = []
        for p in tournament.participants:
            team_name = p['Player Name']
            p['Team Name'] = team_name
            new_teams[team_name] = [p]
            new_tournament_teams.append(team_name)
        tournament.teams = new_teams
        tournament.tournament_teams = new_tournament_teams


def submit_all_tables(client, round_num, win_pattern=None):
    """Submit valid scores for all tables in a round.

    win_pattern: optional dict of {table_name: winner_index} to control who wins.
    If None, first player wins at every table.
    """
    resp = client.get(f'/get_tables/{round_num}')
    data = resp.get_json()
    tables = data.get('tables', {})

    results = []
    for table_name, players in tables.items():
        player_results = []
        winner_idx = 0
        if win_pattern and table_name in win_pattern:
            winner_idx = win_pattern[table_name]

        for idx, player in enumerate(players):
            pid = player['Player ID']
            points = 5 if idx == winner_idx else 0
            player_results.append({'player_id': pid, 'points': points})

        resp = client.post('/submit_table_results', json={
            'round': round_num,
            'table': table_name,
            'results': player_results
        })
        results.append(resp.get_json())

    return results


def finalize_round(client):
    """Finalize the current round via API."""
    resp = client.post('/submit_player_results', json={
        'round': tournament.current_round,
        'results': []
    })
    return resp.get_json()
