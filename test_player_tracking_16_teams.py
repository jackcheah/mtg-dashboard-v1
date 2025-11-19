"""
COMPREHENSIVE PLAYER TRACKING TEST - 16 TEAMS (64 PLAYERS)
============================================================
This test tracks EVERY SINGLE PLAYER across all Swiss rounds and validates:
1. Each player is tracked individually (all 64 players)
2. Each player's opponents are recorded every round
3. NO player faces the same opponent twice in Swiss rounds
4. Teams do not play each other more than once in Swiss rounds

Test Coverage:
- 16 teams (64 players total)
- All Swiss rounds (4 or 5)
- Individual player matchup history
- Team matchup history
- Zero repeat matchups validation

Created: 2025-11-18
Status: COMPREHENSIVE PLAYER & TEAM MATCHUP TRACKING
"""

import sys
import random
from tournament_dashboard import TournamentManager
from collections import defaultdict


class PlayerTrackingTest:
    """Tracks every player's opponents across all Swiss rounds"""

    def __init__(self):
        self.player_matchup_history = defaultdict(set)  # player_id -> set of opponent_ids
        self.team_matchup_history = defaultdict(set)     # team_name -> set of opponent_team_names
        self.player_details = {}  # player_id -> {name, team, round_history}
        self.violations = []
        self.round_details = {}  # round_num -> list of matchups

    def log(self, message, level="INFO"):
        """Log messages"""
        prefix = {
            "INFO": "[INFO]  ",
            "SUCCESS": "[PASS]  ✅ ",
            "ERROR": "[FAIL]  ❌ ",
            "WARNING": "[WARN]  ⚠️  ",
            "PLAYER": "[TRACK] 👤 ",
            "TEAM": "[MATCH] 🏢 "
        }
        try:
            print(f"{prefix.get(level, '')} {message}")
        except UnicodeEncodeError:
            clean_message = message.encode('ascii', 'ignore').decode('ascii')
            print(f"{prefix.get(level, '')} {clean_message}")

    def initialize_player_tracking(self, tournament):
        """Initialize tracking for all 64 players"""
        self.log("\n" + "="*80, "INFO")
        self.log("INITIALIZING PLAYER TRACKING - 16 TEAMS (64 PLAYERS)", "INFO")
        self.log("="*80, "INFO")

        player_count = 0
        for team_name, players in tournament.teams.items():
            for player in players:
                player_id = player['Player ID']
                player_name = player['Player Name']

                self.player_details[player_id] = {
                    'name': player_name,
                    'team': team_name,
                    'opponents': [],
                    'round_history': {}
                }

                self.player_matchup_history[player_id] = set()
                player_count += 1

        self.log(f"✓ Initialized tracking for {player_count} players", "SUCCESS")
        self.log(f"✓ Players organized across {len(tournament.teams)} teams", "SUCCESS")

        # Display team roster
        self.log("\n--- TEAM ROSTER ---", "INFO")
        for team_name, players in sorted(tournament.teams.items()):
            player_list = [f"{p['Player Name']} (ID:{p['Player ID']})" for p in players]
            self.log(f"  {team_name}: {', '.join(player_list)}", "TEAM")

    def track_round_matchups(self, tournament, round_num):
        """Track all player matchups for a specific round"""
        self.log(f"\n{'='*80}", "INFO")
        self.log(f"TRACKING ROUND {round_num} MATCHUPS", "PLAYER")
        self.log(f"{'='*80}", "INFO")

        tables = tournament.tables.get(round_num, {})
        round_matchups = []

        for table_name, players_list in tables.items():
            # Get player IDs and team names
            player_ids = [p.get('Player ID') for p in players_list]
            team_names = [p.get('Team Name') for p in players_list]

            self.log(f"\n{table_name}:", "INFO")

            # Track each player's opponents at this table
            for i, player_id in enumerate(player_ids):
                player_name = self.player_details[player_id]['name']
                player_team = self.player_details[player_id]['team']

                # Get opponents (all other players at this table)
                opponents = []
                for j, opponent_id in enumerate(player_ids):
                    if i != j:
                        opponent_name = self.player_details[opponent_id]['name']
                        opponent_team = self.player_details[opponent_id]['team']
                        opponents.append({
                            'id': opponent_id,
                            'name': opponent_name,
                            'team': opponent_team
                        })

                # Record round history
                self.player_details[player_id]['round_history'][round_num] = {
                    'table': table_name,
                    'opponents': opponents
                }

                # Display player matchup
                opponent_summary = ", ".join([f"{o['name']} ({o['team']})" for o in opponents])
                self.log(f"  Player {player_id} ({player_name} - {player_team}) faces:", "PLAYER")
                self.log(f"    → {opponent_summary}", "INFO")

            # Record matchup
            round_matchups.append({
                'table': table_name,
                'players': player_ids,
                'teams': team_names
            })

        self.round_details[round_num] = round_matchups
        self.log(f"\n✓ Round {round_num}: Tracked {len(tables)} tables", "SUCCESS")

    def validate_no_repeat_player_matchups(self, tournament, swiss_rounds_count):
        """Validate that NO player faces the same opponent twice"""
        self.log("\n" + "="*80, "INFO")
        self.log("VALIDATING NO REPEAT PLAYER MATCHUPS", "WARNING")
        self.log("="*80, "INFO")

        violations = []
        player_violations = defaultdict(list)

        # For each Swiss round, check all matchups
        for round_num in range(1, swiss_rounds_count + 1):
            tables = tournament.tables.get(round_num, {})

            for table_name, players_list in tables.items():
                player_ids = [p.get('Player ID') for p in players_list]

                # For each player at this table
                for i, player_id in enumerate(player_ids):
                    # Check against all opponents at this table
                    for j, opponent_id in enumerate(player_ids):
                        if i != j:
                            # Check if these players have met before
                            if opponent_id in self.player_matchup_history[player_id]:
                                violation = {
                                    'round': round_num,
                                    'table': table_name,
                                    'player_id': player_id,
                                    'player_name': self.player_details[player_id]['name'],
                                    'player_team': self.player_details[player_id]['team'],
                                    'opponent_id': opponent_id,
                                    'opponent_name': self.player_details[opponent_id]['name'],
                                    'opponent_team': self.player_details[opponent_id]['team']
                                }
                                violations.append(violation)
                                player_violations[player_id].append(violation)
                            else:
                                # Record this matchup
                                self.player_matchup_history[player_id].add(opponent_id)

        # Report violations
        if len(violations) > 0:
            self.log(f"\n❌ FOUND {len(violations)} REPEAT MATCHUP VIOLATIONS!", "ERROR")

            # Show affected players
            self.log(f"\n⚠️  Players with repeat matchups: {len(player_violations)}", "WARNING")

            for player_id, player_viols in list(player_violations.items())[:10]:  # Show first 10
                player = self.player_details[player_id]
                self.log(f"\nPlayer {player_id} ({player['name']} - {player['team']}):", "ERROR")
                for v in player_viols:
                    self.log(
                        f"  Round {v['round']}, {v['table']}: "
                        f"Faced {v['opponent_name']} ({v['opponent_team']}) AGAIN!",
                        "ERROR"
                    )

            if len(player_violations) > 10:
                self.log(f"  ... and {len(player_violations) - 10} more players", "ERROR")

            self.violations.extend(violations)
            return False
        else:
            self.log("✅ PERFECT: NO repeat matchups found!", "SUCCESS")
            self.log(f"Total unique matchups tracked: {sum(len(opponents) for opponents in self.player_matchup_history.values())}", "SUCCESS")
            return True

    def validate_no_repeat_team_matchups(self, tournament, swiss_rounds_count):
        """Validate that NO team faces another team twice ACROSS DIFFERENT ROUNDS"""
        self.log("\n" + "="*80, "INFO")
        self.log("VALIDATING NO REPEAT TEAM MATCHUPS (ACROSS ROUNDS)", "WARNING")
        self.log("="*80, "INFO")

        team_violations = []
        round_team_matchups = defaultdict(lambda: defaultdict(set))  # round -> team -> set of opponents

        # First pass: Record all matchups by round
        for round_num in range(1, swiss_rounds_count + 1):
            tables = tournament.tables.get(round_num, {})

            for table_name, players_list in tables.items():
                teams_at_table = [p.get('Team Name') for p in players_list]

                # For each team at this table
                for i, team_name in enumerate(teams_at_table):
                    # Record all opponents at this table for this round
                    for j, opponent_team in enumerate(teams_at_table):
                        if i != j:
                            round_team_matchups[round_num][team_name].add(opponent_team)

        # Second pass: Check for repeat matchups across different rounds
        for team_name in round_team_matchups[1].keys():  # Iterate through all teams
            seen_opponents = set()

            for round_num in range(1, swiss_rounds_count + 1):
                opponents_this_round = round_team_matchups[round_num].get(team_name, set())

                # Check if any opponent was faced before in a previous round
                for opponent_team in opponents_this_round:
                    if opponent_team in seen_opponents:
                        violation = {
                            'team': team_name,
                            'opponent_team': opponent_team,
                            'round': round_num,
                            'previous_rounds': 'earlier'
                        }
                        team_violations.append(violation)

                # Add all opponents from this round to seen list
                seen_opponents.update(opponents_this_round)

        # Report violations
        if len(team_violations) > 0:
            self.log(f"\n❌ FOUND {len(team_violations)} REPEAT TEAM MATCHUP VIOLATIONS!", "ERROR")
            self.log("Teams that faced each other more than once across different rounds:", "ERROR")

            for v in team_violations[:20]:  # Show first 20
                self.log(
                    f"  {v['team']} vs {v['opponent_team']} met again in Round {v['round']}",
                    "ERROR"
                )

            if len(team_violations) > 20:
                self.log(f"  ... and {len(team_violations) - 20} more violations", "ERROR")

            return False
        else:
            self.log("✅ PERFECT: NO repeat team matchups found across different rounds!", "SUCCESS")
            self.log("Each team faces unique opponents every round in Swiss", "SUCCESS")
            return True

    def display_player_matchup_summary(self):
        """Display summary of each player's matchup history"""
        self.log("\n" + "="*80, "INFO")
        self.log("PLAYER MATCHUP SUMMARY (Sample of 10 players)", "INFO")
        self.log("="*80, "INFO")

        # Show first 10 players as sample
        sample_players = list(self.player_details.keys())[:10]

        for player_id in sample_players:
            player = self.player_details[player_id]
            opponents = self.player_matchup_history[player_id]

            self.log(f"\nPlayer {player_id} - {player['name']} ({player['team']}):", "PLAYER")
            self.log(f"  Total opponents faced: {len(opponents)}", "INFO")

            # Show round-by-round history
            for round_num in sorted(player['round_history'].keys()):
                round_info = player['round_history'][round_num]
                opponent_names = [f"{o['name']} ({o['team']})" for o in round_info['opponents']]
                self.log(f"  Round {round_num} at {round_info['table']}: {', '.join(opponent_names)}", "INFO")

    def run_comprehensive_test(self, swiss_rounds=4):
        """Run comprehensive player tracking test"""
        self.log("\n" + "="*100, "INFO")
        self.log(f"COMPREHENSIVE PLAYER TRACKING TEST - 16 TEAMS, {swiss_rounds} SWISS ROUNDS", "INFO")
        self.log("="*100, "INFO")

        # Setup tournament
        self.log("\n--- PHASE 1: Tournament Setup ---", "INFO")
        tournament = TournamentManager()

        # Configure Swiss rounds
        success, msg = tournament.configure_swiss_rounds(swiss_rounds)
        if not success:
            self.log(f"Configuration failed: {msg}", "ERROR")
            return False

        # Create 16 teams (64 players)
        for i in range(16):
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

        # Initialize player tracking
        self.initialize_player_tracking(tournament)

        # Track all Swiss rounds
        self.log("\n--- PHASE 2: Tracking Swiss Rounds ---", "INFO")

        for round_num in range(1, swiss_rounds + 1):
            self.track_round_matchups(tournament, round_num)

            # Simulate results (not critical for matchup validation)
            tables = tournament.tables.get(round_num, {})
            results = []
            for table_name, players_list in tables.items():
                point_options = [5, 1, 1, 0]
                random.shuffle(point_options)
                for idx, player in enumerate(players_list):
                    results.append({
                        'player_id': player.get('Player ID'),
                        'points': point_options[idx]
                    })
            tournament.submit_player_results(round_num, results)
            tournament.calculate_team_scores()

        # Validate matchups
        self.log("\n--- PHASE 3: Validation ---", "INFO")

        player_validation = self.validate_no_repeat_player_matchups(tournament, swiss_rounds)
        team_validation = self.validate_no_repeat_team_matchups(tournament, swiss_rounds)

        # Display summary
        self.display_player_matchup_summary()

        # Final report
        self.log("\n" + "="*100, "INFO")
        self.log("FINAL REPORT", "INFO")
        self.log("="*100, "INFO")

        self.log(f"\nTotal players tracked: {len(self.player_details)}", "INFO")
        self.log(f"Total teams tracked: {len(tournament.teams)}", "INFO")
        self.log(f"Swiss rounds completed: {swiss_rounds}", "INFO")
        self.log(f"Total tables per round: {len(tournament.teams)}", "INFO")

        if player_validation and team_validation:
            self.log("\n✅ ALL VALIDATIONS PASSED!", "SUCCESS")
            self.log("  ✓ Zero repeat player matchups", "SUCCESS")
            self.log("  ✓ Zero repeat team matchups", "SUCCESS")
            self.log("  ✓ All 64 players tracked successfully", "SUCCESS")
            self.log("  ✓ Pairing constraints satisfied", "SUCCESS")
            return True
        else:
            self.log("\n❌ VALIDATIONS FAILED!", "ERROR")
            if not player_validation:
                self.log("  ✗ Repeat player matchups found", "ERROR")
            if not team_validation:
                self.log("  ✗ Repeat team matchups found", "ERROR")
            return False


if __name__ == "__main__":
    # Test both 4 and 5 Swiss rounds
    all_passed = True

    for swiss_rounds in [4, 5]:
        print("\n\n")
        tester = PlayerTrackingTest()
        passed = tester.run_comprehensive_test(swiss_rounds=swiss_rounds)

        if not passed:
            all_passed = False

    print("\n" + "="*100)
    print("="*100)
    if all_passed:
        print("✅ ALL TESTS PASSED - No repeat matchups found in any scenario!")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Repeat matchups detected!")
        sys.exit(1)
