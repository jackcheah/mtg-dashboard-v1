"""Tests for score validation and tournament integrity/reset logic.

Covers: submit_table_results validation, /validate_integrity, and /reset_tournament.

Run: pytest tests/unit/test_validation.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from conftest import setup_via_api, submit_all_tables, finalize_round
from tournament_dashboard import tournament, TournamentState, EventMode, ScoringMode


# ==========================================
# Score Validation (via /submit_table_results)
# ==========================================

class TestScoreValidation:
    """Tests for score validation in /submit_table_results."""

    def _get_table_and_players(self, client, round_num=1):
        """Helper: return (table_name, players_list) for first table in round."""
        resp = client.get(f'/get_tables/{round_num}')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]
        return table_name, players

    def test_rejects_2_winners_in_4_player_pod(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        table_name, players = self._get_table_and_players(client)
        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 5},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'winners' in data['error'].lower() or 'winner' in data['error'].lower()

    def test_rejects_win_with_draw(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        table_name, players = self._get_table_and_players(client)
        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 1},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'draw' in data['error'].lower() or 'loss' in data['error'].lower()

    def test_accepts_1_win_3_loss(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        table_name, players = self._get_table_and_players(client)
        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

    def test_accepts_4_draws(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        table_name, players = self._get_table_and_players(client)
        results = [
            {'player_id': players[0]['Player ID'], 'points': 1},
            {'player_id': players[1]['Player ID'], 'points': 1},
            {'player_id': players[2]['Player ID'], 'points': 1},
            {'player_id': players[3]['Player ID'], 'points': 1},
        ]
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

    def test_accepts_2_draws_2_loss(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        table_name, players = self._get_table_and_players(client)
        results = [
            {'player_id': players[0]['Player ID'], 'points': 1},
            {'player_id': players[1]['Player ID'], 'points': 1},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

    def test_rejects_invalid_points_value(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        table_name, players = self._get_table_and_players(client)
        results = [
            {'player_id': players[0]['Player ID'], 'points': 3},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'Invalid points' in data['error'] or 'points' in data['error'].lower()

    def test_rejects_unknown_player_id(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        table_name, players = self._get_table_and_players(client)
        results = [
            {'player_id': 99999, 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'player_id' in data['error'].lower() or 'not found' in data['error'].lower()


# ==========================================
# Validate Integrity
# ==========================================

class TestValidateIntegrity:
    """Tests for GET /validate_integrity endpoint."""

    def test_validate_integrity_passes_8_teams(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        resp = client.get('/validate_integrity')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['valid'] is True
        assert data['passed_checks'] == data['total_checks']

    def test_validate_integrity_individual_mode_skips_team_check(self, client):
        setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=16)
        resp = client.get('/validate_integrity')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['valid'] is True
        # Should have "Player count validation (individual mode)" instead of "Team count validation"
        assert 'Player count validation (individual mode)' in data['checks_performed']
        assert 'Team count validation' not in data['checks_performed']


# ==========================================
# Reset Tournament
# ==========================================

class TestResetTournament:
    """Tests for POST /reset_tournament endpoint."""

    def test_reset_clears_state_to_initial(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        assert tournament.state != TournamentState.INITIAL

        resp = client.post('/reset_tournament', json={'confirm': 'RESET'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert tournament.state == TournamentState.INITIAL

    def test_reset_rejects_without_confirmation(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        resp = client.post('/reset_tournament', json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_reset_resets_event_mode_to_team(self, client):
        setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=16)
        assert tournament.event_mode == EventMode.INDIVIDUAL

        client.post('/reset_tournament', json={'confirm': 'RESET'})
        assert tournament.event_mode == EventMode.TEAM

    def test_reset_resets_scoring_mode_to_western(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='japanese', num_teams=8)
        assert tournament.scoring_mode == ScoringMode.JAPANESE

        client.post('/reset_tournament', json={'confirm': 'RESET'})
        assert tournament.scoring_mode == ScoringMode.WESTERN

    def test_reset_clears_dropped_players(self, client):
        setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=16)
        submit_all_tables(client, 1)
        # Drop a player
        pid = tournament.participants[0]['Player ID']
        client.post('/drop_player', json={'player_id': pid, 'round': 1})
        assert len(tournament.dropped_players) > 0

        client.post('/reset_tournament', json={'confirm': 'RESET'})
        assert tournament.dropped_players == {}

    def test_reset_clears_bye_players(self, client):
        # Use a player count that produces byes (not divisible by 4)
        # 13 players: 13 % 4 = 1, so 1 bye player
        setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=13)
        # After setup, bye_players may have entries for round 1
        # Even if empty, resetting should clear it
        client.post('/reset_tournament', json={'confirm': 'RESET'})
        assert tournament.bye_players == {}
