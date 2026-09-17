"""Tests for tournament flow edge cases that could break the system.

Covers: out-of-order submissions, double finalization, unfinalize/refinalize,
undrop timing, drop at threshold, legacy finalization, backup/restore fidelity.

Run: pytest tests/unit/test_tournament_flow_edge_cases.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from conftest import setup_via_api, submit_all_tables, make_tournament, finalize_round
from tournament_dashboard import tournament, TournamentState, EventMode, ScoringMode


def finalize_round_num(client, round_num):
    """Finalize a specific round via API."""
    resp = client.post('/submit_player_results', json={'round': round_num, 'results': []})
    return resp.get_json()


# ==========================================================================
# Test 6: Submit scores for wrong round
# ==========================================================================

class TestWrongRoundSubmission:
    """Verify that submitting scores for a non-current round is rejected."""

    def test_submit_for_future_round_rejected(self, client):
        """Cannot submit table results for round 2 while round 1 is active."""
        setup_via_api(client, event_mode='team', num_teams=8)
        assert tournament.current_round == 1

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
            'round': 2, 'table': table_name, 'results': results
        })
        assert resp.status_code == 400

    def test_submit_for_past_round_rejected(self, client):
        """Cannot submit scores for round 1 after it's been finalized."""
        setup_via_api(client, event_mode='team', num_teams=8)
        submit_all_tables(client, 1)
        finalize_round_num(client, 1)
        assert 1 in tournament.finalized_rounds

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
        assert resp.status_code == 400


# ==========================================================================
# Test 7: Double finalization
# ==========================================================================

class TestDoubleFinalization:
    """Verify that finalizing an already-finalized round is rejected."""

    def test_double_finalize_same_round(self, client):
        """Finalizing round 1 twice should be rejected the second time."""
        setup_via_api(client, event_mode='team', num_teams=8)
        submit_all_tables(client, 1)

        result1 = finalize_round_num(client, 1)
        assert result1.get('success') is True

        resp = client.post('/submit_player_results', json={
            'round': 1, 'results': []
        })
        data = resp.get_json()
        assert resp.status_code == 400 or data.get('success') is False


# ==========================================================================
# Test 8: Unfinalize then refinalize cycle
# ==========================================================================

class TestUnfinalizeThenRefinalize:
    """Verify the full cycle: finalize → unfinalize → edit → refinalize."""

    def test_unfinalize_edit_refinalize_continues_tournament(self, client):
        """After unfinalize and re-finalize, the tournament should continue
        to the next round normally."""
        setup_via_api(client, event_mode='team', num_teams=8)
        submit_all_tables(client, 1)
        finalize_round_num(client, 1)

        assert tournament.current_round == 2
        assert 1 in tournament.finalized_rounds

        resp = client.post('/unfinalize_round')
        assert resp.status_code == 200
        assert tournament.current_round == 1
        assert 1 not in tournament.finalized_rounds

        submit_all_tables(client, 1)
        finalize_round_num(client, 1)

        assert tournament.current_round == 2
        assert 1 in tournament.finalized_rounds
        assert 2 in tournament.tables


# ==========================================================================
# Test 9: Unfinalize blocked in FINALS_COMPLETE
# ==========================================================================

class TestUnfinalizeBlockedAfterCompletion:
    """Verify that unfinalize is blocked once the tournament is complete."""

    def test_unfinalize_rejected_in_finals_complete(self, client):
        """Once FINALS_COMPLETE, unfinalize should be rejected."""
        setup_via_api(client, event_mode='team', num_teams=8)

        for r in range(1, tournament.swiss_rounds_count + 1):
            submit_all_tables(client, r)
            finalize_round_num(client, r)

        finals_round = tournament.current_round
        submit_all_tables(client, finals_round)
        finalize_round_num(client, finals_round)

        assert tournament.state == TournamentState.FINALS_COMPLETE

        resp = client.post('/unfinalize_round')
        assert resp.status_code in (400, 403)


# ==========================================================================
# Test 10: Undrop player not in current round tables
# ==========================================================================

class TestUndropTimingEdgeCase:
    """Verify that undropped players are handled correctly with respect
    to current round table assignments."""

    def test_undrop_player_mid_round(self, client):
        """After dropping and undropping between rounds, the player should
        be back in the tournament data structures."""
        setup_via_api(client, event_mode='individual', num_teams=16)

        submit_all_tables(client, 1)

        player = tournament.participants[0]
        pid = player['Player ID']

        resp = client.post('/drop_player', json={
            'player_id': pid, 'round': 1
        })
        data = resp.get_json()
        assert resp.status_code == 200, f"Drop failed: {data}"
        assert pid in tournament.dropped_players

        finalize_round_num(client, 1)

        resp = client.post('/undrop_player', json={'player_id': pid})
        data = resp.get_json()
        assert resp.status_code == 200, f"Undrop failed: {data}"
        assert pid not in tournament.dropped_players

        player_in_teams = pid in [
            p['Player ID']
            for players in tournament.teams.values()
            for p in players
        ]
        assert player_in_teams, "Undropped player should be back in teams dict"


# ==========================================================================
# Test 11: Drop player at minimum threshold
# ==========================================================================

class TestDropAtMinimumThreshold:
    """Test dropping players when close to the minimum player count."""

    def test_drop_at_16_players_individual(self, client):
        """Individual mode with exactly 16 players (minimum). Dropping one
        should still work since the tournament is already set up."""
        setup_via_api(client, event_mode='individual', num_teams=16)
        assert len(tournament.participants) == 16

        submit_all_tables(client, 1)

        player = tournament.participants[-1]
        pid = player['Player ID']
        resp = client.post('/drop_player', json={
            'player_id': pid, 'round': 1
        })
        data = resp.get_json()
        assert resp.status_code == 200, f"Drop failed: {data}"
        assert data.get('success') is True
        assert len(tournament.participants) == 15


# ==========================================================================
# Test 12: Legacy finalization without table submissions
# ==========================================================================

class TestLegacyFinalizationPath:
    """Test the legacy finalization path where submit_player_results is
    called with actual player results (not through table submissions)."""

    def test_finalize_without_any_table_submissions(self, client):
        """Calling submit_player_results without any table submissions
        should either work (legacy path) or be properly rejected."""
        setup_via_api(client, event_mode='team', num_teams=8)

        resp = client.post('/submit_player_results', json={
            'round': 1,
            'results': []
        })
        data = resp.get_json()

        if resp.status_code == 400:
            assert data.get('success') is False
        else:
            assert data.get('success') is True


# ==========================================================================
# Test 13: Backup/restore exact score fidelity
# ==========================================================================

class TestBackupRestoreScoreFidelity:
    """Verify that backup/restore preserves exact player and team scores."""

    def test_restore_returns_exact_round2_scores(self, client):
        """Play 2 rounds, backup, play round 3, restore, verify scores
        match the round-2 snapshot exactly."""
        setup_via_api(client, event_mode='team', num_teams=8)

        submit_all_tables(client, 1)
        finalize_round_num(client, 1)
        submit_all_tables(client, 2)
        finalize_round_num(client, 2)

        scores_after_r2 = dict(tournament.player_scores)

        resp = client.post('/save_backup')
        assert resp.status_code == 200

        submit_all_tables(client, 3)
        finalize_round_num(client, 3)

        assert tournament.player_scores != scores_after_r2

        resp = client.post('/restore_backup')
        assert resp.status_code == 200

        for pid, score in scores_after_r2.items():
            assert tournament.player_scores.get(pid) == score, (
                f"Player {pid} score mismatch: expected {score}, "
                f"got {tournament.player_scores.get(pid)}"
            )
