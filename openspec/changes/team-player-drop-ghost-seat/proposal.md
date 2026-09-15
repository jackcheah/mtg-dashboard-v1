## Why

In team mode (4 players per team), individual players sometimes need to leave a tournament mid-event (emergency, illness, disqualification). Currently, the system has no mechanism for this — the only drop feature is for individual mode, which removes a solo player entirely. A team that loses a member has no way to continue; the operator must either force the team to withdraw or work around it manually. This feature lets teams continue competing with fewer than 4 active members by replacing dropped players with "ghost seats" that preserve pod-of-4 pairing integrity while signaling 3-player (or 2-player) pods to opponents.

## What Changes

- **New: Drop individual player from a team** — Operator can drop any player from any team between rounds (after all tables submit, before finalization). The player becomes a "ghost" placeholder that continues to occupy a pairing slot.
- **New: Ghost seat pairing behavior** — Ghost players are still assigned to pods by the pairing engine (team stays at 4 slots). Opponents at a ghost's table play a reduced-size pod (3-player, or 2-player if multiple ghosts). The pairing optimizer actively avoids placing multiple ghosts in the same pod (higher priority than avoiding repeat opponents).
- **New: Ghost seat scoring** — Ghost auto-loses every round (0 pts Western; contributes 7% to Japanese pool and loses it). Ghost's score is whatever they had at drop time, modified only by Japanese auto-losses. No score submission for ghost players.
- **New: Undrop (restore) a dropped team player** — Reversible operation. Player rejoins with their current score (which may have decayed in Japanese mode).
- **New: Team withdrawal trigger** — Minimum 2 active players per team. If dropping would leave fewer than 2 active, the system requires a full team withdrawal instead.
- **Modified: Score validation** — Tables with ghost players validate real players as an N-player pod (3-player rules for 1 ghost, 2-player rules for 2 ghosts) rather than 4-player rules.
- **Modified: UI across dashboard and projector** — Ghost rows in table views (grayed out, auto-loss label), team standings with drop indicators, drop/undrop modal accessible in team mode.
- **Modified: TopDeck export** — Ghost players omitted from CSV (table exported as 3-player pod). Validation warning for ghost tables.
- **Modified: Persistence** — Dropped team players tracked and serialized for backup/restore.

## Capabilities

### New Capabilities
- `team-player-drop`: Core drop/undrop logic for team mode — ghost flagging, minimum-active-player enforcement, team withdrawal trigger, timing constraints (between rounds only).
- `ghost-seat-pairing`: Pairing engine awareness of ghost players — optimizer penalty for multi-ghost pods (higher priority than repeat-opponent avoidance), ghost-aware constraint tracking.
- `ghost-seat-scoring`: Scoring rules for ghost players — auto-loss mechanics for Western and Japanese modes, score validation for mixed pods (real + ghost players), team score calculation with ghosts.

### Modified Capabilities
(No existing specs to modify — this is a greenfield OpenSpec project.)

## Impact

- **`tournament_dashboard.py`**: New `drop_team_player()` and `undrop_team_player()` methods. Modified `submit_table_results` for ghost detection and auto-loss injection. Modified score validation for mixed-size pods. Modified Japanese scoring pool calculation. New Flask endpoints (`/drop_team_player`, `/undrop_team_player`). Modified `_build_state_dict()` and restore for ghost persistence. Modified `_handle_round_transition` and `generate_swiss_round` to pass ghost info to pairing engine.
- **`unified_swiss_pairing.py`**: Modified Layer 3 permutation optimizer to penalize multi-ghost pods. Ghost tracking data structure. No changes to Layer 1 (team grouping) or Layer 2 (bracket swaps).
- **`static/js/dashboard.js`**: Drop Player button visibility extended to team mode. New team-player-drop modal (team selector → player selector). Ghost row rendering in table views. Score submission UI skips ghost rows.
- **`templates/dashboard_ultra_modern.html`**: Drop/undrop modal markup. Ghost row CSS classes.
- **`templates/projector_view.html`**: Ghost player visual treatment in projector display.
- **`topdeck_exporter.py`**: Ghost player omission from CSV. Validation warning for ghost tables.
- **`static/css/dashboard.css`**: Ghost row styling (grayed out, strikethrough or badge).
- **Tests**: New test coverage for ghost scoring, multi-drop, Japanese decay, pairing with ghosts, undrop, full tournament flow with drops, edge cases (2-ghost table, team at minimum active players).
