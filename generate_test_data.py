#!/usr/bin/env python3
"""Generate test Excel files for tournament testing.

Creates:
1. participant_40teams.xlsx - 40 teams x 4 players = 160 players (team mode)
2. participant_80players.xlsx - 80 individual players (individual mode)
"""

from openpyxl import Workbook
import os

TEAM_NAMES = [
    "Alpha Strike", "Beta Force", "Gamma Ray", "Delta Squad",
    "Epsilon Elite", "Zeta Wing", "Eta Hawks", "Theta Storm",
    "Iota Blaze", "Kappa Shield", "Lambda Fury", "Mu Titans",
    "Nu Vanguard", "Xi Sentinels", "Omicron Rift", "Pi Dominion",
    "Rho Surge", "Sigma Blades", "Tau Breakers", "Upsilon Core",
    "Phi Nexus", "Chi Wardens", "Psi Phantom", "Omega Dawn",
    "Aether Forge", "Boros Legion", "Cabal Rising", "Dimir Shadow",
    "Esper Knights", "Fathom Deep", "Grixis Tide", "Hazoret Sun",
    "Izzet Spark", "Jund Wilds", "Kaladesh Works", "Lorwyn Grove",
    "Mardu Horde", "Naya Pride", "Orzhov Syndicate", "Phyrexia Reborn",
]

FIRST_NAMES = [
    "Alex", "Blake", "Casey", "Dana", "Eli", "Finn", "Gray", "Harper",
    "Indigo", "Jordan", "Kai", "Lane", "Morgan", "Noel", "Oakley", "Parker",
    "Quinn", "Reese", "Sage", "Taylor", "Uma", "Val", "Wren", "Xander",
    "Yuki", "Zara", "Aiden", "Briar", "Cedar", "Devon", "Ellis", "Fern",
    "Glen", "Haven", "Iris", "Jules", "Kit", "Lark", "Mars", "Nash",
    "Onyx", "Penn", "Rae", "Skye", "Teal", "Uri", "Vex", "West",
    "Yew", "Zen", "Ashe", "Birch", "Clay", "Drake", "Eve", "Fox",
    "Gale", "Heath", "Ivy", "Jett", "Knox", "Leaf", "Mace", "Nova",
    "Opal", "Pike", "Reed", "Sol", "Troy", "Umber", "Voss", "Wade",
    "Xia", "Yara", "Zeke", "Arrow", "Bay", "Cove", "Dale", "Elm",
]

LAST_NAMES = [
    "Chen", "Reyes", "Park", "Singh", "Tanaka", "Lopez", "Kim", "Mueller",
    "Silva", "Patel", "Sato", "Jensen", "Ali", "Novak", "Costa", "Yamamoto",
    "Sharma", "Berg", "Torres", "Nakamura", "Li", "Rossi", "Cho", "Khan",
    "Hoffman", "Santos", "Ito", "Andersen", "Nguyen", "Petrov", "Martin", "Diaz",
    "Suzuki", "Larsen", "Gupta", "Flores", "Watanabe", "Dubois", "Choi", "Schmidt",
]


def generate_40_teams():
    """Generate participant_40teams.xlsx with 40 teams x 4 players."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Participants"

    ws.append(["Player ID", "Player Name", "Team Name"])

    player_id = 1
    for team_idx, team_name in enumerate(TEAM_NAMES[:40]):
        for p in range(4):
            first = FIRST_NAMES[(team_idx * 4 + p) % len(FIRST_NAMES)]
            last = LAST_NAMES[(team_idx * 4 + p) % len(LAST_NAMES)]
            ws.append([player_id, f"{first} {last}", team_name])
            player_id += 1

    path = os.path.join("participants", "participant_40teams.xlsx")
    wb.save(path)
    print(f"Created {path}: 40 teams, {player_id - 1} players")


def generate_80_players():
    """Generate participant_80players.xlsx with 80 individual players."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Participants"

    ws.append(["Player ID", "Player Name", "Team Name"])

    for pid in range(1, 81):
        first = FIRST_NAMES[(pid - 1) % len(FIRST_NAMES)]
        last = LAST_NAMES[(pid - 1) % len(LAST_NAMES)]
        ws.append([pid, f"{first} {last}", f"Player_{pid}"])

    path = os.path.join("participants", "participant_80players.xlsx")
    wb.save(path)
    print(f"Created {path}: 80 individual players")


if __name__ == "__main__":
    generate_40_teams()
    generate_80_players()
