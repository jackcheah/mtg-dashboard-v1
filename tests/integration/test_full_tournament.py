"""Integration tests: Complete tournament flows via Flask test client.

Each test exercises the FULL lifecycle of a tournament from setup to champion.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from tournament_dashboard import TournamentManager, TournamentState, ScoringMode, EventMode, app, tournament
from tests.conftest import make_tournament, setup_via_api, submit_all_tables, finalize_round


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


def get_state(client):
    resp = client.get('/get_tournament_state')
    return resp.get_json()


def submit_table(client, round_num, table_name, players, winner_idx=0):
    results = []
    for idx, p in enumerate(players):
        pid = p['Player ID']
        points = 5 if idx == winner_idx else 0
        results.append({'player_id': pid, 'points': points})
    return client.post('/submit_table_results', json={
        'round': round_num, 'table': table_name, 'results': results
    })


class TestFull8TeamWestern:
    """Complete 8-team Western scoring tournament: 3 Swiss + Finals."""

    def test_full_flow(self, client):
        # Setup
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        state = get_state(client)
        assert state['success']
        assert len(state['teams']) == 8

        # Swiss Rounds
        swiss_count = tournament.swiss_rounds_count
        for round_num in range(1, swiss_count + 1):
            results = submit_all_tables(client, round_num)
            assert all(r['success'] for r in results)

            # Verify can_finalize
            state = get_state(client)
            assert state['can_finalize'] is True

            # Finalize
            resp = finalize_round(client)
            assert resp['success']

        # After Swiss rounds, should be in finals
        assert tournament.state == TournamentState.FINALS_IN_PROGRESS

        # Finals round
        finals_round = tournament.current_round
        results = submit_all_tables(client, finals_round)
        assert all(r['success'] for r in results)

        resp = finalize_round(client)
        assert resp['success']

        # Tournament should be complete
        assert tournament.state == TournamentState.FINALS_COMPLETE

        # Final standings
        resp = client.get('/final_standings')
        data = resp.get_json()
        assert data['success']
        assert 'champion' in data or 'standings' in data


class TestFull16TeamWestern:
    """Complete 16-team Western tournament: 3 Swiss + Finals (no Top 8 Cut)."""

    def test_full_flow(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=16)
        state = get_state(client)
        assert len(state['teams']) == 16
        assert tournament.has_semifinals is False

        # Swiss Rounds
        swiss_count = tournament.swiss_rounds_count
        for round_num in range(1, swiss_count + 1):
            submit_all_tables(client, round_num)
            finalize_round(client)

        # Should go directly to Finals (no Top 8 Cut for ≤16 teams)
        assert tournament.state == TournamentState.FINALS_IN_PROGRESS

        # Finals round
        finals_round = tournament.current_round
        submit_all_tables(client, finals_round)
        finalize_round(client)

        assert tournament.state == TournamentState.FINALS_COMPLETE


class TestFull12TeamWestern:
    """Complete 12-team Western tournament: 3 Swiss + Finals."""

    def test_full_flow(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=12)
        state = get_state(client)
        assert len(state['teams']) == 12

        # Swiss Rounds
        swiss_count = tournament.swiss_rounds_count
        for round_num in range(1, swiss_count + 1):
            submit_all_tables(client, round_num)
            finalize_round(client)

        # Finals
        assert tournament.state == TournamentState.FINALS_IN_PROGRESS
        finals_round = tournament.current_round
        submit_all_tables(client, finals_round)
        finalize_round(client)

        assert tournament.state == TournamentState.FINALS_COMPLETE


class TestFull8TeamJapanese:
    """Complete 8-team Japanese scoring tournament."""

    def test_full_flow(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='japanese', num_teams=8)

        # Verify Japanese starting scores
        for pid, score in tournament.player_scores.items():
            assert score == 1000

        # Swiss Rounds
        swiss_count = tournament.swiss_rounds_count
        for round_num in range(1, swiss_count + 1):
            submit_all_tables(client, round_num)
            finalize_round(client)

        # After Swiss, scores should have deviated from 1000
        scores = list(tournament.player_scores.values())
        assert max(scores) > 1000
        assert min(scores) < 1000

        # Finals
        assert tournament.state == TournamentState.FINALS_IN_PROGRESS
        finals_round = tournament.current_round
        submit_all_tables(client, finals_round)
        finalize_round(client)

        assert tournament.state == TournamentState.FINALS_COMPLETE


class TestFull16PlayerIndividual:
    """Complete 16-player individual Western tournament: 4 Swiss + Finals."""

    def test_full_flow(self, client):
        data = setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=16)
        assert data['success']

        assert tournament.event_mode == EventMode.INDIVIDUAL

        # Swiss Rounds 1-4
        for round_num in range(1, 5):
            submit_all_tables(client, round_num)
            finalize_round(client)

        # Finals
        finals_round = tournament.current_round
        submit_all_tables(client, finals_round)
        finalize_round(client)

        assert tournament.state == TournamentState.FINALS_COMPLETE


class TestFull20PlayerIndividualWithTopCut:
    """20-player individual tournament with Top Cut: 4 Swiss + Top Cut + Finals."""

    def test_full_flow(self, client):
        data = setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=20)
        assert data['success']

        assert tournament.has_top_cut is True
        assert len(tournament.participants) == 20

        # Swiss Rounds 1-4
        for round_num in range(1, 5):
            submit_all_tables(client, round_num)
            finalize_round(client)

        # Top Cut round
        top_cut_round = tournament.current_round
        submit_all_tables(client, top_cut_round)
        finalize_round(client)

        # Finals
        finals_round = tournament.current_round
        submit_all_tables(client, finals_round)
        finalize_round(client)

        assert tournament.state == TournamentState.FINALS_COMPLETE


class TestIndividualWithPlayerDrops:
    """Individual tournament with player drops mid-event (needs >16 to stay above minimum)."""

    def test_drop_mid_tournament(self, client):
        setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=20)

        initial_count = len(tournament.participants)
        assert initial_count == 20

        # Round 1: submit all, then drop a player before finalization
        submit_all_tables(client, 1)

        # Find a player to drop
        player_to_drop = tournament.participants[-1]
        drop_id = player_to_drop['Player ID']

        resp = client.post('/drop_player', json={
            'player_id': drop_id,
            'round': 1
        })
        data = resp.get_json()
        assert data['success']
        assert len(tournament.participants) == initial_count - 1
        assert drop_id in tournament.dropped_players

        # Finalize round 1
        finalize_round(client)

        # Round 2 should work with fewer players
        submit_all_tables(client, 2)
        finalize_round(client)

        # Continue remaining Swiss rounds
        for round_num in range(3, 5):
            submit_all_tables(client, round_num)
            finalize_round(client)

        # Top cut (20 players → has top cut)
        if tournament.has_top_cut:
            top_cut_round = tournament.current_round
            submit_all_tables(client, top_cut_round)
            finalize_round(client)

        # Finals
        finals_round = tournament.current_round
        submit_all_tables(client, finals_round)
        finalize_round(client)

        assert tournament.state == TournamentState.FINALS_COMPLETE
        assert drop_id in tournament.dropped_players


class TestRevertAndResubmit:
    """Error recovery: submit → revert → resubmit with different scores."""

    def test_revert_flow(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)

        # Submit first table with player 0 winning
        state = get_state(client)
        tables = state['tables'].get('1') or state['tables'].get(1, {})
        if not tables:
            resp = client.get('/get_tables/1')
            tables = resp.get_json().get('tables', {})

        table_name = list(tables.keys())[0]
        players = tables[table_name]
        pid_0 = players[0]['Player ID']

        # Submit with player 0 winning
        resp = submit_table(client, 1, table_name, players, winner_idx=0)
        assert resp.get_json()['success']

        score_after_submit = tournament.player_scores[pid_0]
        assert score_after_submit == 5

        # Revert
        resp = client.post('/revert_table_submission', json={
            'round': 1, 'table': table_name
        })
        assert resp.get_json()['success']
        assert tournament.player_scores[pid_0] == 0

        # Resubmit with player 1 winning
        resp = submit_table(client, 1, table_name, players, winner_idx=1)
        assert resp.get_json()['success']
        assert tournament.player_scores[pid_0] == 0
        assert tournament.player_scores[players[1]['Player ID']] == 5


class TestEditTableMidRound:
    """Edit scores after submission: verify corrections apply correctly."""

    def test_edit_flow(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)

        resp = client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        # Submit with player 0 winning
        submit_table(client, 1, table_name, players, winner_idx=0)

        pid_0 = players[0]['Player ID']
        pid_1 = players[1]['Player ID']
        assert tournament.player_scores[pid_0] == 5
        assert tournament.player_scores[pid_1] == 0

        # Edit: change winner to player 1
        new_results = [
            {'player_id': p['Player ID'], 'points': 5 if i == 1 else 0}
            for i, p in enumerate(players)
        ]
        resp = client.post('/edit_table_results', json={
            'round': 1,
            'table': table_name,
            'results': new_results,
            'reason': 'Correcting winner'
        })
        data = resp.get_json()
        assert data['success']

        # Verify corrected scores
        assert tournament.player_scores[pid_0] == 0
        assert tournament.player_scores[pid_1] == 5


class TestBackupRestoreMidTournament:
    """Backup after round 2, continue, then restore and verify state."""

    def test_backup_restore(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)

        # Play rounds 1-2
        submit_all_tables(client, 1)
        finalize_round(client)
        submit_all_tables(client, 2)
        finalize_round(client)

        round_2_scores = dict(tournament.player_scores)

        # Save backup
        resp = client.post('/save_backup')
        assert resp.get_json()['success']

        # Play round 3
        submit_all_tables(client, 3)
        finalize_round(client)

        # Scores should have changed from round 2
        assert tournament.player_scores != round_2_scores

        # Restore from backup
        resp = client.post('/restore_backup')
        data = resp.get_json()
        assert data['success']

        # Verify restored to round 2+ state (round advances after finalization)
        assert tournament.current_round >= 3
        assert 1 in tournament.finalized_rounds
        assert 2 in tournament.finalized_rounds
