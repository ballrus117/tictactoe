from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

board = [''] * 9
current_player = 'X'
game_over = False

# The Bouncer - Tracks who is X and who is O
players = {'X': None, 'O': None}

# Keep track of a single shared wallpaper for the session
# Add your wallpaper filenames to this list
wallpapers = ['bg1.jpg', 'bg2.jpg', 'bg3.jpg'] 
shared_wallpaper = random.choice(wallpapers)

def check_winner():
    win_lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  
        [0, 4, 8], [2, 4, 6]              
    ]
    for line in win_lines:
        a, b, c = line
        if board[a] != '' and board[a] == board[b] == board[c]:
            return board[a] 
    
    if '' not in board:
        return 'Tie'
    return None

@app.route('/')
def home():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    role = 'Spectator'
    if players['X'] is None:
        players['X'] = request.sid
        role = 'X'
    elif players['O'] is None:
        players['O'] = request.sid
        role = 'O'
    
    # Send the shared wallpaper along with the role
    emit('assign_role', {'role': role, 'wallpaper': shared_wallpaper})
    emit('update_board', {'board': board, 'turn': current_player})

@socketio.on('disconnect')
def handle_disconnect():
    if players['X'] == request.sid:
        players['X'] = None
    elif players['O'] == request.sid:
        players['O'] = None

@socketio.on('player_clicked')
def handle_move(data):
    global board, current_player, game_over
    
    if players[current_player] != request.sid:
        return 

    square_index = data['index']
    
    if not game_over and board[square_index] == '':
        board[square_index] = current_player
        winner = check_winner()
        
        if winner:
            game_over = True 
            emit('update_board', {'board': board, 'turn': current_player}, broadcast=True)
            
            # Send personalized messages to each player
            if winner == 'Tie':
                emit('announce_winner', {'winner': 'Tie', 'msg': "It's a Tie!"}, broadcast=True)
            else:
                # Tell the winner they won
                winner_sid = players[winner]
                emit('announce_winner', {'winner': winner, 'msg': "You Won!"}, to=winner_sid)
                
                # Tell the loser they lost
                loser_role = 'O' if winner == 'X' else 'X'
                loser_sid = players[loser_role]
                if loser_sid:
                    emit('announce_winner', {'winner': winner, 'msg': "You Lost!"}, to=loser_sid)
                
                # Tell spectators who won
                emit('announce_winner', {'winner': winner, 'msg': f"Player {winner} Won!"}, broadcast=True, include_self=False)
        else:
            current_player = 'O' if current_player == 'X' else 'X'
            emit('update_board', {'board': board, 'turn': current_player}, broadcast=True)

@socketio.on('reset_game')
def reset():
    global board, current_player, game_over, shared_wallpaper
    board = [''] * 9
    current_player = 'X'
    game_over = False
    # Pick a new shared wallpaper for the next round
    shared_wallpaper = random.choice(wallpapers)
    emit('update_board', {'board': board, 'turn': current_player}, broadcast=True)
    emit('new_round', {'wallpaper': shared_wallpaper}, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
