"""Integration tests: Full 20-32 team tournament flows with team player drops.

Tests exercise the complete lifecycle of larger Western scoring tournaments
including player drops (ghost seats), undrop recovery, multi-drop enforcement,
and anti-collusion pairing — all via the Flask test client API.

Run: pytest tests/integration/test_team_tournament_with_drops.py -v
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from tournament_dashboard import (
    TournamentManager, TournamentState, ScoringMode, EventMode, app, tournament
)
from tests.conftest import setup_via_api, finalize_round


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def reset():
    tournament.__init__()
    yield
    tournament.__init__()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_state(client):
    return client.get('/get_tournament_state').get_json()


def submit_all_tables_ghost_aware(client, round_num):
    """Submit valid scores for all tables, correctly excluding ghost players.

    Ghost (dropped) players are filtered out before submission.
    The server auto-injects 0 points for them.
    """
    resp = client.get(f'/get_tables/{round_num}')
    data = resp.get_json()
    tables = data.get('tables', {})

    results = []
    for table_name, players in tables.items():
        real_players = [p for p in players if not p.get('is_dropped')]

        if not real_players:
            continue

        player_results = []
        for idx, player in enumerate(real_players):
            points = 5 if idx == 0 else 0
            player_results.append({
                'player_id': player['Player ID'],
                'points': points
            })

        resp = client.post('/submit_table_results', json={
            'round': round_num,
            'table': table_name,
            'results': player_results
        })
        result = resp.get_json()
        assert result['success'], (
            f"Table {table_name} round {round_num} submit failed: {result}"
        )
        results.append(result)

    return results


def drop_team_player_api(client, player_id, round_num):
    resp = client.post('/drop_team_player', json={
        'player_id': player_id,
        'round': round_num
    })
    return resp.get_json()


def undrop_team_player_api(client, player_id):
    resp = client.post('/undrop_team_player', json={
        'player_id': player_id
    })
    return resp.get_json()


def assert_team_score_consistency():
    """Verify each team's score equals the sum of its players' scores."""
    tournament.calculate_team_scores()
    for team_name, players in tournament.teams.items():
        expected = sum(tournament.player_scores.get(p['Player ID'], 0) for p in players)
        actual = tournament.scores.get(team_name, 0)
        assert actual == expected, (
            f"{team_name}: team score {actual} != sum of player scores {expected}"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFull20TeamWithDrops:
    """20-team Western: 4 Swiss + Finals. Single drops from 2 different teams."""

    def test_full_flow_with_drops(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=20)

        assert len(tournament.teams) == 20
        assert tournament.swiss_rounds_count == 4
        assert tournament.has_semifinals is False

        # -- Round 1: submit all, drop Team A_P1 (pid=1), finalize --
        submit_all_tables_ghost_aware(client, 1)

        drop_result = drop_team_player_api(client, player_id=1, round_num=1)
        assert drop_result['success'], f"Drop failed: {drop_result}"
        assert 1 in tournament.dropped_team_players

        score_at_drop_pid1 = tournament.player_scores[1]

        finalize_result = finalize_round(client)
        assert finalize_result['success']

        # -- Round 2: ghost-aware submit, drop Team B_P1 (pid=5), finalize --
        submit_all_tables_ghost_aware(client, 2)

        drop_result = drop_team_player_api(client, player_id=5, round_num=2)
        assert drop_result['success'], f"Drop failed: {drop_result}"

        score_at_drop_pid5 = tournament.player_scores[5]

        finalize_result = finalize_round(client)
        assert finalize_result['success']

        # -- Rounds 3-4: ghost-aware submit + finalize --
        for round_num in range(3, 5):
            submit_all_tables_ghost_aware(client, round_num)
            finalize_result = finalize_round(client)
            assert finalize_result['success'], f"Finalize round {round_num} failed"

        # After Swiss, should be in finals
        assert tournament.state == TournamentState.FINALS_IN_PROGRESS

        # -- Finals (round 5) --
        submit_all_tables_ghost_aware(client, 5)
        finalize_result = finalize_round(client)
        assert finalize_result['success']

        assert tournament.state == TournamentState.FINALS_COMPLETE

        # Ghost scores: Western adds 0 each round, so score stays at drop value
        assert tournament.player_scores[1] == score_at_drop_pid1
        assert tournament.player_scores[5] == score_at_drop_pid5

        # Team score consistency
        assert_team_score_consistency()

        # Final standings available
        resp = client.get('/final_standings')
        data = resp.get_json()
        assert data['success']

        # Both players still in dropped registry
        assert 1 in tournament.dropped_team_players
        assert 5 in tournament.dropped_team_players


class TestFull24TeamWithDrops:
    """24-team Western: 4 Swiss + Finals. 3 drops from 3 different teams at once."""

    def test_full_flow_ghost_spread(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=24)

        assert len(tournament.teams) == 24
        assert tournament.swiss_rounds_count == 4

        # -- Round 1: submit, drop 3 players from different teams, finalize --
        submit_all_tables_ghost_aware(client, 1)

        # Team C_P1 (pid=9), Team F_P2 (pid=22), Team J_P3 (pid=39)
        ghost_pids = [9, 22, 39]
        scores_at_drop = {}
        for pid in ghost_pids:
            scores_at_drop[pid] = tournament.player_scores[pid]
            drop_result = drop_team_player_api(client, player_id=pid, round_num=1)
            assert drop_result['success'], f"Drop pid={pid} failed: {drop_result}"

        finalize_result = finalize_round(client)
        assert finalize_result['success']

        # -- Rounds 2-4: ghost-aware submit + finalize --
        for round_num in range(2, 5):
            submit_all_tables_ghost_aware(client, round_num)
            finalize_result = finalize_round(client)
            assert finalize_result['success'], f"Finalize round {round_num} failed"

        assert tournament.state == TournamentState.FINALS_IN_PROGRESS

        # -- Finals --
        finals_round = tournament.current_round
        submit_all_tables_ghost_aware(client, finals_round)
        finalize_result = finalize_round(client)
        assert finalize_result['success']

        assert tournament.state == TournamentState.FINALS_COMPLETE

        # Ghost scores frozen at drop values
        for pid in ghost_pids:
            assert tournament.player_scores[pid] == scores_at_drop[pid], (
                f"Ghost pid={pid}: score {tournament.player_scores[pid]} != "
                f"drop value {scores_at_drop[pid]}"
            )

        # All 24 teams have valid scores
        tournament.calculate_team_scores()
        assert len(tournament.scores) == 24

        assert_team_score_consistency()

        resp = client.get('/final_standings')
        assert resp.get_json()['success']


class TestFull28TeamWithMultiDrops:
    """28-team Western: 4 Swiss + Finals. 2 drops from same team + min-2 enforcement."""

    def test_full_flow_max_drops_same_team(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=28)

        assert len(tournament.teams) == 28
        assert tournament.swiss_rounds_count == 4

        # -- Round 1: submit, drop 2 from Team A, verify 3rd rejected --
        submit_all_tables_ghost_aware(client, 1)

        # Drop Team A_P1 (pid=1)
        drop1 = drop_team_player_api(client, player_id=1, round_num=1)
        assert drop1['success'], f"First drop failed: {drop1}"

        # Drop Team A_P2 (pid=2) — Team A now has 2 active
        drop2 = drop_team_player_api(client, player_id=2, round_num=1)
        assert drop2['success'], f"Second drop failed: {drop2}"
        assert drop2['active_players_in_team'] == 2

        # Attempt 3rd drop — should be rejected
        drop3 = drop_team_player_api(client, player_id=3, round_num=1)
        assert drop3['success'] is False
        assert 'Minimum 2 required' in drop3['message']

        finalize_result = finalize_round(client)
        assert finalize_result['success']

        # -- Rounds 2-4: ghost-aware submit (Team A has 2 ghosts → 2-player pod) --
        for round_num in range(2, 5):
            submit_all_tables_ghost_aware(client, round_num)
            finalize_result = finalize_round(client)
            assert finalize_result['success'], f"Finalize round {round_num} failed"

        assert tournament.state == TournamentState.FINALS_IN_PROGRESS

        # -- Finals --
        finals_round = tournament.current_round
        submit_all_tables_ghost_aware(client, finals_round)
        finalize_result = finalize_round(client)
        assert finalize_result['success']

        assert tournament.state == TournamentState.FINALS_COMPLETE

        # Ghost scores frozen at drop-time value (0 added each subsequent round)
        drop_info_1 = tournament.dropped_team_players[1]
        drop_info_2 = tournament.dropped_team_players[2]
        assert tournament.player_scores[1] == drop_info_1['score_at_drop']
        assert tournament.player_scores[2] == drop_info_2['score_at_drop']

        # Team A still participated through the entire tournament
        tournament.calculate_team_scores()
        assert 'Team A' in tournament.scores

        assert_team_score_consistency()

        resp = client.get('/final_standings')
        assert resp.get_json()['success']


class TestFull32TeamWithDropAndUndrop:
    """32-team Western: 4 Swiss + Finals. Drop then undrop recovery + persistent drop."""

    def test_full_flow_drop_and_recovery(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=32)

        assert len(tournament.teams) == 32
        assert tournament.swiss_rounds_count == 4

        # -- Round 1: submit, drop Team D_P1 (pid=13), undrop, finalize --
        submit_all_tables_ghost_aware(client, 1)

        drop_result = drop_team_player_api(client, player_id=13, round_num=1)
        assert drop_result['success']
        assert 13 in tournament.dropped_team_players

        # Undrop immediately
        undrop_result = undrop_team_player_api(client, player_id=13)
        assert undrop_result['success'], f"Undrop failed: {undrop_result}"
        assert 13 not in tournament.dropped_team_players

        # Verify player is restored — name should not have "(Dropped)"
        team_d_players = tournament.teams['Team D']
        pid13_player = next(p for p in team_d_players if p['Player ID'] == 13)
        assert not pid13_player.get('is_dropped')
        assert '(Dropped)' not in pid13_player['Player Name']

        finalize_result = finalize_round(client)
        assert finalize_result['success']

        # -- Round 2: normal submit (no ghosts), drop Team H_P2 (pid=30), finalize --
        submit_all_tables_ghost_aware(client, 2)

        drop_result = drop_team_player_api(client, player_id=30, round_num=2)
        assert drop_result['success']

        score_at_drop_pid30 = tournament.player_scores[30]

        finalize_result = finalize_round(client)
        assert finalize_result['success']

        # -- Rounds 3-4: ghost-aware submit (1 ghost from Team H), finalize --
        for round_num in range(3, 5):
            submit_all_tables_ghost_aware(client, round_num)
            finalize_result = finalize_round(client)
            assert finalize_result['success'], f"Finalize round {round_num} failed"

        assert tournament.state == TournamentState.FINALS_IN_PROGRESS

        # -- Finals --
        finals_round = tournament.current_round
        submit_all_tables_ghost_aware(client, finals_round)
        finalize_result = finalize_round(client)
        assert finalize_result['success']

        assert tournament.state == TournamentState.FINALS_COMPLETE

        # Undropped player (pid=13) should still be active (not dropped)
        assert 13 not in tournament.dropped_team_players
        assert 13 in tournament.player_scores

        # Persistent ghost (pid=30) score frozen at drop value
        assert tournament.player_scores[30] == score_at_drop_pid30

        # Team D should have 4 active players, Team H should have 3
        active_d = sum(1 for p in tournament.teams['Team D'] if not p.get('is_dropped'))
        active_h = sum(1 for p in tournament.teams['Team H'] if not p.get('is_dropped'))
        assert active_d == 4
        assert active_h == 3

        assert_team_score_consistency()

        resp = client.get('/final_standings')
        assert resp.get_json()['success']
