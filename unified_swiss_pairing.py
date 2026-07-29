#!/usr/bin/env python3
"""
Unified Swiss Pairing Algorithm - A robust, scalable solution for Swiss tournament pairings.

This algorithm replaces the existing constraint satisfaction and dynamic pairing approaches
with a unified system that supports 4-20 teams and guarantees optimal Swiss pairings
with minimal repeat matchups.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from itertools import combinations
import random
import copy
import time
from dataclasses import dataclass
from enum import Enum

class ConstraintType(Enum):
    """Types of constraints in Swiss pairing."""
    TEAMMATE = "teammate"
    REPEAT_OPPONENT = "repeat_opponent"
    STRUCTURAL = "structural"

@dataclass
class ValidationReport:
    """Comprehensive validation report for tournament pairings."""
    is_perfect: bool
    total_violations: int
    repeat_opponent_violations: List[str]
    teammate_violations: List[str]
    structural_violations: List[str]
    statistics: Dict[str, Any]

@dataclass
class TournamentStats:
    """Statistical analysis of tournament pairings."""
    total_pairings: int
    expected_pairings: int
    pairing_efficiency: float
    min_opponents_per_player: int
    max_opponents_per_player: int
    perfect_tournament: bool
    generation_time: float
    algorithm_used: str


class UnifiedSwissPairing:
    """
    Unified Swiss pairing algorithm that supports variable team counts (4-20 teams)
    and guarantees optimal Swiss pairings with comprehensive validation.
    
    This class combines constraint satisfaction, dynamic pairing, and heuristic approaches
    to provide a robust solution that works for any valid tournament configuration.
    """
    
    def __init__(self, teams: Dict[str, List[Dict]], tournament_teams: List[str], swiss_rounds_count: int = 4, team_scores: Dict[str, int] = None, use_traditional_swiss: bool = True, max_player_optimization_iterations: int = None, is_individual_mode: bool = False, anti_collusion_enabled: bool = True, anti_collusion_start_round: int = 3):
        """
        Initialize the unified Swiss pairing system.

        Args:
            teams: Dictionary mapping team names to lists of player dictionaries
            tournament_teams: List of team names for the tournament (4-20 teams)
            swiss_rounds_count: Number of Swiss rounds to generate (3, 4, or 5)
            team_scores: Optional dictionary of team scores for score-based pairing (rounds 2+)
            use_traditional_swiss: If True, use traditional Swiss (score-first).
                                   If False, use pod consistency (repeat-avoidance-first)
            max_player_optimization_iterations: Cap for exhaustive player search.
                                               None = unlimited for groups with team repeats
            is_individual_mode: If True, skip team constraints and use individual pairing
            anti_collusion_enabled: If True, use snake interleave grouping in later rounds
                                    to prevent top teams from colluding via intentional draws
            anti_collusion_start_round: Round number from which anti-collusion pairing activates
        """
        self.teams = teams
        self.tournament_teams = tournament_teams
        self.swiss_rounds_count = swiss_rounds_count
        self.team_scores = team_scores or {}
        self.start_time = time.time()
        self.is_individual_mode = is_individual_mode

        # Configuration flags
        self.use_traditional_swiss = use_traditional_swiss
        self.max_player_optimization_iterations = max_player_optimization_iterations
        self.anti_collusion_enabled = anti_collusion_enabled and not is_individual_mode
        self.anti_collusion_start_round = anti_collusion_start_round
        
        # Validate input parameters
        self._validate_tournament_configuration()
        
        # Build player list and initialize tracking
        self.players = []
        self.player_by_id = {}
        self._build_player_list()
        
        # Calculate tournament structure
        self.total_players = len(self.players)
        self.pods_per_round = self.total_players // 4
        self.incomplete_pod_size = self.total_players % 4
        
        # Team mode requires team count divisible by 4
        if not self.is_individual_mode and len(self.tournament_teams) % 4 != 0:
            raise ValueError(
                f"Team mode requires team count divisible by 4. "
                f"Got {len(self.tournament_teams)} teams. Supported counts: 8, 12, 16."
            )
        
        # Initialize constraint tracking
        self.used_pairings: Set[Tuple[int, int]] = set()
        self.player_opponents: Dict[int, Set[int]] = {}
        self.team_matchups: Dict[str, Set[str]] = {}  # NEW: Track team-level matchups
        self.round_solutions: List[List[List[Dict]]] = []
        self.groups_needing_player_optimization: Dict[int, List[Tuple[str, str]]] = {}  # Track groups with unavoidable team repeats

        # Initialize player opponent tracking
        for player in self.players:
            self.player_opponents[player['Player ID']] = set()

        # Initialize team matchup tracking
        for team_name in self.tournament_teams:
            self.team_matchups[team_name] = set()

        # Calculate if strict team matchup constraint is feasible
        if self.is_individual_mode:
            self.enforce_strict_team_matchups = False
        else:
            # For N teams over R rounds, each team faces 3 opponents per round
            # Total matchups needed: R × 3, Available opponents: N - 1
            # Strict constraint only if: R × 3 <= N - 1
            self.enforce_strict_team_matchups = (self.swiss_rounds_count * 3) <= (len(self.tournament_teams) - 1)

        print(f"[WRENCH] Unified Swiss Pairing initialized")
        if self.is_individual_mode:
            print(f"   Mode: INDIVIDUAL")
            print(f"   Players: {self.total_players}")
            print(f"   Pods per round: {self.pods_per_round}" + (f" + 1 pod of {self.incomplete_pod_size}" if self.incomplete_pod_size == 3 else ""))
            if self.incomplete_pod_size in [1, 2]:
                print(f"   Bye players per round: {self.incomplete_pod_size}")
        else:
            print(f"   Teams: {len(tournament_teams)} ({tournament_teams})")
            print(f"   Players: {self.total_players}")
            print(f"   Pods per round: {self.pods_per_round}")
            print(f"   Incomplete pod size: {self.incomplete_pod_size}")
        print(f"   Swiss rounds: {swiss_rounds_count}")

        if not self.is_individual_mode:
            if self.enforce_strict_team_matchups:
                print(f"   [OK] Team matchup policy: STRICT (each team faces unique opponents)")
            else:
                print(f"   [WARNING]  Team matchup policy: RELAXED (repeat matchups allowed when necessary)")
    
    def _validate_tournament_configuration(self):
        """Validate that the tournament configuration is valid."""
        if self.is_individual_mode:
            total_players = sum(len(self.teams[t]) for t in self.tournament_teams)
            if total_players < 16:
                raise ValueError(f"Individual mode requires at least 16 players, got {total_players}")
            if self.swiss_rounds_count not in [3, 4, 5]:
                raise ValueError(f"Swiss rounds must be 3, 4, or 5, got {self.swiss_rounds_count}")
            return

        team_count = len(self.tournament_teams)

        if team_count < 4:
            raise ValueError(f"Minimum 4 teams required, got {team_count}")

        if team_count > 20:
            raise ValueError(f"Maximum 20 teams supported, got {team_count}")

        if self.swiss_rounds_count not in [3, 4, 5]:
            raise ValueError(f"Swiss rounds must be 3, 4, or 5, got {self.swiss_rounds_count}")

        # Validate that all teams exist in the teams dictionary
        for team_name in self.tournament_teams:
            if team_name not in self.teams:
                raise ValueError(f"Team '{team_name}' not found in teams dictionary")

            if len(self.teams[team_name]) != 4:
                raise ValueError(f"Team '{team_name}' must have exactly 4 players, got {len(self.teams[team_name])}")

        # Special validation for team counts that don't divide evenly by 4
        if team_count % 4 != 0:
            print(f"[WARNING]  Warning: {team_count} teams will result in incomplete pods")
            print(f"   Each round will have {team_count // 4} full pods and 1 pod with {team_count % 4} players")
    
    def _build_player_list(self):
        """Build the complete player list from tournament teams."""
        for team_name in self.tournament_teams:
            for player in self.teams[team_name]:
                self.players.append(player)
                self.player_by_id[player['Player ID']] = player
            
        # Randomize player order to prevent deterministic pod groupings (e.g. Team A always in Seat 1)
        random.shuffle(self.players)
    

    def generate_single_round(self, round_num: int) -> Tuple[bool, List[List[Dict]]]:
        """
        Generate a single Swiss round using the pod-consistency algorithm.
        This is used for incremental round generation based on current scores.

        Args:
            round_num: The round number to generate (1-based)

        Returns:
            Tuple of (success, list_of_pods_for_this_round)
        """
        print(f"[ROTATING] Generating Round {round_num} with current scores...")

        # Update team scores from the tournament's current scores
        if hasattr(self, 'team_scores') and self.team_scores:
            print(f"   Using current team scores for pairing")

        try:
            # Route to individual mode if applicable
            if self.is_individual_mode:
                round_solution = self._generate_round_individual_mode(round_num)
            else:
                # Use pod-consistency approach for this round
                round_solution = self._generate_round_with_pod_consistency(round_num)

            if round_solution is None:
                print(f"  [ERROR] Failed to generate Round {round_num}")
                return False, []

            # Check for repeat matchups BEFORE updating constraints
            self.last_round_had_repeats = False
            for pod in round_solution:
                player_ids = [p['Player ID'] for p in pod]
                for i in range(len(player_ids)):
                    for j in range(i + 1, len(player_ids)):
                        pair = tuple(sorted([player_ids[i], player_ids[j]]))
                        if pair in self.used_pairings:
                            self.last_round_had_repeats = True
                            break
                    if self.last_round_had_repeats:
                        break
                if self.last_round_had_repeats:
                    break

            if self.last_round_had_repeats:
                print(f"  [WARNING] Round {round_num} contains unavoidable repeat matchups")

            # Update constraints after this round
            self._update_constraints_after_round(round_solution)

            # Add to round solutions
            self.round_solutions.append(round_solution)

            print(f"  [OK] Round {round_num} generated ({len(round_solution)} pods)")
            return True, round_solution

        except Exception as e:
            print(f"  [ERROR] Error generating Round {round_num}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, []

    def update_team_scores(self, new_scores: Dict[str, int]):
        """
        Update the team scores for score-based pairing in subsequent rounds.

        Args:
            new_scores: Dictionary mapping team names to their current scores
        """
        self.team_scores = new_scores.copy()
        print(f"   Team scores updated: {self.team_scores}")

    def _generate_round_individual_mode(self, round_num: int) -> Optional[List[List[Dict]]]:
        """
        Generate a round for individual mode using score-based Swiss pairing.
        Players are sorted by score, grouped into pods of 4, with swap optimization
        to avoid repeat opponents.

        Returns:
            List of pods (each pod is a list of player dicts), or None on failure.
            Remainder players (1-2) are excluded — caller handles byes.
        """
        print(f"  [INDIVIDUAL] Generating round {round_num} for {len(self.players)} players")

        # Sort players by score (descending), break ties with random shuffle
        sorted_players = sorted(
            self.players,
            key=lambda p: (self.team_scores.get(p['Team Name'], 0), random.random()),
            reverse=True
        )

        total = len(sorted_players)
        remainder = total % 4

        # Players who play this round (exclude bye players)
        if remainder in [1, 2]:
            # Bottom-ranked players get byes, preferring those who haven't had byes before
            candidates = sorted_players[total - remainder * 2:] if total >= remainder * 2 else sorted_players[total - remainder:]
            previous_bye_ids = getattr(self, '_previous_bye_ids', set())
            candidates.sort(key=lambda p: (p['Player ID'] in previous_bye_ids, self.team_scores.get(p['Team Name'], 0)))
            bye_players = candidates[:remainder]
            playing_players = [p for p in sorted_players if p not in bye_players]
            print(f"  [INDIVIDUAL] {len(bye_players)} player(s) receive bye this round")
        elif remainder == 3:
            # Last 3 form a 3-player pod
            playing_players = sorted_players
            bye_players = []
        else:
            playing_players = sorted_players
            bye_players = []

        # Form pods of 4 (and one pod of 3 if remainder==3)
        pods = []
        full_pod_count = len(playing_players) // 4
        for i in range(full_pod_count):
            pods.append(playing_players[i*4:(i+1)*4])

        if remainder == 3:
            pods.append(playing_players[full_pod_count*4:])

        # Optimize: swap players between adjacent pods to minimize repeat opponents
        pods = self._optimize_individual_pods(pods)

        # Store bye player info for caller (accessed via self.last_bye_players)
        self.last_bye_players = [p['Player ID'] for p in bye_players]

        # Track cumulative bye history for future rounds
        if not hasattr(self, '_previous_bye_ids'):
            self._previous_bye_ids = set()
        self._previous_bye_ids.update(self.last_bye_players)

        print(f"  [INDIVIDUAL] Generated {len(pods)} pods" +
              (f" ({len(bye_players)} byes)" if bye_players else ""))
        return pods

    def _optimize_individual_pods(self, pods: List[List[Dict]]) -> List[List[Dict]]:
        """
        Optimize pods for individual mode by swapping players between adjacent pods
        to minimize repeat opponent pairings.
        """
        if len(pods) <= 1:
            return pods

        max_iterations = 150
        improvements = 0

        for _ in range(max_iterations):
            improved = False
            for i in range(len(pods)):
                pod = pods[i]
                repeat_count = self._count_repeat_opponents_in_pod(pod)
                if repeat_count == 0:
                    continue

                # Try swapping with adjacent pods
                for j in [i-1, i+1]:
                    if j < 0 or j >= len(pods):
                        continue
                    if len(pods[j]) != len(pod):
                        continue  # Don't swap between different-sized pods

                    # Calculate old repeat count for pod j BEFORE any swaps
                    old_repeat_j = self._count_repeat_opponents_in_pod(pods[j])

                    # Try each player pair swap
                    for pi in range(len(pod)):
                        for pj in range(len(pods[j])):
                            # Swap
                            pods[i][pi], pods[j][pj] = pods[j][pj], pods[i][pi]

                            new_repeat_i = self._count_repeat_opponents_in_pod(pods[i])
                            new_repeat_j = self._count_repeat_opponents_in_pod(pods[j])

                            if (new_repeat_i + new_repeat_j) < (repeat_count + old_repeat_j):
                                improved = True
                                improvements += 1
                                break
                            else:
                                # Revert swap
                                pods[i][pi], pods[j][pj] = pods[j][pj], pods[i][pi]

                        if improved:
                            break
                    if improved:
                        break

            if not improved:
                break

        # Special pass: optimize 3-player pod by swapping with adjacent 4-player pod
        three_player_indices = [i for i, p in enumerate(pods) if len(p) == 3]
        for three_idx in three_player_indices:
            repeat_3 = self._count_repeat_opponents_in_pod(pods[three_idx])
            if repeat_3 == 0:
                continue
            adjacent_idx = three_idx - 1 if three_idx > 0 else three_idx + 1
            if adjacent_idx < 0 or adjacent_idx >= len(pods) or len(pods[adjacent_idx]) != 4:
                continue
            old_repeat_adj = self._count_repeat_opponents_in_pod(pods[adjacent_idx])
            best_swap = None
            best_total = repeat_3 + old_repeat_adj
            for pi in range(len(pods[three_idx])):
                for pj in range(len(pods[adjacent_idx])):
                    pods[three_idx][pi], pods[adjacent_idx][pj] = pods[adjacent_idx][pj], pods[three_idx][pi]
                    new_total = (self._count_repeat_opponents_in_pod(pods[three_idx]) +
                                 self._count_repeat_opponents_in_pod(pods[adjacent_idx]))
                    if new_total < best_total:
                        best_swap = (pi, pj)
                        best_total = new_total
                    pods[three_idx][pi], pods[adjacent_idx][pj] = pods[adjacent_idx][pj], pods[three_idx][pi]
            if best_swap:
                pi, pj = best_swap
                pods[three_idx][pi], pods[adjacent_idx][pj] = pods[adjacent_idx][pj], pods[three_idx][pi]
                improvements += 1

        if improvements > 0:
            print(f"  [INDIVIDUAL] Pod optimization: {improvements} swaps made")

        return pods

    def _count_repeat_opponents_in_pod(self, pod: List[Dict]) -> int:
        """Count how many player pairs in a pod have already faced each other."""
        count = 0
        for i in range(len(pod)):
            for j in range(i + 1, len(pod)):
                pid_i = pod[i]['Player ID']
                pid_j = pod[j]['Player ID']
                if pid_j in self.player_opponents.get(pid_i, set()):
                    count += 1
        return count

    def _reset_constraint_tracking(self):
        """Reset constraint tracking for a new generation attempt."""
        self.used_pairings.clear()
        for player_id in self.player_opponents:
            self.player_opponents[player_id].clear()
        for team_name in self.team_matchups:
            self.team_matchups[team_name].clear()
        self.round_solutions.clear()

    def _update_constraints_after_round(self, round_solution: List[List[Dict]]):
        """Update constraint tracking after a round is solved."""
        for pod in round_solution:
            for i in range(len(pod)):
                for j in range(i + 1, len(pod)):
                    player1_id = pod[i]['Player ID']
                    player2_id = pod[j]['Player ID']

                    # Add to used pairings
                    pair = tuple(sorted([player1_id, player2_id]))
                    self.used_pairings.add(pair)

                    # Add to opponent tracking
                    self.player_opponents[player1_id].add(player2_id)
                    self.player_opponents[player2_id].add(player1_id)

            # NEW: Update team matchup tracking for each team in the pod
            teams_in_pod = [player['Team Name'] for player in pod]
            for i in range(len(teams_in_pod)):
                for j in range(i + 1, len(teams_in_pod)):
                    team1 = teams_in_pod[i]
                    team2 = teams_in_pod[j]

                    # Record that these teams have faced each other
                    self.team_matchups[team1].add(team2)
                    self.team_matchups[team2].add(team1)
    
    def validate_solution(self, solution: List[List[List[Dict]]]) -> ValidationReport:
        """
        Comprehensive validation of the tournament solution.
        
        Args:
            solution: List of rounds, each containing list of pods
            
        Returns:
            ValidationReport with detailed validation results
        """
        repeat_violations = []
        teammate_violations = []
        structural_violations = []
        
        seen_pairings = set()
        
        for round_num, round_pods in enumerate(solution, 1):
            # Validate round structure
            if self.is_individual_mode:
                # Individual mode: remainder 1-2 = bye players (no pod), only remainder 3 = 3-player pod
                expected_pods = self.pods_per_round + (1 if self.incomplete_pod_size == 3 else 0)
            else:
                expected_pods = self.pods_per_round + (1 if self.incomplete_pod_size > 0 else 0)
            if len(round_pods) != expected_pods:
                structural_violations.append(f"Round {round_num}: Expected {expected_pods} pods, got {len(round_pods)}")
            
            round_players = set()
            
            for pod_idx, pod in enumerate(round_pods, 1):
                # Validate pod structure
                expected_size = 4 if pod_idx <= self.pods_per_round else self.incomplete_pod_size
                if len(pod) != expected_size:
                    structural_violations.append(f"Round {round_num} Pod {pod_idx}: Expected {expected_size} players, got {len(pod)}")
                
                # Check team separation for 4-player pods
                if len(pod) == 4:
                    teams = {player['Team Name'] for player in pod}
                    if len(teams) != 4:
                        teammate_violations.append(f"Round {round_num} Pod {pod_idx}: Teams not separated")
                
                # Check player uniqueness and repeat opponents
                for player in pod:
                    player_id = player['Player ID']
                    if player_id in round_players:
                        structural_violations.append(f"Round {round_num}: Player {player_id} appears multiple times")
                    round_players.add(player_id)
                
                # Check for repeat pairings
                for i in range(len(pod)):
                    for j in range(i + 1, len(pod)):
                        player1_id = pod[i]['Player ID']
                        player2_id = pod[j]['Player ID']
                        
                        pair = tuple(sorted([player1_id, player2_id]))
                        if pair in seen_pairings:
                            repeat_violations.append(f"Round {round_num}: Repeat pairing {player1_id} vs {player2_id}")
                        seen_pairings.add(pair)
        
        # Generate statistics
        stats = self._generate_statistics(solution)
        
        total_violations = len(repeat_violations) + len(teammate_violations) + len(structural_violations)
        
        return ValidationReport(
            is_perfect=total_violations == 0,
            total_violations=total_violations,
            repeat_opponent_violations=repeat_violations,
            teammate_violations=teammate_violations,
            structural_violations=structural_violations,
            statistics=stats
        )
    
    def _generate_statistics(self, solution: List[List[List[Dict]]]) -> Dict[str, Any]:
        """Generate comprehensive statistics for the tournament solution."""
        generation_time = time.time() - self.start_time
        
        total_pairings = len(self.used_pairings)
        expected_pairings = 0
        
        for round_pods in solution:
            for pod in round_pods:
                pod_size = len(pod)
                expected_pairings += (pod_size * (pod_size - 1)) // 2
        
        # Calculate opponent counts per player
        opponent_counts = [len(opponents) for opponents in self.player_opponents.values()]
        
        return {
            'total_pairings': total_pairings,
            'expected_pairings': expected_pairings,
            'pairing_efficiency': (total_pairings / expected_pairings * 100) if expected_pairings > 0 else 0,
            'min_opponents_per_player': min(opponent_counts) if opponent_counts else 0,
            'max_opponents_per_player': max(opponent_counts) if opponent_counts else 0,
            'perfect_tournament': total_pairings == expected_pairings and len(set(opponent_counts)) <= 1,
            'generation_time': generation_time,
            'algorithm_used': 'Unified Swiss Pairing',
            'rounds_generated': len(solution),
            'total_players': self.total_players,
            'total_teams': len(self.tournament_teams)
        }
    
    def get_detailed_statistics(self) -> TournamentStats:
        """Get detailed tournament statistics."""
        if not self.round_solutions:
            raise ValueError("No solution available - generate tournament first")

        stats_dict = self._generate_statistics(self.round_solutions)

        return TournamentStats(
            total_pairings=stats_dict['total_pairings'],
            expected_pairings=stats_dict['expected_pairings'],
            pairing_efficiency=stats_dict['pairing_efficiency'],
            min_opponents_per_player=stats_dict['min_opponents_per_player'],
            max_opponents_per_player=stats_dict['max_opponents_per_player'],
            perfect_tournament=stats_dict['perfect_tournament'],
            generation_time=stats_dict['generation_time'],
            algorithm_used=stats_dict['algorithm_used']
        )

    # =========================================================================
    # POD CONSISTENCY FUNCTIONS - Fix for 16-team tournament bug
    # =========================================================================

    def _generate_round_with_pod_consistency(self, round_num: int) -> Optional[List[List[Dict]]]:
        """
        Generate a round with guaranteed pod consistency.

        This ensures that when 4 teams are paired together, ALL 4 players from each team
        face each other across exactly 4 separate pods. No mixing with other teams.

        Args:
            round_num: The round number being generated (1-based)

        Returns:
            List of pods for the round, or None if generation failed
        """
        print(f"    [WRENCH] Using pod-consistency algorithm for Round {round_num}")

        # Step 1: Group teams into sets of 4
        team_groups = self._create_team_groups_for_round(round_num)

        if team_groups is None:
            return None

        print(f"    Team groups: {team_groups}")

        all_pods = []

        # Step 2: Create 4 pods for each team group
        for group_idx, team_group in enumerate(team_groups):
            print(f"    Creating pods for team group: {team_group}")
            pods = self._create_four_pods_for_team_group(team_group, round_num, group_index=group_idx)

            if pods is None or len(pods) != 4:
                print(f"[ERROR] Failed to create 4 pods for team group: {team_group}")
                return None

            all_pods.extend(pods)

        # Step 3: Validate pod consistency BEFORE constraints are updated
        if not self._validate_round_pod_consistency(all_pods, team_groups):
            print(f"[ERROR] Pod consistency validation failed for round {round_num}")
            return None

        return all_pods


    def _create_team_groups_for_round(self, round_num: int) -> List[List[str]]:
        """
        Divide teams into groups of 4 for the round.

        Round 1: Random grouping
        Rounds 2+: Traditional Swiss (score-based) with three-layer repeat avoidance

        Args:
            round_num: The round number being generated (1-based)

        Returns:
            List of team groups, each containing 4 team names
        """
        available_teams = self.tournament_teams.copy()
        num_groups = len(available_teams) // 4

        if round_num == 1:
            # Round 1: Random grouping (existing logic)
            random.shuffle(available_teams)
            team_groups = []
            for i in range(num_groups):
                group = available_teams[i*4:(i+1)*4]
                team_groups.append(group)
            return team_groups

        # Round 2+: Choose algorithm based on configuration
        if self.use_traditional_swiss:
            # TRADITIONAL SWISS: Three-layer repeat avoidance

            # LAYER 1: Determine grouping strategy
            if self.anti_collusion_enabled and round_num >= self.anti_collusion_start_round:
                groups = self._create_team_groups_snake_interleave(round_num)
            else:
                groups = self._create_team_groups_traditional_swiss(round_num)

            # LAYER 2: Detect and resolve team-level repeats via swapping
            repeats = self._detect_repeat_matchups_in_groups(groups)

            unresolvable_groups = []
            if repeats:
                groups, unresolvable_groups = self._resolve_repeat_matchups_by_swapping(groups, repeats)

            # Final validation
            is_valid, violations, groups_with_repeats = self._validate_all_groups_no_repeats(groups)

            # LAYER 3: Mark groups with unavoidable team repeats for player optimization
            if groups_with_repeats:
                repeat_info = self._mark_groups_for_player_optimization(groups, groups_with_repeats)
                # Store for use in player assignment phase
                self.groups_needing_player_optimization = repeat_info
            else:
                self.groups_needing_player_optimization = {}

            # Logging
            if not is_valid:
                print(f"\n{'='*60}")
                print(f"[WARNING] Round {round_num}: Team-level repeat matchups unavoidable")
                print(f"{'='*60}")
                for violation in violations:
                    print(f"  ⚠️  {violation}")
                print(f"\n[INFO] Player-level optimization will be applied to minimize player repeats")
                print(f"{'='*60}\n")

            return groups

        raise ValueError(f"Non-traditional Swiss not implemented for round {round_num}")

    def _sort_teams_by_score(self, teams: List[str]) -> List[str]:
        """
        Sort teams by current score (highest to lowest).

        Args:
            teams: List of team names to sort

        Returns:
            Sorted list of team names
        """
        if not self.team_scores:
            # No scores available, return as-is
            return teams

        return sorted(teams,
                     key=lambda t: self.team_scores.get(t, 0),
                     reverse=True)

    # ============================================================================
    # TRADITIONAL SWISS PAIRING IMPLEMENTATION (Three-Layer System)
    # ============================================================================

    def _create_team_groups_traditional_swiss(self, round_num: int) -> List[List[str]]:
        """
        Create team groups using traditional Swiss pairing (score-based).

        Groups teams into brackets of 4 based on current scores:
        - Top 4 teams (highest scores) → Group 1
        - Next 4 teams → Group 2
        - etc.

        Args:
            round_num: The round number being generated (1-based)

        Returns:
            List of team groups, each containing 4 team names
            Note: Groups may contain repeat team matchups (will be resolved in Layer 2)
        """
        # Sort teams by score (highest first)
        sorted_teams = self._sort_teams_by_score(self.tournament_teams.copy())

        # Calculate number of groups (4 teams per group)
        num_groups = len(sorted_teams) // 4

        # Create groups by slicing sorted list
        team_groups = []
        for i in range(num_groups):
            group = sorted_teams[i*4:(i+1)*4]
            team_groups.append(group)

        return team_groups

    def _create_team_groups_snake_interleave(self, round_num: int) -> List[List[str]]:
        """
        Create team groups using snake/interleave pattern to prevent top-team collusion.

        Instead of grouping top teams together (traditional Swiss), this spreads
        them across groups so each group has one team from each quartile.

        Snake pattern for N groups:
          Row 0 (forward):  teams[0..N-1]   -> groups [0, 1, ..., N-1]
          Row 1 (reverse):  teams[N..2N-1]  -> groups [N-1, N-2, ..., 0]
          Row 2 (forward):  teams[2N..3N-1] -> groups [0, 1, ..., N-1]
          Row 3 (reverse):  teams[3N..4N-1] -> groups [N-1, N-2, ..., 0]

        Example (16 teams, 4 groups):
          Group 0: seeds 1, 8, 9, 16
          Group 1: seeds 2, 7, 10, 15
          Group 2: seeds 3, 6, 11, 14
          Group 3: seeds 4, 5, 12, 13
        """
        sorted_teams = self._sort_teams_by_score(self.tournament_teams.copy())
        num_groups = len(sorted_teams) // 4

        team_groups = [[] for _ in range(num_groups)]

        for row in range(4):
            start = row * num_groups
            chunk = sorted_teams[start:start + num_groups]
            if row % 2 == 0:
                for i, team in enumerate(chunk):
                    team_groups[i].append(team)
            else:
                for i, team in enumerate(chunk):
                    team_groups[num_groups - 1 - i].append(team)

        print(f"    [ANTI-COLLUSION] Round {round_num}: Using snake interleave grouping")

        return team_groups

    def _detect_repeat_matchups_in_groups(self, groups: List[List[str]]) -> List[Tuple[int, str, str]]:
        """
        Detect all team-level repeat matchups across all groups.

        Args:
            groups: List of team groups to check

        Returns:
            List of tuples: (group_index, team1, team2) for each repeat found
        """
        repeats = []

        for group_idx, team_group in enumerate(groups):
            # Check all pairs within this group
            for i in range(len(team_group)):
                for j in range(i + 1, len(team_group)):
                    team1 = team_group[i]
                    team2 = team_group[j]

                    # Check if these teams have played before
                    if team2 in self.team_matchups.get(team1, set()):
                        repeats.append((group_idx, team1, team2))

        return repeats

    def _mark_groups_for_player_optimization(self, groups: List[List[str]],
                                             groups_with_repeats: List[int]) -> Dict[int, List[Tuple[str, str]]]:
        """
        Mark groups that need aggressive player-level optimization.

        These groups have unavoidable team-level repeats and will use exhaustive
        player assignment search to minimize player-level repeat matchups.

        Args:
            groups: All team groups
            groups_with_repeats: Indices of groups with team-level repeats

        Returns:
            Dict mapping group_index → list of (team1, team2) pairs that are repeats

        Example:
            {
                0: [('Team C', 'Team E')],  # Table 1 has C vs E repeat
                2: [('Team A', 'Team B'), ('Team A', 'Team D')]  # Table 3 has 2 repeats
            }
        """
        optimization_map = {}

        for group_idx in groups_with_repeats:
            team_group = groups[group_idx]
            repeat_pairs = []

            # Find all repeat pairs in this group
            for i in range(len(team_group)):
                for j in range(i + 1, len(team_group)):
                    team1 = team_group[i]
                    team2 = team_group[j]

                    if team2 in self.team_matchups.get(team1, set()):
                        repeat_pairs.append((team1, team2))

            if repeat_pairs:
                optimization_map[group_idx] = repeat_pairs

        return optimization_map

    def _validate_all_groups_no_repeats(self, groups: List[List[str]]) -> Tuple[bool, List[str], List[int]]:
        """
        Comprehensive validation of all groups for repeat team matchups.

        Checks every group for team-level repeats and collects:
        - Violation messages (for logging)
        - Group indices with repeats (for player optimization marking)

        Args:
            groups: List of team groups to validate

        Returns:
            (is_valid, violations_list, group_indices_with_repeats)

        Example:
            (False,
             ['Table 1: Team C vs Team E (teams played before)'],
             [0])
        """
        violations = []
        groups_with_repeats = []

        for group_idx, team_group in enumerate(groups):
            group_name = f"Table {group_idx + 1}"
            group_has_repeat = False

            for i in range(len(team_group)):
                for j in range(i + 1, len(team_group)):
                    team1 = team_group[i]
                    team2 = team_group[j]

                    if team2 in self.team_matchups.get(team1, set()):
                        violations.append(
                            f"{group_name}: {team1} vs {team2} (teams played before)"
                        )
                        group_has_repeat = True

            if group_has_repeat:
                groups_with_repeats.append(group_idx)

        return (len(violations) == 0, violations, groups_with_repeats)

    def _group_has_repeat_matchups(self, team_group: List[str]) -> bool:
        """
        Check if any teams in this group have played each other before.

        Args:
            team_group: List of 4 team names

        Returns:
            True if any repeat matchup exists, False otherwise
        """
        for i in range(len(team_group)):
            for j in range(i + 1, len(team_group)):
                team1 = team_group[i]
                team2 = team_group[j]

                if team2 in self.team_matchups.get(team1, set()):
                    return True

        return False

    # ============================================================================
    # LAYER 2: TEAM SWAP ALGORITHM
    # ============================================================================

    def _resolve_repeat_matchups_by_swapping(self, groups: List[List[str]],
                                              repeats: List[Tuple[int, str, str]]) -> Tuple[List[List[str]], List[int]]:
        """
        Resolve team-level repeat matchups by swapping teams between groups.

        Strategy:
        1. For each repeat, identify the lower-ranked team in the pair
        2. Search adjacent brackets for a swap candidate
        3. Perform swap if it doesn't create new repeats
        4. Track unresolvable groups

        Args:
            groups: List of team groups
            repeats: List of (group_idx, team1, team2) tuples

        Returns:
            (modified_groups, list_of_unresolvable_group_indices)
        """
        # Create mutable copy
        groups = [g.copy() for g in groups]

        # Track which groups have unresolvable repeats
        unresolvable_groups = set()

        # Track swap attempts to prevent infinite loops
        swap_history = set()
        max_swap_attempts = 10

        for group_idx, team1, team2 in repeats:
            # Identify lower-ranked team (to swap out)
            team1_score = self.team_scores.get(team1, 0)
            team2_score = self.team_scores.get(team2, 0)

            if team1_score < team2_score:
                problem_team = team1
            elif team2_score < team1_score:
                problem_team = team2
            else:
                # Same score, pick one arbitrarily (e.g., alphabetically later)
                problem_team = max(team1, team2)

            # Verify problem_team is still in this group (may have been moved by earlier swap)
            if problem_team not in groups[group_idx]:
                continue

            # Try to find swap candidate
            swap_result = self._find_best_swap_candidate(
                problem_team,
                group_idx,
                groups,
                swap_history,
                max_attempts=max_swap_attempts
            )

            if swap_result:
                target_group_idx, swap_team = swap_result

                # Perform the swap
                groups[group_idx].remove(problem_team)
                groups[group_idx].append(swap_team)
                groups[target_group_idx].remove(swap_team)
                groups[target_group_idx].append(problem_team)

                # Record swap
                swap_key = tuple(sorted([problem_team, swap_team]))
                swap_history.add(swap_key)
            else:
                # Cannot resolve this repeat
                unresolvable_groups.add(group_idx)

        return groups, list(unresolvable_groups)

    def _find_best_swap_candidate(self,
                                   problem_team: str,
                                   problem_group_idx: int,
                                   all_groups: List[List[str]],
                                   swap_history: Set[Tuple[str, str]],
                                   max_attempts: int = 10) -> Optional[Tuple[int, str]]:
        """
        Find best team to swap with problem_team to resolve repeat matchup.

        Swap priority:
        1. Adjacent brackets (±1) - minimizes score disruption
        2. Two brackets away (±2) - acceptable score difference
        3. Any bracket - last resort

        Args:
            problem_team: Team that needs to be swapped out
            problem_group_idx: Index of group containing problem_team
            all_groups: All team groups
            swap_history: Set of (team1, team2) swaps already attempted
            max_attempts: Maximum number of candidates to try

        Returns:
            (target_group_index, swap_team_name) or None if no valid swap exists
        """
        candidates = []

        # Try adjacent groups first (±1 bracket)
        for offset in [-1, 1]:
            target_group_idx = problem_group_idx + offset
            if 0 <= target_group_idx < len(all_groups):
                for swap_team in all_groups[target_group_idx]:
                    # Skip if already tried this swap
                    swap_key = tuple(sorted([problem_team, swap_team]))
                    if swap_key in swap_history:
                        continue

                    if self._is_valid_swap(problem_team, swap_team,
                                           problem_group_idx, target_group_idx,
                                           all_groups):
                        score_diff = abs(self.team_scores.get(problem_team, 0) -
                                        self.team_scores.get(swap_team, 0))
                        candidates.append((score_diff, target_group_idx, swap_team))

        # If no adjacent swaps found, try ±2 brackets
        if not candidates and max_attempts > 4:
            for offset in [-2, 2]:
                target_group_idx = problem_group_idx + offset
                if 0 <= target_group_idx < len(all_groups):
                    for swap_team in all_groups[target_group_idx]:
                        swap_key = tuple(sorted([problem_team, swap_team]))
                        if swap_key in swap_history:
                            continue

                        if self._is_valid_swap(problem_team, swap_team,
                                              problem_group_idx, target_group_idx,
                                              all_groups):
                            score_diff = abs(self.team_scores.get(problem_team, 0) -
                                            self.team_scores.get(swap_team, 0))
                            candidates.append((score_diff, target_group_idx, swap_team))

        # If still no candidates, try all groups (last resort)
        if not candidates and max_attempts > 8:
            for target_group_idx in range(len(all_groups)):
                if target_group_idx == problem_group_idx:
                    continue

                for swap_team in all_groups[target_group_idx]:
                    swap_key = tuple(sorted([problem_team, swap_team]))
                    if swap_key in swap_history:
                        continue

                    if self._is_valid_swap(problem_team, swap_team,
                                          problem_group_idx, target_group_idx,
                                          all_groups):
                        score_diff = abs(self.team_scores.get(problem_team, 0) -
                                        self.team_scores.get(swap_team, 0))
                        candidates.append((score_diff, target_group_idx, swap_team))

        # Return swap with smallest score difference
        if candidates:
            candidates.sort()  # Sort by score_diff (first element of tuple)
            return (candidates[0][1], candidates[0][2])

        return None

    def _is_valid_swap(self, team_a: str, team_b: str,
                       group_a_idx: int, group_b_idx: int,
                       all_groups: List[List[str]]) -> bool:
        """
        Check if swapping team_a (from group_a) with team_b (from group_b)
        creates any new repeat matchups.

        Args:
            team_a: First team to swap
            team_b: Second team to swap
            group_a_idx: Index of group containing team_a
            group_b_idx: Index of group containing team_b
            all_groups: All team groups

        Returns:
            True if swap is safe (doesn't create new repeats), False otherwise
        """
        # Simulate the swap
        group_a = all_groups[group_a_idx].copy()
        group_b = all_groups[group_b_idx].copy()

        group_a.remove(team_a)
        group_a.append(team_b)

        group_b.remove(team_b)
        group_b.append(team_a)

        # Check both groups for repeats after swap
        if self._group_has_repeat_matchups(group_a):
            return False

        if self._group_has_repeat_matchups(group_b):
            return False

        return True

    # ============================================================================
    # END OF TRADITIONAL SWISS HELPER FUNCTIONS
    # ============================================================================

    def _create_four_pods_for_team_group(self, team_group: List[str], round_num: int, group_index: int = None) -> Optional[List[List[Dict]]]:
        """
        Create exactly 4 pods from 4 teams, avoiding player-level repeat matchups.

        Uses backtracking to find player assignments that minimize repeat opponents.
        If this group has unavoidable team-level repeats, uses exhaustive search.

        Args:
            team_group: List of 4 team names
            round_num: The round number (used for rotation calculation)
            group_index: Index of this group (used to check if player optimization needed)

        Returns:
            List of 4 pods, each containing 4 players (one from each team)
        """
        # Get all players from these 4 teams
        team_players = {}
        for team in team_group:
            team_players[team] = self.teams[team].copy()

        # Check if this group needs maximum player optimization
        needs_max_optimization = (
            hasattr(self, 'groups_needing_player_optimization') and
            group_index is not None and
            group_index in self.groups_needing_player_optimization
        )

        if needs_max_optimization:
            # Log that we're doing exhaustive search
            repeat_teams = self.groups_needing_player_optimization[group_index]
            print(f"    [PLAYER OPTIMIZATION] Table {group_index + 1}: Team-level repeat unavoidable")
            print(f"                         Teams with repeat: {repeat_teams}")
            print(f"                         Using exhaustive player search to minimize player repeats...")

        # Try to find optimal player assignment using backtracking
        best_pods = None
        best_repeat_count = float('inf')
        best_repeat_details = []

        # Round 1: Collect multiple perfect solutions for random selection
        perfect_solutions = [] if round_num == 1 else None
        max_round1_solutions = 100  # Cap to prevent memory issues

        from itertools import permutations
        import random

        # First team's players go to pods 0,1,2,3 in order
        first_team = team_group[0]
        first_team_players = team_players[first_team]

        # Try different permutations for other teams
        other_teams = team_group[1:]
        other_team_perms = [list(permutations(range(4))) for _ in other_teams]

        # Adjust search depth based on optimization need
        if needs_max_optimization:
            # Exhaustive search: Try ALL permutations (24 per team = 24^3 total)
            max_perms = len(other_team_perms[0]) if other_team_perms else 1
            if self.max_player_optimization_iterations:
                # Apply user-defined cap if set
                max_perms = min(max_perms, self.max_player_optimization_iterations)
            print(f"                         Trying {max_perms**len(other_teams):,} permutation combinations...")
        else:
            # Normal search: Try first 24 combinations (existing behavior)
            max_perms = min(24, len(other_team_perms[0]) if other_team_perms else 1)

        iterations = 0
        early_exit = False  # Flag for Round 1 cap
        for perm1 in other_team_perms[0][:max_perms] if other_team_perms else [()]:
            if early_exit:
                break
            for perm2 in other_team_perms[1][:max_perms] if len(other_team_perms) > 1 else [()]:
                if early_exit:
                    break
                for perm3 in other_team_perms[2][:max_perms] if len(other_team_perms) > 2 else [()]:
                    if early_exit:
                        break
                    iterations += 1

                    # Build pods with this permutation
                    pods = []
                    repeat_count = 0
                    repeat_details = []

                    for pod_idx in range(4):
                        pod = []
                        # First team player
                        if pod_idx < len(first_team_players):
                            pod.append(first_team_players[pod_idx])

                        # Other teams' players based on permutation
                        perms = [perm1, perm2, perm3]
                        for team_idx, team in enumerate(other_teams):
                            if team_idx < len(perms):
                                player_idx = perms[team_idx][pod_idx]
                                if player_idx < len(team_players[team]):
                                    pod.append(team_players[team][player_idx])

                        if len(pod) == 4:
                            pods.append(pod)
                            # Count repeat matchups in this pod
                            if needs_max_optimization:
                                pod_repeats, pod_details = self._count_and_detail_repeat_matchups_in_pod(pod, pod_idx)
                                repeat_count += pod_repeats
                                repeat_details.extend(pod_details)
                            else:
                                repeat_count += self._count_repeat_matchups_in_pod(pod)

                    if len(pods) == 4 and repeat_count < best_repeat_count:
                        best_pods = pods
                        best_repeat_count = repeat_count
                        best_repeat_details = repeat_details

                        if repeat_count == 0:
                            # Round 1: Collect multiple perfect solutions for randomization
                            if round_num == 1 and perfect_solutions is not None:
                                # Deep copy the pods to avoid reference issues
                                pods_copy = [pod[:] for pod in pods]
                                perfect_solutions.append(pods_copy)

                                # Cap collection to prevent memory issues
                                if len(perfect_solutions) >= max_round1_solutions:
                                    early_exit = True
                                    break
                            else:
                                # Round 2+: Return first perfect solution (existing behavior)
                                if needs_max_optimization:
                                    print(f"                         ✅ PERFECT: Found zero player repeats after {iterations:,} iterations!")
                                return best_pods

        # Round 1: Randomly select from collected perfect solutions
        if round_num == 1 and perfect_solutions:
            selected_solution = random.choice(perfect_solutions)
            print(f"    [ROUND 1 RANDOMIZATION] Selected 1 of {len(perfect_solutions)} perfect solutions for enhanced randomization")
            return selected_solution

        # Report results for groups with team repeats
        if needs_max_optimization:
            if best_repeat_count == 0:
                print(f"                         ✅ SUCCESS: Zero player-level repeats despite team repeat!")
            else:
                print(f"                         ⚠️  MINIMIZED: {best_repeat_count} player repeat(s) (unavoidable)")
                for detail in best_repeat_details:
                    print(f"                             - {detail}")

        return best_pods

    def _count_repeat_matchups_in_pod(self, pod: List[Dict]) -> int:
        """Count how many player pairs in this pod have faced each other before."""
        repeat_count = 0
        for i in range(len(pod)):
            for j in range(i + 1, len(pod)):
                player1_id = pod[i]['Player ID']
                player2_id = pod[j]['Player ID']
                if player2_id in self.player_opponents.get(player1_id, set()):
                    repeat_count += 1
        return repeat_count

    def _count_and_detail_repeat_matchups_in_pod(self, pod: List[Dict], pod_idx: int) -> Tuple[int, List[str]]:
        """
        Count and detail player-level repeat matchups in this pod.

        Used for exhaustive player optimization to provide detailed logging.

        Args:
            pod: List of 4 player dictionaries
            pod_idx: Pod index for reporting (0-3)

        Returns:
            (repeat_count, list_of_repeat_descriptions)

        Example:
            (2, ['Pod 1: Alice vs Bob', 'Pod 3: Carol vs Dave'])
        """
        repeat_count = 0
        details = []

        for i in range(len(pod)):
            for j in range(i + 1, len(pod)):
                player1_id = pod[i]['Player ID']
                player2_id = pod[j]['Player ID']
                player1_name = pod[i]['Player Name']
                player2_name = pod[j]['Player Name']

                if player2_id in self.player_opponents.get(player1_id, set()):
                    repeat_count += 1
                    details.append(f"Pod {pod_idx + 1}: {player1_name} vs {player2_name}")

        return repeat_count, details

    def _have_teams_met_before(self, team_group: List[str]) -> bool:
        """
        Check if these 4 teams have all met before.

        Args:
            team_group: List of 4 team names

        Returns:
            True if these teams have faced each other before
        """
        # Check if any team has faced all other teams in the group
        for team in team_group:
            other_teams = set([t for t in team_group if t != team])
            if team in self.team_matchups:
                if other_teams.issubset(self.team_matchups[team]):
                    return True

        return False

    def _calculate_player_rotation(self, team_group: List[str], round_num: int) -> List[int]:
        """
        Calculate rotation offsets to avoid player-level repeats when teams meet again.

        Uses round number to determine rotation pattern, ensuring different matchups
        each time the same 4 teams meet.

        Args:
            team_group: List of 4 team names
            round_num: The round number

        Returns:
            List of rotation offsets for each team
        """
        # Use round number to determine rotation
        # This ensures different matchups each time
        base_rotation = (round_num - 1) % 4
        return [(base_rotation + i) % 4 for i in range(4)]

    def _validate_round_pod_consistency(self, all_pods: List[List[Dict]],
                                       team_groups: List[List[str]]) -> bool:
        """
        Validate that pods maintain consistency requirements.

        Checks:
        1. Each team matchup group has exactly 4 pods
        2. Each team has exactly 1 player per pod
        3. All 4 players from each team participate

        Args:
            all_pods: All pods in the round
            team_groups: The team groups that were used

        Returns:
            True if validation passes, False otherwise
        """
        # Group pods by team sets
        pods_by_team_set = {}

        for pod in all_pods:
            teams_in_pod = frozenset([p['Team Name'] for p in pod])

            if teams_in_pod not in pods_by_team_set:
                pods_by_team_set[teams_in_pod] = []

            pods_by_team_set[teams_in_pod].append(pod)

        # Verify each team set has exactly 4 pods
        for team_set, pods in pods_by_team_set.items():
            if len(pods) != 4:
                print(f"[ERROR] Validation failed: Team set {team_set} has {len(pods)} pods (expected 4)")
                return False

            # Verify each team has exactly 1 player per pod
            for team in team_set:
                for pod in pods:
                    team_players_in_pod = [p for p in pod if p['Team Name'] == team]
                    if len(team_players_in_pod) != 1:
                        print(f"[ERROR] Validation failed: {team} has {len(team_players_in_pod)} players in a pod")
                        return False

        return True