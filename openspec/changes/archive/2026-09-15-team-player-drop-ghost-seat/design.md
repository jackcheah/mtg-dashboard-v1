## Context

See proposal.md for motivation. The system currently supports player drops only in individual mode, where each player is a standalone entity removed entirely from all structures. Team mode has no drop mechanism. The pairing engine (`UnifiedSwissPairing`) enforces exactly 4 players per team (line 177-178) and creates pods by assigning one player per team from groups of 4 teams.

Key constraints shaping this design:
- The pairing engine's 4-player-per-team invariant is deeply embedded and used by pod creation, validation, and optimization.
- Team scores are derived by summing all members' `player_scores`. Changing this relationship is high-risk.
- Score submission validation is pod-size-aware (3-player vs 4-player rules). Ghost tables need hybrid handling.
- The backup/restore system serializes and replays pairing history for engine rehydration. Ghost state must survive this.

## Goals / Non-Goals

**Goals:**
- Allow individual player drops in team mode without disrupting the pairing engine's core invariants
- Ghost placeholder approach: dropped players keep their pairing slot, preserving pod-of-4 structure
- Auto-loss scoring for ghosts in both Western and Japanese modes
- Pairing optimizer avoids multi-ghost pods (higher priority than repeat avoidance)
- Full reversibility via undrop
- Consistent UX across dashboard, projector, and TopDeck export

**Non-Goals:**
- Team withdrawal (dropping the entire team) — separate future feature, out of scope
- Mid-round drops (only between rounds, matching individual mode's timing)
- Ghost player re-assignment to a different team
- Automatic replacement of dropped players with substitutes
- Changes to the individual mode drop mechanism (it stays as-is)

## Decisions

### Decision 1: Ghost stays in `self.teams` with an `is_dropped` flag

**Approach:** Add `"is_dropped": True` to the player dict within `self.teams[team_name]`. The ghost remains in all data structures — `self.teams`, `self.player_scores`, `self.participants`. A separate `self.dropped_team_players` dict tracks metadata (drop round, score at drop).

**Why not remove the player (like individual mode)?** Individual mode removes the player entirely and rebuilds the pairing engine. This works because each individual player is a synthetic "team of 1." In team mode, removing a player from the team would violate the 4-player invariant (line 177-178) and require deep changes to pod creation logic. Keeping the ghost in-place means:
- Zero changes to `UnifiedSwissPairing.__init__` validation
- Zero changes to `_create_four_pods_for_team_group` pod assignment
- Zero changes to Layer 1 (team grouping) or Layer 2 (bracket swaps)
- Only Layer 3 (permutation optimizer) needs a new penalty term

**Alternative considered:** Create a synthetic "Ghost Player" entity with a special team name. Rejected because it would break the no-teammates-in-same-pod constraint (ghost needs to remain on the original team for correct pod assignment).

### Decision 2: Player name changed to `<Name> (Dropped)` in the dict

**Approach:** Modify the `"Player Name"` field in the player dict to append ` (Dropped)`. Store the original name in `dropped_team_players[player_id]["original_name"]` for undrop restoration.

**Why modify the name field?** The name field is what all views render — tables, standings, projector, search. Modifying it once propagates automatically everywhere without changing any rendering logic. The `is_dropped` flag is for programmatic checks (scoring, validation).

**Alternative considered:** Keep the name unchanged and add `(Dropped)` only in the UI layer. Rejected because too many render paths exist (dashboard, projector, TopDeck, API endpoints) and each would need separate ghost-name logic.

### Decision 3: Backend injects ghost score, not frontend

**Approach:** Frontend submits only real players' scores (3 results for a 1-ghost table). Backend detects ghost players at the table via `is_dropped` flag, auto-injects their 0-point result, and validates the real players as an N-player pod.

**Why not frontend injection?** Backend authority prevents the frontend from submitting incorrect ghost scores. The backend already knows which players are ghosts (via `self.teams` data). This keeps the scoring logic's single source of truth in `tournament_dashboard.py`.

**Implementation in `submit_table_results`:**
1. Load table players from `self.tables[round_num][table_name]`
2. Partition into `real_players` and `ghost_players` based on `is_dropped`
3. Validate submitted results match `real_players` count
4. Validate real results using N-player pod rules (N = len(real_players))
5. Auto-inject ghost results: 0 pts Western, or calculated Japanese loss
6. Update `player_scores` for all players (real + ghost)
7. Call `calculate_team_scores()` as usual

### Decision 4: Japanese ghost contributes to pool and loses it

**Approach:** Ghost is included in the 7% pool calculation. Pool = sum of 7% of all 4 players' scores (3 real + 1 ghost). Winner takes the full pool. Ghost loses their 7%. Two real losers each lose their 7%.

**Why include ghost in pool?** This is a deliberate design choice to penalize teams with drops. The ghost's 7% contribution goes to the winning player at that table, creating:
- Extra reward for opponents at ghost tables (winner gets 4 contributions but only beats 2)
- Progressive score drain on the ghost (and thus the team) each round
- Strong deterrent against frivolous drops

**Math:** Ghost score decays as `score × 0.93^rounds_since_drop`.

### Decision 5: Multi-ghost avoidance via Layer 3 penalty weight

**Approach:** Add ghost-overlap detection to the permutation scoring function in `UnifiedSwissPairing`. When scoring a candidate permutation, count ghost players per pod. If any pod has 2+ ghosts, add a heavy penalty (e.g., 1000 per extra ghost, vs. 1-10 for repeat opponents). This makes the optimizer strongly prefer separating ghosts even at the cost of repeat opponents.

**Why not a hard constraint?** Hard constraints can make the system unsolvable in extreme cases (e.g., 5+ ghosts across 4 teams in one bracket). A high-weight soft constraint always finds a solution while strongly preferring separation.

**Implementation:** Pass `ghost_player_ids: Set[int]` to the pairing engine constructor. In `_score_permutation()` (or equivalent optimization function), count ghosts per pod and add penalty.

### Decision 6: Minimum 2 active players, below that = full team withdrawal

**Approach:** `drop_team_player()` checks active player count before allowing the drop. If the team has exactly 2 active players, the drop is rejected with a message to withdraw the team instead. Team withdrawal itself is out of scope — the operator would need to handle it manually (or a future feature).

**Why 2, not 1?** A team of 1 active + 3 ghosts creates a situation where every pod that player joins is essentially a 3-player pod, and the solo player auto-wins if all opponents are ghosts. This is degenerate gameplay. 2 active players is the minimum for meaningful team competition.

### Decision 7: Undrop restores player at current score

**Approach:** When undropping, remove `is_dropped` flag, restore original name, remove from `dropped_team_players` dict. The player's `player_scores` entry is whatever it currently is — which in Japanese mode may be lower than at drop time due to decay. The player resumes active play from the next round.

**Why not restore to score-at-drop?** In Japanese mode, the ghost has been contributing to (and losing from) pools each round. The score has changed legitimately through the system's mechanics. Restoring to the original score would create points from nothing. The current score is the honest state.

### Decision 8: Separate tracking dict from individual mode drops

**Approach:** Use `self.dropped_team_players` (new dict) rather than reusing `self.dropped_players` (existing individual mode dict). This avoids conflating two very different drop semantics — individual mode removes the player entirely while team mode keeps a ghost.

**Structure:**
```python
self.dropped_team_players = {
    player_id: {
        "original_name": "Alex",
        "team": "Team Alpha",
        "score_at_drop": 15,
        "dropped_after_round": 2
    }
}
```

## Risks / Trade-offs

**[Risk] Ghost score decay in Japanese mode may confuse operators** → Mitigation: The confirmation dialog explicitly warns about Japanese score decay. The undrop UI shows both score-at-drop and current score so operators can see the impact.

**[Risk] Multi-ghost pod creates degenerate 2-player game** → Mitigation: Pairing optimizer strongly avoids this. Only occurs in extreme scenarios (multiple teams each losing multiple players). Accept as rare edge case — 2 players can still play a valid pod.

**[Risk] TopDeck 3-player pod rows are unverified** → Mitigation: Already flagged in existing TopDeck integration. Ghost tables exported with warning. Operator should test in an unpublished TopDeck event. No new risk beyond what already existed for individual mode's 3-player pods.

**[Risk] Backup file format changes (new fields)** → Mitigation: Restore logic uses `.get()` with defaults for new fields. Old backups without `dropped_team_players` restore cleanly (empty dict). No migration needed.

**[Risk] Ghost opponent tracking inflates used_pairings counts** → Mitigation: Acceptable. The ghost's "opponents" are real players who sat at the table. Tracking them prevents re-pairing the same real players with the same ghost seat unnecessarily.

**[Trade-off] Name modification (`Player Name` field) vs. separate display logic** → Chose name modification for simplicity. The trade-off is that the original name is only available via `dropped_team_players` dict, not from the player dict directly. Undrop must restore it.
