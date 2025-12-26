#!/usr/bin/env python3
"""
Tournament Flow E2E Simulation (Enhanced Version)

This script has been updated to properly track players through ALL tournament phases:
- Swiss Rounds (1-4): 16 teams compete in 4 rounds of Swiss pairing
- Top 8 Cut (Round 5): Top 8 teams compete in 2 pods of 4 (16-team tournaments only)
- Finals (Round 6): Top 4 teams compete in 1 pod of 4
- Champion Declaration: Final winner is announced

Enhanced features:
- PairingValidator for Swiss pairing rule validation
- Comprehensive logging of round results
- Phase transition detection
- Champion verification
"""

import random
import time
import os
import collections
import itertools
from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeout


class PairingValidator:
    """Validates Swiss pairing rules to ensure fair competition."""
    
    def __init__(self):
        self.match_history = set()  # Stores pairs (p1, p2) sorted as tuples
        self.teammates_map = {}     # player_id -> team_name

    def record_and_validate(self, round_num, tables_data, is_swiss_round=True):
        """
        Validate pairings for a round and record them.
        
        Args:
            round_num: Current round number
            tables_data: List of tables, where each table is a list of dicts:
                         {'id': int, 'name': str, 'team': str, 'score': int/str}
            is_swiss_round: True if validating Swiss round (stricter rules)
        """
        print(f"--- Validating Round {round_num} Pairings ---")
        
        repeats_found = 0
        teammate_conflicts = 0
        
        for t_idx, table in enumerate(tables_data):
            # Extract IDs and Teams
            ids = [p['id'] for p in table]
            teams = [p['team'] for p in table if p['team']]
            
            # 1. Check Teammate Avoidance
            # In Swiss rounds (<= 4), strictly avoid teammates if possible.
            # In Top 8 (Round 5) or Finals (Round 6), it might be unavoidable/allowed.
            team_counts = collections.Counter(teams)
            for team, count in team_counts.items():
                if count > 1:
                    msg = f"WARNING: Teammate Conflict at Table {t_idx+1}: {team} has {count} players."
                    if is_swiss_round:
                        print(f"  ⚠️  {msg}")
                        teammate_conflicts += 1
                    else:
                        print(f"  ℹ️  {msg} (Acceptable in Top Cut/Finals)")

            # 2. Check Repeat Matchups & Update History
            # In a 4-player pod, check if any pair of players has been together before
            for p1, p2 in itertools.combinations(ids, 2):
                pair = tuple(sorted((p1, p2)))
                
                if pair in self.match_history:
                    msg = f"Repeat Pairing Detected: Players {p1} and {p2} were in same pod before!"
                    if is_swiss_round:
                        print(f"  ⚠️  WARNING: {msg}")
                        repeats_found += 1
                    else:
                        print(f"  ℹ️  {msg} (May be acceptable in Top Cut/Finals)")
                
                # Record for future
                self.match_history.add(pair)

        if repeats_found == 0 and teammate_conflicts == 0:
            print(f"  ✅ Round {round_num} Validation Passed: No repeats or conflicts.")
        else:
            print(f"  ⚠️  Round {round_num} Validation Completed with {repeats_found} repeats, {teammate_conflicts} teammate conflicts.")
        
        return repeats_found, teammate_conflicts


# Configuration
URL = "http://localhost:5001"
TEAMS_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "teams_16.csv"))


def detect_round_phase(page, round_num, swiss_rounds=4, has_top8=True):
    """Detect what phase of the tournament we're in."""
    if round_num <= swiss_rounds:
        return "Swiss"
    elif has_top8 and round_num == swiss_rounds + 1:
        return "Top8Cut"
    else:
        return "Finals"


def run(playwright):
    """Main test execution function."""
    browser = playwright.chromium.launch(headless=False, slow_mo=50)
    context = browser.new_context()
    page = context.new_page()

    print("="*60)
    print("MTG TOURNAMENT DASHBOARD - E2E SIMULATION")
    print("="*60)
    print(f"\nLoading {URL}...")
    page.goto(URL)
    page.wait_for_load_state("networkidle")

    # 1. Reset / Setup
    # Handle existing tournament state
    try:
        reset_btn = page.locator("text=Reset Tournament").first
        if reset_btn.is_visible(timeout=2000):
            print("Found existing tournament, resetting...")
            
            # Set up dialog handler before clicking
            page.on("dialog", lambda dialog: dialog.accept())
            reset_btn.click()
            time.sleep(2)
            page.reload()
            page.wait_for_load_state("networkidle")
    except PlaywrightTimeout:
        pass

    # 2. Load Participants
    print("\n--- Loading Participants ---")
    load_btn = page.get_by_role("button", name="Load Participants")
    if load_btn.is_visible():
        print("Clicking 'Load Participants'...")
        load_btn.click()
        time.sleep(2)
        
        # Wait for teams to appear
        try:
            expect(page.locator("#teams-grid")).not_to_be_empty(timeout=10000)
            print("✅ Participants loaded successfully")
        except PlaywrightTimeout:
            print("⚠️  Teams grid may not be visible, continuing...")

    # 3. Start Tournament
    print("\n--- Setting Up Tournament ---")
    setup_btn = page.get_by_role("button", name="Setup Tournament")
    if setup_btn.is_visible():
        setup_btn.click()
        time.sleep(3)
        print("✅ Tournament setup complete")
    else:
        print("⚠️  Setup Tournament button not visible, assuming already started.")

    # 4. Initialize Validator and tracking
    validator = PairingValidator()
    
    # Tournament configuration (for 16 teams)
    swiss_rounds_count = 4
    has_semifinals = True  # 16 teams = True
    max_rounds = 6  # 4 Swiss + Top8Cut + Finals
    
    round_num = 1
    round_results = {}
    
    # 5. Loop through Rounds until Winner
    print("\n" + "="*60)
    print("STARTING TOURNAMENT SIMULATION")
    print("="*60)
    
    while True:
        phase = detect_round_phase(page, round_num, swiss_rounds_count, has_semifinals)
        
        print(f"\n--- Round {round_num}: {phase} ---")
        
        # Verify Round Info
        try:
            stat_round = page.locator("#stat-round")
            if stat_round.is_visible():
                round_text = stat_round.inner_text()
                print(f"  Dashboard shows: Round {round_text}")
        except:
            pass
        
        # Wait for tables to appear
        try:
            page.wait_for_selector(".table-card", timeout=15000)
        except PlaywrightTimeout:
            # Check if tournament is complete
            if page.get_by_text("Tournament Complete").first.is_visible():
                print("\n🏆 Tournament Complete detected!")
                break
            if page.get_by_text("Champion:").first.is_visible():
                print("\n🏆 Champion declared!")
                break
            print(f"⚠️  No tables found for round {round_num}")
            break
        
        # Get all table cards
        table_cards = page.locator(".table-card").all()
        num_tables = len(table_cards)
        print(f"  Found {num_tables} tables to score")

        if num_tables == 0:
            print("⚠️  No tables found. Checking for completion...")
            if page.get_by_text("Champion:").first.is_visible():
                print("🏆 Champion declared!")
                break
            else:
                print("❌ Unexpected state: No tables and no champion.")
                break

        # --- PAIRING VALIDATION ---
        current_round_data = []
        for card in table_cards:
            players_data = []
            rows = card.locator(".table-player").all()
            for row in rows:
                try:
                    p_id_str = row.locator(".score-btn-win").get_attribute("data-player")
                    p_id = int(p_id_str) if p_id_str else 0
                    
                    t_name = row.locator(".table-player-team").inner_text().strip()
                    
                    players_data.append({'id': p_id, 'team': t_name})
                except Exception as e:
                    print(f"    ⚠️  Error scraping player: {e}")
            current_round_data.append(players_data)
        
        is_swiss = (phase == "Swiss")
        validator.record_and_validate(round_num, current_round_data, is_swiss)

        # --- SCORE TABLES ---
        print(f"\n  Scoring {num_tables} tables...")
        wins_this_round = 0
        draws_this_round = 0
        losses_this_round = 0
        
        for t_idx, card in enumerate(table_cards):
            # Decide scenario: 70% Decisive Win, 30% Draw
            is_win = random.random() < 0.7
            
            # Get all player rows in this table
            player_rows = card.locator(".table-player").all()
            
            if is_win and len(player_rows) > 0:
                # Pick ONE winner
                winner_idx = random.randint(0, len(player_rows) - 1)
                for i, row in enumerate(player_rows):
                    try:
                        if i == winner_idx:
                            row.locator(".score-btn-win").click()
                            wins_this_round += 1
                        else:
                            row.locator(".score-btn-loss").click()
                            losses_this_round += 1
                    except Exception as e:
                        print(f"    ⚠️  Error clicking score button: {e}")
            else:
                # Draw scenario - All draw
                for row in player_rows:
                    try:
                        row.locator(".score-btn-draw").click()
                        draws_this_round += 1
                    except Exception as e:
                        print(f"    ⚠️  Error clicking draw button: {e}")
            
            time.sleep(0.05)  # Small delay between tables
        
        round_results[round_num] = {
            'phase': phase,
            'tables': num_tables,
            'wins': wins_this_round,
            'draws': draws_this_round,
            'losses': losses_this_round
        }
        
        print(f"  Results: {wins_this_round} wins, {draws_this_round} draws, {losses_this_round} losses")

        # --- SUBMIT ROUND ---
        print("  Submitting round results...")
        submit_btn = page.get_by_role("button", name="Submit Round Results")
        
        if submit_btn.is_visible():
            submit_btn.click()
            time.sleep(3)
        else:
            print("  ⚠️  Submit button not found!")
            # Try to find any submit-like button
            alt_btn = page.locator("button:has-text('Submit')").first
            if alt_btn.is_visible():
                alt_btn.click()
                time.sleep(3)
            else:
                page.pause()  # Debug pause
        
        # --- CHECK FOR TOURNAMENT END ---
        time.sleep(2)
        
        if page.get_by_text("Tournament Complete").first.is_visible():
            print("\n" + "="*60)
            print("🏆 TOURNAMENT COMPLETED SUCCESSFULLY! 🏆")
            print("="*60)
            
            # Try to extract winner info
            try:
                toast = page.locator(".toast-success .toast-message").first
                if toast.is_visible():
                    champion_text = toast.inner_text()
                    print(f"Champion Info: {champion_text}")
            except:
                pass
            break
        
        if page.get_by_text("Champion:").first.is_visible():
            print("\n" + "="*60)
            print("🏆 CHAMPION DECLARED! 🏆")
            print("="*60)
            break
        
        # Move to next round
        round_num += 1
        
        # Safety break
        if round_num > max_rounds + 2:
            print(f"\n⚠️  Stopping after round {round_num-1} - safety limit reached.")
            break
    
    # --- FINAL SUMMARY ---
    print("\n" + "="*60)
    print("SIMULATION SUMMARY")
    print("="*60)
    print(f"Total Rounds Played: {len(round_results)}")
    for r, data in round_results.items():
        print(f"  Round {r} ({data['phase']}): {data['tables']} tables")
    
    print(f"\nEnd of Simulation")
    time.sleep(2)
    browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
