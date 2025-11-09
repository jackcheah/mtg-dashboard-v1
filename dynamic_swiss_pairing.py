#!/usr/bin/env python3
"""
Dynamic Swiss Pairing System - Performance-Based Team Pairing with Player Randomization

This module implements true Swiss pairing where:
1. Teams are paired based on performance (winners vs winners)
2. Players are randomized within team pairings to avoid repeat matchups
3. Maximum variety and fairness across all rounds

Author: MTG Tournament Dashboard
Date: November 2025
"""

from typing import Dict, List, Set, Tuple, Optional
import random
from itertools import combinations


class PlayerPairingTracker:
    """
    Track which players have faced each other across all tournament rounds.
    
    This class maintains a complete history of all player-vs-player matchups
    to enable intelligent pairing that avoids repeat encounters.
    """
    
    def __init__(self):
        """Initialize the player pairing tracker."""
        # Track all previous opponents for each player
        # Structure: {player_id: set(opponent_ids)}
        self.player_opponents: Dict[int, Set[int]] = {}
        
        # Track complete round history for analysis
        self.round_history: List[List[List[Dict]]] = []
        
        # Track matchup counts for statistics
        self.matchup_counts: Dict[Tuple[int, int], int] = {}
    
    def record_matchup(self, player_id: int, opponent_id: int):
        """
        Record that two players faced each other.
        
        Args:
            player_id: ID of first player
            opponent_id: ID of second player
        """
        # Initialize if needed
        if player_id not in self.player_opponents:
            self.player_opponents[player_id] = set()
        if opponent_id not in self.player_opponents:
            self.player_opponents[opponent_id] = set()
        
        # Record mutual opponents
        self.player_opponents[player_id].add(opponent_id)
        self.player_opponents[opponent_id].add(player_id)
        
        # Track matchup count
        pair = tuple(sorted([player_id, opponent_id]))
        self.matchup_counts[pair] = self.matchup_counts.get(pair, 0) + 1
    
    def have_played_before(self, player_id: int, opponent_id: int) -> bool:
        """
        Check if two players have faced each other before.
        
        Args:
            player_id: ID of first player
            opponent_id: ID of second player
            
        Returns:
            True if players have faced each other, False otherwise
        """
        return opponent_id in self.player_opponents.get(player_id, set())
    
    def get_opponent_count(self, player_id: int) -> int:
        """
        Get number of unique opponents a player has faced.
        
        Args:
            player_id: Player ID
            
        Returns:
            Number of unique opponents
        """
        return len(self.player_opponents.get(player_id, set()))
    
    def get_player_opponents(self, player_id: int) -> Set[int]:
        """
        Get all opponents a player has faced.
        
        Args:
            player_id: Player ID
            
        Returns:
            Set of opponent player IDs
        """
        return self.player_opponents.get(player_id, set()).copy()
    
    def record_round(self, tables: List[List[Dict]]):
        """
        Record an entire round of tables.
        
        Args:
            tables: List of tables, each containing 4 players
        """
        for table in tables:
            # Record all pairings at this table
            for i in range(len(table)):
                for j in range(i + 1, len(table)):
                    player1_id = table[i]['Player ID']
                    player2_id = table[j]['Player ID']
                    self.record_matchup(player1_id, player2_id)
        
        # Store round history
        self.round_history.append(tables)
    
    def get_statistics(self) -> Dict:
        """
        Get pairing statistics for analysis.
        
        Returns:
            Dictionary with pairing statistics
        """
        # Count total unique matchups (each pair counted once)
        total_unique_matchups = len(self.matchup_counts)
        
        # Count total matchups including repeats
        total_matchups_with_repeats = sum(self.matchup_counts.values())
        
        # Count how many pairs have met more than once
        repeat_pairs = sum(1 for count in self.matchup_counts.values() if count > 1)
        
        # Count total excess matchups (repeats beyond the first meeting)
        repeat_matchups = sum(count - 1 for count in self.matchup_counts.values() if count > 1)
        
        return {
            'total_players': len(self.player_opponents),
            'total_matchups': total_matchups_with_repeats,
            'unique_matchups': total_unique_matchups,
            'rounds_played': len(self.round_history),
            'repeat_matchups': repeat_matchups,
            'repeat_pairs': repeat_pairs
        }


class DynamicSwissPairing:
    """
    Dynamic Swiss pairing system with performance-based team pairing
    and intelligent player assignment.
    
    This class implements true Swiss pairing where:
    - Round 1: Random team pairings
    - Round 2+: Winners vs winners, losers vs losers
    - Player assignment optimized to avoid repeat matchups
    """
    
    def __init__(self, teams: Dict[str, List[Dict]], tournament_teams: List[str], 
                 swiss_rounds_count: int = 4):
        """
        Initialize the dynamic Swiss pairing system.
        
        Args:
            teams: Dictionary mapping team names to lists of 4 players
            tournament_teams: List of team names participating (8 or 16)
            swiss_rounds_count: Number of Swiss rounds (3 or 4)
        """
        self.teams = teams
        self.tournament_teams = tournament_teams
        self.swiss_rounds_count = swiss_rounds_count
        
        # Team standings tracking
        self.team_scores: Dict[str, int] = {team: 0 for team in tournament_teams}
        self.team_records: Dict[str, Tuple[int, int]] = {team: (0, 0) for team in tournament_teams}
        self.round_team_scores: Dict[int, Dict[str, int]] = {}
        
        # Player tracking
        self.player_tracker = PlayerPairingTracker()
        
        # Round storage
        self.generated_rounds: Dict[int, List[List[Dict]]] = {}
        
        print(f"[INIT] Dynamic Swiss Pairing initialized")
        print(f"       Teams: {len(tournament_teams)} ({tournament_teams})")
        print(f"       Players per team: 4")
        print(f"       Total players: {len(tournament_teams) * 4}")
        print(f"       Swiss rounds: {swiss_rounds_count}")
    
    def generate_round_pairing(self, round_num: int, 
                              previous_round_results: Optional[Dict[str, int]] = None) -> List[List[Dict]]:
        """
        Generate pairings for a specific round.
        
        Args:
            round_num: Round number (1-4)
            previous_round_results: Team scores from previous round (None for Round 1)
            
        Returns:
            List of tables, each containing 4 players from different teams
        """
        print(f"\n{'='*70}")
        print(f"Generating Round {round_num} Pairings")
        print(f"{'='*70}")
        
        if round_num == 1:
            # Round 1: Random team pairings
            print("Round 1: Using random team pairings")
            tables = self._generate_round_1_pairings()
        else:
            # Round 2+: Performance-based team pairings
            print(f"Round {round_num}: Using performance-based team pairings")
            
            # Update standings from previous round
            if previous_round_results:
                self._update_standings(round_num - 1, previous_round_results)
            
            tables = self._generate_performance_based_pairings(round_num)
        
        # Store generated round
        self.generated_rounds[round_num] = tables
        
        # Display pairing summary
        self._display_pairing_summary(round_num, tables)
        
        return tables
    
    def _generate_round_1_pairings(self) -> List[List[Dict]]:
        """
        Generate Round 1 pairings with random team assignment.
        
        Returns:
            List of tables with optimized player assignments
        """
        # Shuffle teams randomly
        shuffled_teams = self.tournament_teams.copy()
        random.shuffle(shuffled_teams)
        
        # Create pods of 4 teams each
        num_teams = len(shuffled_teams)
        pods_per_round = num_teams // 4
        
        all_tables = []
        
        for pod_idx in range(pods_per_round):
            # Get 4 teams for this pod
            start_idx = pod_idx * 4
            pod_teams = shuffled_teams[start_idx:start_idx + 4]
            
            print(f"  Pod {pod_idx + 1}: {', '.join(pod_teams)}")
            
            # Assign players to 4 tables (one from each team)
            pod_tables = self._assign_players_to_tables(pod_teams, is_round_1=True)
            all_tables.extend(pod_tables)
        
        return all_tables
    
    def _generate_performance_based_pairings(self, round_num: int) -> List[List[Dict]]:
        """
        Generate pairings based on current standings (winners vs winners).
        
        Args:
            round_num: Current round number
            
        Returns:
            List of tables with optimized player assignments
        """
        # Group teams by performance
        brackets = self._group_teams_by_performance()
        
        print(f"\n  Current Standings:")
        for record, teams in sorted(brackets.items(), reverse=True):
            wins, losses = record
            team_info = [f"{t} ({self.team_scores[t]}pts)" for t in teams]
            print(f"    {wins}-{losses}: {', '.join(team_info)}")
        
        # Create pairings within brackets
        all_tables = []
        remaining_teams = []
        
        # Process each bracket
        for record in sorted(brackets.keys(), reverse=True):
            bracket_teams = brackets[record].copy()
            remaining_teams.extend(bracket_teams)
            
            # When we have 4+ teams, create a pod
            while len(remaining_teams) >= 4:
                # Take next 4 teams
                pod_teams = remaining_teams[:4]
                remaining_teams = remaining_teams[4:]
                
                print(f"\n  Pairing Pod: {', '.join(pod_teams)}")
                
                # Assign players with repeat avoidance
                pod_tables = self._assign_players_to_tables(pod_teams, is_round_1=False)
                all_tables.extend(pod_tables)
        
        return all_tables
    
    def _assign_players_to_tables(self, pod_teams: List[str], 
                                  is_round_1: bool = False) -> List[List[Dict]]:
        """
        Assign players from 4 teams to 4 tables, optimizing to avoid repeat matchups.
        
        This is the KEY algorithm that provides player-level randomization
        while maintaining team-level structure.
        
        Args:
            pod_teams: List of 4 team names
            is_round_1: If True, use simple random assignment (no history yet)
            
        Returns:
            List of 4 tables, each with 4 players (one from each team)
        """
        # Get players from each team
        team_players = {team: self.teams[team].copy() for team in pod_teams}
        
        if is_round_1:
            # Round 1: Simple random shuffle for each team
            best_tables = self._simple_random_assignment(team_players)
            repeat_count = 0
        else:
            # Round 2+: Optimize to minimize repeats
            best_tables, repeat_count = self._optimized_player_assignment(team_players)
        
        if repeat_count > 0:
            print(f"    [WARNING] {repeat_count} repeat matchups (unavoidable)")
        else:
            print(f"    [OK] Perfect assignment - no repeat matchups!")
        
        return best_tables
    
    def _simple_random_assignment(self, team_players: Dict[str, List[Dict]]) -> List[List[Dict]]:
        """
        Simple random player assignment for Round 1.
        
        Args:
            team_players: Dict mapping team names to player lists
            
        Returns:
            List of 4 tables
        """
        teams = list(team_players.keys())
        
        # Shuffle each team's players
        shuffled = {team: random.sample(team_players[team], 4) for team in teams}
        
        # Create tables: table i gets player i from each team
        tables = [
            [shuffled[teams[0]][i], shuffled[teams[1]][i], 
             shuffled[teams[2]][i], shuffled[teams[3]][i]]
            for i in range(4)
        ]
        
        return tables
    
    def _optimized_player_assignment(self, team_players: Dict[str, List[Dict]]) -> Tuple[List[List[Dict]], int]:
        """
        Optimized player assignment that minimizes repeat matchups.
        
        Uses constraint satisfaction with random search to find best assignment.
        
        Args:
            team_players: Dict mapping team names to player lists
            
        Returns:
            Tuple of (best_tables, repeat_count)
        """
        teams = list(team_players.keys())
        best_tables = None
        min_repeats = float('inf')
        
        # Try multiple random arrangements to find one with minimal repeats
        max_attempts = 5000
        for attempt in range(max_attempts):
            # Create random player order for each team
            shuffled = {team: random.sample(team_players[team], 4) for team in teams}
            
            # Build tables: table i gets player i from each team
            candidate_tables = [
                [shuffled[teams[0]][i], shuffled[teams[1]][i], 
                 shuffled[teams[2]][i], shuffled[teams[3]][i]]
                for i in range(4)
            ]
            
            # Count repeat matchups
            repeat_count = self._count_repeat_matchups(candidate_tables)
            
            # Track best solution
            if repeat_count < min_repeats:
                min_repeats = repeat_count
                best_tables = candidate_tables
                
                # If found perfect assignment (no repeats), stop immediately
                if repeat_count == 0:
                    break
            
            # Progress indicator for long searches
            if (attempt + 1) % 1000 == 0:
                print(f"    Searching... attempt {attempt + 1}, best: {min_repeats} repeats")
        
        return best_tables, min_repeats
    
    def _count_repeat_matchups(self, tables: List[List[Dict]]) -> int:
        """
        Count total repeat matchups across all tables.
        
        Args:
            tables: List of tables to check
            
        Returns:
            Number of repeat matchups
        """
        repeat_count = 0
        
        for table in tables:
            # Check all pairs at this table
            for i in range(len(table)):
                for j in range(i + 1, len(table)):
                    p1_id = table[i]['Player ID']
                    p2_id = table[j]['Player ID']
                    
                    if self.player_tracker.have_played_before(p1_id, p2_id):
                        repeat_count += 1
        
        return repeat_count
    
    def _group_teams_by_performance(self) -> Dict[Tuple[int, int], List[str]]:
        """
        Group teams by their win-loss record.
        
        Returns:
            Dictionary mapping (wins, losses) to list of team names
        """
        brackets = {}
        
        for team_name in self.tournament_teams:
            record = self.team_records[team_name]
            if record not in brackets:
                brackets[record] = []
            brackets[record].append(team_name)
        
        # Sort teams within each bracket by total points (tiebreaker)
        for record in brackets:
            brackets[record].sort(key=lambda t: self.team_scores[t], reverse=True)
        
        return brackets
    
    def _update_standings(self, round_num: int, round_results: Dict[str, int]):
        """
        Update team standings after a round completes.
        
        Args:
            round_num: Completed round number
            round_results: Dict mapping team names to points earned this round
        """
        print(f"\n  Updating standings after Round {round_num}...")
        
        # Store round scores
        self.round_team_scores[round_num] = round_results
        
        # Update cumulative scores and records
        for team_name, points in round_results.items():
            # Add to cumulative score
            self.team_scores[team_name] = self.team_scores.get(team_name, 0) + points
            
            # Update win-loss record (simplified: >0 points = win)
            wins, losses = self.team_records[team_name]
            if points > 0:
                self.team_records[team_name] = (wins + 1, losses)
            else:
                self.team_records[team_name] = (wins, losses + 1)
        
        # Display updated standings
        sorted_teams = sorted(self.team_scores.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  Updated Standings:")
        for rank, (team, score) in enumerate(sorted_teams, 1):
            record = self.team_records[team]
            print(f"    {rank}. {team}: {score} points ({record[0]}-{record[1]})")
    
    def finalize_round(self, round_num: int):
        """
        Finalize a round by recording all matchups in player history.
        
        Args:
            round_num: Round number to finalize
        """
        if round_num not in self.generated_rounds:
            raise ValueError(f"Round {round_num} has not been generated yet")
        
        tables = self.generated_rounds[round_num]
        
        # Record all matchups
        self.player_tracker.record_round(tables)
        
        print(f"\n[OK] Round {round_num} finalized")
        stats = self.player_tracker.get_statistics()
        print(f"     Total matchups recorded: {stats['total_matchups']}")
        print(f"     Repeat matchups: {stats['repeat_matchups']}")
    
    def _display_pairing_summary(self, round_num: int, tables: List[List[Dict]]):
        """
        Display a summary of the generated pairings.
        
        Args:
            round_num: Round number
            tables: List of generated tables
        """
        print(f"\n{'='*70}")
        print(f"Round {round_num} Pairing Summary")
        print(f"{'='*70}")
        print(f"Total tables: {len(tables)}\n")
        
        for idx, table in enumerate(tables, 1):
            player_names = [f"{p['Player Name']} ({p['Team Name']})" for p in table]
            print(f"Table {idx}: {' vs '.join(player_names)}")
        
        print(f"{'='*70}\n")
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive tournament statistics.
        
        Returns:
            Dictionary with tournament statistics
        """
        player_stats = self.player_tracker.get_statistics()
        
        # Calculate proper repeat rate: (excess matchups / total matchups) * 100
        total_matchups = player_stats['total_matchups']
        unique_matchups = player_stats['unique_matchups']
        repeat_matchups = player_stats['repeat_matchups']
        
        # Repeat rate = (repeat matchups / total matchups) * 100
        repeat_rate = (repeat_matchups / total_matchups * 100) if total_matchups > 0 else 0
        
        return {
            'teams': len(self.tournament_teams),
            'players': len(self.tournament_teams) * 4,
            'rounds_generated': len(self.generated_rounds),
            'total_matchups': total_matchups,
            'unique_matchups': unique_matchups,
            'repeat_matchups': repeat_matchups,
            'repeat_rate': repeat_rate,
            'team_standings': sorted(self.team_scores.items(), key=lambda x: x[1], reverse=True)
        }

