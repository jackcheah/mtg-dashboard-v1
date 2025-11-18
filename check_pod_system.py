"""Check if the pairing algorithm creates fixed pods"""

from tournament_dashboard import TournamentManager

# Setup 16-team tournament
tournament = TournamentManager()
tournament.configure_swiss_rounds(4)

for i in range(16):
    team_name = f'Team_{i+1:02d}'
    tournament.teams[team_name] = []
    for j in range(4):
        player_id = (i * 4) + j + 1
        tournament.teams[team_name].append({
            'Player ID': player_id,
            'Player Name': f'Player_{player_id:03d}',
            'Team Name': team_name
        })

tournament.determine_tournament_structure()
tournament.setup_tournament()

# Check all teams
print('='*80)
print('CHECKING ALL TEAMS FOR REPEAT MATCHUPS')
print('='*80)

pods_detected = {}

for target_team in tournament.teams.keys():
    opponents_per_round = {}

    for round_num in range(1, 5):
        tables = tournament.tables.get(round_num, {})

        for table_name, players in tables.items():
            for player in players:
                if player['Team Name'] == target_team:
                    opponents = set([p['Team Name'] for p in players if p['Team Name'] != target_team])
                    if round_num not in opponents_per_round:
                        opponents_per_round[round_num] = opponents
                    break

    # Check if same opponents every round
    all_opponents = list(opponents_per_round.values())
    if len(set(frozenset(x) for x in all_opponents)) == 1:
        pod = frozenset([target_team]).union(all_opponents[0])
        pods_detected[pod] = True

print(f'\n❌ POD SYSTEM DETECTED: {len(pods_detected)} pods of 4 teams each')
print('Each pod plays internally for all rounds (NOT proper Swiss pairing!)\n')

for i, pod in enumerate(pods_detected.keys(), 1):
    print(f'Pod {i}: {sorted(list(pod))}')

print('\n' + '='*80)
print('CONCLUSION')
print('='*80)
print('❌ The current pairing algorithm creates FIXED PODS')
print('❌ Teams face the SAME 3 opponents in EVERY Swiss round')
print('❌ This is NOT proper Swiss pairing!')
print('')
print('✅ Proper Swiss should pair teams against DIFFERENT opponents each round')
print('✅ Teams should only meet each other ONCE across all Swiss rounds')
