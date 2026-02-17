from game_sim import Team, hockey_simulation, strategy
import simpy
from numpy import random
REGULATION_WIN_POINTS = 3
OT_WIN_POINTS = 2
TIE_POINTS = 1
OT_LOSS_POINTS = 1
REGULATION_LOSS_POINTS = 0
AGGRESSIVENESS_COEFFICIENT = 3.3077
OT_PROBABILITY = 0.2

def playoff_probability(standings: dict, games: int, ot: bool, playoff_teams: int) -> dict:
    probs = {}
    simulations = 10000
    playoff_apperances = {team: 0 for team in standings.keys()}
    for _ in range(simulations):
        sim_standings = {team: stats.copy() for team, stats in standings.items()}
        for team in sim_standings.keys():
            games_remaining = games - sim_standings[team]['GP']
            if ot:
                avg_points_per_game = (1 - OT_PROBABILITY)* 0.5 * REGULATION_WIN_POINTS + OT_PROBABILITY * 0.5 * OT_WIN_POINTS + OT_PROBABILITY * 0.5 * OT_LOSS_POINTS +  (1 - OT_PROBABILITY) * 0.5 * REGULATION_LOSS_POINTS
            else:
                avg_points_per_game = (1 - OT_PROBABILITY) * 0.5 * REGULATION_WIN_POINTS + OT_PROBABILITY * TIE_POINTS + (1 - OT_PROBABILITY) * 0.5 * REGULATION_LOSS_POINTS
            sim_standings[team]['PTS'] += random.normal(loc=avg_points_per_game * games_remaining, scale=games_remaining**0.5)
        sorted_teams = sorted(sim_standings.items(), key=lambda x: x[1]['PTS'], reverse=True)
        for i in range(playoff_teams):
            playoff_apperances[sorted_teams[i][0]] += 1
    for team, count in playoff_apperances.items():
        probs[team] = count / simulations
    return sorted(probs.items(), key=lambda x: x[1], reverse=True)

def get_goalie_pull_threshold(standings: dict, games: int, ot: bool, playoff_teams: int) -> dict:
    base_probabilities = playoff_probability(standings, games, ot, playoff_teams)
    prob_gained_with_win = {}
    prob_lost_with_loss = {}
    for team in standings.keys():
        original_prob = dict(base_probabilities)[team]
        standings[team]['PTS'] += REGULATION_WIN_POINTS
        standings[team]['GP'] += 1
        new_prob_win = dict(playoff_probability(standings, games, ot, playoff_teams))[team]
        prob_gained_with_win[team] = new_prob_win - original_prob
        standings[team]['PTS'] -= REGULATION_WIN_POINTS
        standings[team]['GP'] -= 1
        
        standings[team]['PTS'] += OT_LOSS_POINTS
        standings[team]['GP'] += 1
        new_prob_loss = dict(playoff_probability(standings, games, ot, playoff_teams))[team]
        prob_lost_with_loss[team] = original_prob - new_prob_loss
        standings[team]['PTS'] -= OT_LOSS_POINTS
        standings[team]['GP'] -= 1
    thresholds = {team: prob_gained_with_win[team] / prob_lost_with_loss[team] if prob_lost_with_loss[team] > 0 else float('inf') for team in standings.keys()}
    return thresholds

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

def season_simulation(teams, num_games_per_opp=10, game_length=60, ot=True, playoff_teams=4):
    standings = {team.name: {'GP': 0, 'W': 0, 'L': 0, 'OTL': 0, 'PTS': 0, 'RW': 0} for team in teams}
    full_schedule = generate_round_robin_schedule(teams, repeats=num_games_per_opp)
    games = num_games_per_opp * (len(teams) - 1)
    game_count = 1
    for round_matchups in full_schedule:
        thresholds = get_goalie_pull_threshold(standings, games, ot, playoff_teams)
        for home_team, away_team in round_matchups:
            if home_team == "BYE" or away_team == "BYE": 
                continue
            env = simpy.Environment()
            for team in teams:
                team.goals = 0
                team.penalties = 0
                team.goalie_pulled = False
                team.active_penalty_ids = []
                team.cleared_penalty_ids = []
                team.penalty_counter = 0
                team.pull_goalie_in_tie = thresholds[team.name] > team.pull_in_tie_threshold
            
            print(f"\nStarting Game {game_count}: {home_team.name} vs {away_team.name}")
            game_process = env.process(hockey_simulation(env, home_team, away_team, game_length, ot))
            env.run(until=game_process)
        
            result = game_process.value 
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
        # print(playoff_probability(standings, games=games, ot=ot, playoff_teams=playoff_teams))
        print_league_standings(standings)
    # print_league_standings(standings)
    

if __name__ == "__main__":
    det = Team("Red Wings", strategy=strategy.BALANCED, pull_in_tie_threshold=3.3077)
    tor = Team("Maple Leafs", strategy=strategy.BALANCED, pull_in_tie_threshold=1.0)
    bos = Team("Bruins", strategy=strategy.BALANCED, pull_in_tie_threshold=3.0)
    mtl = Team("Canadiens", strategy=strategy.BALANCED, pull_in_tie_threshold=2.3077)
    nyr = Team("Rangers", strategy=strategy.BALANCED, pull_in_tie_threshold=4.3077)
    chi = Team("Blackhawks", strategy=strategy.BALANCED, pull_in_tie_threshold=float('inf'))
    teams = [tor,chi,det,bos,mtl,nyr]
    season_simulation(teams, num_games_per_opp=16, game_length=60, ot=True, playoff_teams=4)