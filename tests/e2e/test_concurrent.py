"""Concurrent access testing for the tournament API.

Tests thread safety of the Flask backend under concurrent requests.
Requires a running server at http://localhost:5001.

Run: python tests/e2e/test_concurrent.py
"""
import threading
import requests
import time
import sys
import os

BASE_URL = "http://localhost:5001"


def setup_tournament(num_teams=8):
    """Reset and set up a fresh tournament."""
    requests.post(f"{BASE_URL}/reset_tournament")
    requests.post(f"{BASE_URL}/load_data", json={"use_sample_data": True, "sample_team_count": num_teams})
    resp = requests.post(f"{BASE_URL}/setup_tournament")
    assert resp.json()["success"], "Tournament setup failed"
    return resp.json()


def get_table_players(round_num, table_name):
    """Get player IDs for a specific table."""
    resp = requests.get(f"{BASE_URL}/get_tables/{round_num}")
    players = resp.json()["tables"][table_name]
    return [p["Player ID"] for p in players]


def submit_table(round_num, table_name, results):
    """Submit table results and return the response."""
    return requests.post(f"{BASE_URL}/submit_table_results", json={
        "round": round_num,
        "table": table_name,
        "results": results
    })


def test_concurrent_table_submissions():
    """4 threads each submit a different table simultaneously."""
    print("\n=== Test: Concurrent Table Submissions ===")
    setup_tournament(8)

    tables = requests.get(f"{BASE_URL}/get_tables/1").json()["tables"]
    table_names = sorted(tables.keys())[:4]

    results = {}
    errors = []

    def submit_one(tname):
        try:
            pids = [p["Player ID"] for p in tables[tname]]
            resp = submit_table(1, tname, [
                {"player_id": pids[0], "points": 5},
                {"player_id": pids[1], "points": 0},
                {"player_id": pids[2], "points": 0},
                {"player_id": pids[3], "points": 0},
            ])
            results[tname] = resp.json()
        except Exception as e:
            errors.append(f"{tname}: {e}")

    threads = [threading.Thread(target=submit_one, args=(t,)) for t in table_names]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"Errors: {errors}"
    for tname in table_names:
        assert results[tname]["success"], f"{tname} failed: {results[tname]}"

    status = requests.get(f"{BASE_URL}/get_submission_status/1").json()
    assert status["submitted_count"] == 4, f"Expected 4 submitted, got {status['submitted_count']}"
    print(f"  PASS: {len(table_names)} tables submitted concurrently, all succeeded")


def test_double_finalization():
    """Two threads try to finalize the same round — one should succeed, one should fail."""
    print("\n=== Test: Double Finalization ===")
    setup_tournament(8)

    tables = requests.get(f"{BASE_URL}/get_tables/1").json()["tables"]
    for tname, players in tables.items():
        pids = [p["Player ID"] for p in players]
        submit_table(1, tname, [
            {"player_id": pids[0], "points": 5},
            {"player_id": pids[1], "points": 0},
            {"player_id": pids[2], "points": 0},
            {"player_id": pids[3], "points": 0},
        ])

    results = {}

    def finalize(thread_id):
        resp = requests.post(f"{BASE_URL}/submit_player_results", json={"round": 1})
        results[thread_id] = resp.json()

    t1 = threading.Thread(target=finalize, args=("A",))
    t2 = threading.Thread(target=finalize, args=("B",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    successes = sum(1 for r in results.values() if r.get("success"))
    failures = sum(1 for r in results.values() if not r.get("success"))

    assert successes == 1, f"Expected 1 success, got {successes}"
    assert failures == 1, f"Expected 1 failure, got {failures}"
    print(f"  PASS: One finalization succeeded, one correctly rejected")


def test_submit_during_edit():
    """One thread edits Table 1 while another submits Table 2 — both should succeed."""
    print("\n=== Test: Submit During Edit ===")
    setup_tournament(8)

    tables = requests.get(f"{BASE_URL}/get_tables/1").json()["tables"]
    table_names = sorted(tables.keys())

    for tname in table_names[:2]:
        pids = [p["Player ID"] for p in tables[tname]]
        submit_table(1, tname, [
            {"player_id": pids[0], "points": 5},
            {"player_id": pids[1], "points": 0},
            {"player_id": pids[2], "points": 0},
            {"player_id": pids[3], "points": 0},
        ])

    results = {}
    errors = []

    def edit_table1():
        try:
            pids = [p["Player ID"] for p in tables[table_names[0]]]
            resp = requests.post(f"{BASE_URL}/edit_table_results", json={
                "round": 1, "table": table_names[0], "reason": "concurrent test",
                "results": [
                    {"player_id": pids[0], "points": 0},
                    {"player_id": pids[1], "points": 5},
                    {"player_id": pids[2], "points": 0},
                    {"player_id": pids[3], "points": 0},
                ]
            })
            results["edit"] = resp.json()
        except Exception as e:
            errors.append(f"edit: {e}")

    def submit_table3():
        try:
            pids = [p["Player ID"] for p in tables[table_names[2]]]
            resp = submit_table(1, table_names[2], [
                {"player_id": pids[0], "points": 5},
                {"player_id": pids[1], "points": 0},
                {"player_id": pids[2], "points": 0},
                {"player_id": pids[3], "points": 0},
            ])
            results["submit"] = resp.json()
        except Exception as e:
            errors.append(f"submit: {e}")

    t1 = threading.Thread(target=edit_table1)
    t2 = threading.Thread(target=submit_table3)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not errors, f"Errors: {errors}"
    assert results["edit"]["success"], f"Edit failed: {results['edit']}"
    assert results["submit"]["success"], f"Submit failed: {results['submit']}"
    print(f"  PASS: Concurrent edit + submit both succeeded without corruption")


if __name__ == "__main__":
    try:
        requests.get(f"{BASE_URL}/get_state_info", timeout=2)
    except requests.ConnectionError:
        print(f"ERROR: Server not running at {BASE_URL}")
        sys.exit(1)

    passed = 0
    failed = 0

    for test_fn in [test_concurrent_table_submissions, test_double_finalization, test_submit_during_edit]:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
