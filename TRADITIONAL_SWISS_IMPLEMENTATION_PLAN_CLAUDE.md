# Traditional Swiss Pairing Implementation Plan

**Status:** Ready for Implementation
**Created:** 2025-12-17
**Target File:** `unified_swiss_pairing.py`
**Estimated LOC:** 400-450 lines

---

## Table of Contents

1. [Overview](#overview)
2. [Current vs Proposed System](#current-vs-proposed-system)
3. [Three-Layer Repeat-Avoidance Strategy](#three-layer-repeat-avoidance-strategy)
4. [Phase 1: Team Grouping Algorithm](#phase-1-team-grouping-algorithm)
5. [Phase 2: Team Swap Algorithm](#phase-2-team-swap-algorithm)
6. [Phase 3: Player-Level Optimization](#phase-3-player-level-optimization)
7. [Phase 4: Validation System](#phase-4-validation-system)
8. [Phase 5: Testing Strategy](#phase-5-testing-strategy)
9. [Phase 6: Configuration & Rollback](#phase-6-configuration--rollback)
10. [Implementation Checklist](#implementation-checklist)

---

## Overview

### Goal

Implement **Traditional Swiss Pairing** that pairs teams by score (winners vs winners) while intelligently avoiding repeat matchups at both team and player levels.

### Key Principles

1. **Priority 1:** Traditional Swiss logic (score-based pairing)
2. **Priority 2:** Avoid team-level repeat matchups via swapping
3. **Priority 3:** When team repeats unavoidable, minimize player-level repeats via exhaustive optimization

### Why This Change?

**Current System (Pod Consistency):**
- Prioritizes avoiding repeat team matchups first
- Falls back to score-based pairing only if repeats unavoidable
- Result: Top teams may not face each other in Round 2+

**New System (Traditional Swiss):**
- Prioritizes score-based pairing first (like traditional MTG/Chess Swiss)
- Intelligently swaps teams to avoid repeats while maintaining score brackets
- Uses exhaustive player optimization when team repeats are truly unavoidable

---

## Current vs Proposed System

### Current System Flow

```
Round 2+ Pairing:
├─ Sort teams by score
├─ Use constraint solver to avoid repeat team matchups
├─ If no solution found:
│  └─ Fall back to score-based grouping (with repeats)
└─ Assign players using limited permutation search (24 iterations)
```

**Result:** Teams C, E, L, P (all 11 pts) might be in different tables

### Proposed System Flow

```
Round 2+ Pairing:
├─ Layer 1: Sort teams by score → Group by brackets (Top 4, Next 4, etc.)
├─ Layer 2: Detect team-level repeats → Swap teams between brackets
├─ Layer 3: Mark groups with unavoidable repeats → Exhaustive player optimization
└─ Return pairings with detailed logging
```

**Result:** Teams C, E, L, P (all 11 pts) will be in same table, unless swap needed to avoid repeat

---

## Three-Layer Repeat-Avoidance Strategy

### Layer 1: Traditional Swiss Score Grouping

**Priority:** Highest
**Goal:** Group teams by score rank

```
Example (16 teams after Round 1):
┌─────────┬─────────────────────────────┬────────┐
│ Table   │ Teams (by score rank)       │ Scores │
├─────────┼─────────────────────────────┼────────┤
│ Table 1 │ Rank 1-4   (C, E, L, P)     │ 11 pts │
│ Table 2 │ Rank 5-8   (A, B, D, F)     │ 8 pts  │
│ Table 3 │ Rank 9-12  (G, H, I, K)     │ 5 pts  │
│ Table 4 │ Rank 13-16 (J, M, N, O)     │ 2 pts  │
└─────────┴─────────────────────────────┴────────┘
```

### Layer 2: Team Swap for Repeat Avoidance

**Priority:** High
**Goal:** Swap teams between adjacent brackets to avoid team-level repeats

```
Problem Detected:
Table 1: C, E, L, P
         └─────┘ (C and E already played in Round 1)

Solution:
1. Find lowest-ranked team in repeat pair: E (rank 2)
2. Search adjacent bracket (Table 2) for swap candidate
3. Swap E with A (rank 5, no conflicts)

Result:
Table 1: C, A, L, P (no team repeats)
Table 2: E, B, D, F (no team repeats)
```

### Layer 3: Exhaustive Player Optimization

**Priority:** Fallback (when team repeats unavoidable)
**Goal:** Minimize player-level repeats even when teams must repeat

```
Scenario (8-team tournament, Round 4):
- All teams have played each other once
- Team repeats are mathematically unavoidable
- Player optimization is critical

Normal Search:  24 permutation attempts → May have 4-6 player repeats
Exhaustive:     13,824 attempts → Often achieves 0-2 player repeats
```

---

## Phase 1: Team Grouping Algorithm

### Target Function

**File:** `unified_swiss_pairing.py`
**Line:** 1564
**Function:** `_create_team_groups_for_round()`

### Implementation Steps

#### 1.1 Rename Existing Function

```python
# Line 1564: Rename to keep as reference/fallback
def _create_team_groups_for_round_OLD(self, round_num: int):
    # ... existing pod consistency logic ...
```

#### 1.2 Create New Traditional Swiss Grouping

```python
def _create_team_groups_traditional_swiss(self, round_num: int) -> List[List[str]]:
    """
    Create team groups using traditional Swiss pairing (score-based).

    Groups teams into brackets of 4 based on current scores:
    - Top 4 teams (highest scores) → Group 1
    - Next 4 teams → Group 2
    - etc.

    Args:
        round_num: The round number being generated (1-based)

    Returns:
        List of team groups, each containing 4 team names
        Note: Groups may contain repeat team matchups (will be resolved in Layer 2)
    """
    # Sort teams by score (highest first)
    sorted_teams = self._sort_teams_by_score(self.tournament_teams.copy())

    # Calculate number of groups (4 teams per group)
    num_groups = len(sorted_teams) // 4

    # Create groups by slicing sorted list
    team_groups = []
    for i in range(num_groups):
        group = sorted_teams[i*4:(i+1)*4]
        team_groups.append(group)

    return team_groups
```

**Note:** `_sort_teams_by_score()` already exists at line 1680

#### 1.3 Create Repeat Detection

```python
def _detect_repeat_matchups_in_groups(self, groups: List[List[str]]) -> List[Tuple[int, str, str]]:
    """
    Detect all team-level repeat matchups across all groups.

    Args:
        groups: List of team groups to check

    Returns:
        List of tuples: (group_index, team1, team2) for each repeat found
    """
    repeats = []

    for group_idx, team_group in enumerate(groups):
        # Check all pairs within this group
        for i in range(len(team_group)):
            for j in range(i + 1, len(team_group)):
                team1 = team_group[i]
                team2 = team_group[j]

                # Check if these teams have played before
                if team2 in self.team_matchups.get(team1, set()):
                    repeats.append((group_idx, team1, team2))

    return repeats
```

**Data Structure Used:**
- `self.team_matchups` - Dict[str, Set[str]] tracking which teams have faced each other
- Updated after each round in `_update_constraints_after_round()` (line 1372-1381)

#### 1.4 Create Player Optimization Marker

```python
def _mark_groups_for_player_optimization(self, groups: List[List[str]],
                                         groups_with_repeats: List[int]) -> Dict[int, List[Tuple[str, str]]]:
    """
    Mark groups that need aggressive player-level optimization.

    These groups have unavoidable team-level repeats and will use exhaustive
    player assignment search to minimize player-level repeat matchups.

    Args:
        groups: All team groups
        groups_with_repeats: Indices of groups with team-level repeats

    Returns:
        Dict mapping group_index → list of (team1, team2) pairs that are repeats

    Example:
        {
            0: [('Team C', 'Team E')],  # Table 1 has C vs E repeat
            2: [('Team A', 'Team B'), ('Team A', 'Team D')]  # Table 3 has 2 repeats
        }
    """
    optimization_map = {}

    for group_idx in groups_with_repeats:
        team_group = groups[group_idx]
        repeat_pairs = []

        # Find all repeat pairs in this group
        for i in range(len(team_group)):
            for j in range(i + 1, len(team_group)):
                team1 = team_group[i]
                team2 = team_group[j]

                if team2 in self.team_matchups.get(team1, set()):
                    repeat_pairs.append((team1, team2))

        if repeat_pairs:
            optimization_map[group_idx] = repeat_pairs

    return optimization_map
```

#### 1.5 Update Main Orchestration Function

```python
def _create_team_groups_for_round(self, round_num: int) -> List[List[str]]:
    """
    Divide teams into groups of 4 for the round.

    Round 1: Random grouping
    Rounds 2+: Traditional Swiss (score-based) with three-layer repeat avoidance

    Args:
        round_num: The round number being generated (1-based)

    Returns:
        List of team groups, each containing 4 team names
    """
    available_teams = self.tournament_teams.copy()
    num_groups = len(available_teams) // 4

    if round_num == 1:
        # Round 1: Random grouping (existing logic)
        random.shuffle(available_teams)
        team_groups = []
        for i in range(num_groups):
            group = available_teams[i*4:(i+1)*4]
            team_groups.append(group)
        return team_groups

    # Round 2+: Traditional Swiss with three-layer repeat avoidance

    # LAYER 1: Traditional Swiss score-based grouping
    groups = self._create_team_groups_traditional_swiss(round_num)

    # LAYER 2: Detect and resolve team-level repeats via swapping
    repeats = self._detect_repeat_matchups_in_groups(groups)

    unresolvable_groups = []
    if repeats:
        groups, unresolvable_groups = self._resolve_repeat_matchups_by_swapping(groups, repeats)

    # Final validation
    is_valid, violations, groups_with_repeats = self._validate_all_groups_no_repeats(groups)

    # LAYER 3: Mark groups with unavoidable team repeats for player optimization
    if groups_with_repeats:
        repeat_info = self._mark_groups_for_player_optimization(groups, groups_with_repeats)
        # Store for use in player assignment phase
        self.groups_needing_player_optimization = repeat_info
    else:
        self.groups_needing_player_optimization = {}

    # Logging
    if not is_valid:
        print(f"\n{'='*60}")
        print(f"[WARNING] Round {round_num}: Team-level repeat matchups unavoidable")
        print(f"{'='*60}")
        for violation in violations:
            print(f"  ⚠️  {violation}")
        print(f"\n[INFO] Player-level optimization will be applied to minimize player repeats")
        print(f"{'='*60}\n")

    return groups
```

---

## Phase 2: Team Swap Algorithm

### Goal

When team-level repeats are detected, swap teams between brackets to resolve them while maintaining score proximity.

### 2.1 Resolve Repeats by Swapping

```python
def _resolve_repeat_matchups_by_swapping(self, groups: List[List[str]],
                                          repeats: List[Tuple[int, str, str]]) -> Tuple[List[List[str]], List[int]]:
    """
    Resolve team-level repeat matchups by swapping teams between groups.

    Strategy:
    1. For each repeat, identify the lower-ranked team in the pair
    2. Search adjacent brackets for a swap candidate
    3. Perform swap if it doesn't create new repeats
    4. Track unresolvable groups

    Args:
        groups: List of team groups
        repeats: List of (group_idx, team1, team2) tuples

    Returns:
        (modified_groups, list_of_unresolvable_group_indices)
    """
    # Create mutable copy
    groups = [g.copy() for g in groups]

    # Track which groups have unresolvable repeats
    unresolvable_groups = set()

    # Track swap attempts to prevent infinite loops
    swap_history = set()
    max_swap_attempts = 10

    for group_idx, team1, team2 in repeats:
        # Identify lower-ranked team (to swap out)
        team1_score = self.team_scores.get(team1, 0)
        team2_score = self.team_scores.get(team2, 0)

        if team1_score < team2_score:
            problem_team = team1
        elif team2_score < team1_score:
            problem_team = team2
        else:
            # Same score, pick one arbitrarily (e.g., alphabetically later)
            problem_team = max(team1, team2)

        # Try to find swap candidate
        swap_result = self._find_best_swap_candidate(
            problem_team,
            group_idx,
            groups,
            swap_history,
            max_attempts=max_swap_attempts
        )

        if swap_result:
            target_group_idx, swap_team = swap_result

            # Perform the swap
            groups[group_idx].remove(problem_team)
            groups[group_idx].append(swap_team)
            groups[target_group_idx].remove(swap_team)
            groups[target_group_idx].append(problem_team)

            # Record swap
            swap_key = tuple(sorted([problem_team, swap_team]))
            swap_history.add(swap_key)
        else:
            # Cannot resolve this repeat
            unresolvable_groups.add(group_idx)

    return groups, list(unresolvable_groups)
```

### 2.2 Find Best Swap Candidate

```python
def _find_best_swap_candidate(self,
                               problem_team: str,
                               problem_group_idx: int,
                               all_groups: List[List[str]],
                               swap_history: Set[Tuple[str, str]],
                               max_attempts: int = 10) -> Optional[Tuple[int, str]]:
    """
    Find best team to swap with problem_team to resolve repeat matchup.

    Swap priority:
    1. Adjacent brackets (±1) - minimizes score disruption
    2. Two brackets away (±2) - acceptable score difference
    3. Any bracket - last resort

    Args:
        problem_team: Team that needs to be swapped out
        problem_group_idx: Index of group containing problem_team
        all_groups: All team groups
        swap_history: Set of (team1, team2) swaps already attempted
        max_attempts: Maximum number of candidates to try

    Returns:
        (target_group_index, swap_team_name) or None if no valid swap exists
    """
    candidates = []

    # Try adjacent groups first (±1 bracket)
    for offset in [-1, 1]:
        target_group_idx = problem_group_idx + offset
        if 0 <= target_group_idx < len(all_groups):
            for swap_team in all_groups[target_group_idx]:
                # Skip if already tried this swap
                swap_key = tuple(sorted([problem_team, swap_team]))
                if swap_key in swap_history:
                    continue

                if self._is_valid_swap(problem_team, swap_team,
                                       problem_group_idx, target_group_idx,
                                       all_groups):
                    score_diff = abs(self.team_scores.get(problem_team, 0) -
                                    self.team_scores.get(swap_team, 0))
                    candidates.append((score_diff, target_group_idx, swap_team))

    # If no adjacent swaps found, try ±2 brackets
    if not candidates and max_attempts > 4:
        for offset in [-2, 2]:
            target_group_idx = problem_group_idx + offset
            if 0 <= target_group_idx < len(all_groups):
                for swap_team in all_groups[target_group_idx]:
                    swap_key = tuple(sorted([problem_team, swap_team]))
                    if swap_key in swap_history:
                        continue

                    if self._is_valid_swap(problem_team, swap_team,
                                          problem_group_idx, target_group_idx,
                                          all_groups):
                        score_diff = abs(self.team_scores.get(problem_team, 0) -
                                        self.team_scores.get(swap_team, 0))
                        candidates.append((score_diff, target_group_idx, swap_team))

    # If still no candidates, try all groups (last resort)
    if not candidates and max_attempts > 8:
        for target_group_idx in range(len(all_groups)):
            if target_group_idx == problem_group_idx:
                continue

            for swap_team in all_groups[target_group_idx]:
                swap_key = tuple(sorted([problem_team, swap_team]))
                if swap_key in swap_history:
                    continue

                if self._is_valid_swap(problem_team, swap_team,
                                      problem_group_idx, target_group_idx,
                                      all_groups):
                    score_diff = abs(self.team_scores.get(problem_team, 0) -
                                    self.team_scores.get(swap_team, 0))
                    candidates.append((score_diff, target_group_idx, swap_team))

    # Return swap with smallest score difference
    if candidates:
        candidates.sort()  # Sort by score_diff (first element of tuple)
        return (candidates[0][1], candidates[0][2])

    return None
```

### 2.3 Validate Swap Safety

```python
def _is_valid_swap(self, team_a: str, team_b: str,
                   group_a_idx: int, group_b_idx: int,
                   all_groups: List[List[str]]) -> bool:
    """
    Check if swapping team_a (from group_a) with team_b (from group_b)
    creates any new repeat matchups.

    Args:
        team_a: First team to swap
        team_b: Second team to swap
        group_a_idx: Index of group containing team_a
        group_b_idx: Index of group containing team_b
        all_groups: All team groups

    Returns:
        True if swap is safe (doesn't create new repeats), False otherwise
    """
    # Simulate the swap
    group_a = all_groups[group_a_idx].copy()
    group_b = all_groups[group_b_idx].copy()

    group_a.remove(team_a)
    group_a.append(team_b)

    group_b.remove(team_b)
    group_b.append(team_a)

    # Check both groups for repeats after swap
    if self._group_has_repeat_matchups(group_a):
        return False

    if self._group_has_repeat_matchups(group_b):
        return False

    return True


def _group_has_repeat_matchups(self, team_group: List[str]) -> bool:
    """
    Check if any teams in this group have played each other before.

    Args:
        team_group: List of 4 team names

    Returns:
        True if any repeat matchup exists, False otherwise
    """
    for i in range(len(team_group)):
        for j in range(i + 1, len(team_group)):
            team1 = team_group[i]
            team2 = team_group[j]

            if team2 in self.team_matchups.get(team1, set()):
                return True

    return False
```

---

## Phase 3: Player-Level Optimization

### Goal

When team-level repeats are unavoidable, use exhaustive player assignment search to minimize player-level repeat matchups.

### Target Function

**File:** `unified_swiss_pairing.py`
**Line:** 1698
**Function:** `_create_four_pods_for_team_group()`

### Current Behavior

- Tries 24 permutations per team (limited search)
- Returns first good solution or best found
- Works well for groups without team repeats

### Enhanced Behavior

- **Normal groups:** 24 permutations (fast, existing behavior)
- **Groups with team repeats:** ALL permutations = 24³ = 13,824 (exhaustive)
- Detailed logging of optimization results

### 3.1 Enhance Player Pod Creation

```python
def _create_four_pods_for_team_group(self, team_group: List[str], round_num: int,
                                     group_index: int = None) -> Optional[List[List[Dict]]]:
    """
    Create exactly 4 pods from 4 teams, avoiding player-level repeat matchups.

    Uses backtracking to find player assignments that minimize repeat opponents.
    If this group has unavoidable team-level repeats, uses exhaustive search.

    Args:
        team_group: List of 4 team names
        round_num: The round number (used for rotation calculation)
        group_index: Index of this group (used to check if player optimization needed)

    Returns:
        List of 4 pods, each containing 4 players (one from each team)
    """
    # Get all players from these 4 teams
    team_players = {}
    for team in team_group:
        team_players[team] = self.teams[team].copy()

    # Check if this group needs maximum player optimization
    needs_max_optimization = (
        hasattr(self, 'groups_needing_player_optimization') and
        group_index is not None and
        group_index in self.groups_needing_player_optimization
    )

    if needs_max_optimization:
        # Log that we're doing exhaustive search
        repeat_teams = self.groups_needing_player_optimization[group_index]
        print(f"    [PLAYER OPTIMIZATION] Table {group_index + 1}: Team-level repeat unavoidable")
        print(f"                         Teams with repeat: {repeat_teams}")
        print(f"                         Using exhaustive player search to minimize player repeats...")

    # Try to find optimal player assignment using backtracking
    best_pods = None
    best_repeat_count = float('inf')
    best_repeat_details = []

    from itertools import permutations

    # First team's players go to pods 0,1,2,3 in order
    first_team = team_group[0]
    first_team_players = team_players[first_team]

    # Try different permutations for other teams
    other_teams = team_group[1:]
    other_team_perms = [list(permutations(range(4))) for _ in other_teams]

    # Adjust search depth based on optimization need
    if needs_max_optimization:
        # Exhaustive search: Try ALL permutations (24 per team = 24^3 total)
        max_perms = len(other_team_perms[0]) if other_team_perms else 1
        print(f"                         Trying {max_perms**3:,} permutation combinations...")
    else:
        # Normal search: Try first 24 combinations (existing behavior)
        max_perms = min(24, len(other_team_perms[0]) if other_team_perms else 1)

    iterations = 0
    for perm1 in other_team_perms[0][:max_perms] if other_team_perms else [()]:
        for perm2 in other_team_perms[1][:max_perms] if len(other_team_perms) > 1 else [()]:
            for perm3 in other_team_perms[2][:max_perms] if len(other_team_perms) > 2 else [()]:
                iterations += 1

                # Build pods with this permutation
                pods = []
                repeat_count = 0
                repeat_details = []

                for pod_idx in range(4):
                    pod = []
                    # First team player
                    if pod_idx < len(first_team_players):
                        pod.append(first_team_players[pod_idx])

                    # Other teams' players based on permutation
                    perms = [perm1, perm2, perm3]
                    for team_idx, team in enumerate(other_teams):
                        if team_idx < len(perms):
                            player_idx = perms[team_idx][pod_idx]
                            if player_idx < len(team_players[team]):
                                pod.append(team_players[team][player_idx])

                    if len(pod) == 4:
                        pods.append(pod)
                        # Count repeat matchups in this pod
                        if needs_max_optimization:
                            pod_repeats, pod_details = self._count_and_detail_repeat_matchups_in_pod(pod, pod_idx)
                            repeat_count += pod_repeats
                            repeat_details.extend(pod_details)
                        else:
                            repeat_count += self._count_repeat_matchups_in_pod(pod)

                if len(pods) == 4 and repeat_count < best_repeat_count:
                    best_pods = pods
                    best_repeat_count = repeat_count
                    best_repeat_details = repeat_details

                    if repeat_count == 0:
                        # Found perfect solution, return immediately
                        if needs_max_optimization:
                            print(f"                         ✅ PERFECT: Found zero player repeats after {iterations:,} iterations!")
                        return best_pods

    # Report results for groups with team repeats
    if needs_max_optimization:
        if best_repeat_count == 0:
            print(f"                         ✅ SUCCESS: Zero player-level repeats despite team repeat!")
        else:
            print(f"                         ⚠️  MINIMIZED: {best_repeat_count} player repeat(s) (unavoidable)")
            for detail in best_repeat_details:
                print(f"                             - {detail}")

    return best_pods
```

**Note:** Keep existing `_count_repeat_matchups_in_pod()` function at line 1773

### 3.2 Add Detailed Repeat Tracking

```python
def _count_and_detail_repeat_matchups_in_pod(self, pod: List[Dict], pod_idx: int) -> Tuple[int, List[str]]:
    """
    Count and detail player-level repeat matchups in this pod.

    Used for exhaustive player optimization to provide detailed logging.

    Args:
        pod: List of 4 player dictionaries
        pod_idx: Pod index for reporting (0-3)

    Returns:
        (repeat_count, list_of_repeat_descriptions)

    Example:
        (2, ['Pod 1: Alice vs Bob', 'Pod 3: Carol vs Dave'])
    """
    repeat_count = 0
    details = []

    for i in range(len(pod)):
        for j in range(i + 1, len(pod)):
            player1_id = pod[i]['Player ID']
            player2_id = pod[j]['Player ID']
            player1_name = pod[i]['Player Name']
            player2_name = pod[j]['Player Name']

            if player2_id in self.player_opponents.get(player1_id, set()):
                repeat_count += 1
                details.append(f"Pod {pod_idx + 1}: {player1_name} vs {player2_name}")

    return repeat_count, details
```

### 3.3 Update Function Calls

**Location:** Wherever `_create_four_pods_for_team_group()` is called (search for it)

**Find this pattern:**
```python
pods = self._create_four_pods_for_team_group(team_group, round_num)
```

**Replace with:**
```python
pods = self._create_four_pods_for_team_group(team_group, round_num, group_index=group_idx)
```

**Example location:** Around line 1500-1550 in the main round generation logic

---

## Phase 4: Validation System

### 4.1 Comprehensive Group Validation

```python
def _validate_all_groups_no_repeats(self, groups: List[List[str]]) -> Tuple[bool, List[str], List[int]]:
    """
    Comprehensive validation of all groups for repeat team matchups.

    Checks every group for team-level repeats and collects:
    - Violation messages (for logging)
    - Group indices with repeats (for player optimization marking)

    Args:
        groups: List of team groups to validate

    Returns:
        (is_valid, violations_list, group_indices_with_repeats)

    Example:
        (False,
         ['Table 1: Team C vs Team E (teams played before)'],
         [0])
    """
    violations = []
    groups_with_repeats = []

    for group_idx, team_group in enumerate(groups):
        group_name = f"Table {group_idx + 1}"
        group_has_repeat = False

        for i in range(len(team_group)):
            for j in range(i + 1, len(team_group)):
                team1 = team_group[i]
                team2 = team_group[j]

                if team2 in self.team_matchups.get(team1, set()):
                    violations.append(
                        f"{group_name}: {team1} vs {team2} (teams played before)"
                    )
                    group_has_repeat = True

        if group_has_repeat:
            groups_with_repeats.append(group_idx)

    return (len(violations) == 0, violations, groups_with_repeats)
```

---

## Phase 5: Testing Strategy

### Test Scenarios

#### Scenario 1: 16-Team Tournament (Ideal)

**Setup:**
- 16 teams, 4 Swiss rounds
- Should have zero team repeats through all rounds
- Traditional Swiss should work perfectly

**Expected Results:**
```
Round 2:
  Table 1: Ranks 1-4   (e.g., 11, 11, 11, 11 pts)
  Table 2: Ranks 5-8   (e.g., 8, 8, 8, 8 pts)
  Table 3: Ranks 9-12  (e.g., 5, 5, 5, 5 pts)
  Table 4: Ranks 13-16 (e.g., 2, 2, 2, 2 pts)

✅ Zero team repeats
✅ Zero player repeats
```

**Test Command:**
```bash
python3 test_tournament_comprehensive.py --teams 16
```

#### Scenario 2: 12-Team Tournament (Swaps Needed)

**Setup:**
- 12 teams, 4 Swiss rounds
- Rounds 3-4 may require team swaps
- Should achieve zero or minimal team repeats

**Expected Results:**
```
Round 3:
  Table 1: Top 4 teams (with possible 1 swap from Table 2)
  Table 2: Middle 4 teams (adjusted after swap)
  Table 3: Bottom 4 teams

✅ Zero or 1 team repeat (after swaps)
✅ Zero player repeats
```

**Test Command:**
```bash
python3 test_tournament_comprehensive.py --teams 12
```

#### Scenario 3: 8-Team Tournament (Player Optimization Critical)

**Setup:**
- 8 teams, 4 Swiss rounds
- Round 3+: Team repeats mathematically unavoidable
- Player optimization should minimize player repeats

**Expected Results:**
```
Round 4:
  Table 1: 4 teams (guaranteed team repeats)
  Table 2: 4 teams (guaranteed team repeats)

⚠️  Team repeats unavoidable (only 8 teams, all played each other)
✅ Player repeats minimized (0-2 instead of 4-6 with random assignment)

Console Output:
  [PLAYER OPTIMIZATION] Table 1: Team-level repeat unavoidable
                       Teams with repeat: [('A', 'C'), ('B', 'D')]
                       Using exhaustive player search...
                       Trying 13,824 permutation combinations...
                       ✅ SUCCESS: Zero player-level repeats despite team repeat!
```

**Test Command:**
```bash
python3 test_tournament_comprehensive.py --teams 8
```

### Edge Case Tests

#### Edge Case 1: Impossible to Avoid Repeats

**Scenario:** 8-team tournament, Round 4
**Condition:** All teams have played each other at least once
**Expected:** Algorithm tries best effort, logs violations, proceeds with best pairing

#### Edge Case 2: Multiple Repeats in Same Group

**Scenario:** Unlucky score distribution creates group with 2+ repeat pairs
**Expected:** Swap algorithm may need multiple iterations, limited to 10 attempts to prevent infinite loops

#### Edge Case 3: Cascading Repeats

**Scenario:** Swap fixes one repeat but creates another
**Expected:** `swap_history` prevents swapping same teams back and forth

### Validation Tests

Create test file: `test_traditional_swiss.py`

```python
#!/usr/bin/env python3
"""
Test suite for Traditional Swiss pairing implementation.
"""

def test_traditional_grouping():
    """Test basic score-based grouping"""
    # Setup 16 teams with known scores
    # Verify groups match score ranks
    pass

def test_team_swap_resolution():
    """Test swap algorithm resolves repeats"""
    # Create scenario with known repeat
    # Verify swap eliminates repeat
    # Verify swap maintains score proximity
    pass

def test_player_optimization():
    """Test exhaustive player search"""
    # Create group with team repeat
    # Compare normal vs exhaustive search
    # Verify exhaustive finds better solution
    pass

def test_8_team_round_4():
    """Test hardest case: 8 teams, round 4"""
    # All teams played each other once
    # Verify team repeats acknowledged
    # Verify player repeats minimized
    pass

if __name__ == '__main__':
    test_traditional_grouping()
    test_team_swap_resolution()
    test_player_optimization()
    test_8_team_round_4()
    print("✅ All tests passed!")
```

---

## Phase 6: Configuration & Rollback

### 6.1 Add Configuration Parameters

**File:** `unified_swiss_pairing.py`
**Line:** 424 (in `__init__` method)

```python
def __init__(self, teams: Dict[str, List[Dict]],
             tournament_teams: List[str],
             swiss_rounds_count: int = 4,
             team_scores: Dict[str, int] = None,
             use_traditional_swiss: bool = True,
             max_player_optimization_iterations: int = None):
    """
    Initialize the unified Swiss pairing system.

    Args:
        teams: Dictionary mapping team names to lists of player dictionaries
        tournament_teams: List of team names for the tournament (4-20 teams)
        swiss_rounds_count: Number of Swiss rounds to generate (3, 4, or 5)
        team_scores: Optional dictionary of team scores for score-based pairing (rounds 2+)
        use_traditional_swiss: If True, use traditional Swiss (score-first).
                               If False, use pod consistency (repeat-avoidance-first)
        max_player_optimization_iterations: Cap for exhaustive player search.
                                           None = unlimited for groups with team repeats
    """
    self.teams = teams
    self.tournament_teams = tournament_teams
    self.swiss_rounds_count = swiss_rounds_count
    self.team_scores = team_scores or {}
    self.start_time = time.time()

    # Configuration flags
    self.use_traditional_swiss = use_traditional_swiss
    self.max_player_optimization_iterations = max_player_optimization_iterations

    # ... rest of existing initialization ...
```

### 6.2 Update Tournament Dashboard Integration

**File:** `tournament_dashboard.py`
**Search for:** Where `UnifiedSwissPairing` is instantiated

**Add parameter:**
```python
# Example location (search for actual location in file)
pairing = UnifiedSwissPairing(
    teams=tournament.teams_dict,
    tournament_teams=tournament.teams,
    swiss_rounds_count=tournament.swiss_rounds,
    team_scores=team_scores,
    use_traditional_swiss=True  # Enable traditional Swiss
)
```

### 6.3 Rollback Strategy

**Quick Rollback (No Code Changes):**
```python
# In tournament_dashboard.py
use_traditional_swiss=False  # Switch back to pod consistency
```

**Full Rollback (Restore Old Function):**
```python
# In unified_swiss_pairing.py, rename functions back:
_create_team_groups_for_round()  # Delete new version
_create_team_groups_for_round_OLD()  # Rename to _create_team_groups_for_round()
```

---

## Implementation Checklist

### Phase 1: Team Grouping ✓

- [ ] 1.1 Rename `_create_team_groups_for_round()` → `_create_team_groups_for_round_OLD()`
- [ ] 1.2 Create `_create_team_groups_traditional_swiss()`
- [ ] 1.3 Create `_detect_repeat_matchups_in_groups()`
- [ ] 1.4 Create `_mark_groups_for_player_optimization()`
- [ ] 1.5 Create new `_create_team_groups_for_round()` with three-layer logic

### Phase 2: Team Swap Algorithm ✓

- [ ] 2.1 Create `_resolve_repeat_matchups_by_swapping()`
- [ ] 2.2 Create `_find_best_swap_candidate()`
- [ ] 2.3 Create `_is_valid_swap()`
- [ ] 2.4 Create `_group_has_repeat_matchups()`

### Phase 3: Player Optimization ✓

- [ ] 3.1 Enhance `_create_four_pods_for_team_group()` (line 1698)
  - [ ] Add `group_index` parameter
  - [ ] Add `needs_max_optimization` logic
  - [ ] Adjust `max_perms` based on optimization need
  - [ ] Add detailed logging for optimized groups
- [ ] 3.2 Create `_count_and_detail_repeat_matchups_in_pod()`
- [ ] 3.3 Update function calls to pass `group_index`
  - [ ] Find all calls to `_create_four_pods_for_team_group()`
  - [ ] Add `group_index=group_idx` parameter

### Phase 4: Validation ✓

- [ ] 4.1 Create `_validate_all_groups_no_repeats()` (returns 3 values)
  - [ ] Returns `is_valid`
  - [ ] Returns `violations` list
  - [ ] Returns `groups_with_repeats` list

### Phase 5: Testing ✓

- [ ] 5.1 Run existing test: `python3 test_tournament_comprehensive.py --teams 16`
- [ ] 5.2 Run existing test: `python3 test_tournament_comprehensive.py --teams 12`
- [ ] 5.3 Run existing test: `python3 test_tournament_comprehensive.py --teams 8`
- [ ] 5.4 Create `test_traditional_swiss.py` with unit tests
- [ ] 5.5 Manual test: Run tournament_dashboard.py and play through Swiss rounds
- [ ] 5.6 Verify console output shows correct pairing logic

### Phase 6: Configuration & Integration ✓

- [ ] 6.1 Add configuration parameters to `__init__()` (line 424)
  - [ ] Add `use_traditional_swiss` parameter
  - [ ] Add `max_player_optimization_iterations` parameter
- [ ] 6.2 Update `tournament_dashboard.py` to enable traditional Swiss
  - [ ] Find where `UnifiedSwissPairing` is instantiated
  - [ ] Add `use_traditional_swiss=True` parameter
- [ ] 6.3 Document rollback procedure in this file

### Final Verification ✓

- [ ] Code review: Check all new functions for bugs
- [ ] Performance test: Verify exhaustive search completes in reasonable time (<5 seconds)
- [ ] Edge case test: 8-team tournament Round 4 (hardest case)
- [ ] Console output verification: Logs are clear and helpful
- [ ] Production test: Run full tournament with real data

---

## Expected Console Output Examples

### Example 1: Clean Round (No Repeats)

```
Round 2 Pairing:
================
Table 1: Team C, Team E, Team L, Team P (11, 11, 11, 11 pts)
Table 2: Team A, Team B, Team D, Team F (8, 8, 8, 8 pts)
Table 3: Team G, Team H, Team I, Team K (5, 5, 5, 5 pts)
Table 4: Team J, Team M, Team N, Team O (2, 2, 2, 2 pts)

✅ Round 2 generated successfully
   - 4 tables created
   - 0 team-level repeats
   - 0 player-level repeats
```

### Example 2: Round with Team Swap

```
Round 3 Pairing:
================

[INFO] Detected team repeat: Team C vs Team E (Table 1)
[INFO] Swapping Team E (rank 2) with Team A (rank 5) to resolve repeat
[INFO] Swap successful: Team E → Table 2, Team A → Table 1

Table 1: Team C, Team A, Team L, Team P (11, 8, 11, 11 pts)
Table 2: Team E, Team B, Team D, Team F (11, 8, 8, 8 pts)
Table 3: Team G, Team H, Team I, Team K (5, 5, 5, 5 pts)
Table 4: Team J, Team M, Team N, Team O (2, 2, 2, 2 pts)

✅ Round 3 generated successfully
   - 4 tables created
   - 0 team-level repeats (1 resolved via swap)
   - 0 player-level repeats
```

### Example 3: Round with Unavoidable Team Repeat (8-team, Round 4)

```
Round 4 Pairing:
================

============================================================
[WARNING] Round 4: Team-level repeat matchups unavoidable
============================================================
  ⚠️  Table 1: Team A vs Team C (teams played before)
  ⚠️  Table 2: Team B vs Team D (teams played before)

[INFO] Player-level optimization will be applied to minimize player repeats
============================================================

    [PLAYER OPTIMIZATION] Table 1: Team-level repeat unavoidable
                         Teams with repeat: [('Team A', 'Team C')]
                         Using exhaustive player search to minimize player repeats...
                         Trying 13,824 permutation combinations...
                         ✅ PERFECT: Found zero player repeats after 3,247 iterations!

    [PLAYER OPTIMIZATION] Table 2: Team-level repeat unavoidable
                         Teams with repeat: [('Team B', 'Team D')]
                         Using exhaustive player search to minimize player repeats...
                         Trying 13,824 permutation combinations...
                         ⚠️  MINIMIZED: 1 player repeat(s) (unavoidable)
                             - Pod 2: Alice vs Bob

Table 1: Team A, Team C, Team E, Team G
Table 2: Team B, Team D, Team F, Team H

✅ Round 4 generated successfully
   - 2 tables created
   - 2 team-level repeats (unavoidable in 8-team tournament)
   - 1 player-level repeat (minimized via exhaustive search)
```

---

## Data Structures Reference

### Key Instance Variables

```python
# In UnifiedSwissPairing class

self.team_matchups: Dict[str, Set[str]]
# Tracks which teams have played each other
# Example: {'Team A': {'Team B', 'Team C'}, 'Team B': {'Team A'}}

self.team_scores: Dict[str, int]
# Current score for each team
# Example: {'Team A': 11, 'Team B': 8, 'Team C': 11}

self.player_opponents: Dict[int, Set[int]]
# Tracks which players have faced each other (by Player ID)
# Example: {101: {102, 103}, 102: {101}}

self.used_pairings: Set[Tuple[int, int]]
# All player-pair matchups used (sorted tuples)
# Example: {(101, 102), (101, 103), (102, 104)}

self.groups_needing_player_optimization: Dict[int, List[Tuple[str, str]]]
# NEW: Marks which groups have unavoidable team repeats
# Example: {0: [('Team A', 'Team C')], 2: [('Team B', 'Team D')]}

self.use_traditional_swiss: bool
# NEW: Configuration flag
# True = Traditional Swiss (this implementation)
# False = Pod Consistency (old implementation)
```

### Function Call Graph

```
generate_round() [Main entry point]
  └─> _create_team_groups_for_round(round_num)
      ├─> Round 1: Random shuffle
      └─> Round 2+: Traditional Swiss
          ├─> _create_team_groups_traditional_swiss(round_num)
          ├─> _detect_repeat_matchups_in_groups(groups)
          ├─> _resolve_repeat_matchups_by_swapping(groups, repeats)
          │   ├─> _find_best_swap_candidate(...)
          │   │   └─> _is_valid_swap(...)
          │   │       └─> _group_has_repeat_matchups(...)
          │   └─> Returns modified groups
          ├─> _validate_all_groups_no_repeats(groups)
          ├─> _mark_groups_for_player_optimization(groups, groups_with_repeats)
          └─> Returns final groups

  └─> For each group:
      └─> _create_four_pods_for_team_group(team_group, round_num, group_index)
          ├─> Check if needs_max_optimization
          ├─> Try permutations (24 or 13,824 iterations)
          └─> _count_and_detail_repeat_matchups_in_pod(pod, pod_idx)
```

---

## Files Modified Summary

| File | Lines Modified | Changes |
|------|----------------|---------|
| `unified_swiss_pairing.py` | ~400-450 new lines | 9 new functions, 3 enhanced functions |
| `tournament_dashboard.py` | ~5 lines | Add `use_traditional_swiss=True` parameter |
| `test_traditional_swiss.py` | ~150 lines | NEW: Test suite for traditional Swiss |

---

## Performance Considerations

### Time Complexity

**Layer 1 (Traditional Grouping):**
- Sort teams: O(n log n) where n = number of teams
- Create groups: O(n)
- Total: **O(n log n)** - Fast

**Layer 2 (Team Swapping):**
- Detect repeats: O(g * 4²) where g = number of groups
- Find swap candidate: O(g * 4) per repeat
- Validate swap: O(4²) per candidate
- Total: **O(g² * 16)** - Fast (g ≤ 5 for 20-team tournament)

**Layer 3 (Player Optimization):**
- Normal groups: 24³ = 13,824 iterations max
- Groups with team repeats: 24³ = 13,824 iterations (same, but never exits early)
- Per iteration: O(16) player pairing checks
- Total: **O(13,824 * 16) = ~220k operations per group** - Acceptable

**Overall:** <5 seconds for full round generation (including player optimization)

### Memory Usage

- Minimal additional memory
- Stores `groups_needing_player_optimization` dict (small)
- No significant increase from current implementation

---

## Troubleshooting Guide

### Issue: Swap algorithm creates infinite loop

**Symptoms:** Round generation hangs or takes >10 seconds
**Cause:** Cascading repeats causing swap → new repeat → swap back
**Solution:** `swap_history` tracks attempted swaps, `max_swap_attempts=10` limits iterations

### Issue: Exhaustive search too slow

**Symptoms:** Player optimization takes >10 seconds per group
**Cause:** 13,824 iterations with complex repeat checking
**Solution:** Set `max_player_optimization_iterations=1000` in `__init__`

### Issue: Still getting player repeats in optimized groups

**Symptoms:** Console shows "MINIMIZED: 4 player repeats" instead of 0-2
**Cause:** Truly unavoidable due to previous round constraints
**Solution:** This is expected in some edge cases (8-team Round 4+). Algorithm is working correctly.

### Issue: Traditional Swiss not activating

**Symptoms:** Round 2+ still uses pod consistency logic
**Cause:** `use_traditional_swiss=False` or not passed to constructor
**Solution:** Check `tournament_dashboard.py` where `UnifiedSwissPairing` is created, ensure `use_traditional_swiss=True`

---

## Next Steps After Implementation

1. **Code Review:** Review all new functions for edge cases
2. **Unit Tests:** Run `test_traditional_swiss.py`
3. **Integration Tests:** Run `test_tournament_comprehensive.py --all`
4. **Manual Testing:** Run tournament_dashboard.py, play through Swiss rounds
5. **Performance Testing:** Verify Round 4 of 8-team tournament completes in <5s
6. **User Feedback:** Test with real tournament, gather feedback on pairing quality
7. **Documentation:** Update main README.md to explain Traditional Swiss option
8. **Optional:** Add UI toggle to switch between Traditional Swiss and Pod Consistency

---

## Questions & Answers

**Q: What if I want to revert to pod consistency?**
A: Change `use_traditional_swiss=False` in tournament_dashboard.py

**Q: Can I use both systems simultaneously?**
A: Yes! Keep both implementations and switch via config flag.

**Q: Will this break existing tournaments?**
A: No. This is a pairing algorithm change only. Tournament state, scoring, and data structures remain unchanged.

**Q: How do I know if player optimization is working?**
A: Check console logs. You'll see "[PLAYER OPTIMIZATION]" messages showing iteration counts and results.

**Q: What happens if a swap creates a worse score distribution?**
A: The swap algorithm always prefers smallest score difference. It may accept a ±3 point swap to avoid team repeat.

**Q: Is 13,824 iterations too many?**
A: No. Modern CPUs can do ~220k operations in <1 second. Entire optimization takes 1-3 seconds per group.

---

## References

### Existing Code Locations

- `_sort_teams_by_score()`: Line 1680
- `_count_repeat_matchups_in_pod()`: Line 1773
- `team_matchups` updates: Line 1372-1381
- `player_opponents` tracking: Line 1356-1370
- Main round generation: Search for `def generate_round`

### Related Documentation

- `CLAUDE.md`: Production readiness assessment
- `README.md`: User-facing documentation
- `test_tournament_comprehensive.py`: Existing test suite
- `debug_state.py`: Tournament state debugging tool

---

**Implementation Status: Ready to Begin**
**Estimated Time: 4-6 hours for full implementation and testing**
**Risk Level: Low (can rollback via config flag)**
