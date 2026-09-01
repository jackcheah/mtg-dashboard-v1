# TopDeck.gg Integration Specification

**Target system:** MTG Tournament Dashboard  
**Use case:** Individual and four-player-team cEDH tournaments  
**Document status:** Implementation draft  
**Last verified:** 1 September 2026

## 1. Purpose

This document defines how the MTG Tournament Dashboard should export tournament data to TopDeck.gg so that:

- externally generated cEDH pods can be published on TopDeck.gg;
- TopDeck can act as a public tournament record and operational backup;
- completed TopDeck data can be verified against the dashboard;
- the event can later be considered for inclusion in EDHTop16; and
- the dashboard does not depend on undocumented TopDeck endpoints.

Normative words such as **MUST**, **MUST NOT**, **SHOULD**, and **MAY** describe implementation requirements.

## 2. Confirmed TopDeck capabilities

As of the verification date, TopDeck officially supports the following relevant capabilities:

1. A round can import externally generated pairings from CSV using **Round actions → Import pairings**.
2. The documented pairing layout is `table, player 1, player 2, ...`.
3. The import dialog reconciles names against the TopDeck roster before applying changes.
4. The operator can separately:
   - add players found in the file but missing from the roster;
   - drop registered players absent from the file;
   - apply pairings; and
   - apply results when the uploaded file carries a result format recognized by TopDeck.
5. TopDeck publishes final results after the tournament is ended.
6. TopDeck has a documented API for retrieving completed tournaments, standings, decklists, rounds, tables, players, and winners.
7. TopDeck webhooks send TopDeck-originated events to external systems.

The public documentation does **not** currently define an organizer write API for creating tournaments, creating rounds, uploading pairings, or reporting results programmatically. Therefore, this integration MUST use TopDeck's organizer interface and CSV importer for writes. It MAY use the documented API for readback verification after completion.

## 3. Architectural decision

### 3.1 Source-of-truth ownership

| Data | Authoritative system | TopDeck role |
| --- | --- | --- |
| Team registration and membership | MTG Tournament Dashboard | Optional descriptive metadata |
| Team pairing algorithm | MTG Tournament Dashboard | Not used |
| Cross-team four-player pods | MTG Tournament Dashboard | Imported as individual EDH tables |
| Team scores and team standings | MTG Tournament Dashboard | Not representable in the recommended mirror event |
| Individual pod result | MTG Tournament Dashboard | Mirrored into TopDeck |
| Public player/deck record | TopDeck after verification | Publication and downstream data source |
| EDHTop16 inclusion | EDHTop16 | Requested using the completed TopDeck event URL |

### 3.2 Why TopDeck team mode MUST NOT be used for this team format

The dashboard's team format has these rules:

- each team contains four players;
- teammates are distributed across separate multiplayer pods;
- every pod contains four players from different teams; and
- individual results are aggregated into a team score.

TopDeck's documented team model is structurally different. In TopDeck, the **team is the competitor**, teams are paired directly against teams, and each seat either plays a corresponding seat or the teams share one game. This does not represent four different teams contributing one player each to the same cEDH pod.

For this reason, a dashboard team event MUST be mirrored to TopDeck as:

- Game: `Magic: The Gathering`
- Format: `EDH`
- Team Size: `1`
- Multiplayer pods containing the actual players who played together

The TopDeck event name and description SHOULD state that it is an individual-results mirror of a team tournament.

Suggested event name:

> Four Horsemen cEDH Team Event — Individual Results

Suggested description notice:

> This was a four-player-team cEDH event. Each team member played in a separate four-player pod, and advancement was determined by aggregate team score. The TopDeck standings record individual pod results; the official team standings were maintained by the tournament organizer.

## 4. Supported integration modes

### 4.1 Individual tournament mode

For an ordinary individual cEDH tournament, TopDeck can accurately represent:

- roster;
- pods;
- wins, draws, and losses;
- individual standings;
- decklists; and
- individual top cut.

The dashboard remains responsible for generating the pairings, but TopDeck standings SHOULD match the dashboard when scoring and tiebreakers are configured identically.

### 4.2 Four-player-team tournament mode

TopDeck can accurately represent:

- the actual player roster;
- the actual four-player pods;
- the winner or draw of every pod;
- each player's individual record; and
- player decklists.

TopDeck cannot accurately represent within the recommended mirror event:

- aggregate team score;
- official team rank;
- team-based advancement; or
- one winning team instead of one winning player.

The dashboard MUST remain authoritative for those values.

## 5. TopDeck event configuration

Before importing Round 1, the operator SHOULD configure TopDeck as follows.

| Setting | Required value or rule |
| --- | --- |
| Game | `Magic: The Gathering` |
| Format | `EDH` |
| Team Size | `1` |
| Player Identifier | `Name` unless another identifier has been validated with the importer |
| Best Of | `1` |
| Decklist Submission | Enabled for future events |
| Show Decklists | Enabled when publication is intended |
| Hide Standings | Disabled when public standings are intended |
| Scoring | Must match the dashboard scoring mode |
| Tiebreakers | Must match the published event rules where an exact TopDeck equivalent exists |

### 5.1 Western scoring

For the dashboard's Western mode, configure TopDeck Standard scoring as:

- Win: 5 points
- Draw: 1 point
- Loss: 0 points

The dashboard MUST derive each player's round result as follows:

| Pod outcome | Winner | Other players |
| --- | --- | --- |
| One player wins | Win | Loss |
| No player wins / agreed or timed draw | Draw | Draw |

### 5.2 Japanese point-wager scoring

TopDeck documents a Point Wager scoring mode, including starting points, wager amount, and draw wager. This appears suitable for the dashboard's Japanese mode, but the integration MUST remain disabled until a test event confirms all of the following:

- starting score is 1000;
- each player contributes exactly 7% of their current score;
- the same rounding rule is used by both systems;
- the winner receives the complete wager pool;
- draws are processed identically; and
- standings remain equal after several rounds with fractional calculations.

Until those tests pass, Japanese-mode events SHOULD publish only a separate result report or use manual TopDeck entry after comparing every table.

## 6. Pairings CSV contract

### 6.1 Confirmed upload schema

The first implementation MUST generate pairings-only CSV files using the documented TopDeck structure:

```csv
table,player 1,player 2,player 3,player 4
1,Alice Tan,Ben Lim,Cheryl Ng,Daniel Lee
2,Emma Wong,Faris Rahman,Grace Koh,Hassan Ali
```

Rules:

1. The first column MUST be named `table`.
2. Player columns MUST be named sequentially as `player 1`, `player 2`, `player 3`, and `player 4`.
3. Each row MUST represent one physical multiplayer pod.
4. Team-mode export MUST contain exactly four non-empty player values per table.
5. Table numbers MUST be positive integers and unique within the round.
6. Each active player MUST occur exactly once in the round export.
7. Player names MUST match the identifier used in the TopDeck roster.
8. CSV output MUST use UTF-8 encoding.
9. Fields containing commas, quotation marks, or line breaks MUST be escaped using standard CSV quoting.
10. Rows SHOULD be ordered by ascending table number.
11. The exporter MUST produce deterministic output for an unchanged round.

Recommended filename:

```text
topdeck_<event-slug>_round_<round-number>_pairings.csv
```

Example:

```text
topdeck_four-horsemen-2026_round_03_pairings.csv
```

### 6.2 Player identity requirements

TopDeck's importer reconciles names in the CSV against its roster. Therefore:

- exported names MUST NOT be silently shortened;
- leading and trailing whitespace MUST be removed;
- internal normalization MUST NOT alter the displayed exported name;
- duplicate exported names MUST be treated as a blocking validation error unless a different TopDeck-supported player identifier has been tested; and
- the operator MUST review both the **New players** and **Not in file** lists before applying an import.

The system SHOULD retain its own immutable `player_id`, but that ID MUST NOT be placed into the TopDeck CSV unless TopDeck documents or confirms support for it.

### 6.3 Results columns

TopDeck's current help page says the importer can apply results carried by an uploaded file. However, the public documentation does not define the exact result column names or values.

Consequently:

- Version 1 of the integration MUST export pairings only.
- Results MUST initially be entered or confirmed in TopDeck manually.
- The system MUST NOT invent fields such as `winner`, `result`, or `player 1 result` and assume TopDeck will accept them.
- A results-import implementation MAY be added only after obtaining a sample or template from the live TopDeck import dialog or written confirmation from TopDeck support.
- Once confirmed, the exact schema MUST be stored as a versioned adapter with automated fixture tests.

Suggested feature flag:

```text
TOPDECK_RESULTS_CSV_ENABLED=false
```

## 7. Export validation

The export operation MUST fail without creating an upload-ready file when any blocking condition is present.

### 7.1 Blocking errors

- Round does not exist.
- Round has not been finalized for publication.
- Duplicate table number.
- Duplicate player within the same round.
- Duplicate exported player name.
- Team-mode pod contains fewer or more than four players.
- Missing player name.
- Player is seated with a teammate in team mode.
- Player is assigned to more than one table.
- Result export was requested while the result schema feature flag is disabled.

### 7.2 Warnings requiring operator review

- A registered player is absent because they dropped.
- Only top-cut players appear in a later round.
- A decklist URL is missing.
- A commander cannot be determined.
- A player changed their public display name after an earlier export.
- TopDeck scoring or tiebreakers have not been recorded in the dashboard's integration settings.

### 7.3 Validation summary

Every export SHOULD show:

```text
Event: Four Horsemen 2026
Round: 3
Tables: 8
Players exported: 32
Players omitted: 0
Duplicate players: 0
Team conflicts: 0
Result data included: No
Status: Ready for TopDeck import
```

## 8. Operator workflow

### 8.1 Initial setup

1. Create the event in TopDeck.
2. Set the game, format, scoring, tiebreakers, features, and Player Identifier.
3. Keep Team Size at 1 for the four-player-team cEDH format.
4. Add the complete player roster.
5. For future events, have players submit and lock their decklists through TopDeck.
6. Record the TopDeck tournament ID (`tid`) and public URL in the dashboard.

### 8.2 Each Swiss round

1. Generate and verify the round in the dashboard.
2. Export the TopDeck pairings CSV.
3. In TopDeck, create or open the corresponding round.
4. Select **Round actions → Import pairings**.
5. Upload the CSV.
6. Review the reconciliation screen.
7. Add genuinely missing players if necessary.
8. Do **not** drop players merely because the CSV was wrong or incomplete.
9. Apply the pairings.
10. Publish/start the round if TopDeck is also being used live.
11. Enter or confirm the table results in TopDeck.
12. End the TopDeck round only when every table is complete.
13. Compare TopDeck standings with the dashboard before generating the next round.

### 8.3 Team-based playoffs

TopDeck's individual **Make cut** function MUST NOT be used to select a team-based cut by individual rank.

Instead:

1. Determine advancing teams and players in the dashboard.
2. Preserve a copy of the final Swiss standings.
3. Explicitly mark non-advancing players as dropped in TopDeck only after confirming the correct list.
4. Import the playoff pods generated by the dashboard.
5. Describe in the public event notes that advancement was based on aggregate team standings.
6. Record the official winning team and final team standings outside TopDeck's individual standings.

The system and operator MUST NOT fabricate a single individual champion when the event awarded victory to a team.

### 8.4 Retroactive publication

For an already completed event:

1. Create the TopDeck event using the original event information and date where the organizer interface permits it.
2. If TopDeck refuses a past date, contact TopDeck support rather than entering a false date.
3. Import rounds chronologically.
4. Enter all results and corrections before ending the tournament.
5. Add decklists or commander information wherever available.
6. End the tournament only after comparing every round and the final standings.

## 9. Readback verification through the TopDeck API

The dashboard MAY implement a read-only verification tool for completed TopDeck tournaments.

### 9.1 Request

TopDeck documents the following retrieval endpoint:

```http
POST https://topdeck.gg/api/v2/tournaments
Authorization: ${TOPDECK_API_KEY}
Content-Type: application/json
```

Recommended request body:

```json
{
  "TID": "TOPDECK_TOURNAMENT_ID",
  "columns": ["name", "decklist", "wins", "draws", "losses"],
  "rounds": true,
  "tables": ["table", "players", "winner", "status"],
  "players": ["name", "id", "decklist"]
}
```

The API documentation states that game and format values are case-sensitive. When query mode is used instead of `TID`, use:

```json
{
  "game": "Magic: The Gathering",
  "format": "EDH"
}
```

### 9.2 Verification checks

The verification tool SHOULD compare:

- event name and date;
- number of participants;
- number of rounds;
- table numbers per round;
- players seated at every table;
- table winner or draw;
- completed/pending table status;
- each player's wins, draws, and losses; and
- missing decklists.

The comparison SHOULD be order-insensitive for players within a pod unless seat order is operationally important.

Suggested output:

```text
TopDeck verification: FAILED

Round 2, Table 5
Dashboard winner: player_018 / Alice Tan
TopDeck winner: Draw

Round 4, Table 3
Dashboard players: A, B, C, D
TopDeck players: A, B, C, E
```

### 9.3 API security and attribution

- Store the API key in `TOPDECK_API_KEY` or a secrets manager.
- Never commit the key into source control.
- Make API calls from the server, not from public browser JavaScript.
- Log the HTTP status and TopDeck tournament ID, but never log the authorization header.
- Respect TopDeck's published rate limits.
- If the application displays TopDeck API data to users, include visible attribution and a link to TopDeck.gg as required by its API terms.

## 10. Optional webhooks

TopDeck webhooks are outbound notifications from TopDeck to the dashboard. They do not replace the CSV import path.

They MAY be used later for:

- `round.published` notifications;
- `round.ended` synchronization;
- `match.result_reported` updates;
- `player.registered` and `player.dropped` updates; and
- `tournament.finished` verification.

If webhooks are implemented:

- verify the TopDeck signature using the raw request body;
- store the signing secret securely;
- acknowledge successful delivery quickly;
- process asynchronously;
- deduplicate deliveries using the webhook event ID;
- route by TopDeck tournament ID; and
- define conflict rules before allowing TopDeck events to modify dashboard data.

For the first release, webhooks SHOULD be read-only audit inputs. The dashboard SHOULD NOT overwrite its authoritative team pairings or team standings from a TopDeck webhook.

## 11. EDHTop16 publication workflow

EDHTop16 is a separate aggregation service. Its official site asks organizers to contact the EDHTop16 team when they want a tournament added.

After TopDeck publication, prepare the following submission package:

- TopDeck public event URL and tournament ID;
- event name, date, location, and player count;
- explanation of the four-player-team structure;
- complete player roster;
- commander and decklist for every player where possible;
- Swiss and playoff pod results;
- final individual TopDeck standings;
- official team standings; and
- explicit statement that advancement and the champion were determined by team score.

Because EDHTop16 focuses on individual pilots, commanders, standings, and decklists, inclusion of this custom team format MUST NOT be assumed. The organizer SHOULD ask whether EDHTop16 wants:

- all individual games;
- Swiss games only; or
- the event excluded from normal conversion statistics.

## 12. Recommended dashboard features

### 12.1 Required for Version 1

- TopDeck tournament ID and public URL fields.
- **Export TopDeck Pairings CSV** action for every finalized round.
- Pre-export validation with blocking errors and warnings.
- Deterministic CSV generation.
- Export history containing timestamp, round, operator, and checksum.
- Event description template explaining the team format.
- Manual checklist for TopDeck result entry and round completion.

### 12.2 Recommended for Version 2

- Completed-tournament API readback.
- Round-by-round difference report.
- Decklist completeness report.
- EDHTop16 submission bundle export.
- Optional signed webhook receiver in audit-only mode.

### 12.3 Deferred until TopDeck confirmation

- Results-in-CSV export.
- Direct write API synchronization.
- Automatic roster creation through API.
- Automatic result posting through API.
- Japanese point-wager synchronization.
- Native representation of aggregate four-player-team standings.

## 13. Suggested internal interface

The dashboard MAY expose the following internal service contract:

```python
class TopDeckExporter:
    def validate_round(self, event_id: str, round_number: int) -> ValidationReport:
        ...

    def export_pairings_csv(self, event_id: str, round_number: int) -> bytes:
        ...

    def build_event_description(self, event_id: str) -> str:
        ...

    def verify_completed_event(self, event_id: str, topdeck_tid: str) -> VerificationReport:
        ...
```

Minimal CSV generation logic:

```python
import csv
import io


TOPDECK_FIELDS = ["table", "player 1", "player 2", "player 3", "player 4"]


def build_topdeck_pairings_csv(pods) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=TOPDECK_FIELDS)
    writer.writeheader()

    for pod in sorted(pods, key=lambda item: item.table_number):
        if len(pod.players) != 4:
            raise ValueError(f"Table {pod.table_number} does not contain four players")

        writer.writerow({
            "table": pod.table_number,
            "player 1": pod.players[0].name.strip(),
            "player 2": pod.players[1].name.strip(),
            "player 3": pod.players[2].name.strip(),
            "player 4": pod.players[3].name.strip(),
        })

    return output.getvalue().encode("utf-8")
```

The production implementation MUST perform all validation described in Section 7 before calling this serializer.

## 14. Acceptance tests

The integration is ready for production only when the following tests pass:

1. A 32-player team-event round produces eight four-player rows.
2. No player appears twice in an export.
3. No pod contains two members of the same team.
4. Names containing commas, apostrophes, hyphens, or non-ASCII characters survive an export/import cycle.
5. A duplicate display name blocks export.
6. A draw can be entered into TopDeck and produces four individual draws.
7. A winner produces one win and three losses.
8. A dropped player does not disappear without an operator warning.
9. Team-based playoff entrants can be imported without using an individual-rank cut.
10. Correcting a result in TopDeck causes standings to recompute as documented.
11. Completed-event API readback finds no table, player, or result differences.
12. Missing decklists are reported before the event is sent to EDHTop16.

## 15. Open questions to confirm with TopDeck

Before implementing beyond Version 1, obtain answers to these questions:

1. What exact CSV columns and values are accepted for multiplayer results?
2. Are player names matched case-sensitively?
3. How does the importer resolve two roster entries with identical names?
4. Can past-dated tournaments be created and finalized without support intervention?
5. Can a custom list of players be placed into a multiplayer top cut without using individual rank?
6. Does Point Wager use the same 7% calculation and rounding rules as the dashboard's Japanese mode?
7. Is native support planned for four-team Commander pods with aggregate team standings?
8. Does EDHTop16 currently ingest TopDeck team events or custom team-qualified EDH events without manual review?

## 16. References

- [TopDeck — Running an event](https://topdeck.gg/help/running-a-tournament)
- [TopDeck — CSV Pairings Import](https://topdeck.gg/blog/csv-pairings-import-20251009)
- [TopDeck — Event configuration](https://topdeck.gg/help/event-configuration)
- [TopDeck — Running team events](https://topdeck.gg/help/running-team-events)
- [TopDeck — Tournaments API v2](https://topdeck.gg/docs/tournaments-v2)
- [TopDeck — Webhooks](https://topdeck.gg/docs/webhooks)
- [EDHTop16 — About and tournament contact information](https://edhtop16.com/about)

## 17. Final implementation rule

The safe supported integration is:

> **Dashboard generates and validates the tournament → dashboard exports each round as TopDeck pairing CSV → operator imports and records results in TopDeck → dashboard verifies the completed TopDeck event through the read API → organizer submits the TopDeck event to EDHTop16 for review.**

Do not build against undocumented TopDeck browser endpoints. Treat result-CSV support, Japanese point-wager equivalence, and native four-player-team standings as unconfirmed until tested or approved by TopDeck.
