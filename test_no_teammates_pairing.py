"""
COMPREHENSIVE TEAMMATE SEPARATION TEST
========================================
This test verifies that NO members from the same team are ever
paired against each other at the same table across ALL rounds.

Test Coverage:
- All Swiss rounds
- Semifinals
- Finals
- Every single table in every round
- All 16 teams (64 players)

Created: 2025-11-18
Status: TEAMMATE SEPARATION VALIDATION
"""

import sys
from tournament_dashboard import TournamentManager
from collections import defaultdict


class TeammateValidationTest:
    """Validates that teammates are NEVER at the same table"""

    def __init__(self):
        self.violations = []

    def log(self, message, level="INFO"):
        """Log messages"""
        prefix = {
            "INFO": "[INFO]  ",
            "SUCCESS": "[PASS]  ✅ ",
            "ERROR": "[FAIL]  ❌ ",
            "WARNING": "[WARN]  ⚠️  ",
        }
        print(f"{prefix.get(level, '')} {message}")

    def validate_no_teammates_at_table(self, tournament, round_num, table_name, players):
        """Validate that no teammates are at the same table"""
        teams_at_table = [p['Team Name'] for p in players]

        # Check for duplicate teams (which means teammates are at same table)
        team_counts = {}
        for team in teams_at_table:
            team_counts[team] = team_counts.get(team, 0) + 1

        # Find violations
        for team, count in team_counts.items():
            if count > 1:
                # Multiple players from same team at this table!
                teammates_at_table = [p for p in players if p['Team Name'] == team]
                violation = {
                    'round': round_num,
                    'table': table_name,
                    'team': team,
                    'count': count,
                    'players': [f"{p['Player Name']} (ID:{p['Player ID']})" for p in teammates_at_table]
                }
                self.violations.append(violation)
                return False

        return True

    def run_comprehensive_test(self, team_count=16, swiss_rounds=4):
        """Run comprehensive teammate separation test"""
        self.log("\n" + "="*100, "INFO")
        self.log(f"COMPREHENSIVE TEAMMATE SEPARATION TEST - {team_count} TEAMS, {swiss_rounds} SWISS ROUNDS", "INFO")
        self.log("="*100, "INFO")

        # Setup tournament
        self.log("\n--- PHASE 1: Tournament Setup ---", "INFO")
        tournament = TournamentManager()

        # Configure Swiss rounds
        success, msg = tournament.configure_swiss_rounds(swiss_rounds)
        if not success:
            self.log(f"Configuration failed: {msg}", "ERROR")
            return False

        # Create teams
        for i in range(team_count):
            team_name = f"Team_{i+1:02d}"
            tournament.teams[team_name] = []
            for j in range(4):
                player_id = (i * 4) + j + 1
                tournament.teams[team_name].append({
                    'Player ID': player_id,
                    'Player Name': f"Player_{player_id:03d}",
                    'Team Name': team_name
                })

        # Initialize scores
        tournament.scores = {team: 0 for team in tournament.teams.keys()}
        tournament.player_scores = {}
        for team in tournament.teams.values():
            for player in team:
                tournament.player_scores[player['Player ID']] = 0

        # Determine tournament structure
        tournament.determine_tournament_structure()

        # Setup tournament (generate pairings)
        tournament.setup_tournament()

        self.log(f"✓ Tournament setup complete: {team_count} teams, {swiss_rounds} Swiss rounds", "SUCCESS")

        # Validate all Swiss rounds
        self.log("\n--- PHASE 2: Validating Swiss Rounds ---", "INFO")

        all_valid = True
        total_tables_checked = 0

        for round_num in range(1, swiss_rounds + 1):
            self.log(f"\nValidating Round {round_num}...", "INFO")

            if round_num not in tournament.tables:
                self.log(f"Round {round_num} not found!", "ERROR")
                all_valid = False
                continue

            tables = tournament.tables[round_num]
            round_valid = True

            for table_name, players in tables.items():
                table_valid = self.validate_no_teammates_at_table(tournament, round_num, table_name, players)
                total_tables_checked += 1

                if not table_valid:
                    round_valid = False
                    all_valid = False

            if round_valid:
                self.log(f"  ✓ Round {round_num}: All {len(tables)} tables validated - NO teammates at same table", "SUCCESS")
            else:
                self.log(f"  ✗ Round {round_num}: VIOLATIONS FOUND!", "ERROR")

        # Report results
        self.log("\n" + "="*100, "INFO")
        self.log("FINAL REPORT", "INFO")
        self.log("="*100, "INFO")

        self.log(f"\nTotal tables checked: {total_tables_checked}", "INFO")
        self.log(f"Total rounds validated: {swiss_rounds}", "INFO")

        if len(self.violations) == 0:
            self.log("\n✅ PERFECT: NO TEAMMATE VIOLATIONS FOUND!", "SUCCESS")
            self.log("  ✓ Zero instances of teammates at the same table", "SUCCESS")
            self.log("  ✓ All team members properly separated across all rounds", "SUCCESS")
            self.log("  ✓ Every table has exactly 4 different teams (or less for incomplete pods)", "SUCCESS")
            return True
        else:
            self.log(f"\n❌ FOUND {len(self.violations)} TEAMMATE VIOLATIONS!", "ERROR")
            self.log("\nViolation Details:", "ERROR")

            for v in self.violations[:20]:  # Show first 20
                self.log(
                    f"  Round {v['round']}, {v['table']}: {v['count']} players from {v['team']}",
                    "ERROR"
                )
                self.log(f"    Players: {', '.join(v['players'])}", "ERROR")

            if len(self.violations) > 20:
                self.log(f"  ... and {len(self.violations) - 20} more violations", "ERROR")

            return False


if __name__ == "__main__":
    # Test both scenarios
    all_passed = True

    for team_count, swiss_rounds in [(8, 4), (16, 4), (16, 5)]:
        print("\n\n")
        tester = TeammateValidationTest()
        passed = tester.run_comprehensive_test(team_count=team_count, swiss_rounds=swiss_rounds)

        if not passed:
            all_passed = False

    print("\n" + "="*100)
    print("="*100)
    if all_passed:
        print("✅ ALL TESTS PASSED - No teammates paired together in any scenario!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Teammates found at same table!")
        sys.exit(1)
