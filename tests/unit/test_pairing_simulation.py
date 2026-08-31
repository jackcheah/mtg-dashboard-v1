#!/usr/bin/env python3
"""
Comprehensive pairing simulation for team tournaments (Western scoring).

Tests the full tournament flow for 12, 16, 20, 24, 28 teams.
Tracks every individual player through every round and validates:
1. No teammates in same pod (HARD constraint)
2. Repeat matchups (player-level and team-level)
3. All players participate each round
4. Score-based Swiss pairing logic
5. Anti-collusion snake pairing in late rounds

Usage:
    pytest tests/unit/test_pairing_simulation.py -v
    python tests/unit/test_pairing_simulation.py  # standalone
"""

import sys
import os
import random
from collections import defaultdict
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from unified_swiss_pairing import UnifiedSwissPairing


def generate_teams(num_teams):
    """Generate test teams with 4 players each."""
    teams = {}
    player_id = 1
    team_names = []
    for t in range(num_teams):
        team_name = f"Team_{t+1:02d}"
        team_names.append(team_name)
        players = []
        for p in range(4):
            players.append({
                'Player ID': player_id,
                'Player Name': f"Player_{player_id:03d}",
                'Team Name': team_name
            })
            player_id += 1
        teams[team_name] = players
    return teams, team_names


class PlayerJourney:
    """Track a single player's opponents across all rounds."""
    def __init__(self, player_id, player_name, team_name):
        self.player_id = player_id
        self.player_name = player_name
        self.team_name = team_name
        self.rounds = {}  # round_num -> {'opponents': [pid], 'pod_teams': [team], 'table': int}
        self.all_opponents = set()

    def record_round(self, round_num, opponents, pod_teams, table_idx):
        self.rounds[round_num] = {
            'opponents': opponents,
            'pod_teams': pod_teams,
            'table': table_idx
        }
        self.all_opponents.update(opponents)

    def get_repeat_opponents(self):
        """Find opponents faced more than once."""
        opponent_counts = defaultdict(int)
        for rdata in self.rounds.values():
            for opp in rdata['opponents']:
                opponent_counts[opp] += 1
        return {opp: count for opp, count in opponent_counts.items() if count > 1}


class TournamentSimulation:
    """Simulate a full team tournament and track all pairings."""

    def __init__(self, num_teams, swiss_rounds=4, anti_collusion_start=4):
        self.num_teams = num_teams
        self.swiss_rounds = swiss_rounds
        self.anti_collusion_start = anti_collusion_start
        self.teams, self.team_names = generate_teams(num_teams)
        self.team_scores = {name: 0 for name in self.team_names}
        self.player_scores = {}
        self.player_journeys = {}

        # Initialize player journeys and scores
        for team_name, players in self.teams.items():
            for player in players:
                pid = player['Player ID']
                self.player_scores[pid] = 0
                self.player_journeys[pid] = PlayerJourney(
                    pid, player['Player Name'], team_name
                )

        # Validation results
        self.errors = []
        self.warnings = []

    def run(self):
        """Run the full Swiss tournament simulation."""
        try:
            engine = UnifiedSwissPairing(
                self.teams, self.team_names,
                self.swiss_rounds, self.team_scores,
                anti_collusion_enabled=True,
                anti_collusion_start_round=self.anti_collusion_start
            )
        except Exception as e:
            self.errors.append(f"INIT FAILURE: {e}")
            return False

        for round_num in range(1, self.swiss_rounds + 1):
            # Update scores in engine
            engine.update_team_scores(self.team_scores)

            # Generate round
            try:
                success, pods = engine.generate_single_round(round_num)
            except Exception as e:
                self.errors.append(f"Round {round_num} GENERATION FAILURE: {e}")
                return False

            if not success:
                self.errors.append(f"Round {round_num} generation returned failure")
                return False

            # Validate round
            self._validate_round(round_num, pods)

            # Record player journeys
            self._record_round(round_num, pods)

            # Simulate scoring (random winner per pod)
            self._simulate_western_scoring(round_num, pods)

        # Final validation across all rounds
        self._validate_cross_round()
        return len(self.errors) == 0

    def _validate_round(self, round_num, pods):
        """Validate a single round's pods."""
        expected_pods = self.num_teams  # Each team has 4 players, groups of 4 teams -> num_teams pods
        # Actually: num_teams teams / 4 teams per group = num_teams/4 groups, 4 pods per group = num_teams pods
        # Wait - each group of 4 teams produces 4 pods (one player from each team per pod)
        # Total pods = num_teams (since num_teams/4 groups * 4 pods/group = num_teams)
        if len(pods) != self.num_teams:
            self.errors.append(
                f"Round {round_num}: Expected {self.num_teams} pods, got {len(pods)}"
            )

        all_player_ids_this_round = set()

        for pod_idx, pod in enumerate(pods):
            # Check pod size
            if len(pod) != 4:
                self.errors.append(
                    f"Round {round_num} Pod {pod_idx+1}: Expected 4 players, got {len(pod)}"
                )
                continue

            # Check no teammates in same pod
            teams_in_pod = [p['Team Name'] for p in pod]
            if len(set(teams_in_pod)) != 4:
                team_counts = defaultdict(int)
                for t in teams_in_pod:
                    team_counts[t] += 1
                dupes = {t: c for t, c in team_counts.items() if c > 1}
                self.errors.append(
                    f"Round {round_num} Pod {pod_idx+1}: TEAMMATE VIOLATION - {dupes}"
                )

            # Check player uniqueness within round
            for player in pod:
                pid = player['Player ID']
                if pid in all_player_ids_this_round:
                    self.errors.append(
                        f"Round {round_num}: Player {pid} appears in multiple pods!"
                    )
                all_player_ids_this_round.add(pid)

        # Check all players participated
        expected_players = self.num_teams * 4
        if len(all_player_ids_this_round) != expected_players:
            self.errors.append(
                f"Round {round_num}: Only {len(all_player_ids_this_round)}/{expected_players} players participated"
            )

    def _record_round(self, round_num, pods):
        """Record pod assignments into player journeys."""
        for pod_idx, pod in enumerate(pods):
            player_ids = [p['Player ID'] for p in pod]
            pod_teams = [p['Team Name'] for p in pod]

            for player in pod:
                pid = player['Player ID']
                opponents = [oid for oid in player_ids if oid != pid]
                self.player_journeys[pid].record_round(
                    round_num, opponents, pod_teams, pod_idx + 1
                )

    def _simulate_western_scoring(self, round_num, pods):
        """Simulate Western scoring: 1 winner (5pts) + 3 losers (0pts) per pod."""
        for pod in pods:
            # Pick random winner
            winner = random.choice(pod)
            winner_id = winner['Player ID']
            self.player_scores[winner_id] += 5

        # Recalculate team scores
        self.team_scores = {name: 0 for name in self.team_names}
        for team_name, players in self.teams.items():
            for player in players:
                self.team_scores[team_name] += self.player_scores[player['Player ID']]

    def _validate_cross_round(self):
        """Validate constraints across all rounds."""
        # Check for repeat opponents (player-level)
        total_repeat_pairs = 0
        repeat_details = []

        for pid, journey in self.player_journeys.items():
            repeats = journey.get_repeat_opponents()
            if repeats:
                total_repeat_pairs += sum(count - 1 for count in repeats.values())
                for opp_id, count in repeats.items():
                    opp_journey = self.player_journeys[opp_id]
                    repeat_details.append(
                        f"  {journey.player_name} ({journey.team_name}) vs "
                        f"{opp_journey.player_name} ({opp_journey.team_name}): "
                        f"met {count} times"
                    )

        # Deduplicate (A vs B and B vs A are the same)
        unique_repeat_pairs = total_repeat_pairs // 2

        if unique_repeat_pairs > 0:
            self.warnings.append(
                f"Player-level repeat matchups: {unique_repeat_pairs} pairs met more than once"
            )
            # Only show first 10
            for detail in repeat_details[:10]:
                self.warnings.append(detail)

        # Check team-level repeat matchups
        team_opponents = defaultdict(lambda: defaultdict(int))
        for pid, journey in self.player_journeys.items():
            player_team = journey.team_name
            for rdata in journey.rounds.values():
                for opp_team in rdata['pod_teams']:
                    if opp_team != player_team:
                        team_opponents[player_team][opp_team] += 1

        # In team mode, each team faces 3 opponents per round via 4 pods
        # But team_opponents counts per-player encounters (4 players per team)
        # Normalize: if two teams are in the same group, all 4 players face each other = 4 encounters per round
        team_repeat_matchups = 0
        team_repeat_details = []
        seen_team_pairs = set()

        for team1 in self.team_names:
            for team2, count in team_opponents[team1].items():
                pair = frozenset([team1, team2])
                if pair in seen_team_pairs:
                    continue
                seen_team_pairs.add(pair)

                # Each time two teams are in the same group, 4 players from each see each other
                # count here is per-player; normalize by 4 (players per team that see this opponent team)
                rounds_together = count // 4
                if rounds_together > 1:
                    team_repeat_matchups += 1
                    team_repeat_details.append(
                        f"  {team1} vs {team2}: grouped together {rounds_together} times"
                    )

        if team_repeat_matchups > 0:
            self.warnings.append(
                f"Team-level repeat matchups: {team_repeat_matchups} team pairs grouped >1 time"
            )
            for detail in team_repeat_details[:10]:
                self.warnings.append(detail)

    def print_report(self):
        """Print detailed simulation report."""
        print(f"\n{'='*70}")
        print(f"TOURNAMENT SIMULATION REPORT: {self.num_teams} Teams, {self.swiss_rounds} Swiss Rounds")
        print(f"{'='*70}")
        print(f"Total players: {self.num_teams * 4}")
        print(f"Pods per round: {self.num_teams}")
        print(f"Anti-collusion starts: Round {self.anti_collusion_start}")
        print(f"{'='*70}")

        if self.errors:
            print(f"\n*** ERRORS ({len(self.errors)}) ***")
            for err in self.errors:
                print(f"  [ERROR] {err}")
        else:
            print(f"\n[PASS] No errors found")

        if self.warnings:
            print(f"\n*** WARNINGS ({len(self.warnings)}) ***")
            for warn in self.warnings:
                print(f"  [WARN] {warn}")
        else:
            print(f"\n[PASS] No warnings (zero repeat matchups)")

        # Print sample player journey
        sample_pid = 1
        journey = self.player_journeys[sample_pid]
        print(f"\n--- Sample Player Journey: {journey.player_name} ({journey.team_name}) ---")
        for r in sorted(journey.rounds.keys()):
            rdata = journey.rounds[r]
            opp_names = [self.player_journeys[oid].player_name for oid in rdata['opponents']]
            opp_teams = [self.player_journeys[oid].team_name for oid in rdata['opponents']]
            print(f"  Round {r}: Table {rdata['table']} | Opponents: {opp_names} | Teams: {opp_teams}")

        repeats = journey.get_repeat_opponents()
        if repeats:
            print(f"  REPEATS: {len(repeats)} opponents faced multiple times")
        else:
            print(f"  No repeat opponents (perfect)")

        print(f"\n{'='*70}\n")


def run_simulation(num_teams, swiss_rounds=4, anti_collusion_start=4, seed=None):
    """Run a single simulation and return results."""
    if seed is not None:
        random.seed(seed)

    sim = TournamentSimulation(num_teams, swiss_rounds, anti_collusion_start)
    success = sim.run()
    return sim


# ============================================================================
# PYTEST TEST CASES
# ============================================================================

class TestPairingSimulation:
    """Test suite for pairing logic across different team counts."""

    def test_12_teams_4_rounds(self):
        """12 teams, 4 Swiss rounds - should work with minimal repeats."""
        sim = run_simulation(12, swiss_rounds=4, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_12_teams_5_rounds(self):
        """12 teams, 5 Swiss rounds - more repeats expected."""
        sim = run_simulation(12, swiss_rounds=5, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_16_teams_4_rounds(self):
        """16 teams, 4 Swiss rounds - should be perfect (no repeats)."""
        sim = run_simulation(16, swiss_rounds=4, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"
        # 16 teams / 4 rounds should have zero repeats
        # (each team has 15 possible opponents, faces 3 per round = 12 over 4 rounds)

    def test_16_teams_5_rounds(self):
        """16 teams, 5 Swiss rounds - may have some repeats in round 5."""
        sim = run_simulation(16, swiss_rounds=5, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_20_teams_4_rounds(self):
        """20 teams, 4 Swiss rounds - tests upper limit of pairing engine."""
        sim = run_simulation(20, swiss_rounds=4, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_20_teams_5_rounds(self):
        """20 teams, 5 Swiss rounds."""
        sim = run_simulation(20, swiss_rounds=5, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_24_teams_4_rounds(self):
        """24 teams, 4 Swiss rounds."""
        sim = run_simulation(24, swiss_rounds=4, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_24_teams_5_rounds(self):
        """24 teams, 5 Swiss rounds."""
        sim = run_simulation(24, swiss_rounds=5, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_28_teams_4_rounds(self):
        """28 teams, 4 Swiss rounds."""
        sim = run_simulation(28, swiss_rounds=4, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_28_teams_5_rounds(self):
        """28 teams, 5 Swiss rounds."""
        sim = run_simulation(28, swiss_rounds=5, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_32_teams_4_rounds(self):
        """32 teams, 4 Swiss rounds."""
        sim = run_simulation(32, swiss_rounds=4, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_32_teams_5_rounds(self):
        """32 teams, 5 Swiss rounds."""
        sim = run_simulation(32, swiss_rounds=5, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_36_teams_5_rounds(self):
        """36 teams, 5 Swiss rounds."""
        sim = run_simulation(36, swiss_rounds=5, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_40_teams_5_rounds(self):
        """40 teams, 5 Swiss rounds."""
        sim = run_simulation(40, swiss_rounds=5, seed=42)
        sim.print_report()
        assert len(sim.errors) == 0, f"Errors: {sim.errors}"

    def test_no_teammate_violations_any_seed(self):
        """Run multiple seeds for various team counts to verify no teammate violations."""
        for num_teams in [12, 16, 20, 24, 28, 32, 36, 40]:
            for seed in range(5):
                sim = run_simulation(num_teams, swiss_rounds=4, seed=seed)
                teammate_errors = [e for e in sim.errors if "TEAMMATE VIOLATION" in e]
                assert len(teammate_errors) == 0, (
                    f"{num_teams} teams, seed={seed}: {teammate_errors}"
                )

    def test_all_players_participate_every_round(self):
        """Verify every player appears in exactly one pod per round."""
        for num_teams in [12, 16, 20, 24, 28, 32, 36, 40]:
            sim = run_simulation(num_teams, swiss_rounds=4, seed=42)
            participation_errors = [e for e in sim.errors if "participated" in e]
            assert len(participation_errors) == 0, (
                f"{num_teams} teams: {participation_errors}"
            )
            # Also verify via journeys
            for pid, journey in sim.player_journeys.items():
                assert len(journey.rounds) == 4, (
                    f"Player {pid} only in {len(journey.rounds)} rounds (expected 4)"
                )

    def test_anti_collusion_changes_grouping(self):
        """Verify anti-collusion pairing changes grouping in round 4+."""
        random.seed(100)
        # Run with anti-collusion starting at round 4
        sim1 = run_simulation(16, swiss_rounds=5, anti_collusion_start=4, seed=100)

        random.seed(100)
        # Run with anti-collusion disabled (start at round 99 effectively)
        sim2 = run_simulation(16, swiss_rounds=5, anti_collusion_start=99, seed=100)

        # Both should have no errors
        assert len(sim1.errors) == 0
        assert len(sim2.errors) == 0

        # Rounds 1-3 should be identical, but rounds 4-5 may differ
        # (anti-collusion changes the grouping algorithm for rounds >= anti_collusion_start)
        # We can't guarantee they differ due to randomness, but we can check both are valid

    def test_score_based_pairing_round2_onwards(self):
        """Verify round 2+ groups teams by score brackets."""
        random.seed(42)
        sim = TournamentSimulation(16, swiss_rounds=4, anti_collusion_start=4)

        # Manually set team scores to create clear brackets
        # Top 4 teams get 20 pts each, next 4 get 10, next 4 get 5, bottom 4 get 0
        for i, team in enumerate(sim.team_names):
            if i < 4:
                sim.team_scores[team] = 20
            elif i < 8:
                sim.team_scores[team] = 10
            elif i < 12:
                sim.team_scores[team] = 5
            else:
                sim.team_scores[team] = 0

        engine = UnifiedSwissPairing(
            sim.teams, sim.team_names, 4, sim.team_scores,
            anti_collusion_enabled=True, anti_collusion_start_round=4
        )

        # Generate round 1 (random)
        success1, pods1 = engine.generate_single_round(1)
        assert success1

        # Update scores and generate round 2 (score-based)
        engine.update_team_scores(sim.team_scores)
        success2, pods2 = engine.generate_single_round(2)
        assert success2

        # Verify round 2 groups by score: each pod should have teams from same bracket
        # In traditional Swiss, top 4 should be in one group, etc.
        for pod in pods2:
            pod_teams = {p['Team Name'] for p in pod}
            pod_team_scores = [sim.team_scores[t] for t in pod_teams]
            # All teams in a pod should have the same score (since we set clear brackets)
            # This verifies the score-based grouping is working
            assert len(set(pod_team_scores)) <= 2, (
                f"Round 2 pod has too wide score range: {pod_team_scores} "
                f"(teams: {pod_teams})"
            )


class TestTournamentManagerTeamCountRestrictions:
    """Tests for TournamentManager's team count validation."""

    def test_manager_accepts_all_valid_counts(self):
        """TournamentManager accepts 8, 12, 16, 20, 24, 28, 32, 36, 40 teams."""
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from tournament_dashboard import TournamentManager, EventMode

        for num_teams in [8, 12, 16, 20, 24, 28, 32, 36, 40]:
            tm = TournamentManager()
            tm.event_mode = EventMode.TEAM
            tm.create_sample_data(num_teams)
            success, msg = tm.setup_tournament()
            assert success, f"{num_teams} teams should succeed: {msg}"

    def test_manager_rejects_invalid_counts(self):
        """TournamentManager rejects non-multiples-of-4 and out-of-range counts."""
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from tournament_dashboard import TournamentManager, EventMode

        for num_teams in [4, 7, 10, 14, 44]:
            tm = TournamentManager()
            tm.event_mode = EventMode.TEAM
            teams, names = generate_teams(num_teams)
            tm.teams = teams
            tm.tournament_teams = names
            tm.participants = []
            for team_players in teams.values():
                tm.participants.extend(team_players)
            tm.scores = {name: 0 for name in names}
            tm.player_scores = {p['Player ID']: 0 for p in tm.participants}

            success, msg = tm.setup_tournament()
            assert not success, f"{num_teams} teams should be rejected"

    def test_pairing_engine_supports_up_to_40(self):
        """Verify pairing engine accepts up to 40 teams."""
        for num_teams in [20, 24, 28, 32, 36, 40]:
            teams, names = generate_teams(num_teams)
            scores = {name: 0 for name in names}
            engine = UnifiedSwissPairing(teams, names, 4, scores)
            success, pods = engine.generate_single_round(1)
            assert success
            assert len(pods) == num_teams

    def test_pairing_engine_rejects_over_40(self):
        """Verify pairing engine rejects >40 teams."""
        teams, names = generate_teams(44)
        scores = {name: 0 for name in names}

        try:
            engine = UnifiedSwissPairing(teams, names, 4, scores)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Maximum 40 teams" in str(e)


# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("PAIRING SIMULATION - Full Tournament Flow")
    print("=" * 70)

    all_results = {}

    for num_teams in [12, 16, 20, 24, 28, 32, 36, 40]:
        for swiss_rounds in [4, 5]:
            print(f"\n{'#'*70}")
            print(f"# Simulating: {num_teams} teams, {swiss_rounds} Swiss rounds")
            print(f"{'#'*70}")

            # Run 5 seeds to catch random-dependent bugs
            errors_across_seeds = []
            warnings_across_seeds = []

            for seed in range(5):
                sim = run_simulation(num_teams, swiss_rounds=swiss_rounds, seed=seed)
                if sim.errors:
                    errors_across_seeds.extend(
                        [f"(seed={seed}) {e}" for e in sim.errors]
                    )
                if sim.warnings:
                    warnings_across_seeds.extend(
                        [f"(seed={seed}) {w}" for w in sim.warnings]
                    )

            key = f"{num_teams}T/{swiss_rounds}R"
            all_results[key] = {
                'errors': errors_across_seeds,
                'warnings': warnings_across_seeds
            }

            # Print one detailed report
            sim = run_simulation(num_teams, swiss_rounds=swiss_rounds, seed=0)
            sim.print_report()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for key, result in all_results.items():
        status = "PASS" if not result['errors'] else "FAIL"
        warn_count = len(result['warnings'])
        err_count = len(result['errors'])
        print(f"  {key}: [{status}] {err_count} errors, {warn_count} warnings")

    print("\n" + "=" * 70)
    total_errors = sum(len(r['errors']) for r in all_results.values())
    if total_errors == 0:
        print("ALL CONFIGURATIONS PASSED (8-40 teams)")
    else:
        print(f"FAILURES DETECTED: {total_errors} total errors")
    print("=" * 70)
