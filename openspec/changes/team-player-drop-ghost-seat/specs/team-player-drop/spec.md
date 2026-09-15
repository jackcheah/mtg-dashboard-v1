## Purpose

Allows individual players to be dropped from teams during a team-mode tournament, converting them to ghost placeholders that preserve pod-of-4 pairing integrity while the team continues with fewer active members.

## ADDED Requirements

### Requirement: Drop a player from a team

The system SHALL allow the tournament operator to drop any active player from any team during a team-mode event. The dropped player SHALL be converted to a "ghost" placeholder that remains in the team's roster for pairing purposes. The player's name SHALL be displayed as `<Name> (Dropped)` in all views after the drop.

#### Scenario: Operator drops a player between rounds
- **WHEN** operator selects a player to drop from a team, all tables for the current round have submitted scores, and the current round has not been finalized
- **THEN** the player is flagged as a ghost, the player's display name changes to `<Name> (Dropped)`, the team's active player count decreases by one, and the system confirms the drop with a success message

#### Scenario: Drop attempted during wrong timing
- **WHEN** operator attempts to drop a player but the current round's tables have not all submitted, or the round is already finalized, or the tournament is not in Swiss rounds
- **THEN** the system SHALL reject the drop with an error message explaining the timing constraint

#### Scenario: Drop attempted in individual mode
- **WHEN** operator attempts to use team player drop in individual mode
- **THEN** the system SHALL reject with an error indicating this feature is for team mode only (individual mode has its own separate drop mechanism)

#### Scenario: Drop attempted on already-dropped player
- **WHEN** operator attempts to drop a player who is already a ghost
- **THEN** the system SHALL reject with an error indicating the player is already dropped

### Requirement: Minimum active player enforcement

The system SHALL enforce a minimum of 2 active (non-ghost) players per team. If dropping a player would reduce the team to fewer than 2 active players, the system SHALL reject the individual drop and instruct the operator to withdraw the entire team instead.

#### Scenario: Drop would leave 2 active players
- **WHEN** a team has 3 active players and the operator drops one
- **THEN** the drop succeeds, the team has 2 active players and 2 ghosts, and the system warns that no further individual drops are allowed for this team

#### Scenario: Drop would leave 1 active player
- **WHEN** a team has 2 active players and the operator attempts to drop one
- **THEN** the system SHALL reject the drop with a message: the team must be withdrawn entirely rather than dropping to 1 active player

### Requirement: Undrop (restore) a dropped team player

The system SHALL allow the tournament operator to restore a previously dropped team player. The restored player SHALL rejoin as an active team member with their current score (which may have decayed due to Japanese auto-losses while ghosted). Undrop timing follows the same constraints as drop: between rounds, all tables submitted, round not finalized.

#### Scenario: Operator restores a dropped player
- **WHEN** operator selects a ghost player to restore, timing constraints are met
- **THEN** the player's ghost flag is removed, the display name reverts to the original name, the player resumes active play from the next round, and the player's score is whatever it currently is (including any Japanese decay)

#### Scenario: Undrop when no players are dropped
- **WHEN** operator opens the drop/undrop interface but no team has any ghost players
- **THEN** the undrop section shows an empty state message indicating no players are currently dropped

### Requirement: Ghost player persistence

The system SHALL persist all ghost player state (which players are dropped, when they were dropped, their score at drop time) in the tournament backup. Restoring from backup SHALL fully rehydrate ghost state including display names and scoring behavior.

#### Scenario: Backup and restore with ghost players
- **WHEN** operator saves a backup after dropping a player, then restores from that backup
- **THEN** all ghost players are restored with correct flags, display names show `(Dropped)`, scoring behavior continues as ghost, and the pairing engine is correctly rehydrated with ghost awareness

### Requirement: Ghost players carry through all tournament phases

Ghost players SHALL remain as ghost placeholders through all tournament phases: Swiss rounds, Top 8 Cut (if applicable), and Finals. The ghost seat behavior (auto-loss, reduced pod) applies identically in playoff rounds.

#### Scenario: Team with ghost advances to finals
- **WHEN** a team with a ghost player qualifies for playoffs
- **THEN** the ghost player is still assigned to a pod in the finals round, that pod plays as a reduced-size pod, and the ghost auto-loses as in Swiss rounds

### Requirement: Drop Player UI in team mode

The system SHALL display a "Drop Player" button in the active round controls bar when in team mode, visible under the same conditions as the existing individual-mode drop button (all tables submitted, round not finalized, Swiss rounds in progress). The button SHALL open a modal with a team selector followed by a player selector showing only active players from the selected team.

#### Scenario: Operator opens drop modal in team mode
- **WHEN** operator clicks "Drop Player" during a team event with valid timing
- **THEN** a modal appears with a team dropdown listing all teams with their active player counts, and selecting a team reveals its active players with their current scores

#### Scenario: Drop modal shows undrop section
- **WHEN** one or more players have been dropped across any teams
- **THEN** the modal also shows an "Undrop (Restore)" section listing all ghost players with their team, drop round, and a restore button

### Requirement: Ghost visual treatment in table views

Ghost player rows in table/pod views SHALL be visually distinct from active players: grayed out or styled with a muted appearance, showing "DROPPED" label and "auto: 0 pts" instead of a score submission dropdown. The table header SHALL display a badge indicating the reduced pod size (e.g., "3-player pod").

#### Scenario: Table with one ghost player displayed
- **WHEN** a round is generated and a table contains one ghost player
- **THEN** the ghost row is visually muted, shows no score input, displays "auto: 0 pts", and the table header shows a "3-player pod" indicator

#### Scenario: Projector view with ghost player
- **WHEN** the projector view displays a round with ghost players
- **THEN** ghost player names show with a `(Dropped)` suffix and a visual cue distinguishing them from active players, so opponents and audience know which tables are reduced pods

### Requirement: TopDeck export with ghost players

Ghost players SHALL be omitted from the TopDeck CSV export. Tables with ghost players SHALL be exported as 3-player (or 2-player) rows with empty trailing player columns. The TopDeck validation endpoint SHALL include a warning for each table containing ghost players.

#### Scenario: Export round with ghost tables
- **WHEN** operator exports a round that contains tables with ghost players
- **THEN** the CSV omits ghost player names, affected tables have fewer player columns filled, and the validation response includes warnings listing which tables have ghosts

#### Scenario: Validation warning for ghost tables
- **WHEN** operator validates a round for TopDeck export and ghost players exist
- **THEN** the validation response includes a warning per ghost table (e.g., "Table 4 has 1 dropped player — exported as 3-player pod")
