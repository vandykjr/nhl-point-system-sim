from game_sim import Team, hockey_simulation, strategy
import simpy
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing as mp
REGULATION_WIN_POINTS = 2
OT_WIN_POINTS = 2
TIE_POINTS = 1
OT_LOSS_POINTS = 1
REGULATION_LOSS_POINTS = 0
OT_PROBABILITY = 0.2

def playoff_probability(standings: dict, total_games: int, ot: bool, playoff_teams: int, n_sims: int = 10000) -> list:
    team_names = list(standings.keys())
    n_teams = len(team_names)
    
    current_pts = np.array([standings[t]['PTS'] for t in team_names])
    games_played = np.array([standings[t]['GP'] for t in team_names])
    games_remaining = total_games - games_played
    
    games_remaining = np.maximum(games_remaining, 0)

    if ot:
        avg_ppg = ((1 - OT_PROBABILITY) * 0.5 * REGULATION_WIN_POINTS + 
                   OT_PROBABILITY * 0.5 * OT_WIN_POINTS + 
                   OT_PROBABILITY * 0.5 * OT_LOSS_POINTS + 
                   (1 - OT_PROBABILITY) * 0.5 * REGULATION_LOSS_POINTS)
    else:
        avg_ppg = ((1 - OT_PROBABILITY) * 0.5 * REGULATION_WIN_POINTS + 
                   OT_PROBABILITY * TIE_POINTS + 
                   (1 - OT_PROBABILITY) * 0.5 * REGULATION_LOSS_POINTS)

    means = avg_ppg * games_remaining
    stds = np.sqrt(games_remaining)
    
    simulated_future_pts = np.random.normal(loc=means, scale=stds, size=(n_sims, n_teams))

    max_possible_pts = games_remaining * REGULATION_WIN_POINTS
    simulated_future_pts = np.clip(simulated_future_pts, 0, max_possible_pts)

    final_pts = current_pts + simulated_future_pts

    ranks = np.argsort(np.argsort(-final_pts, axis=1), axis=1)

    made_playoffs = ranks < playoff_teams
    
    probs_array = np.mean(made_playoffs, axis=0)

    results = {team: prob for team, prob in zip(team_names, probs_array)}
    return sorted(results.items(), key=lambda x: x[1], reverse=True)

def get_goalie_pull_threshold(standings: dict, games: int, ot: bool, playoff_teams: int) -> tuple[dict, dict]:
    base_probabilities = playoff_probability(standings, games, ot, playoff_teams)
    prob_gained_with_win = {}
    prob_lost_with_loss = {}
    MIN_THRESHOLD = 0.05
    for team in standings.keys():
        original_prob = dict(base_probabilities)[team]
        standings[team]['PTS'] += REGULATION_WIN_POINTS
        standings[team]['GP'] += 1
        new_prob_win = dict(playoff_probability(standings, games, ot, playoff_teams))[team]
        prob_gained_with_win[team] = new_prob_win - original_prob
        standings[team]['PTS'] -= REGULATION_WIN_POINTS
        standings[team]['GP'] -= 1
        
        standings[team]['PTS'] += REGULATION_LOSS_POINTS
        standings[team]['GP'] += 1
        new_prob_loss = dict(playoff_probability(standings, games, ot, playoff_teams))[team]
        prob_lost_with_loss[team] = original_prob - new_prob_loss
        standings[team]['PTS'] -= REGULATION_LOSS_POINTS
        standings[team]['GP'] -= 1
    thresholds = {team: prob_gained_with_win[team] / prob_lost_with_loss[team] if prob_lost_with_loss[team] > 0 or prob_gained_with_win[team] > MIN_THRESHOLD else 0.0 for team in standings.keys()}
    # print(base_probabilities)
    # print(prob_gained_with_win)
    # print(prob_lost_with_loss)
    # print(thresholds)
    return thresholds, base_probabilities

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
    standings_list = []
    probabilities_list = []
    full_schedule = generate_round_robin_schedule(teams, repeats=num_games_per_opp)
    games = num_games_per_opp * (len(teams) - 1)
    game_count = 1
    for round_matchups in full_schedule:
        # thresholds, probabilities = get_goalie_pull_threshold(standings, games, ot, playoff_teams)
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
                team.pull_goalie_in_tie = False
            
            # print(f"\nStarting Game {game_count}: {home_team.name} vs {away_team.name}")
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
        # print_league_standings(standings)
        standings_list.append({team: stats.copy() for team, stats in standings.items()})
        probabilities = playoff_probability(standings, games, ot, playoff_teams)
        probabilities_list.append(probabilities)
    print_league_standings(standings)
    return standings_list, probabilities_list    

def plot_probs_by_rank(avg_probs_by_rank):
    plt.figure(figsize=(12, 7))
    for r in range(avg_probs_by_rank.shape[1]):
        plt.plot(avg_probs_by_rank[:, r], label=f"Rank {r+1}")
    
    plt.title("Average Playoff Probability Based on Current Rank")
    plt.xlabel("Days / Games into Season")
    plt.ylabel("Playoff Probability")
    plt.ylim(0, 1.05)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()

def plot_playoff_percent_by_pull_threshold(playoff_percentages, pull_thresholds):
    plt.figure(figsize=(10, 6))
    
    x_labels = [str(t) for t in pull_thresholds]
    
    bars = plt.bar(x_labels, playoff_percentages, color='skyblue', edgecolor='navy', alpha=0.8)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.01, f'{yval:.1%}', ha='center', va='bottom')

    plt.title("Playoff Success vs. Goalie Pull Strategy", fontsize=14)
    plt.xlabel("Goalie Pull Threshold", fontsize=12)
    plt.ylabel("Percentage of Seasons Made Playoffs", fontsize=12)
    plt.ylim(0, max(playoff_percentages) + 0.1)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

def plot_playoff_percent_by_strategy(strategies, percentages):
    plt.figure(figsize=(8, 6))    
    bars = plt.bar(strategies, percentages, edgecolor='black', alpha=0.8)
    
    plt.title("Playoff Success by Team Strategy", fontsize=14)
    plt.ylabel("Average Playoff Made %", fontsize=12)
    plt.xlabel("Strategy Type", fontsize=12)
    plt.ylim(0, max(percentages) + 0.1)
    
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                 f'{height:.1%}', ha='center', va='bottom', fontweight='bold')
    
    plt.grid(axis='y', linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.show()

def plot_team_points_progression(standings_list):
    """
    Plots the point progression for each team over the course of the season.
    """
    if not standings_list:
        print("No data to plot.")
        return

    team_names = list(standings_list[0].keys())
    
    history = {name: [0] for name in team_names}
    
    for snapshot in standings_list:
        for name in team_names:
            history[name].append(snapshot[name]['PTS'])

    plt.figure(figsize=(12, 6))
    
    rounds = range(len(history[team_names[0]]))
    for name in team_names:
        plt.plot(rounds, history[name], marker='o', label=name, linewidth=2)

    plt.title("Team Points Progression Over the Season", fontsize=14)
    plt.xlabel("Games Played", fontsize=12)
    plt.ylabel("Points (PTS)", fontsize=12)
    plt.xticks(rounds) 
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.tight_layout()
    plt.show()

def run_single_season(teams):
    return season_simulation(teams, num_games_per_opp=16, game_length=60, ot=True, playoff_teams=4)

if __name__ == "__main__":
    det = Team("Red Wings", strategy=strategy.BALANCED)
    tor = Team("Maple Leafs", strategy=strategy.AGGRESSIVE)
    bos = Team("Bruins", strategy=strategy.CONSERVATIVE)
    mtl = Team("Canadiens", strategy=strategy.AGGRESSIVE)
    teams = [tor,det,bos,mtl]
    standings_list_list = []
    probabilities_list_list = []
    seasons_to_sim = 1
    # pool = mp.Pool(processes=mp.cpu_count() - 1)
    # results = pool.map(run_single_season, [teams] * seasons_to_sim)
    
    # pool.close()
    # pool.join()
    results = [run_single_season(teams) for _ in range(seasons_to_sim)]
    standings_list_list = [r[0] for r in results]
    plot_team_points_progression(standings_list_list[0])
    # probabilities_list_list = [r[1] for r in results]
    # playoffs_made_percentages = {team.name: 0 for team in teams}
    # avg_rankings = {team.name: 0 for team in teams}
    # avg_points = {team.name: 0 for team in teams}
    # std_dev_points_by_team = {team.name: 0 for team in teams}
    # std_dev_points_ovr = 0
    # avg_probs_by_team = {team.name: 0 for team in teams}
    # avg_probs_by_rank = {rank: 0 for rank in range(1, len(teams) + 1)}
    # for standings_list in standings_list_list:
    #     final_standings = standings_list[-1]
    #     sorted_teams = sorted(final_standings.items(), key=lambda x: (x[1]['PTS'], x[1]['RW'], x[1]['W']), reverse=True)
    #     std_dev_points_ovr += np.std([stats['PTS'] for team_name, stats in sorted_teams])
    #     for rank, (team_name, stats) in enumerate(sorted_teams, start=1):
    #         avg_rankings[team_name] += rank
    #         avg_points[team_name] += stats['PTS']
    #         std_dev_points_by_team[team_name] += stats['PTS'] ** 2
    #         if rank <= 4:
    #             playoffs_made_percentages[team_name] += 1
    # std_dev_points_ovr /= seasons_to_sim
    # for team_name in playoffs_made_percentages.keys():
    #     playoffs_made_percentages[team_name] /= seasons_to_sim
    #     avg_rankings[team_name] /= seasons_to_sim
    #     avg_points[team_name] /= seasons_to_sim
    #     std_dev_points_by_team[team_name] = np.sqrt(std_dev_points_by_team[team_name] / seasons_to_sim - avg_points[team_name] ** 2)
    # print("Playoff Percentages:")
    # for team_name, percentage in playoffs_made_percentages.items():
    #     print(f"{team_name}: {percentage:.2%}")
    # print("\nAverage Final Rankings:")
    # for team_name, avg_rank in avg_rankings.items():
    #     print(f"{team_name}: {avg_rank:.2f}")
    # print("\nAverage Final Points:")
    # for team_name, avg_pts in avg_points.items():
    #     print(f"{team_name}: {avg_pts:.2f} (std dev: {std_dev_points_by_team[team_name]:.2f})")
    # print(f"\nOverall Standard Deviation of Points: {std_dev_points_ovr:.2f}")

    # num_time_steps = len(standings_list_list[0])
    # num_teams = len(teams)
    # probs_by_rank_history = np.zeros((num_time_steps, num_teams))

    # for s in range(seasons_to_sim):
    #     season_standings = standings_list_list[s]
    #     season_probs = probabilities_list_list[s]
        
    #     for t in range(num_time_steps):
    #         current_standings = season_standings[t]
    #         current_probs = dict(season_probs[t])
            
    #         sorted_at_t = sorted(
    #             current_standings.items(), 
    #             key=lambda x: (x[1]['PTS'], x[1].get('RW', 0), x[1].get('W', 0)), 
    #             reverse=True
    #         )
            
    #         for rank, (team_name, _) in enumerate(sorted_at_t):
    #             probs_by_rank_history[t, rank] += current_probs[team_name]

    # avg_probs_by_rank = probs_by_rank_history / seasons_to_sim

    # plot_probs_by_rank(avg_probs_by_rank)
    # plot_data = []
    # for team in teams:
    #     threshold = team.pull_in_tie_threshold
    #     percentage = playoffs_made_percentages[team.name]
    #     plot_data.append((threshold, percentage))

    # plot_data.sort(key=lambda x: x[0])

    # sorted_thresholds = [item[0] for item in plot_data]
    # sorted_percentages = [item[1] for item in plot_data]

    # plot_playoff_percent_by_pull_threshold(sorted_percentages, sorted_thresholds)

    # strat_results = {}

    # for team in teams:
    #     strat_name = str(team.strategy).split('.')[-1] 
    #     percent = playoffs_made_percentages[team.name]
        
    #     if strat_name not in strat_results:
    #         strat_results[strat_name] = []
    #     strat_results[strat_name].append(percent)

    # avg_strat_percents = {s: np.mean(p) for s, p in strat_results.items()}

    # order = ['CONSERVATIVE', 'BALANCED', 'AGGRESSIVE']
    # sorted_strats = [s for s in order if s in avg_strat_percents]
    # sorted_vals = [avg_strat_percents[s] for s in sorted_strats]
    # plot_playoff_percent_by_strategy(sorted_strats, sorted_vals)
