#!/usr/bin/env python3
"""
Score Correction Test Suite (Task 3.2)
Tests the /edit_table_results and /get_score_history endpoints within
the 16-team tournament flow.

Usage:
    python test_score_correction.py [--verbose]
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tournament_dashboard import app, tournament, TournamentState


class ScoreCorrectionTester:
    """Test suite for Task 3.2 Score Correction Mechanism."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = app.test_client()
        self.passed = []
        self.failed = []
        self.warnings = []

    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"  ℹ {message}")

    def add_pass(self, test_id: str, message: str):
        self.passed.append((test_id, message))
        print(f"\033[92m✓ [{test_id}] {message}\033[0m")

    def add_fail(self, test_id: str, message: str):
        self.failed.append((test_id, message))
        print(f"\033[91m✗ [{test_id}] {message}\033[0m")

    def add_warning(self, test_id: str, message: str):
        self.warnings.append((test_id, message))
        print(f"\033[93m⚠ [{test_id}] {message}\033[0m")

    def setup_16_team_tournament(self) -> bool:
        """Initialize a fresh 16-team tournament and submit some initial scores."""
        print("\n" + "=" * 70)
        print(" Setting Up 16-Team Tournament for Score Correction Tests")
        print("=" * 70)

        # Reset tournament state
        tournament.__init__()
        tournament.create_sample_data(16)

        # Setup tournament
        success, msg = tournament.setup_tournament(swiss_rounds=4)
        if not success:
            self.add_fail("SETUP-001", f"Tournament setup failed: {msg}")
            return False
        self.add_pass("SETUP-001", "16-team tournament setup complete")

        # Transition to SWISS_IN_PROGRESS by submitting first table
        if 1 in tournament.tables:
            first_table = list(tournament.tables[1].keys())[0]
            players = tournament.tables[1][first_table]

            # Initialize round results
            tournament.round_results[1] = {
                'table_submissions': {},
                'submitted_tables': set()
            }

            # Submit first table with initial scores
            initial_results = []
            for i, player in enumerate(players):
                points = 5 if i == 0 else 0  # First player wins
                initial_results.append({
                    'player_id': player['Player ID'],
                    'points': points
                })
                tournament.player_scores[player['Player ID']] += points

            tournament.round_results[1]['table_submissions'][first_table] = initial_results
            tournament.round_results[1]['submitted_tables'].add(first_table)

            # Transition state
            tournament.transition_to(TournamentState.SWISS_IN_PROGRESS, "Test setup")

            self.add_pass("SETUP-002", f"Submitted initial scores for {first_table}")
            self.log(f"Initial results: {initial_results}")
            return True
        else:
            self.add_fail("SETUP-002", "No tables found in Round 1")
            return False

    # =========================================================================
    # TEST SECTION 1: EDIT TABLE RESULTS ENDPOINT
    # =========================================================================

    def test_edit_table_results(self) -> bool:
        """Test the /edit_table_results endpoint."""
        print("\n" + "=" * 70)
        print(" Section 1: Edit Table Results Endpoint Tests")
        print("=" * 70)

        all_passed = True
        first_table = list(tournament.tables[1].keys())[0]
        players = tournament.tables[1][first_table]

        # EDIT-001: Edit a submitted table successfully
        new_results = []
        for i, player in enumerate(players):
            # Change who won: last player wins instead of first
            points = 5 if i == 3 else (1 if i == 0 else 0)
            new_results.append({
                'player_id': player['Player ID'],
                'points': points
            })

        response = self.client.post('/edit_table_results', json={
            'round': 1,
            'table': first_table,
            'results': new_results,
            'reason': 'Test correction - changing winner'
        })

        data = response.get_json()
        if response.status_code == 200 and data.get('success'):
            self.add_pass("EDIT-001", f"Successfully edited {first_table}")
            self.log(f"Edit count: {data.get('edit_count')}")
            self.log(f"Previous results: {data.get('previous_results')}")
        else:
            self.add_fail("EDIT-001", f"Edit failed: {data.get('error')}")
            all_passed = False

        # EDIT-002: Verify scores were recalculated correctly
        # Old winner (Player 0): should lose 5 pts, gain 1 pt = net -4
        # New winner (Player 3): should gain 5 pts
        player_0_id = players[0]['Player ID']
        player_3_id = players[3]['Player ID']

        expected_p0 = 1  # Changed from 5 to 1 (draw)
        expected_p3 = 5  # Changed from 0 to 5 (win)

        if tournament.player_scores.get(player_0_id) == expected_p0:
            self.add_pass("EDIT-002a", f"Player {player_0_id} score updated correctly: {expected_p0}")
        else:
            self.add_fail("EDIT-002a", f"Player {player_0_id} expected {expected_p0}, got {tournament.player_scores.get(player_0_id)}")
            all_passed = False

        if tournament.player_scores.get(player_3_id) == expected_p3:
            self.add_pass("EDIT-002b", f"Player {player_3_id} score updated correctly: {expected_p3}")
        else:
            self.add_fail("EDIT-002b", f"Player {player_3_id} expected {expected_p3}, got {tournament.player_scores.get(player_3_id)}")
            all_passed = False

        # EDIT-003: Verify history was recorded
        if 1 in tournament.round_results:
            history = tournament.round_results[1].get('score_history', {}).get(first_table, [])
            if len(history) == 1:
                self.add_pass("EDIT-003", "Edit history recorded correctly")
                self.log(f"History entry: {history[0]}")
            else:
                self.add_fail("EDIT-003", f"Expected 1 history entry, got {len(history)}")
                all_passed = False
        else:
            self.add_fail("EDIT-003", "Round results not found")
            all_passed = False

        # EDIT-004: Test editing unsubmitted table (should fail)
        unsubmitted_table = list(tournament.tables[1].keys())[1]  # A table not yet submitted
        response = self.client.post('/edit_table_results', json={
            'round': 1,
            'table': unsubmitted_table,
            'results': new_results,
            'reason': 'Should fail'
        })
        data = response.get_json()
        if response.status_code == 400 and not data.get('success'):
            self.add_pass("EDIT-004", "Correctly rejected edit of unsubmitted table")
        else:
            self.add_fail("EDIT-004", "Should have rejected edit of unsubmitted table")
            all_passed = False

        # EDIT-005: Test editing with invalid round (should fail)
        response = self.client.post('/edit_table_results', json={
            'round': 999,
            'table': first_table,
            'results': new_results
        })
        data = response.get_json()
        if response.status_code == 400:
            self.add_pass("EDIT-005", "Correctly rejected invalid round number")
        else:
            self.add_fail("EDIT-005", "Should have rejected invalid round")
            all_passed = False

        # EDIT-006: Test editing with invalid points (should fail)
        bad_results = [{'player_id': players[0]['Player ID'], 'points': 10}]  # 10 is invalid
        response = self.client.post('/edit_table_results', json={
            'round': 1,
            'table': first_table,
            'results': bad_results
        })
        data = response.get_json()
        if response.status_code == 400:
            self.add_pass("EDIT-006", "Correctly rejected invalid points value")
        else:
            self.add_fail("EDIT-006", "Should have rejected invalid points")
            all_passed = False

        # EDIT-007: Test editing with wrong number of players (should fail)
        incomplete_results = [{'player_id': players[0]['Player ID'], 'points': 5}]  # Only 1 player
        response = self.client.post('/edit_table_results', json={
            'round': 1,
            'table': first_table,
            'results': incomplete_results
        })
        data = response.get_json()
        if response.status_code == 400:
            self.add_pass("EDIT-007", "Correctly rejected incomplete player results")
        else:
            self.add_fail("EDIT-007", "Should have rejected incomplete results")
            all_passed = False

        return all_passed

    # =========================================================================
    # TEST SECTION 2: GET SCORE HISTORY ENDPOINT
    # =========================================================================

    def test_get_score_history(self) -> bool:
        """Test the /get_score_history endpoint."""
        print("\n" + "=" * 70)
        print(" Section 2: Get Score History Endpoint Tests")
        print("=" * 70)

        all_passed = True
        first_table = list(tournament.tables[1].keys())[0]

        # HIST-001: Get history for edited table
        encoded_table = first_table.replace(' ', '%20')
        response = self.client.get(f'/get_score_history/1/{encoded_table}')
        data = response.get_json()

        if response.status_code == 200 and data.get('success'):
            self.add_pass("HIST-001", f"History retrieved for {first_table}")
            self.log(f"Edit count: {data.get('edit_count')}")
            self.log(f"Has edits: {data.get('has_edits')}")
        else:
            self.add_fail("HIST-001", f"History retrieval failed: {data.get('error')}")
            all_passed = False

        # HIST-002: Verify history content
        if data.get('edit_count', 0) >= 1:
            history = data.get('history', [])
            if history:
                entry = history[0]
                if 'timestamp' in entry and 'old_results' in entry and 'new_results' in entry:
                    self.add_pass("HIST-002", "History entry contains required fields")
                else:
                    self.add_fail("HIST-002", f"History entry missing fields: {list(entry.keys())}")
                    all_passed = False
            else:
                self.add_fail("HIST-002", "History list is empty despite edit_count > 0")
                all_passed = False
        else:
            self.add_fail("HIST-002", "No edits found (expected at least 1)")
            all_passed = False

        # HIST-003: Get history for non-edited table (should return empty)
        second_table = list(tournament.tables[1].keys())[1]
        encoded_table2 = second_table.replace(' ', '%20')
        response = self.client.get(f'/get_score_history/1/{encoded_table2}')
        data = response.get_json()

        if response.status_code == 200 and data.get('edit_count', 0) == 0:
            self.add_pass("HIST-003", "Empty history returned for non-edited table")
        else:
            self.add_warning("HIST-003", f"Expected empty history, got: {data}")

        # HIST-004: Get history for non-existent round (should return 404)
        response = self.client.get('/get_score_history/999/Table%201')
        if response.status_code == 404:
            self.add_pass("HIST-004", "Correctly returned 404 for non-existent round")
        else:
            self.add_warning("HIST-004", f"Expected 404, got {response.status_code}")

        return all_passed

    # =========================================================================
    # TEST SECTION 3: FINALIZED ROUND PROTECTION
    # =========================================================================

    def test_finalized_round_protection(self) -> bool:
        """Test that finalized rounds cannot be edited."""
        print("\n" + "=" * 70)
        print(" Section 3: Finalized Round Protection Tests")
        print("=" * 70)

        all_passed = True
        first_table = list(tournament.tables[1].keys())[0]
        players = tournament.tables[1][first_table]

        # Finalize round 1
        tournament.finalized_rounds.add(1)

        # FINAL-001: Try to edit finalized round (should fail)
        new_results = [
            {'player_id': p['Player ID'], 'points': 1} for p in players
        ]
        response = self.client.post('/edit_table_results', json={
            'round': 1,
            'table': first_table,
            'results': new_results,
            'reason': 'Should fail - round finalized'
        })
        data = response.get_json()

        if response.status_code == 400 and not data.get('success'):
            if 'finalized' in data.get('error', '').lower():
                self.add_pass("FINAL-001", "Correctly rejected edit of finalized round")
            else:
                self.add_pass("FINAL-001", "Edit rejected (finalized protection)")
        else:
            self.add_fail("FINAL-001", "Should have rejected edit of finalized round")
            all_passed = False

        # Unfinalize for other tests
        tournament.finalized_rounds.discard(1)

        return all_passed

    # =========================================================================
    # TEST SECTION 4: MULTIPLE EDITS
    # =========================================================================

    def test_multiple_edits(self) -> bool:
        """Test that multiple edits are tracked properly."""
        print("\n" + "=" * 70)
        print(" Section 4: Multiple Edits Tests")
        print("=" * 70)

        all_passed = True
        first_table = list(tournament.tables[1].keys())[0]
        players = tournament.tables[1][first_table]

        # Edit 2 more times
        for edit_num in range(2):
            new_results = []
            for i, player in enumerate(players):
                points = 5 if i == edit_num else 0
                new_results.append({
                    'player_id': player['Player ID'],
                    'points': points
                })

            response = self.client.post('/edit_table_results', json={
                'round': 1,
                'table': first_table,
                'results': new_results,
                'reason': f'Multiple edit test #{edit_num + 2}'
            })

        # MULTI-001: Check edit count
        encoded_table = first_table.replace(' ', '%20')
        response = self.client.get(f'/get_score_history/1/{encoded_table}')
        data = response.get_json()

        # We had 1 edit from earlier tests + 2 more = 3 total
        expected_edits = 3
        if data.get('edit_count', 0) >= expected_edits:
            self.add_pass("MULTI-001", f"Multiple edits tracked: {data.get('edit_count')} edits")
        else:
            self.add_fail("MULTI-001", f"Expected at least {expected_edits} edits, got {data.get('edit_count')}")
            all_passed = False

        # MULTI-002: Verify each edit has timestamp
        history = data.get('history', [])
        timestamps_valid = all('timestamp' in entry for entry in history)
        if timestamps_valid:
            self.add_pass("MULTI-002", "All edits have timestamps")
        else:
            self.add_fail("MULTI-002", "Some edits missing timestamps")
            all_passed = False

        return all_passed

    # =========================================================================
    # TEST SECTION 5: STATE VALIDATION
    # =========================================================================

    def test_state_validation(self) -> bool:
        """Test that editing requires proper tournament state."""
        print("\n" + "=" * 70)
        print(" Section 5: State Validation Tests")
        print("=" * 70)

        all_passed = True
        first_table = list(tournament.tables[1].keys())[0]
        players = tournament.tables[1][first_table]

        new_results = [
            {'player_id': p['Player ID'], 'points': 1} for p in players
        ]

        # STATE-001: Test with TOURNAMENT_SETUP state (should fail)
        original_state = tournament.state
        tournament.state = TournamentState.TOURNAMENT_SETUP

        response = self.client.post('/edit_table_results', json={
            'round': 1,
            'table': first_table,
            'results': new_results
        })

        if response.status_code == 400:
            self.add_pass("STATE-001", "Editing blocked in TOURNAMENT_SETUP state")
        else:
            self.add_fail("STATE-001", f"Should block editing in TOURNAMENT_SETUP, got {response.status_code}")
            all_passed = False

        # Restore state
        tournament.state = original_state

        return all_passed

    # =========================================================================
    # MAIN TEST RUNNER
    # =========================================================================

    def run_all_tests(self) -> bool:
        """Run complete test suite."""
        print("\n" + "=" * 70)
        print("  Task 3.2 Score Correction - Test Suite")
        print("  Testing with 16-team tournament flow")
        print("=" * 70)

        # Setup tournament
        if not self.setup_16_team_tournament():
            print("\n\033[91m✗ SETUP FAILED - Cannot proceed\033[0m")
            return False

        # Run test sections
        self.test_edit_table_results()
        self.test_get_score_history()
        self.test_finalized_round_protection()
        self.test_multiple_edits()
        self.test_state_validation()

        # Print summary
        print("\n" + "=" * 70)
        print("  Test Summary")
        print("=" * 70)
        print(f"  Passed:   \033[92m{len(self.passed)}\033[0m")
        print(f"  Failed:   \033[91m{len(self.failed)}\033[0m")
        print(f"  Warnings: \033[93m{len(self.warnings)}\033[0m")

        if len(self.failed) == 0:
            print(f"\n\033[92m✓ ALL TESTS PASSED!\033[0m")
            return True
        else:
            print(f"\n\033[91m✗ SOME TESTS FAILED\033[0m")
            print("\n  Failed tests:")
            for test_id, msg in self.failed:
                print(f"    - [{test_id}] {msg}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Task 3.2 Score Correction Test Suite')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output')
    args = parser.parse_args()

    tester = ScoreCorrectionTester(verbose=args.verbose)
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
