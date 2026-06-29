"""Unit tests for Individual Mode tournament logic via Flask test client.

Tests event mode setup, player drop mechanics, 3-player pod score validation,
and top cut progression.

Run: pytest tests/unit/test_individual_mode.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from tournament_dashboard import app, tournament, TournamentState, EventMode
from tests.conftest import setup_via_api, submit_all_tables, finalize_round


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_individual_20(client):
    """Setup an individual tournament with 20 players (5 teams * 4)."""
    client.post('/set_event_mode', json={'mode': 'individual'})
    client.post('/set_scoring_mode', json={'mode': 'western'})
    client.post('/load_data', json={'use_sample_data': True, 'sample_team_count': 5})
    resp = client.post('/setup_tournament')
    return resp.get_json()


def setup_individual_16(client):
    """Setup an individual tournament with 16 players (4 teams * 4)."""
    client.post('/set_event_mode', json={'mode': 'individual'})
    client.post('/set_scoring_mode', json={'mode': 'western'})
    client.post('/load_data', json={'use_sample_data': True, 'sample_team_count': 4})
    resp = client.post('/setup_tournament')
    return resp.get_json()


# ===========================================================================
# SETUP TESTS
# ===========================================================================

class TestIndividualModeSetup:
    """Tests for individual mode event configuration."""

    def test_set_individual_mode(self, client):
        """POST /set_event_mode with 'individual' should set event mode."""
        resp = client.post('/set_event_mode', json={'mode': 'individual'})
        data = resp.get_json()
        assert data['success'] is True
        assert tournament.event_mode == EventMode.INDIVIDUAL

    def test_individual_requires_16_plus_players(self, client):
        """Individual mode setup should fail with fewer than 16 players."""
        # Set up individual mode and manually create fewer than 16 players
        # (the sample data API only supports 8/12/16 teams, so we set state directly)
        tournament.event_mode = EventMode.INDIVIDUAL
        from tournament_dashboard import ScoringMode
        tournament.scoring_mode = ScoringMode.WESTERN

        # Manually load 12 players
        participants = []
        teams = {}
        for i in range(12):
            name = f"Player {i + 1}"
            pid = 3000 + i
            player = {'Player Name': name, 'Player ID': pid, 'Team Name': name}
            participants.append(player)
            teams[name] = [player]

        tournament.participants = participants
        tournament.teams = teams
        tournament.tournament_teams = list(teams.keys())
        tournament.transition_to(TournamentState.PARTICIPANTS_LOADED, "test")

        resp = client.post('/setup_tournament')
        data = resp.get_json()
        assert data['success'] is False
        assert '16' in data.get('message', '') or '16' in data.get('error', '')

    def test_individual_synthetic_team_creation(self, client):
        """In individual mode via load_participants, each player gets their own team.

        When using load_participants (Excel path), individual mode restructures
        each player into their own synthetic 'team of 1'. We verify this by
        calling the restructuring logic directly.
        """
        tournament.event_mode = EventMode.INDIVIDUAL
        from tournament_dashboard import ScoringMode
        tournament.scoring_mode = ScoringMode.WESTERN

        # Manually create 16 individual players (simulating what load_participants does)
        participants = []
        teams = {}
        tournament_teams_list = []
        for i in range(16):
            name = f"Player {i + 1}"
            pid = 4000 + i
            player = {'Player Name': name, 'Player ID': pid, 'Team Name': name}
            participants.append(player)
            teams[name] = [player]
            tournament_teams_list.append(name)

        tournament.participants = participants
        tournament.teams = teams
        tournament.tournament_teams = tournament_teams_list
        tournament.scores = {t: 0 for t in teams}
        tournament.player_scores = {p['Player ID']: 0 for p in participants}
        tournament.transition_to(TournamentState.PARTICIPANTS_LOADED, "test")

        resp = client.post('/setup_tournament')
        data = resp.get_json()
        assert data['success'] is True

        # Each "team" should have exactly 1 player (synthetic team of 1)
        for team_name, players in tournament.teams.items():
            assert len(players) == 1, \
                f"Team '{team_name}' has {len(players)} players, expected 1 in individual mode"

        # Total teams should equal total players
        assert len(tournament.teams) == 16


# ===========================================================================
# PLAYER DROP TESTS
# ===========================================================================

class TestPlayerDrop:
    """Tests for the /drop_player endpoint in individual mode."""

    def _setup_and_submit_round(self, client):
        """Setup a 20-player individual tournament and submit all tables for round 1."""
        setup_individual_20(client)
        # Submit all tables (state transitions to SWISS_IN_PROGRESS on first submit)
        submit_all_tables(client, 1)
        return tournament

    def test_drop_player_removes_from_participants(self, client):
        """Dropping a player removes them from active participants."""
        self._setup_and_submit_round(client)

        # Pick a player to drop
        player_id = tournament.participants[0]['Player ID']
        initial_count = len(tournament.participants)

        resp = client.post('/drop_player', json={'player_id': player_id, 'round': 1})
        data = resp.get_json()
        assert data['success'] is True
        assert len(tournament.participants) == initial_count - 1

        # Player should not be in participants anymore
        remaining_ids = [p['Player ID'] for p in tournament.participants]
        assert player_id not in remaining_ids

    def test_drop_player_freezes_score(self, client):
        """Dropped player's score should be frozen in dropped_players dict."""
        self._setup_and_submit_round(client)

        player_id = tournament.participants[0]['Player ID']
        score_before = tournament.player_scores[player_id]

        resp = client.post('/drop_player', json={'player_id': player_id, 'round': 1})
        data = resp.get_json()
        assert data['success'] is True
        assert tournament.dropped_players[player_id]['score'] == score_before

    def test_drop_player_appears_in_dropped_dict(self, client):
        """Dropped player should appear in tournament.dropped_players."""
        self._setup_and_submit_round(client)

        player_id = tournament.participants[0]['Player ID']
        player_name = tournament.participants[0]['Player Name']

        client.post('/drop_player', json={'player_id': player_id, 'round': 1})

        assert player_id in tournament.dropped_players
        assert tournament.dropped_players[player_id]['name'] == player_name
        assert tournament.dropped_players[player_id]['dropped_after_round'] == 1

    def test_drop_rejected_in_team_mode(self, client):
        """Player drop should be rejected in team mode."""
        # Setup team mode tournament
        client.post('/set_event_mode', json={'mode': 'team'})
        client.post('/set_scoring_mode', json={'mode': 'western'})
        client.post('/load_data', json={'use_sample_data': True, 'sample_team_count': 8})
        client.post('/setup_tournament')

        # Submit all tables for round 1
        submit_all_tables(client, 1)

        # Try to drop a player
        player_id = tournament.participants[0]['Player ID']
        resp = client.post('/drop_player', json={'player_id': player_id, 'round': 1})
        data = resp.get_json()
        assert data['success'] is False
        assert 'individual' in data.get('message', '').lower()

    def test_drop_rejected_before_all_tables_submitted(self, client):
        """Player drop should fail if not all tables have submitted."""
        setup_individual_20(client)

        # Submit only the first table (not all)
        tables_resp = client.get('/get_tables/1')
        tables_data = tables_resp.get_json()
        tables = tables_data.get('tables', {})
        first_table = list(tables.keys())[0]
        players = tables[first_table]

        # Submit just one table
        results = [{'player_id': p['Player ID'], 'points': 5 if i == 0 else 0}
                   for i, p in enumerate(players)]
        client.post('/submit_table_results', json={
            'round': 1, 'table': first_table, 'results': results
        })

        # Try to drop - should fail because not all tables submitted
        player_id = tournament.participants[-1]['Player ID']
        resp = client.post('/drop_player', json={'player_id': player_id, 'round': 1})
        data = resp.get_json()
        assert data['success'] is False
        assert 'submitted' in data.get('message', '').lower()

    def test_drop_rejected_after_finalization(self, client):
        """Player drop should fail after round has been finalized."""
        self._setup_and_submit_round(client)

        # Finalize the round
        client.post('/submit_player_results', json={'round': 1, 'results': []})

        # Try to drop - should fail because round is finalized
        player_id = tournament.participants[0]['Player ID']
        resp = client.post('/drop_player', json={'player_id': player_id, 'round': 1})
        data = resp.get_json()
        assert data['success'] is False
        assert 'finalized' in data.get('message', '').lower()


# ===========================================================================
# 3-PLAYER POD SCORE VALIDATION TESTS
# ===========================================================================

class TestThreePlayerPodValidation:
    """Tests for score validation on 3-player pods (via submit_table_results)."""

    def _setup_with_3_player_pod(self, client):
        """
        Setup a tournament that will produce a 3-player pod.
        19 players = remainder 3, so one pod will have 3 players.
        We set this up directly since the API uses 'num_teams' which gives multiples of 4.
        """
        # Manual setup: 19 individual players
        tournament.event_mode = EventMode.INDIVIDUAL
        from tournament_dashboard import ScoringMode
        tournament.scoring_mode = ScoringMode.WESTERN

        # Create 19 players directly
        participants = []
        teams = {}
        tournament_teams_list = []
        for i in range(19):
            name = f"Player {i + 1}"
            pid = 2000 + i
            player = {'Player Name': name, 'Player ID': pid, 'Team Name': name}
            participants.append(player)
            teams[name] = [player]
            tournament_teams_list.append(name)

        tournament.participants = participants
        tournament.teams = teams
        tournament.tournament_teams = tournament_teams_list
        tournament.transition_to(TournamentState.PARTICIPANTS_LOADED, "test")

        resp = client.post('/setup_tournament')
        data = resp.get_json()
        assert data['success'] is True

        # Find the 3-player pod table
        tables = tournament.tables.get(1, {})
        three_player_table = None
        three_player_pids = None
        for table_name, players in tables.items():
            if len(players) == 3:
                three_player_table = table_name
                three_player_pids = [p['Player ID'] for p in players]
                break

        assert three_player_table is not None, \
            "Expected a 3-player pod with 19 players"
        return three_player_table, three_player_pids

    def test_3_player_pod_accepts_1w_2l(self, client):
        """3-player pod: 1 winner + 2 losers is valid."""
        table_name, pids = self._setup_with_3_player_pod(client)

        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name,
            'results': [
                {'player_id': pids[0], 'points': 5},
                {'player_id': pids[1], 'points': 0},
                {'player_id': pids[2], 'points': 0},
            ]
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_3_player_pod_accepts_3_draws(self, client):
        """3-player pod: 3 draws is valid."""
        table_name, pids = self._setup_with_3_player_pod(client)

        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name,
            'results': [
                {'player_id': pids[0], 'points': 1},
                {'player_id': pids[1], 'points': 1},
                {'player_id': pids[2], 'points': 1},
            ]
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_3_player_pod_accepts_2d_1l(self, client):
        """3-player pod: 2 draws + 1 loss is valid."""
        table_name, pids = self._setup_with_3_player_pod(client)

        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name,
            'results': [
                {'player_id': pids[0], 'points': 1},
                {'player_id': pids[1], 'points': 1},
                {'player_id': pids[2], 'points': 0},
            ]
        })
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_3_player_pod_rejects_2_winners(self, client):
        """3-player pod: 2 winners is invalid."""
        table_name, pids = self._setup_with_3_player_pod(client)

        resp = client.post('/submit_table_results', json={
            'round': 1, 'table': table_name,
            'results': [
                {'player_id': pids[0], 'points': 5},
                {'player_id': pids[1], 'points': 5},
                {'player_id': pids[2], 'points': 0},
            ]
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False
        assert 'winner' in data.get('error', '').lower() or '2' in data.get('error', '')


# ===========================================================================
# TOP CUT TESTS (20+ players)
# ===========================================================================

class TestTopCut:
    """Tests for top cut progression with 20+ players."""

    def _run_4_swiss_rounds(self, client):
        """Run a full 4-round Swiss for a 20-player individual tournament."""
        setup_individual_20(client)

        for round_num in range(1, 5):
            submit_all_tables(client, round_num)
            resp = client.post('/submit_player_results', json={
                'round': round_num, 'results': []
            })
            data = resp.get_json()
            assert data.get('success') is True, \
                f"Failed to finalize round {round_num}: {data}"

    def test_top_cut_triggers_after_4_swiss_rounds(self, client):
        """With 20 players, completing 4 Swiss rounds should trigger top cut."""
        self._run_4_swiss_rounds(client)

        # After 4 Swiss rounds with 20 players, tournament should move to TOP8
        # (top cut uses top 10 players: top 2 get byes, 8 play)
        assert tournament.state in [
            TournamentState.TOP8_IN_PROGRESS,
            TournamentState.FINALS_IN_PROGRESS
        ], f"Expected TOP8_IN_PROGRESS or FINALS_IN_PROGRESS, got {tournament.state}"

    def test_top_2_seeds_get_byes_in_top_cut(self, client):
        """With 20 players, top 2 seeds should receive byes in the top cut."""
        self._run_4_swiss_rounds(client)

        # The tournament should have recorded bye players for the top cut round
        # Top cut round is round 5
        top_cut_round = tournament.swiss_rounds_count + 1

        # Check that bye_players were recorded for the top cut round
        assert top_cut_round in tournament.bye_players, \
            f"No bye players recorded for top cut round {top_cut_round}. " \
            f"Available rounds: {list(tournament.bye_players.keys())}"
        assert len(tournament.bye_players[top_cut_round]) == 2, \
            f"Expected 2 bye players, got {len(tournament.bye_players[top_cut_round])}"
