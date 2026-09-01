"""Tests for TopDeck.gg pairings CSV exporter.

Covers: extract_table_number, validate_round_for_topdeck, build_pairings_csv,
generate_export_filename, and the /topdeck/* Flask endpoints.

Run: pytest tests/unit/test_topdeck_exporter.py -v
"""
import sys
import os
import csv
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from conftest import setup_via_api, submit_all_tables, finalize_round
from tournament_dashboard import tournament, TournamentState
import topdeck_exporter


# ==========================================
# extract_table_number
# ==========================================

class TestExtractTableNumber:
    def test_swiss_table(self):
        assert topdeck_exporter.extract_table_number("Table 1") == 1

    def test_swiss_table_double_digit(self):
        assert topdeck_exporter.extract_table_number("Table 12") == 12

    def test_semifinals_table(self):
        assert topdeck_exporter.extract_table_number("Semifinals Table 3") == 3

    def test_finals_table_numbered(self):
        assert topdeck_exporter.extract_table_number("Finals Table 2") == 2

    def test_finals_table_no_number(self):
        assert topdeck_exporter.extract_table_number("Finals Table") == 1

    def test_empty_string(self):
        assert topdeck_exporter.extract_table_number("") == 1

    def test_trailing_whitespace(self):
        assert topdeck_exporter.extract_table_number("Table 5 ") == 5


# ==========================================
# validate_round_for_topdeck
# ==========================================

def _make_player(pid, name, team="Team X"):
    return {"Player ID": pid, "Player Name": name, "Team Name": team}


def _make_tables(*pods, prefix="Table"):
    """Build a tables dict from lists of player tuples (pid, name, team)."""
    tables = {}
    for i, pod in enumerate(pods, 1):
        tables[f"{prefix} {i}"] = [_make_player(pid, name, team) for pid, name, team in pod]
    return tables


class TestValidateRoundForTopdeck:
    def test_round_not_exist(self):
        result = topdeck_exporter.validate_round_for_topdeck(
            tables={}, round_num=1, finalized_rounds={1}, event_mode='team'
        )
        assert len(result['errors']) > 0
        assert 'does not exist' in result['errors'][0]

    def test_round_none(self):
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=None, round_num=1, finalized_rounds={1}, event_mode='team'
        )
        assert len(result['errors']) > 0

    def test_round_not_finalized(self):
        tables = _make_tables(
            [(1, "A", "T1"), (2, "B", "T2"), (3, "C", "T3"), (4, "D", "T4")]
        )
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=1, finalized_rounds=set(), event_mode='team'
        )
        assert any('not been finalized' in e for e in result['errors'])

    def test_duplicate_player_name(self):
        tables = _make_tables(
            [(1, "Alice", "T1"), (2, "Bob", "T2"), (3, "Carol", "T3"), (4, "Dave", "T4")],
            [(5, "Alice", "T5"), (6, "Eve", "T6"), (7, "Frank", "T7"), (8, "Grace", "T8")],
        )
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=1, finalized_rounds={1}, event_mode='team'
        )
        assert any('Duplicate exported player name' in e for e in result['errors'])

    def test_missing_player_name(self):
        tables = _make_tables(
            [(1, "", "T1"), (2, "Bob", "T2"), (3, "Carol", "T3"), (4, "Dave", "T4")]
        )
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=1, finalized_rounds={1}, event_mode='team'
        )
        assert any('missing or empty name' in e for e in result['errors'])

    def test_team_mode_pod_size_wrong(self):
        tables = {"Table 1": [_make_player(1, "A", "T1"), _make_player(2, "B", "T2"), _make_player(3, "C", "T3")]}
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=1, finalized_rounds={1}, event_mode='team'
        )
        assert any('3 players (expected 4)' in e for e in result['errors'])

    def test_individual_mode_3_player_pod_ok_with_warning(self):
        tables = {"Table 1": [_make_player(1, "A", "A"), _make_player(2, "B", "B"), _make_player(3, "C", "C")]}
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=1, finalized_rounds={1}, event_mode='individual'
        )
        assert len(result['errors']) == 0
        assert any('three-player pod' in w for w in result['warnings'])
        assert any('not been verified' in w for w in result['warnings'])

    def test_teammate_conflict(self):
        tables = _make_tables(
            [(1, "A", "TeamX"), (2, "B", "TeamX"), (3, "C", "T3"), (4, "D", "T4")]
        )
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=1, finalized_rounds={1}, event_mode='team'
        )
        assert any("seated together" in e for e in result['errors'])

    def test_player_on_multiple_tables(self):
        tables = {
            "Table 1": [_make_player(1, "A", "T1"), _make_player(2, "B", "T2"),
                        _make_player(3, "C", "T3"), _make_player(4, "D", "T4")],
            "Table 2": [_make_player(1, "A2", "T5"), _make_player(5, "E", "T6"),
                        _make_player(6, "F", "T7"), _make_player(7, "G", "T8")],
        }
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=1, finalized_rounds={1}, event_mode='team'
        )
        assert any('assigned to both' in e for e in result['errors'])

    def test_valid_team_round_passes(self):
        tables = _make_tables(
            [(1, "A", "T1"), (2, "B", "T2"), (3, "C", "T3"), (4, "D", "T4")],
            [(5, "E", "T5"), (6, "F", "T6"), (7, "G", "T7"), (8, "H", "T8")],
        )
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=1, finalized_rounds={1}, event_mode='team'
        )
        assert len(result['errors']) == 0
        assert result['summary']['status'] == 'Ready for TopDeck import'

    def test_dropped_player_warning(self):
        tables = _make_tables(
            [(1, "A", "T1"), (2, "B", "T2"), (3, "C", "T3"), (4, "D", "T4")]
        )
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=1, finalized_rounds={1}, event_mode='individual',
            dropped_players={99: {'name': 'Zara'}}
        )
        assert len(result['errors']) == 0
        assert any('dropped' in w.lower() for w in result['warnings'])

    def test_bye_player_warning(self):
        tables = _make_tables(
            [(1, "A", "T1"), (2, "B", "T2"), (3, "C", "T3"), (4, "D", "T4")]
        )
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=1, finalized_rounds={1}, event_mode='individual',
            bye_players=[99, 100]
        )
        assert any('bye' in w.lower() for w in result['warnings'])

    def test_summary_counts(self):
        tables = _make_tables(
            [(1, "A", "T1"), (2, "B", "T2"), (3, "C", "T3"), (4, "D", "T4")],
            [(5, "E", "T5"), (6, "F", "T6"), (7, "G", "T7"), (8, "H", "T8")],
        )
        result = topdeck_exporter.validate_round_for_topdeck(
            tables=tables, round_num=3, finalized_rounds={3}, event_mode='team'
        )
        s = result['summary']
        assert s['round'] == 3
        assert s['tables'] == 2
        assert s['players_exported'] == 8
        assert s['result_data_included'] is False


# ==========================================
# build_pairings_csv
# ==========================================

class TestBuildPairingsCsv:
    def test_csv_header(self):
        tables = _make_tables(
            [(1, "A", "T1"), (2, "B", "T2"), (3, "C", "T3"), (4, "D", "T4")]
        )
        csv_bytes = topdeck_exporter.build_pairings_csv(tables, 'team')
        lines = csv_bytes.decode('utf-8').strip().split('\r\n')
        assert lines[0] == 'table,player 1,player 2,player 3,player 4'

    def test_basic_csv_structure(self):
        tables = _make_tables(
            [(1, "A", "T1"), (2, "B", "T2"), (3, "C", "T3"), (4, "D", "T4")],
            [(5, "E", "T5"), (6, "F", "T6"), (7, "G", "T7"), (8, "H", "T8")],
        )
        csv_bytes = topdeck_exporter.build_pairings_csv(tables, 'team')
        reader = csv.reader(io.StringIO(csv_bytes.decode('utf-8')))
        rows = list(reader)
        assert len(rows) == 3  # header + 2 data rows

    def test_csv_table_numbers_sequential(self):
        tables = {
            "Table 3": [_make_player(1, "A", "T1"), _make_player(2, "B", "T2"),
                        _make_player(3, "C", "T3"), _make_player(4, "D", "T4")],
            "Table 7": [_make_player(5, "E", "T5"), _make_player(6, "F", "T6"),
                        _make_player(7, "G", "T7"), _make_player(8, "H", "T8")],
        }
        csv_bytes = topdeck_exporter.build_pairings_csv(tables, 'team')
        reader = csv.reader(io.StringIO(csv_bytes.decode('utf-8')))
        rows = list(reader)
        assert rows[1][0] == '1'
        assert rows[2][0] == '2'

    def test_csv_player_names_stripped(self):
        tables = {"Table 1": [
            _make_player(1, "  Alice  ", "T1"), _make_player(2, "Bob", "T2"),
            _make_player(3, "Carol", "T3"), _make_player(4, "Dave", "T4"),
        ]}
        csv_bytes = topdeck_exporter.build_pairings_csv(tables, 'team')
        reader = csv.reader(io.StringIO(csv_bytes.decode('utf-8')))
        rows = list(reader)
        assert rows[1][1] == 'Alice'

    def test_csv_special_characters(self):
        tables = {"Table 1": [
            _make_player(1, "O'Brien", "T1"), _make_player(2, "Lee, Jr.", "T2"),
            _make_player(3, "José García", "T3"), _make_player(4, "田中太郎", "T4"),
        ]}
        csv_bytes = topdeck_exporter.build_pairings_csv(tables, 'team')
        text = csv_bytes.decode('utf-8')
        assert "O'Brien" in text
        assert "José García" in text
        assert "田中太郎" in text
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert rows[1][2] == "Lee, Jr."

    def test_csv_utf8_encoding(self):
        tables = {"Table 1": [
            _make_player(1, "Ünsal", "T1"), _make_player(2, "Müller", "T2"),
            _make_player(3, "Björk", "T3"), _make_player(4, "Čech", "T4"),
        ]}
        csv_bytes = topdeck_exporter.build_pairings_csv(tables, 'team')
        text = csv_bytes.decode('utf-8')
        assert "Ünsal" in text
        assert "Čech" in text

    def test_csv_3_player_pod_individual_mode(self):
        tables = {"Table 1": [
            _make_player(1, "A", "A"), _make_player(2, "B", "B"), _make_player(3, "C", "C"),
        ]}
        csv_bytes = topdeck_exporter.build_pairings_csv(tables, 'individual')
        reader = csv.reader(io.StringIO(csv_bytes.decode('utf-8')))
        rows = list(reader)
        assert len(rows[1]) == 5  # table + 4 columns (player 4 empty)
        assert rows[1][4] == ''

    def test_csv_deterministic(self):
        tables = _make_tables(
            [(1, "A", "T1"), (2, "B", "T2"), (3, "C", "T3"), (4, "D", "T4")],
            [(5, "E", "T5"), (6, "F", "T6"), (7, "G", "T7"), (8, "H", "T8")],
        )
        out1 = topdeck_exporter.build_pairings_csv(tables, 'team')
        out2 = topdeck_exporter.build_pairings_csv(tables, 'team')
        assert out1 == out2

    def test_32_players_8_tables(self):
        pods = []
        pid = 1
        for i in range(8):
            pod = []
            for j in range(4):
                pod.append((pid, f"Player_{pid}", f"Team_{i * 4 + j}"))
                pid += 1
            pods.append(pod)
        tables = _make_tables(*pods)
        csv_bytes = topdeck_exporter.build_pairings_csv(tables, 'team')
        reader = csv.reader(io.StringIO(csv_bytes.decode('utf-8')))
        rows = list(reader)
        assert len(rows) == 9  # header + 8 data rows

    def test_no_player_appears_twice(self):
        pods = []
        pid = 1
        for _ in range(4):
            pod = [(pid + j, f"Player_{pid + j}", f"T{pid + j}") for j in range(4)]
            pid += 4
            pods.append(pod)
        tables = _make_tables(*pods)
        csv_bytes = topdeck_exporter.build_pairings_csv(tables, 'team')
        reader = csv.reader(io.StringIO(csv_bytes.decode('utf-8')))
        rows = list(reader)[1:]  # skip header
        all_names = []
        for row in rows:
            all_names.extend([n for n in row[1:] if n])
        assert len(all_names) == len(set(all_names))


# ==========================================
# generate_export_filename
# ==========================================

class TestGenerateExportFilename:
    def test_without_event_name(self):
        assert topdeck_exporter.generate_export_filename(3) == "topdeck_round_03_pairings.csv"

    def test_with_event_name(self):
        name = topdeck_exporter.generate_export_filename(1, "Four Horsemen 2026")
        assert name == "topdeck_four-horsemen-2026_round_01_pairings.csv"

    def test_single_digit_round(self):
        assert "round_01" in topdeck_exporter.generate_export_filename(1)

    def test_double_digit_round(self):
        assert "round_12" in topdeck_exporter.generate_export_filename(12)


# ==========================================
# Flask endpoint integration tests
# ==========================================

class TestTopdeckEndpoints:
    def test_validate_returns_errors_for_unfinalized_round(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        # Submit all tables and finalize round 1 to advance to SWISS_IN_PROGRESS
        submit_all_tables(client, 1)
        finalize_round(client)
        # Now round 2 exists but is not finalized
        resp = client.get('/topdeck/validate/2')
        data = resp.get_json()
        assert data['success'] is False
        assert any('not been finalized' in e for e in data['errors'])

    def test_validate_passes_after_finalization(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)
        finalize_round(client)
        resp = client.get('/topdeck/validate/1')
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['errors']) == 0
        assert data['summary']['tables'] == 8
        assert data['summary']['players_exported'] == 32

    def test_export_blocked_before_finalization(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        resp = client.get('/topdeck/export/1')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_export_succeeds_after_finalization(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)
        finalize_round(client)
        resp = client.get('/topdeck/export/1')
        assert resp.status_code == 200
        assert resp.content_type == 'text/csv; charset=utf-8'

    def test_export_csv_content_correct(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)
        finalize_round(client)
        resp = client.get('/topdeck/export/1')
        text = resp.data.decode('utf-8')
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert rows[0] == ['table', 'player 1', 'player 2', 'player 3', 'player 4']
        assert len(rows) == 9  # header + 8 tables
        all_names = []
        for row in rows[1:]:
            assert len(row) == 5
            names = [n for n in row[1:] if n]
            assert len(names) == 4
            all_names.extend(names)
        assert len(all_names) == 32
        assert len(set(all_names)) == 32

    def test_export_wrong_state_returns_400(self, client):
        resp = client.get('/topdeck/export/1')
        assert resp.status_code == 400

    def test_validate_nonexistent_round(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)
        finalize_round(client)
        resp = client.get('/topdeck/validate/99')
        data = resp.get_json()
        assert data['success'] is False
        assert any('does not exist' in e for e in data['errors'])

    def test_export_filename_in_content_disposition(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=8)
        submit_all_tables(client, 1)
        finalize_round(client)
        resp = client.get('/topdeck/export/1')
        cd = resp.headers.get('Content-Disposition', '')
        assert 'topdeck_round_01_pairings.csv' in cd

    def test_validate_team_mode_12_teams(self, client):
        setup_via_api(client, event_mode='team', scoring_mode='western', num_teams=12)
        submit_all_tables(client, 1)
        finalize_round(client)
        resp = client.get('/topdeck/validate/1')
        data = resp.get_json()
        assert data['success'] is True
        assert data['summary']['tables'] == 12
        assert data['summary']['players_exported'] == 48

    def test_validate_individual_mode(self, client):
        setup_via_api(client, event_mode='individual', scoring_mode='western', num_teams=16)
        submit_all_tables(client, 1)
        finalize_round(client)
        resp = client.get('/topdeck/validate/1')
        data = resp.get_json()
        assert data['success'] is True
        assert data['summary']['players_exported'] == 16
