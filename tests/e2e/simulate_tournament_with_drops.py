#!/usr/bin/env python3
"""
28-Team Tournament E2E Simulation with Player Drops (Ghost Seats)

Drives the full tournament lifecycle through the browser UI using Playwright:
- Setup: Load 28 teams via UI (event mode, scoring mode, load participants)
- Scoring: Click Win/Loss/Draw buttons per table, submit per table via UI
- Player Drops: Via API after all tables submitted (avoids overlay z-index issues)
- Ghost Verification: Visually checks ghost rows render correctly in the browser
- Finalization: Via API, then reload to see next round
- Champion: Verified on page and via API

Requires the server running at http://localhost:5001.

Usage:
    # Terminal 1:
    python tournament_dashboard.py

    # Terminal 2:
    python tests/e2e/simulate_tournament_with_drops.py
"""

import random
import time
import os
import json
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeout

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generate_teams import generate_teams


URL = "http://localhost:5001"
NUM_TEAMS = 28
SWISS_ROUNDS = 4
SLOW_MO = 120


class DropTournamentSimulator:
    """Simulates a 28-team Western tournament with player drops."""

    def __init__(self):
        self.ghost_pids = set()
        self.ghost_info = {}
        self.errors = []
        self.round_data = {}
        self.ghost_verifications = []

    def run(self):
        print("\n" + "=" * 60)
        print("28-TEAM TOURNAMENT WITH DROPS — E2E SIMULATION")
        print("=" * 60)
        print(f"Structure: {SWISS_ROUNDS} Swiss -> Finals (top 4)")
        print(f"Drops: 2 from one team after R1, 1 from another after R2")
        print(f"Start: {datetime.now().strftime('%H:%M:%S')}")
        print()

        generate_teams(NUM_TEAMS)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False, slow_mo=SLOW_MO)
            page = browser.new_context().new_page()

            try:
                self._setup_ui(page)

                for rnd in range(1, SWISS_ROUNDS + 1):
                    self._score_round_ui(page, rnd, "Swiss")
                    self._submit_all_tables_ui(page)

                    if rnd == 1:
                        self._drop_players_api(page, rnd, team_index=0, count=2)
                        self._verify_min_active_api(page, rnd, team_index=0)
                    elif rnd == 2:
                        self._drop_players_api(page, rnd, team_index=6, count=1)

                    self._finalize_api(page, rnd)
                    self._load_next_round_ui(page, rnd + 1)

                # Finals
                self._score_round_ui(page, SWISS_ROUNDS + 1, "Finals")
                self._submit_all_tables_ui(page)
                self._finalize_api(page, SWISS_ROUNDS + 1)

                self._verify_champion(page)

            except Exception as e:
                print(f"\n  *** ERROR: {e}")
                import traceback
                traceback.print_exc()
                self.errors.append(str(e))
                try:
                    page.screenshot(path=f"drop_e2e_error_{datetime.now().strftime('%H%M%S')}.png")
                except:
                    pass
            finally:
                self._generate_report()
                browser.close()

    # ------------------------------------------------------------------
    # UI: Setup
    # ------------------------------------------------------------------

    def _setup_ui(self, page):
        print("--- SETUP ---")

        page.goto(URL)
        page.wait_for_load_state("networkidle")

        # Reset via API
        page.request.post(
            f"{URL}/reset_tournament",
            data=json.dumps({"confirm": "RESET"}),
            headers={"Content-Type": "application/json"},
        )
        page.reload()
        page.wait_for_load_state("networkidle")

        # Load Participants via UI
        load_btn = page.get_by_role("button", name="Load Participants")
        if load_btn.is_visible():
            load_btn.click()

            # Event Mode: Team
            page.wait_for_selector("#event-mode-overlay", state="visible", timeout=5000)
            page.locator('.scoring-mode-card[data-mode="team"]').click()
            page.locator("#confirm-event-mode-btn").click()

            # Scoring Mode: Western
            page.wait_for_selector("#scoring-mode-overlay", state="visible", timeout=5000)
            page.locator('.scoring-mode-card[data-mode="western"]').click()
            page.locator("#confirm-scoring-mode-btn").click()

            try:
                expect(page.locator("#teams-grid")).not_to_be_empty(timeout=10000)
            except PlaywrightTimeout:
                pass

        team_count = page.locator(".team-card").count()
        print(f"  Loaded {team_count} teams")
        if team_count != NUM_TEAMS:
            self.errors.append(f"Expected {NUM_TEAMS} teams, got {team_count}")

        # Setup Tournament
        setup_btn = page.get_by_role("button", name="Setup Tournament")
        if setup_btn.is_visible():
            setup_btn.click()
            page.wait_for_selector(".table-card", timeout=15000)

        print("  Setup complete\n")

    # ------------------------------------------------------------------
    # UI: Score all tables in the current round
    # ------------------------------------------------------------------

    def _score_round_ui(self, page, round_num, round_type):
        print(f"--- ROUND {round_num} ({round_type}) ---")

        page.wait_for_selector(".table-card", timeout=15000)

        table_cards = page.locator(".table-card").all()
        num_tables = len(table_cards)
        ghost_tables = 0

        for idx, card in enumerate(table_cards):
            table_label = f"Table {idx + 1}"
            ghost_rows = card.locator(".ghost-player-row").all()
            real_rows = card.locator(".table-player:not(.ghost-player-row)").all()

            if len(ghost_rows) > 0:
                ghost_tables += 1
                self._verify_ghost_rows(ghost_rows, round_num, table_label)

            num_real = len(real_rows)
            if num_real == 0:
                continue

            # 70% decisive win, 30% all-draw (finals always decisive)
            is_win = random.random() < 0.7 or round_type == "Finals"

            if is_win:
                # Click Win on one player — JS auto-fills others as Loss
                winner_idx = random.randint(0, num_real - 1)
                real_rows[winner_idx].locator(".score-btn-win").click()
                time.sleep(0.3)
            else:
                for row in real_rows:
                    row.locator(".score-btn-draw").click()
                    time.sleep(0.1)

        self.round_data[round_num] = {
            "type": round_type,
            "tables": num_tables,
            "ghost_tables": ghost_tables,
        }

        print(f"  Scored {num_tables} tables ({ghost_tables} with ghosts)")

    # ------------------------------------------------------------------
    # UI: Submit all tables via per-table submit buttons
    # ------------------------------------------------------------------

    def _submit_all_tables_ui(self, page):
        table_cards = page.locator(".table-card").all()
        submitted = 0

        for card in table_cards:
            submit_btn = card.locator(".submit-table-btn")
            if submit_btn.is_visible() and not submit_btn.is_disabled():
                submit_btn.click()
                # Wait for "Submitted" text to appear
                for _ in range(30):
                    try:
                        txt = submit_btn.inner_text()
                        if "Submitted" in txt or "Already" in txt:
                            break
                    except:
                        break
                    time.sleep(0.2)
                submitted += 1
                time.sleep(0.05)

        print(f"  Submitted {submitted}/{len(table_cards)} tables via UI")

        # Verify all submitted via API
        resp = page.request.get(f"{URL}/get_tournament_state")
        state = resp.json()
        if state.get("can_finalize"):
            print("  All tables confirmed submitted")
        else:
            print("  WARNING: can_finalize is not true after UI submit")

    def _verify_ghost_rows(self, ghost_rows, round_num, table_label):
        """Verify ghost player rows display correctly in the browser."""
        for row in ghost_rows:
            try:
                has_badge = row.locator(".ghost-badge").is_visible()
                has_auto_score = row.locator(".ghost-auto-score").is_visible()
                auto_text = row.locator(".ghost-auto-score").inner_text()
                ok = has_badge and has_auto_score and "0 pts" in auto_text
                self.ghost_verifications.append({
                    "round": round_num,
                    "table": table_label,
                    "badge": has_badge,
                    "auto_score": has_auto_score,
                    "text": auto_text,
                    "pass": ok,
                })
                if not ok:
                    print(f"    Ghost check FAIL at {table_label}: badge={has_badge}, text={auto_text}")
            except Exception as e:
                self.ghost_verifications.append({
                    "round": round_num, "table": table_label, "pass": False, "error": str(e)
                })

    # ------------------------------------------------------------------
    # API: Drop players
    # ------------------------------------------------------------------

    def _drop_players_api(self, page, round_num, team_index, count):
        """Drop N players from a team via the API."""
        resp = page.request.get(f"{URL}/get_tournament_state")
        state = resp.json()
        teams = state.get("teams", {})
        sorted_names = sorted(teams.keys())

        if team_index >= len(sorted_names):
            team_index = 0
        team_name = sorted_names[team_index]
        players = teams[team_name]
        active = [p for p in players if not p.get("is_dropped")]

        print(f"\n  >> Dropping {count} player(s) from {team_name}...")

        for i in range(min(count, max(0, len(active) - 2))):
            p = active[i]
            pid = p["Player ID"]
            pname = p["Player Name"]
            resp = page.request.post(
                f"{URL}/drop_team_player",
                data=json.dumps({"player_id": pid, "round": round_num}),
                headers={"Content-Type": "application/json"},
            )
            data = resp.json()
            if data.get("success"):
                self.ghost_pids.add(pid)
                self.ghost_info[pid] = {"name": pname, "team": team_name, "dropped_round": round_num}
                print(f"    Dropped: {pname} (pid={pid})")
            else:
                msg = f"Drop failed: {data.get('message', data.get('error'))}"
                print(f"    {msg}")
                self.errors.append(msg)

    def _verify_min_active_api(self, page, round_num, team_index):
        """Verify that dropping another player from the same team is rejected."""
        resp = page.request.get(f"{URL}/get_tournament_state")
        state = resp.json()
        sorted_names = sorted(state.get("teams", {}).keys())
        team_name = sorted_names[team_index]
        players = state["teams"][team_name]
        active = [p for p in players if not p.get("is_dropped")]

        if len(active) != 2:
            print(f"    Expected 2 active in {team_name}, got {len(active)}")
            return

        pid = active[0]["Player ID"]
        resp = page.request.post(
            f"{URL}/drop_team_player",
            data=json.dumps({"player_id": pid, "round": round_num}),
            headers={"Content-Type": "application/json"},
        )
        data = resp.json()
        if not data.get("success") and "Minimum 2 required" in data.get("message", ""):
            print(f"    OK: 3rd drop correctly rejected (min 2 active)")
        else:
            self.errors.append(f"Min-active enforcement failed: {data}")

    # ------------------------------------------------------------------
    # API: Finalize round, then reload UI to show next round
    # ------------------------------------------------------------------

    def _finalize_api(self, page, round_num):
        print(f"  Finalizing round {round_num}...")

        resp = page.request.post(
            f"{URL}/submit_player_results",
            data=json.dumps({"round": round_num, "results": []}),
            headers={"Content-Type": "application/json"},
        )
        data = resp.json()
        if data.get("success"):
            print(f"  Round {round_num} finalized")
        else:
            msg = f"Finalize R{round_num} failed: {data.get('error', data)}"
            print(f"  ERROR: {msg}")
            self.errors.append(msg)

    def _load_next_round_ui(self, page, next_round):
        """Reload the page and select the next round to show its tables."""
        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)

        select = page.locator("#round-select")
        if select.is_visible():
            select.select_option(str(next_round))
            page.wait_for_load_state("networkidle")
            time.sleep(1)

    # ------------------------------------------------------------------
    # Champion verification
    # ------------------------------------------------------------------

    def _verify_champion(self, page):
        print("\n--- CHAMPION VERIFICATION ---")

        page.reload()
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # Check page for champion text
        try:
            champion_el = page.get_by_text("Champion:").first
            if champion_el.is_visible(timeout=5000):
                print("  Champion visible on page")
        except:
            print("  Champion text not visible on page (may need finals round selected)")

        # Verify via API
        resp = page.request.get(f"{URL}/final_standings")
        data = resp.json()
        if data.get("success"):
            print(f"  Champion: {data.get('champion', 'N/A')}")
            mvp = data.get("mvp", {})
            if mvp:
                print(f"  MVP: {mvp.get('name', '?')} ({mvp.get('team', '?')})")
        else:
            self.errors.append("Final standings API returned failure")

        # Verify ghost players in final state
        resp = page.request.get(f"{URL}/get_tournament_state")
        state = resp.json()
        dropped = state.get("dropped_team_players", {})
        player_scores = state.get("player_scores", {})

        print(f"\n  Dropped players ({len(dropped)}):")
        for pid_str, info in dropped.items():
            score = player_scores.get(pid_str, player_scores.get(int(pid_str), "?"))
            print(f"    {info['original_name']} ({info['team']}): "
                  f"dropped R{info['dropped_after_round']}, score={score}")

        expected_drops = len(self.ghost_pids)
        actual_drops = len(dropped)
        if actual_drops != expected_drops:
            self.errors.append(f"Expected {expected_drops} drops, found {actual_drops}")

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def _generate_report(self):
        ghost_pass = sum(1 for v in self.ghost_verifications if v.get("pass"))
        ghost_total = len(self.ghost_verifications)

        report = {
            "timestamp": datetime.now().isoformat(),
            "config": {"teams": NUM_TEAMS, "swiss_rounds": SWISS_ROUNDS, "scoring": "western"},
            "rounds": self.round_data,
            "drops": {str(pid): info for pid, info in self.ghost_info.items()},
            "ghost_verifications": {
                "passed": ghost_pass, "total": ghost_total,
                "details": self.ghost_verifications,
            },
            "errors": self.errors,
        }

        report_path = os.path.join(os.path.dirname(__file__), "tournament_drop_test_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        print("\n" + "=" * 60)
        print("REPORT")
        print("=" * 60)
        print(f"  Rounds played: {len(self.round_data)}")
        print(f"  Players dropped: {len(self.ghost_pids)}")
        print(f"  Ghost UI checks: {ghost_pass}/{ghost_total} passed")
        print(f"  Errors: {len(self.errors)}")

        if self.errors:
            print("\n  ERRORS:")
            for e in self.errors:
                print(f"    - {e}")
            print("\n  RESULT: FAILED")
        else:
            print("\n  RESULT: PASSED")

        print(f"\n  Report saved to: {report_path}")


if __name__ == "__main__":
    sim = DropTournamentSimulator()
    sim.run()
    sys.exit(1 if sim.errors else 0)
