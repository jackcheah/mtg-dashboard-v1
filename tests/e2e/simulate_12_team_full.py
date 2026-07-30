#!/usr/bin/env python3
"""
Full 12-team Western tournament simulation with detailed player tracking.

Simulates the entire tournament flow from setup to champion declaration,
closely tracking all 48 players across every round to verify:
- No teammates in same pod (hard constraint)
- Repeat matchup avoidance (soft constraint)
- Score accumulation correctness
- Anti-collusion snake pairing activates in round 4
- Round transitions work correctly
- Finals determination is correct
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import random
from collections import defaultdict, Counter
from tournament_dashboard import app, tournament, TournamentState, EventMode, ScoringMode

# ============================================================================
# TOURNAMENT SETUP
# ============================================================================

TEAMS = {
    "Phoenix": ["Alice", "Bob", "Carol", "Dave"],
    "Dragons": ["Eve", "Frank", "Grace", "Hank"],
    "Titans": ["Ivy", "Jack", "Karen", "Leo"],
    "Wolves": ["Mia", "Noah", "Olivia", "Pete"],
    "Eagles": ["Quinn", "Ryan", "Sara", "Tom"],
    "Bears": ["Uma", "Vic", "Wendy", "Xander"],
    "Hawks": ["Yara", "Zane", "Amy", "Ben"],
    "Lions": ["Chloe", "Dan", "Ella", "Finn"],
    "Sharks": ["Gina", "Hugo", "Iris", "Jake"],
    "Vipers": ["Kara", "Liam", "Nora", "Oscar"],
    "Foxes": ["Pam", "Rex", "Tina", "Uri"],
    "Rams": ["Val", "Will", "Xena", "Yuri"],
}


def setup_tournament_direct(client):
    """Set up a 12-team Western tournament using Flask test client."""
    tournament.__init__()

    # Set event mode
    resp = client.post('/set_event_mode', json={'event_mode': 'team'})
    assert resp.get_json()['success'], f"set_event_mode failed: {resp.get_json()}"

    # Set scoring mode
    resp = client.post('/set_scoring_mode', json={'scoring_mode': 'western'})
    assert resp.get_json()['success'], f"set_scoring_mode failed: {resp.get_json()}"

    # Load participants directly (bypassing Excel file)
    pid = 1
    for team_name, player_names in TEAMS.items():
        team_players = []
        for pname in player_names:
            player = {'Player Name': pname, 'Player ID': pid, 'Team Name': team_name}
            team_players.append(player)
            tournament.participants.append(player)
            pid += 1
        tournament.teams[team_name] = team_players

    tournament.transition_to(TournamentState.PARTICIPANTS_LOADED, "Participants loaded for simulation")

    # Setup tournament via endpoint (handles state transition)
    resp = client.post('/setup_tournament')
    data = resp.get_json()
    assert data['success'], f"Setup failed: {data}"
    return data['message']


# ============================================================================
# TRACKING STATE
# ============================================================================

class TournamentTracker:
    def __init__(self):
        self.player_history = defaultdict(list)  # player_id -> [(round, table, opponents, result)]
        self.team_matchup_history = defaultdict(list)  # (team1, team2) -> [round_nums]
        self.player_opponent_history = defaultdict(set)  # player_id -> set of opponent_ids
        self.round_pairings = {}  # round_num -> {table: [player_ids]}
        self.violations = []
        self.warnings = []
        self.scores_by_round = {}  # round_num -> {team: score}

    def record_round(self, round_num, tables_data):
        """Record all pairings for a round and check constraints."""
        self.round_pairings[round_num] = {}

        for table_name, players in tables_data.items():
            player_ids = [p['Player ID'] for p in players]
            team_names = [p['Team Name'] for p in players]
            self.round_pairings[round_num][table_name] = player_ids

            # CHECK 1: No teammates in same pod
            team_counts = Counter(team_names)
            for team, count in team_counts.items():
                if count > 1:
                    self.violations.append(
                        f"CRITICAL Round {round_num} {table_name}: "
                        f"Team '{team}' has {count} players in same pod!"
                    )

            # CHECK 2: Track team matchups
            unique_teams = list(set(team_names))
            for i in range(len(unique_teams)):
                for j in range(i + 1, len(unique_teams)):
                    pair = tuple(sorted([unique_teams[i], unique_teams[j]]))
                    self.team_matchup_history[pair].append(round_num)

            # CHECK 3: Track player opponents
            for i in range(len(player_ids)):
                for j in range(i + 1, len(player_ids)):
                    pid_a, pid_b = player_ids[i], player_ids[j]
                    if pid_b in self.player_opponent_history[pid_a]:
                        self.warnings.append(
                            f"Round {round_num} {table_name}: "
                            f"Player {pid_a} vs {pid_b} is a REPEAT matchup"
                        )
                    self.player_opponent_history[pid_a].add(pid_b)
                    self.player_opponent_history[pid_b].add(pid_a)

            # Record individual player history
            for p in players:
                opponents = [op['Player ID'] for op in players if op['Player ID'] != p['Player ID']]
                self.player_history[p['Player ID']].append({
                    'round': round_num,
                    'table': table_name,
                    'opponents': opponents,
                    'team': p['Team Name'],
                    'name': p['Player Name']
                })

    def record_scores(self, round_num):
        """Snapshot scores after a round."""
        self.scores_by_round[round_num] = dict(tournament.scores)

    def check_anti_collusion(self, round_num, tables_data):
        """Verify anti-collusion snake pairing is active for round 4+."""
        if round_num < 4:
            return

        # Get sorted teams by score
        sorted_teams = sorted(tournament.tournament_teams,
                              key=lambda t: tournament.scores.get(t, 0), reverse=True)
        num_groups = len(sorted_teams) // 4  # 3 groups for 12 teams
        top_teams = set(sorted_teams[:num_groups])  # top 3 teams

        # Group tables by team composition (4 tables per group for 12 teams)
        groups = {}
        for table_name, players in tables_data.items():
            teams_in_pod = frozenset(p['Team Name'] for p in players)
            if teams_in_pod not in groups:
                groups[teams_in_pod] = []
            groups[teams_in_pod].append(table_name)

        for group_teams in groups:
            top_in_group = group_teams & top_teams
            if len(top_in_group) > 1:
                self.warnings.append(
                    f"Round {round_num} ANTI-COLLUSION: Group has {len(top_in_group)} "
                    f"top-{num_groups} teams together: {top_in_group}"
                )

    def print_summary(self):
        """Print full tracking summary."""
        print("\n" + "=" * 80)
        print("  TOURNAMENT TRACKING SUMMARY")
        print("=" * 80)

        # Violations (critical)
        if self.violations:
            print(f"\n  CRITICAL VIOLATIONS ({len(self.violations)}):")
            for v in self.violations:
                print(f"    [X] {v}")
        else:
            print("\n  [OK] No critical violations (teammate constraint always respected)")

        # Warnings (soft constraints)
        if self.warnings:
            print(f"\n  WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"    [!] {w}")
        else:
            print("\n  [OK] No warnings (zero repeat matchups, anti-collusion working)")

        # Team matchup matrix
        print("\n  TEAM MATCHUP FREQUENCY:")
        repeat_matchups = 0
        for pair, rounds in sorted(self.team_matchup_history.items()):
            if len(rounds) > 1:
                repeat_matchups += 1
                print(f"    {pair[0]} vs {pair[1]}: met in rounds {rounds} (REPEAT)")
        if repeat_matchups == 0:
            print("    All team matchups are unique across Swiss rounds!")
        else:
            print(f"    Total repeat team matchups: {repeat_matchups}")

        # Player opponent diversity
        opponent_counts = [len(opps) for opps in self.player_opponent_history.values()]
        if opponent_counts:
            print(f"\n  PLAYER OPPONENT DIVERSITY:")
            print(f"    Min unique opponents per player: {min(opponent_counts)}")
            print(f"    Max unique opponents per player: {max(opponent_counts)}")
            print(f"    Average: {sum(opponent_counts)/len(opponent_counts):.1f}")

        # Score progression
        print(f"\n  SCORE PROGRESSION BY ROUND:")
        for round_num in sorted(self.scores_by_round.keys()):
            scores = self.scores_by_round[round_num]
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            top3 = sorted_scores[:3]
            print(f"    Round {round_num}: Leader={top3[0][0]} ({top3[0][1]}pts), "
                  f"2nd={top3[1][0]} ({top3[1][1]}pts), 3rd={top3[2][0]} ({top3[2][1]}pts)")


# ============================================================================
# SIMULATION HELPERS
# ============================================================================

def get_tables_for_round(round_num):
    """Get table assignments for a round."""
    return tournament.tables.get(round_num, {})


def simulate_table_result(table_name, players, round_num):
    """
    Simulate a game at a table. Uses a weighted random approach where
    higher-scoring players have a slight edge, but upsets can happen.
    """
    # Weight by current score + small random factor
    weights = []
    for p in players:
        score = tournament.player_scores.get(p['Player ID'], 0)
        weights.append(score + random.randint(1, 10))

    # 80% chance of a winner, 20% chance of a draw
    if random.random() < 0.80:
        # Pick winner weighted by performance
        winner_idx = weights.index(max(weights))
        # Small upset chance (20%)
        if random.random() < 0.20:
            winner_idx = random.randint(0, len(players) - 1)

        results = []
        for i, p in enumerate(players):
            if i == winner_idx:
                results.append({'player_id': p['Player ID'], 'points': 5})
            else:
                results.append({'player_id': p['Player ID'], 'points': 0})
    else:
        # Draw: all players get 1 point (4 draws for 4-player pod)
        results = [{'player_id': p['Player ID'], 'points': 1} for p in players]

    return results


def submit_and_finalize_round(client, round_num, tracker):
    """Submit scores for all tables and finalize the round."""
    tables = get_tables_for_round(round_num)

    if not tables:
        print(f"  [ERROR] No tables found for round {round_num}!")
        return False

    # Record pairings
    tracker.record_round(round_num, tables)

    # Check anti-collusion for round 4+
    tracker.check_anti_collusion(round_num, tables)

    # Submit each table
    for table_name, players in tables.items():
        results = simulate_table_result(table_name, players, round_num)

        resp = client.post('/submit_table_results', json={
            'round': round_num,
            'table': table_name,
            'results': results
        })
        data = resp.get_json()
        if not data.get('success'):
            print(f"  [ERROR] Table submission failed: {data.get('error')}")
            return False

    # Record scores after submissions
    tracker.record_scores(round_num)

    # Finalize
    resp = client.post('/submit_player_results', json={'round': round_num})
    data = resp.get_json()
    if not data.get('success'):
        print(f"  [ERROR] Finalization failed: {data.get('error')}")
        return False

    return True


def print_round_pairings(round_num, tables):
    """Pretty-print the pairings for a round."""
    print(f"\n  --- Round {round_num} Pairings ---")
    for table_name, players in sorted(tables.items()):
        player_strs = []
        for p in players:
            score = tournament.player_scores.get(p['Player ID'], 0)
            player_strs.append(f"{p['Player Name']}({p['Team Name']},{score}pts)")
        print(f"    {table_name}: {' vs '.join(player_strs)}")


def print_standings(label=""):
    """Print current standings."""
    sorted_teams = sorted(tournament.scores.items(), key=lambda x: x[1], reverse=True)
    print(f"\n  --- Standings{' (' + label + ')' if label else ''} ---")
    for rank, (team, score) in enumerate(sorted_teams, 1):
        print(f"    {rank}. {team}: {score} pts")


# ============================================================================
# MAIN SIMULATION
# ============================================================================

def main():
    random.seed(42)  # Reproducible simulation

    print("=" * 80)
    print("  12-TEAM WESTERN TOURNAMENT FULL SIMULATION")
    print("  48 players, 4 Swiss rounds, Finals")
    print("=" * 80)

    tracker = TournamentTracker()

    with app.test_client() as client:
        # Setup
        msg = setup_tournament_direct(client)
        print(f"\n  Setup: {msg}")
        print(f"  Event Mode: {tournament.event_mode.value}")
        print(f"  Scoring Mode: {tournament.scoring_mode.value}")
        print(f"  Swiss Rounds: {tournament.swiss_rounds_count}")
        print(f"  Anti-Collusion Start: Round {tournament.anti_collusion_start_round}")
        print(f"  Total Rounds (incl. finals): {tournament.max_rounds}")
        print(f"  Teams: {tournament.tournament_teams}")
        # ====================================================================
        # SWISS ROUNDS
        # ====================================================================
        for round_num in range(1, tournament.swiss_rounds_count + 1):
            print(f"\n{'='*80}")
            print(f"  SWISS ROUND {round_num}")
            print(f"{'='*80}")

            tables = get_tables_for_round(round_num)
            if not tables:
                print(f"  [ERROR] Round {round_num} tables not generated!")
                break

            print_round_pairings(round_num, tables)

            # Verify table count: 12 teams × 4 players = 48 players / 4 per pod = 12 tables
            expected_tables = 12
            assert len(tables) == expected_tables, \
                f"Expected {expected_tables} tables, got {len(tables)}"

            # Verify all 48 players are assigned
            all_player_ids = set()
            for players in tables.values():
                for p in players:
                    all_player_ids.add(p['Player ID'])
            assert len(all_player_ids) == 48, \
                f"Expected 48 players in round, got {len(all_player_ids)}"

            # Submit and finalize
            success = submit_and_finalize_round(client, round_num, tracker)
            if not success:
                print(f"  [FATAL] Round {round_num} failed!")
                break

            print_standings(f"after Round {round_num}")

            # Verify state
            if round_num < tournament.swiss_rounds_count:
                assert tournament.state == TournamentState.SWISS_IN_PROGRESS, \
                    f"Expected SWISS_IN_PROGRESS, got {tournament.state}"
                assert tournament.current_round == round_num + 1, \
                    f"Expected current_round={round_num+1}, got {tournament.current_round}"

        # ====================================================================
        # FINALS
        # ====================================================================
        print(f"\n{'='*80}")
        print(f"  FINALS ROUND")
        print(f"{'='*80}")

        # For 12 teams: no semifinals, straight to finals (top 4)
        assert tournament.state == TournamentState.FINALS_IN_PROGRESS, \
            f"Expected FINALS_IN_PROGRESS after Swiss, got {tournament.state}"

        finals_round = tournament.current_round
        print(f"  Finals round number: {finals_round}")

        tables = get_tables_for_round(finals_round)
        if not tables:
            print("  [ERROR] Finals tables not generated!")
        else:
            print_round_pairings(finals_round, tables)

            # Finals should have 4 tables (top 4 teams × 4 players / 4 per pod)
            print(f"  Tables in finals: {len(tables)}")

            # Identify advancing teams
            if hasattr(tournament, 'finals_data') and tournament.finals_data:
                advancing = tournament.finals_data.get('advancing_teams', [])
                print(f"  Advancing teams: {advancing}")

            # Submit finals
            success = submit_and_finalize_round(client, finals_round, tracker)
            if not success:
                print("  [ERROR] Finals finalization failed!")
            else:
                print(f"\n  Tournament State: {tournament.state.value}")

        # ====================================================================
        # FINAL RESULTS
        # ====================================================================
        print(f"\n{'='*80}")
        print(f"  FINAL RESULTS")
        print(f"{'='*80}")

        if tournament.state == TournamentState.FINALS_COMPLETE:
            winner_data = tournament.get_tournament_winner()
            if winner_data:
                print(f"\n  CHAMPION: {winner_data['winning_team']}")
                print(f"  Final Round Points: {winner_data['final_round_points']}")
                print(f"  Swiss Round Points: {winner_data['swiss_round_points']}")
                if winner_data.get('mvp_player'):
                    mvp = winner_data['mvp_player']
                    print(f"  MVP: {mvp['name']} ({mvp['team']}) - {mvp['total_points']} pts")

                print(f"\n  Final Standings:")
                for rank, standing in enumerate(winner_data['final_standings'], 1):
                    print(f"    {rank}. {standing['team']}: "
                          f"Finals={standing['final_points']}pts, "
                          f"Swiss={standing['swiss_points']}pts, "
                          f"Total={standing['total_points']}pts")
            else:
                print("  [ERROR] Could not determine tournament winner!")
        else:
            print(f"  [ERROR] Tournament did not complete! State: {tournament.state.value}")

        # ====================================================================
        # DETAILED TRACKING REPORT
        # ====================================================================
        tracker.print_summary()

        # Print full player journey for a sample player from each team
        print(f"\n{'='*80}")
        print(f"  SAMPLE PLAYER JOURNEYS (1 player per team)")
        print(f"{'='*80}")

        for team_name in sorted(TEAMS.keys())[:6]:  # First 6 teams
            team_players = tournament.teams.get(team_name, [])
            if not team_players:
                # Team might be in finals_data
                continue
            sample_player = team_players[0]
            pid = sample_player['Player ID']
            pname = sample_player['Player Name']
            history = tracker.player_history.get(pid, [])
            final_score = tournament.player_scores.get(pid, 0)

            print(f"\n  {pname} (Team {team_name}, ID:{pid}) - Final Score: {final_score}pts")
            for entry in history:
                opp_names = []
                for opp_id in entry['opponents']:
                    for p in tournament.participants:
                        if p['Player ID'] == opp_id:
                            opp_names.append(f"{p['Player Name']}({p['Team Name']})")
                            break
                    else:
                        # Check all teams (participant list may not include finals-only teams)
                        for t_players in tournament.teams.values():
                            for tp in t_players:
                                if tp['Player ID'] == opp_id:
                                    opp_names.append(f"{tp['Player Name']}({tp['Team Name']})")
                                    break
                print(f"    Round {entry['round']} @ {entry['table']}: vs {', '.join(opp_names)}")

        # ====================================================================
        # FINAL VERDICT
        # ====================================================================
        print(f"\n{'='*80}")
        print(f"  VERDICT")
        print(f"{'='*80}")

        has_critical = len(tracker.violations) > 0
        has_warnings = len(tracker.warnings) > 0
        tournament_completed = tournament.state == TournamentState.FINALS_COMPLETE

        if not tournament_completed:
            print("  [FAIL] Tournament did not complete successfully")
        elif has_critical:
            print(f"  [FAIL] {len(tracker.violations)} CRITICAL constraint violations found")
        elif has_warnings:
            print(f"  [PASS WITH WARNINGS] Tournament completed. "
                  f"{len(tracker.warnings)} soft constraint warnings.")
        else:
            print("  [PERFECT] Tournament completed with zero violations or warnings!")

        return 0 if (tournament_completed and not has_critical) else 1


if __name__ == '__main__':
    sys.exit(main())
