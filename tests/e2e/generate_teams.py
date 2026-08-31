#!/usr/bin/env python3
"""
Generate Teams for Tournament Testing

This script generates an Excel file with N teams (4 players each)
in the format expected by the MTG Dashboard.

Usage:
    python generate_teams.py [num_teams]

    num_teams: any multiple of 4 from 8 to 40 (default: 16)
"""

import os
import sys
import openpyxl

def generate_teams(num_teams=16):
    """Generate teams with 4 players each."""
    
    if num_teams % 4 != 0 or num_teams < 8 or num_teams > 40:
        print(f"⚠️  Warning: {num_teams} is not a supported team count (8-40, multiples of 4). Generating anyway...")
    
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
    
    # Generate teams with 4 players each
    player_id = 1
    
    # Pool of team names (40 names to support max team count)
    team_names_pool = [
        "Alpha Strike", "Beta Force", "Gamma Wave", "Delta Squad",
        "Epsilon Elite", "Zeta Zealots", "Eta Hawks", "Theta Thunder",
        "Iota Impact", "Kappa Kings", "Lambda Legion", "Mu Masters",
        "Nu Knights", "Xi Xtremes", "Omicron Ops", "Pi Pioneers",
        "Rho Raiders", "Sigma Storm", "Tau Titans", "Upsilon Ultra",
        "Phi Phoenix", "Chi Champions", "Psi Power", "Omega Order",
        "Atlas Army", "Bolt Brigade", "Crux Crew", "Dusk Dynasty",
        "Echo Elite", "Flux Force", "Gale Guard", "Hex Hawks",
        "Ion Impact", "Jinx Jokers", "Knox Knights", "Lynx Legends",
        "Mist Mages", "Nova Nexus", "Onyx Order", "Pyro Phantoms"
    ]
    
    team_names = team_names_pool[:num_teams]
    
    # If we need more names than in the pool (unlikely for <20)
    if len(team_names) < num_teams:
        for i in range(len(team_names), num_teams):
            team_names.append(f"Team {chr(65+i)}")
            
    for i, team_name in enumerate(team_names):
        # Generate 4 player names per team
        player_prefixes = ["Captain", "Scout", "Striker", "Guard"]
        
        for p_idx in range(4):
            # Create unique player name
            prefix = player_prefixes[p_idx]
            # Use short team identifier for player name to keep it readable
            team_short = team_name.split()[0]
            player_name = f"{prefix}_{team_short}"
            
            ws.append([team_name, player_name, player_id])
            player_id += 1
    
    wb.save(filepath)
    print(f"✅ Generated {filepath}")
    print(f"   - {num_teams} teams")
    print(f"   - 4 players per team")
    print(f"   - {player_id - 1} total players")
    
    return filepath

if __name__ == "__main__":
    num_teams = 16
    if len(sys.argv) > 1:
        try:
            num_teams = int(sys.argv[1])
        except ValueError:
            print("Usage: python generate_teams.py [num_teams]")
            sys.exit(1)
            
    generate_teams(num_teams)
