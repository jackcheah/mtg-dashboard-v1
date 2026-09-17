"""Tests for PIN authentication on protected endpoints.

The @require_pin decorator protects 9 endpoints. Previously untested.

Run: pytest tests/unit/test_pin_protection.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from conftest import setup_via_api, submit_all_tables
from tournament_dashboard import tournament, TournamentState, EventMode
import tournament_dashboard


@pytest.fixture
def pin_client():
    """Flask test client with TOURNAMENT_PIN enabled."""
    original_pin = tournament_dashboard.TOURNAMENT_PIN
    tournament_dashboard.TOURNAMENT_PIN = '9876'
    tournament_dashboard.app.config['TESTING'] = True
    with tournament_dashboard.app.test_client() as c:
        yield c
    tournament_dashboard.TOURNAMENT_PIN = original_pin


@pytest.fixture
def nopin_client():
    """Flask test client with TOURNAMENT_PIN disabled."""
    original_pin = tournament_dashboard.TOURNAMENT_PIN
    tournament_dashboard.TOURNAMENT_PIN = None
    tournament_dashboard.app.config['TESTING'] = True
    with tournament_dashboard.app.test_client() as c:
        yield c
    tournament_dashboard.TOURNAMENT_PIN = original_pin


class TestPinRequired:
    """Verify PIN-protected endpoints reject requests without valid PIN."""

    def test_submit_table_results_requires_pin(self, pin_client):
        """POST /submit_table_results without PIN returns 403."""
        setup_via_api(pin_client, event_mode='team', num_teams=8)

        resp = pin_client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = pin_client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.status_code == 403
        data = resp.get_json()
        assert data['requires_pin'] is True

    def test_edit_table_results_requires_pin(self, pin_client):
        """POST /edit_table_results without PIN returns 403."""
        setup_via_api(pin_client, event_mode='team', num_teams=8)
        # Submit first table with PIN to get into SWISS_IN_PROGRESS
        resp = pin_client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]
        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        pin_client.post('/submit_table_results',
            json={'round': 1, 'table': table_name, 'results': results},
            headers={'X-Tournament-Pin': '9876'}
        )
        # Now try edit without PIN
        resp = pin_client.post('/edit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.status_code == 403
        data = resp.get_json()
        assert data['requires_pin'] is True

    def test_revert_table_requires_pin(self, pin_client):
        """POST /revert_table_submission without PIN returns 403."""
        setup_via_api(pin_client, event_mode='team', num_teams=8)
        # Submit first table with PIN to get into SWISS_IN_PROGRESS
        resp = pin_client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]
        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        pin_client.post('/submit_table_results',
            json={'round': 1, 'table': table_name, 'results': results},
            headers={'X-Tournament-Pin': '9876'}
        )
        # Now try revert without PIN
        resp = pin_client.post('/revert_table_submission', json={
            'round': 1, 'table': table_name
        })
        assert resp.status_code == 403
        data = resp.get_json()
        assert data['requires_pin'] is True


class TestCorrectPin:
    """Verify correct PIN allows requests through."""

    def test_correct_pin_in_header(self, pin_client):
        """X-Tournament-Pin header with correct PIN allows the request."""
        setup_via_api(pin_client, event_mode='team', num_teams=8)

        resp = pin_client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = pin_client.post('/submit_table_results',
            json={'round': 1, 'table': table_name, 'results': results},
            headers={'X-Tournament-Pin': '9876'}
        )
        assert resp.status_code == 200

    def test_correct_pin_in_json_body(self, pin_client):
        """PIN in JSON body {"pin": "9876"} should also work."""
        setup_via_api(pin_client, event_mode='team', num_teams=8)

        resp = pin_client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = pin_client.post('/submit_table_results',
            json={'round': 1, 'table': table_name, 'results': results,
                  'pin': '9876'}
        )
        assert resp.status_code == 200


class TestWrongPin:
    """Verify wrong PIN is rejected."""

    def test_wrong_pin_rejected(self, pin_client):
        """Incorrect PIN returns 403."""
        setup_via_api(pin_client, event_mode='team', num_teams=8)

        resp = pin_client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = pin_client.post('/submit_table_results',
            json={'round': 1, 'table': table_name, 'results': results},
            headers={'X-Tournament-Pin': 'wrong'}
        )
        assert resp.status_code == 403

    def test_integer_pin_in_body_rejected(self, pin_client):
        """Integer PIN in JSON body (1234 vs "1234") fails type comparison."""
        setup_via_api(pin_client, event_mode='team', num_teams=8)

        resp = pin_client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = pin_client.post('/submit_table_results',
            json={'round': 1, 'table': table_name, 'results': results,
                  'pin': 9876}
        )
        assert resp.status_code == 403


class TestNoPinMode:
    """Verify endpoints work normally when TOURNAMENT_PIN is not set."""

    def test_no_pin_required_when_unset(self, nopin_client):
        """When TOURNAMENT_PIN env var is not set, no PIN is needed."""
        setup_via_api(nopin_client, event_mode='team', num_teams=8)

        resp = nopin_client.get('/get_tables/1')
        tables = resp.get_json()['tables']
        table_name = list(tables.keys())[0]
        players = tables[table_name]

        results = [
            {'player_id': players[0]['Player ID'], 'points': 5},
            {'player_id': players[1]['Player ID'], 'points': 0},
            {'player_id': players[2]['Player ID'], 'points': 0},
            {'player_id': players[3]['Player ID'], 'points': 0},
        ]
        resp = nopin_client.post('/submit_table_results', json={
            'round': 1, 'table': table_name, 'results': results
        })
        assert resp.status_code == 200
