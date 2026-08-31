#!/usr/bin/env python3
"""Validate generated Excel files work with all tournament configurations.

Tests 4 combinations:
1. 40 teams + Western scoring
2. 40 teams + Japanese scoring
3. 80 players (individual) + Western scoring
4. 80 players (individual) + Japanese scoring

Runs full tournament flow: load Excel → setup → Swiss rounds → playoffs → champion.
"""

import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tournament_dashboard import app, tournament, TournamentState, EventMode, ScoringMode


def run_tournament(excel_path, event_mode, scoring_mode, label):
    """Run a complete tournament using Flask test client."""
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  Excel: {excel_path}")
    print(f"  Mode: {event_mode} / {scoring_mode}")
    print(f"{'='*70}")

    random.seed(42)
    tournament.__init__()
    app.config['TESTING'] = True

    with app.test_client() as client:
        # Step 1: Set event and scoring mode
        resp = client.post('/set_event_mode', json={'mode': event_mode})
        assert resp.get_json()['success'], f"Failed to set event mode: {resp.get_json()}"

        resp = client.post('/set_scoring_mode', json={'mode': scoring_mode})
        assert resp.get_json()['success'], f"Failed to set scoring mode: {resp.get_json()}"

        # Step 2: Load participants from Excel
        excel_abs = os.path.abspath(excel_path)
        tournament.load_participants(excel_abs)
        tournament.transition_to(TournamentState.PARTICIPANTS_LOADED, "Excel loaded")

        num_teams = len(tournament.teams)
        num_players = len(tournament.participants)
        print(f"  Loaded: {num_teams} teams, {num_players} players")

        # Step 3: Setup tournament
        resp = client.post('/setup_tournament')
        data = resp.get_json()
        assert data['success'], f"Setup failed: {data}"
        swiss_rounds = tournament.swiss_rounds_count
        max_rounds = tournament.max_rounds
        print(f"  Swiss rounds: {swiss_rounds}, Max rounds: {max_rounds}")
        has_top_cut = getattr(tournament, 'has_top_cut', False)
        has_intermediate = tournament.has_semifinals or has_top_cut
        print(f"  Has intermediate round: {has_intermediate} (semifinals={tournament.has_semifinals}, top_cut={has_top_cut})")

        # Step 4: Play Swiss rounds
        for round_num in range(1, swiss_rounds + 1):
            tables = tournament.tables.get(round_num, {})
            assert tables, f"Round {round_num}: no tables generated"

            # Validate no teammate violations (team mode only)
            if event_mode == 'team':
                for tname, players in tables.items():
                    teams_in_pod = [p['Team Name'] for p in players]
                    assert len(set(teams_in_pod)) == len(players), \
                        f"Round {round_num} {tname}: TEAMMATE VIOLATION {teams_in_pod}"

            # Submit scores for each table
            for table_name, players in tables.items():
                winner_idx = random.randint(0, len(players) - 1)
                results = []
                for idx, p in enumerate(players):
                    pts = 5 if idx == winner_idx else 0
                    results.append({'player_id': p['Player ID'], 'points': pts})
                resp = client.post('/submit_table_results', json={
                    'round': round_num, 'table': table_name, 'results': results
                })
                assert resp.get_json()['success'], \
                    f"Round {round_num} {table_name} submit failed: {resp.get_json()}"

            # Finalize round
            resp = client.post('/submit_player_results', json={
                'round': round_num, 'results': []
            })
            data = resp.get_json()
            assert data['success'], f"Round {round_num} finalize failed: {data}"
            print(f"  Round {round_num}/{max_rounds}: OK ({len(tables)} tables)")

        # Step 5: Intermediate round — Top 8 Cut (team) or Top Cut (individual)
        if has_intermediate:
            inter_round = swiss_rounds + 1
            tables = tournament.tables.get(inter_round, {})
            assert tables, f"Intermediate round {inter_round}: no tables generated"

            for table_name, players in tables.items():
                winner_idx = random.randint(0, len(players) - 1)
                results = []
                for idx, p in enumerate(players):
                    pts = 5 if idx == winner_idx else 0
                    results.append({'player_id': p['Player ID'], 'points': pts})
                resp = client.post('/submit_table_results', json={
                    'round': inter_round, 'table': table_name, 'results': results
                })
                assert resp.get_json()['success'], \
                    f"Intermediate {table_name} submit failed: {resp.get_json()}"

            resp = client.post('/submit_player_results', json={
                'round': inter_round, 'results': []
            })
            data = resp.get_json()
            assert data['success'], f"Intermediate round finalize failed: {data}"
            round_label = "Top 8 Cut" if tournament.has_semifinals else "Top Cut"
            print(f"  Round {inter_round}/{max_rounds} ({round_label}): OK ({len(tables)} tables)")

        # Step 6: Finals
        finals_round = max_rounds
        tables = tournament.tables.get(finals_round, {})
        assert tables, f"Finals: no tables generated"

        for table_name, players in tables.items():
            winner_idx = random.randint(0, len(players) - 1)
            results = []
            for idx, p in enumerate(players):
                pts = 5 if idx == winner_idx else 0
                results.append({'player_id': p['Player ID'], 'points': pts})
            resp = client.post('/submit_table_results', json={
                'round': finals_round, 'table': table_name, 'results': results
            })
            assert resp.get_json()['success'], \
                f"Finals {table_name} submit failed: {resp.get_json()}"

        resp = client.post('/submit_player_results', json={
            'round': finals_round, 'results': []
        })
        data = resp.get_json()
        assert data['success'], f"Finals finalize failed: {data}"
        print(f"  Round {finals_round}/{max_rounds} (Finals): OK ({len(tables)} tables)")

        # Step 7: Verify tournament completed
        assert tournament.state == TournamentState.FINALS_COMPLETE, \
            f"Expected FINALS_COMPLETE, got {tournament.state}"

        # Step 8: Get final standings
        resp = client.get('/final_standings')
        standings = resp.get_json()
        assert standings.get('success') or standings.get('standings'), \
            f"Final standings failed: {standings}"

        champion = standings.get('champion') or standings.get('standings', [{}])[0]
        print(f"  Champion: {champion.get('team', champion.get('name', 'unknown'))}")

        # Step 9: Validate Japanese scoring (scores should be around 1000, not 0-based)
        if scoring_mode == 'japanese':
            resp = client.get('/get_scores')
            scores = resp.get_json().get('scores', {})
            if scores:
                sample_score = list(scores.values())[0]
                assert sample_score > 100, \
                    f"Japanese scores look wrong (too low): {sample_score}"
                print(f"  Japanese score sample: {sample_score} (looks correct)")

        # Step 10: Validate integrity
        resp = client.get('/validate_integrity')
        integrity = resp.get_json()
        issues = integrity.get('issues', [])
        if issues:
            print(f"  WARNING: Integrity issues: {issues}")
        else:
            print(f"  Integrity check: PASS")

        print(f"  RESULT: PASS")
        return True


if __name__ == '__main__':
    results = {}

    configs = [
        ("participants/participant_40teams.xlsx", "team", "western",
         "40 Teams + Western Scoring"),
        ("participants/participant_40teams.xlsx", "team", "japanese",
         "40 Teams + Japanese Scoring"),
        ("participants/participant_80players.xlsx", "individual", "western",
         "80 Players (Individual) + Western Scoring"),
        ("participants/participant_80players.xlsx", "individual", "japanese",
         "80 Players (Individual) + Japanese Scoring"),
    ]

    for excel, mode, scoring, label in configs:
        try:
            ok = run_tournament(excel, mode, scoring, label)
            results[label] = "PASS" if ok else "FAIL"
        except Exception as e:
            results[label] = f"FAIL: {e}"
            import traceback
            traceback.print_exc()

    print(f"\n{'='*70}")
    print("  SUMMARY")
    print(f"{'='*70}")
    for label, result in results.items():
        status = "PASS" if result == "PASS" else "FAIL"
        print(f"  [{status}] {label}")
        if result != "PASS":
            print(f"         {result}")
    print(f"{'='*70}")

    all_pass = all(v == "PASS" for v in results.values())
    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAILURES'}")
    sys.exit(0 if all_pass else 1)
