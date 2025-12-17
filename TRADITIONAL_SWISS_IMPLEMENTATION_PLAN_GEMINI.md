# Implementation Plan - Traditional Swiss Pairing

## User Review Required

> [!IMPORTANT]
> This plan changes the core team grouping logic in `unified_swiss_pairing.py`. It prioritizes **Rank** (Score) over **Novelty** (Alphabetical availability) when finding opponents.

## Proposed Changes

### `unified_swiss_pairing.py`

#### [MODIFY] `_create_non_repeat_team_groups(self, teams, num_groups)`

**Goal:** Implement the "Traditional Swiss" logic with "Sort -> Pair -> Swap".

**Algorithm:**
1.  **Sort Teams:**
    -   Sort input `teams` list by Score (Descending).
    -   Let `sorted_teams = [Team_1, Team_2, ..., Team_N]`.

2.  **Pairing Loop (Greedy with Backtracking/Swapping):**
    -   While `sorted_teams` is not empty:
        -   Take the highest ranked team: `Anchor = sorted_teams[0]`.
        -   **Attempt 1 (Ideal Swiss):** Try to pair with the next 3 highest ranked teams (`sorted_teams[1..3]`).
        -   **Check Conflict:** Do any of these 4 teams have a repeat match history?
            -   **No Conflict:** Great! Form the group `[Anchor, T2, T3, T4]`. Remove them from pool.
            -   **Conflict Detected (Repeat Matchup):**
                -   **Swap Strategy:** Keep `Anchor`. Look down the list for the next eligible candidate (e.g., `sorted_teams[4]`, then `sorted_teams[5]`) to replace the conflicting team.
                -   "Move up" the lower-ranked team to form the pod.
                -   Recursive backtracking to ensure the *remaining* teams can still form valid groups.

3.  **Fallback Strategy (Unavoidable Team Repeat):**
    -   If the strict "No Team Repeat" search fails (returns `None`), we implicitly fall back to the existing logic in `_create_team_groups_for_round`, which pairs teams purely by Score.
    -   **Constraint:** In this fallback scenario, we rely on `_create_four_pods_for_team_group` to **swap players** within the assigned team pods to minimize/eliminate *player-level* repeat matchups.
    -   *Note: This player-level swapping logic is already present in `_create_four_pods_for_team_group`, we just need to verify it activates correctly during fallback.*

4.  **Final Verification:**
    -   Before returning the list of groups, run a global check.
    -   `_validate_groups(groups)`: Ensure 0 repeat team matchups across all generated groups.
    -   If validation fails, backtrack further or fall back to relaxed constraints (if permitted).

**Code Structure:**

```python
def _create_non_repeat_team_groups(self, teams: List[str], num_groups: int) -> Optional[List[List[str]]]:
    # 1. Sort by Score
    sorted_teams = self._sort_teams_by_score(teams)
    groups = []

    def backtrack(remaining_teams, current_groups):
        # ... logic to pick remaining_teams[0] (Anchor) ...
        # ... try to pair with remaining_teams[1], [2], [3] ...
        # ... if conflict, swap with [4], [5], etc. ...
    
    if backtrack(sorted_teams, groups):
        # 3. Final Verification
        if self._are_all_groups_valid(groups):
             return groups
    
    return None
```

## Verification Plan

### Automated Tests
I will run the comprehensive tournament simulation to ensure the logic holds for 16 teams.

```bash
python test_tournament_comprehensive.py --teams 16
```

### Manual Verification
1.  **Start Server:** `python tournament_dashboard.py`
2.  **Load Data:** 16 Teams.
3.  **Run Round 1:** Random pairings. Submit scores such that 4 teams clearly have perfect 5-0 or 4-0 records (e.g., Team A, B, C, D).
4.  **Run Round 2:**
    -   **Expected Result:** Team A, B, C, D should be paired together in "Pod 1" (assuming they haven't played).
    -   **Action:** Verify the pairing on the dashboard.
5.  **Force Conflict:**
    -   Manually edit database or submit scores such that Team A has already played Team B.
    -   **Expected Result:** Team A should NOT pair with Team B.
    -   Team A should pair with Team C, D, and Team E (the next highest).
    -   Team B should drop to the next pod.
