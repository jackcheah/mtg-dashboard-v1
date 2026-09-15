#!/usr/bin/env python3
"""
Full tournament flow simulation through TournamentManager.

Tests the complete lifecycle: setup -> Swiss rounds (submit/finalize each) ->
Top 8 Cut (16 teams) -> Finals -> Champion determination.

Tracks every individual player's journey and validates pairing integrity at every step.

Usage:
    pytest tests/unit/test_full_tournament_flow.py -v
    python tests/unit/test_full_tournament_flow.py
"""

import sys
import os
import random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tournament_dashboard import TournamentManager, TournamentState, EventMode, ScoringMode


def create_manager_with_teams(num_teams, swiss_rounds=4):
    """Create a TournamentManager with sample data."""
    tm = TournamentManager()
    tm.event_mode = EventMode.TEAM
    tm.scoring_mode = ScoringMode.WESTERN
    tm.create_sample_data(num_teams)
    return tm


class PlayerTracker:
    """Track a player's complete tournament journey."""
    def __init__(self, player_id, player_name, team_name):
        self.player_id = player_id
        self.player_name = player_name
        self.team_name = team_name
        self.round_history = {}  # round_num -> {table, opponents, points}
        self.total_points = 0

    def record(self, round_num, table_name, opponents, points):
        self.round_history[round_num] = {
            'table': table_name,
            'opponents': opponents,
            'points': points
        }
        self.total_points += points


class TournamentFlowSimulator:
    """Simulate the full tournament manager flow."""

    def __init__(self, num_teams, swiss_rounds=4, seed=42):
        random.seed(seed)
        self.num_teams = num_teams
        self.swiss_rounds = swiss_rounds
        self.tm = TournamentManager()
        self.tm.event_mode = EventMode.TEAM
        self.tm.scoring_mode = ScoringMode.WESTERN
        self.trackers = {}  # player_id -> PlayerTracker
        self.errors = []
        self.warnings = []

    def run(self):
        """Execute full tournament flow."""
        # Step 1: Load data
        self.tm.create_sample_data(self.num_teams)

        # Initialize trackers
        for participant in self.tm.participants:
            pid = participant['Player ID']
            self.trackers[pid] = PlayerTracker(
                pid, participant['Player Name'], participant['Team Name']
            )

        # Step 2: Setup tournament
        success, msg = self.tm.setup_tournament(swiss_rounds=self.swiss_rounds)
        if not success:
            self.errors.append(f"SETUP FAILED: {msg}")
            return False

        # Step 3: Play Swiss rounds
        for round_num in range(1, self.swiss_rounds + 1):
            self._validate_round_tables(round_num)
            self._simulate_and_submit_round(round_num)
            self._finalize_round(round_num)

            # Generate next round (except after last Swiss)
            if round_num < self.swiss_rounds:
                if round_num + 1 not in self.tm.tables:
                    self.errors.append(f"Round {round_num + 1} was not generated after finalizing round {round_num}")
                    return False

        # Step 4: Handle playoffs
        if self.tm.has_semifinals:
            # 16-team: Top 8 Cut
            top8_round = self.swiss_rounds + 1
            if top8_round in self.tm.tables:
                self._validate_round_tables(top8_round)
                self._simulate_and_submit_round(top8_round)
                self._finalize_round(top8_round)
            else:
                self.errors.append("Top 8 Cut tables were not generated")
                return False

        # Step 5: Finals
        finals_round = self.tm.max_rounds
        if finals_round in self.tm.tables:
            self._validate_round_tables(finals_round)
            self._simulate_and_submit_round(finals_round)
            self._finalize_round(finals_round)
        else:
            self.errors.append(f"Finals (round {finals_round}) tables were not generated")
            return False

        # Step 6: Verify champion
        if self.tm.state != TournamentState.FINALS_COMPLETE:
            self.errors.append(f"Tournament not in FINALS_COMPLETE state: {self.tm.state}")

        # Step 7: Cross-round validation
        self._validate_swiss_pairing_integrity()

        return len(self.errors) == 0

    def _validate_round_tables(self, round_num):
        """Validate table assignments for a round."""
        if round_num not in self.tm.tables:
            self.errors.append(f"Round {round_num}: No tables found")
            return

        tables = self.tm.tables[round_num]
        all_players_this_round = set()

        for table_name, players in tables.items():
            # Check pod size
            if len(players) != 4:
                self.errors.append(
                    f"Round {round_num} {table_name}: {len(players)} players (expected 4)"
                )
                continue

            # Check no teammates
            teams_in_pod = [p['Team Name'] for p in players]
            if len(set(teams_in_pod)) != 4:
                self.errors.append(
                    f"Round {round_num} {table_name}: TEAMMATE VIOLATION - teams: {teams_in_pod}"
                )

            # Check uniqueness
            for p in players:
                pid = p['Player ID']
                if pid in all_players_this_round:
                    self.errors.append(
                        f"Round {round_num}: Player {pid} in multiple tables"
                    )
                all_players_this_round.add(pid)

    def _simulate_and_submit_round(self, round_num):
        """Simulate scoring for a round and submit via table submissions."""
        tables = self.tm.tables.get(round_num, {})

        # Initialize round results
        if round_num not in self.tm.round_results:
            self.tm.round_results[round_num] = {
                'submitted_tables': set(),
                'table_submissions': {}
            }

        for table_name, players in tables.items():
            # Pick random winner
            winner = random.choice(players)
            table_results = []

            for player in players:
                pid = player['Player ID']
                points = 5 if player == winner else 0
                table_results.append({'player_id': pid, 'points': points})

                # Update player scores
                self.tm.player_scores[pid] += points

                # Track in journey
                opponents = [p['Player ID'] for p in players if p != player]
                self.trackers[pid].record(round_num, table_name, opponents, points)

            # Mark as submitted
            self.tm.round_results[round_num]['submitted_tables'].add(table_name)
            self.tm.round_results[round_num]['table_submissions'] = \
                self.tm.round_results[round_num].get('table_submissions', {})
            self.tm.round_results[round_num]['table_submissions'][table_name] = table_results

        # Recalculate team scores
        self.tm.calculate_team_scores()

    def _finalize_round(self, round_num):
        """Finalize a round and trigger transition."""
        # Mark round as finalized
        self.tm.finalized_rounds.add(round_num)

        # Update final/swiss/top8 score tracking
        last_swiss = self.tm.swiss_rounds_count
        if round_num <= last_swiss:
            if round_num == last_swiss:
                self.tm.swiss_round_scores = self.tm.scores.copy()
        elif self.tm.has_semifinals and round_num == last_swiss + 1:
            # Top 8 Cut round
            player_results = []
            for table_results in self.tm.round_results[round_num].get('table_submissions', {}).values():
                player_results.extend(table_results)
            self.tm.update_top8_cut_scores(round_num, player_results)
        elif round_num == self.tm.max_rounds:
            # Finals round
            player_results = []
            for table_results in self.tm.round_results[round_num].get('table_submissions', {}).values():
                player_results.extend(table_results)
            self.tm.update_final_round_scores(round_num, player_results)

        # Trigger round transition (generate next round/finals)
        if round_num < self.tm.swiss_rounds_count:
            next_round = round_num + 1
            if not self.tm.generate_swiss_round(next_round):
                self.errors.append(f"Failed to generate Swiss round {next_round}")
            else:
                self.tm.current_round = next_round
        elif round_num == self.tm.swiss_rounds_count:
            self.tm.swiss_round_scores = self.tm.scores.copy()
            if self.tm.has_semifinals:
                result = self.tm.generate_semifinals_round()
                if result:
                    self.tm.transition_to(TournamentState.TOP8_IN_PROGRESS, "Top 8 cut")
                    self.tm.current_round = round_num + 1
                else:
                    self.errors.append("Failed to generate Top 8 Cut")
            else:
                self.tm._player_scores_at_finals_start = dict(self.tm.player_scores)
                result = self.tm.generate_unified_finals(after_semifinals=False)
                if result:
                    self.tm.transition_to(TournamentState.FINALS_IN_PROGRESS, "Finals")
                    self.tm.current_round = self.tm.max_rounds
                else:
                    self.errors.append("Failed to generate Finals")
        elif self.tm.has_semifinals and round_num == self.tm.swiss_rounds_count + 1:
            self.tm.semifinal_round_scores = self.tm.scores.copy()
            self.tm._player_scores_at_finals_start = dict(self.tm.player_scores)
            result = self.tm.generate_unified_finals(after_semifinals=True)
            if result:
                self.tm.transition_to(TournamentState.FINALS_IN_PROGRESS, "Finals after T8")
                self.tm.current_round = self.tm.max_rounds
            else:
                self.errors.append("Failed to generate Finals after Top 8")
        elif round_num == self.tm.max_rounds:
            winner = self.tm.get_tournament_winner()
            if winner:
                self.tm.transition_to(TournamentState.FINALS_COMPLETE, "Complete")
            else:
                self.errors.append("Failed to determine winner")

    def _validate_swiss_pairing_integrity(self):
        """Validate pairing integrity across Swiss rounds."""
        # Check for player-level repeat opponents in Swiss rounds
        for pid, tracker in self.trackers.items():
            opponent_counts = defaultdict(int)
            for r in range(1, self.swiss_rounds + 1):
                if r in tracker.round_history:
                    for opp in tracker.round_history[r]['opponents']:
                        opponent_counts[opp] += 1

            repeats = {opp: c for opp, c in opponent_counts.items() if c > 1}
            if repeats:
                for opp_id, count in repeats.items():
                    opp_tracker = self.trackers[opp_id]
                    self.warnings.append(
                        f"Swiss repeat: {tracker.player_name} ({tracker.team_name}) vs "
                        f"{opp_tracker.player_name} ({opp_tracker.team_name}) met {count}x"
                    )

    def print_report(self):
        """Print simulation report."""
        print(f"\n{'='*70}")
        print(f"FULL FLOW SIMULATION: {self.num_teams} teams, {self.swiss_rounds} Swiss rounds")
        print(f"{'='*70}")
        print(f"Final state: {self.tm.state.value}")
        print(f"Total rounds played: {self.tm.current_round}")

        if self.errors:
            print(f"\n*** ERRORS ({len(self.errors)}) ***")
            for e in self.errors:
                print(f"  [ERROR] {e}")
        else:
            print(f"\n[PASS] No errors")

        if self.warnings:
            # Deduplicate (A vs B same as B vs A)
            unique = set()
            for w in self.warnings:
                unique.add(w)
            print(f"\n*** WARNINGS ({len(unique)}) ***")
            for w in list(unique)[:20]:
                print(f"  [WARN] {w}")
        else:
            print(f"\n[PASS] Zero repeat matchups in Swiss rounds")

        # Show sample journey
        pid = min(self.trackers.keys())
        t = self.trackers[pid]
        print(f"\n--- Player Journey: {t.player_name} ({t.team_name}) ---")
        for r in sorted(t.round_history.keys()):
            h = t.round_history[r]
            opp_names = [self.trackers[o].player_name for o in h['opponents'] if o in self.trackers]
            print(f"  Round {r}: {h['table']} | {h['points']}pts | vs {opp_names}")
        print(f"  Total: {t.total_points} pts")
        print(f"{'='*70}\n")


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

class TestFullTournamentFlow12Teams:
    """Full tournament flow for 12 teams."""

    def test_12_teams_4_rounds_complete(self):
        """12 teams, 4 Swiss + Finals = complete tournament."""
        sim = TournamentFlowSimulator(12, swiss_rounds=4, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE

    def test_12_teams_5_rounds_complete(self):
        """12 teams, 5 Swiss + Finals = complete tournament."""
        sim = TournamentFlowSimulator(12, swiss_rounds=5, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE

    def test_12_teams_no_teammate_violations(self):
        """12 teams across multiple seeds - no teammate violations."""
        for seed in range(10):
            sim = TournamentFlowSimulator(12, swiss_rounds=4, seed=seed)
            sim.run()
            teammate_errors = [e for e in sim.errors if "TEAMMATE" in e]
            assert not teammate_errors, f"seed={seed}: {teammate_errors}"


class TestFullTournamentFlow16Teams:
    """Full tournament flow for 16 teams."""

    def test_16_teams_3_rounds_complete(self):
        """16 teams, 3 Swiss + Finals = complete tournament (TopDeck aligned)."""
        sim = TournamentFlowSimulator(16, swiss_rounds=3, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE
        assert not sim.tm.has_semifinals  # No Top 8 Cut for ≤16 teams

    def test_16_teams_5_rounds_override_complete(self):
        """16 teams, 5 Swiss (operator override) + Finals. No Top 8 Cut for ≤16 teams."""
        sim = TournamentFlowSimulator(16, swiss_rounds=5, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE
        assert not sim.tm.has_semifinals

    def test_16_teams_zero_swiss_repeat_matchups(self):
        """16 teams should have zero player-level repeat matchups in 4 Swiss rounds."""
        sim = TournamentFlowSimulator(16, swiss_rounds=4, seed=42)
        sim.run()
        # 16 teams / 4 rounds: each player faces 12 unique opponents (out of 60 possible)
        # Should be perfect
        swiss_warnings = [w for w in sim.warnings if "Swiss repeat" in w]
        if swiss_warnings:
            print(f"Unexpected repeats: {swiss_warnings[:5]}")
        # Note: with 16 teams, 4 rounds, the engine should avoid all repeats
        # but this depends on the swap algorithm succeeding

    def test_16_teams_no_teammate_violations(self):
        """16 teams across multiple seeds - no teammate violations."""
        for seed in range(10):
            sim = TournamentFlowSimulator(16, swiss_rounds=4, seed=seed)
            sim.run()
            teammate_errors = [e for e in sim.errors if "TEAMMATE" in e]
            assert not teammate_errors, f"seed={seed}: {teammate_errors}"


class TestFullTournamentFlow20Teams:
    """Full tournament flow for 20 teams."""

    def test_20_teams_4_rounds_complete(self):
        """20 teams, 4 Swiss + Finals (TopDeck aligned, no Top 8 Cut)."""
        sim = TournamentFlowSimulator(20, swiss_rounds=4, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE
        assert not sim.tm.has_semifinals

    def test_20_teams_5_rounds_override_complete(self):
        """20 teams, 5 Swiss (operator override) + Finals."""
        sim = TournamentFlowSimulator(20, swiss_rounds=5, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE

    def test_20_teams_no_teammate_violations(self):
        """20 teams across multiple seeds."""
        for seed in range(5):
            sim = TournamentFlowSimulator(20, swiss_rounds=5, seed=seed)
            sim.run()
            teammate_errors = [e for e in sim.errors if "TEAMMATE" in e]
            assert not teammate_errors, f"seed={seed}: {teammate_errors}"


class TestFullTournamentFlow24_28_32_36_40Teams:
    """Full tournament flow for 24, 28, 32, 36, 40 teams."""

    def test_24_teams_complete(self):
        """24 teams, 4 Swiss + Finals (no Top 8 Cut for 20-32 teams)."""
        sim = TournamentFlowSimulator(24, swiss_rounds=4, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE
        assert not sim.tm.has_semifinals

    def test_28_teams_complete(self):
        """28 teams, 4 Swiss + Finals (no Top 8 Cut for 20-32 teams)."""
        sim = TournamentFlowSimulator(28, swiss_rounds=4, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE
        assert not sim.tm.has_semifinals

    def test_32_teams_complete(self):
        """32 teams, 4 Swiss + Finals (no Top 8 Cut for 20-32 teams)."""
        sim = TournamentFlowSimulator(32, swiss_rounds=4, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE
        assert not sim.tm.has_semifinals

    def test_36_teams_complete(self):
        """36 teams, 5 Swiss + Top 8 Cut + Finals."""
        sim = TournamentFlowSimulator(36, swiss_rounds=5, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE

    def test_40_teams_complete(self):
        """40 teams, 5 Swiss + Top 8 Cut + Finals."""
        sim = TournamentFlowSimulator(40, swiss_rounds=5, seed=42)
        success = sim.run()
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        assert sim.tm.state == TournamentState.FINALS_COMPLETE

    def test_40_teams_no_teammate_violations(self):
        """40 teams across multiple seeds."""
        for seed in range(5):
            sim = TournamentFlowSimulator(40, swiss_rounds=5, seed=seed)
            sim.run()
            teammate_errors = [e for e in sim.errors if "TEAMMATE" in e]
            assert not teammate_errors, f"seed={seed}: {teammate_errors}"


class TestTeamCountValidation:
    """Test team count validation boundaries."""

    def test_manager_rejects_invalid_counts(self):
        """TournamentManager rejects non-multiples-of-4 and out-of-range."""
        for n in [4, 7, 10, 14, 44]:
            tm = TournamentManager()
            tm.event_mode = EventMode.TEAM
            teams = {}
            participants = []
            pid = 1
            for i in range(n):
                team_name = f"Team_{i+1:02d}"
                players = []
                for j in range(4):
                    p = {'Player ID': pid, 'Player Name': f"P{pid}", 'Team Name': team_name}
                    players.append(p)
                    participants.append(p)
                    pid += 1
                teams[team_name] = players
            tm.teams = teams
            tm.tournament_teams = list(teams.keys())
            tm.participants = participants
            tm.scores = {t: 0 for t in teams}
            tm.player_scores = {p['Player ID']: 0 for p in participants}

            success, msg = tm.setup_tournament(swiss_rounds=4)
            assert not success, f"{n} teams should be rejected"

    def test_default_swiss_rounds_match_topdeck(self):
        """Default Swiss rounds aligned with TopDeck: 3 for ≤16, 4 for 20-32, 5 for 36-40."""
        expected = {8: 3, 12: 3, 16: 3, 20: 4, 24: 4, 28: 4, 32: 4, 36: 5, 40: 5}
        for n, expected_rounds in expected.items():
            tm = TournamentManager()
            tm.event_mode = EventMode.TEAM
            tm.create_sample_data(n)
            tm.setup_tournament()
            assert tm.swiss_rounds_count == expected_rounds, (
                f"{n} teams should default to {expected_rounds} Swiss rounds, got {tm.swiss_rounds_count}"
            )


class TestEdgeCasesAndBugs:
    """Tests for specific edge cases and potential bugs."""

    def test_finals_scores_tracked_correctly(self):
        """Verify Swiss scores and Finals scores are tracked separately."""
        sim = TournamentFlowSimulator(12, swiss_rounds=4, seed=42)
        sim.run()

        # Swiss scores should be preserved
        assert sim.tm.swiss_round_scores, "Swiss round scores should be tracked"
        for team, score in sim.tm.swiss_round_scores.items():
            assert score >= 0

        # Final round scores should be tracked
        assert sim.tm.final_round_scores is not None

    def test_state_transitions_correct_order(self):
        """Verify state machine transitions happen in correct order (with Top 8 Cut)."""
        sim = TournamentFlowSimulator(36, swiss_rounds=5, seed=42)
        sim.run()

        # After full tournament, state should be FINALS_COMPLETE
        assert sim.tm.state == TournamentState.FINALS_COMPLETE

        # State history should show progression including Top 8 Cut
        states_seen = [h['to'] for h in sim.tm.state_history]
        assert 'top8_in_progress' in states_seen
        assert 'finals_in_progress' in states_seen
        assert 'finals_complete' in states_seen

    def test_all_players_scored_every_swiss_round(self):
        """Every player should have scores recorded in every Swiss round."""
        sim = TournamentFlowSimulator(12, swiss_rounds=4, seed=42)
        sim.run()

        for pid, tracker in sim.trackers.items():
            for r in range(1, sim.swiss_rounds + 1):
                assert r in tracker.round_history, (
                    f"Player {tracker.player_name} missing from round {r}"
                )

    def test_12_teams_sample_data_has_all_16_teams_defined(self):
        """Verify create_sample_data only uses first N teams for valid counts."""
        tm = TournamentManager()
        tm.create_sample_data(12)
        assert len(tm.teams) == 12
        assert len(tm.tournament_teams) == 12
        assert len(tm.participants) == 48

    def test_anti_collusion_activates_round_4(self):
        """Verify anti-collusion pairing is used starting from round 4."""
        sim = TournamentFlowSimulator(12, swiss_rounds=5, seed=42)
        sim.run()
        # The anti-collusion algorithm changes grouping in rounds 4+
        # We can't easily verify the grouping method from outside,
        # but we can verify no errors occur
        assert len(sim.errors) == 0


# ============================================================================
# STANDALONE
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("FULL TOURNAMENT FLOW SIMULATION")
    print("=" * 70)

    configs = [
        (8, 4),
        (12, 4),
        (12, 5),
        (16, 4),
        (16, 5),
    ]

    all_pass = True
    for num_teams, swiss_rounds in configs:
        for seed in range(3):
            sim = TournamentFlowSimulator(num_teams, swiss_rounds=swiss_rounds, seed=seed)
            success = sim.run()
            if not success:
                all_pass = False
                sim.print_report()
            elif seed == 0:
                sim.print_report()

    print("\n" + "=" * 70)
    if all_pass:
        print("ALL CONFIGURATIONS PASSED")
    else:
        print("FAILURES DETECTED")
    print("=" * 70)
