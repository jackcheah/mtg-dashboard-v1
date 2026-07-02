"""Unit tests for TournamentManager core logic.

Tests tiebreaker calculation, scoring, state machine transitions,
and backup/restore integrity.

Run: pytest tests/unit/test_tournament_manager.py -v
"""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tournament_dashboard import TournamentManager, TournamentState, app


def make_tournament(num_teams=8):
    """Create a tournament with sample data for testing."""
    tm = TournamentManager()
    tm.create_sample_data(num_teams)
    tm.determine_tournament_structure()
    return tm


class TestEarlyWinsScore:
    """Tests for calculate_early_wins_score tiebreaker."""

    def test_returns_zero_with_no_results(self):
        tm = make_tournament()
        score = tm.calculate_early_wins_score('Team Alpha')
        assert score == 0

    def test_weights_scale_with_swiss_rounds(self):
        tm = make_tournament()
        tm.swiss_rounds_count = 5
        tm.round_results = {
            1: {'table_submissions': {'Table 1': [{'player_id': 1, 'points': 5}]}},
            5: {'table_submissions': {'Table 1': [{'player_id': 1, 'points': 5}]}},
        }
        score = tm.calculate_early_wins_score('Team Alpha')
        assert score > 0
        # Round 1 weight = 10^(5-1) = 10000, Round 5 weight = 10^(5-5) = 1
        assert score == 5 * 10000 + 5 * 1

    def test_reads_from_table_submissions(self):
        tm = make_tournament()
        tm.round_results = {
            1: {'table_submissions': {'T1': [{'player_id': 1, 'points': 5}, {'player_id': 2, 'points': 1}]}},
        }
        score = tm.calculate_early_wins_score('Team Alpha')
        assert score == (5 + 1) * 1000

    def test_reads_from_legacy_players_key(self):
        tm = make_tournament()
        tm.round_results = {
            1: {'players': {1: 5, 2: 1}},
        }
        score = tm.calculate_early_wins_score('Team Alpha')
        assert score == (5 + 1) * 1000

    def test_ignores_non_swiss_rounds(self):
        tm = make_tournament()
        tm.round_results = {
            5: {'table_submissions': {'T1': [{'player_id': 1, 'points': 5}]}},
        }
        score = tm.calculate_early_wins_score('Team Alpha')
        assert score == 0


class TestTiebreakerKey:
    """Tests for get_team_tiebreaker_key ordering."""

    def test_higher_total_wins(self):
        tm = make_tournament()
        tm.player_scores = {1: 10, 2: 5, 3: 5, 4: 5, 5: 3, 6: 3, 7: 3, 8: 3}
        key_alpha = tm.get_team_tiebreaker_key('Team Alpha', 25)
        key_beta = tm.get_team_tiebreaker_key('Team Beta', 12)
        assert key_alpha > key_beta

    def test_same_total_best_player_breaks_tie(self):
        tm = make_tournament()
        tm.player_scores = {1: 15, 2: 0, 3: 0, 4: 0, 5: 5, 6: 5, 7: 3, 8: 2}
        key_alpha = tm.get_team_tiebreaker_key('Team Alpha', 15)
        key_beta = tm.get_team_tiebreaker_key('Team Beta', 15)
        assert key_alpha > key_beta


class TestFinalStandings:
    """Tests for calculate_final_round_standings."""

    def test_returns_none_without_finals_data(self):
        tm = make_tournament()
        result = tm.calculate_final_round_standings()
        assert result is None

    def test_sorts_by_final_points_primary(self):
        tm = make_tournament()
        tm.finals_data = {'advancing_teams': ['Team Alpha', 'Team Beta', 'Team Gamma', 'Team Delta']}
        tm.final_round_scores = {'Team Alpha': 5, 'Team Beta': 10, 'Team Gamma': 3, 'Team Delta': 8}
        tm.swiss_round_scores = {'Team Alpha': 20, 'Team Beta': 15, 'Team Gamma': 25, 'Team Delta': 10}

        standings = tm.calculate_final_round_standings()
        assert standings[0]['team'] == 'Team Beta'
        assert standings[1]['team'] == 'Team Delta'


class TestMVP:
    """Tests for get_mvp restricting to Top 4 teams."""

    def test_mvp_from_top4_only(self):
        tm = make_tournament()
        tm.finals_data = {'advancing_teams': ['Team Alpha', 'Team Beta', 'Team Gamma', 'Team Delta']}
        tm.final_round_scores = {'Team Alpha': 10, 'Team Beta': 8, 'Team Gamma': 6, 'Team Delta': 4}
        tm.swiss_round_scores = {'Team Alpha': 10, 'Team Beta': 10, 'Team Gamma': 10, 'Team Delta': 10}
        # Player 17 is on Team Epsilon (NOT in finals) with highest score
        tm.player_scores = {1: 5, 2: 5, 3: 5, 4: 5, 5: 3, 6: 3, 7: 3, 8: 3,
                            9: 4, 10: 4, 11: 4, 12: 4, 13: 2, 14: 2, 15: 2, 16: 2,
                            17: 100, 18: 0, 19: 0, 20: 0}
        mvp = tm.get_mvp()
        assert mvp is not None
        # MVP must be from a finalist team, NOT from Team Epsilon
        assert mvp['team_name'] != 'Team Epsilon'
        assert mvp['team_name'] in ['Team Alpha', 'Team Beta', 'Team Gamma', 'Team Delta']


class TestStateMachine:
    """Tests for tournament state transitions."""

    def test_setup_generates_round_1(self):
        tm = make_tournament()
        tm.transition_to(TournamentState.PARTICIPANTS_LOADED, "test")
        success, msg = tm.setup_tournament()
        assert success is True
        assert tm.current_round == 1
        assert 1 in tm.tables
        assert len(tm.tables[1]) > 0

    def test_transition_logs_history(self):
        tm = make_tournament()
        tm.transition_to(TournamentState.PARTICIPANTS_LOADED, "test")
        assert len(tm.state_history) == 1
        assert tm.state_history[0]['to'] == 'participants_loaded'


class TestBackupRestore:
    """Tests for save_state / load_state integrity."""

    def test_round_trip_preserves_scores(self):
        tm = make_tournament()
        tm.scores = {'Team Alpha': 25, 'Team Beta': 20}
        tm.swiss_round_scores = {'Team Alpha': 25, 'Team Beta': 20}
        tm.top8_cut_scores = {'Team Alpha': 5}
        tm.finalized_rounds = {1, 2}

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            tm.save_state(filepath)
            tm2 = TournamentManager()
            tm2.load_state(filepath)

            assert tm2.scores == tm.scores
            assert tm2.swiss_round_scores == tm.swiss_round_scores
            assert tm2.top8_cut_scores == tm.top8_cut_scores
            assert tm2.finalized_rounds == tm.finalized_rounds
        finally:
            os.unlink(filepath)

    def test_submitted_tables_restored_as_set(self):
        tm = make_tournament()
        tm.round_results = {1: {'submitted_tables': {'Table 1', 'Table 2'}, 'table_submissions': {}}}

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            tm.save_state(filepath)
            tm2 = TournamentManager()
            tm2.load_state(filepath)

            submitted = tm2.round_results[1]['submitted_tables']
            assert isinstance(submitted, set)
            submitted.add('Table 3')  # This would crash if it were a list
            assert 'Table 3' in submitted
        finally:
            os.unlink(filepath)

    def test_tries_numbered_backups(self):
        tm = make_tournament()
        tm.scores = {'Team Alpha': 42}

        with tempfile.NamedTemporaryFile(suffix='.json.bak', delete=False) as f:
            filepath = f.name

        backup1 = f"{filepath}.1"
        try:
            tm.save_state(backup1)
            # Primary doesn't exist, but .1 does
            if os.path.exists(filepath):
                os.unlink(filepath)

            tm2 = TournamentManager()
            result = tm2.load_state(filepath)
            assert result is True
            assert tm2.scores == {'Team Alpha': 42}
        finally:
            for f in [filepath, backup1]:
                if os.path.exists(f):
                    os.unlink(f)


class TestScoreValidation:
    """Tests for C1 (score combo), C2 (incomplete finalization), C5 (player count)."""

    def setup_method(self):
        """Set up a tournament ready for scoring via Flask test client."""
        from tournament_dashboard import tournament, TournamentState
        self.client = app.test_client()
        # Reset and set up tournament
        tournament.__init__()
        tournament.create_sample_data(8)
        tournament.determine_tournament_structure()
        tournament.setup_tournament()
        tournament.state = TournamentState.SWISS_IN_PROGRESS
        self.tournament = tournament

    def _get_table1_players(self):
        """Get player IDs for Table 1 Round 1."""
        return [p['Player ID'] for p in self.tournament.tables[1]['Table 1']]

    def test_c1_rejects_two_winners(self):
        pids = self._get_table1_players()
        resp = self.client.post('/submit_table_results', json={
            'round': 1, 'table': 'Table 1',
            'results': [
                {'player_id': pids[0], 'points': 5},
                {'player_id': pids[1], 'points': 5},
                {'player_id': pids[2], 'points': 0},
                {'player_id': pids[3], 'points': 0},
            ]
        })
        assert resp.status_code == 400
        assert 'Only 1 winner' in resp.get_json()['error']

    def test_c1_rejects_win_with_draw(self):
        pids = self._get_table1_players()
        resp = self.client.post('/submit_table_results', json={
            'round': 1, 'table': 'Table 1',
            'results': [
                {'player_id': pids[0], 'points': 5},
                {'player_id': pids[1], 'points': 1},
                {'player_id': pids[2], 'points': 0},
                {'player_id': pids[3], 'points': 0},
            ]
        })
        assert resp.status_code == 400
        assert 'win (5pts) means all others must be losses' in resp.get_json()['error']

    def test_c1_accepts_valid_win(self):
        pids = self._get_table1_players()
        resp = self.client.post('/submit_table_results', json={
            'round': 1, 'table': 'Table 1',
            'results': [
                {'player_id': pids[0], 'points': 5},
                {'player_id': pids[1], 'points': 0},
                {'player_id': pids[2], 'points': 0},
                {'player_id': pids[3], 'points': 0},
            ]
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_c1_accepts_valid_draws(self):
        pids = self._get_table1_players()
        resp = self.client.post('/submit_table_results', json={
            'round': 1, 'table': 'Table 1',
            'results': [
                {'player_id': pids[0], 'points': 1},
                {'player_id': pids[1], 'points': 1},
                {'player_id': pids[2], 'points': 0},
                {'player_id': pids[3], 'points': 0},
            ]
        })
        assert resp.status_code == 200

    def test_c5_rejects_partial_players(self):
        pids = self._get_table1_players()
        resp = self.client.post('/submit_table_results', json={
            'round': 1, 'table': 'Table 1',
            'results': [
                {'player_id': pids[0], 'points': 5},
                {'player_id': pids[1], 'points': 0},
            ]
        })
        assert resp.status_code == 400
        assert 'Expected 4' in resp.get_json()['error'] or 'Expected' in resp.get_json()['error']

    def test_c2_rejects_incomplete_finalization(self):
        pids = self._get_table1_players()
        # Submit only Table 1
        self.client.post('/submit_table_results', json={
            'round': 1, 'table': 'Table 1',
            'results': [
                {'player_id': pids[0], 'points': 5},
                {'player_id': pids[1], 'points': 0},
                {'player_id': pids[2], 'points': 0},
                {'player_id': pids[3], 'points': 0},
            ]
        })
        # Try to finalize with only 1/8 tables
        resp = self.client.post('/submit_player_results', json={'round': 1})
        assert resp.status_code == 400
        assert 'Cannot finalize' in resp.get_json()['error']
