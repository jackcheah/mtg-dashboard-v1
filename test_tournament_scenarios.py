"""
Comprehensive Tournament Test Suite
Tests all tournament scenarios:
- 8 teams with 4 Swiss rounds
- 8 teams with 5 Swiss rounds
- 16 teams with 4 Swiss rounds
- 16 teams with 5 Swiss rounds

Validates:
- Tournament structure determination
- Round generation
- Semifinals logic
- Finals logic
- Score tracking
- Round advancement
"""

import sys
import json
from tournament_dashboard import TournamentManager

class TournamentTester:
    def __init__(self):
        self.test_results = []
        self.current_test = None
        
    def log(self, message, level="INFO"):
        """Log test messages"""
        prefix = {
            "INFO": "[INFO] ",
            "SUCCESS": "[PASS] ",
            "ERROR": "[FAIL] ",
            "WARNING": "[WARN] "
        }
        try:
            print(f"{prefix.get(level, '')} {message}")
        except UnicodeEncodeError:
            # Fallback for systems that don't support Unicode
            print(f"{prefix.get(level, '')} {message}".encode('ascii', 'ignore').decode('ascii'))
        
    def assert_equal(self, actual, expected, message):
        """Assert equality and log result"""
        if actual == expected:
            self.log(f"PASS: {message} (expected: {expected}, got: {actual})", "SUCCESS")
            return True
        else:
            self.log(f"FAIL: {message} (expected: {expected}, got: {actual})", "ERROR")
            self.test_results.append({
                "test": self.current_test,
                "message": message,
                "expected": expected,
                "actual": actual,
                "status": "FAIL"
            })
            return False
            
    def assert_true(self, condition, message):
        """Assert condition is true"""
        if condition:
            self.log(f"PASS: {message}", "SUCCESS")
            return True
        else:
            self.log(f"FAIL: {message}", "ERROR")
            self.test_results.append({
                "test": self.current_test,
                "message": message,
                "status": "FAIL"
            })
            return False
    
    def create_test_teams(self, count):
        """Create test teams with players"""
        teams = []
        for i in range(count):
            team_name = f"Team_{i+1:02d}"
            players = []
            for j in range(4):
                player_id = (i * 4) + j + 1
                players.append({
                    "Player ID": player_id,
                    "Player Name": f"Player_{player_id:02d}",
                    "Team Name": team_name
                })
            teams.append({
                "name": team_name,
                "players": players
            })
        return teams
    
    def validate_no_repeat_matchups(self, tournament, swiss_rounds_count):
        """
        CRITICAL VALIDATION: Ensure no player faces the same opponent twice in Swiss rounds
        This is the most important constraint for Swiss pairing
        """
        self.log(f"\n{'='*60}", "INFO")
        self.log("CRITICAL VALIDATION: Checking for repeat matchups in Swiss rounds", "WARNING")
        self.log(f"{'='*60}", "INFO")

        # Track all matchups for each player
        player_matchups = {}  # player_id -> set of opponent player_ids
        violations = []

        # Go through all Swiss rounds
        for round_num in range(1, swiss_rounds_count + 1):
            tables = tournament.tables.get(round_num, {})
            self.log(f"\nRound {round_num}: Checking {len(tables)} tables", "INFO")

            for table_name, players_list in tables.items():
                # Get all player IDs at this table
                player_ids = [p.get('Player ID', p.get('id')) for p in players_list]

                # For each player, check if they've faced any opponent before
                for i, player_id in enumerate(player_ids):
                    if player_id not in player_matchups:
                        player_matchups[player_id] = set()

                    # Check against all other players at this table
                    for j, opponent_id in enumerate(player_ids):
                        if i != j:  # Don't compare player with themselves
                            # Check if this matchup already exists
                            if opponent_id in player_matchups[player_id]:
                                violation = {
                                    'round': round_num,
                                    'table': table_name,
                                    'player_id': player_id,
                                    'opponent_id': opponent_id
                                }
                                violations.append(violation)
                                self.log(
                                    f"❌ VIOLATION: Player {player_id} faces Player {opponent_id} "
                                    f"again in Round {round_num} at {table_name}!",
                                    "ERROR"
                                )
                            else:
                                # Record this matchup
                                player_matchups[player_id].add(opponent_id)

        # Report results
        self.log(f"\n{'='*60}", "INFO")
        if len(violations) == 0:
            self.log("✅ PERFECT: No repeat matchups found in Swiss rounds!", "SUCCESS")
            self.log(f"Total unique matchups tracked: {sum(len(opponents) for opponents in player_matchups.values())}", "INFO")
            return True
        else:
            self.log(f"❌ CRITICAL FAILURE: Found {len(violations)} repeat matchup violations!", "ERROR")
            for v in violations[:10]:  # Show first 10 violations
                self.log(
                    f"  - Round {v['round']}, {v['table']}: "
                    f"Player {v['player_id']} vs Player {v['opponent_id']}",
                    "ERROR"
                )
            if len(violations) > 10:
                self.log(f"  ... and {len(violations) - 10} more violations", "ERROR")

            self.test_results.append({
                "test": self.current_test,
                "message": "Repeat matchup validation",
                "violations": len(violations),
                "status": "FAIL"
            })
            return False

    def simulate_round_results(self, tournament, round_num, tables):
        """Simulate random results for a round"""
        import random
        results = {}

        # tables is a dictionary where keys are table names and values are lists of players
        for table_name, players_list in tables.items():
            # Assign random points (0-3) to each player
            points = [3, 2, 1, 0]  # 1st, 2nd, 3rd, 4th place
            random.shuffle(points)

            table_results = {}
            for idx, player in enumerate(players_list):
                player_id = player.get('Player ID', player.get('id'))
                table_results[player_id] = points[idx]

            results[table_name] = table_results

        return results
    
    def test_8_teams_4_rounds(self):
        """Test: 8 teams, 4 Swiss rounds, no semifinals"""
        self.current_test = "8 Teams - 4 Swiss Rounds"
        self.log(f"\n{'='*60}", "INFO")
        self.log(f"TEST: {self.current_test}", "INFO")
        self.log(f"{'='*60}", "INFO")
        
        # Create tournament
        tournament = TournamentManager()
        
        # Configure Swiss rounds
        success, msg = tournament.configure_swiss_rounds(4)
        self.assert_true(success, "Configure 4 Swiss rounds")
        
        # Load 8 teams
        teams = self.create_test_teams(8)
        tournament.teams = {}
        tournament.participants = []
        for team in teams:
            tournament.teams[team['name']] = team['players']
            tournament.participants.extend(team['players'])
        
        # Determine structure
        tournament.determine_tournament_structure()
        
        # Validate structure
        self.assert_equal(tournament.has_semifinals, False, "No semifinals for 8 teams")
        self.assert_equal(tournament.max_rounds, 5, "Total rounds = 5 (4 Swiss + 1 Finals)")
        self.assert_equal(len(tournament.teams), 8, "8 teams loaded")
        
        # Setup tournament
        tournament.setup_tournament()
        
        # Validate Swiss rounds generated
        swiss_rounds_count = len([r for r in tournament.tables.keys() if r <= 4])
        self.assert_equal(swiss_rounds_count, 4, "4 Swiss rounds generated")
        
        # Simulate Swiss rounds
        for round_num in range(1, 5):
            self.log(f"\n--- Simulating Swiss Round {round_num} ---", "INFO")
            tables = tournament.tables.get(round_num, [])
            self.assert_equal(len(tables), 8, f"Round {round_num} has 8 tables")

            # Simulate results
            results = self.simulate_round_results(tournament, round_num, tables)

            # Submit results
            for table_num, table_results in results.items():
                for player_id, points in table_results.items():
                    tournament.player_scores[player_id] = tournament.player_scores.get(player_id, 0) + points

        # CRITICAL: Validate no repeat matchups in Swiss rounds
        self.assert_true(
            self.validate_no_repeat_matchups(tournament, 4),
            "No player faces same opponent twice in Swiss rounds"
        )

        # After round 4, finals should be generated
        self.log("\n--- Checking Finals Generation ---", "INFO")
        finals_data = tournament.generate_unified_finals(after_semifinals=False)
        
        self.assert_true(finals_data is not None, "Finals generated after Swiss rounds")
        self.assert_true(5 in tournament.tables, "Finals round (5) exists")
        
        finals_tables = tournament.tables.get(5, [])
        self.assert_equal(len(finals_tables), 4, "Finals has 4 tables (top 4 teams)")
        
        self.log(f"\n✅ TEST PASSED: {self.current_test}", "SUCCESS")
        return True
    
    def test_8_teams_5_rounds(self):
        """Test: 8 teams, 5 Swiss rounds, no semifinals"""
        self.current_test = "8 Teams - 5 Swiss Rounds"
        self.log(f"\n{'='*60}", "INFO")
        self.log(f"TEST: {self.current_test}", "INFO")
        self.log(f"{'='*60}", "INFO")
        
        # Create tournament
        tournament = TournamentManager()
        
        # Configure Swiss rounds
        success, msg = tournament.configure_swiss_rounds(5)
        self.assert_true(success, "Configure 5 Swiss rounds")
        
        # Load 8 teams
        teams = self.create_test_teams(8)
        tournament.teams = {}
        tournament.participants = []
        for team in teams:
            tournament.teams[team['name']] = team['players']
            tournament.participants.extend(team['players'])
        
        # Determine structure
        tournament.determine_tournament_structure()
        
        # Validate structure
        self.assert_equal(tournament.has_semifinals, False, "No semifinals for 8 teams")
        self.assert_equal(tournament.max_rounds, 6, "Total rounds = 6 (5 Swiss + 1 Finals)")
        
        # Setup tournament
        tournament.setup_tournament()
        
        # Validate Swiss rounds generated
        swiss_rounds_count = len([r for r in tournament.tables.keys() if r <= 5])
        self.assert_equal(swiss_rounds_count, 5, "5 Swiss rounds generated")
        
        # Simulate Swiss rounds
        for round_num in range(1, 6):
            self.log(f"\n--- Simulating Swiss Round {round_num} ---", "INFO")
            tables = tournament.tables.get(round_num, [])
            self.assert_equal(len(tables), 8, f"Round {round_num} has 8 tables")

            # Simulate results
            results = self.simulate_round_results(tournament, round_num, tables)

            # Submit results
            for table_num, table_results in results.items():
                for player_id, points in table_results.items():
                    tournament.player_scores[player_id] = tournament.player_scores.get(player_id, 0) + points

        # CRITICAL: Validate no repeat matchups in Swiss rounds
        self.assert_true(
            self.validate_no_repeat_matchups(tournament, 5),
            "No player faces same opponent twice in Swiss rounds"
        )

        # After round 5, finals should be generated
        self.log("\n--- Checking Finals Generation ---", "INFO")
        finals_data = tournament.generate_unified_finals(after_semifinals=False)
        
        self.assert_true(finals_data is not None, "Finals generated after Swiss rounds")
        self.assert_true(6 in tournament.tables, "Finals round (6) exists")
        
        finals_tables = tournament.tables.get(6, [])
        self.assert_equal(len(finals_tables), 4, "Finals has 4 tables (top 4 teams)")
        
        self.log(f"\n✅ TEST PASSED: {self.current_test}", "SUCCESS")
        return True
    
    def test_16_teams_4_rounds(self):
        """Test: 16 teams, 4 Swiss rounds, with semifinals"""
        self.current_test = "16 Teams - 4 Swiss Rounds"
        self.log(f"\n{'='*60}", "INFO")
        self.log(f"TEST: {self.current_test}", "INFO")
        self.log(f"{'='*60}", "INFO")
        
        # Create tournament
        tournament = TournamentManager()
        
        # Configure Swiss rounds
        success, msg = tournament.configure_swiss_rounds(4)
        self.assert_true(success, "Configure 4 Swiss rounds")
        
        # Load 16 teams
        teams = self.create_test_teams(16)
        tournament.teams = {}
        tournament.participants = []
        for team in teams:
            tournament.teams[team['name']] = team['players']
            tournament.participants.extend(team['players'])
        
        # Determine structure
        tournament.determine_tournament_structure()
        
        # Validate structure
        self.assert_equal(tournament.has_semifinals, True, "Semifinals enabled for 16 teams")
        self.assert_equal(tournament.max_rounds, 6, "Total rounds = 6 (4 Swiss + 1 Semifinals + 1 Finals)")
        self.assert_equal(len(tournament.teams), 16, "16 teams loaded")
        
        # Setup tournament
        tournament.setup_tournament()
        
        # Validate Swiss rounds generated
        swiss_rounds_count = len([r for r in tournament.tables.keys() if r <= 4])
        self.assert_equal(swiss_rounds_count, 4, "4 Swiss rounds generated")
        
        # Simulate Swiss rounds
        for round_num in range(1, 5):
            self.log(f"\n--- Simulating Swiss Round {round_num} ---", "INFO")
            tables = tournament.tables.get(round_num, [])
            self.assert_equal(len(tables), 16, f"Round {round_num} has 16 tables")

            # Simulate results
            results = self.simulate_round_results(tournament, round_num, tables)

            # Submit results
            for table_num, table_results in results.items():
                for player_id, points in table_results.items():
                    tournament.player_scores[player_id] = tournament.player_scores.get(player_id, 0) + points

        # CRITICAL: Validate no repeat matchups in Swiss rounds
        self.assert_true(
            self.validate_no_repeat_matchups(tournament, 4),
            "No player faces same opponent twice in Swiss rounds"
        )

        # After round 4, semifinals should be generated
        self.log("\n--- Checking Semifinals Generation ---", "INFO")
        semifinals_data = tournament.generate_semifinals_round()
        
        self.assert_true(semifinals_data is not None, "Semifinals generated after Swiss rounds")
        self.assert_true(5 in tournament.tables, "Semifinals round (5) exists")
        
        semifinals_tables = tournament.tables.get(5, [])
        self.assert_equal(len(semifinals_tables), 8, "Semifinals has 8 tables (top 8 teams)")
        
        # Simulate semifinals
        self.log("\n--- Simulating Semifinals ---", "INFO")
        results = self.simulate_round_results(tournament, 5, semifinals_tables)
        for table_num, table_results in results.items():
            for player_id, points in table_results.items():
                tournament.player_scores[player_id] = tournament.player_scores.get(player_id, 0) + points
        
        # After semifinals, finals should be generated
        self.log("\n--- Checking Finals Generation ---", "INFO")
        finals_data = tournament.generate_unified_finals(after_semifinals=True)
        
        self.assert_true(finals_data is not None, "Finals generated after Semifinals")
        self.assert_true(6 in tournament.tables, "Finals round (6) exists")
        
        finals_tables = tournament.tables.get(6, [])
        self.assert_equal(len(finals_tables), 4, "Finals has 4 tables (top 4 teams)")
        
        self.log(f"\n✅ TEST PASSED: {self.current_test}", "SUCCESS")
        return True

    def test_16_teams_5_rounds(self):
        """Test: 16 teams, 5 Swiss rounds, with semifinals"""
        self.current_test = "16 Teams - 5 Swiss Rounds"
        self.log(f"\n{'='*60}", "INFO")
        self.log(f"TEST: {self.current_test}", "INFO")
        self.log(f"{'='*60}", "INFO")

        # Create tournament
        tournament = TournamentManager()

        # Configure Swiss rounds
        success, msg = tournament.configure_swiss_rounds(5)
        self.assert_true(success, "Configure 5 Swiss rounds")

        # Load 16 teams
        teams = self.create_test_teams(16)
        tournament.teams = {}
        tournament.participants = []
        for team in teams:
            tournament.teams[team['name']] = team['players']
            tournament.participants.extend(team['players'])

        # Determine structure
        tournament.determine_tournament_structure()

        # Validate structure
        self.assert_equal(tournament.has_semifinals, True, "Semifinals enabled for 16 teams")
        self.assert_equal(tournament.max_rounds, 7, "Total rounds = 7 (5 Swiss + 1 Semifinals + 1 Finals)")
        self.assert_equal(len(tournament.teams), 16, "16 teams loaded")

        # Setup tournament
        tournament.setup_tournament()

        # Validate Swiss rounds generated
        swiss_rounds_count = len([r for r in tournament.tables.keys() if r <= 5])
        self.assert_equal(swiss_rounds_count, 5, "5 Swiss rounds generated")

        # Simulate Swiss rounds
        for round_num in range(1, 6):
            self.log(f"\n--- Simulating Swiss Round {round_num} ---", "INFO")
            tables = tournament.tables.get(round_num, [])
            self.assert_equal(len(tables), 16, f"Round {round_num} has 16 tables")

            # Simulate results
            results = self.simulate_round_results(tournament, round_num, tables)

            # Submit results
            for table_num, table_results in results.items():
                for player_id, points in table_results.items():
                    tournament.player_scores[player_id] = tournament.player_scores.get(player_id, 0) + points

        # CRITICAL: Validate no repeat matchups in Swiss rounds
        self.assert_true(
            self.validate_no_repeat_matchups(tournament, 5),
            "No player faces same opponent twice in Swiss rounds"
        )

        # After round 5, semifinals should be generated
        self.log("\n--- Checking Semifinals Generation ---", "INFO")
        semifinals_data = tournament.generate_semifinals_round()

        self.assert_true(semifinals_data is not None, "Semifinals generated after Swiss rounds")
        self.assert_true(6 in tournament.tables, "Semifinals round (6) exists")

        semifinals_tables = tournament.tables.get(6, [])
        self.assert_equal(len(semifinals_tables), 8, "Semifinals has 8 tables (top 8 teams)")

        # Simulate semifinals
        self.log("\n--- Simulating Semifinals ---", "INFO")
        results = self.simulate_round_results(tournament, 6, semifinals_tables)
        for table_num, table_results in results.items():
            for player_id, points in table_results.items():
                tournament.player_scores[player_id] = tournament.player_scores.get(player_id, 0) + points

        # After semifinals, finals should be generated
        self.log("\n--- Checking Finals Generation ---", "INFO")
        finals_data = tournament.generate_unified_finals(after_semifinals=True)

        self.assert_true(finals_data is not None, "Finals generated after Semifinals")
        self.assert_true(7 in tournament.tables, "Finals round (7) exists")

        finals_tables = tournament.tables.get(7, [])
        self.assert_equal(len(finals_tables), 4, "Finals has 4 tables (top 4 teams)")

        self.log(f"\n✅ TEST PASSED: {self.current_test}", "SUCCESS")
        return True

    def run_all_tests(self):
        """Run all test scenarios"""
        self.log("\n" + "="*60, "INFO")
        self.log("COMPREHENSIVE TOURNAMENT TEST SUITE", "INFO")
        self.log("="*60, "INFO")

        tests = [
            self.test_8_teams_4_rounds,
            self.test_8_teams_5_rounds,
            self.test_16_teams_4_rounds,
            self.test_16_teams_5_rounds
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"EXCEPTION in {test.__name__}: {str(e)}", "ERROR")
                failed += 1
                import traceback
                traceback.print_exc()

        # Print summary
        self.log("\n" + "="*60, "INFO")
        self.log("TEST SUMMARY", "INFO")
        self.log("="*60, "INFO")
        self.log(f"Total Tests: {passed + failed}", "INFO")
        self.log(f"Passed: {passed}", "SUCCESS")
        self.log(f"Failed: {failed}", "ERROR" if failed > 0 else "INFO")

        if self.test_results:
            self.log("\n--- Failed Assertions ---", "ERROR")
            for result in self.test_results:
                self.log(f"Test: {result['test']}", "ERROR")
                self.log(f"  {result['message']}", "ERROR")
                if 'expected' in result:
                    self.log(f"  Expected: {result['expected']}, Got: {result['actual']}", "ERROR")

        return failed == 0


if __name__ == "__main__":
    tester = TournamentTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
