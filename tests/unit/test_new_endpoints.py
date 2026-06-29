"""Tests for new tournament dashboard endpoints.

Covers: /unfinalize_round, /undrop_player, /find_player, /search_player,
/list_backups, /preview_finalize, and /control_timer.

Run: pytest tests/unit/test_new_endpoints.py -v
"""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from conftest import setup_via_api, submit_all_tables, make_tournament
from tournament_dashboard import tournament, TournamentState, EventMode


def finalize_round_num(client, round_num):
    """Finalize a specific round via API."""
    resp = client.post('/submit_player_results', json={'round': round_num, 'results': []})
    return resp.get_json()


# ==========================================
# Unfinalize Round
# ==========================================

class TestUnfinalizeRound:
    """Tests for POST /unfinalize_round endpoint."""

    def test_unfinalize_removes_from_finalized_set(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)
        finalize_round_num(client, 1)
        assert 1 in tournament.finalized_rounds

        resp = client.post('/unfinalize_round')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is True
        assert 1 not in tournament.finalized_rounds

    def test_unfinalize_resets_current_round(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)
        finalize_round_num(client, 1)
        # After finalize, current_round advances to 2
        assert tournament.current_round == 2

        client.post('/unfinalize_round')
        assert tournament.current_round == 1

    def test_unfinalize_rejects_if_next_round_has_submissions(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)
        finalize_round_num(client, 1)
        # Submit at least one table in round 2
        resp = client.get('/get_tables/2')
        tables = resp.get_json().get('tables', {})
        table_name = list(tables.keys())[0]
        players = tables[table_name]
        results = [{'player_id': p['Player ID'], 'points': 5 if i == 0 else 0}
                   for i, p in enumerate(players)]
        client.post('/submit_table_results', json={
            'round': 2, 'table': table_name, 'results': results
        })

        resp = client.post('/unfinalize_round')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'already has submissions' in data['error']

    def test_unfinalize_rejects_when_no_rounds_finalized(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        # Submit tables to transition state to SWISS_IN_PROGRESS, but don't finalize
        submit_all_tables(client, 1)
        resp = client.post('/unfinalize_round')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'No rounds have been finalized' in data['error']

    def test_unfinalize_rejects_in_initial_state(self, client):
        # Tournament in INITIAL state, require_state decorator should block
        resp = client.post('/unfinalize_round')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'Invalid operation' in data['error'] or 'current state' in data.get('suggestion', '')


# ==========================================
# Undrop Player
# ==========================================

class TestUndropPlayer:
    """Tests for POST /undrop_player endpoint."""

    def _setup_individual_with_drop(self, client):
        """Helper: set up individual tournament, submit round 1, drop a player."""
        setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=16)
        submit_all_tables(client, 1)
        # Find a player to drop
        player = tournament.participants[0]
        pid = player['Player ID']
        resp = client.post('/drop_player', json={
            'player_id': pid, 'round': 1
        })
        return pid, resp.get_json()

    def test_undrop_restores_player_to_participants(self, client):
        pid, _ = self._setup_individual_with_drop(client)
        assert pid in tournament.dropped_players
        participant_ids_before = [p['Player ID'] for p in tournament.participants]
        assert pid not in participant_ids_before

        resp = client.post('/undrop_player', json={'player_id': pid})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        participant_ids_after = [p['Player ID'] for p in tournament.participants]
        assert pid in participant_ids_after

    def test_undrop_restores_frozen_score(self, client):
        pid, _ = self._setup_individual_with_drop(client)
        frozen_score = tournament.dropped_players[pid]['score']

        client.post('/undrop_player', json={'player_id': pid})
        assert tournament.player_scores[pid] == frozen_score

    def test_undrop_removes_from_dropped_dict(self, client):
        pid, _ = self._setup_individual_with_drop(client)
        assert pid in tournament.dropped_players

        client.post('/undrop_player', json={'player_id': pid})
        assert pid not in tournament.dropped_players

    def test_undrop_rejects_team_mode(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        resp = client.post('/undrop_player', json={'player_id': 9999})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'individual mode' in data['error'].lower()

    def test_undrop_rejects_unknown_player(self, client):
        setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=16)
        submit_all_tables(client, 1)
        resp = client.post('/undrop_player', json={'player_id': 99999})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'not in the dropped list' in data['error']


# ==========================================
# Find Player
# ==========================================

class TestFindPlayer:
    """Tests for GET /find_player/<player_id> endpoint."""

    def test_find_player_returns_table_and_seat(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        # Pick a player from the first table of round 1
        tables = tournament.tables[1]
        first_table = list(tables.keys())[0]
        player = tables[first_table][0]
        pid = player['Player ID']

        resp = client.get(f'/find_player/{pid}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['table'] == first_table
        assert data['seat'] == 1
        assert data['round'] == 1

    def test_find_player_returns_opponents(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        tables = tournament.tables[1]
        first_table = list(tables.keys())[0]
        player = tables[first_table][0]
        pid = player['Player ID']

        resp = client.get(f'/find_player/{pid}')
        data = resp.get_json()
        assert 'opponents' in data
        # Pod of 4 means 3 opponents
        assert len(data['opponents']) == 3
        # Each opponent has name and id
        for opp in data['opponents']:
            assert 'name' in opp
            assert 'id' in opp

    def test_find_player_404_for_unknown_id(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        resp = client.get('/find_player/99999')
        assert resp.status_code == 404
        data = resp.get_json()
        assert data['success'] is False


# ==========================================
# Search Player
# ==========================================

class TestSearchPlayer:
    """Tests for GET /search_player endpoint."""

    def test_search_partial_match(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        # Sample data generates players with known names; search for a substring
        # Get a known player name
        player = tournament.participants[0]
        name = player['Player Name']
        # Use first 3 chars as partial query
        query = name[:3]

        resp = client.get(f'/search_player?q={query}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['results']) >= 1
        # The first player should match
        found_ids = [r['player_id'] for r in data['results']]
        assert player['Player ID'] in found_ids

    def test_search_case_insensitive(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        player = tournament.participants[0]
        name = player['Player Name']
        # Search with uppercase version
        query = name[:4].upper()

        resp = client.get(f'/search_player?q={query}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        found_ids = [r['player_id'] for r in data['results']]
        assert player['Player ID'] in found_ids

    def test_search_rejects_short_query(self, client):
        resp = client.get('/search_player?q=a')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'at least 2 characters' in data['error']

    def test_search_max_20_results(self, client):
        # Create individual tournament with many similarly-named players
        setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=16)
        # All sample players likely share the substring "Player"
        resp = client.get('/search_player?q=Pl')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['results']) <= 20


# ==========================================
# List Backups
# ==========================================

class TestListBackups:
    """Tests for GET /list_backups endpoint."""

    def test_list_backups_empty_when_no_file(self, client):
        # Ensure no backup files exist (base + rotated copies)
        base = tournament.backup_file
        for path in [base, f"{base}.1", f"{base}.2", f"{base}.3"]:
            if os.path.exists(path):
                os.remove(path)

        resp = client.get('/list_backups')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['backups'] == []

    def test_list_backups_shows_file_after_save(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        # Save a backup
        save_resp = client.post('/save_backup')
        assert save_resp.get_json()['success'] is True

        resp = client.get('/list_backups')
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['backups']) >= 1
        backup = data['backups'][0]
        assert 'filepath' in backup
        assert 'size_bytes' in backup
        assert backup['size_bytes'] > 0
        assert 'modified' in backup
        assert 'state' in backup

        # Cleanup
        if os.path.exists(tournament.backup_file):
            os.remove(tournament.backup_file)

    def test_backup_rotation_creates_numbered_files(self, client):
        """Verify saving multiple times rotates backup files."""
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        base = tournament.backup_file

        # Clean any existing backups
        for path in [base, f"{base}.1", f"{base}.2", f"{base}.3"]:
            if os.path.exists(path):
                os.remove(path)

        # Save 4 times to trigger rotation
        for _ in range(4):
            client.post('/save_backup')

        # Verify rotated files exist
        assert os.path.exists(base), "Primary backup should exist"
        assert os.path.exists(f"{base}.1"), "Backup .1 should exist"
        assert os.path.exists(f"{base}.2"), "Backup .2 should exist"
        assert os.path.exists(f"{base}.3"), "Backup .3 should exist"

        # Cleanup
        for path in [base, f"{base}.1", f"{base}.2", f"{base}.3"]:
            if os.path.exists(path):
                os.remove(path)


# ==========================================
# Preview Finalize
# ==========================================

class TestPreviewFinalize:
    """Tests for GET /preview_finalize/<round_num> endpoint."""

    def test_preview_next_swiss_round(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)

        resp = client.get('/preview_finalize/1')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['next_phase'] == 'Swiss Round 2'
        assert data['is_last_swiss_round'] is False

    def test_preview_finals_for_8_teams(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        # Play through all 4 Swiss rounds
        for rnd in range(1, 5):
            submit_all_tables(client, rnd)
            if rnd < 4:
                finalize_round_num(client, rnd)

        resp = client.get('/preview_finalize/4')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['is_last_swiss_round'] is True
        assert 'Finals' in data['next_phase']

    def test_preview_top_cut_for_individual_over_16(self, client):
        # Individual mode with >16 players triggers has_top_cut
        setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=20)
        # Play through Swiss rounds
        for rnd in range(1, 5):
            submit_all_tables(client, rnd)
            if rnd < 4:
                finalize_round_num(client, rnd)

        resp = client.get('/preview_finalize/4')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['is_last_swiss_round'] is True
        assert 'Top Cut' in data['next_phase']

    def test_preview_rejects_incomplete(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        # Don't submit any tables for round 1
        resp = client.get('/preview_finalize/1')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'tables submitted' in data['error']


# ==========================================
# Control Timer
# ==========================================

class TestControlTimer:
    """Tests for POST /control_timer endpoint."""

    def test_timer_start_returns_running(self, client):
        resp = client.post('/control_timer', json={'action': 'start'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['running'] is True

    def test_timer_stop_accumulates_elapsed(self, client):
        # Start the timer and simulate time passing by backdating start_time
        client.post('/control_timer', json={'action': 'start'})
        from datetime import timedelta
        tournament.timer_start_time -= timedelta(seconds=5)
        resp = client.post('/control_timer', json={'action': 'stop'})
        data = resp.get_json()
        assert data['success'] is True
        assert data['running'] is False
        assert data['elapsed'] >= 4

    def test_timer_reset_clears(self, client):
        client.post('/control_timer', json={'action': 'start'})
        from datetime import timedelta
        tournament.timer_start_time -= timedelta(seconds=5)
        client.post('/control_timer', json={'action': 'stop'})

        resp = client.post('/control_timer', json={'action': 'reset'})
        data = resp.get_json()
        assert data['success'] is True
        assert data['running'] is False
        assert data['elapsed'] == 0

    def test_timer_set_duration(self, client):
        resp = client.post('/control_timer', json={'action': 'start', 'duration': 1800})
        data = resp.get_json()
        assert data['success'] is True
        assert data['duration'] == 1800

    def test_timer_rejects_duration_below_60(self, client):
        # Set a valid duration first
        client.post('/control_timer', json={'duration': 600})
        # Attempt to set below minimum — should be silently ignored
        resp = client.post('/control_timer', json={'duration': 30})
        data = resp.get_json()
        assert data['success'] is True
        # Duration should remain at 600, not 30
        assert data['duration'] == 600

    def test_timer_returns_remaining_and_expired(self, client):
        # Set a short duration and start
        resp = client.post('/control_timer', json={'action': 'start', 'duration': 60})
        data = resp.get_json()
        assert 'remaining' in data
        assert 'expired' in data
        assert data['remaining'] <= 60
        assert data['expired'] is False
