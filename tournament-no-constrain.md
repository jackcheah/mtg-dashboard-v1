# Feasibility Analysis: Removing the Multiple-of-4 Team Count Constraint

**Date:** 2026-09-17
**Status:** Parked for future exploration
**Reference file:** `unified_swiss_pairing_cj.py` (CJ's wraparound prototype)

---

## Background

The current system only supports team counts that are multiples of 4 (8, 12, 16, 20, 24, 28, 32, 36, 40). CJ prototyped an alternative "wraparound" pairing algorithm in `unified_swiss_pairing_cj.py` that works for ANY team count >= 4.

This document captures the feasibility analysis so we can revisit it later.

---

## How the Wraparound Algorithm Works

Instead of grouping teams into blocks of 4 (which requires a multiple of 4), the wraparound arranges all N teams in a ring and forms pods using a sliding window:

```
For N teams ordered[0..N-1]:
  Pod j = teams at positions j, j+1, j+2, j+3 (mod N)
```

This produces exactly **N pods** per round. Each pod has 4 players from 4 distinct teams. Each team appears in exactly 4 pods. Every player plays exactly once.

Example with 5 teams (A, B, C, D, E):
```
Pod 0: A, B, C, D
Pod 1: B, C, D, E
Pod 2: C, D, E, A
Pod 3: D, E, A, B
Pod 4: E, A, B, C
```

---

## The Overlap Problem

The wraparound creates overlapping pods where nearby teams in the ring share multiple pods per round. This is fine for larger N but degrades badly for small N:

| N teams | Pairs sharing 3 pods | Sharing 2 | Sharing 1 | Sharing 0 |
|---------|---------------------|-----------|-----------|-----------|
| **5**   | **ALL 10 pairs**    | 0         | 0         | 0         |
| **6**   | 6                   | 9         | 0         | 0         |
| **7**   | 7                   | 7         | 7         | 0         |
| 8       | 8                   | 8         | 8         | 4         |
| 9       | 9                   | 9         | 9         | 9         |
| 10      | 10                  | 10        | 10        | 15        |

**Impact:**
- **N=5**: Every pair of teams shares 3/4 pods. Player-level repeat avoidance is impossible from round 2 onward.
- **N=6-7**: Every pair shares at least 1-2 pods. Repeat-free Swiss becomes very strained by round 3.
- **N=8+**: Teams at ring distance >= 4 share 0 pods. Quality is acceptable.

**Conclusion:** The wraparound only produces quality tournaments for **N >= 8**. For 5-7 teams, it runs but produces poor competitive integrity.

---

## Scoring System Compatibility

**The scoring system would work without changes.** It operates per-table and per-player:
- `submit_table_results()` — submits one table at a time, no assumption on total count
- `calculate_team_scores()` — sums player scores, doesn't care about table count
- `get_submission_status()` — uses `len(tables)` dynamically
- Round completion — just checks all tables are submitted

---

## What Would Need to Change (~11+ locations)

### Hard blockers (code rejects or crashes):
1. `tournament_dashboard.py:84` — `supported_team_counts = [8, 12, ..., 40]`
2. `tournament_dashboard.py:688-853` — `determine_tournament_structure()` only branches for multiples of 4
3. `tournament_dashboard.py:1298-1307` — `setup_tournament()` validation rejects non-multiples
4. `unified_swiss_pairing.py:101-106` — constructor `raise ValueError`
5. `unified_swiss_pairing.py:648,743,773` — group formation `// 4` drops remainder teams

### Silent data loss:
6. `tournament_dashboard.py:1262-1264` — `create_sample_data()` resets to 8

### Frontend:
7. `dashboard_ultra_modern.html:78` — UI text says "multiples of 4"
8. `dashboard.js:873` — hardcoded sample of 8

### Health checks:
9. `tournament_dashboard.py:5163` — validation rejects non-standard counts

### Tests (4+ files):
10. `test_full_tournament_flow.py:479-502` — asserts non-multiples are rejected
11. `test_pairing_simulation.py:519-549` — same
12. Multiple E2E files hardcoded to multiples of 4

### CJ's file still has vestiges:
13. `unified_swiss_pairing_cj.py:777,872,902` — legacy group methods still use `// 4`

---

## CJ's Version vs Current: Key Differences

| Area | Current (`unified_swiss_pairing.py`) | CJ (`unified_swiss_pairing_cj.py`) |
|------|--------------------------------------|-------------------------------------|
| Multiple-of-4 check | Hard `raise ValueError` | Removed |
| Pod generation | Block-of-4 grouping | Wraparound modular arithmetic |
| Player assignment | Permutation search per 4-team group | `_best_player_slot_assignment()` per team |
| Anti-collusion snake | Produces groups of 4 | `_snake_interleave_order()` for ring ordering |
| Ghost player support | `ghost_player_ids` + penalty scoring | Removed |
| Old code | Active | Preserved as `_legacy_generate_round_with_pod_consistency_block()` |
| Validation | Checks team-set has 4 pods | Checks wraparound invariants |

---

## Verdict

| Scenario | Structurally works? | Tournament quality? |
|----------|--------------------|--------------------|
| N=5,6,7 | Yes | **Poor** — severe repeat overlap |
| N=8+ non-multiple of 4 (9,10,11,13...) | Yes | Decent — manageable overlap |
| N=8+ multiples of 4 | Yes | Good — comparable to current |

---

## If We Revisit This

The recommended approach would be:
1. Replace pairing engine's block-of-4 with wraparound (from CJ's version)
2. Expand `supported_team_counts` to all integers 8-40
3. Extend `determine_tournament_structure()` for non-standard counts
4. Update ~8 other validation/frontend/test locations
5. **Keep** `ghost_player_ids` (CJ removed it)
6. **Don't** support N < 8 unless a fundamentally different approach is found (team byes, 3-player team pods, etc.)
