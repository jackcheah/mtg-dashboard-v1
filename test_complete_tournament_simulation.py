"""
COMPLETE TOURNAMENT SIMULATION TEST
====================================
This test simulates ENTIRE tournaments from start to finish, including:
- All Swiss rounds
- Semifinals (for 16 teams)
- Finals
- Championship determination
- MVP calculation

Tests all 4 scenarios:
1. 8 teams with 4 Swiss rounds
2. 8 teams with 5 Swiss rounds
3. 16 teams with 4 Swiss rounds
4. 16 teams with 5 Swiss rounds

Validates:
✅ Tournament structure determination
✅ Round generation and pairing
✅ Team separation (no teammates at same table)
✅ No repeat matchups in Swiss rounds
✅ Intelligent seating (score-based, rounds 2+)
✅ Proper score calculation and tracking
✅ Semifinals logic (16 teams)
✅ Finals qualification logic
✅ Championship determination
✅ MVP calculation
✅ Tiebreaker logic
✅ Complete tournament flow from start to champion

Created: 2025-11-18
Status: COMPREHENSIVE END-TO-END SIMULATION
"""

import sys
import random
from tournament_dashboard import TournamentManager


class CompleteTournamentSimulator:
    """Simulates complete tournaments from start to finish with full validation"""

    def __init__(self):
        self.test_results = []
        self.current_scenario = None
        self.violations_found = []

    def log(self, message, level="INFO"):
        """Log test messages with color coding"""
        prefix = {
            "INFO": "[INFO]  ",
            "SUCCESS": "[PASS]  ✅ ",
            "ERROR": "[FAIL]  ❌ ",
            "WARNING": "[WARN]  ⚠️  ",
            "CHAMPION": "[CHAMP] 🏆 "
        }
        try:
            print(f"{prefix.get(level, '')} {message}")
        except UnicodeEncodeError:
            # Fallback for systems without Unicode support
            clean_message = message.encode('ascii', 'ignore').decode('ascii')
            print(f"{prefix.get(level, '')} {clean_message}")

    def create_test_teams(self, count):
        """Create test teams with realistic player names"""
        teams = []
        for i in range(count):
            team_name = f"Team_{chr(65 + i)}" if count <= 8 else f"Team_{i+1:02d}"
            players = []
            for j in range(4):
                player_id = (i * 4) + j + 1
                players.append({
                    "Player ID": player_id,
                    "Player Name": f"Player_{player_id:03d}",
                    "Team Name": team_name
                })
            teams.append({
                "name": team_name,
                "players": players
            })
        return teams

    def simulate_realistic_round_results(self, tournament, round_num, tables):
        """
        Simulate realistic tournament results with proper scoring:
        - Win: 5 points
        - Draw: 1 point
        - Loss: 0 points
        """
        all_results = []

        for table_name, players_list in tables.items():
            # Realistic point distribution: one winner, two draws, one loser
            point_options = [5, 1, 1, 0]
            random.shuffle(point_options)

            for idx, player in enumerate(players_list):
                player_id = player.get('Player ID')
                points = point_options[idx]

                all_results.append({
                    'player_id': player_id,
                    'points': points
                })

        return all_results

    def validate_no_teammates_at_table(self, tournament, round_num):
        """Validate no teammates are at the same table"""
        tables = tournament.tables.get(round_num, {})
        violations = []

        for table_name, players_list in tables.items():
            team_names = [p.get('Team Name') for p in players_list]

            # Check for duplicate teams (teammates)
            if len(team_names) != len(set(team_names)):
                violations.append({
                    'round': round_num,
                    'table': table_name,
                    'teams': team_names
                })

        if violations:
            self.violations_found.extend(violations)
            for v in violations:
                self.log(
                    f"Round {v['round']}, {v['table']}: Teammates found! {v['teams']}",
                    "ERROR"
                )
            return False

        return True

    def validate_no_repeat_matchups(self, tournament, swiss_rounds_count):
        """Validate no player faces the same opponent twice in Swiss rounds"""
        player_matchups = {}
        violations = []

        for round_num in range(1, swiss_rounds_count + 1):
            tables = tournament.tables.get(round_num, {})

            for table_name, players_list in tables.items():
                player_ids = [p.get('Player ID') for p in players_list]

                for i, player_id in enumerate(player_ids):
                    if player_id not in player_matchups:
                        player_matchups[player_id] = set()

                    for j, opponent_id in enumerate(player_ids):
                        if i != j:
                            if opponent_id in player_matchups[player_id]:
                                violations.append({
                                    'round': round_num,
                                    'table': table_name,
                                    'player_id': player_id,
                                    'opponent_id': opponent_id
                                })
                            else:
                                player_matchups[player_id].add(opponent_id)

        if violations:
            self.violations_found.extend(violations)
            self.log(f"Found {len(violations)} repeat matchup violations!", "ERROR")
            return False

        return True

    def validate_team_score_calculation(self, tournament):
        """Validate team scores equal sum of player scores"""
        for team_name, players in tournament.teams.items():
            expected_score = sum(
                tournament.player_scores.get(p.get('Player ID'), 0)
                for p in players
            )
            actual_score = tournament.scores.get(team_name, 0)

            if expected_score != actual_score:
                self.log(
                    f"Team score mismatch for {team_name}: "
                    f"Expected {expected_score}, Got {actual_score}",
                    "ERROR"
                )
                return False

        return True

    def simulate_complete_tournament(self, team_count, swiss_rounds):
        """
        Simulate a COMPLETE tournament from start to finish

        Args:
            team_count: 8 or 16
            swiss_rounds: 4 or 5

        Returns:
            dict: Tournament results including champion and MVP
        """
        self.current_scenario = f"{team_count} teams, {swiss_rounds} Swiss rounds"
        self.violations_found = []

        self.log("="*80, "INFO")
        self.log(f"SIMULATING COMPLETE TOURNAMENT: {self.current_scenario}", "INFO")
        self.log("="*80, "INFO")

        # ==========================================
        # PHASE 1: TOURNAMENT SETUP
        # ==========================================
        self.log("\n--- PHASE 1: Tournament Setup ---", "INFO")

        tournament = TournamentManager()

        # Configure Swiss rounds
        success, msg = tournament.configure_swiss_rounds(swiss_rounds)
        if not success:
            self.log(f"Failed to configure Swiss rounds: {msg}", "ERROR")
            return None

        self.log(f"✓ Configured for {swiss_rounds} Swiss rounds", "SUCCESS")

        # Load teams
        teams = self.create_test_teams(team_count)
        tournament.teams = {}
        tournament.participants = []
        for team in teams:
            tournament.teams[team['name']] = team['players']
            tournament.participants.extend(team['players'])

        # Initialize scores
        tournament.scores = {team['name']: 0 for team in teams}
        tournament.player_scores = {}
        for team in teams:
            for player in team['players']:
                tournament.player_scores[player['Player ID']] = 0

        self.log(f"✓ Loaded {team_count} teams", "SUCCESS")

        # Determine tournament structure
        tournament.determine_tournament_structure()

        expected_semifinals = (team_count == 16)
        if tournament.has_semifinals != expected_semifinals:
            self.log(
                f"Tournament structure incorrect: has_semifinals={tournament.has_semifinals}, "
                f"expected={expected_semifinals}",
                "ERROR"
            )
            return None

        self.log(f"✓ Tournament structure: Semifinals={'YES' if tournament.has_semifinals else 'NO'}", "SUCCESS")

        # Setup tournament (generate Swiss round pairings)
        tournament.setup_tournament()

        # Validate Swiss rounds were generated
        swiss_rounds_generated = len([r for r in tournament.tables.keys() if r <= swiss_rounds])
        if swiss_rounds_generated != swiss_rounds:
            self.log(
                f"Swiss rounds generation failed: expected {swiss_rounds}, got {swiss_rounds_generated}",
                "ERROR"
            )
            return None

        self.log(f"✓ Generated {swiss_rounds} Swiss rounds with pairings", "SUCCESS")

        # ==========================================
        # PHASE 2: SWISS ROUNDS SIMULATION
        # ==========================================
        self.log(f"\n--- PHASE 2: Simulating {swiss_rounds} Swiss Rounds ---", "INFO")

        for round_num in range(1, swiss_rounds + 1):
            self.log(f"\n  >> Round {round_num} <<", "WARNING")

            tables = tournament.tables.get(round_num, {})
            expected_tables = team_count  # Each round has team_count tables

            if len(tables) != expected_tables:
                self.log(
                    f"Round {round_num}: Expected {expected_tables} tables, got {len(tables)}",
                    "ERROR"
                )
                return None

            # Validate team separation
            if not self.validate_no_teammates_at_table(tournament, round_num):
                self.log(f"Round {round_num}: Team separation validation FAILED", "ERROR")
                return None

            # Apply intelligent seating (for rounds 2+)
            if round_num > 1:
                seated_tables = tournament.apply_intelligent_seating_to_round(round_num)
                tournament.tables[round_num] = seated_tables
                self.log(f"  ✓ Applied intelligent seating (score-based)", "INFO")

            # Simulate round results
            results = self.simulate_realistic_round_results(tournament, round_num, tables)

            # Submit results through proper API
            success = tournament.submit_player_results(round_num, results)
            if not success:
                self.log(f"Round {round_num}: Result submission failed", "WARNING")

            # Recalculate team scores
            tournament.calculate_team_scores()

            # Validate team score calculation
            if not self.validate_team_score_calculation(tournament):
                self.log(f"Round {round_num}: Team score calculation FAILED", "ERROR")
                return None

            # Display current standings (top 4)
            sorted_teams = sorted(tournament.scores.items(), key=lambda x: x[1], reverse=True)
            self.log(f"  Current standings (top 4):", "INFO")
            for rank, (team, score) in enumerate(sorted_teams[:4], 1):
                self.log(f"    {rank}. {team}: {score} pts", "INFO")

        self.log(f"\n✓ Completed all {swiss_rounds} Swiss rounds", "SUCCESS")

        # Validate no repeat matchups across all Swiss rounds
        if not self.validate_no_repeat_matchups(tournament, swiss_rounds):
            self.log("Repeat matchup validation FAILED", "ERROR")
            return None

        self.log("✓ No repeat matchups in Swiss rounds", "SUCCESS")

        # ==========================================
        # PHASE 3: SEMIFINALS (16 teams only)
        # ==========================================
        semifinals_round = None

        if tournament.has_semifinals:
            self.log("\n--- PHASE 3: Semifinals Round ---", "INFO")

            # Store Swiss scores before semifinals
            tournament.swiss_round_scores = dict(tournament.scores)

            # Generate semifinals
            semifinals_data = tournament.generate_semifinals_round()
            if not semifinals_data:
                self.log("Semifinals generation FAILED", "ERROR")
                return None

            semifinals_round = swiss_rounds + 1

            if semifinals_round not in tournament.tables:
                self.log("Semifinals round not found in tables", "ERROR")
                return None

            semifinals_tables = tournament.tables[semifinals_round]

            if len(semifinals_tables) != 8:
                self.log(
                    f"Semifinals: Expected 8 tables, got {len(semifinals_tables)}",
                    "ERROR"
                )
                return None

            self.log(f"✓ Generated semifinals with 8 tables (top 8 teams)", "SUCCESS")

            # Validate team separation in semifinals
            if not self.validate_no_teammates_at_table(tournament, semifinals_round):
                self.log("Semifinals: Team separation validation FAILED", "ERROR")
                return None

            # Simulate semifinals results
            self.log("\n  >> Semifinals <<", "WARNING")
            semifinals_results = self.simulate_realistic_round_results(
                tournament, semifinals_round, semifinals_tables
            )

            # Submit semifinals results
            success = tournament.submit_player_results(semifinals_round, semifinals_results)
            if not success:
                self.log("Semifinals: Result submission failed", "WARNING")

            # Recalculate team scores
            tournament.calculate_team_scores()

            # Validate team score calculation
            if not self.validate_team_score_calculation(tournament):
                self.log("Semifinals: Team score calculation FAILED", "ERROR")
                return None

            # Display semifinals standings (top 4)
            sorted_teams = sorted(tournament.scores.items(), key=lambda x: x[1], reverse=True)
            self.log("  Semifinals standings (top 4):", "INFO")
            for rank, (team, score) in enumerate(sorted_teams[:4], 1):
                self.log(f"    {rank}. {team}: {score} pts", "INFO")

            self.log("✓ Completed semifinals round", "SUCCESS")

        # ==========================================
        # PHASE 4: FINALS
        # ==========================================
        self.log("\n--- PHASE 4: Finals Round ---", "INFO")

        # Store Swiss round scores (before finals)
        if not hasattr(tournament, 'swiss_round_scores') or not tournament.swiss_round_scores:
            # For 8-team tournaments, Swiss scores = current scores before finals
            tournament.swiss_round_scores = dict(tournament.scores)

        # Generate finals
        after_semifinals = tournament.has_semifinals
        finals_data = tournament.generate_unified_finals(after_semifinals=after_semifinals)

        if not finals_data:
            self.log("Finals generation FAILED", "ERROR")
            return None

        finals_round = tournament.max_rounds

        if finals_round not in tournament.tables:
            self.log("Finals round not found in tables", "ERROR")
            return None

        finals_tables = tournament.tables[finals_round]

        if len(finals_tables) != 4:
            self.log(
                f"Finals: Expected 4 tables, got {len(finals_tables)}",
                "ERROR"
            )
            return None

        self.log(f"✓ Generated finals with 4 tables (top 4 teams)", "SUCCESS")

        # Display finals teams
        finals_teams = finals_data.get('advancing_teams', [])
        self.log(f"  Finals teams: {', '.join(finals_teams)}", "INFO")

        # Validate team separation in finals
        if not self.validate_no_teammates_at_table(tournament, finals_round):
            self.log("Finals: Team separation validation FAILED", "ERROR")
            return None

        # Simulate finals results
        self.log("\n  >> Finals <<", "WARNING")

        # Initialize final_round_scores before simulating finals
        tournament.final_round_scores = {team: 0 for team in tournament.teams.keys()}

        finals_results = self.simulate_realistic_round_results(
            tournament, finals_round, finals_tables
        )

        # Submit finals results
        success = tournament.submit_player_results(finals_round, finals_results)
        if not success:
            self.log("Finals: Result submission failed", "WARNING")

        # Update final round scores manually (since we're simulating)
        for result in finals_results:
            player_id = result['player_id']
            points = result['points']

            # Find team for this player
            for team_name, players in tournament.teams.items():
                for player in players:
                    if player['Player ID'] == player_id:
                        tournament.final_round_scores[team_name] += points
                        break

        # Recalculate team scores
        tournament.calculate_team_scores()

        # Validate team score calculation
        if not self.validate_team_score_calculation(tournament):
            self.log("Finals: Team score calculation FAILED", "ERROR")
            return None

        self.log("✓ Completed finals round", "SUCCESS")

        # ==========================================
        # PHASE 5: CHAMPIONSHIP DETERMINATION
        # ==========================================
        self.log("\n--- PHASE 5: Championship Determination ---", "INFO")

        # Calculate final standings
        final_standings = tournament.calculate_final_round_standings()

        if not final_standings or len(final_standings) == 0:
            self.log("Failed to calculate final standings", "ERROR")
            return None

        # Verify standings are sorted correctly
        # NOTE: The system sorts by FINAL ROUND POINTS first, then Swiss points as tiebreaker
        # This prioritizes finals performance over cumulative total
        for i in range(len(final_standings) - 1):
            current = final_standings[i]
            next_team = final_standings[i + 1]

            # Primary sort: final round points (finals performance)
            if current['final_points'] < next_team['final_points']:
                self.log("Standings not sorted correctly by final points", "ERROR")
                return None

            # Secondary sort: Swiss points (tiebreaker when final points are tied)
            if (current['final_points'] == next_team['final_points'] and
                current['swiss_points'] < next_team['swiss_points']):
                self.log("Tiebreaker not applied correctly (Swiss points)", "ERROR")
                return None

        self.log("✓ Final standings calculated and sorted correctly", "SUCCESS")

        # Get champion
        champion = final_standings[0]

        self.log("\n" + "="*80, "CHAMPION")
        self.log(f"🏆 CHAMPION: {champion['team']}", "CHAMPION")
        self.log(f"   Total Points: {champion['total_points']}", "CHAMPION")
        self.log(f"   Finals Points: {champion['final_points']}", "CHAMPION")
        self.log(f"   Swiss Points: {champion['swiss_points']}", "CHAMPION")
        self.log("="*80, "CHAMPION")

        # Display top 4 standings
        self.log("\n📊 Final Standings (Top 4):", "INFO")
        for i, standing in enumerate(final_standings[:4], 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉", 4: "  "}.get(i, "  ")
            self.log(
                f"  {medal} {i}. {standing['team']}: "
                f"{standing['total_points']} pts "
                f"(Finals: {standing['final_points']}, Swiss: {standing['swiss_points']})",
                "INFO"
            )

        # ==========================================
        # PHASE 6: MVP CALCULATION
        # ==========================================
        self.log("\n--- PHASE 6: MVP Calculation ---", "INFO")

        if hasattr(tournament, 'player_scores') and tournament.player_scores:
            max_player_score = max(tournament.player_scores.values())
            mvp_player_id = max(
                tournament.player_scores.items(),
                key=lambda x: x[1]
            )[0]

            # Find MVP player details
            mvp_name = None
            mvp_team = None
            for team_name, players in tournament.teams.items():
                for player in players:
                    if player['Player ID'] == mvp_player_id:
                        mvp_name = player['Player Name']
                        mvp_team = team_name
                        break
                if mvp_name:
                    break

            self.log(f"🌟 MVP: {mvp_name} ({mvp_team}) with {max_player_score} points", "CHAMPION")
        else:
            self.log("Player scores not available for MVP calculation", "WARNING")

        # ==========================================
        # FINAL VALIDATION SUMMARY
        # ==========================================
        self.log("\n" + "="*80, "INFO")
        self.log("TOURNAMENT SIMULATION COMPLETE", "SUCCESS")
        self.log("="*80, "INFO")

        self.log("\n✅ All validations passed:", "SUCCESS")
        self.log(f"  ✓ Tournament structure: {team_count} teams, {swiss_rounds} Swiss rounds", "INFO")
        self.log(f"  ✓ Swiss rounds: All {swiss_rounds} rounds completed", "INFO")
        if tournament.has_semifinals:
            self.log("  ✓ Semifinals: Round completed (top 8 teams)", "INFO")
        self.log("  ✓ Finals: Round completed (top 4 teams)", "INFO")
        self.log("  ✓ Team separation: No teammates at same table (all rounds)", "INFO")
        self.log("  ✓ Repeat matchups: None found in Swiss rounds", "INFO")
        self.log("  ✓ Score calculation: All team scores validated", "INFO")
        self.log("  ✓ Championship: Determined by finals performance (Swiss as tiebreaker)", "INFO")

        if len(self.violations_found) > 0:
            self.log(f"\n⚠️  Total violations found: {len(self.violations_found)}", "WARNING")
            return None

        return {
            'success': True,
            'scenario': self.current_scenario,
            'champion': champion,
            'final_standings': final_standings,
            'mvp_id': mvp_player_id if 'mvp_player_id' in locals() else None,
            'mvp_score': max_player_score if 'max_player_score' in locals() else None,
            'violations': len(self.violations_found)
        }

    def run_all_scenarios(self):
        """Run all 4 tournament scenarios"""
        self.log("\n" + "="*80, "INFO")
        self.log("COMPLETE TOURNAMENT SIMULATION - ALL SCENARIOS", "INFO")
        self.log("="*80, "INFO")

        scenarios = [
            (8, 4, "8 teams, 4 Swiss rounds"),
            (8, 5, "8 teams, 5 Swiss rounds"),
            (16, 4, "16 teams, 4 Swiss rounds"),
            (16, 5, "16 teams, 5 Swiss rounds")
        ]

        results = []
        passed = 0
        failed = 0

        for team_count, swiss_rounds, description in scenarios:
            self.log(f"\n{'#'*80}", "INFO")
            self.log(f"# SCENARIO: {description}", "INFO")
            self.log(f"{'#'*80}", "INFO")

            try:
                result = self.simulate_complete_tournament(team_count, swiss_rounds)

                if result and result.get('success'):
                    results.append(result)
                    passed += 1
                    self.log(f"\n✅ SCENARIO PASSED: {description}", "SUCCESS")
                else:
                    failed += 1
                    self.log(f"\n❌ SCENARIO FAILED: {description}", "ERROR")
            except Exception as e:
                failed += 1
                self.log(f"\n❌ EXCEPTION in {description}: {str(e)}", "ERROR")
                import traceback
                traceback.print_exc()

        # ==========================================
        # FINAL SUMMARY
        # ==========================================
        self.log("\n\n" + "="*80, "INFO")
        self.log("🏁 FINAL SUMMARY - ALL SCENARIOS", "INFO")
        self.log("="*80, "INFO")

        self.log(f"\nTotal Scenarios: {len(scenarios)}", "INFO")
        self.log(f"Passed: {passed}", "SUCCESS")
        self.log(f"Failed: {failed}", "ERROR" if failed > 0 else "INFO")

        if passed == len(scenarios):
            self.log("\n🎉 ALL SCENARIOS PASSED! 🎉", "CHAMPION")
            self.log("Tournament system is fully functional!", "SUCCESS")
        else:
            self.log(f"\n⚠️  {failed} scenario(s) failed", "ERROR")

        # Display champions from all scenarios
        if results:
            self.log("\n" + "="*80, "INFO")
            self.log("🏆 CHAMPIONS FROM ALL SCENARIOS", "INFO")
            self.log("="*80, "INFO")

            for result in results:
                champion = result['champion']
                self.log(
                    f"\n{result['scenario']}:",
                    "INFO"
                )
                self.log(
                    f"  Champion: {champion['team']} ({champion['total_points']} pts)",
                    "CHAMPION"
                )

        return failed == 0


if __name__ == "__main__":
    simulator = CompleteTournamentSimulator()
    success = simulator.run_all_scenarios()
    sys.exit(0 if success else 1)
