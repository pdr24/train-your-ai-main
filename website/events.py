import functools
from flask import flash, render_template
from flask_login import current_user
from flask_socketio import disconnect
from .extensions import socketio

def authenticated_only(f):
    @functools.wraps(f) # preserves the wrapped function's metadata
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect(current_user) # disconnects from the web socket if the user is not authenticated
        else:
            return f(*args, **kwargs) # calls original function if the user is authenticated
    return wrapped # returns wrapped function that can be used in place of the original function f

@socketio.on("connect")
@authenticated_only # so only authenticated users can connect
def handle_connect(): 
    print(f"{current_user.first_name} connected") # prints to console saying the user has connected 

@socketio.on("user_join")
def handle_user_join(username):
    print(f"user {username} joined") # prints to console to indicate user has joined

@socketio.on("train") # registers handle_train as event handler for train event --> triggers the AI training 
@authenticated_only # only authenticated users can trigger this 
def handle_train(food, alive, die):
    if(food != "" and alive != "" and die != ""): # checks if arguments for rewards values are valid
        from .agent import start
        start(food, alive, die) # calls the start function to start the training process
    else:
        print("error") # error if any of the reward value arguments were empty(venv)