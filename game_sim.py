import simpy
import random

GOAL_RATE_HOME_5v5 = 28.6  # minutes per goal
GOAL_RATE_AWAY_5v5 = 26.2  
GOAL_RATE_HOME_4v4 = 27.8  
GOAL_RATE_AWAY_4v4 = 21.4  
GOAL_RATE_HOME_5v4 = 9.5  
GOAL_RATE_AWAY_5v4 = 9.8
GOAL_RATE_HOME_4v5 = 70.3  
GOAL_RATE_AWAY_4v5 = 78.4 
GOAL_RATE_HOME_6v5 = 8.5
GOAL_RATE_AWAY_6v5 = 8.5
GOAL_RATE_HOME_6v4 = 6.0
GOAL_RATE_AWAY_6v4 = 5.1
GOAL_RATE_HOME_6v3 = 4.0 # No data for 3 player situations, I estimated
GOAL_RATE_AWAY_6v3 = 3.5
GOAL_RATE_HOME_5v3 = 3.7 
GOAL_RATE_AWAY_5v3 = 4.1
GOAL_RATE_HOME_4v3 = 7.0
GOAL_RATE_AWAY_4v3 = 8.0
GOAL_RATE_HOME_3v4 = 50.0
GOAL_RATE_AWAY_3v4 = 60.0
GOAL_RATE_HOME_3v3 = 15.0
GOAL_RATE_AWAY_3v3 = 15.0
GOAL_RATE_HOME_3v5 = 180.0 
GOAL_RATE_AWAY_3v5 = 200.0
OPP_GOALIE_PULL_MULTIPLIER = 0.1
PENALTY_RATE = 11.2    # minutes per penalty
PENALTY_LENGTH = 2.0  # minutes
GOALIE_PULL_TIME = 2.0
GOALIE_PULL_TIME_2 = 6.0

class Team:
    def __init__(self, name):
        self.name = name
        self.goals = 0
        self.penalties = 0
        self.goalie_pulled = False
        self.active_penalty_ids = []
        self.cleared_penalty_ids = []
        self.penalty_counter = 0


def penalty_killer(env, team, p_id):
    """Handle penalty expiration for a specific penalty ID"""
    yield env.timeout(PENALTY_LENGTH)
    
    if p_id in team.cleared_penalty_ids:
        team.cleared_penalty_ids.remove(p_id)
    else:
        if p_id in team.active_penalty_ids:
            team.active_penalty_ids.remove(p_id)
            team.penalties = len(team.active_penalty_ids)
            print(f"[{env.now:.1f}] {team.name} penalty expires (penalties: {team.penalties})")

def check_goalie_pull(env, home_team, away_team, game_length):
    """Check if either team should pull their goalie"""
    time_remaining = game_length - env.now
    
    score_diff = home_team.goals - away_team.goals
    if score_diff < 0 and score_diff >= -3:
        if score_diff == -1 and time_remaining <= GOALIE_PULL_TIME and not home_team.goalie_pulled:
            home_team.goalie_pulled = True
            print(f"[{env.now:.1f}] GOALIE PULL! {home_team.name} pull goalie (down by 1)")
        elif time_remaining <= GOALIE_PULL_TIME_2 and not home_team.goalie_pulled:
            home_team.goalie_pulled = True
            print(f"[{env.now:.1f}] GOALIE PULL! {home_team.name} pull goalie (down by {-score_diff})")
    elif home_team.goalie_pulled:
        home_team.goalie_pulled = False
        print(f"[{env.now:.1f}] GOALIE RETURNED! {home_team.name} return goalie to net")
    
    score_diff = away_team.goals - home_team.goals
    if score_diff < 0 and score_diff >= -3:
        if score_diff == -1 and time_remaining <= GOALIE_PULL_TIME and not away_team.goalie_pulled:
            away_team.goalie_pulled = True
            print(f"[{env.now:.1f}] GOALIE PULL! {away_team.name} pull goalie (down by 1)")
        elif time_remaining <= GOALIE_PULL_TIME_2 and not away_team.goalie_pulled:
            away_team.goalie_pulled = True
            print(f"[{env.now:.1f}] GOALIE PULL! {away_team.name} pull goalie (down by {-score_diff})")
    elif away_team.goalie_pulled:
        away_team.goalie_pulled = False
        print(f"[{env.now:.1f}] GOALIE RETURNED! {away_team.name} return goalie to net")

def get_goal_rate(home_penalties, away_penalties, home_goalie_pulled, away_goalie_pulled):
    if home_goalie_pulled:
        if home_penalties == 0 and away_penalties == 0:
            return GOAL_RATE_HOME_6v5, GOAL_RATE_AWAY_5v5 * OPP_GOALIE_PULL_MULTIPLIER
        elif home_penalties == 1 and away_penalties == 0:
            return GOAL_RATE_HOME_5v5, GOAL_RATE_AWAY_5v4 * OPP_GOALIE_PULL_MULTIPLIER
        elif home_penalties == 0 and away_penalties == 1:
            return GOAL_RATE_HOME_6v4, GOAL_RATE_AWAY_4v5 * OPP_GOALIE_PULL_MULTIPLIER
        elif home_penalties == 1 and away_penalties == 1:
            return GOAL_RATE_HOME_5v4, GOAL_RATE_AWAY_4v4 * OPP_GOALIE_PULL_MULTIPLIER
        elif home_penalties >= 2 and away_penalties >= 2:
            return GOAL_RATE_HOME_4v3, GOAL_RATE_AWAY_3v3 * OPP_GOALIE_PULL_MULTIPLIER
        elif home_penalties >= 2 and away_penalties == 1:
            return GOAL_RATE_HOME_4v4, GOAL_RATE_AWAY_4v3 * OPP_GOALIE_PULL_MULTIPLIER
        elif home_penalties >= 2 and away_penalties == 0:
            return GOAL_RATE_HOME_4v5, GOAL_RATE_AWAY_5v3 * OPP_GOALIE_PULL_MULTIPLIER
        elif home_penalties == 1 and away_penalties >= 2:
            return GOAL_RATE_HOME_5v3, GOAL_RATE_AWAY_3v4 * OPP_GOALIE_PULL_MULTIPLIER
        elif home_penalties == 0 and away_penalties >= 2:
            return GOAL_RATE_HOME_6v3, GOAL_RATE_AWAY_3v5 * OPP_GOALIE_PULL_MULTIPLIER
    elif away_goalie_pulled:
        if home_penalties == 0 and away_penalties == 0:
            return GOAL_RATE_HOME_5v5 * OPP_GOALIE_PULL_MULTIPLIER, GOAL_RATE_AWAY_6v5
        elif home_penalties == 1 and away_penalties == 0:
            return GOAL_RATE_HOME_4v5 * OPP_GOALIE_PULL_MULTIPLIER, GOAL_RATE_AWAY_6v4 
        elif home_penalties == 0 and away_penalties == 1:
            return GOAL_RATE_HOME_5v4 * OPP_GOALIE_PULL_MULTIPLIER, GOAL_RATE_AWAY_5v5
        elif home_penalties == 1 and away_penalties == 1:
            return GOAL_RATE_HOME_4v4 * OPP_GOALIE_PULL_MULTIPLIER, GOAL_RATE_AWAY_5v4
        elif home_penalties >= 2 and away_penalties >= 2:
            return GOAL_RATE_HOME_3v3 * OPP_GOALIE_PULL_MULTIPLIER, GOAL_RATE_AWAY_4v3
        elif home_penalties >= 2 and away_penalties == 1:
            return GOAL_RATE_HOME_3v4 * OPP_GOALIE_PULL_MULTIPLIER, GOAL_RATE_AWAY_5v3
        elif home_penalties >= 2 and away_penalties == 0:
            return GOAL_RATE_HOME_3v5 * OPP_GOALIE_PULL_MULTIPLIER, GOAL_RATE_AWAY_6v3
        elif home_penalties == 1 and away_penalties >= 2:
            return GOAL_RATE_HOME_4v3 * OPP_GOALIE_PULL_MULTIPLIER, GOAL_RATE_AWAY_4v4
        elif home_penalties == 0 and away_penalties >= 2:
            return GOAL_RATE_HOME_5v3 * OPP_GOALIE_PULL_MULTIPLIER, GOAL_RATE_AWAY_4v5
    else:
        if home_penalties == 0 and away_penalties == 0:
            return GOAL_RATE_HOME_5v5, GOAL_RATE_AWAY_5v5
        elif home_penalties == 1 and away_penalties == 0:
            return GOAL_RATE_HOME_4v5, GOAL_RATE_AWAY_5v4
        elif home_penalties == 0 and away_penalties == 1:
            return GOAL_RATE_HOME_5v4, GOAL_RATE_AWAY_4v5
        elif home_penalties == 1 and away_penalties == 1:
            return GOAL_RATE_HOME_4v4, GOAL_RATE_AWAY_4v4
        elif home_penalties >= 2 and away_penalties >= 2:
            return GOAL_RATE_HOME_3v3, GOAL_RATE_AWAY_3v3
        elif home_penalties >= 2 and away_penalties == 1:
            return GOAL_RATE_HOME_3v4, GOAL_RATE_AWAY_4v3
        elif home_penalties >= 2 and away_penalties == 0:
            return GOAL_RATE_HOME_3v5, GOAL_RATE_AWAY_5v3
        elif home_penalties == 1 and away_penalties >= 2:
            return GOAL_RATE_HOME_4v3, GOAL_RATE_AWAY_3v4
        elif home_penalties == 0 and away_penalties >= 2:
            return GOAL_RATE_HOME_5v3, GOAL_RATE_AWAY_3v5


def hockey_simulation(env, home_team, away_team, game_length=60, ot=True):
    """Main simulation process with 5v5, penalties, and power plays"""
    
    while env.now < game_length:
        home_goal_rate, away_goal_rate = get_goal_rate(home_team.penalties, away_team.penalties, home_team.goalie_pulled, away_team.goalie_pulled)
        
        time_to_home_goal = random.expovariate(1.0 / home_goal_rate)
        time_to_away_goal = random.expovariate(1.0 / away_goal_rate)
        time_to_penalty_home = random.expovariate(1.0 / PENALTY_RATE)
        time_to_penalty_away = random.expovariate(1.0 / PENALTY_RATE)
        
        next_home_goal = env.now + time_to_home_goal
        next_away_goal = env.now + time_to_away_goal
        next_penalty_home = env.now + time_to_penalty_home
        next_penalty_away = env.now + time_to_penalty_away
        
        events = [
            (next_home_goal, "goal_home"),
            (next_away_goal, "goal_away"),
            (next_penalty_home, "penalty_home"),
            (next_penalty_away, "penalty_away")
        ]
        
        pull_time_2_mark = game_length - GOALIE_PULL_TIME_2
        if env.now < pull_time_2_mark:
            events.append((pull_time_2_mark, "check_goalie_pull"))
            
        pull_time_1_mark = game_length - GOALIE_PULL_TIME
        if env.now < pull_time_1_mark:
            events.append((pull_time_1_mark, "check_goalie_pull"))
        
        events.sort()
        
        next_time, event_type = events[0]
        
        if next_time >= game_length:
            break
        
        yield env.timeout(next_time - env.now)
        
        if event_type == "goal_home":
            home_team.goals += 1
            if away_team.penalties > home_team.penalties:
                print(f"[{env.now:.1f}] POWER PLAY GOAL! {home_team.name} score!")
                if away_team.active_penalty_ids:
                    oldest_p = away_team.active_penalty_ids.pop(0)
                    away_team.cleared_penalty_ids.append(oldest_p)
                    away_team.penalties = len(away_team.active_penalty_ids)
            else:
                print(f"[{env.now:.1f}] GOAL! {home_team.name} score! ({home_team.goals}-{away_team.goals})")
            check_goalie_pull(env, home_team, away_team, game_length)
        
        elif event_type == "goal_away":
            away_team.goals += 1
            if home_team.penalties > away_team.penalties:
                print(f"[{env.now:.1f}] POWER PLAY GOAL! {away_team.name} score!")
                if home_team.active_penalty_ids:
                    oldest_p = home_team.active_penalty_ids.pop(0)
                    home_team.cleared_penalty_ids.append(oldest_p)
                    home_team.penalties = len(home_team.active_penalty_ids)
            else:
                print(f"[{env.now:.1f}] GOAL! {away_team.name} score! ({home_team.goals}-{away_team.goals})")
            check_goalie_pull(env, home_team, away_team, game_length)
        
        elif event_type == "penalty_home":
            home_team.penalty_counter += 1
            p_id = home_team.penalty_counter
            home_team.active_penalty_ids.append(p_id)
            home_team.penalties = len(home_team.active_penalty_ids)
            print(f"[{env.now:.1f}] PENALTY! {home_team.name} (ID:{p_id}) (penalties: {home_team.penalties})")
            env.process(penalty_killer(env, home_team, p_id))
        
        elif event_type == "penalty_away":
            away_team.penalty_counter += 1
            p_id = away_team.penalty_counter
            away_team.active_penalty_ids.append(p_id)
            away_team.penalties = len(away_team.active_penalty_ids)
            print(f"[{env.now:.1f}] PENALTY! {away_team.name} (ID:{p_id}) (penalties: {away_team.penalties})")
            env.process(penalty_killer(env, away_team, p_id))
            
        elif event_type == "check_goalie_pull":
            check_goalie_pull(env, home_team, away_team, game_length)
        
    print("\n" + "="*50)
    print(f"END OF REGULATION: {home_team.name} {home_team.goals} - {away_team.goals} {away_team.name}")
    print("="*50)
    if home_team.goals > away_team.goals:
        return 0
    elif away_team.goals > home_team.goals:
        return 2
    else:
        if ot:
            random_value = random.random()
            if random_value <= 0.5:
                print("Overtime Result: Home team wins in OT!")
                return 1
            else:
                print("Overtime Result: Away team wins in OT!")
                return 3
        return 4


# if __name__ == "__main__":
#     home = Team("Red Wings")
#     away = Team("Maple Leafs")
#     env = simpy.Environment()
#     env.process(hockey_simulation(env, home, away, game_length=60))
#     env.run()