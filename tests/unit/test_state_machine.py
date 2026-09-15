"""Unit tests for the tournament state machine transitions and guards.

Covers:
- Valid state transitions (INITIAL -> PARTICIPANTS_LOADED -> TOURNAMENT_SETUP -> SWISS_IN_PROGRESS)
- Guard checks (invalid operations in wrong states)
- Version/ETag behavior
- Transition history logging

Run: pytest tests/unit/test_state_machine.py -v
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from tournament_dashboard import TournamentManager, TournamentState, ScoringMode, EventMode, app, tournament
from tests.conftest import make_tournament, setup_via_api, submit_all_tables, finalize_round


# ============================================================
# Valid Transitions - Flask Test Client
# ============================================================

class TestValidTransitions:
    """Test valid state machine transitions triggered by API calls."""

    def test_initial_to_participants_loaded_on_load_data(self, client):
        """Loading data transitions from INITIAL to PARTICIPANTS_LOADED."""
        assert tournament.state == TournamentState.INITIAL
        client.post('/set_event_mode', json={'mode': 'team'})
        client.post('/set_scoring_mode', json={'mode': 'western'})
        resp = client.post('/load_data', json={'use_sample': True, 'num_teams': 8})
        assert tournament.state == TournamentState.PARTICIPANTS_LOADED

    def test_participants_loaded_to_tournament_setup(self, client):
        """Setup tournament transitions from PARTICIPANTS_LOADED to TOURNAMENT_SETUP."""
        client.post('/set_event_mode', json={'mode': 'team'})
        client.post('/set_scoring_mode', json={'mode': 'western'})
        client.post('/load_data', json={'use_sample': True, 'num_teams': 8})
        assert tournament.state == TournamentState.PARTICIPANTS_LOADED

        resp = client.post('/setup_tournament')
        assert resp.status_code == 200
        assert tournament.state == TournamentState.TOURNAMENT_SETUP

    def test_tournament_setup_to_swiss_in_progress_on_first_submit(self, client):
        """First table submission transitions from TOURNAMENT_SETUP to SWISS_IN_PROGRESS."""
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        assert tournament.state == TournamentState.TOURNAMENT_SETUP

        # Submit first table
        resp = client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.get_json()['success'] is True
        assert tournament.state == TournamentState.SWISS_IN_PROGRESS

    def test_swiss_in_progress_persists_through_round_finalization(self, client):
        """State remains SWISS_IN_PROGRESS after finalizing a non-final Swiss round."""
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)
        assert tournament.state == TournamentState.SWISS_IN_PROGRESS

        # Finalize round 1
        resp = client.post('/submit_player_results', json={'round': 1, 'results': []})
        data = resp.get_json()
        assert data['success'] is True
        # Should still be in Swiss (rounds remain)
        assert tournament.state == TournamentState.SWISS_IN_PROGRESS

    def test_full_swiss_to_finals_transition(self, client):
        """After all Swiss rounds complete, transition to FINALS_IN_PROGRESS."""
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)

        # Play through all Swiss rounds
        for round_num in range(1, tournament.swiss_rounds_count + 1):
            submit_all_tables(client, round_num)
            resp = client.post('/submit_player_results', json={'round': round_num, 'results': []})
            assert resp.get_json()['success'] is True

        # After all Swiss rounds, should be in FINALS_IN_PROGRESS
        assert tournament.state == TournamentState.FINALS_IN_PROGRESS

    def test_12_team_structure_no_top_cut(self, client):
        """12-team tournament: 3 Swiss rounds, no Top 8 cut, direct to Finals."""
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=12)

        assert tournament.swiss_rounds_count == 3
        assert tournament.has_semifinals is False
        assert tournament.max_rounds == 4

        # Play through all 3 Swiss rounds
        for round_num in range(1, 4):
            submit_all_tables(client, round_num)
            resp = client.post('/submit_player_results', json={'round': round_num, 'results': []})
            assert resp.get_json()['success'] is True

        # Should go directly to Finals (no Top 8 cut)
        assert tournament.state == TournamentState.FINALS_IN_PROGRESS
        assert tournament.current_round == 4

        # Finals should have 4 tables (top 4 teams, 1 player per team per table)
        resp = client.get('/get_tables/4')
        tables = resp.get_json()['tables']
        assert len(tables) == 4


# ============================================================
# Guard Checks - Invalid Operations
# ============================================================

class TestGuardChecks:
    """Test that operations are rejected in invalid states."""

    def test_submit_player_results_rejects_in_initial_state(self, client):
        """submit_player_results should reject when state is INITIAL."""
        assert tournament.state == TournamentState.INITIAL
        resp = client.post('/submit_player_results', json={'round': 1, 'results': []})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_submit_player_results_rejects_in_participants_loaded(self, client):
        """submit_player_results should reject when state is PARTICIPANTS_LOADED."""
        client.post('/set_event_mode', json={'mode': 'team'})
        client.post('/set_scoring_mode', json={'mode': 'western'})
        client.post('/load_data', json={'use_sample': True, 'num_teams': 8})
        assert tournament.state == TournamentState.PARTICIPANTS_LOADED

        resp = client.post('/submit_player_results', json={'round': 1, 'results': []})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_set_event_mode_rejects_after_participants_loaded(self, client):
        """set_event_mode should reject if state is not INITIAL."""
        client.post('/set_event_mode', json={'mode': 'team'})
        client.post('/set_scoring_mode', json={'mode': 'western'})
        client.post('/load_data', json={'use_sample': True, 'num_teams': 8})
        assert tournament.state == TournamentState.PARTICIPANTS_LOADED

        resp = client.post('/set_event_mode', json={'mode': 'individual'})
        data = resp.get_json()
        assert data['success'] is False

    def test_drop_player_rejects_in_team_mode(self, client):
        """drop_player should reject when event mode is team."""
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)

        # Try to drop a player in team mode
        resp = client.post('/drop_player', json={'player_id': 1, 'round': 1})
        data = resp.get_json()
        assert data['success'] is False
        assert 'individual' in data.get('message', '').lower()

    def test_submit_table_rejects_in_initial_state(self, client):
        """submit_table_results should reject when tournament is in INITIAL state."""
        assert tournament.state == TournamentState.INITIAL
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': 'Table 1',
            'results': [{'player_id': 1, 'points': 5}]
        })
        assert resp.status_code == 400

    def test_setup_tournament_rejects_in_initial_state(self, client):
        """setup_tournament requires PARTICIPANTS_LOADED state."""
        assert tournament.state == TournamentState.INITIAL
        resp = client.post('/setup_tournament')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False


# ============================================================
# Version / ETag
# ============================================================

class TestVersionETag:
    """Test version counter and ETag behavior."""

    def test_version_increments_on_table_submit(self, client):
        """State version should increment when a table is submitted."""
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        version_before = tournament._state_version

        resp = client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert tournament._state_version > version_before

    def test_get_tournament_state_returns_304_with_matching_etag(self, client):
        """If client sends matching If-None-Match, server returns 304."""
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        current_version = str(tournament._state_version)

        resp = client.get('/get_tournament_state', headers={'If-None-Match': current_version})
        assert resp.status_code == 304

    def test_get_tournament_state_returns_200_with_wrong_etag(self, client):
        """If client sends non-matching If-None-Match, server returns 200 with full data."""
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)

        resp = client.get('/get_tournament_state', headers={'If-None-Match': '99999'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'teams' in data

    def test_get_tournament_state_returns_200_without_etag(self, client):
        """Without If-None-Match header, server always returns 200."""
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)

        resp = client.get('/get_tournament_state')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True


# ============================================================
# Transition History
# ============================================================

class TestTransitionHistory:
    """Test that state transitions are logged correctly."""

    def test_transition_to_logs_from_to_reason_timestamp(self):
        """transition_to should record from, to, reason, and timestamp."""
        tournament.state = TournamentState.INITIAL
        tournament.state_history = []

        tournament.transition_to(TournamentState.PARTICIPANTS_LOADED, "Test load")

        assert len(tournament.state_history) == 1
        entry = tournament.state_history[0]
        assert entry['from'] == 'initial'
        assert entry['to'] == 'participants_loaded'
        assert entry['reason'] == 'Test load'
        assert 'timestamp' in entry
        # Verify timestamp is a valid ISO format string
        assert 'T' in entry['timestamp']

    def test_multiple_transitions_accumulate_history(self):
        """Each transition appends to state_history."""
        tournament.state = TournamentState.INITIAL
        tournament.state_history = []

        tournament.transition_to(TournamentState.PARTICIPANTS_LOADED, "Load participants")
        tournament.transition_to(TournamentState.TOURNAMENT_SETUP, "Setup complete")

        assert len(tournament.state_history) == 2
        assert tournament.state_history[0]['to'] == 'participants_loaded'
        assert tournament.state_history[1]['from'] == 'participants_loaded'
        assert tournament.state_history[1]['to'] == 'tournament_setup'

    def test_transition_bumps_version(self):
        """transition_to should increment the version counter."""
        tournament.state = TournamentState.INITIAL
        version_before = tournament._state_version

        tournament.transition_to(TournamentState.PARTICIPANTS_LOADED, "Test")

        assert tournament._state_version == version_before + 1
