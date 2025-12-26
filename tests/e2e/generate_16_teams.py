#!/usr/bin/env python3
"""
Generate 16 Teams for Tournament Testing

This script generates an Excel file with 16 teams (4 players each = 64 total players)
in the format expected by the MTG Dashboard.

The file is placed in the participants directory where the dashboard looks for it.
"""

import os
import openpyxl


def generate_teams():
    """Generate 16 teams with 4 players each."""
    
    # Target path required by the backend
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../participants"))
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, "participant_team.xlsx")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Teams"
    
    # Headers suitable for "Standard column format"
    headers = ["Team Name", "Player Name", "Player ID"]
    ws.append(headers)
    
    # Generate 16 teams with 4 players each
    player_id = 1
    team_names = [
        "Alpha Strike", "Beta Force", "Gamma Wave", "Delta Squad",
        "Epsilon Elite", "Zeta Zealots", "Eta Hawks", "Theta Thunder",
        "Iota Impact", "Kappa Kings", "Lambda Legion", "Mu Masters",
        "Nu Knights", "Xi Xtremes", "Omicron Ops", "Pi Pioneers"
    ]
    
    for i in range(16):
        team_name = team_names[i] if i < len(team_names) else f"Team {chr(65+i)}"
        
        # Generate 4 player names per team
        player_prefixes = ["Captain", "Scout", "Striker", "Guard"]
        
        for p_idx in range(4):
            # Create unique player name
            player_name = f"{player_prefixes[p_idx]}_{team_name.split()[0]}"
            ws.append([team_name, player_name, player_id])
            player_id += 1
    
    wb.save(filepath)
    print(f"✅ Generated {filepath}")
    print(f"   - 16 teams")
    print(f"   - 4 players per team")
    print(f"   - {player_id - 1} total players")
    
    return filepath


def generate_simple_teams():
    """Generate simple team names (Team A, Team B, etc.) for basic testing."""
    
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../participants"))
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, "participant_team.xlsx")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Teams"
    
    # Headers
    headers = ["Team Name", "Player Name", "Player ID"]
    ws.append(headers)
    
    # Generate 16 teams with 4 players each (simple naming)
    player_id = 1
    for i in range(16):
        team_name = f"Team {chr(65+i)}"  # Team A, Team B, ..., Team P
        for p in range(1, 5):
            player_name = f"P{p}_{chr(65+i)}"  # P1_A, P2_A, P3_A, P4_A
            ws.append([team_name, player_name, player_id])
            player_id += 1
    
    wb.save(filepath)
    print(f"✅ Generated {filepath}")
    print(f"   - 16 teams (Team A through Team P)")
    print(f"   - 4 players per team")
    print(f"   - {player_id - 1} total players")
    
    return filepath


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        generate_simple_teams()
    else:
        generate_teams()
