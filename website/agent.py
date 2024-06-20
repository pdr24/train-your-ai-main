import torch
import random
import numpy as np
import sys
from collections import deque
from flask_login import current_user
from .game import SnakeGameAI, Direction, Point, BLOCK_SIZE
from .model import Linear_QNet, QTrainer
from .dbmodels import AI
from . import db
import time
from .events import socketio
from flask_socketio import emit
from flask_login import current_user
from flask import request

MAX_MEMORY = 100_000 # size of replay buffer
BATCH_SIZE = 1000 # batch size of subset used for training the model
LR = 0.001 # learning rate used for the neural network

class Agent: # represents the RL agent

    # called when a new agent object is created
    def __init__(self):
        self.n_games = 0 # tracks the number of games played by the agent (starts at 0)
        self.epsilon = 0 # controls the exploration rate (randomness) of the agent
        self.gamma = 0.9 # discount rate for future rewards
        self.memory = deque(maxlen=MAX_MEMORY) # popleft() (deque object to store past experiences)
        self.model = Linear_QNet(11, 256, 3) # model is initialized here. model is from model.py
        self.trainer = QTrainer(self.model, lr=LR, gamma=self.gamma) # creates object to handle training of the neural network using the Q-learning algorithm

    # gets the current state of the game and encodes it numerically for the neural network 
    def get_state(self, game):
        head = game.snake[0] # gets the position of the snake's head
        point_l = Point(head.x - BLOCK_SIZE, head.y) # point to left of the head
        point_r = Point(head.x + BLOCK_SIZE, head.y) # point to right of the head
        point_u = Point(head.x, head.y - BLOCK_SIZE) # point above the head
        point_d = Point(head.x, head.y + BLOCK_SIZE) # point below the head
        
        dir_l = game.direction == Direction.LEFT # checks if snake is going left
        dir_r = game.direction == Direction.RIGHT # checks if snake is going right 
        dir_u = game.direction == Direction.UP # checks if snake is going up 
        dir_d = game.direction == Direction.DOWN # checks if snake is going down

        # makes array representing the state of the game
        state = [
            # Danger straight
            (dir_r and game.is_collision(point_r)) or 
            (dir_l and game.is_collision(point_l)) or 
            (dir_u and game.is_collision(point_u)) or 
            (dir_d and game.is_collision(point_d)),

            # Danger right
            (dir_u and game.is_collision(point_r)) or 
            (dir_d and game.is_collision(point_l)) or 
            (dir_l and game.is_collision(point_u)) or 
            (dir_r and game.is_collision(point_d)),

            # Danger left
            (dir_d and game.is_collision(point_r)) or 
            (dir_u and game.is_collision(point_l)) or 
            (dir_r and game.is_collision(point_u)) or 
            (dir_l and game.is_collision(point_d)),
            
            # Move direction
            dir_l,
            dir_r,
            dir_u,
            dir_d,
            
            # Food location 
            game.food.x < game.head.x,  # food left
            game.food.x > game.head.x,  # food right
            game.food.y < game.head.y,  # food up
            game.food.y > game.head.y  # food down
            ]
        
        # returns the array representing the state of the game 
        return np.array(state, dtype=int)

    # stores the experience in the replay buffer 
    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done)) # popleft if MAX_MEMORY is reached

    def train_long_memory(self):
        # gets the batch of experiences or a random subset of it
        if len(self.memory) > BATCH_SIZE:
            mini_sample = random.sample(self.memory, BATCH_SIZE) # list of tuples
        else:
            mini_sample = self.memory
        
        # gets the states, actions, rewards, next states, and done flags from the sampled experience
        states, actions, rewards, next_states, dones = zip(*mini_sample)
        # trains the model
        self.trainer.train_step(states, actions, rewards, next_states, dones)

    def train_short_memory(self, state, action, reward, next_state, done):
        # trains the model on a single experience
        self.trainer.train_step(state, action, reward, next_state, done)

    def get_action(self, state):
        # random moves: tradeoff exploration / exploitation
        self.epsilon = 80 - self.n_games # adjusts the exploration rate based on the number of games that have been played
        
        # decides the next move
        final_move = [0,0,0]
        if random.randint(0, 200) < self.epsilon: # defining logic for exploration (random move)
            move = random.randint(0, 2)
            final_move[move] = 1
        else:  # defining logic for exploitation (move based on prediction from the model)
            state0 = torch.tensor(state, dtype=torch.float)
            prediction = self.model(state0)
            move = torch.argmax(prediction).item()
            final_move[move] = 1
        
        return final_move # returns the move

def train(eat_apple, stay_alive, die):

    start_time = time.time() # records the start time so it can be used to calculate the duration of training
    plot_scores = [] 
    plot_mean_scores = []
    total_score = 0
    record = 0
    score = 0
    agent = Agent() # initializing the agent
    game = SnakeGameAI(eat_apple, stay_alive, die) # initializing the game

    while agent.n_games <= 100: # continues until the agent plays 100 games
        # get current state
        state_old = agent.get_state(game)

        # determines the next move
        final_move = agent.get_action(state_old)

        # perform the move and get new state
        reward, done, score, games = game.play_step(final_move, agent.n_games, total_score, record, score)
        state_new = agent.get_state(game)
        agent.n_games = games # update the number of games played by the model

        # train short memory (trains the neural network using the most recent experience)
        agent.train_short_memory(state_old, final_move, reward, state_new, done)

        # add recent experience to the replay buffer
        agent.remember(state_old, final_move, reward, state_new, done)

        if done: # if the snake died
            # train long memory, plot result
            game.reset()
            agent.n_games += 1
            agent.train_long_memory() # train the model on a random batch of experiences (trains the models so it learns before the next game)

            if score > record: # update the model's record (max score reached) if needed
                record = score
                agent.model.save()

            total_score += score # update total score

            # output current game number, score, and record to the console
            print('Game', agent.n_games, 'Score', score, 'Record:', record)

    mean_score = total_score / agent.n_games # computes avg score
    return agent.n_games, record, mean_score # return number of games played, record, and avg score

# creates new AI entry with training results and commits it to the database 
def log_to_db(high_score, avg_score, eat, alive, die, user_id):
    ai = AI(high_score=int(high_score), avg_score=int(avg_score), eat=int(eat), alive=int(alive), die=int(die), user_id=user_id)
    db.session.add(ai)
    db.session.commit()

# def send_high_scores():
#     data = {}
#     data["ais"] = []
#     for ai in current_user.ais:
#         data["ais"].append({"highscore": ai.high_score, "eat": ai.eat, "alive": ai.alive, "die": ai.die})
#     socketio.emit("highscore_data", {"data": data}, to=request.sid)
#     print(data)

def start(eat, alive, die):
    # calls the train function with rewards values for eat, alive, and die 
    num_games, high_score, avg_score = train(int(eat), int(alive), int(die))
    # calls log_to_db() to store training results to the database 
    log_to_db(high_score, avg_score, eat, alive, die, current_user.id)

if __name__ == '__main__':
    start()
