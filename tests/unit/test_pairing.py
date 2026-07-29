"""Unit tests for the UnifiedSwissPairing engine.

Tests team mode pairing constraints, individual mode logic (byes, 3-player pods,
score-based grouping), and edge cases.

Run: pytest tests/unit/test_pairing.py -v
"""
import sys
import os
import random
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unified_swiss_pairing import UnifiedSwissPairing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_teams(num_teams):
    """Create team data structures for num_teams teams (4 players each)."""
    teams = {}
    tournament_teams = []
    for t in range(num_teams):
        team_name = f"Team {chr(65 + t)}" if t < 26 else f"Team {t + 1}"
        players = []
        for p in range(4):
            pid = t * 4 + p + 1
            players.append({
                'Player Name': f'{team_name} P{p + 1}',
                'Player ID': pid,
                'Team Name': team_name,
            })
        teams[team_name] = players
        tournament_teams.append(team_name)
    return teams, tournament_teams


def make_individual_players(num_players):
    """Create individual-mode data structures for num_players players."""
    teams = {}
    tournament_teams = []
    for i in range(num_players):
        name = f"Player {i + 1}"
        pid = 1000 + i
        player = {'Player Name': name, 'Player ID': pid, 'Team Name': name}
        teams[name] = [player]
        tournament_teams.append(name)
    return teams, tournament_teams


# ===========================================================================
# TEAM MODE TESTS
# ===========================================================================

class TestTeamModeNoTeammatesInPod:
    """Verify that no two players from the same team end up in the same pod."""

    def test_no_teammates_in_same_pod_8_teams(self):
        teams, tournament_teams = make_teams(8)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4)
        success, round_solution = engine.generate_single_round(1)

        assert success
        for pod in round_solution:
            team_names = [p['Team Name'] for p in pod]
            assert len(team_names) == len(set(team_names)), \
                f"Pod has duplicate teams: {team_names}"

    def test_no_teammates_in_same_pod_16_teams(self):
        teams, tournament_teams = make_teams(16)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4)
        success, round_solution = engine.generate_single_round(1)

        assert success
        for pod in round_solution:
            team_names = [p['Team Name'] for p in pod]
            assert len(team_names) == len(set(team_names)), \
                f"Pod has duplicate teams: {team_names}"


class TestTeamModePodStructure:
    """Verify structural properties of generated pods."""

    def test_all_pods_have_4_players(self):
        teams, tournament_teams = make_teams(8)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4)
        success, round_solution = engine.generate_single_round(1)

        assert success
        for pod in round_solution:
            assert len(pod) == 4, f"Pod has {len(pod)} players, expected 4"

    def test_16_teams_zero_repeat_player_matchups_4_rounds(self):
        """For 16 teams over 4 rounds, no player pair should meet twice.

        The algorithm guarantees zero player-level repeat matchups for 16 teams
        across 4 Swiss rounds, even when team-level groupings must repeat for
        Swiss score-fairness. It achieves this via exhaustive player-position
        optimization within each team group.
        """
        teams, tournament_teams = make_teams(16)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4)

        solution = []
        for round_num in range(1, 5):
            if round_num > 1:
                scores = {t: random.randint(0, 20) for t in tournament_teams}
                engine.update_team_scores(scores)
            success, round_solution = engine.generate_single_round(round_num)
            assert success, f"Failed to generate round {round_num}"
            solution.append(round_solution)

        # Validate: no player pair should appear in the same pod more than once
        report = engine.validate_solution(solution)
        assert report.repeat_opponent_violations == [], \
            f"Repeat player matchups found: {report.repeat_opponent_violations}"


class TestTeamModeScoreGrouping:
    """Verify that score-based Swiss pairing groups top teams together."""

    def test_score_based_grouping_after_round_1(self):
        teams, tournament_teams = make_teams(8)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4)

        # Generate round 1
        success, _ = engine.generate_single_round(1)
        assert success

        # Set scores: first 4 teams are top-scoring
        scores = {}
        for i, team in enumerate(tournament_teams):
            scores[team] = 20 - i  # Descending scores
        engine.update_team_scores(scores)

        # Generate round 2
        success, round_solution = engine.generate_single_round(2)
        assert success

        # The top 4 teams (highest scores) should be grouped together
        top_4_teams = set(sorted(tournament_teams, key=lambda t: scores[t], reverse=True)[:4])
        # Check that at least one pod contains mostly top-4 teams
        best_overlap = 0
        for pod in round_solution:
            pod_teams = set(p['Team Name'] for p in pod)
            overlap = len(pod_teams & top_4_teams)
            best_overlap = max(best_overlap, overlap)

        # In traditional Swiss, the top bracket should have 4 top teams together
        assert best_overlap == 4, \
            f"Expected top 4 teams grouped together, best overlap was {best_overlap}"


class TestTeamModeValidation:
    """Validate entire tournament solutions."""

    def test_pairing_validation_report_clean(self):
        """validate_solution on a fresh 8-team 4-round generation should report no violations."""
        teams, tournament_teams = make_teams(8)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4)

        solution = []
        for round_num in range(1, 5):
            if round_num > 1:
                scores = {t: random.randint(0, 15) for t in tournament_teams}
                engine.update_team_scores(scores)
            success, round_sol = engine.generate_single_round(round_num)
            assert success
            solution.append(round_sol)

        report = engine.validate_solution(solution)
        assert report.teammate_violations == [], \
            f"Teammate violations found: {report.teammate_violations}"
        assert report.structural_violations == [], \
            f"Structural violations found: {report.structural_violations}"


# ===========================================================================
# INDIVIDUAL MODE TESTS
# ===========================================================================

class TestIndividualModeScoreSorting:
    """Verify score-based pod assignment in individual mode."""

    def test_individual_pods_sorted_by_score(self):
        """Players with highest scores should end up in the first pods."""
        teams, tournament_teams = make_individual_players(20)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     is_individual_mode=True)

        # Generate round 1 (scores all 0, random order)
        success, _ = engine.generate_single_round(1)
        assert success

        # Assign graduated scores
        scores = {}
        for i, name in enumerate(tournament_teams):
            scores[name] = 100 - i * 5
        engine.update_team_scores(scores)

        # Generate round 2
        success, round_solution = engine.generate_single_round(2)
        assert success

        # First pod should contain the highest-scored players
        first_pod_scores = [scores[p['Team Name']] for p in round_solution[0]]
        last_pod_scores = [scores[p['Team Name']] for p in round_solution[-1]]
        assert min(first_pod_scores) >= max(last_pod_scores), \
            f"First pod min score {min(first_pod_scores)} < last pod max {max(last_pod_scores)}"


class TestIndividualModeRemainders:
    """Verify correct handling of player counts not divisible by 4."""

    def test_individual_remainder_3_forms_3_player_pod(self):
        """19 players = 4 pods of 4 + 1 pod of 3, no byes."""
        teams, tournament_teams = make_individual_players(19)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     is_individual_mode=True)

        success, round_solution = engine.generate_single_round(1)
        assert success

        pod_sizes = sorted([len(pod) for pod in round_solution])
        assert pod_sizes.count(4) == 4, f"Expected 4 pods of size 4, got {pod_sizes}"
        assert pod_sizes.count(3) == 1, f"Expected 1 pod of size 3, got {pod_sizes}"
        assert engine.last_bye_players == []

    def test_individual_remainder_1_gets_bye(self):
        """17 players = 4 pods of 4, 1 player gets a bye."""
        teams, tournament_teams = make_individual_players(17)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     is_individual_mode=True)

        success, round_solution = engine.generate_single_round(1)
        assert success

        # All pods should be size 4
        for pod in round_solution:
            assert len(pod) == 4, f"Pod has {len(pod)} players, expected 4"

        assert len(round_solution) == 4
        assert len(engine.last_bye_players) == 1

    def test_individual_remainder_2_gets_bye(self):
        """18 players = 4 pods of 4, 2 players get byes."""
        teams, tournament_teams = make_individual_players(18)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     is_individual_mode=True)

        success, round_solution = engine.generate_single_round(1)
        assert success

        for pod in round_solution:
            assert len(pod) == 4
        assert len(round_solution) == 4
        assert len(engine.last_bye_players) == 2


class TestIndividualModeRepeatAvoidance:
    """Verify that the optimizer avoids repeat opponents."""

    def test_individual_repeat_avoidance(self):
        """Generate 2 rounds and check that opponents differ where possible."""
        teams, tournament_teams = make_individual_players(20)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     is_individual_mode=True)

        success, round1 = engine.generate_single_round(1)
        assert success

        # Collect round 1 opponents
        round1_opponents = {}
        for pod in round1:
            for player in pod:
                pid = player['Player ID']
                opponents = frozenset(p['Player ID'] for p in pod if p['Player ID'] != pid)
                round1_opponents[pid] = opponents

        # Update scores and generate round 2
        scores = {name: random.randint(0, 15) for name in tournament_teams}
        engine.update_team_scores(scores)

        success, round2 = engine.generate_single_round(2)
        assert success

        # Count repeat opponent pairs across all pods in round 2
        total_pairs = 0
        repeat_pairs = 0
        for pod in round2:
            for i in range(len(pod)):
                for j in range(i + 1, len(pod)):
                    total_pairs += 1
                    pid_i = pod[i]['Player ID']
                    pid_j = pod[j]['Player ID']
                    if pid_j in round1_opponents.get(pid_i, set()):
                        repeat_pairs += 1

        # With 20 players over 2 rounds, expect very few (ideally 0) repeats
        # Allow some tolerance since optimization is best-effort
        repeat_ratio = repeat_pairs / total_pairs if total_pairs > 0 else 0
        assert repeat_ratio < 0.3, \
            f"Too many repeat opponents: {repeat_pairs}/{total_pairs} ({repeat_ratio:.0%})"


# ===========================================================================
# EDGE CASES
# ===========================================================================

class TestEdgeCases:
    """Edge case tests for the pairing engine."""

    def test_pairing_all_tied_scores(self):
        """When all players have the same score, generation should still succeed."""
        teams, tournament_teams = make_individual_players(20)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     is_individual_mode=True)

        # Generate round 1
        success, _ = engine.generate_single_round(1)
        assert success

        # All players at same score
        scores = {name: 10 for name in tournament_teams}
        engine.update_team_scores(scores)

        # Round 2 should still succeed
        success, round_solution = engine.generate_single_round(2)
        assert success
        assert len(round_solution) == 5  # 20 players / 4 = 5 pods

        # Every pod should have exactly 4 players
        for pod in round_solution:
            assert len(pod) == 4

    def test_pairing_after_player_removal(self):
        """Rebuilding engine with fewer players should produce valid generation."""
        # Start with 20 players
        teams, tournament_teams = make_individual_players(20)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     is_individual_mode=True)

        success, _ = engine.generate_single_round(1)
        assert success

        # Simulate dropping 2 players: rebuild engine with 18 players
        new_teams, new_tournament_teams = make_individual_players(18)
        new_engine = UnifiedSwissPairing(new_teams, new_tournament_teams,
                                         swiss_rounds_count=4, is_individual_mode=True)

        success, round_solution = new_engine.generate_single_round(1)
        assert success

        # 18 players: 4 pods of 4 + 2 byes
        for pod in round_solution:
            assert len(pod) == 4
        assert len(round_solution) == 4
        assert len(new_engine.last_bye_players) == 2


# ===========================================================================
# ANTI-COLLUSION SNAKE PAIRING TESTS
# ===========================================================================

class TestAntiCollusionSnakePairing:
    """Verify snake interleave grouping prevents top teams from being grouped together."""

    def _run_rounds_up_to(self, engine, up_to_round):
        """Generate and commit rounds 1 through up_to_round-1, return engine ready for up_to_round."""
        for r in range(1, up_to_round):
            success, solution = engine.generate_single_round(r)
            assert success, f"Failed to generate round {r}"
            engine._update_constraints_after_round(solution)
            engine.round_solutions.append(solution)

    def test_snake_grouping_spreads_top_teams_16(self):
        """With 16 teams, no group in round 3 should contain 2+ of the top 4 teams."""
        teams, tournament_teams = make_teams(16)
        scores = {t: (16 - i) * 5 for i, t in enumerate(tournament_teams)}
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     team_scores=scores, anti_collusion_enabled=True,
                                     anti_collusion_start_round=3)

        # Run rounds 1-2
        self._run_rounds_up_to(engine, 3)
        engine.update_team_scores(scores)

        # Directly test the grouping method
        groups = engine._create_team_groups_snake_interleave(3)

        top_4 = set(tournament_teams[:4])
        for group in groups:
            top_in_group = [t for t in group if t in top_4]
            assert len(top_in_group) <= 1, \
                f"Group has multiple top-4 teams: {top_in_group}"

    def test_snake_grouping_spreads_top_teams_8(self):
        """With 8 teams, no group should contain both of the top 2 teams."""
        teams, tournament_teams = make_teams(8)
        scores = {t: (8 - i) * 5 for i, t in enumerate(tournament_teams)}
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     team_scores=scores, anti_collusion_enabled=True,
                                     anti_collusion_start_round=3)

        self._run_rounds_up_to(engine, 3)
        engine.update_team_scores(scores)

        groups = engine._create_team_groups_snake_interleave(3)

        top_2 = set(tournament_teams[:2])
        for group in groups:
            top_in_group = [t for t in group if t in top_2]
            assert len(top_in_group) <= 1, \
                f"Group has both top-2 teams: {top_in_group}"

    def test_snake_not_active_round_2(self):
        """Round 2 should still use traditional Swiss (top teams grouped together)."""
        teams, tournament_teams = make_teams(16)
        scores = {t: (16 - i) * 5 for i, t in enumerate(tournament_teams)}
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     team_scores=scores, anti_collusion_enabled=True,
                                     anti_collusion_start_round=3)

        self._run_rounds_up_to(engine, 2)
        engine.update_team_scores(scores)

        # Round 2 uses traditional Swiss — top 4 should be in same group
        groups = engine._create_team_groups_traditional_swiss(2)
        top_4 = set(tournament_teams[:4])
        group_0_top = [t for t in groups[0] if t in top_4]
        assert len(group_0_top) == 4, \
            "Round 2 should group top 4 teams together (traditional Swiss)"

    def test_snake_disabled_flag(self):
        """With anti_collusion_enabled=False, round 3 should use traditional Swiss."""
        teams, tournament_teams = make_teams(16)
        scores = {t: (16 - i) * 5 for i, t in enumerate(tournament_teams)}
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     team_scores=scores, anti_collusion_enabled=False,
                                     anti_collusion_start_round=3)

        self._run_rounds_up_to(engine, 3)
        engine.update_team_scores(scores)

        # With anti-collusion disabled, the routing should use traditional Swiss
        # which puts top 4 in same group
        groups = engine._create_team_groups_traditional_swiss(3)
        top_4 = set(tournament_teams[:4])
        group_0_top = [t for t in groups[0] if t in top_4]
        assert len(group_0_top) == 4

    def test_snake_groups_composition_16_teams(self):
        """Each group should have exactly one team from each quartile."""
        teams, tournament_teams = make_teams(16)
        scores = {t: (16 - i) * 5 for i, t in enumerate(tournament_teams)}
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     team_scores=scores, anti_collusion_enabled=True,
                                     anti_collusion_start_round=3)

        engine.update_team_scores(scores)
        groups = engine._create_team_groups_snake_interleave(3)

        sorted_teams = sorted(tournament_teams, key=lambda t: scores[t], reverse=True)
        quartiles = [
            set(sorted_teams[0:4]),
            set(sorted_teams[4:8]),
            set(sorted_teams[8:12]),
            set(sorted_teams[12:16]),
        ]

        for group in groups:
            for q_idx, quartile in enumerate(quartiles):
                in_quartile = [t for t in group if t in quartile]
                assert len(in_quartile) == 1, \
                    f"Group {group} has {len(in_quartile)} teams from quartile {q_idx+1}"

    def test_snake_custom_start_round(self):
        """Anti-collusion with start_round=4 should not activate in round 3."""
        teams, tournament_teams = make_teams(16)
        scores = {t: (16 - i) * 5 for i, t in enumerate(tournament_teams)}
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=5,
                                     team_scores=scores, anti_collusion_enabled=True,
                                     anti_collusion_start_round=4)

        self._run_rounds_up_to(engine, 3)
        engine.update_team_scores(scores)

        # Round 3 should still be traditional (start_round=4)
        groups = engine._create_team_groups_traditional_swiss(3)
        top_4 = set(tournament_teams[:4])
        group_0_top = [t for t in groups[0] if t in top_4]
        assert len(group_0_top) == 4

    def test_full_tournament_with_anti_collusion(self):
        """4-round tournament with 16 teams completes without structural violations."""
        teams, tournament_teams = make_teams(16)
        engine = UnifiedSwissPairing(teams, tournament_teams, swiss_rounds_count=4,
                                     anti_collusion_enabled=True,
                                     anti_collusion_start_round=3)

        for round_num in range(1, 5):
            success, solution = engine.generate_single_round(round_num)
            assert success, f"Round {round_num} generation failed"

            # Validate no teammates in same pod
            for pod in solution:
                pod_teams = [p['Team Name'] for p in pod]
                assert len(pod_teams) == len(set(pod_teams)), \
                    f"Round {round_num}: teammates in same pod: {pod_teams}"

            engine._update_constraints_after_round(solution)
            engine.round_solutions.append(solution)

            # Update scores (simulate wins for top teams)
            scores = {}
            for i, t in enumerate(tournament_teams):
                scores[t] = (16 - i) * 5 * round_num
            engine.update_team_scores(scores)
