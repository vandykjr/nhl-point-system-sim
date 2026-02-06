import simpy
import random
from statemachine import StateMachine, State

GOAL_RATE_HOME_5v5 = 28.6  # minutes per goal
GOAL_RATE_AWAY_5v5 = 26.2  
GOAL_RATE_HOME_4v4 = 27.8  
GOAL_RATE_AWAY_4v4 = 21.4  
GOAL_RATE_HOME_5v4 = 9.5  
GOAL_RATE_AWAY_5v4 = 9.8
GOAL_RATE_HOME_5v3 = 3.7 # No data for 5v3, I estimated
GOAL_RATE_AWAY_5v3 = 4.1
GOAL_RATE_HOME_4v5 = 70.3  
GOAL_RATE_AWAY_4v5 = 78.4 
GOAL_RATE_HOME_3v5 = 180.0 
GOAL_RATE_AWAY_3v5 = 200.0
GOAL_RATE_HOME_4v3 = 7.0
GOAL_RATE_AWAY_4v3 = 8.0
GOAL_RATE_HOME_3v4 = 50.0
GOAL_RATE_AWAY_3v4 = 60.0
GOAL_RATE_HOME_3v3 = 15.0
GOAL_RATE_AWAY_3v3 = 15.0
GOAL_RATE_HOME_6v5 = 8.5
GOAL_RATE_AWAY_6v5 = 8.5
GOAL_RATE_HOME_6v4 = 6.0
GOAL_RATE_AWAY_6v4 = 5.1
OPP_GOALIE_PULL_MULTIPLIER = 0.1
PENALTY_RATE = 10.0    # minutes per penalty
PENALTY_LENGTH = 2.0  # minutes
GOALIE_PULL_TIME = 2.0
GOALIE_PULL_TIME_2 = 6.0

class StrengthStateMachine(StateMachine):
    five_v_five = State("5v5", initial=True)
    four_v_four = State("4v4")
    five_v_four = State("5v4")
    four_v_five = State("4v5")
    five_v_three = State("5v3")
    three_v_five = State("3v5")
    three_v_three = State("3v3")
    six_v_five = State("6v5")
    five_v_six = State("5v6")
    six_v_four = State("6v4")
    four_v_six = State("4v6")
    six_v_three = State("6v3")
    three_v_six = State("3v6")
    six_v_six = State("6v6")
    three_v_four = State("3v4")
    four_v_three = State("4v3")

    goalie_pull_home = five_v_five.to(six_v_five) | four_v_five.to(five_v_five) | three_v_five.to(four_v_five) | five_v_four.to(six_v_four) | four_v_four.to(five_v_four) | three_v_four.to(four_v_four) | five_v_three.to(six_v_three) | four_v_three.to(five_v_three) | three_v_three.to(four_v_three) | five_v_six.to(six_v_six) | four_v_six.to(five_v_six) | three_v_six.to(four_v_six)

    goalie_pull_away = five_v_five.to(five_v_six) | five_v_four.to(five_v_five) | five_v_three.to(five_v_four) | six_v_five.to(six_v_six) | six_v_four.to(six_v_five) | six_v_three.to(six_v_four) | four_v_five.to(four_v_six) | three_v_five.to(three_v_six) | four_v_four.to(four_v_five) | three_v_four.to(three_v_five) | three_v_three.to(three_v_four) | four_v_three.to(four_v_four)

    goalie_return_home = six_v_five.to(five_v_five) | five_v_five.to(four_v_five) | four_v_five.to(three_v_five) | six_v_four.to(five_v_four) | five_v_four.to(four_v_four) | four_v_four.to(three_v_four) | six_v_three.to(five_v_three) | five_v_three.to(four_v_three) | four_v_three.to(three_v_three) | six_v_six.to(five_v_six) | five_v_six.to(four_v_six) | four_v_six.to(three_v_six)

    goalie_return_away = five_v_six.to(five_v_five) | five_v_five.to(five_v_four) | five_v_four.to(five_v_three) | six_v_six.to(six_v_five) | six_v_five.to(six_v_four) | six_v_four.to(six_v_three) | four_v_six.to(four_v_five) | three_v_six.to(three_v_five) | four_v_five.to(four_v_four) | three_v_five.to(three_v_four) | three_v_four.to(three_v_three) | four_v_four.to(four_v_three)

    goal_scored_home = five_v_four.to(five_v_five) | five_v_three.to(five_v_four) | six_v_four.to(six_v_five) | six_v_three.to(six_v_four) | four_v_three.to(four_v_four)

    goal_scored_away = four_v_five.to(five_v_five) | three_v_five.to(four_v_five) | four_v_six.to(five_v_six) | three_v_six.to(four_v_six) | three_v_four.to(four_v_four)

    penalty_called_home = five_v_five.to(four_v_five) | four_v_four.to(three_v_four) | five_v_four.to(four_v_four) | six_v_five.to(five_v_five) | six_v_four.to(five_v_four) | five_v_three.to(four_v_three) | six_v_three.to(five_v_three) | four_v_three.to(three_v_three) |five_v_six.to(four_v_six) | four_v_six.to(three_v_six)  | three_v_three.to(three_v_four) | three_v_four.to(three_v_five)

    penalty_called_away = five_v_five.to(five_v_four) | four_v_four.to(four_v_three) | four_v_five.to(four_v_four) | five_v_six.to(five_v_five) | six_v_five.to(six_v_four) | four_v_six.to(four_v_five) | three_v_five.to(three_v_four) | three_v_four.to(three_v_three) | three_v_three.to(four_v_three) | three_v_six.to(four_v_six) | four_v_three.to(five_v_three) | six_v_four.to(six_v_three)

class Team:
    def __init__(self, name):
        self.name = name
        self.goals = 0
        self.penalties = 0
        self.goalie_pulled = False


def penalty_killer(env, team):
    """Handle penalty expiration"""
    yield env.timeout(PENALTY_LENGTH)
    team.penalties -= 1
    print(f"[{env.now:.1f}] {team.name} penalty expires (penalties: {team.penalties})")


def hockey_simulation(env, sm, home_team, away_team, game_length=60):
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
    home = Team("Red Wings")
    away = Team("Maple Leafs")
    sm = StrengthStateMachine()
    env = simpy.Environment()
    env.process(hockey_simulation(env, sm, home, away, game_length=60))
    env.run()