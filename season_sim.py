from game_sim import Team, hockey_simulation
import simpy
REGULATION_WIN_POINTS = 3
OT_WIN_POINTS = 2
TIE_POINTS = 1
OT_LOSS_POINTS = 1
REGULATION_LOSS_POINTS = 0

def generate_round_robin_schedule(teams, repeats=10):
    if len(teams) % 2 != 0:
        teams.append("BYE")
        
    n = len(teams)
    schedule = []
    
    for _ in range(repeats):
        rotation = list(teams)
        
        for round_num in range(n - 1):
            round_matchups = []
            for i in range(n // 2):
                home = rotation[i]
                away = rotation[n - 1 - i]
                
                if round_num % 2 == 0:
                    round_matchups.append((home, away))
                else:
                    round_matchups.append((away, home))
            
            schedule.append(round_matchups)
            rotation = [rotation[0]] + [rotation[-1]] + rotation[1:-1]
            
    return schedule

def print_league_standings(standings):
    sorted_table = sorted(standings.items(), key=lambda x: (x[1]['PTS'], x[1]['RW'], x[1]['W']), reverse=True)
    
    print(f"{'TEAM':<15} | {'GP':>3} | {'W':>3} | {'L':>3} | {'OTL':>3} | {'PTS':>4} | {'RW':>3}")
    for name, stats in sorted_table:
        print(f"{name:<15} | {stats['GP']:>3} | {stats['W']:>3} | {stats['L']:>3} | {stats['OTL']:>3} | {stats['PTS']:>4} | {stats['RW']:>3}")

def season_simulation(teams, num_games_per_opp=10, game_length=60, ot=True):
    standings = {team.name: {'GP': 0, 'W': 0, 'L': 0, 'OTL': 0, 'PTS': 0, 'RW': 0} for team in teams}
    full_schedule = generate_round_robin_schedule(teams, repeats=num_games_per_opp)
    
    game_count = 1
    for round_matchups in full_schedule:
        for home_team, away_team in round_matchups:
            if home_team == "BYE" or away_team == "BYE": continue
            env = simpy.Environment()
        
            for team in teams:
                team.goals = 0
                team.penalties = 0
                team.goalie_pulled = False
                team.active_penalty_ids = []
                team.cleared_penalty_ids = []

            
            print(f"\nStarting Game {game_count}: {home_team.name} vs {away_team.name}")
            game_process = env.process(hockey_simulation(env, home_team, away_team, game_length))
            env.run(until=game_process)
        
            result = game_process.value 
            game_count += 1
            standings[home_team.name]['GP'] += 1
            standings[away_team.name]['GP'] += 1
            if result == 0:  # Home team wins in regulation
                standings[home_team.name]['W'] += 1
                standings[home_team.name]['RW'] += 1
                standings[home_team.name]['PTS'] += REGULATION_WIN_POINTS
                standings[away_team.name]['L'] += 1
            elif result == 2:  # Away team wins in regulation
                standings[away_team.name]['W'] += 1
                standings[away_team.name]['RW'] += 1
                standings[away_team.name]['PTS'] += REGULATION_WIN_POINTS
                standings[home_team.name]['L'] += 1
            elif result == 1:  # Home team wins in OT
                standings[home_team.name]['W'] += 1
                standings[home_team.name]['PTS'] += OT_WIN_POINTS
                standings[away_team.name]['OTL'] += 1
                standings[away_team.name]['PTS'] += OT_LOSS_POINTS
            elif result == 3:  # Away team wins in OT
                standings[away_team.name]['W'] += 1
                standings[away_team.name]['PTS'] += OT_WIN_POINTS
                standings[home_team.name]['OTL'] += 1
                standings[home_team.name]['PTS'] += OT_LOSS_POINTS
            else: # Tie
                standings[home_team.name]['PTS'] += TIE_POINTS
                standings[away_team.name]['PTS'] += TIE_POINTS
                standings[home_team.name]['OTL'] += 1
                standings[away_team.name]['OTL'] += 1
            game_count += 1

    print_league_standings(standings)
    

if __name__ == "__main__":
    det = Team("Red Wings")
    tor = Team("Maple Leafs")
    bos = Team("Bruins")
    mtl = Team("Canadiens")
    nyr = Team("Rangers")
    chi = Team("Blackhawks")
    teams = [det, tor, bos, mtl, nyr, chi]
    season_simulation(teams, num_games_per_opp=10, game_length=60, ot=True)