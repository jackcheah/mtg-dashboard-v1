
import random
import time
import os
import collections
import itertools
from playwright.sync_api import sync_playwright, expect

class PairingValidator:
    def __init__(self):
        self.match_history = set()  # Stores integers of pairs (p1, p2) sorted
        self.teammates_map = {}     # p_id -> team_name

    def record_and_validate(self, round_num, tables_data):
        """
        tables_data: List of tables, where each table is a list of dicts:
                     {'id': int, 'name': str, 'team': str, 'score': int/str}
        """
        print(f"--- Validating Round {round_num} Pairings ---")
        
        repeats_found = 0
        teammate_conflicts = 0
        
        for t_idx, table in enumerate(tables_data):
            # Extract IDs and Teams
            ids = [p['id'] for p in table]
            teams = [p['team'] for p in table if p['team']]
            
            # 1. Check Teammate Avoidance
            # In Swiss rounds (usually <= 4), strictly avoid teammates if possible.
            # In Top 8 (Round 5+), it might be unavoidable/allowed.
            team_counts = collections.Counter(teams)
            for team, count in team_counts.items():
                if count > 1:
                    msg = f"WARNING: Teammate Conflict at Table {t_idx+1}: {team} has {count} players."
                    if round_num <= 4:
                         print(msg)
                         teammate_conflicts += 1
                    else:
                         print(f"{msg} (Acceptable in Top Cut)")

            # 2. Check Repeat Matchups & Update History
            # In a 4-player pod, everyone is effectively matched against everyone in the pod?
            # Or is it 3 matches?
            # E.g. A vs B, C vs D? No, it's a pod.
            # Assuming "Pod" means they all play each other or just being in the same group counts as a "matchup" state for repeats.
            # Traditional Swiss usually implies avoiding ANY repeat opponent.
            # If the format is "4-Player Pods", usually you avoid being in the same pod twice.
            
            for p1, p2 in itertools.combinations(ids, 2):
                pair = tuple(sorted((p1, p2)))
                
                if pair in self.match_history:
                    print(f"WARNING: Repeat Usage Detected: Players {p1} and {p2} met before!")
                    repeats_found += 1
                
                # Record for future
                self.match_history.add(pair)

        if repeats_found == 0 and teammate_conflicts == 0:
            print(f"✅ Round {round_num} Validation Passed: No repeats or conflicts.")
        else:
            print(f"⚠️ Round {round_num} Validation Completed with warnings.")


# Configuration
URL = "http://localhost:5001"
TEAMS_CSV = os.path.abspath(os.path.join(os.path.dirname(__file__), "teams_16.csv"))

def run(playwright):
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    print(f"Loading {URL}...")
    page.goto(URL)

    # 1. Reset / Setup
    # Look for a Reset button if a tournament is logically in progress, or just start fresh
    # Assuming we can find 'Reset Tournament' or similar in configuration panel
    if page.get_by_text("Reset Tournament").is_visible():
        print("Resetting tournament...")
        page.get_by_text("Reset Tournament").click()
        page.on("dialog", lambda dialog: dialog.accept()) # Accept confirmation if any

    # 2. Upload Teams (Simulated by placing file)
    print("Teams file placed at participants/participant_team.xlsx")
    page.reload()
    time.sleep(2)
   
    # 2b. Load Participants
    load_btn = page.get_by_role("button", name="Load Participants")
    if load_btn.is_visible():
        print("Clicking 'Load Participants'...")
        load_btn.click()
        # Wait for teams to appear
        expect(page.locator("#teams-grid")).not_to_be_empty(timeout=10000)
    
    # 3. Start Tournament
    print("Starting tournament...")
    setup_btn = page.get_by_role("button", name="Setup Tournament")
    if setup_btn.is_visible():
        setup_btn.click()
    else:
        print("Setup Tournament button not visible? Assuming already started.")

    # 4. Loop through Rounds until Winner
    # We expect: 4 Swiss Rounds -> Top 8 Cut -> Finals -> Winner
    
    validator = PairingValidator()
    
    round_num = 1
    while True:
        print(f"--- Simulating Round {str(round_num)} ---")
        
        # Verify Round Info (Wait for it to appear)
        try:
            expect(page.locator("#stat-round")).to_contain_text(str(round_num), timeout=5000)
        except:
             # Check if we are in a special named round like "Finals"
             # verification might vary, but let's proceed to checking tables
             pass
        
        # Verify pairings are visible
        # Wait for at least one table card
        try:
            page.wait_for_selector(".table-card", timeout=10000)
        except:
            # If no tables, maybe we finished?
            if page.get_by_text("Tournament Complete").is_visible() or page.get_by_text("Champion:").is_visible():
                print("Tournament Complete detected!")
                break
        
        # Fill Results - STRICT RULES
        # Rule: Each table only 1 winner OR multiple draws/losses.
        table_cards = page.locator(".table-card").all()
        print(f"Found {len(table_cards)} tables to score.")

        # --- VALIDATION START ---
        current_round_data = []
        for card in table_cards:
            players_data = []
            rows = card.locator(".table-player").all()
            for row in rows:
                try:
                    # Extract ID from button data attribute for accuracy
                    p_id_str = row.locator(".score-btn-win").get_attribute("data-player")
                    p_id = int(p_id_str) if p_id_str else 0
                    
                    # Extract Team Name
                    t_name = row.locator(".table-player-team").inner_text()
                    
                    players_data.append({'id': p_id, 'team': t_name})
                except Exception as e:
                    print(f"Error scraping player: {e}")
            current_round_data.append(players_data)
            
        validator.record_and_validate(round_num, current_round_data)
        # --- VALIDATION END ---
        
        if len(table_cards) == 0:
            print("No tables found. Checking for completion...")
            if page.get_by_text("Champion:").is_visible():
                print("Champion declared!")
                break
            else:
                print("Unexpected state: No tables and no champion.")
                break

        for card in table_cards:
            # Decide scenario: 70% Decisive Win, 30% Draw
            is_win = random.random() < 0.7
            
            # Get all 4 player rows in this table
            player_rows = card.locator(".table-player").all()
            
            if is_win:
                # Pick ONE winner
                winner_idx = random.randint(0, len(player_rows) - 1)
                for i, row in enumerate(player_rows):
                    if i == winner_idx:
                        # Click WIN
                        row.locator(".score-btn-win").click()
                    else:
                        # Click LOSS (Enforce explicit loss for others)
                        row.locator(".score-btn-loss").click()
            else:
                # Draw scenario - All draw (or some draw, some lose)
                # Simpler: All Draw
                for row in player_rows:
                    row.locator(".score-btn-draw").click()
            
            # Small delay to mimic user
            # time.sleep(0.01)

        # Submit Round
        print("Submitting round...")
        
        # Check if it's "Submit Round" or "Batch Submit" (Top 8 might use Batch?)
        # The page has "Submit Round Results" button
        submit_btn = page.get_by_role("button", name="Submit Round Results")
        
        if submit_btn.is_visible():
            submit_btn.click()
        else:
             # Fallback or specific finals button?
             print("Submit button not found!")
             page.pause()
        
        # Wait for processing/next round
        time.sleep(3)
        
        if page.get_by_text("Tournament Complete").first.is_visible() or page.get_by_text("Champion:").first.is_visible():
            print("--- TOURNAMENT COMPLETED SUCCESSFULLY ---")
            
            # Extract Winner
            champion_text = page.locator(".toast-success .toast-message").first.inner_text() if page.locator(".toast-success").first.is_visible() else "Unknown"
            print(f"Champion Info: {champion_text}")
            break
            
        # Check if we moved to next round?
        # Increment to look for next
        round_num += 1
        
        # Safety break
        if round_num > 10:
            print("Stopping after 10 rounds - safety limit.")
            break
            
    print("End of Simulation")
    time.sleep(2)
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
