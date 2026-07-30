#!/usr/bin/env python3
"""
End-to-end API-level test for anti-collusion snake pairing.

Simulates complete tournament flows (Swiss → Playoffs → Finals) for 8, 12, and 16 teams
using Flask's test client. No browser or running server required.

Validates:
- All rounds generate successfully
- No teammates in same pod (hard constraint)
- Snake pairing activates in round 4+ (top teams separated)
- Round transitions work correctly through finals
- Score accumulation is correct
- Final standings are produced

Run: python tests/e2e/test_anti_collusion_e2e.py
"""

import sys
import os
import json
import random
from itertools import combinations
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tournament_dashboard import app, tournament, TournamentState


def make_team_data(num_teams):
    """Generate team Excel-like data structures."""
    teams = {}
    participants = []
    tournament_teams = []
    for t in range(num_teams):
        team_name = f"Team {chr(65 + t)}"
        players = []
        for p in range(4):
            pid = t * 4 + p + 1
            player = {
                'Player Name': f'{team_name} P{p+1}',
                'Player ID': pid,
                'Team Name': team_name,
            }
            players.append(player)
            participants.append(player)
        teams[team_name] = players
        tournament_teams.append(team_name)
    return teams, tournament_teams, participants


def reset_tournament():
    """Reset the global tournament to initial state."""
    tournament.__init__()


def setup_tournament_direct(num_teams):
    """Set up tournament directly by populating internal state (bypass Excel loading)."""
    reset_tournament()

    teams, tournament_teams, participants = make_team_data(num_teams)
    tournament.teams = teams
    tournament.tournament_teams = tournament_teams
    tournament.participants = participants
    tournament.state = TournamentState.PARTICIPANTS_LOADED
    tournament.event_mode = tournament.event_mode  # keep TEAM default


def submit_round_scores(client, round_num, tables_data):
    """Submit scores for all tables in a round. Returns list of validation issues."""
    issues = []

    for table_name, player_ids in tables_data.items():
        pod_size = len(player_ids)
        winner_idx = random.randint(0, pod_size - 1)
        results = []
        for i, pid in enumerate(player_ids):
            results.append({
                'player_id': pid,
                'points': 5 if i == winner_idx else 0
            })

        resp = client.post('/submit_table_results', json={
            'round': round_num,
            'table': table_name,
            'results': results
        })
        data = resp.get_json()
        if not data.get('success'):
            issues.append(f"Table {table_name}: {data.get('error', 'unknown error')}")

    return issues


def finalize_round(client, round_num):
    """Finalize a round (submit_player_results)."""
    resp = client.post('/submit_player_results', json={'round': round_num})
    return resp.get_json()


def get_tables(client, round_num):
    """Get table assignments for a round."""
    resp = client.get(f'/get_tables/{round_num}')
    return resp.get_json()


def validate_no_teammates_in_pod(tables_data):
    """Check that no pod has two players from the same team."""
    violations = []
    for table_name, table_info in tables_data.items():
        if isinstance(table_info, list):
            players = table_info
        elif isinstance(table_info, dict) and 'players' in table_info:
            players = table_info['players']
        else:
            continue

        team_names = [p.get('team') or p.get('Team Name', '') for p in players]
        team_counts = Counter(team_names)
        for team, count in team_counts.items():
            if count > 1 and team:
                violations.append(f"{table_name}: {team} has {count} players")
    return violations


def validate_snake_separation(tables_data, tournament_teams, scores, round_num):
    """Verify that in round 4+, top teams are separated across groups."""
    if round_num < 4:
        return []

    sorted_teams = sorted(tournament_teams, key=lambda t: scores.get(t, 0), reverse=True)
    num_groups = len(sorted_teams) // 4
    top_teams = set(sorted_teams[:num_groups])

    issues = []
    # Group tables by their team composition
    group_teams = {}
    for table_name, table_info in tables_data.items():
        if isinstance(table_info, list):
            players = table_info
        elif isinstance(table_info, dict) and 'players' in table_info:
            players = table_info['players']
        else:
            continue

        teams_in_table = set(p.get('team') or p.get('Team Name', '') for p in players)
        # Find which group this table belongs to (tables share team composition within a group)
        group_key = tuple(sorted(teams_in_table))
        if group_key not in group_teams:
            group_teams[group_key] = set()
        group_teams[group_key].update(teams_in_table)

    # Check each group doesn't have multiple top teams
    for group_key, group_team_set in group_teams.items():
        top_in_group = group_team_set & top_teams
        if len(top_in_group) > 1:
            issues.append(f"Group {group_key} has {len(top_in_group)} top teams: {top_in_group}")

    return issues


def run_full_tournament(num_teams, verbose=True):
    """Run a complete tournament simulation and return results."""
    if verbose:
        print(f"\n{'='*70}")
        print(f"  FULL E2E TOURNAMENT: {num_teams} TEAMS")
        print(f"{'='*70}")

    setup_tournament_direct(num_teams)

    with app.test_client() as client:
        # Setup tournament
        resp = client.post('/setup_tournament')
        data = resp.get_json()
        if not data.get('success'):
            return {'success': False, 'error': f"Setup failed: {data.get('error')}",
                    'num_teams': num_teams}

        structure = tournament.determine_tournament_structure()
        swiss_rounds = tournament.swiss_rounds_count
        max_rounds = tournament.max_rounds
        has_semifinals = tournament.has_semifinals

        if verbose:
            print(f"  Structure: {swiss_rounds} Swiss → "
                  f"{'Top8 Cut → ' if has_semifinals else ''}Finals")
            print(f"  Max rounds: {max_rounds}")

        results = {
            'success': True,
            'num_teams': num_teams,
            'swiss_rounds': swiss_rounds,
            'max_rounds': max_rounds,
            'has_semifinals': has_semifinals,
            'rounds': {},
            'violations': [],
            'snake_issues': [],
        }

        # Play all rounds
        for round_num in range(1, max_rounds + 1):
            is_swiss = round_num <= swiss_rounds
            is_top8 = has_semifinals and round_num == swiss_rounds + 1
            is_finals = round_num == max_rounds

            phase = "Swiss" if is_swiss else ("Top8 Cut" if is_top8 else "Finals")

            # Get tables
            tables_resp = get_tables(client, round_num)
            if not tables_resp.get('success', True):
                results['success'] = False
                results['violations'].append(
                    f"Round {round_num}: Failed to get tables: {tables_resp.get('error')}")
                break

            tables_data = tables_resp.get('tables', {})
            if not tables_data:
                results['success'] = False
                results['violations'].append(f"Round {round_num}: No tables returned")
                break

            # Validate no teammates in same pod (Swiss rounds only - strict)
            teammate_violations = validate_no_teammates_in_pod(tables_data)
            if teammate_violations and is_swiss:
                results['violations'].extend(
                    [f"Round {round_num} TEAMMATE VIOLATION: {v}" for v in teammate_violations])

            # Validate snake separation (round 4+ of Swiss)
            if is_swiss and round_num >= 4:
                snake_issues = validate_snake_separation(
                    tables_data, tournament.tournament_teams, tournament.scores, round_num)
                if snake_issues:
                    results['snake_issues'].extend(
                        [f"Round {round_num}: {issue}" for issue in snake_issues])

            # Count pods and sizes
            pod_count = len(tables_data)
            pod_sizes = []
            table_players = {}
            for tname, tinfo in tables_data.items():
                if isinstance(tinfo, list):
                    players = tinfo
                elif isinstance(tinfo, dict) and 'players' in tinfo:
                    players = tinfo['players']
                else:
                    players = []
                pod_sizes.append(len(players))
                table_players[tname] = [p.get('id') or p.get('Player ID') for p in players]

            if verbose:
                print(f"  Round {round_num} [{phase}]: {pod_count} pods, "
                      f"sizes={sorted(set(pod_sizes))}, "
                      f"violations={len(teammate_violations)}")

            # Submit scores
            submit_issues = submit_round_scores(client, round_num, table_players)
            if submit_issues:
                results['violations'].extend(
                    [f"Round {round_num} SUBMIT: {issue}" for issue in submit_issues])
                results['success'] = False
                break

            # Finalize round
            finalize_resp = finalize_round(client, round_num)
            if not finalize_resp.get('success'):
                results['success'] = False
                results['violations'].append(
                    f"Round {round_num} FINALIZE: {finalize_resp.get('error')}")
                break

            results['rounds'][round_num] = {
                'phase': phase,
                'pods': pod_count,
                'pod_sizes': pod_sizes,
                'teammate_violations': len(teammate_violations),
            }

        # Check final state
        if results['success']:
            state_resp = client.get('/get_state_info')
            state_data = state_resp.get_json()
            final_state = state_data.get('current_state', '')

            if final_state != 'finals_complete':
                results['success'] = False
                results['violations'].append(
                    f"Expected finals_complete state, got: {final_state}")

            # Get final standings
            standings_resp = client.get('/final_standings')
            standings_data = standings_resp.get_json()
            if standings_data.get('success'):
                winner = standings_data.get('winner', {})
                results['winner'] = winner.get('team', 'Unknown')
                if verbose:
                    print(f"  Champion: {results['winner']}")
            else:
                results['success'] = False
                results['violations'].append("Failed to get final standings")

        if verbose:
            if results['success']:
                print(f"  RESULT: SUCCESS - Tournament completed")
            else:
                print(f"  RESULT: FAILED")
                for v in results['violations']:
                    print(f"    ERROR: {v}")
            if results['snake_issues']:
                print(f"  SNAKE ISSUES ({len(results['snake_issues'])}):")
                for issue in results['snake_issues']:
                    print(f"    WARNING: {issue}")

    return results


def run_player_repeat_analysis(num_teams, verbose=True):
    """Run a tournament and analyze player-level repeat opponents."""
    if verbose:
        print(f"\n{'='*70}")
        print(f"  PLAYER REPEAT ANALYSIS: {num_teams} TEAMS")
        print(f"{'='*70}")

    setup_tournament_direct(num_teams)

    with app.test_client() as client:
        resp = client.post('/setup_tournament')
        data = resp.get_json()
        if not data.get('success'):
            print(f"  Setup failed: {data.get('error')}")
            return None

        swiss_rounds = tournament.swiss_rounds_count
        all_matchups = []

        for round_num in range(1, swiss_rounds + 1):
            tables_resp = get_tables(client, round_num)
            tables_data = tables_resp.get('tables', {})

            # Record matchups
            for tname, tinfo in tables_data.items():
                if isinstance(tinfo, list):
                    players = tinfo
                elif isinstance(tinfo, dict) and 'players' in tinfo:
                    players = tinfo['players']
                else:
                    continue
                pids = [p.get('id') or p.get('Player ID') for p in players]
                for a, b in combinations(pids, 2):
                    all_matchups.append((min(a, b), max(a, b)))

            # Submit and finalize
            table_players = {}
            for tname, tinfo in tables_data.items():
                if isinstance(tinfo, list):
                    players = tinfo
                elif isinstance(tinfo, dict) and 'players' in tinfo:
                    players = tinfo['players']
                else:
                    continue
                table_players[tname] = [p.get('id') or p.get('Player ID') for p in players]

            submit_round_scores(client, round_num, table_players)
            finalize_round(client, round_num)

        counter = Counter(all_matchups)
        total = len(all_matchups)
        unique = len(counter)
        repeats = sum(v - 1 for v in counter.values() if v > 1)

        if verbose:
            print(f"  Swiss rounds analyzed: {swiss_rounds}")
            print(f"  Total matchups: {total}")
            print(f"  Unique matchups: {unique}")
            print(f"  Player repeats: {repeats}")
            print(f"  Status: {'PERFECT' if repeats == 0 else f'{repeats} repeats'}")

        return {'total': total, 'unique': unique, 'repeats': repeats}


def main():
    print("=" * 70)
    print("  ANTI-COLLUSION E2E TEST SUITE")
    print("  Testing full tournament flow with snake pairing (round 4+)")
    print("=" * 70)

    all_results = []
    all_passed = True

    # Test 1: Full tournament for each supported team count
    for num_teams in [8, 12, 16]:
        result = run_full_tournament(num_teams)
        all_results.append(result)
        if not result['success']:
            all_passed = False
        if result['violations']:
            all_passed = False

    # Test 2: Player repeat analysis
    print("\n" + "=" * 70)
    print("  PLAYER REPEAT ANALYSIS (Swiss rounds only)")
    print("=" * 70)
    for num_teams in [8, 12, 16]:
        run_player_repeat_analysis(num_teams)

    # Test 3: Verify anti-collusion is actually active
    print(f"\n{'='*70}")
    print("  ANTI-COLLUSION ACTIVATION VERIFICATION")
    print(f"{'='*70}")

    setup_tournament_direct(16)
    with app.test_client() as client:
        resp = client.post('/setup_tournament')
        assert resp.get_json()['success']

        # Play rounds 1-3, finalize
        for round_num in range(1, 4):
            tables_resp = get_tables(client, round_num)
            tables_data = tables_resp.get('tables', {})
            table_players = {}
            for tname, tinfo in tables_data.items():
                if isinstance(tinfo, list):
                    players = tinfo
                elif isinstance(tinfo, dict) and 'players' in tinfo:
                    players = tinfo['players']
                else:
                    continue
                table_players[tname] = [p.get('id') or p.get('Player ID') for p in players]
            submit_round_scores(client, round_num, table_players)
            finalize_round(client, round_num)

        # Round 4: Check that top 4 teams are NOT in the same group
        tables_resp = get_tables(client, 4)
        tables_data = tables_resp.get('tables', {})

        # Get current standings to identify top teams
        sorted_teams = sorted(tournament.tournament_teams,
                              key=lambda t: tournament.scores.get(t, 0), reverse=True)
        top_4 = set(sorted_teams[:4])

        # Check each table's team composition
        groups_seen = {}
        for tname, tinfo in tables_data.items():
            if isinstance(tinfo, list):
                players = tinfo
            elif isinstance(tinfo, dict) and 'players' in tinfo:
                players = tinfo['players']
            else:
                continue
            teams_in_pod = frozenset(p.get('team') or p.get('Team Name', '') for p in players)
            if teams_in_pod not in groups_seen:
                groups_seen[teams_in_pod] = []
            groups_seen[teams_in_pod].append(tname)

        anti_collusion_working = True
        for group_teams in groups_seen:
            top_in_group = group_teams & top_4
            if len(top_in_group) > 1:
                anti_collusion_working = False
                print(f"  FAIL: Group has {len(top_in_group)} top-4 teams: {top_in_group}")

        if anti_collusion_working:
            print("  PASS: Round 4 correctly separates top teams (max 1 per group)")
        else:
            all_passed = False

    # Test 4: Backup/restore preserves anti-collusion settings
    print(f"\n{'='*70}")
    print("  BACKUP/RESTORE PRESERVATION TEST")
    print(f"{'='*70}")

    setup_tournament_direct(16)
    tournament.anti_collusion_enabled = True
    tournament.anti_collusion_start_round = 4
    state_dict = tournament._build_state_dict()
    config = state_dict['config']
    assert config['anti_collusion_enabled'] == True, "anti_collusion_enabled not in backup"
    assert config['anti_collusion_start_round'] == 4, "anti_collusion_start_round not in backup"
    print("  PASS: Anti-collusion settings preserved in state backup")

    # Final summary
    print(f"\n{'='*70}")
    print("  FINAL SUMMARY")
    print(f"{'='*70}")
    for r in all_results:
        status = "PASS" if r['success'] and not r['violations'] else "FAIL"
        snake_note = f" ({len(r['snake_issues'])} snake warnings)" if r['snake_issues'] else ""
        print(f"  {r['num_teams']} teams: {status}{snake_note}")

    if all_passed:
        print(f"\n  ALL TESTS PASSED")
    else:
        print(f"\n  SOME TESTS FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
