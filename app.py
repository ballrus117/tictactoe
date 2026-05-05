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

players = {'X': None, 'O': None}
wallpapers = ['bg1.jpg', 'bg2.jpg', 'bg3.jpg'] 
shared_wallpaper = random.choice(wallpapers)

def check_winner():
    win_lines = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]]
    for line in win_lines:
        a, b, c = line
        if board[a] != '' and board[a] == board[b] == board[c]:
            return board[a] 
    if '' not in board:
        return 'Tie'
    return None

def broadcast_custom_turns():
    global current_player
    # Use socketio.emit to ensure 'to=' works perfectly
    for role, sid in players.items():
        if sid:
            msg = "Your turn b0ss" if role == current_player else f"waiting for {current_player}"
            socketio.emit('update_board', {'board': board, 'turn_msg': msg}, to=sid)
    
    # Update anyone else (Spectators)
    socketio.emit('update_board', {'board': board, 'turn_msg': f"waiting for {current_player}"}, broadcast=True, include_self=False)

@app.route('/')
def home():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    global shared_wallpaper
    role = 'Spectator'
    if players['X'] is None:
        players['X'] = request.sid
        role = 'X'
    elif players['O'] is None:
        players['O'] = request.sid
        role = 'O'
    
    emit('assign_role', {'role': role, 'wallpaper': shared_wallpaper})
    broadcast_custom_turns()

@socketio.on('disconnect')
def handle_disconnect():
    if players['X'] == request.sid:
        players['X'] = None
    elif players['O'] == request.sid:
        players['O'] = None

@socketio.on('player_clicked')
def handle_move(data):
    global board, current_player, game_over
    if players[current_player] != request.sid or game_over:
        return 

    square_index = data['index']
    if board[square_index] == '':
        board[square_index] = current_player
        winner = check_winner()
        
        if winner:
            game_over = True
            # Update board one last time so the winning move appears
            socketio.emit('update_board', {'board': board, 'turn_msg': "Game Over!"}, broadcast=True)
            
            if winner == 'Tie':
                socketio.emit('announce_winner', {'msg': "wow both of you suck it is a tie."}, broadcast=True)
            else:
                # Targeted Winner Message
                socketio.emit('announce_winner', {'msg': "wow congratulations you won."}, to=players[winner])
                
                # Targeted Loser Message
                loser_role = 'O' if winner == 'X' else 'X'
                if players[loser_role]:
                    socketio.emit('announce_winner', {'msg': "wow you suck you lost."}, to=players[loser_role])
                
                # Spectator Message
                socketio.emit('announce_winner', {'msg': f"Player {winner} Won!"}, broadcast=True, include_self=False)
        else:
            current_player = 'O' if current_player == 'X' else 'X'
            broadcast_custom_turns()

@socketio.on('reset_game')
def reset():
    global board, current_player, game_over, shared_wallpaper
    board = [''] * 9
    current_player = 'X'
    game_over = False
    shared_wallpaper = random.choice(wallpapers)
    socketio.emit('new_round', {'wallpaper': shared_wallpaper}, broadcast=True)
    broadcast_custom_turns()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
