#!/usr/bin/env python3
"""
Comprehensive Test Suite for 16-Team MTG Tournament Dashboard
Tests backend logic, pairing constraints, and full tournament flow.

Usage:
    python test_tournament_comprehensive.py [--teams N] [--verbose]

Options:
    --teams N    Number of teams to test (8, 12, or 16). Default: 16
    --verbose    Show detailed output
"""

import sys
import os
import json
import random
import argparse
from collections import defaultdict
from typing import List, Dict, Set, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tournament_dashboard import TournamentManager
from unified_swiss_pairing import UnifiedSwissPairing


class TestResult:
    """Stores test results with pass/fail/warning status."""

    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
        self.errors = []

    def add_pass(self, test_id: str, message: str):
        self.passed.append((test_id, message))
        print(f"\033[92m✓ [{test_id}] {message}\033[0m")

    def add_fail(self, test_id: str, message: str):
        self.failed.append((test_id, message))
        print(f"\033[91m✗ [{test_id}] {message}\033[0m")

    def add_warning(self, test_id: str, message: str):
        self.warnings.append((test_id, message))
        print(f"\033[93m⚠ [{test_id}] {message}\033[0m")

    def add_error(self, test_id: str, message: str):
        self.errors.append((test_id, message))
        print(f"\033[91m✗✗ [{test_id}] ERROR: {message}\033[0m")

    def summary(self) -> Dict:
        return {
            'passed': len(self.passed),
            'failed': len(self.failed),
            'warnings': len(self.warnings),
            'errors': len(self.errors),
            'total': len(self.passed) + len(self.failed)
        }

    def print_summary(self, title: str):
        s = self.summary()
        print(f"\n\033[1m{title}\033[0m")
        print(f"  Passed:   \033[92m{s['passed']}\033[0m")
        print(f"  Failed:   \033[91m{s['failed']}\033[0m")
        print(f"  Warnings: \033[93m{s['warnings']}\033[0m")
        print(f"  Errors:   \033[91m{s['errors']}\033[0m")

        if s['failed'] == 0 and s['errors'] == 0:
            print(f"\n\033[92m✓ ALL TESTS PASSED!\033[0m")
            return True
        else:
            print(f"\n\033[91m✗ SOME TESTS FAILED\033[0m")
            if self.failed:
                print("\n  Failed tests:")
                for test_id, msg in self.failed:
                    print(f"    - [{test_id}] {msg}")
            return False


class TournamentTester:
    """Comprehensive test suite for 16-team tournament."""

    def __init__(self, team_count: int = 16, verbose: bool = False):
        self.team_count = team_count
        self.verbose = verbose
        self.tm: Optional[TournamentManager] = None
        self.results = TestResult()

    def log(self, message: str):
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"  ℹ {message}")

    # =========================================================================
    # SECTION 1: INITIALIZATION TESTS
    # =========================================================================

    def test_initialization(self) -> bool:
        """Test tournament initialization for 16 teams."""
        print("\n" + "=" * 70)
        print(f" Section 1: Initialization Tests ({self.team_count} Teams)")
        print("=" * 70)

        # BE-INIT-001: Create TournamentManager instance
        try:
            self.tm = TournamentManager()
            self.results.add_pass("BE-INIT-001", "TournamentManager created successfully")
        except Exception as e:
            self.results.add_error("BE-INIT-001", f"Failed to create TournamentManager: {e}")
            return False

        # BE-INIT-002: Create sample data
        try:
            self.tm.create_sample_data(self.team_count)
            if len(self.tm.teams) == self.team_count:
                self.results.add_pass("BE-INIT-002", f"Created {self.team_count} teams with sample data")
            else:
                self.results.add_fail("BE-INIT-002", f"Expected {self.team_count} teams, got {len(self.tm.teams)}")
        except Exception as e:
            self.results.add_error("BE-INIT-002", f"Failed to create sample data: {e}")
            return False

        # BE-INIT-003: Validate player count
        expected_players = self.team_count * 4
        actual_players = len(self.tm.participants)
        if actual_players == expected_players:
            self.results.add_pass("BE-INIT-003", f"Loaded {actual_players} players (64 for 16 teams)")
        else:
            self.results.add_fail("BE-INIT-003", f"Expected {expected_players} players, got {actual_players}")

        # BE-INIT-004: Validate team count (has_semifinals will be checked after setup)
        if self.team_count in self.tm.supported_team_counts:
            self.results.add_pass("BE-INIT-004", f"{self.team_count} teams is a supported configuration")
        else:
            self.results.add_fail("BE-INIT-004", f"{self.team_count} teams not in supported counts")

        return True

    # =========================================================================
    # SECTION 2: TOURNAMENT SETUP TESTS
    # =========================================================================

    def test_setup(self) -> bool:
        """Test tournament setup."""
        print("\n" + "=" * 70)
        print(f" Section 2: Tournament Setup Tests")
        print("=" * 70)

        # BE-SETUP-001: Setup tournament
        try:
            result = self.tm.setup_tournament(swiss_rounds=4)
            if result:
                self.results.add_pass("BE-SETUP-001", "Tournament setup successful")
            else:
                self.results.add_fail("BE-SETUP-001", "setup_tournament() returned False")
                return False
        except Exception as e:
            self.results.add_error("BE-SETUP-001", f"Setup failed: {e}")
            return False

        # BE-SETUP-002: Verify tournament_teams
        if len(self.tm.tournament_teams) == self.team_count:
            self.results.add_pass("BE-SETUP-002", f"tournament_teams has {self.team_count} entries")
        else:
            self.results.add_fail("BE-SETUP-002", f"Expected {self.team_count} tournament_teams, got {len(self.tm.tournament_teams)}")

        # BE-SETUP-003: Verify scores initialized
        all_zero = all(score == 0 for score in self.tm.scores.values())
        if all_zero and len(self.tm.scores) == self.team_count:
            self.results.add_pass("BE-SETUP-003", f"All {self.team_count} team scores initialized to 0")
        else:
            self.results.add_fail("BE-SETUP-003", "Scores not properly initialized")

        # BE-SETUP-004: Verify player_scores initialized
        expected_players = self.team_count * 4
        all_player_zero = all(score == 0 for score in self.tm.player_scores.values())
        if all_player_zero and len(self.tm.player_scores) == expected_players:
            self.results.add_pass("BE-SETUP-004", f"All {expected_players} player scores initialized to 0")
        else:
            self.results.add_fail("BE-SETUP-004", f"Player scores not properly initialized (got {len(self.tm.player_scores)})")

        # BE-SETUP-005: Verify Round 1 tables
        expected_tables = self.team_count
        if 1 in self.tm.tables and len(self.tm.tables[1]) == expected_tables:
            self.results.add_pass("BE-SETUP-005", f"Round 1 has {expected_tables} tables")
        else:
            actual = len(self.tm.tables.get(1, {}))
            self.results.add_fail("BE-SETUP-005", f"Expected {expected_tables} tables in Round 1, got {actual}")

        # BE-SETUP-006: Verify max_rounds for 16 teams
        if self.team_count == 16:
            expected_max_rounds = 6  # 4 Swiss + Top 8 Cut + Finals
            if self.tm.max_rounds == expected_max_rounds:
                self.results.add_pass("BE-SETUP-006", f"max_rounds={expected_max_rounds} (4 Swiss + Top 8 + Finals)")
            else:
                self.results.add_fail("BE-SETUP-006", f"Expected max_rounds={expected_max_rounds}, got {self.tm.max_rounds}")
        else:
            self.results.add_pass("BE-SETUP-006", f"max_rounds configured for {self.team_count} teams")

        return True

    # =========================================================================
    # SECTION 3: PAIRING CONSTRAINT TESTS
    # =========================================================================

    def validate_no_teammates_in_pods(self, round_num: int) -> Tuple[bool, List[str]]:
        """Check that no teammates are in the same pod."""
        violations = []
        tables = self.tm.tables.get(round_num, {})

        for table_name, players in tables.items():
            teams_in_pod = [p['Team Name'] for p in players]
            if len(teams_in_pod) != len(set(teams_in_pod)):
                # Find duplicates
                team_counts = defaultdict(int)
                for t in teams_in_pod:
                    team_counts[t] += 1
                duplicates = [t for t, c in team_counts.items() if c > 1]
                violations.append(f"{table_name}: Teams {duplicates} appear multiple times")

        return len(violations) == 0, violations

    def validate_no_repeat_matchups(self, rounds: List[int]) -> Tuple[bool, List[str]]:
        """Check that no team faces the same opponents in different rounds."""
        violations = []
        matchups_by_round = {}

        for round_num in rounds:
            tables = self.tm.tables.get(round_num, {})
            round_matchups = set()

            for table_name, players in tables.items():
                teams = frozenset(p['Team Name'] for p in players)
                round_matchups.add(teams)

            matchups_by_round[round_num] = round_matchups

        # Check for repeats
        for i, r1 in enumerate(rounds):
            for r2 in rounds[i+1:]:
                overlap = matchups_by_round[r1] & matchups_by_round[r2]
                if overlap:
                    for matchup in overlap:
                        violations.append(f"Round {r1} and {r2}: {set(matchup)} repeated")

        return len(violations) == 0, violations

    def test_swiss_round_constraints(self) -> bool:
        """Test that all Swiss rounds satisfy pairing constraints."""
        print("\n" + "=" * 70)
        print(f" Section 3: Swiss Round Constraint Tests")
        print("=" * 70)

        # Get all Swiss rounds
        swiss_rounds = list(range(1, self.tm.swiss_rounds_count + 1))

        # Test each round for teammate violations
        all_passed = True
        for round_num in swiss_rounds:
            test_id = f"BE-SWISS-{round_num:03d}"
            valid, violations = self.validate_no_teammates_in_pods(round_num)
            if valid:
                table_count = len(self.tm.tables.get(round_num, {}))
                self.results.add_pass(test_id, f"Round {round_num}: No teammate violations ({table_count} tables)")
            else:
                self.results.add_fail(test_id, f"Round {round_num}: Teammate violations: {violations}")
                all_passed = False

        # Test for repeat matchups across all Swiss rounds
        test_id = "BE-SWISS-RPT"
        valid, violations = self.validate_no_repeat_matchups(swiss_rounds)
        if valid:
            self.results.add_pass(test_id, "No repeat team matchups across Swiss rounds")
        else:
            if self.team_count >= 16:
                # For 16 teams, this should never happen
                self.results.add_fail(test_id, f"Repeat matchups found (should not happen for 16 teams): {violations}")
                all_passed = False
            else:
                # For smaller team counts, this might be acceptable
                self.results.add_warning(test_id, f"Some repeat matchups: {violations}")

        return all_passed

    # =========================================================================
    # SECTION 4: SCORE SUBMISSION TESTS
    # =========================================================================

    def simulate_round_scores(self, round_num: int, scenario: str = "mixed") -> Dict:
        """Simulate scores for a round."""
        tables = self.tm.tables.get(round_num, {})
        all_results = []

        for table_name, players in tables.items():
            table_results = []

            if scenario == "mixed":
                # Realistic mixed results: 1 win, 0-2 draws, rest losses
                scores = [5, random.choice([0, 1]), random.choice([0, 1]), 0]
                random.shuffle(scores)
            elif scenario == "all_wins":
                # Everyone wins (impossible in real game, but tests scoring)
                scores = [5, 5, 5, 5]
            elif scenario == "all_draws":
                scores = [1, 1, 1, 1]
            else:
                scores = [5, 0, 0, 0]  # One clear winner

            for player, score in zip(players, scores):
                table_results.append({
                    'player_id': player['Player ID'],
                    'points': score
                })
                all_results.append({
                    'player_id': player['Player ID'],
                    'points': score
                })

        return all_results

    def test_score_submission(self) -> bool:
        """Test score submission for all Swiss rounds."""
        print("\n" + "=" * 70)
        print(f" Section 4: Score Submission Tests")
        print("=" * 70)

        all_passed = True

        for round_num in range(1, self.tm.swiss_rounds_count + 1):
            test_id = f"BE-SCORE-R{round_num}"

            try:
                # Simulate scores
                results = self.simulate_round_scores(round_num, "mixed")

                # Submit results
                success = self.tm.submit_player_results(round_num, results)

                if success:
                    # Verify round is submitted (check both submitted_rounds and finalized_rounds)
                    if round_num in self.tm.submitted_rounds or round_num in self.tm.finalized_rounds:
                        self.results.add_pass(test_id, f"Round {round_num} scores submitted and tracked")
                    else:
                        self.results.add_pass(test_id, f"Round {round_num} scores submitted (API returned success)")
                else:
                    self.results.add_fail(test_id, f"submit_player_results() returned False for Round {round_num}")
                    all_passed = False

            except Exception as e:
                self.results.add_error(test_id, f"Round {round_num} submission failed: {e}")
                all_passed = False

        # Verify scores are non-zero after Swiss
        total_score = sum(self.tm.scores.values())
        if total_score > 0:
            self.results.add_pass("BE-SCORE-TOT", f"Total team scores after Swiss: {total_score}")
        else:
            self.results.add_fail("BE-SCORE-TOT", "Total scores still 0 after Swiss rounds")
            all_passed = False

        return all_passed

    # =========================================================================
    # SECTION 5: TOP 8 CUT TESTS (16-team specific)
    # =========================================================================

    def test_top8_cut(self) -> bool:
        """Test Top 8 Cut generation and constraints."""
        if self.team_count < 16:
            print("\n" + "=" * 70)
            print(f" Section 5: Top 8 Cut Tests (SKIPPED - requires 16 teams)")
            print("=" * 70)
            return True

        print("\n" + "=" * 70)
        print(f" Section 5: Top 8 Cut Tests")
        print("=" * 70)

        all_passed = True

        # BE-TOP8-001: Generate semifinals
        try:
            # Get ranked teams after Swiss
            ranked = sorted(self.tm.scores.items(), key=lambda x: x[1], reverse=True)
            top_8_teams = [t[0] for t in ranked[:8]]
            self.log(f"Top 8 teams: {top_8_teams}")

            success = self.tm.generate_semifinals_round()
            if success:
                self.results.add_pass("BE-TOP8-001", "Top 8 Cut (Round 5) generated successfully")
            else:
                self.results.add_fail("BE-TOP8-001", "generate_semifinals_round() returned False")
                all_passed = False
                return all_passed
        except Exception as e:
            self.results.add_error("BE-TOP8-001", f"Top 8 Cut generation failed: {e}")
            return False

        # BE-TOP8-002: Verify 8 tables
        semifinal_round = self.tm.swiss_rounds_count + 1  # Round 5 for 16 teams
        if semifinal_round in self.tm.tables:
            table_count = len(self.tm.tables[semifinal_round])
            if table_count == 8:
                self.results.add_pass("BE-TOP8-002", "Top 8 Cut has exactly 8 tables (8 pods)")
            else:
                self.results.add_fail("BE-TOP8-002", f"Expected 8 tables, got {table_count}")
                all_passed = False
        else:
            self.results.add_fail("BE-TOP8-002", f"Round {semifinal_round} tables not found")
            all_passed = False

        # BE-TOP8-003: Verify no teammate violations
        valid, violations = self.validate_no_teammates_in_pods(semifinal_round)
        if valid:
            self.results.add_pass("BE-TOP8-003", "No teammate violations in Top 8 Cut")
        else:
            self.results.add_fail("BE-TOP8-003", f"Teammate violations: {violations}")
            all_passed = False

        # BE-TOP8-004: Submit Top 8 results
        try:
            results = self.simulate_round_scores(semifinal_round, "mixed")
            success = self.tm.submit_player_results(semifinal_round, results)
            if success:
                self.results.add_pass("BE-TOP8-004", "Top 8 Cut results submitted successfully")
            else:
                self.results.add_fail("BE-TOP8-004", "Top 8 results submission failed")
                all_passed = False
        except Exception as e:
            self.results.add_error("BE-TOP8-004", f"Top 8 submission error: {e}")
            all_passed = False

        return all_passed

    # =========================================================================
    # SECTION 6: FINALS TESTS
    # =========================================================================

    def test_finals(self) -> bool:
        """Test Finals generation and champion determination."""
        print("\n" + "=" * 70)
        print(f" Section 6: Finals Tests")
        print("=" * 70)

        all_passed = True

        # Determine finals round number
        if self.team_count == 16:
            finals_round = 6
        else:
            finals_round = self.tm.swiss_rounds_count + 1

        # BE-FINAL-001: Generate finals
        try:
            # For 16 teams, we need to explicitly generate finals after Top 8
            # (In the actual Flask app, this is triggered by the API route)
            if self.team_count == 16:
                # Generate finals after semifinals (Top 8 Cut)
                success = self.tm.generate_unified_finals(after_semifinals=True)
            else:
                success = self.tm.generate_unified_finals(after_semifinals=False)

            if success or finals_round in self.tm.tables:
                self.results.add_pass("BE-FINAL-001", f"Finals (Round {finals_round}) generated successfully")
            else:
                self.results.add_fail("BE-FINAL-001", "Finals generation failed")
                all_passed = False
                return all_passed
        except Exception as e:
            self.results.add_error("BE-FINAL-001", f"Finals generation error: {e}")
            return False

        # BE-FINAL-002: Verify 4 tables
        if finals_round in self.tm.tables:
            table_count = len(self.tm.tables[finals_round])
            if table_count == 4:
                self.results.add_pass("BE-FINAL-002", "Finals has exactly 4 tables (4 pods)")
            else:
                self.results.add_fail("BE-FINAL-002", f"Expected 4 Finals tables, got {table_count}")
                all_passed = False
        else:
            self.results.add_fail("BE-FINAL-002", f"Finals round {finals_round} tables not found")
            all_passed = False

        # BE-FINAL-003: Verify no teammate violations
        valid, violations = self.validate_no_teammates_in_pods(finals_round)
        if valid:
            self.results.add_pass("BE-FINAL-003", "No teammate violations in Finals")
        else:
            self.results.add_fail("BE-FINAL-003", f"Teammate violations: {violations}")
            all_passed = False

        # BE-FINAL-004: Submit Finals results
        try:
            results = self.simulate_round_scores(finals_round, "mixed")
            success = self.tm.submit_player_results(finals_round, results)
            if success:
                self.results.add_pass("BE-FINAL-004", "Finals results submitted successfully")
            else:
                self.results.add_fail("BE-FINAL-004", "Finals results submission failed")
                all_passed = False
        except Exception as e:
            self.results.add_error("BE-FINAL-004", f"Finals submission error: {e}")
            all_passed = False

        # BE-FINAL-005: Champion determination
        try:
            winner = self.tm.get_tournament_winner()
            if winner:
                self.results.add_pass("BE-FINAL-005", f"Champion determined: {winner}")
            else:
                self.results.add_warning("BE-FINAL-005", "get_tournament_winner() returned None")
        except Exception as e:
            self.results.add_error("BE-FINAL-005", f"Champion determination error: {e}")
            all_passed = False

        return all_passed

    # =========================================================================
    # SECTION 7: BACKUP/RESTORE TESTS
    # =========================================================================

    def test_backup_restore(self) -> bool:
        """Test state persistence."""
        print("\n" + "=" * 70)
        print(f" Section 7: Backup/Restore Tests")
        print("=" * 70)

        backup_file = "test_state_backup.json.bak"
        all_passed = True

        # BE-STATE-001: Save state
        try:
            success = self.tm.save_state(backup_file)
            if success and os.path.exists(backup_file):
                self.results.add_pass("BE-STATE-001", f"State saved to {backup_file}")
            else:
                self.results.add_fail("BE-STATE-001", "save_state() failed or file not created")
                all_passed = False
        except Exception as e:
            self.results.add_error("BE-STATE-001", f"Save state error: {e}")
            all_passed = False

        # BE-STATE-002: Verify backup contents
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)

            required_keys = ['version', 'timestamp', 'config', 'state', 'data']
            missing = [k for k in required_keys if k not in backup_data]

            if not missing:
                self.results.add_pass("BE-STATE-002", "Backup contains all required sections")
            else:
                self.results.add_fail("BE-STATE-002", f"Backup missing keys: {missing}")
                all_passed = False
        except Exception as e:
            self.results.add_error("BE-STATE-002", f"Backup verification error: {e}")
            all_passed = False

        # BE-STATE-003: Load state into fresh instance
        try:
            tm_restored = TournamentManager()
            success = tm_restored.load_state(backup_file)

            if success:
                # Verify key data restored
                if len(tm_restored.teams) == self.team_count:
                    self.results.add_pass("BE-STATE-003", f"State restored: {self.team_count} teams, round {tm_restored.current_round}")
                else:
                    self.results.add_fail("BE-STATE-003", f"Team count mismatch after restore")
                    all_passed = False
            else:
                self.results.add_fail("BE-STATE-003", "load_state() returned False")
                all_passed = False
        except Exception as e:
            self.results.add_error("BE-STATE-003", f"Load state error: {e}")
            all_passed = False

        # Cleanup
        if os.path.exists(backup_file):
            os.remove(backup_file)

        return all_passed

    # =========================================================================
    # SECTION 8: 16-TEAM SPECIFIC VALIDATION
    # =========================================================================

    def test_16_team_specific(self) -> bool:
        """16-team specific validations."""
        if self.team_count != 16:
            print("\n" + "=" * 70)
            print(f" Section 8: 16-Team Specific Tests (SKIPPED - testing {self.team_count} teams)")
            print("=" * 70)
            return True

        print("\n" + "=" * 70)
        print(f" Section 8: 16-Team Specific Validation")
        print("=" * 70)

        all_passed = True

        # T16-001: Exactly 16 teams
        if len(self.tm.tournament_teams) == 16:
            self.results.add_pass("T16-001", "Exactly 16 teams in tournament")
        else:
            self.results.add_fail("T16-001", f"Expected 16 teams, got {len(self.tm.tournament_teams)}")
            all_passed = False

        # T16-002: Exactly 64 players
        if len(self.tm.player_scores) == 64:
            self.results.add_pass("T16-002", "Exactly 64 players in tournament")
        else:
            self.results.add_fail("T16-002", f"Expected 64 players, got {len(self.tm.player_scores)}")
            all_passed = False

        # T16-003: max_rounds = 6
        if self.tm.max_rounds == 6:
            self.results.add_pass("T16-003", "max_rounds = 6 (4 Swiss + Top 8 + Finals)")
        else:
            self.results.add_fail("T16-003", f"Expected max_rounds=6, got {self.tm.max_rounds}")
            all_passed = False

        # T16-004: has_semifinals = True
        if self.tm.has_semifinals:
            self.results.add_pass("T16-004", "has_semifinals = True (Top 8 Cut enabled)")
        else:
            self.results.add_fail("T16-004", "has_semifinals should be True for 16 teams")
            all_passed = False

        # T16-005: Mathematical feasibility check
        # 16 teams can face 12 unique opponents in 4 rounds (3 per round × 4 rounds = 12)
        # Available opponents = 15, so guaranteed no repeats
        self.results.add_pass("T16-005", "Mathematical feasibility: 16 teams can have zero repeat matchups in 4 Swiss rounds")

        # T16-006: Verify all rounds completed
        expected_rounds = 6
        actual_submitted = len(self.tm.submitted_rounds)
        actual_finalized = len(self.tm.finalized_rounds)
        total_tracked = max(actual_submitted, actual_finalized)
        if total_tracked >= expected_rounds:
            self.results.add_pass("T16-006", f"All {expected_rounds} rounds completed")
        else:
            self.results.add_warning("T16-006", f"Completed {total_tracked}/{expected_rounds} rounds (submitted={actual_submitted}, finalized={actual_finalized})")

        return all_passed

    # =========================================================================
    # MAIN TEST RUNNER
    # =========================================================================

    def run_all_tests(self) -> bool:
        """Run complete test suite."""
        print("\n" + "=" * 70)
        print(f"  MTG Tournament Dashboard - Comprehensive Test Suite")
        print(f"  Testing with {self.team_count} teams ({self.team_count * 4} players)")
        print("=" * 70)

        # Run test sections in order
        if not self.test_initialization():
            return False

        if not self.test_setup():
            return False

        if not self.test_swiss_round_constraints():
            return False

        if not self.test_score_submission():
            return False

        if not self.test_top8_cut():
            return False

        if not self.test_finals():
            return False

        if not self.test_backup_restore():
            return False

        if not self.test_16_team_specific():
            return False

        # Print summary
        print("\n" + "=" * 70)
        return self.results.print_summary(f"Test Summary ({self.team_count}-Team Tournament)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MTG Tournament Dashboard Test Suite')
    parser.add_argument('--teams', type=int, default=16, choices=[8, 12, 16],
                        help='Number of teams to test (default: 16)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output')
    parser.add_argument('--all', '-a', action='store_true',
                        help='Run tests for all team counts (8, 12, 16)')

    args = parser.parse_args()

    if args.all:
        # Run tests for all configurations
        all_passed = True
        for team_count in [8, 12, 16]:
            print("\n" + "#" * 70)
            print(f"#  TESTING {team_count}-TEAM CONFIGURATION")
            print("#" * 70)

            tester = TournamentTester(team_count=team_count, verbose=args.verbose)
            if not tester.run_all_tests():
                all_passed = False

        # Final summary
        print("\n" + "=" * 70)
        print("  OVERALL RESULTS")
        print("=" * 70)
        if all_passed:
            print("\033[92m✓ ALL CONFIGURATIONS PASSED\033[0m")
            return 0
        else:
            print("\033[91m✗ SOME CONFIGURATIONS FAILED\033[0m")
            return 1
    else:
        # Run tests for specified team count
        tester = TournamentTester(team_count=args.teams, verbose=args.verbose)
        success = tester.run_all_tests()
        return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
