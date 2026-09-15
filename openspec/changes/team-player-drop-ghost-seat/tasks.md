## 1. Data Model & Core Drop/Undrop Logic

- [ ] 1.1 Add `dropped_team_players` dict and `is_dropped` flag support to `TournamentManager.__init__()`. Add the field to `_build_state_dict()` serialization and restore logic (with `.get()` default for backward compatibility). Verify: unit test creates a TournamentManager, serializes, and restores with empty `dropped_team_players`; restoring an old backup without the field does not error.

- [ ] 1.2 Implement `drop_team_player(player_id, round_num)` method on `TournamentManager`. Must: validate team mode, validate timing (all tables submitted, round not finalized, Swiss in progress), check player is active and not already dropped, enforce minimum 2 active players, set `is_dropped: True` on the player dict, rename `Player Name` to `<Name> (Dropped)`, record metadata in `dropped_team_players`. Verify: unit tests cover successful drop, wrong timing rejection, individual mode rejection, already-dropped rejection, minimum-active-player rejection.

- [ ] 1.3 Implement `undrop_team_player(player_id)` method on `TournamentManager`. Must: validate team mode, validate timing (same as drop), check player is actually dropped, remove `is_dropped` flag, restore original name from `dropped_team_players`, remove entry from `dropped_team_players`. Verify: unit tests cover successful undrop, undrop of non-dropped player rejection, name and flag restoration.

- [ ] 1.4 Add Flask endpoints `POST /drop_team_player` and `POST /undrop_team_player` with PIN protection. Wire to the methods from 1.2 and 1.3. Return appropriate success/error JSON. Verify: unit tests call endpoints with valid and invalid payloads, confirm correct HTTP status codes and response bodies.

- [ ] 1.5 Update `_build_state_dict()` and restore to serialize/deserialize `dropped_team_players`, and ensure player dicts with `is_dropped` flag round-trip correctly. Verify: unit test drops a player, saves backup, restores, and confirms ghost state (flag, name, metadata) is intact.

## 2. Score Submission & Validation Changes

- [ ] 2.1 Modify `submit_table_results` to detect ghost players at a table (check `is_dropped` flag on players in `self.tables[round_num][table_name]`). Partition results into real and ghost. Reject submissions that include ghost player IDs. Validate real player results using N-player pod rules (N = number of non-ghost players). Verify: unit test submits scores for a 3-real + 1-ghost table with valid 3-player results — succeeds. Test submitting 4 results (including ghost) — rejected.

- [ ] 2.2 Implement ghost auto-score injection in `submit_table_results` for Western mode: after validating real results, auto-inject ghost result as 0 points and update `player_scores[ghost_id]` with +0. Call `calculate_team_scores()` as normal. Verify: unit test confirms ghost score unchanged after submission, team score includes ghost's frozen value.

- [ ] 2.3 Implement ghost auto-score injection in `submit_table_results` for Japanese mode: ghost contributes 7% of their current score to the pool, loses that contribution. Pool = sum of all 4 contributions (3 real + ghost). Winner takes full pool. Ghost's `player_scores` decremented by 7% of their current score. Verify: unit test with known scores confirms exact Japanese math — ghost score decays by 7%, winner receives correct pool amount including ghost's contribution.

- [ ] 2.4 Verify score validation edge cases: 2-ghost table (2 real players, 1 win + 1 loss), all-draw at ghost table (3 draws + ghost auto-loss), ghost table in Japanese mode with draw (no winner, ghost still loses 7%). Verify: unit tests for each scenario pass validation and produce correct score updates.

## 3. Pairing Engine Changes

- [ ] 3.1 Add `ghost_player_ids: Set[int]` parameter to `UnifiedSwissPairing.__init__()` (default empty set). Store as instance attribute. No changes to existing validation or initialization logic. Verify: existing pairing tests still pass with default empty set.

- [ ] 3.2 Modify Layer 3 permutation scoring to add multi-ghost penalty. In the optimization function that evaluates candidate pod assignments, count ghost players per pod using `ghost_player_ids`. If any pod has 2+ ghosts, add a heavy penalty (e.g., 1000 per extra ghost beyond 1). This must outweigh repeat-opponent penalties (typically 1-10). Verify: unit test with 2 teams each having 1 ghost in the same bracket — optimizer separates ghosts into different pods.

- [ ] 3.3 Update `generate_swiss_round()` in `tournament_dashboard.py` to pass `ghost_player_ids` when constructing or rebuilding `UnifiedSwissPairing`. Collect ghost IDs from `dropped_team_players` keys. Verify: integration test drops a player, generates next round, confirms ghost is at a table and no double-ghost tables exist (when avoidable).

- [ ] 3.4 Verify pairing engine rehydration with ghosts: after backup/restore, the rebuilt engine receives ghost IDs and opponent tracking from replayed rounds includes ghost pairings. Verify: unit test drops a player, plays 2 rounds, saves, restores, generates another round — pairings are valid and ghost avoidance works.

## 4. UI: Dashboard Drop/Undrop Interface

- [ ] 4.1 Extend "Drop Player" button visibility in `dashboard.js` to show in team mode (currently gated to `currentEventMode === 'individual'`). Same timing conditions: all tables submitted, round not finalized, Swiss in progress. Verify: run the app, set up a team tournament, submit all table scores — "Drop Player" button appears.

- [ ] 4.2 Implement team-mode drop modal in `dashboard.js`: team selector dropdown (showing team name + active player count), player list for selected team (showing name + score, only active players), and "Drop Selected Player" button. Wire to `POST /drop_team_player`. Show confirmation dialog with consequences (ghost mechanics, Japanese penalty warning, reversibility note). Verify: run the app, open modal, select team, select player, confirm — player is dropped and toast confirms.

- [ ] 4.3 Add undrop section to the drop modal: list all ghost players across all teams with team name, drop round, score at drop, current score, and "Restore Player" button. Wire to `POST /undrop_team_player`. Show empty state if no ghosts exist. Verify: run the app, drop a player, reopen modal — undrop section shows the ghost, click restore — player is restored.

- [ ] 4.4 Add HTML markup and CSS for the drop/undrop modal in `dashboard_ultra_modern.html` and `dashboard.css`. Include the team selector, player list, undrop section, and confirmation dialog. Verify: modal renders correctly with proper styling, responsive on typical tournament operator screens.

## 5. UI: Ghost Player Display

- [ ] 5.1 Modify table/pod rendering in `dashboard.js` to detect ghost players (check for `(Dropped)` in name or `is_dropped` flag in player data). Ghost rows: grayed out appearance, no score dropdown, display "auto: 0 pts" label. Table header: add "N-player pod" badge when ghosts present. Verify: run the app, drop a player, generate next round — ghost table displays correctly with muted row and badge.

- [ ] 5.2 Modify score submission UI for ghost tables: skip ghost player rows when building the score form, submit only real players' scores. Verify: run the app, open score submission for a ghost table — only 3 score dropdowns appear, submission succeeds.

- [ ] 5.3 Update standings display to show ghost indicators: team row has a warning icon if it has ghost players, individual player scores show ghost players with `(Dropped)` label and muted styling. Verify: run the app, drop a player — standings view shows team warning and ghost player styling.

- [ ] 5.4 Update projector view (`projector_view.html`) to display ghost players with visual distinction: `(Dropped)` suffix, muted styling, "3-player pod" label on affected tables. Verify: open projector view in browser — ghost tables display correctly for audience.

## 6. TopDeck Export Changes

- [ ] 6.1 Modify `validate_round_for_topdeck()` in `topdeck_exporter.py` to detect ghost players in table data (by `is_dropped` flag or name suffix). Add a warning per ghost table: "Table N has M dropped player(s) — exported as K-player pod." Verify: unit test validates a round with ghost tables — warnings present, no blocking errors.

- [ ] 6.2 Modify `build_pairings_csv()` in `topdeck_exporter.py` to omit ghost players from CSV rows. Ghost player's column left empty (e.g., 3-player pod has `player 4` empty). Verify: unit test builds CSV for a round with ghost tables — ghost names absent, correct number of player columns filled per row.

## 7. Comprehensive Testing

- [ ] 7.1 Full tournament flow test with team player drops: set up 8-team tournament, play round 1, drop 1 player from 1 team, finalize round 1, generate round 2, verify ghost at table, submit scores for all tables (including ghost table), finalize round 2, continue through finals. Verify: test completes without errors, final standings include ghost team, scores are mathematically correct.

- [ ] 7.2 Multi-drop test: drop 2 players from the same team (leaving 2 active). Verify minimum enforcement — attempt to drop a 3rd is rejected. Generate a round, verify 2 ghost tables (or 1 table with 2 ghosts if same bracket). Score submission works for both.

- [ ] 7.3 Japanese scoring decay test: set up Japanese mode tournament, drop a player, play 3 rounds. Verify ghost score decays as `score × 0.93^N` (within floating-point tolerance). Verify team scores reflect the decay. Verify the winner at ghost tables receives the correct inflated pool.

- [ ] 7.4 Undrop flow test: drop a player, play 1 round (ghost score may decay in Japanese), undrop the player, verify name restored, score is current (not original), player plays normally in next round.

- [ ] 7.5 Ghost pairing avoidance test: set up tournament with 2 teams each having 1 ghost in the same bracket. Generate multiple rounds. Verify that ghosts are never in the same pod unless no other permutation exists. Verify that repeat opponents are accepted over double-ghost pods.

- [ ] 7.6 Backup/restore with ghosts test: drop players, play rounds, save backup, restore. Verify all ghost state (flags, names, scores, metadata) is intact and the next generated round respects ghost constraints.
