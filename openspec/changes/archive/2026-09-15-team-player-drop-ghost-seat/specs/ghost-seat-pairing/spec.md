## Purpose

Extends the Swiss pairing engine to be aware of ghost (dropped) players, actively avoiding placing multiple ghosts in the same pod to minimize the number of reduced-size pods per round.

## ADDED Requirements

### Requirement: Ghost players are paired normally by the engine

Ghost players SHALL occupy a pairing slot on their team. The pairing engine SHALL treat ghost players as valid team members for the purpose of team grouping (Layer 1), bracket swaps (Layer 2), and pod assignment. The existing constraint that each team has exactly 4 players SHALL be satisfied by counting ghost players.

#### Scenario: Pairing engine generates round with ghost player
- **WHEN** a round is generated and one team has a ghost player
- **THEN** the ghost is assigned to a pod like any other player, the pod contains 4 player slots (3 real + 1 ghost), and the no-teammates-in-same-pod constraint is enforced normally

#### Scenario: Pairing engine validates team size with ghosts
- **WHEN** the pairing engine initializes with a team that has 1 ghost + 3 active players
- **THEN** the team passes the 4-player-per-team validation because the ghost counts toward the team size

### Requirement: Multi-ghost pod avoidance

The pairing optimizer (Layer 3 permutation search) SHALL penalize permutations that place 2 or more ghost players in the same pod. This penalty SHALL have higher priority than the repeat-opponent avoidance penalty. The system SHALL prefer repeat opponents over multi-ghost pods.

#### Scenario: Two teams in same bracket each have one ghost
- **WHEN** a bracket of 4 teams contains 2 teams that each have one ghost player, and permutations exist that separate the ghosts into different pods
- **THEN** the optimizer selects a permutation where the 2 ghosts are in different pods, even if that permutation has more repeat-opponent violations than an alternative that puts both ghosts together

#### Scenario: Multi-ghost unavoidable due to extreme drops
- **WHEN** a bracket has more ghost players than can be separated across 4 pods (e.g., 5+ ghosts from multiple teams)
- **THEN** the optimizer minimizes the number of multi-ghost pods and selects the best available permutation, accepting that some pods will have 2 ghosts

#### Scenario: Single ghost in bracket
- **WHEN** a bracket of 4 teams has exactly 1 ghost player total
- **THEN** exactly 1 pod is a reduced-size pod and the other 3 pods are full 4-player pods, with repeat-opponent optimization applied normally

### Requirement: Ghost opponent tracking

The pairing engine SHALL track opponents of ghost players in its constraint history (`used_pairings`, `player_opponents`). This ensures that the players who were seated with a ghost in round N are tracked as having "faced" that ghost's opponents, maintaining accurate repeat-avoidance data for future rounds.

#### Scenario: Opponent tracking includes ghost
- **WHEN** a round is completed with a ghost at Table 4 alongside players B, C, D
- **THEN** the opponent tracking records B-C, B-D, C-D as real pairings AND B-ghost, C-ghost, D-ghost as pairings, so future rounds can optimize to avoid re-pairing B, C, or D with the same ghost seat

### Requirement: Ghost info passed to pairing engine

The system SHALL pass ghost player identification to the pairing engine when constructing or rebuilding it. The engine SHALL accept a set of dropped player IDs and use this information for the multi-ghost avoidance penalty during optimization.

#### Scenario: Pairing engine constructed with ghost info
- **WHEN** the pairing engine is created or rebuilt for a new round after a player has been dropped
- **THEN** the engine receives the set of ghost player IDs and uses this to calculate ghost-overlap penalties during permutation optimization
