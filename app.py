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
wallpapers = ['bg1.jpg', 'bg2.jpg', 'bg3.jpg', 'bg4.jpg', 'bg5.jpg', 'bg6.jpg', 'qotsa.jpg'] 
shared_wallpaper = random.choice(wallpapers)

def check_winner():
    win_lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], # Horizontal
        [0, 3, 6], [1, 4, 7], [2, 5, 8], # Vertical
        [0, 4, 8], [2, 4, 6]              # Diagonal
    ]
    for line in win_lines:
        a, b, c = line
        if board[a] != '' and board[a] == board[b] == board[c]:
            return board[a] 
    if '' not in board:
        return 'Tie'
    return None

def broadcast_custom_turns():
    """Sends personalized turn messages. Precision targeting using socketio.emit with 'to'."""
    global current_player
    for role, sid in players.items():
        if sid:
            # Personalize the message based on who is looking at the screen
            if role == current_player:
                msg = "Your turn b0ss"
            else:
                msg = f"waiting for {current_player}"
            
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
    
    # Send the role and the currently active wallpaper to the newcomer
    emit('assign_role', {'role': role, 'wallpaper': shared_wallpaper})
    
    # Small pause to allow the socket connection to stabilize before sending turn data
    socketio.sleep(0.2)
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
    
    # Validation: Only the current active player can move
    if players.get(current_player) != request.sid or game_over:
        return 

    square_index = data['index']
    if board[square_index] == '':
        board[square_index] = current_player
        winner = check_winner()
        
        if winner:
            game_over = True
            # Update board one last time so the winning move is rendered
            socketio.emit('update_board', {'board': board, 'turn_msg': "Game Over!"}, broadcast=True)
            
            if winner == 'Tie':
                socketio.emit('announce_winner', {'msg': "wow both of you suck it is a tie."}, broadcast=True)
            else:
                # 1. Target the winner specifically
                winner_sid = players[winner]
                socketio.emit('announce_winner', {'msg': "wow congratulations you won."}, to=winner_sid)
                
                # 2. Target the loser specifically
                loser_role = 'O' if winner == 'X' else 'X'
                if players[loser_role]:
                    socketio.emit('announce_winner', {'msg': "wow you suck you lost."}, to=players[loser_role])
                
                # 3. Inform spectators
                socketio.emit('announce_winner', {'msg': f"Player {winner} won"}, broadcast=True, include_self=False)
        else:
            # No winner yet, swap turns and update everyone
            current_player = 'O' if current_player == 'X' else 'X'
            broadcast_custom_turns()

@socketio.on('reset_game')
def reset():
    global board, current_player, game_over, shared_wallpaper
    board = [''] * 9
    current_player = 'X'
    game_over = False
    
    # Shuffle the wallpaper for the new round
    shared_wallpaper = random.choice(wallpapers)
    
    # Notify everyone to change their wallpaper and clear the board
    socketio.emit('new_round', {'wallpaper': shared_wallpaper}, broadcast=True)
    broadcast_custom_turns()

if __name__ == '__main__':
    # Using Render's environment variable for Port
    port = int(os.environ.get('PORT', 10000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
  
