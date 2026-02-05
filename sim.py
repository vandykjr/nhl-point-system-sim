import simpy
import random
from statemachine import StateMachine, State

GOAL_RATE_HOME_5v5 = 28.6  # minutes per goal
GOAL_RATE_AWAY_5v5 = 26.2  
GOAL_RATE_HOME_4v4 = 27.8  
GOAL_RATE_AWAY_4v4 = 21.4  
GOAL_RATE_HOME_5v4 = 9.5  
GOAL_RATE_AWAY_5v4 = 9.8
GOAL_RATE_HOME_5v3 = 3.7 # No supporting data for 5v3, estimated
GOAL_RATE_AWAY_5v3 = 4.1
GOAL_RATE_HOME_4v5 = 70.3  
GOAL_RATE_AWAY_4v5 = 78.4 
GOAL_RATE_HOME_3v5 = 180.0 
GOAL_RATE_AWAY_3v5 = 200.0
PENALTY_RATE = 10.0    # minutes per penalty
PENALTY_LENGTH = 2.0  # minutes
GOALIE_PULL_TIME = 2.0
GOALIE_PULL_TIME_2 = 6.0

class StrengthStateMachine(StateMachine):
    five_on_five = State("5v5", initial=True)
    four_on_four = State("4v4")
    five_on_four = State("5v4")
    four_on_five = State("4v5")
    five_on_three = State("5v3")
    three_on_five = State("3v5")
    three_on_three = State("3v3")
    six_on_five = State("6v5")
    five_on_six = State("5v6")
    six_on_four = State("6v4")
    four_on_six = State("4v6")
    six_on_three = State("6v3")
    three_on_six = State("3v6")
    six_on_six = State("6v6")

class Team:
    def __init__(self, name):
        self.name = name
        self.goals = 0
        self.penalties = 0


def penalty_killer(env, team):
    """Handle penalty expiration"""
    yield env.timeout(PENALTY_LENGTH)
    team.penalties -= 1
    print(f"[{env.now:.1f}] {team.name} penalty expires (penalties: {team.penalties})")


def hockey_simulation(env, home_team, away_team, game_length=60):
    """Main simulation process with 5v5, penalties, and power plays"""
    
    while env.now < game_length:
        home_goal_rate = GOAL_RATE_HOME_5v4 if away_team.penalties > 0 else GOAL_RATE_HOME_5v5
        away_goal_rate = GOAL_RATE_AWAY_5v4 if home_team.penalties > 0 else GOAL_RATE_AWAY_5v5
        
        time_to_home_goal = random.expovariate(1.0 / home_goal_rate)
        time_to_away_goal = random.expovariate(1.0 / away_goal_rate)
        time_to_penalty_home = random.expovariate(1.0 / PENALTY_RATE)
        time_to_penalty_away = random.expovariate(1.0 / PENALTY_RATE)
        
        # Find next event
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
        events.sort()
        
        next_time, event_type = events[0]
        
        if next_time >= game_length:
            break
        
        yield env.timeout(next_time - env.now)
        
        if event_type == "goal_home":
            home_team.goals += 1
            if away_team.penalties > 0:
                print(f"[{env.now:.1f}] POWER PLAY GOAL! {home_team.name} score! ({home_team.goals}-{away_team.goals})")
            else:
                print(f"[{env.now:.1f}] GOAL! {home_team.name} score! ({home_team.goals}-{away_team.goals})")
        
        elif event_type == "goal_away":
            away_team.goals += 1
            if home_team.penalties > 0:
                print(f"[{env.now:.1f}] POWER PLAY GOAL! {away_team.name} score! ({home_team.goals}-{away_team.goals})")
            else:
                print(f"[{env.now:.1f}] GOAL! {away_team.name} score! ({home_team.goals}-{away_team.goals})")
        
        elif event_type == "penalty_home":
            home_team.penalties += 1
            print(f"[{env.now:.1f}] PENALTY! {home_team.name} take a penalty (penalties: {home_team.penalties})")
            env.process(penalty_killer(env, home_team))
        
        elif event_type == "penalty_away":
            away_team.penalties += 1
            print(f"[{env.now:.1f}] PENALTY! {away_team.name} take a penalty (penalties: {away_team.penalties})")
            env.process(penalty_killer(env, away_team))
    
    print("\n" + "="*50)
    print(f"FINAL SCORE: {home_team.name} {home_team.goals} - {away_team.goals} {away_team.name}")
    print("="*50)


if __name__ == "__main__":
    random.seed(0)
    
    home = Team("Red Wings")
    away = Team("Maple Leafs")
    
    env = simpy.Environment()
    env.process(hockey_simulation(env, home, away, game_length=60))
    env.run()