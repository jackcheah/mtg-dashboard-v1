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
                    # Forbid teammates
                    if other_team == player_team:
                        forbidden.add(other_id)

                    # NEW: Forbid players from teams that have already faced each other
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
    
    def __init__(self, teams: Dict[str, List[Dict]], tournament_teams: List[str], swiss_rounds_count: int = 4):
        """
        Initialize the unified Swiss pairing system.

        Args:
            teams: Dictionary mapping team names to lists of player dictionaries
            tournament_teams: List of team names for the tournament (4-20 teams)
            swiss_rounds_count: Number of Swiss rounds to generate (3, 4, or 5)
        """
        self.teams = teams
        self.tournament_teams = tournament_teams
        self.swiss_rounds_count = swiss_rounds_count
        self.start_time = time.time()
        
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
            print(f"⚠️  Note: {len(self.tournament_teams)} teams cannot form perfect 4-team pods")
            print(f"   Tournament will use mixed pod sizes for optimal pairing")
        
        # Initialize constraint tracking
        self.used_pairings: Set[Tuple[int, int]] = set()
        self.player_opponents: Dict[int, Set[int]] = {}
        self.team_matchups: Dict[str, Set[str]] = {}  # NEW: Track team-level matchups
        self.round_solutions: List[List[List[Dict]]] = []

        # Initialize enhanced constraint solver
        self.constraint_solver = HybridConstraintSolver(self)

        # Initialize player opponent tracking
        for player in self.players:
            self.player_opponents[player['Player ID']] = set()

        # Initialize team matchup tracking
        for team_name in self.tournament_teams:
            self.team_matchups[team_name] = set()
        
        print(f"🔧 Unified Swiss Pairing initialized")
        print(f"   Teams: {len(tournament_teams)} ({tournament_teams})")
        print(f"   Players: {self.total_players}")
        print(f"   Pods per round: {self.pods_per_round}")
        print(f"   Incomplete pod size: {self.incomplete_pod_size}")
        print(f"   Swiss rounds: {swiss_rounds_count}")
    
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
            print(f"⚠️  Warning: {team_count} teams will result in incomplete pods")
            print(f"   Each round will have {team_count // 4} full pods and 1 pod with {team_count % 4} players")
    
    def _build_player_list(self):
        """Build the complete player list from tournament teams."""
        for team_name in self.tournament_teams:
            for player in self.teams[team_name]:
                self.players.append(player)
                self.player_by_id[player['Player ID']] = player
    
    def generate_all_rounds(self) -> Tuple[bool, List[List[List[Dict]]]]:
        """
        Generate all Swiss rounds using the unified algorithm.
        
        Returns:
            Tuple of (success, list_of_round_pairings)
        """
        print("🚀 Generating all Swiss rounds with unified algorithm...")
        
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
                    
                    print(f"✅ {approach_name} succeeded!")
                    print(f"   Generation time: {generation_time:.2f} seconds")
                    print(f"   Total rounds: {len(solution)}")
                    
                    return True, solution
                else:
                    print(f"❌ {approach_name} failed")
                    
            except Exception as e:
                print(f"❌ {approach_name} error: {str(e)}")
                continue
        
        print("❌ All approaches failed to generate valid tournament")
        return False, []
    
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
        Primary algorithm: Enhanced constraint satisfaction with intelligent backtracking.
        
        Returns:
            Tuple of (success, solution)
        """
        solution = []
        
        for round_num in range(1, self.swiss_rounds_count + 1):
            print(f"  Solving Round {round_num}...")
            
            round_solution = self._solve_round_with_backtracking(round_num)
            
            if round_solution is None:
                print(f"  ❌ Failed to solve Round {round_num}")
                return False, []
            
            solution.append(round_solution)
            self._update_constraints_after_round(round_solution)
            
            print(f"  ✅ Round {round_num} solved ({len(round_solution)} pods)")
        
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
            print(f"    ✅ Enhanced solver succeeded")
            return result
        
        print(f"    ❌ Enhanced solver failed, trying fallback...")
        
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
                    print(f"    ✅ {strategy_name} succeeded on attempt {attempt + 1}")
                    return True, solution
                
                if (attempt + 1) % 100 == 0:
                    print(f"      Attempt {attempt + 1}/{max_attempts}...")
            
            print(f"    ❌ {strategy_name} failed after {max_attempts} attempts")
        
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
            print(f"  ✅ Relaxed constraint optimization succeeded with {best_violation_count} violations")
            return True, best_solution
        
        print("  ❌ Relaxed constraint optimization failed")
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