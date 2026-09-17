## Purpose

Defines how scoring works for ghost (dropped) players and for the real players at their tables, ensuring team scores, Japanese pool mechanics, and score validation all handle mixed-size pods correctly.

## ADDED Requirements

### Requirement: Ghost auto-loss in Western scoring

In Western scoring mode, ghost players SHALL automatically receive 0 points (loss) for every round after they are dropped. No score submission is required or allowed for ghost players. The ghost's `player_scores` entry remains at whatever value it held at drop time (since Western loss = +0, the score is effectively frozen).

#### Scenario: Ghost at table in Western mode
- **WHEN** a round is played with a ghost player at a table in Western scoring mode
- **THEN** the ghost receives 0 points for that round, the ghost's cumulative score does not change, and the 3 real players' scores are updated based on their submitted results

#### Scenario: Ghost score after multiple rounds (Western)
- **WHEN** a player was dropped with 10 points after round 2, and rounds 3 and 4 are played
- **THEN** the ghost's score remains 10 after both rounds (0 + 0 added)

### Requirement: Ghost auto-loss in Japanese scoring

In Japanese scoring mode, ghost players SHALL contribute 7% of their current score to the table's pool each round and then lose that contribution (auto-loss). The pool is formed from all 4 players' contributions (3 real + 1 ghost). The winner among the 3 real players takes the entire pool. The 2 real losers each lose their 7% contribution. The ghost also loses their 7% contribution.

#### Scenario: Ghost at table in Japanese mode
- **WHEN** a round is played with a ghost (current score 1000) at a table with 3 real players (scores 1000, 900, 800) in Japanese mode, and one real player wins
- **THEN** the pool equals (1000×0.07) + (1000×0.07) + (900×0.07) + (800×0.07) = 259, the winner gains 259 minus their own contribution, the 2 real losers each lose their 7% contribution, and the ghost loses 70 (7% of 1000), dropping to 930

#### Scenario: Ghost score decays over multiple Japanese rounds
- **WHEN** a ghost with score 1000 plays 3 rounds in Japanese mode
- **THEN** the ghost's score decreases each round: 1000 → 930 → 864.9 → 804.4 (each time losing 7% of current score), progressively penalizing the dropped player's team

#### Scenario: All players at ghost table draw (Japanese)
- **WHEN** a ghost table has 3 real players who all draw and 1 ghost
- **THEN** the ghost still contributes 7% and loses it (auto-loss regardless of draw outcome among real players), the 3 drawing real players each lose their 7% contribution (standard draw behavior), and the pool is not awarded to anyone

### Requirement: Score validation for mixed pods

Score validation SHALL recognize tables containing ghost players and validate the real players' results using the appropriate reduced-pod rules. A table with 1 ghost validates as a 3-player pod. A table with 2 ghosts validates as a 2-player pod.

#### Scenario: Submit scores for table with 1 ghost (win scenario)
- **WHEN** operator submits results for a table with 1 ghost and 3 real players, with 1 winner and 2 losers among the real players
- **THEN** validation passes (1 win + 2 losses is valid for a 3-player pod)

#### Scenario: Submit scores for table with 1 ghost (draw scenario)
- **WHEN** operator submits results for a table with 1 ghost and 3 real players, with 3 draws among the real players
- **THEN** validation passes (3 draws is valid for a 3-player pod)

#### Scenario: Submit scores for table with 1 ghost using 4-player rules
- **WHEN** operator submits results with 1 winner and 3 losers for a table that has 1 ghost (attempting 4-player validation)
- **THEN** validation fails because only 3 real results should be submitted (the ghost's score is injected automatically, not submitted)

#### Scenario: Submit scores for table with 2 ghosts
- **WHEN** operator submits results for a table with 2 ghosts and 2 real players, with 1 winner and 1 loser
- **THEN** validation passes (1 win + 1 loss is valid for a 2-player pod)

### Requirement: Ghost score excluded from manual submission

The system SHALL NOT accept score submissions for ghost player IDs. When processing table results, the system SHALL automatically inject the ghost's result (0 points Western, or the calculated Japanese loss) without requiring operator input. If a submission payload includes a ghost player's score, the system SHALL either ignore it or reject the submission.

#### Scenario: Backend receives submission without ghost score
- **WHEN** operator submits results for a ghost table with only the 3 real players' scores
- **THEN** the system accepts the submission, auto-injects the ghost's 0-point result, and updates all player scores including the ghost's Japanese decay if applicable

#### Scenario: Backend receives submission with ghost score included
- **WHEN** operator submits results for a ghost table with 4 results including a ghost player's score
- **THEN** the system SHALL reject the submission indicating that ghost player scores cannot be manually submitted

### Requirement: Team score calculation with ghosts

Team scores SHALL continue to be calculated as the sum of all team members' `player_scores`, including ghost players. The ghost's score (frozen in Western, decaying in Japanese) is part of the team total. This means teams with ghosts are naturally disadvantaged: fewer earners in Western, active score drain in Japanese.

#### Scenario: Team score includes ghost score (Western)
- **WHEN** Team Alpha has 3 active players (scores 15, 10, 5) and 1 ghost (score frozen at 5)
- **THEN** the team's total score is 35 (15 + 10 + 5 + 5)

#### Scenario: Team score includes decaying ghost score (Japanese)
- **WHEN** Team Alpha has 3 active players and 1 ghost whose score has decayed from 1000 to 800 over 3 rounds
- **THEN** the team's total includes the ghost's 800, and the team total is lower than it would be if all 4 players were active

### Requirement: Tiebreaker handling with ghosts

Ghost players SHALL be included in all tiebreaker calculations (best player score, average player score, early wins). The ghost's frozen/decayed score counts toward these metrics. The ghost does not generate wins for tiebreaker purposes (they auto-lose every round).

#### Scenario: Best player tiebreaker with ghost
- **WHEN** two teams are tied on total score and one team has a ghost player
- **THEN** the "best individual player" tiebreaker considers all 4 players including the ghost, and the ghost's score counts (likely dragging down the team's best-player metric if the ghost was the team's top scorer before dropping)

#### Scenario: Early wins tiebreaker with ghost
- **WHEN** tiebreaker uses early-round win counts and a team has a ghost
- **THEN** the ghost's wins from rounds before they were dropped still count, but no wins are attributed to the ghost for rounds after the drop
