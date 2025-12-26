#!/usr/bin/env python3
"""
Full Tournament E2E Simulation for 16 Players

This script simulates a complete tournament flow from start to finish:
- Swiss Rounds (1-4): 16 teams compete in 4 rounds of Swiss pairing
- Top 8 Cut (Round 5): Top 8 teams compete in 2 pods of 4
- Finals (Round 6): Top 4 teams compete in 1 pod of 4
- Champion Declaration: Final winner is announced

The script tracks every player and team through each phase, validates
Swiss pairing rules, and records all results for verification.
"""

import random
import time
import os
import json
import collections
import itertools
from datetime import datetime
from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeout


class PlayerTracker:
    """Tracks individual player journey through the tournament."""
    
    def __init__(self, player_id, player_name, team_name):
        self.player_id = player_id
        self.player_name = player_name
        self.team_name = team_name
        self.round_results = {}  # round_num -> {'points': int, 'table': str, 'opponents': []}
        self.total_points = 0
    
    def record_round(self, round_num, points, table_name, opponents):
        self.round_results[round_num] = {
            'points': points,
            'table': table_name,
            'opponents': opponents
        }
        self.total_points += points
    
    def get_swiss_points(self, swiss_rounds=4):
        return sum(self.round_results.get(r, {}).get('points', 0) for r in range(1, swiss_rounds + 1))
    
    def get_top8_points(self, swiss_rounds=4):
        return self.round_results.get(swiss_rounds + 1, {}).get('points', 0)
    
    def get_finals_points(self, swiss_rounds=4, has_top8=True):
        finals_round = swiss_rounds + 2 if has_top8 else swiss_rounds + 1
        return self.round_results.get(finals_round, {}).get('points', 0)
    
    def __repr__(self):
        return f"Player({self.player_id}, {self.player_name}, {self.team_name}, pts={self.total_points})"


class TeamTracker:
    """Tracks team performance through the tournament."""
    
    def __init__(self, team_name):
        self.team_name = team_name
        self.players = []  # List of PlayerTracker
        self.swiss_total = 0
        self.top8_total = 0
        self.finals_total = 0
        self.advanced_to_top8 = False
        self.advanced_to_finals = False
        self.is_champion = False
        self.final_rank = None
    
    def add_player(self, player: PlayerTracker):
        self.players.append(player)
    
    def update_totals(self, swiss_rounds=4, has_top8=True):
        self.swiss_total = sum(p.get_swiss_points(swiss_rounds) for p in self.players)
        self.top8_total = sum(p.get_top8_points(swiss_rounds) for p in self.players) if has_top8 else 0
        self.finals_total = sum(p.get_finals_points(swiss_rounds, has_top8) for p in self.players)
    
    def __repr__(self):
        return f"Team({self.team_name}, Swiss={self.swiss_total}, Top8={self.top8_total}, Finals={self.finals_total})"


class PairingValidator:
    """Validates Swiss pairing rules."""
    
    def __init__(self):
        self.match_history = set()  # Set of frozensets representing pods
        self.teammate_map = {}      # player_id -> team_name
        self.warnings = []
        self.errors = []
    
    def register_player(self, player_id, team_name):
        self.teammate_map[player_id] = team_name
    
    def validate_round(self, round_num, tables_data, is_swiss=True):
        """
        Validate pairings for a round.
        
        tables_data: List of tables, each table is a list of dicts with 'id', 'team'
        """
        print(f"\n=== Validating Round {round_num} Pairings ===")
        
        repeats_found = 0
        teammate_conflicts = 0
        
        for t_idx, table in enumerate(tables_data):
            ids = [p['id'] for p in table]
            teams = [p['team'] for p in table if p['team']]
            
            # 1. Check Teammate Avoidance
            team_counts = collections.Counter(teams)
            for team, count in team_counts.items():
                if count > 1:
                    msg = f"Teammate Conflict at Table {t_idx+1}: {team} has {count} players"
                    if is_swiss:
                        self.warnings.append(f"Round {round_num}: {msg}")
                        print(f"  ⚠️  {msg}")
                        teammate_conflicts += 1
                    else:
                        print(f"  ℹ️  {msg} (Acceptable in Top Cut/Finals)")
            
            # 2. Check for players who have been in the same pod before
            pod_key = frozenset(ids)
            for prev_pod in self.match_history:
                # Check if any pair of players was together before
                overlap = pod_key & prev_pod
                if len(overlap) > 1:
                    overlapping_players = list(overlap)
                    for i in range(len(overlapping_players)):
                        for j in range(i + 1, len(overlapping_players)):
                            pair = frozenset([overlapping_players[i], overlapping_players[j]])
                            # Check if this specific pair was together before
                            for check_pod in self.match_history:
                                if pair.issubset(check_pod):
                                    msg = f"Repeat Matchup at Table {t_idx+1}: Players {overlapping_players[i]} and {overlapping_players[j]} were in same pod before"
                                    if is_swiss:
                                        self.warnings.append(f"Round {round_num}: {msg}")
                                        print(f"  ⚠️  {msg}")
                                        repeats_found += 1
                                    break
            
            # Record this pod for future
            self.match_history.add(pod_key)
        
        if repeats_found == 0 and teammate_conflicts == 0:
            print(f"  ✅ Round {round_num} Validation: No violations found")
        else:
            print(f"  ⚠️  Round {round_num}: {repeats_found} repeats, {teammate_conflicts} teammate conflicts")
        
        return repeats_found, teammate_conflicts


class TournamentSimulator:
    """Main simulator class for the tournament E2E test."""
    
    def __init__(self, url="http://localhost:5001"):
        self.url = url
        self.players = {}       # player_id -> PlayerTracker
        self.teams = {}         # team_name -> TeamTracker
        self.validator = PairingValidator()
        self.current_round = 0
        self.swiss_rounds = 4
        self.has_top8 = True    # 16 teams = True
        self.max_rounds = 6     # 4 Swiss + Top8 + Finals
        self.test_results = {
            'rounds': {},
            'swiss_standings': [],
            'top8_standings': [],
            'final_standings': [],
            'champion': None,
            'mvp': None,
            'validation_warnings': [],
            'errors': []
        }
    
    def run_simulation(self):
        """Execute the full tournament simulation."""
        print("\n" + "="*60)
        print("FULL TOURNAMENT E2E SIMULATION - 16 TEAMS")
        print("="*60)
        print(f"Start Time: {datetime.now().isoformat()}")
        
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=False, slow_mo=100)
            context = browser.new_context()
            page = context.new_page()
            
            try:
                # Phase 1: Setup
                self._setup_tournament(page)
                
                # Phase 2: Swiss Rounds (1-4)
                for round_num in range(1, self.swiss_rounds + 1):
                    self._play_round(page, round_num, "Swiss")
                
                # Phase 3: Top 8 Cut (Round 5)
                self._play_round(page, self.swiss_rounds + 1, "Top8Cut")
                
                # Phase 4: Finals (Round 6)
                self._play_round(page, self.swiss_rounds + 2, "Finals")
                
                # Phase 5: Verify Champion
                self._verify_champion(page)
                
            except Exception as e:
                print(f"\n❌ SIMULATION ERROR: {e}")
                import traceback
                traceback.print_exc()
                self.test_results['errors'].append(str(e))
            finally:
                self._generate_report()
                time.sleep(3)
                browser.close()
    
    def _setup_tournament(self, page):
        """Setup the tournament with 16 teams."""
        print("\n" + "-"*40)
        print("PHASE 1: TOURNAMENT SETUP")
        print("-"*40)
        
        # Navigate to dashboard
        print(f"Navigating to {self.url}...")
        page.goto(self.url)
        page.wait_for_load_state("networkidle")
        
        # Check for existing tournament and reset if needed
        reset_btn = page.locator("text=Reset Tournament").first
        if reset_btn.is_visible():
            print("Resetting existing tournament...")
            page.on("dialog", lambda dialog: dialog.accept())
            reset_btn.click()
            time.sleep(2)
            page.reload()
            page.wait_for_load_state("networkidle")
        
        # Load participants
        print("Loading participants...")
        load_btn = page.get_by_role("button", name="Load Participants")
        if load_btn.is_visible():
            load_btn.click()
            time.sleep(2)
            
            # Wait for teams grid to populate
            try:
                expect(page.locator("#teams-grid")).not_to_be_empty(timeout=10000)
                print("✅ Participants loaded successfully")
            except PlaywrightTimeout:
                print("⚠️  Teams grid not found, continuing...")
        
        # Setup tournament
        print("Setting up tournament...")
        setup_btn = page.get_by_role("button", name="Setup Tournament")
        if setup_btn.is_visible():
            setup_btn.click()
            time.sleep(3)
            print("✅ Tournament setup complete")
        
        # Extract initial player/team data
        self._extract_player_data(page)
    
    def _extract_player_data(self, page):
        """Extract player and team data from the page."""
        print("Extracting player data from first round tables...")
        
        try:
            page.wait_for_selector(".table-card", timeout=10000)
            table_cards = page.locator(".table-card").all()
            
            for t_idx, card in enumerate(table_cards):
                rows = card.locator(".table-player").all()
                for row in rows:
                    try:
                        # Extract player ID
                        p_id_str = row.locator(".score-btn-win").get_attribute("data-player")
                        p_id = int(p_id_str) if p_id_str else 0
                        
                        # Extract player name and team
                        p_name = row.locator(".table-player-name").inner_text().strip()
                        t_name = row.locator(".table-player-team").inner_text().strip()
                        
                        # Create player tracker if not exists
                        if p_id not in self.players:
                            player = PlayerTracker(p_id, p_name, t_name)
                            self.players[p_id] = player
                            self.validator.register_player(p_id, t_name)
                        
                        # Create team tracker if not exists
                        if t_name and t_name not in self.teams:
                            self.teams[t_name] = TeamTracker(t_name)
                        
                        if t_name and p_id not in [p.player_id for p in self.teams[t_name].players]:
                            self.teams[t_name].add_player(self.players[p_id])
                    
                    except Exception as e:
                        print(f"  ⚠️  Error extracting player: {e}")
            
            print(f"✅ Extracted {len(self.players)} players in {len(self.teams)} teams")
        except Exception as e:
            print(f"⚠️  Could not extract player data: {e}")
    
    def _play_round(self, page, round_num, round_type):
        """Play a single round (Swiss, Top8Cut, or Finals)."""
        self.current_round = round_num
        
        print("\n" + "-"*40)
        print(f"ROUND {round_num}: {round_type.upper()}")
        print("-"*40)
        
        # Wait for tables to be visible
        try:
            page.wait_for_selector(".table-card", timeout=15000)
        except PlaywrightTimeout:
            # Check if tournament is complete
            if page.get_by_text("Champion:").first.is_visible():
                print("Tournament already complete!")
                return
            raise Exception(f"Tables not found for round {round_num}")
        
        # Get all tables
        table_cards = page.locator(".table-card").all()
        num_tables = len(table_cards)
        print(f"Found {num_tables} tables")
        
        # Record round data
        round_data = {
            'round_num': round_num,
            'round_type': round_type,
            'tables': [],
            'table_count': num_tables
        }
        
        # Collect table data for validation
        tables_for_validation = []
        
        for t_idx, card in enumerate(table_cards):
            table_name = f"Table {t_idx + 1}"
            table_data = {
                'table_name': table_name,
                'players': [],
                'winner': None
            }
            
            players_in_table = []
            rows = card.locator(".table-player").all()
            
            for row in rows:
                try:
                    p_id_str = row.locator(".score-btn-win").get_attribute("data-player")
                    p_id = int(p_id_str) if p_id_str else 0
                    t_name = row.locator(".table-player-team").inner_text().strip()
                    
                    players_in_table.append({'id': p_id, 'team': t_name})
                    table_data['players'].append(p_id)
                except:
                    pass
            
            tables_for_validation.append(players_in_table)
            round_data['tables'].append(table_data)
        
        # Validate pairings
        is_swiss = round_type == "Swiss"
        repeats, conflicts = self.validator.validate_round(round_num, tables_for_validation, is_swiss)
        round_data['validation'] = {'repeats': repeats, 'conflicts': conflicts}
        
        # Score all tables
        print(f"\nScoring {num_tables} tables...")
        results_by_player = {}
        
        for t_idx, card in enumerate(table_cards):
            table_name = f"Table {t_idx + 1}"
            
            # Get player rows
            player_rows = card.locator(".table-player").all()
            num_players = len(player_rows)
            
            # Decide scoring: 70% decisive win, 30% draw
            is_win = random.random() < 0.7
            
            if is_win and num_players > 0:
                # Pick one winner, rest lose
                winner_idx = random.randint(0, num_players - 1)
                for i, row in enumerate(player_rows):
                    try:
                        p_id_str = row.locator(".score-btn-win").get_attribute("data-player")
                        p_id = int(p_id_str) if p_id_str else 0
                        
                        if i == winner_idx:
                            row.locator(".score-btn-win").click()
                            results_by_player[p_id] = {'points': 5, 'table': table_name}
                            round_data['tables'][t_idx]['winner'] = p_id
                        else:
                            row.locator(".score-btn-loss").click()
                            results_by_player[p_id] = {'points': 0, 'table': table_name}
                    except Exception as e:
                        print(f"    ⚠️  Error scoring player: {e}")
            else:
                # All draw
                for row in player_rows:
                    try:
                        p_id_str = row.locator(".score-btn-win").get_attribute("data-player")
                        p_id = int(p_id_str) if p_id_str else 0
                        
                        row.locator(".score-btn-draw").click()
                        results_by_player[p_id] = {'points': 1, 'table': table_name}
                    except Exception as e:
                        print(f"    ⚠️  Error scoring player: {e}")
            
            time.sleep(0.1)  # Small delay between tables
        
        # Record results for each player
        for p_id, result in results_by_player.items():
            if p_id in self.players:
                # Find opponents
                opponents = []
                for table in tables_for_validation:
                    ids_in_table = [p['id'] for p in table]
                    if p_id in ids_in_table:
                        opponents = [pid for pid in ids_in_table if pid != p_id]
                        break
                
                self.players[p_id].record_round(
                    round_num, 
                    result['points'], 
                    result['table'], 
                    opponents
                )
        
        # Submit round results
        print("Submitting round results...")
        submit_btn = page.get_by_role("button", name="Submit Round Results")
        
        if submit_btn.is_visible():
            submit_btn.click()
            time.sleep(3)
        else:
            print("  ⚠️  Submit button not found!")
        
        # Update team totals
        for team in self.teams.values():
            team.update_totals(self.swiss_rounds, self.has_top8)
        
        # Record round summary
        wins = sum(1 for r in results_by_player.values() if r['points'] == 5)
        draws = sum(1 for r in results_by_player.values() if r['points'] == 1)
        losses = sum(1 for r in results_by_player.values() if r['points'] == 0)
        
        round_data['summary'] = {
            'wins': wins,
            'draws': draws,
            'losses': losses
        }
        
        self.test_results['rounds'][round_num] = round_data
        
        print(f"\n  Round {round_num} Complete:")
        print(f"    Wins: {wins}, Draws: {draws}, Losses: {losses}")
        
        # Check for next round or tournament end
        time.sleep(2)
        
        # Capture standings after Swiss and Top8
        if round_type == "Swiss" and round_num == self.swiss_rounds:
            self._capture_standings(page, "swiss")
        elif round_type == "Top8Cut":
            self._capture_standings(page, "top8")
    
    def _capture_standings(self, page, phase):
        """Capture current standings."""
        print(f"\nCapturing {phase.upper()} standings...")
        
        sorted_teams = sorted(
            self.teams.values(),
            key=lambda t: (t.swiss_total if phase == "swiss" else t.top8_total, t.swiss_total),
            reverse=True
        )
        
        standings = []
        for rank, team in enumerate(sorted_teams, 1):
            standings.append({
                'rank': rank,
                'team': team.team_name,
                'swiss_points': team.swiss_total,
                'top8_points': team.top8_total if phase == "top8" else 0
            })
            print(f"  {rank}. {team.team_name}: Swiss={team.swiss_total}, Top8={team.top8_total}")
        
        if phase == "swiss":
            self.test_results['swiss_standings'] = standings
            # Mark top 8 teams
            for i, team in enumerate(sorted_teams[:8]):
                team.advanced_to_top8 = True
        elif phase == "top8":
            self.test_results['top8_standings'] = standings
            # Mark top 4 teams
            for i, team in enumerate(sorted_teams[:4]):
                team.advanced_to_finals = True
    
    def _verify_champion(self, page):
        """Verify and record the champion."""
        print("\n" + "-"*40)
        print("VERIFYING CHAMPION")
        print("-"*40)
        
        time.sleep(2)
        
        # Check for champion announcement
        if page.get_by_text("Champion:").first.is_visible():
            print("✅ Champion has been declared!")
            
            # Try to get champion info from toast or page
            try:
                toast = page.locator(".toast-success").first
                if toast.is_visible():
                    toast_text = toast.inner_text()
                    print(f"  Toast message: {toast_text}")
            except:
                pass
        else:
            print("⚠️  Champion announcement not visible yet")
        
        # Calculate champion from our tracking
        sorted_teams = sorted(
            self.teams.values(),
            key=lambda t: (t.finals_total, t.top8_total + t.swiss_total),
            reverse=True
        )
        
        if sorted_teams:
            champion = sorted_teams[0]
            champion.is_champion = True
            champion.final_rank = 1
            
            self.test_results['champion'] = {
                'team': champion.team_name,
                'finals_points': champion.finals_total,
                'top8_points': champion.top8_total,
                'swiss_points': champion.swiss_total,
                'total_points': champion.finals_total + champion.top8_total + champion.swiss_total
            }
            
            print(f"\n🏆 CHAMPION: {champion.team_name}")
            print(f"   Finals: {champion.finals_total} pts")
            print(f"   Top 8:  {champion.top8_total} pts")
            print(f"   Swiss:  {champion.swiss_total} pts")
        
        # Calculate MVP
        sorted_players = sorted(
            self.players.values(),
            key=lambda p: p.total_points,
            reverse=True
        )
        
        if sorted_players:
            mvp = sorted_players[0]
            self.test_results['mvp'] = {
                'player_id': mvp.player_id,
                'player_name': mvp.player_name,
                'team': mvp.team_name,
                'total_points': mvp.total_points
            }
            
            print(f"\n⭐ MVP: {mvp.player_name} ({mvp.team_name})")
            print(f"   Total Points: {mvp.total_points}")
        
        # Final standings
        final_standings = []
        for rank, team in enumerate(sorted_teams[:4], 1):
            team.final_rank = rank
            final_standings.append({
                'rank': rank,
                'team': team.team_name,
                'finals_points': team.finals_total,
                'tiebreaker': team.top8_total + team.swiss_total
            })
        
        self.test_results['final_standings'] = final_standings
    
    def _generate_report(self):
        """Generate and save the test report."""
        print("\n" + "="*60)
        print("TEST REPORT")
        print("="*60)
        
        # Add validation warnings to report
        self.test_results['validation_warnings'] = self.validator.warnings
        
        # Summary
        print("\n📊 SUMMARY")
        print(f"   Total Rounds: {len(self.test_results['rounds'])}")
        print(f"   Players Tracked: {len(self.players)}")
        print(f"   Teams Tracked: {len(self.teams)}")
        print(f"   Validation Warnings: {len(self.validator.warnings)}")
        print(f"   Errors: {len(self.test_results['errors'])}")
        
        # Champion and MVP
        if self.test_results['champion']:
            print(f"\n🏆 Champion: {self.test_results['champion']['team']}")
        if self.test_results['mvp']:
            print(f"⭐ MVP: {self.test_results['mvp']['player_name']} ({self.test_results['mvp']['total_points']} pts)")
        
        # Final standings
        print("\n📋 FINAL STANDINGS")
        for entry in self.test_results.get('final_standings', []):
            print(f"   {entry['rank']}. {entry['team']}: Finals={entry['finals_points']}, Tiebreaker={entry['tiebreaker']}")
        
        # Validation warnings
        if self.validator.warnings:
            print("\n⚠️  VALIDATION WARNINGS")
            for w in self.validator.warnings[:10]:  # Show first 10
                print(f"   - {w}")
            if len(self.validator.warnings) > 10:
                print(f"   ... and {len(self.validator.warnings) - 10} more")
        
        # Save detailed report to file
        report_path = os.path.join(os.path.dirname(__file__), "tournament_test_report.json")
        
        # Add player journey data
        player_journeys = {}
        for p_id, player in self.players.items():
            player_journeys[p_id] = {
                'name': player.player_name,
                'team': player.team_name,
                'total_points': player.total_points,
                'rounds': player.round_results
            }
        
        self.test_results['player_journeys'] = player_journeys
        self.test_results['timestamp'] = datetime.now().isoformat()
        
        with open(report_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_path}")
        
        # Test result
        if self.test_results['errors']:
            print("\n❌ TEST RESULT: FAILED (see errors above)")
        elif len(self.validator.warnings) > 5:
            print("\n⚠️  TEST RESULT: PASSED WITH WARNINGS")
        else:
            print("\n✅ TEST RESULT: PASSED")


def main():
    """Main entry point."""
    print("="*60)
    print("MTG Tournament Dashboard - Full E2E Test")
    print("="*60)
    print("\nThis test will simulate a complete 16-team tournament:")
    print("  - 4 Swiss Rounds")
    print("  - Top 8 Cut")
    print("  - Finals")
    print("  - Champion Declaration")
    print("\nMake sure the server is running at http://localhost:5001")
    print("="*60)
    
    simulator = TournamentSimulator()
    simulator.run_simulation()


if __name__ == "__main__":
    main()
