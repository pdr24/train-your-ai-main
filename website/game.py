import pygame
import random
import numpy as np
import sys
from enum import Enum
from collections import namedtuple
from .events import socketio
from flask_socketio import emit
from flask_login import current_user
from flask import request
import time

pygame.init() # initialize all imported pygame modules

class Direction(Enum):
    RIGHT = 1
    LEFT = 2
    UP = 3
    DOWN = 4

Point = namedtuple('Point', 'x, y')

# rgb colors
WHITE = (255, 255, 255)
RED = (200,0,0)
BLUE1 = (0, 0, 255)
BLUE2 = (0, 100, 255)
BLACK = (0,0,0)

BLOCK_SIZE = 20 # block size of each block in the grid 
SPEED = 1000 # speed of the game (frame rate)
GAMES = 0 # variable to track the number of games played 

#publisher of training data
def send_data(data): # emits the game data to the client via SocketIO
    socketio.emit("snake_data", {"data": data}, to=request.sid, callback=acknowledgment)

def acknowledgment(running):
    if (not running):
        global GAMES
        GAMES = 1000
        time.sleep(0.3)
        GAMES = 0

# main game class for the AI to interact with 
class SnakeGameAI:

    def __init__(self, eat_apple, stay_alive, die, w=640, h=480):
        self.w = w # width of game window
        self.h = h # height of game window
        self.eat_apple = eat_apple # sets the reward for eating an apple
        self.stay_alive = stay_alive # sets the reward for staying alive
        self.die = die # sets the reward for dying
        self.clock = pygame.time.Clock() # initializes pygame clock to control the game's frame rate
        self.reset() # calls reset to initalize the game state 

    def reset(self):
        # init game state
        self.direction = Direction.RIGHT # sets initial direction of the snake to right

        self.head = Point(self.w/2, self.h/2) # positions snake's head at the center of the window
        self.snake = [self.head,
                      Point(self.head.x-BLOCK_SIZE, self.head.y),
                      Point(self.head.x-(2*BLOCK_SIZE), self.head.y)] # initializes snake's body with 3 segments

        self.score = 0 # sets score to 0
        self.food = None # initializes food position to none 
        self._place_food() # places food at random position
        self.frame_iteration = 0 # resets frame iteration counter to 0 

    def _place_food(self):
        x = random.randint(0, (self.w-BLOCK_SIZE )//BLOCK_SIZE )*BLOCK_SIZE # random x coordinate for the food
        y = random.randint(0, (self.h-BLOCK_SIZE )//BLOCK_SIZE )*BLOCK_SIZE # random y coordinate for the food
        self.food = Point(x, y) # places food at the generated x and y coordinates
        if self.food in self.snake: # if the food overlaps with the snake, recursively calls this function again to generate new position
            self._place_food()

    # executes one step of the game
    def play_step(self, action, games, total_score, record, score):
        global GAMES
        if (GAMES == 1000): # updates GAMES and games variables 
            games = 1000
            GAMES = 0

        self.frame_iteration += 1 # increments frame iteration counter
        
        # 1. collect user input
        for event in pygame.event.get(): # iterates over all pygame events
            if event.type == pygame.QUIT: # exits game is quit is detected
                pygame.quit()
                quit()
        
        # 2. move
        self._move(action) # update the head position of the snake
        self.snake.insert(0, self.head) # inserts new head position into beginning of the snake list
        
        # 3. check if game over
        reward = self.stay_alive # sets reward to stay alive value                       
        game_over = False # sets game over flag to false
        if self.is_collision() or self.frame_iteration > 60*len(self.snake): # if snake has collided with something or frame iteration limit is exceeded
            game_over = True # set game over flag to true
            reward = self.die # sets reward to die value                   
            return reward, game_over, self.score, games # returns reward, gameover status, score, and games played

        # 4. place new food or just move
        if self.head == self.food: # if snake eats food
            self.score += 1 # increments score 
            reward = self.eat_apple # sets reward to reward value for eating apple                       # REWARD FUNCTION IF EATS FOOD
            self._place_food() # places new food
        else:
            self.snake.pop() # removes last segment of snake to move it forward
        
        # 5. update ui and clock
        self._update_ui(games, total_score, record, score) # updates the ui
        self.clock.tick(SPEED) # controls game speed by limiting the frame rate (?)
        
        # 6. return game over and score
        return reward, game_over, self.score, games

    def is_collision(self, pt=None):
        if pt is None: # if not pt is provided set pt to head
            pt = self.head
        # hits boundary
        if pt.x > self.w - BLOCK_SIZE or pt.x < 0 or pt.y > self.h - BLOCK_SIZE or pt.y < 0: # checks if point is outside the game boundaries
            return True
        # hits itself
        if pt in self.snake[1:]: # checks if snake head hits its body (excluding the head)
            return True

        return False

    ####################################################
    def get_state(self):
        head = self.snake[0]
        point_l = Point(head.x - BLOCK_SIZE, head.y)
        point_r = Point(head.x + BLOCK_SIZE, head.y)
        point_u = Point(head.x, head.y - BLOCK_SIZE)
        point_d = Point(head.x, head.y + BLOCK_SIZE)

        dir_l = self.direction == Direction.LEFT
        dir_r = self.direction == Direction.RIGHT
        dir_u = self.direction == Direction.UP
        dir_d = self.direction == Direction.DOWN

        state = [
            # Danger straight
            (dir_r and self.is_collision(point_r)) or 
            (dir_l and self.is_collision(point_l)) or 
            (dir_u and self.is_collision(point_u)) or 
            (dir_d and self.is_collision(point_d)),

            # Danger right
            (dir_u and self.is_collision(point_r)) or 
            (dir_d and self.is_collision(point_l)) or 
            (dir_l and self.is_collision(point_u)) or 
            (dir_r and self.is_collision(point_d)),

            # Danger left
            (dir_d and self.is_collision(point_r)) or 
            (dir_u and self.is_collision(point_l)) or 
            (dir_r and self.is_collision(point_u)) or 
            (dir_l and self.is_collision(point_d)),
            
            # Move direction
            dir_l,
            dir_r,
            dir_u,
            dir_d,
            
            # Food location 
            self.food.x < self.head.x,  # food left
            self.food.x > self.head.x,  # food right
            self.food.y < self.head.y,  # food up
            self.food.y > self.head.y  # food down
        ]

        return np.array(state, dtype=int)
    ####################################################

    def _update_ui(self, games, total_score, record, score):

        data = {} # initializes empty dictionary to hold game data
        data['snake'] = [] # initializes empty list to hold snake's position
        data['stats'] = {'games': games, 'record': record, 'score': score} # add game stats to the data dictionary

        i = 0
        for pt in self.snake: # iterates over snake's segments
            data['snake'].append({'x': pt.x, 'y': pt.y}) # adds segment's positions to the snake list in the data dictionary
            if ((data['snake'][i]['x'] != pt.x) or (data['snake'][i]['y'] != pt.y)): # checks for data consistency 
                print(f"DATA INCONSISTENT")
                print(f"SNAKE: x: {pt.x}, y: {pt.y}")
                print(f"JSON DATA: x: {data['snake'][i]['x']}, y: {data['snake'][i]['x']}")

            i = i + 1

        data['apple'] = {'x': self.food.x, 'y': self.food.y} # adds food's position to the data dictionary 
        if((data['apple']['x'] != self.food.x) or (data['apple']['y'] != self.food.y)): # checks for data consistency
            print(f"DATA INCONSISTENT")
            print(f"APPLE: x: {self.food.x}, y: {self.food.y}")
            print(f"JSON DATA: x: {data['apple']['x']}, y: {data['apple']['y']}")
           
        data['state'] = self.get_state().tolist()
        print(data['state']) # print state data to terminal for testing purposes

        send_data(data) # sends the data to the client 

    def _move(self, action):
        # [straight, right, left]

        clock_wise = [Direction.RIGHT, Direction.DOWN, Direction.LEFT, Direction.UP] # defines order of the directions to be clockwise
        idx = clock_wise.index(self.direction) # finds index of current direction

        if np.array_equal(action, [1, 0, 0]): # if the action is go straight, keep the current direction
            new_dir = clock_wise[idx] # no change in the direction
        elif np.array_equal(action, [0, 1, 0]): # if action is turn right, set direction to next direction clockwise
            next_idx = (idx + 1) % 4
            new_dir = clock_wise[next_idx] # right turn r -> d -> l -> u
        else: # [0, 0, 1] if left turn, set direction to previous direction clockwise
            next_idx = (idx - 1) % 4
            new_dir = clock_wise[next_idx] # left turn r -> u -> l -> d

        self.direction = new_dir # sets new direction

        x = self.head.x # gets x coordinate of current head position
        y = self.head.y # gets y coordinate of current head position

        # update head position depending on the current movement direction
        if self.direction == Direction.RIGHT:
            x += BLOCK_SIZE
        elif self.direction == Direction.LEFT:
            x -= BLOCK_SIZE
        elif self.direction == Direction.DOWN:
            y += BLOCK_SIZE
        elif self.direction == Direction.UP:
            y -= BLOCK_SIZE

        self.head = Point(x, y) # updates the head position