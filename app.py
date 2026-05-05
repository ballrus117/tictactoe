from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# ping_timeout helps prevent mobile players from dropping during slow network shifts
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60)

board = [''] * 9
current_player = 'X'
game_over = False

# Role management
players = {'X': None, 'O': None}

# Ensure these filenames match your /static folder EXACTLY (case-sensitive)
wallpapers = ['bg1.jpg', 'bg2.jpg', 'bg3.jpg', 'bg4.jpg', 'bg5.
