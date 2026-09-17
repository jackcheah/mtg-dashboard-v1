"""TopDeck.gg pairings CSV exporter.

Generates CSV files compatible with TopDeck's Round actions → Import pairings
feature. This module has no dependencies on Flask or TournamentManager — it
operates on plain Python data structures only.

V1 scope: pairings export only (no results CSV).
"""
import csv
import io
import re


TOPDECK_FIELDS = ["table", "player 1", "player 2", "player 3", "player 4"]


def extract_table_number(table_name):
    """Extract the trailing integer from a table name string.

    Returns 1 when no number is found (e.g. "Finals Table" — single table).
    """
    match = re.search(r'(\d+)\s*$', table_name)
    return int(match.group(1)) if match else 1


def validate_round_for_topdeck(tables, round_num, finalized_rounds, event_mode,
                                teams=None, dropped_players=None, bye_players=None):
    """Validate a round's data before TopDeck CSV export.

    Args:
        tables: dict of {table_name: [player_dicts]} for this round.
                Each player dict has 'Player ID', 'Player Name', 'Team Name'.
        round_num: integer round number.
        finalized_rounds: set of finalized round numbers.
        event_mode: 'team' or 'individual'.
        teams: dict of {team_name: [player_dicts]} — needed for teammate checks.
        dropped_players: dict of dropped player info, keyed by player ID.
        bye_players: list of player IDs on bye this round.

    Returns:
        dict with 'errors' (blocking), 'warnings' (informational), 'summary'.
    """
    errors = []
    warnings = []
    player_count = 0
    duplicate_name_count = 0
    team_conflict_count = 0

    if not tables:
        errors.append(f"Round {round_num} does not exist or has no tables.")
        return _build_result(errors, warnings, round_num, 0, 0, 0, 0, 0)

    if round_num not in finalized_rounds:
        errors.append(f"Round {round_num} has not been finalized. Finalize the round before exporting.")

    table_numbers = []
    seen_player_ids = {}
    seen_player_names = {}

    ghost_tables = []

    for table_name, players in tables.items():
        tnum = extract_table_number(table_name)
        table_numbers.append(tnum)

        ghost_count = sum(1 for p in players if p.get('is_dropped'))
        real_count = len(players) - ghost_count
        if ghost_count > 0:
            ghost_tables.append((table_name, ghost_count, real_count))

        if event_mode == 'team' and len(players) != 4:
            errors.append(f"{table_name}: team-mode pod contains {len(players)} players (expected 4).")

        team_names_in_pod = []
        for p in players:
            if p.get('is_dropped'):
                continue
            player_count += 1
            pid = p.get('Player ID')
            pname = (p.get('Player Name') or '').strip()
            team_name = p.get('Team Name', '')

            if not pname:
                errors.append(f"{table_name}: player ID {pid} has a missing or empty name.")
                continue

            if pid in seen_player_ids:
                errors.append(f"Player '{pname}' (ID {pid}) is assigned to both {seen_player_ids[pid]} and {table_name}.")
            else:
                seen_player_ids[pid] = table_name

            if pname in seen_player_names:
                duplicate_name_count += 1
                if duplicate_name_count == 1:
                    errors.append(f"Duplicate exported player name '{pname}' at {seen_player_names[pname]} and {table_name}.")
                elif duplicate_name_count <= 3:
                    errors.append(f"Duplicate exported player name '{pname}'.")
            else:
                seen_player_names[pname] = table_name

            if event_mode == 'team':
                team_names_in_pod.append(team_name)

        if event_mode == 'team' and len(team_names_in_pod) != len(set(team_names_in_pod)):
            seen = set()
            for tn in team_names_in_pod:
                if tn in seen:
                    team_conflict_count += 1
                    errors.append(f"{table_name}: multiple players from team '{tn}' are seated together.")
                seen.add(tn)

    dup_table_nums = [n for n in table_numbers if table_numbers.count(n) > 1]
    if dup_table_nums:
        errors.append(f"Duplicate table numbers detected: {sorted(set(dup_table_nums))}.")

    if dropped_players:
        dropped_names = [dp.get('name', f'ID {pid}') for pid, dp in dropped_players.items()]
        if dropped_names:
            warnings.append(f"{len(dropped_names)} dropped player(s) absent from this round: {', '.join(dropped_names[:5])}" +
                            (f" and {len(dropped_names) - 5} more" if len(dropped_names) > 5 else "") + ".")

    if bye_players:
        warnings.append(f"{len(bye_players)} player(s) on bye are not included in the export.")

    three_player_pods = [name for name, players in tables.items() if len(players) == 3]
    if three_player_pods:
        warnings.append(
            f"{len(three_player_pods)} three-player pod(s) detected ({', '.join(three_player_pods)}). "
            "TopDeck supports 3-player pods, but importing them via CSV with an empty player 4 field "
            "has not been verified against TopDeck's live importer. Test in an unpublished event first."
        )

    if ghost_tables:
        for tname, gcount, rcount in ghost_tables:
            warnings.append(
                f"{tname} has {gcount} dropped player(s) — exported as {rcount}-player pod."
            )

    players_omitted = sum(gc for _, gc, _ in ghost_tables)
    return _build_result(errors, warnings, round_num, len(tables),
                         player_count,
                         players_omitted, duplicate_name_count, team_conflict_count)


def _build_result(errors, warnings, round_num, table_count, player_count,
                  omitted_count, duplicate_count, team_conflicts):
    status = "Ready for TopDeck import" if not errors else f"Blocked: {len(errors)} error(s)"
    return {
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "round": round_num,
            "tables": table_count,
            "players_exported": player_count,
            "players_omitted": omitted_count,
            "duplicate_players": duplicate_count,
            "team_conflicts": team_conflicts,
            "result_data_included": False,
            "status": status,
        }
    }


def build_pairings_csv(tables, event_mode):
    """Generate a TopDeck-compatible pairings CSV from validated table data.

    Args:
        tables: dict of {table_name: [player_dicts]}, already validated.
        event_mode: 'team' or 'individual'.

    Returns:
        UTF-8 encoded CSV bytes.
    """
    sorted_tables = sorted(tables.items(), key=lambda item: extract_table_number(item[0]))

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=TOPDECK_FIELDS, extrasaction='ignore')
    writer.writeheader()

    for seq_num, (table_name, players) in enumerate(sorted_tables, 1):
        row = {"table": seq_num}
        real_players = [p for p in players if not p.get('is_dropped')]
        for i, player in enumerate(real_players):
            row[f"player {i + 1}"] = (player.get("Player Name") or "").strip()
        writer.writerow(row)

    return output.getvalue().encode("utf-8")


def generate_export_filename(round_num, event_name=None):
    """Generate a TopDeck export filename.

    Returns:
        String like 'topdeck_round_03_pairings.csv' or
        'topdeck_my-event_round_03_pairings.csv'.
    """
    padded = str(round_num).zfill(2)
    if event_name:
        slug = re.sub(r'[^a-z0-9]+', '-', event_name.lower()).strip('-')
        return f"topdeck_{slug}_round_{padded}_pairings.csv"
    return f"topdeck_round_{padded}_pairings.csv"
