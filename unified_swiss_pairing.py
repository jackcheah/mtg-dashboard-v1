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

class HybridConstraintSolver:
    """
    Enhanced constraint satisfaction solver with intelligent backtracking.
    
    This solver implements advanced constraint satisfaction techniques including:
    - Most-constrained-first heuristics
    - Constraint propagation
    - Intelligent backtracking with conflict analysis
    - Multiple fallback strategies
    """
    
    def __init__(self, pairing_system):
        """Initialize the constraint solver with reference to the pairing system."""
        self.pairing_system = pairing_system
        self.constraint_graph = {}
        self.domain_constraints = {}
        self.backtrack_stats = {'nodes_explored': 0, 'backtracks': 0, 'pruned_branches': 0}
    
    def build_constraint_graph(self, available_players: List[Dict]) -> Dict[int, Set[int]]:
        """
        Build a constraint graph showing which players cannot be paired together.

        Args:
            available_players: List of players to build constraints for

        Returns:
            Dictionary mapping player IDs to sets of forbidden opponent IDs
        """
        constraint_graph = {}

        for player in available_players:
            player_id = player['Player ID']
            player_team = player['Team Name']
            forbidden = set()

            # Add teammates as forbidden opponents
            for other_player in available_players:
                other_id = other_player['Player ID']
                other_team = other_player['Team Name']

                if other_id != player_id:
                    # Forbid teammates (always enforced)
                    if other_team == player_team:
                        forbidden.add(other_id)

                    # NEW: Forbid players from teams that have already faced each other
                    # Only enforce if strict team matchup constraint is enabled
                    if self.pairing_system.enforce_strict_team_matchups:
                        if other_team in self.pairing_system.team_matchups.get(player_team, set()):
                            forbidden.add(other_id)

            # Add previous individual opponents as forbidden
            if player_id in self.pairing_system.player_opponents:
                forbidden.update(self.pairing_system.player_opponents[player_id])

            constraint_graph[player_id] = forbidden

        return constraint_graph
    
    def calculate_constraint_degrees(self, available_players: List[Dict], constraint_graph: Dict[int, Set[int]]) -> Dict[int, int]:
        """
        Calculate constraint degrees for most-constrained-first heuristic.
        
        Args:
            available_players: List of available players
            constraint_graph: Graph of player constraints
            
        Returns:
            Dictionary mapping player IDs to their constraint degrees
        """
        degrees = {}
        available_ids = {p['Player ID'] for p in available_players}
        
        for player in available_players:
            player_id = player['Player ID']
            # Count how many available players this player cannot be paired with
            forbidden_available = constraint_graph[player_id] & available_ids
            degrees[player_id] = len(forbidden_available)
        
        return degrees
    
    def propagate_constraints(self, partial_pod: List[Dict], available_players: List[Dict], 
                            constraint_graph: Dict[int, Set[int]]) -> List[Dict]:
        """
        Apply constraint propagation to reduce the search space.
        
        Args:
            partial_pod: Players already assigned to current pod
            available_players: Remaining available players
            constraint_graph: Graph of player constraints
            
        Returns:
            Filtered list of players that can still be added to the pod
        """
        if not partial_pod:
            return available_players
        
        valid_candidates = []
        pod_player_ids = {p['Player ID'] for p in partial_pod}
        pod_teams = {p['Team Name'] for p in partial_pod}
        
        for candidate in available_players:
            candidate_id = candidate['Player ID']
            candidate_team = candidate['Team Name']
            
            # Skip if already in pod
            if candidate_id in pod_player_ids:
                continue
            
            # For 4-player pods, enforce team separation
            if len(partial_pod) < 4 and candidate_team in pod_teams:
                continue
            
            # Check constraint violations
            valid = True
            for pod_player in partial_pod:
                if pod_player['Player ID'] in constraint_graph.get(candidate_id, set()):
                    valid = False
                    break
            
            if valid:
                valid_candidates.append(candidate)
        
        return valid_candidates
    
    def solve_with_enhanced_backtracking(self, available_players: List[Dict]) -> Optional[List[List[Dict]]]:
        """
        Solve round using enhanced constraint satisfaction with intelligent backtracking.
        
        Args:
            available_players: List of players to assign to pods
            
        Returns:
            List of pods or None if no solution found
        """
        self.backtrack_stats = {'nodes_explored': 0, 'backtracks': 0, 'pruned_branches': 0}
        
        # Build constraint graph
        constraint_graph = self.build_constraint_graph(available_players)
        self.constraint_graph = constraint_graph
        
        # Calculate initial constraint degrees
        constraint_degrees = self.calculate_constraint_degrees(available_players, constraint_graph)
        
        # Sort players by most-constrained-first heuristic
        sorted_players = sorted(available_players, 
                              key=lambda p: constraint_degrees[p['Player ID']], 
                              reverse=True)
        
        result = self._backtrack_with_constraints(sorted_players, [], constraint_graph)
        
        print(f"    Backtrack stats: {self.backtrack_stats['nodes_explored']} nodes, "
              f"{self.backtrack_stats['backtracks']} backtracks, "
              f"{self.backtrack_stats['pruned_branches']} pruned")
        
        return result
    
    def _backtrack_with_constraints(self, available_players: List[Dict], current_pods: List[List[Dict]], 
                                  constraint_graph: Dict[int, Set[int]]) -> Optional[List[List[Dict]]]:
        """
        Enhanced backtracking with constraint propagation and conflict analysis.
        
        Args:
            available_players: Players not yet assigned
            current_pods: Pods constructed so far
            constraint_graph: Graph of player constraints
            
        Returns:
            Complete list of pods or None if no solution
        """
        self.backtrack_stats['nodes_explored'] += 1
        
        # Safety limit to prevent infinite loops/timeouts
        if self.backtrack_stats['nodes_explored'] > 500000:
            raise Exception(f"Solver timeout - search space too large ({self.backtrack_stats['nodes_explored']} nodes)")
        
        # Base case: all pods filled
        expected_pods = self.pairing_system.pods_per_round + (1 if self.pairing_system.incomplete_pod_size > 0 else 0)
        
        if len(current_pods) == expected_pods:
            return current_pods if len(available_players) == 0 else None
        
        # Determine pod size for next pod
        if len(current_pods) < self.pairing_system.pods_per_round:
            pod_size = 4
        else:
            pod_size = self.pairing_system.incomplete_pod_size
        
        # Early pruning: check if enough players remain
        remaining_pods = expected_pods - len(current_pods)
        min_players_needed = (remaining_pods - 1) * 4 + pod_size
        
        if len(available_players) < min_players_needed:
            self.backtrack_stats['pruned_branches'] += 1
            return None
        
        # Try to build next pod with enhanced constraint satisfaction
        pod_result = self._build_pod_with_constraints(available_players, pod_size, constraint_graph)
        
        if pod_result is None:
            self.backtrack_stats['backtracks'] += 1
            return None
        
        next_pod = pod_result
        new_available = [p for p in available_players if p not in next_pod]
        new_pods = current_pods + [next_pod]
        
        # Recursively solve remaining
        result = self._backtrack_with_constraints(new_available, new_pods, constraint_graph)
        
        if result is not None:
            return result
        
        # Backtrack and try alternative pod configurations
        self.backtrack_stats['backtracks'] += 1
        return self._try_alternative_pod_configurations(available_players, current_pods, pod_size, constraint_graph)
    
    def _build_pod_with_constraints(self, available_players: List[Dict], pod_size: int, 
                                  constraint_graph: Dict[int, Set[int]]) -> Optional[List[Dict]]:
        """
        Build a single pod using constraint satisfaction techniques.
        
        Args:
            available_players: Available players
            pod_size: Required pod size
            constraint_graph: Player constraints
            
        Returns:
            Valid pod or None if impossible
        """
        if pod_size == 4:
            return self._build_four_player_pod_with_constraints(available_players, constraint_graph)
        else:
            return self._build_partial_pod_with_constraints(available_players, pod_size, constraint_graph)
    
    def _build_four_player_pod_with_constraints(self, available_players: List[Dict], 
                                              constraint_graph: Dict[int, Set[int]]) -> Optional[List[Dict]]:
        """Build a 4-player pod with team separation using constraint satisfaction."""
        # Group players by team
        players_by_team = {}
        for player in available_players:
            team = player['Team Name']
            if team not in players_by_team:
                players_by_team[team] = []
            players_by_team[team].append(player)
        
        # Need at least 4 teams with available players
        available_teams = [team for team, players in players_by_team.items() if len(players) > 0]
        
        if len(available_teams) < 4:
            return None
        
        # Use constraint satisfaction to find valid 4-team combination
        return self._find_constrained_team_combination(players_by_team, available_teams, constraint_graph)
    
    def _find_constrained_team_combination(self, players_by_team: Dict[str, List[Dict]], 
                                         available_teams: List[str], 
                                         constraint_graph: Dict[int, Set[int]]) -> Optional[List[Dict]]:
        """Find a valid combination of players from 4 different teams using constraint satisfaction."""
        # Sort teams by constraint degree (most constrained first)
        team_constraint_scores = {}
        for team in available_teams:
            total_constraints = 0
            for player in players_by_team[team]:
                player_id = player['Player ID']
                total_constraints += len(constraint_graph.get(player_id, set()))
            team_constraint_scores[team] = total_constraints / len(players_by_team[team])
        
        sorted_teams = sorted(available_teams, key=lambda t: team_constraint_scores[t], reverse=True)
        
        # Try combinations starting with most constrained teams
        for team_combo in combinations(sorted_teams, 4):
            pod = self._find_valid_player_combination(team_combo, players_by_team, constraint_graph)
            if pod is not None:
                return pod
        
        return None
    
    def _find_valid_player_combination(self, team_combo: Tuple[str, ...], 
                                     players_by_team: Dict[str, List[Dict]], 
                                     constraint_graph: Dict[int, Set[int]]) -> Optional[List[Dict]]:
        """Find a valid combination of one player from each of the specified teams."""
        team_players = [players_by_team[team] for team in team_combo]
        
        # Sort players within each team by constraint degree
        for i, players in enumerate(team_players):
            team_players[i] = sorted(players, 
                                   key=lambda p: len(constraint_graph.get(p['Player ID'], set())), 
                                   reverse=True)
        
        # Use constraint satisfaction to find valid combination
        return self._recursive_player_selection(team_players, [], constraint_graph)
    
    def _recursive_player_selection(self, remaining_teams: List[List[Dict]], 
                                  current_pod: List[Dict], 
                                  constraint_graph: Dict[int, Set[int]]) -> Optional[List[Dict]]:
        """Recursively select players using constraint satisfaction."""
        if not remaining_teams:
            return current_pod if len(current_pod) == 4 else None
        
        current_team_players = remaining_teams[0]
        remaining_teams = remaining_teams[1:]
        
        for player in current_team_players:
            player_id = player['Player ID']
            
            # Check if this player violates constraints with current pod
            valid = True
            for pod_player in current_pod:
                if pod_player['Player ID'] in constraint_graph.get(player_id, set()):
                    valid = False
                    break
            
            if valid:
                new_pod = current_pod + [player]
                result = self._recursive_player_selection(remaining_teams, new_pod, constraint_graph)
                if result is not None:
                    return result
        
        return None
    
    def _build_partial_pod_with_constraints(self, available_players: List[Dict], pod_size: int, 
                                          constraint_graph: Dict[int, Set[int]]) -> Optional[List[Dict]]:
        """Build a partial pod (less than 4 players) with minimal constraint violations."""
        best_pod = None
        min_violations = float('inf')
        
        # Sort players by constraint degree
        sorted_players = sorted(available_players, 
                              key=lambda p: len(constraint_graph.get(p['Player ID'], set())), 
                              reverse=True)
        
        for pod_combo in combinations(sorted_players, pod_size):
            pod = list(pod_combo)
            violations = self._count_constraint_violations(pod, constraint_graph)
            
            if violations < min_violations:
                min_violations = violations
                best_pod = pod
                
                # If we found a perfect pod, use it
                if violations == 0:
                    break
        
        return best_pod
    
    def _count_constraint_violations(self, pod: List[Dict], constraint_graph: Dict[int, Set[int]]) -> int:
        """Count constraint violations in a pod."""
        violations = 0
        
        for i in range(len(pod)):
            for j in range(i + 1, len(pod)):
                player1_id = pod[i]['Player ID']
                player2_id = pod[j]['Player ID']
                
                if player2_id in constraint_graph.get(player1_id, set()):
                    violations += 1
        
        return violations
    
    def _try_alternative_pod_configurations(self, available_players: List[Dict], 
                                          current_pods: List[List[Dict]], pod_size: int, 
                                          constraint_graph: Dict[int, Set[int]]) -> Optional[List[List[Dict]]]:
        """Try alternative pod configurations when primary approach fails."""
        # This could implement more sophisticated backtracking strategies
        # For now, we'll return None to trigger the next algorithm level
        return None


class UnifiedSwissPairing:
    """
    Unified Swiss pairing algorithm that supports variable team counts (4-20 teams)
    and guarantees optimal Swiss pairings with comprehensive validation.
    
    This class combines constraint satisfaction, dynamic pairing, and heuristic approaches
    to provide a robust solution that works for any valid tournament configuration.
    """
    
    def __init__(self, teams: Dict[str, List[Dict]], tournament_teams: List[str], swiss_rounds_count: int = 4, team_scores: Dict[str, int] = None, use_traditional_swiss: bool = True, max_player_optimization_iterations: int = None):
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
        """
        self.teams = teams
        self.tournament_teams = tournament_teams
        self.swiss_rounds_count = swiss_rounds_count
        self.team_scores = team_scores or {}
        self.start_time = time.time()

        # Configuration flags
        self.use_traditional_swiss = use_traditional_swiss
        self.max_player_optimization_iterations = max_player_optimization_iterations
        
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
        
        # For team counts not divisible by 4, we need special handling
        if len(self.tournament_teams) % 4 != 0:
            # We can't have proper 4-team pods, so we'll use the best available configuration
            # This is a limitation that should be documented
            print(f"[WARNING]  Note: {len(self.tournament_teams)} teams cannot form perfect 4-team pods")
            print(f"   Tournament will use mixed pod sizes for optimal pairing")
        
        # Initialize constraint tracking
        self.used_pairings: Set[Tuple[int, int]] = set()
        self.player_opponents: Dict[int, Set[int]] = {}
        self.team_matchups: Dict[str, Set[str]] = {}  # NEW: Track team-level matchups
        self.round_solutions: List[List[List[Dict]]] = []
        self.groups_needing_player_optimization: Dict[int, List[Tuple[str, str]]] = {}  # Track groups with unavoidable team repeats

        # Initialize enhanced constraint solver
        self.constraint_solver = HybridConstraintSolver(self)

        # Initialize player opponent tracking
        for player in self.players:
            self.player_opponents[player['Player ID']] = set()

        # Initialize team matchup tracking
        for team_name in self.tournament_teams:
            self.team_matchups[team_name] = set()

        # Calculate if strict team matchup constraint is feasible
        # For N teams over R rounds, each team faces 3 opponents per round
        # Total matchups needed: R × 3, Available opponents: N - 1
        # Strict constraint only if: R × 3 <= N - 1
        self.enforce_strict_team_matchups = (self.swiss_rounds_count * 3) <= (len(self.tournament_teams) - 1)

        print(f"[WRENCH] Unified Swiss Pairing initialized")
        print(f"   Teams: {len(tournament_teams)} ({tournament_teams})")
        print(f"   Players: {self.total_players}")
        print(f"   Pods per round: {self.pods_per_round}")
        print(f"   Incomplete pod size: {self.incomplete_pod_size}")
        print(f"   Swiss rounds: {swiss_rounds_count}")

        if self.enforce_strict_team_matchups:
            print(f"   [OK] Team matchup policy: STRICT (each team faces unique opponents)")
        else:
            print(f"   [WARNING]  Team matchup policy: RELAXED (repeat matchups allowed when necessary)")
    
    def _validate_tournament_configuration(self):
        """Validate that the tournament configuration is valid."""
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
    
    def generate_all_rounds(self) -> Tuple[bool, List[List[List[Dict]]]]:
        """
        Generate all Swiss rounds using the unified algorithm.
        
        Returns:
            Tuple of (success, list_of_round_pairings)
        """
        print("[ROCKET] Generating all Swiss rounds with unified algorithm...")
        
        # Try multiple approaches in order of preference
        approaches = [
            ("Enhanced Constraint Satisfaction", self._solve_with_constraint_satisfaction),
            ("Dynamic Pairing with Backtracking", self._solve_with_dynamic_pairing),
            ("Relaxed Constraint Optimization", self._solve_with_relaxed_constraints)
        ]
        
        for approach_name, solve_method in approaches:
            print(f"\n--- Attempting {approach_name} ---")
            
            # Reset state for new attempt
            self._reset_constraint_tracking()
            
            try:
                success, solution = solve_method()
                
                if success:
                    self.round_solutions = solution
                    generation_time = time.time() - self.start_time
                    
                    print(f"[OK] {approach_name} succeeded!")
                    print(f"   Generation time: {generation_time:.2f} seconds")
                    print(f"   Total rounds: {len(solution)}")
                    
                    return True, solution
                else:
                    print(f"[ERROR] {approach_name} failed")
                    
            except Exception as e:
                print(f"[ERROR] {approach_name} error: {str(e)}")
                continue
        
        print("[ERROR] All approaches failed to generate valid tournament")
        return False, []

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
            # Use pod-consistency approach for this round
            round_solution = self._generate_round_with_pod_consistency(round_num)

            if round_solution is None:
                print(f"  [ERROR] Failed to generate Round {round_num}")
                return False, []

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

    def _reset_constraint_tracking(self):
        """Reset constraint tracking for a new generation attempt."""
        self.used_pairings.clear()
        for player_id in self.player_opponents:
            self.player_opponents[player_id].clear()
        for team_name in self.team_matchups:
            self.team_matchups[team_name].clear()
        self.round_solutions.clear()
    
    def _solve_with_constraint_satisfaction(self) -> Tuple[bool, List[List[List[Dict]]]]:
        """
        Primary algorithm: Team-grouping approach with pod consistency guarantee.

        Returns:
            Tuple of (success, solution)
        """
        solution = []

        for round_num in range(1, self.swiss_rounds_count + 1):
            print(f"  Solving Round {round_num}...")

            # Use new pod-consistency approach
            round_solution = self._generate_round_with_pod_consistency(round_num)

            if round_solution is None:
                print(f"  [ERROR] Failed to solve Round {round_num}")
                return False, []

            solution.append(round_solution)
            self._update_constraints_after_round(round_solution)

            print(f"  [OK] Round {round_num} solved ({len(round_solution)} pods)")

        return True, solution
    
    def _solve_round_with_backtracking(self, round_num: int) -> Optional[List[List[Dict]]]:
        """
        Solve a single round using enhanced constraint satisfaction with intelligent backtracking.
        
        Args:
            round_num: The round number being solved
            
        Returns:
            List of pods or None if no solution found
        """
        available_players = self.players.copy()
        
        print(f"    Using enhanced constraint satisfaction solver...")
        
        # Use the enhanced constraint solver
        result = self.constraint_solver.solve_with_enhanced_backtracking(available_players)
        
        if result is not None:
            print(f"    [OK] Enhanced solver succeeded")
            return result
        
        print(f"    [ERROR] Enhanced solver failed, trying fallback...")
        
        # Fallback to original backtracking if enhanced solver fails
        available_players.sort(key=lambda p: self._count_valid_opponents(p), reverse=False)
        return self._backtrack_round_solution(available_players, [])
    
    def _backtrack_round_solution(self, available_players: List[Dict], current_pods: List[List[Dict]]) -> Optional[List[List[Dict]]]:
        """
        Use backtracking to find a valid round solution.
        
        Args:
            available_players: Players not yet assigned to pods
            current_pods: Pods constructed so far
            
        Returns:
            Complete list of pods or None if no solution
        """
        # Base case: all pods filled
        expected_pods = self.pods_per_round + (1 if self.incomplete_pod_size > 0 else 0)
        
        if len(current_pods) == expected_pods:
            return current_pods if len(available_players) == 0 else None
        
        # Determine pod size for next pod
        if len(current_pods) < self.pods_per_round:
            pod_size = 4
        else:
            pod_size = self.incomplete_pod_size
        
        # Try to create next pod
        next_pod = self._find_valid_pod(available_players, pod_size)
        
        if next_pod is None:
            return None
        
        # Recursively try this pod assignment
        new_available = [p for p in available_players if p not in next_pod]
        new_pods = current_pods + [next_pod]
        
        result = self._backtrack_round_solution(new_available, new_pods)
        
        if result is not None:
            return result
        
        # If that didn't work, try other pod combinations
        return self._try_alternative_pods(available_players, current_pods, pod_size)
    
    def _find_valid_pod(self, available_players: List[Dict], pod_size: int) -> Optional[List[Dict]]:
        """
        Find a valid pod from available players using constraint satisfaction.
        
        Args:
            available_players: List of available players
            pod_size: Required pod size (3 or 4)
            
        Returns:
            List of players forming a valid pod, or None
        """
        # For 4-player pods, ensure team separation
        if pod_size == 4:
            return self._find_team_separated_pod(available_players)
        else:
            # For 3-player pods, find best available combination
            return self._find_best_three_player_pod(available_players)
    
    def _find_team_separated_pod(self, available_players: List[Dict]) -> Optional[List[Dict]]:
        """Find a 4-player pod with one player from each of 4 different teams."""
        # Group players by team
        players_by_team = {}
        for player in available_players:
            team = player['Team Name']
            if team not in players_by_team:
                players_by_team[team] = []
            players_by_team[team].append(player)
        
        # Need at least 4 teams with available players
        available_teams = [team for team, players in players_by_team.items() if len(players) > 0]
        
        if len(available_teams) < 4:
            return None
        
        # Try combinations of 4 teams
        for team_combo in combinations(available_teams, 4):
            # Try all combinations of one player from each team
            team_players = [players_by_team[team] for team in team_combo]
            
            for player_combo in self._cartesian_product(team_players):
                if self._is_valid_pod(list(player_combo)):
                    return list(player_combo)
        
        return None
    
    def _find_best_three_player_pod(self, available_players: List[Dict]) -> Optional[List[Dict]]:
        """Find the best 3-player pod minimizing constraint violations."""
        best_pod = None
        min_violations = float('inf')
        
        for pod_combo in combinations(available_players, 3):
            pod = list(pod_combo)
            violations = self._count_pod_violations(pod)
            
            if violations < min_violations:
                min_violations = violations
                best_pod = pod
                
                # If we found a perfect pod, use it
                if violations == 0:
                    break
        
        return best_pod
    
    def _cartesian_product(self, lists: List[List]) -> List[Tuple]:
        """Generate cartesian product of lists."""
        if not lists:
            return [()]
        
        result = []
        for item in lists[0]:
            for rest in self._cartesian_product(lists[1:]):
                result.append((item,) + rest)
        
        return result
    
    def _is_valid_pod(self, pod: List[Dict]) -> bool:
        """Check if a pod satisfies all hard constraints."""
        if len(pod) < 3 or len(pod) > 4:
            return False

        # For 4-player pods, check team separation
        if len(pod) == 4:
            teams = {player['Team Name'] for player in pod}
            if len(teams) != 4:
                return False

        # NEW: Check for repeat team matchups across all Swiss rounds
        # Only enforce if strict team matchup constraint is enabled
        if self.enforce_strict_team_matchups:
            teams_in_pod = [player['Team Name'] for player in pod]
            for i in range(len(teams_in_pod)):
                for j in range(i + 1, len(teams_in_pod)):
                    team1 = teams_in_pod[i]
                    team2 = teams_in_pod[j]

                    # If these teams have already faced each other, pod is invalid
                    if team2 in self.team_matchups.get(team1, set()):
                        return False

        # Check for repeat player opponents
        for i in range(len(pod)):
            for j in range(i + 1, len(pod)):
                player1_id = pod[i]['Player ID']
                player2_id = pod[j]['Player ID']

                if player2_id in self.player_opponents.get(player1_id, set()):
                    return False

        return True
    
    def _count_pod_violations(self, pod: List[Dict]) -> int:
        """Count constraint violations in a pod."""
        violations = 0

        # Count teammate violations
        teams = [player['Team Name'] for player in pod]
        team_counts = {}
        for team in teams:
            team_counts[team] = team_counts.get(team, 0) + 1

        for count in team_counts.values():
            if count > 1:
                violations += count - 1

        # NEW: Count repeat team matchup violations
        # Only count if strict team matchup constraint is enabled
        if self.enforce_strict_team_matchups:
            teams_in_pod = [player['Team Name'] for player in pod]
            for i in range(len(teams_in_pod)):
                for j in range(i + 1, len(teams_in_pod)):
                    team1 = teams_in_pod[i]
                    team2 = teams_in_pod[j]

                    if team2 in self.team_matchups.get(team1, set()):
                        violations += 1

        # Count repeat player opponent violations
        for i in range(len(pod)):
            for j in range(i + 1, len(pod)):
                player1_id = pod[i]['Player ID']
                player2_id = pod[j]['Player ID']

                if player2_id in self.player_opponents.get(player1_id, set()):
                    violations += 1

        return violations
    
    def _count_valid_opponents(self, player: Dict) -> int:
        """Count how many valid opponents a player has (for heuristic ordering)."""
        player_id = player['Player ID']
        player_team = player['Team Name']
        
        count = 0
        for other_player in self.players:
            if (other_player['Player ID'] != player_id and 
                other_player['Team Name'] != player_team and
                other_player['Player ID'] not in self.player_opponents.get(player_id, set())):
                count += 1
        
        return count
    
    def _try_alternative_pods(self, available_players: List[Dict], current_pods: List[List[Dict]], pod_size: int) -> Optional[List[List[Dict]]]:
        """Try alternative pod combinations when backtracking fails."""
        # This is a simplified fallback - in a full implementation,
        # we would try different pod combinations systematically
        return None
    
    def _solve_with_dynamic_pairing(self) -> Tuple[bool, List[List[List[Dict]]]]:
        """
        Enhanced fallback algorithm: Dynamic pairing with intelligent heuristics and multiple strategies.
        
        Returns:
            Tuple of (success, solution)
        """
        strategies = [
            ("Constraint-Guided Random", self._dynamic_pairing_constraint_guided),
            ("Team-Balanced Random", self._dynamic_pairing_team_balanced),
            ("Pure Random", self._dynamic_pairing_pure_random)
        ]
        
        for strategy_name, strategy_method in strategies:
            print(f"    Trying {strategy_name} strategy...")
            
            max_attempts = 500  # Reduced per strategy but multiple strategies
            
            for attempt in range(max_attempts):
                self._reset_constraint_tracking()
                
                success, solution = strategy_method()
                
                if success:
                    print(f"    [OK] {strategy_name} succeeded on attempt {attempt + 1}")
                    return True, solution
                
                if (attempt + 1) % 100 == 0:
                    print(f"      Attempt {attempt + 1}/{max_attempts}...")
            
            print(f"    [ERROR] {strategy_name} failed after {max_attempts} attempts")
        
        return False, []
    
    def _dynamic_pairing_constraint_guided(self) -> Tuple[bool, List[List[List[Dict]]]]:
        """Dynamic pairing guided by constraint analysis."""
        solution = []
        
        for round_num in range(1, self.swiss_rounds_count + 1):
            # Build constraint graph for this round
            constraint_graph = self.constraint_solver.build_constraint_graph(self.players)
            
            # Generate round using constraint guidance
            round_solution = self._generate_round_with_constraint_guidance(constraint_graph)
            
            if round_solution is None:
                return False, []
            
            solution.append(round_solution)
            self._update_constraints_after_round(round_solution)
        
        return True, solution
    
    def _dynamic_pairing_team_balanced(self) -> Tuple[bool, List[List[List[Dict]]]]:
        """Dynamic pairing with team balance optimization."""
        solution = []
        
        for round_num in range(1, self.swiss_rounds_count + 1):
            round_solution = self._generate_round_team_balanced()
            
            if round_solution is None:
                return False, []
            
            solution.append(round_solution)
            self._update_constraints_after_round(round_solution)
        
        return True, solution
    
    def _dynamic_pairing_pure_random(self) -> Tuple[bool, List[List[List[Dict]]]]:
        """Pure random dynamic pairing (original algorithm)."""
        solution = []
        
        for round_num in range(1, self.swiss_rounds_count + 1):
            round_solution = self._generate_round_dynamically(round_num)
            
            if round_solution is None:
                return False, []
            
            solution.append(round_solution)
            self._update_constraints_after_round(round_solution)
        
        return True, solution
    
    def _generate_round_with_constraint_guidance(self, constraint_graph: Dict[int, Set[int]]) -> Optional[List[List[Dict]]]:
        """Generate a round using constraint graph guidance."""
        available_players = self.players.copy()
        
        # Sort players by constraint degree (most constrained first)
        constraint_degrees = self.constraint_solver.calculate_constraint_degrees(available_players, constraint_graph)
        available_players.sort(key=lambda p: constraint_degrees[p['Player ID']], reverse=True)
        
        pods = []
        used_players = set()
        
        # Create full 4-player pods first
        for _ in range(self.pods_per_round):
            pod = self._create_constraint_guided_pod(available_players, used_players, 4, constraint_graph)
            if pod is None:
                return None
            
            pods.append(pod)
            used_players.update(p['Player ID'] for p in pod)
        
        # Create incomplete pod if needed
        if self.incomplete_pod_size > 0:
            remaining_players = [p for p in available_players if p['Player ID'] not in used_players]
            if len(remaining_players) == self.incomplete_pod_size:
                # Validate the remaining pod
                if self._count_constraint_violations(remaining_players, constraint_graph) <= 2:  # Allow some violations for incomplete pods
                    pods.append(remaining_players)
                else:
                    return None
            else:
                return None
        
        return pods
    
    def _create_constraint_guided_pod(self, available_players: List[Dict], used_players: Set[int], 
                                    pod_size: int, constraint_graph: Dict[int, Set[int]]) -> Optional[List[Dict]]:
        """Create a pod using constraint graph guidance."""
        candidates = [p for p in available_players if p['Player ID'] not in used_players]
        
        if len(candidates) < pod_size:
            return None
        
        if pod_size == 4:
            # Use constraint-guided team separation
            return self._create_team_separated_pod_guided(candidates, constraint_graph)
        else:
            # For partial pods, find best combination
            return self.constraint_solver._build_partial_pod_with_constraints(candidates, pod_size, constraint_graph)
    
    def _create_team_separated_pod_guided(self, candidates: List[Dict], constraint_graph: Dict[int, Set[int]]) -> Optional[List[Dict]]:
        """Create a 4-player pod with team separation using constraint guidance."""
        # Group by team
        players_by_team = {}
        for player in candidates:
            team = player['Team Name']
            if team not in players_by_team:
                players_by_team[team] = []
            players_by_team[team].append(player)
        
        available_teams = [team for team, players in players_by_team.items() if len(players) > 0]
        
        if len(available_teams) < 4:
            return None
        
        # Use constraint solver's method
        return self.constraint_solver._find_constrained_team_combination(players_by_team, available_teams, constraint_graph)
    
    def _generate_round_team_balanced(self) -> Optional[List[List[Dict]]]:
        """Generate a round with team balance optimization."""
        available_players = self.players.copy()
        
        # Group players by team and track team usage
        players_by_team = {}
        for player in available_players:
            team = player['Team Name']
            if team not in players_by_team:
                players_by_team[team] = []
            players_by_team[team].append(player)
        
        pods = []
        used_players = set()
        
        # Create full 4-player pods with team balance
        for _ in range(self.pods_per_round):
            pod = self._create_team_balanced_pod(players_by_team, used_players)
            if pod is None:
                return None
            
            pods.append(pod)
            used_players.update(p['Player ID'] for p in pod)
            
            # Remove used players from team groups
            for player in pod:
                team = player['Team Name']
                if player in players_by_team[team]:
                    players_by_team[team].remove(player)
        
        # Handle incomplete pod
        if self.incomplete_pod_size > 0:
            remaining_players = [p for team_players in players_by_team.values() for p in team_players]
            if len(remaining_players) == self.incomplete_pod_size:
                pods.append(remaining_players)
            else:
                return None
        
        return pods
    
    def _create_team_balanced_pod(self, players_by_team: Dict[str, List[Dict]], used_players: Set[int]) -> Optional[List[Dict]]:
        """Create a pod with optimal team balance."""
        available_teams = [team for team, players in players_by_team.items() 
                          if any(p['Player ID'] not in used_players for p in players)]
        
        if len(available_teams) < 4:
            return None
        
        # Try to select one player from each of 4 different teams
        for team_combo in combinations(available_teams, 4):
            pod_candidates = []
            
            for team in team_combo:
                team_players = [p for p in players_by_team[team] if p['Player ID'] not in used_players]
                if not team_players:
                    break
                
                # Select player with fewest previous opponents (most flexible)
                best_player = min(team_players, key=lambda p: len(self.player_opponents.get(p['Player ID'], set())))
                pod_candidates.append(best_player)
            
            if len(pod_candidates) == 4 and self._is_valid_pod(pod_candidates):
                return pod_candidates
        
        return None
    
    def _count_constraint_violations(self, pod: List[Dict], constraint_graph: Dict[int, Set[int]]) -> int:
        """Count constraint violations in a pod using the constraint graph."""
        return self.constraint_solver._count_constraint_violations(pod, constraint_graph)
    
    def _generate_round_dynamically(self, round_num: int) -> Optional[List[List[Dict]]]:
        """Generate a single round using dynamic pairing."""
        available_players = self.players.copy()
        random.shuffle(available_players)
        
        pods = []
        used_players = set()
        
        # Create full 4-player pods first
        for _ in range(self.pods_per_round):
            pod = self._create_dynamic_pod(available_players, used_players, 4)
            if pod is None:
                return None
            
            pods.append(pod)
            used_players.update(p['Player ID'] for p in pod)
        
        # Create incomplete pod if needed
        if self.incomplete_pod_size > 0:
            remaining_players = [p for p in available_players if p['Player ID'] not in used_players]
            if len(remaining_players) == self.incomplete_pod_size:
                pods.append(remaining_players)
            else:
                return None
        
        return pods
    
    def _create_dynamic_pod(self, available_players: List[Dict], used_players: Set[int], pod_size: int) -> Optional[List[Dict]]:
        """Create a pod using dynamic selection."""
        candidates = [p for p in available_players if p['Player ID'] not in used_players]
        
        if len(candidates) < pod_size:
            return None
        
        # Try multiple random combinations
        for _ in range(100):
            pod = random.sample(candidates, pod_size)
            if self._is_valid_pod(pod):
                return pod
        
        return None
    
    def _solve_with_relaxed_constraints(self) -> Tuple[bool, List[List[List[Dict]]]]:
        """
        Last resort: Relaxed constraint optimization to minimize violations.
        
        This algorithm allows some constraint violations but attempts to minimize them
        using optimization techniques.
        
        Returns:
            Tuple of (success, solution)
        """
        print("  Using relaxed constraints - minimizing violations...")
        
        best_solution = None
        best_violation_count = float('inf')
        
        # Try multiple optimization approaches
        optimization_attempts = 50
        
        for attempt in range(optimization_attempts):
            self._reset_constraint_tracking()
            
            solution = []
            total_violations = 0
            
            success = True
            for round_num in range(1, self.swiss_rounds_count + 1):
                round_solution, round_violations = self._generate_round_with_minimal_violations(round_num)
                
                if round_solution is None:
                    success = False
                    break
                
                solution.append(round_solution)
                total_violations += round_violations
                self._update_constraints_after_round(round_solution)
            
            if success and total_violations < best_violation_count:
                best_solution = solution
                best_violation_count = total_violations
                
                print(f"    New best solution: {total_violations} violations")
                
                # If we found a perfect solution, use it
                if total_violations == 0:
                    break
            
            if (attempt + 1) % 10 == 0:
                print(f"    Optimization attempt {attempt + 1}/{optimization_attempts}...")
        
        if best_solution is not None:
            print(f"  [OK] Relaxed constraint optimization succeeded with {best_violation_count} violations")
            return True, best_solution
        
        print("  [ERROR] Relaxed constraint optimization failed")
        return False, []
    
    def _generate_round_with_minimal_violations(self, round_num: int) -> Tuple[Optional[List[List[Dict]]], int]:
        """
        Generate a round that minimizes constraint violations.
        
        Args:
            round_num: The round number being generated
            
        Returns:
            Tuple of (round_solution, violation_count) or (None, 0) if failed
        """
        available_players = self.players.copy()
        random.shuffle(available_players)
        
        # Build constraint graph
        constraint_graph = self.constraint_solver.build_constraint_graph(available_players)
        
        best_round = None
        best_violations = float('inf')
        
        # Try multiple random arrangements
        for _ in range(20):
            random.shuffle(available_players)
            
            pods = []
            used_players = set()
            round_violations = 0
            
            # Create full 4-player pods
            for _ in range(self.pods_per_round):
                pod, pod_violations = self._create_pod_minimal_violations(available_players, used_players, 4, constraint_graph)
                if pod is None:
                    break
                
                pods.append(pod)
                round_violations += pod_violations
                used_players.update(p['Player ID'] for p in pod)
            
            # Create incomplete pod if needed
            if self.incomplete_pod_size > 0 and len(pods) == self.pods_per_round:
                remaining_players = [p for p in available_players if p['Player ID'] not in used_players]
                if len(remaining_players) == self.incomplete_pod_size:
                    pod_violations = self._count_constraint_violations(remaining_players, constraint_graph)
                    pods.append(remaining_players)
                    round_violations += pod_violations
            
            # Check if this is a complete round
            expected_pods = self.pods_per_round + (1 if self.incomplete_pod_size > 0 else 0)
            if len(pods) == expected_pods and round_violations < best_violations:
                best_round = pods
                best_violations = round_violations
                
                # If perfect round found, use it
                if round_violations == 0:
                    break
        
        return best_round, best_violations
    
    def _create_pod_minimal_violations(self, available_players: List[Dict], used_players: Set[int], 
                                     pod_size: int, constraint_graph: Dict[int, Set[int]]) -> Tuple[Optional[List[Dict]], int]:
        """
        Create a pod that minimizes constraint violations.
        
        Args:
            available_players: Available players
            used_players: Already used players
            pod_size: Required pod size
            constraint_graph: Player constraints
            
        Returns:
            Tuple of (pod, violation_count) or (None, 0) if impossible
        """
        candidates = [p for p in available_players if p['Player ID'] not in used_players]
        
        if len(candidates) < pod_size:
            return None, 0
        
        if pod_size == 4:
            return self._create_four_player_pod_minimal_violations(candidates, constraint_graph)
        else:
            return self._create_partial_pod_minimal_violations(candidates, pod_size, constraint_graph)
    
    def _create_four_player_pod_minimal_violations(self, candidates: List[Dict], 
                                                 constraint_graph: Dict[int, Set[int]]) -> Tuple[Optional[List[Dict]], int]:
        """Create a 4-player pod with minimal violations."""
        # Group by team
        players_by_team = {}
        for player in candidates:
            team = player['Team Name']
            if team not in players_by_team:
                players_by_team[team] = []
            players_by_team[team].append(player)
        
        available_teams = list(players_by_team.keys())
        
        best_pod = None
        best_violations = float('inf')
        
        # If we have 4+ teams, try team separation first
        if len(available_teams) >= 4:
            for team_combo in combinations(available_teams, 4):
                for player_combo in self._cartesian_product([players_by_team[team] for team in team_combo]):
                    pod = list(player_combo)
                    violations = self._count_constraint_violations(pod, constraint_graph)
                    
                    if violations < best_violations:
                        best_violations = violations
                        best_pod = pod
                        
                        if violations == 0:
                            return best_pod, best_violations
        
        # If team separation doesn't work well, try all 4-player combinations
        if best_violations > 2:  # Only if team separation had many violations
            for pod_combo in combinations(candidates, 4):
                pod = list(pod_combo)
                violations = self._count_constraint_violations(pod, constraint_graph)
                
                if violations < best_violations:
                    best_violations = violations
                    best_pod = pod
                    
                    if violations == 0:
                        break
        
        return best_pod, best_violations
    
    def _create_partial_pod_minimal_violations(self, candidates: List[Dict], pod_size: int, 
                                             constraint_graph: Dict[int, Set[int]]) -> Tuple[Optional[List[Dict]], int]:
        """Create a partial pod with minimal violations."""
        best_pod = None
        best_violations = float('inf')
        
        for pod_combo in combinations(candidates, pod_size):
            pod = list(pod_combo)
            violations = self._count_constraint_violations(pod, constraint_graph)
            
            if violations < best_violations:
                best_violations = violations
                best_pod = pod
                
                if violations == 0:
                    break
        
        return best_pod, best_violations
    
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

        # Step 3: Update player opponent tracking
        for pod in all_pods:
            for player in pod:
                player_id = player['Player ID']
                opponents = [p['Player ID'] for p in pod if p['Player ID'] != player_id]

                if player_id not in self.player_opponents:
                    self.player_opponents[player_id] = set()

                self.player_opponents[player_id].update(opponents)

        # Step 4: Update team matchup tracking
        for team_group in team_groups:
            for team in team_group:
                other_teams = [t for t in team_group if t != team]
                if team not in self.team_matchups:
                    self.team_matchups[team] = set()
                self.team_matchups[team].update(other_teams)

        # Step 5: Validate pod consistency
        if not self._validate_round_pod_consistency(all_pods, team_groups):
            print(f"[ERROR] Pod consistency validation failed for round {round_num}")
            return None

        return all_pods

    def _create_team_groups_for_round_OLD(self, round_num: int) -> Optional[List[List[str]]]:
        """
        OLD VERSION - Divide teams into groups of 4 for the round (Pod Consistency approach).

        Kept for reference/rollback purposes.

        Round 1: Random grouping
        Rounds 2+: Create new groupings where teams face opponents they haven't met yet

        Args:
            round_num: The round number being generated (1-based)

        Returns:
            List of team groups, each containing 4 team names
        """
        available_teams = self.tournament_teams.copy()
        num_groups = len(available_teams) // 4

        if round_num == 1:
            # Round 1: Random grouping
            random.shuffle(available_teams)
            team_groups = []
            for i in range(num_groups):
                group = available_teams[i*4:(i+1)*4]
                team_groups.append(group)
            return team_groups

        # Rounds 2+: Create groups where teams face NEW opponents
        # Use constraint-based approach to avoid repeat team matchups
        team_groups = self._create_non_repeat_team_groups(available_teams, num_groups)

        if team_groups is None:
            # Fallback: If we can't avoid all repeats, use score-based grouping
            # (This should only happen for 8 and 12 team tournaments)
            print(f"    [WARNING] Could not avoid all repeat team matchups for round {round_num}")
            available_teams = self._sort_teams_by_score(available_teams)
            team_groups = []
            for i in range(num_groups):
                group = available_teams[i*4:(i+1)*4]
                team_groups.append(group)

        return team_groups

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

            # LAYER 1: Traditional Swiss score-based grouping
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
        else:
            # POD CONSISTENCY: Use old algorithm (fallback/rollback)
            return self._create_team_groups_for_round_OLD(round_num)

    def _create_non_repeat_team_groups(self, teams: List[str], num_groups: int) -> Optional[List[List[str]]]:
        """
        Create team groups where teams face opponents they haven't met before.
        Crucially, this prioritizes grouping high-scoring teams together (Swiss System).

        Args:
            teams: List of team names to group
            num_groups: Number of groups to create (each with 4 teams)

        Returns:
            List of team groups, or None if no valid grouping exists
        """
        # Sort teams by score (Highest first) to ensure Swiss pairing
        sorted_teams = self._sort_teams_by_score(teams)
        groups = []

        def can_form_group(candidate_teams: List[str]) -> bool:
            """Check if 4 teams can form a group without repeat matchups."""
            for i in range(len(candidate_teams)):
                for j in range(i + 1, len(candidate_teams)):
                    team1 = candidate_teams[i]
                    team2 = candidate_teams[j]
                    # Check if these teams have already faced each other
                    if team2 in self.team_matchups.get(team1, set()):
                        return False
            return True

        def backtrack(remaining: List[str], current_groups: List[List[str]]) -> bool:
            """Recursively build valid team groups using score-ranked list."""
            if not remaining:
                return True

            if len(remaining) < 4:
                return False

            # Always pick the highest-ranked remaining team first
            first_team = remaining[0]
            
            # Candidates are other remaining teams that haven't played first_team
            # They are already sorted by score because 'remaining' is sorted
            candidates = []
            for team in remaining[1:]:
                if team not in self.team_matchups.get(first_team, set()):
                    candidates.append(team)

            # Optimization: If we don't have enough candidates to form a group of 4, fail early
            if len(candidates) < 3:
                return False

            # Try combinations of 3 from candidates
            # Since candidates are sorted by score, 'combinations' will produce
            # pairings of highest-ranked accessible opponents first.
            from itertools import combinations
            for combo in combinations(candidates, 3):
                group = [first_team] + list(combo)
                
                # Check if the 3 candidates can play each other
                if can_form_group(group):
                    current_groups.append(group)
                    
                    # Create new remaining list maintaining order
                    group_set = set(group)
                    new_remaining = [t for t in remaining if t not in group_set]
                    
                    if backtrack(new_remaining, current_groups):
                        return True
                    
                    current_groups.pop()

            return False

        if backtrack(sorted_teams, groups):
            return groups
        return None

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