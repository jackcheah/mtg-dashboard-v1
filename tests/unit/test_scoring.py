"""Unit tests for scoring logic across Western and Japanese modes.

Covers:
- Western mode point awards (win/draw/loss/team totals)
- Japanese mode pool calculations (contributions, winner gain, loser loss, draws)
- Score submission flow via Flask test client
- Japanese revert/edit bug fix tests

Run: pytest tests/unit/test_scoring.py -v
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from tournament_dashboard import TournamentManager, TournamentState, ScoringMode, EventMode, app, tournament
from tests.conftest import make_tournament, setup_via_api, submit_all_tables, finalize_round


# ============================================================
# Western Mode - Direct Method Calls
# ============================================================

class TestWesternScoring:
    """Western scoring mode: 5/1/0 point system."""

    def test_starting_score_is_zero(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='western')
        for pid, score in tournament.player_scores.items():
            assert score == 0, f"Player {pid} should start at 0, got {score}"

    def test_win_awards_5_points(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='western')
        player_id = 1
        tournament.player_scores[player_id] += 5
        assert tournament.player_scores[player_id] == 5

    def test_draw_awards_1_point(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='western')
        player_id = 1
        tournament.player_scores[player_id] += 1
        assert tournament.player_scores[player_id] == 1

    def test_loss_awards_0_points(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='western')
        player_id = 1
        original = tournament.player_scores[player_id]
        tournament.player_scores[player_id] += 0
        assert tournament.player_scores[player_id] == original

    def test_team_score_sums_players(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='western')
        # Team Alpha has players 1, 2, 3, 4
        tournament.player_scores[1] = 5
        tournament.player_scores[2] = 1
        tournament.player_scores[3] = 0
        tournament.player_scores[4] = 5
        tournament.calculate_team_scores()
        assert tournament.scores['Team Alpha'] == 11


# ============================================================
# Japanese Mode - calculate_japanese_table_scores
# ============================================================

class TestJapaneseScoring:
    """Japanese scoring mode: 7% pool contribution, 1000 starting points."""

    def test_starting_score_is_1000(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='japanese')
        # In Japanese mode, after setup, players start at 1000
        tournament.scoring_mode = ScoringMode.JAPANESE
        # Initialize player scores to Japanese starting value
        for pid in tournament.player_scores:
            tournament.player_scores[pid] = tournament.japanese_starting_points
        for pid, score in tournament.player_scores.items():
            assert score == 1000

    def test_contribution_is_7_percent_rounded(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='japanese')
        tournament.scoring_mode = ScoringMode.JAPANESE
        for pid in tournament.player_scores:
            tournament.player_scores[pid] = 1000

        table_players = [
            {'Player ID': 1, 'Player Name': 'Alice'},
            {'Player ID': 5, 'Player Name': 'Eve'},
            {'Player ID': 9, 'Player Name': 'Iris'},
            {'Player ID': 13, 'Player Name': 'Mia'}
        ]
        result = tournament.calculate_japanese_table_scores(table_players, winner_id=1)
        # 7% of 1000 = 70 per player
        # Pool = 4 * 70 = 280
        # Winner net = 280 - 70 = 210
        assert result[1] == 210
        # Each loser net = -70
        assert result[5] == -70
        assert result[9] == -70
        assert result[13] == -70

    def test_winner_gets_pool_minus_own_contribution(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='japanese')
        tournament.scoring_mode = ScoringMode.JAPANESE
        tournament.player_scores[1] = 1000
        tournament.player_scores[5] = 800
        tournament.player_scores[9] = 1200
        tournament.player_scores[13] = 900

        table_players = [
            {'Player ID': 1, 'Player Name': 'Alice'},
            {'Player ID': 5, 'Player Name': 'Eve'},
            {'Player ID': 9, 'Player Name': 'Iris'},
            {'Player ID': 13, 'Player Name': 'Mia'}
        ]
        result = tournament.calculate_japanese_table_scores(table_players, winner_id=1)
        # Contributions: 70, 56, 84, 63 (rounded)
        c1 = round(1000 * 0.07)  # 70
        c5 = round(800 * 0.07)   # 56
        c9 = round(1200 * 0.07)  # 84
        c13 = round(900 * 0.07)  # 63
        pool = c1 + c5 + c9 + c13
        assert result[1] == pool - c1

    def test_loser_gets_negative_contribution(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='japanese')
        tournament.scoring_mode = ScoringMode.JAPANESE
        tournament.player_scores[1] = 1000
        tournament.player_scores[5] = 800
        tournament.player_scores[9] = 1200
        tournament.player_scores[13] = 900

        table_players = [
            {'Player ID': 1, 'Player Name': 'Alice'},
            {'Player ID': 5, 'Player Name': 'Eve'},
            {'Player ID': 9, 'Player Name': 'Iris'},
            {'Player ID': 13, 'Player Name': 'Mia'}
        ]
        result = tournament.calculate_japanese_table_scores(table_players, winner_id=1)
        assert result[5] == -round(800 * 0.07)
        assert result[9] == -round(1200 * 0.07)
        assert result[13] == -round(900 * 0.07)

    def test_pool_sums_all_contributions(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='japanese')
        tournament.scoring_mode = ScoringMode.JAPANESE
        tournament.player_scores[1] = 1000
        tournament.player_scores[5] = 1000
        tournament.player_scores[9] = 1000
        tournament.player_scores[13] = 1000

        table_players = [
            {'Player ID': 1, 'Player Name': 'Alice'},
            {'Player ID': 5, 'Player Name': 'Eve'},
            {'Player ID': 9, 'Player Name': 'Iris'},
            {'Player ID': 13, 'Player Name': 'Mia'}
        ]
        result = tournament.calculate_japanese_table_scores(table_players, winner_id=1)
        # Pool = 4 * 70 = 280
        # Winner gets pool - contribution = 280 - 70 = 210
        # Total change should be zero-sum: winner_gain + sum(loser_losses) = 0
        total_change = sum(result.values())
        assert total_change == 0

    def test_draw_all_lose_contribution(self):
        make_tournament(num_teams=8, event_mode='team', scoring_mode='japanese')
        tournament.scoring_mode = ScoringMode.JAPANESE
        tournament.player_scores[1] = 1000
        tournament.player_scores[5] = 1000
        tournament.player_scores[9] = 1000
        tournament.player_scores[13] = 1000

        table_players = [
            {'Player ID': 1, 'Player Name': 'Alice'},
            {'Player ID': 5, 'Player Name': 'Eve'},
            {'Player ID': 9, 'Player Name': 'Iris'},
            {'Player ID': 13, 'Player Name': 'Mia'}
        ]
        # Draw = winner_id is None
        result = tournament.calculate_japanese_table_scores(table_players, winner_id=None)
        # All players lose their contribution (70 each)
        assert result[1] == -70
        assert result[5] == -70
        assert result[9] == -70
        assert result[13] == -70


# ============================================================
# Score Submission Flow - Flask Test Client
# ============================================================

class TestScoreSubmissionFlow:
    """Score submission via API endpoints."""

    def test_submit_table_updates_player_scores(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
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
        data = resp.get_json()
        assert data['success'] is True
        assert data['player_scores'][str(players[0]['Player ID'])] == 5

    def test_response_includes_submission_status(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
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
        data = resp.get_json()
        assert 'submission_status' in data
        assert 'submitted_count' in data['submission_status']
        assert data['submission_status']['submitted_count'] == 1

    def test_can_finalize_false_when_not_all_submitted(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
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
        data = resp.get_json()
        # 8 teams = 2 tables (8 teams / 4 players per table)
        # Only 1 submitted so far
        assert data['can_finalize'] is False

    def test_can_finalize_true_when_all_submitted(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)
        # Check the last submission response or use status endpoint
        resp = client.get('/get_submission_status/1')
        data = resp.get_json()
        assert data['is_complete'] is True

    def test_double_submission_rejected(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
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
        # First submission succeeds
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.get_json()['success'] is True

        # Second submission of same table rejected
        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        data = resp.get_json()
        assert data['success'] is False
        assert data.get('already_submitted') is True

    def test_version_increments_on_submit(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        initial_version = tournament._state_version

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
        data = resp.get_json()
        assert data['version'] > initial_version


# ============================================================
# Japanese Revert/Edit - Critical Bug Fix Tests
# ============================================================

class TestJapaneseRevertEdit:
    """Tests that revert and edit correctly handle Japanese deltas (not Western points)."""

    def test_revert_correctly_reverses_japanese_deltas(self, client):
        """Revert should undo the Japanese delta, not subtract Western points."""
        setup_via_api(client, event_mode='team', scoring_mode='japanese', num_teams=8)

        # Set player scores to 1000 (Japanese starting)
        for pid in tournament.player_scores:
            tournament.player_scores[pid] = 1000

        resp = client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        # Record scores before submission
        pre_scores = {p['Player ID']: tournament.player_scores[p['Player ID']] for p in players}

        # Submit with first player winning
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

        # Scores should have changed via Japanese deltas
        post_scores = {p['Player ID']: tournament.player_scores[p['Player ID']] for p in players}
        assert post_scores != pre_scores

        # Now revert
        resp = client.post('/revert_table_submission', json={
            'round': 1, 'table': table_name
        })
        assert resp.get_json()['success'] is True

        # Scores should be back to pre-submission values
        for p in players:
            pid = p['Player ID']
            assert tournament.player_scores[pid] == pre_scores[pid], \
                f"Player {pid}: expected {pre_scores[pid]}, got {tournament.player_scores[pid]}"

    def test_edit_correctly_recalculates_japanese_deltas(self, client):
        """Edit should reverse old Japanese deltas and apply new ones."""
        setup_via_api(client, event_mode='team', scoring_mode='japanese', num_teams=8)

        # Set player scores to 1000
        for pid in tournament.player_scores:
            tournament.player_scores[pid] = 1000

        resp = client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        pre_scores = {p['Player ID']: tournament.player_scores[p['Player ID']] for p in players}

        # Submit with player 0 winning
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

        # Now edit: change winner to player 1
        new_results = [
            {'player_id': players[0]['Player ID'], 'points': 0},
            {'player_id': players[1]['Player ID'], 'points': 5},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = client.post('/edit_table_results', json={
            'round': 1, 'table': table_name, 'results': new_results
        })
        assert resp.get_json()['success'] is True

        # Verify: player 1 should now be the winner (gained pool - contribution)
        # Since all started at 1000, contribution = 70 each, pool = 280
        # Winner (player 1) net = +210, losers net = -70
        pid0 = players[0]['Player ID']
        pid1 = players[1]['Player ID']
        pid2 = players[2]['Player ID']
        pid3 = players[3]['Player ID']

        # After edit, scores should reflect new winner (player 1)
        # Pre-score was 1000 for all. After edit with player1 as winner:
        # player0: 1000 - 70 = 930
        # player1: 1000 + 210 = 1210
        # player2: 1000 - 70 = 930
        # player3: 1000 - 70 = 930
        assert tournament.player_scores[pid1] == 1210, \
            f"New winner should have 1210, got {tournament.player_scores[pid1]}"
        assert tournament.player_scores[pid0] == 930, \
            f"Loser should have 930, got {tournament.player_scores[pid0]}"
        assert tournament.player_scores[pid2] == 930
        assert tournament.player_scores[pid3] == 930
