"""Tests for confirmed bugs in the MTG Tournament Dashboard.

Each test documents a specific bug, exercises the buggy code path,
and is marked with @pytest.mark.xfail where the bug causes a test failure.

Run: pytest tests/unit/test_bug_fixes.py -v
"""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from conftest import setup_via_api, submit_all_tables, make_tournament, finalize_round
from tournament_dashboard import tournament, TournamentManager, TournamentState, EventMode, ScoringMode


# ==========================================================================
# Test 1: edit_table_results rejects 2-player pods
# ==========================================================================

class TestEdit2PlayerPod:
    """BUG: edit_table_results hardcodes len(new_results) not in (3, 4) at line 3847.

    This means any table with fewer than 3 real players (e.g., a 2-player pod
    created by dropping team members) cannot have its results edited.
    The validation should use the actual table size instead of hardcoding (3, 4).
    """

    def test_edit_rejects_2_result_submission(self, client):
        """edit_table_results returns 400 when given 2 results, even if that
        matches the actual number of active players at the table."""
        setup_via_api(client, event_mode='team', num_teams=8)

        # Get round 1 tables
        resp = client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        # Submit valid 4-player results first
        results_4p = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results_4p
        })
        assert resp.status_code == 200

        # Now simulate a scenario where only 2 players remain at this table.
        # Directly manipulate the table to have only 2 players (simulating
        # a future feature where team players can be dropped mid-round).
        tournament.tables[1][table_name] = players[:2]

        # Try to edit with 2 results matching the 2-player table
        edit_results = [
            {'player_id': players[0]['Player ID'], 'points': 0},
            {'player_id': players[1]['Player ID'], 'points': 5},
        ]
        resp = client.post('/edit_table_results', json={
            'round': 1, 'table': table_name, 'results': edit_results
        })

        # BUG: This returns 400 because the hardcoded check rejects 2 results.
        # The expected behavior is 200 (accept the edit for a 2-player table).
        assert resp.status_code == 200, (
            f"edit_table_results rejected 2 results with: {resp.get_json()}"
        )


# ==========================================================================
# Test 2: edit_table_results score consistency after re-edit
# ==========================================================================

class TestEditTableScoreConsistency:
    """BUG: edit_table_results subtracts old scores for ALL players in the
    original submission, but only re-adds scores for the players in the new
    results list. If a player was removed from the table between submission
    and edit, their score is subtracted but never restored.

    The subtraction loop (line ~3977) iterates over old_results (4 players),
    while the addition loop (line ~3997) iterates over new_results (3 players).
    The missing player loses their score permanently.
    """

    def test_edit_ghost_table_preserves_ghost_scores(self, client):
        """When a table with a ghost player is edited, the ghost player's
        auto-injected 0-point score should be preserved in stored results
        and team totals should remain consistent.

        Previously, editing a ghost table would lose ghost entries from
        table_submissions, corrupting future edits.
        """
        setup_via_api(client, event_mode='team', num_teams=8)

        # Submit ALL tables first (required before drop)
        submit_all_tables(client, 1)

        # Get table info for the first table
        resp = client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        # Drop a player from this table's team using the proper API
        ghost_pid = players[3]['Player ID']
        success, msg = tournament.drop_team_player(ghost_pid, 1)
        assert success, f"drop_team_player failed: {msg}"

        # Revert this table's submission so we can re-submit with ghost detection
        resp = client.post('/revert_table_submission', json={
            'round': 1, 'table': table_name
        })
        assert resp.status_code == 200

        # Re-submit with 3 real players (ghost auto-injected)
        results_3p = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
        ]
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results_3p
        })
        assert resp.status_code == 200, f"Submit with ghost failed: {resp.get_json()}"

        # Edit: change the winner from player 0 to player 1
        edit_results = [
            {'player_id': players[0]['Player ID'], 'points': 0},
            {'player_id': players[1]['Player ID'], 'points': 5},
            {'player_id': players[2]['Player ID'], 'points': 0},
        ]
        resp = client.post('/edit_table_results', json={
            'round': 1, 'table': table_name, 'results': edit_results
        })
        assert resp.status_code == 200, f"Edit with ghost failed: {resp.get_json()}"

        # Ghost player should still have 0 points
        assert tournament.player_scores[ghost_pid] == 0

        # Ghost entry should be preserved in stored results
        stored = tournament.round_results[1]['table_submissions'][table_name]
        ghost_entries = [r for r in stored if r.get('is_ghost')]
        assert len(ghost_entries) > 0, (
            "Ghost entry should be preserved in table_submissions after edit"
        )


# ==========================================================================
# Test 3: _build_state_dict doesn't save _next_player_id
# ==========================================================================

class TestBackupRestorePlayerIdCounter:
    """BUG: _build_state_dict doesn't include _next_player_id in the saved state.

    After save and restore, _next_player_id resets to the default (10000),
    which could cause player ID collisions when new players are added.
    """

    def test_save_restore_preserves_next_player_id(self):
        """_next_player_id should survive a save/restore cycle."""
        make_tournament(num_teams=8)

        # Simulate generating some player IDs
        tournament._next_player_id = 10042
        original_next_id = tournament._next_player_id

        # Save state to a temp file
        tmpfile = os.path.join(tempfile.gettempdir(), 'test_player_id_backup.json')
        tournament.save_state(tmpfile)

        # Reset tournament (simulates server restart)
        tournament.__init__()
        assert tournament._next_player_id == 10000  # default

        # Restore from backup
        tournament.load_state(tmpfile)

        # BUG: _next_player_id is NOT restored because _build_state_dict
        # doesn't include it in the serialized state.
        assert tournament._next_player_id == original_next_id, (
            f"Expected _next_player_id={original_next_id}, "
            f"got {tournament._next_player_id}"
        )

        # Cleanup
        if os.path.exists(tmpfile):
            os.remove(tmpfile)

    def test_build_state_dict_includes_next_player_id(self):
        """Verify that _build_state_dict output contains _next_player_id."""
        make_tournament(num_teams=8)
        tournament._next_player_id = 10042

        state = tournament._build_state_dict()

        assert '_next_player_id' in state.get('data', {}), (
            "_next_player_id should be in the data section of state dict"
        )
        assert state['data']['_next_player_id'] == 10042


# ==========================================================================
# Test 4: reset_tournament doesn't clear all state fields
# ==========================================================================

class TestResetClearsAllState:
    """BUG: reset_tournament doesn't reset several state fields that are
    initialized in __init__ or set during tournament play.

    Missing from reset: state_history, _player_scores_at_finals_start,
    anti_collusion_enabled, anti_collusion_start_round, _next_player_id,
    and the dynamically-created 'semifinals' attribute.
    """

    def test_reset_clears_player_scores_at_finals_start(self, client):
        """_player_scores_at_finals_start should be cleared after reset."""
        setup_via_api(client, event_mode='team', num_teams=8)

        # Simulate finals state
        tournament._player_scores_at_finals_start = {1: 100, 2: 200, 3: 150}

        # Reset
        resp = client.post('/reset_tournament', json={'confirm': 'RESET'})
        assert resp.status_code == 200

        # BUG: _player_scores_at_finals_start is not cleared by reset
        finals_start = getattr(tournament, '_player_scores_at_finals_start', {})
        assert finals_start == {}, (
            f"_player_scores_at_finals_start not cleared: {finals_start}"
        )

    def test_reset_restores_anti_collusion_defaults(self, client):
        """anti_collusion settings should revert to defaults after reset."""
        setup_via_api(client, event_mode='team', num_teams=8)

        # Modify anti-collusion settings
        tournament.anti_collusion_enabled = False
        tournament.anti_collusion_start_round = 2

        # Reset
        resp = client.post('/reset_tournament', json={'confirm': 'RESET'})
        assert resp.status_code == 200

        # BUG: anti_collusion fields are not reset
        assert tournament.anti_collusion_enabled is True, (
            f"anti_collusion_enabled not reset: {tournament.anti_collusion_enabled}"
        )
        assert tournament.anti_collusion_start_round == 4, (
            f"anti_collusion_start_round not reset: {tournament.anti_collusion_start_round}"
        )

    def test_reset_clears_semifinals(self, client):
        """The dynamically-created 'semifinals' attribute should be cleared."""
        setup_via_api(client, event_mode='team', num_teams=8)

        # Set semifinals data (as done during Top 8 Cut flow)
        tournament.semifinals = {'advancing_teams': ['Team A', 'Team B'],
                                 'tables': {'Table 1': []}}

        # Reset
        resp = client.post('/reset_tournament', json={'confirm': 'RESET'})
        assert resp.status_code == 200

        # BUG: 'semifinals' is not cleared by reset_tournament
        semis = getattr(tournament, 'semifinals', None)
        assert semis is None or semis == {}, (
            f"semifinals not cleared after reset: {semis}"
        )

    def test_reset_clears_state_history(self, client):
        """state_history should be reset to empty (or contain only the reset transition)."""
        setup_via_api(client, event_mode='team', num_teams=8)

        # state_history accumulates entries from setup
        assert len(tournament.state_history) > 0

        # Reset
        resp = client.post('/reset_tournament', json={'confirm': 'RESET'})
        assert resp.status_code == 200

        # BUG: state_history is never cleared in reset_tournament.
        # After reset, it should contain at most the reset transition itself.
        assert len(tournament.state_history) <= 1, (
            f"state_history has {len(tournament.state_history)} entries after reset, "
            f"expected at most 1 (the reset transition)"
        )

    def test_reset_restores_next_player_id(self, client):
        """_next_player_id should reset to its default value (10000)."""
        setup_via_api(client, event_mode='team', num_teams=8)

        # Advance the counter
        tournament._next_player_id = 10500

        # Reset
        resp = client.post('/reset_tournament', json={'confirm': 'RESET'})
        assert resp.status_code == 200

        # BUG: _next_player_id is not reset
        assert tournament._next_player_id == 10000, (
            f"_next_player_id not reset: {tournament._next_player_id}"
        )


# ==========================================================================
# Test 5: Read endpoints write _cached_final_standings without lock
# ==========================================================================

class TestCachedStandingsThreadSafety:
    """BUG: Several read-only endpoints (/standings, /get_final_standings,
    /final_standings) call calculate_final_round_standings() which writes to
    tournament._cached_final_standings — but these endpoints are NOT decorated
    with @with_lock, creating a potential race condition.

    Concurrent GET requests during finals could cause:
    - Torn reads of _cached_final_standings
    - Multiple simultaneous calculations overwriting each other

    This test documents the issue by verifying these endpoints lack @with_lock.
    """

    def test_standings_endpoint_accessible(self, client):
        """Verify /standings endpoint is accessible in Swiss phase."""
        setup_via_api(client, event_mode='team', num_teams=8)
        resp = client.get('/standings')
        assert resp.status_code == 200

    def test_get_final_standings_endpoint_accessible(self, client):
        """Verify /get_final_standings endpoint is accessible during setup."""
        setup_via_api(client, event_mode='team', num_teams=8)
        resp = client.get('/get_final_standings')
        data = resp.get_json()
        # Endpoint returns 200 regardless of tournament phase
        assert resp.status_code == 200

    def test_final_standings_endpoint_accessible(self, client):
        """Verify /final_standings endpoint is accessible (returns not-ready)."""
        setup_via_api(client, event_mode='team', num_teams=8)
        resp = client.get('/final_standings')
        data = resp.get_json()
        assert resp.status_code == 200
        assert data['success'] is False  # no finals data

    def test_standings_endpoints_have_lock(self):
        """Verify that standings endpoints have @with_lock to prevent
        race conditions when writing _cached_final_standings."""
        from tournament_dashboard import app

        for rule in app.url_map.iter_rules():
            if rule.rule in ('/standings', '/get_final_standings', '/final_standings'):
                view_func = app.view_functions[rule.endpoint]
                has_lock = hasattr(view_func, '__wrapped__')
                assert has_lock, (
                    f"Endpoint {rule.rule} should have @with_lock decorator"
                )
