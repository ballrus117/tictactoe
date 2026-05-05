from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
# The secret_key helps secure the session
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

board = [''] * 9
current_player = 'X'
game_over = False

# The Bouncer - Tracks who is X and who is O
players = {'X': None, 'O': None}

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
    
    emit('assign_role', {'role': role})
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
            emit('announce_winner', {'winner': winner}, broadcast=True)
        else:
            current_player = 'O' if current_player == 'X' else 'X'
            emit('update_board', {'board': board, 'turn': current_player}, broadcast=True)

@socketio.on('reset_game')
def reset():
    global board, current_player, game_over
    board = [''] * 9
    current_player = 'X'
    game_over = False
    emit('update_board', {'board': board, 'turn': current_player}, broadcast=True)

# FINAL RENDER CONFIGURATION
if __name__ == '__main__':
    # Grabs the PORT from Render (10000) or defaults to 5000 for local testing
    port = int(os.environ.get('PORT', 10000))
    # host='0.0.0.0' is required for the public internet to see the app
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
