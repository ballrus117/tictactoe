from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

board = [''] * 9
current_player = 'X'
game_over = False

# NEW: The Bouncer - Tracks who is X and who is O using their secret connection IDs
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

# NEW: Assign roles as soon as someone opens the page
@socketio.on('connect')
def handle_connect():
    role = 'Spectator'
    
    # Give them X or O if the seat is empty
    if players['X'] is None:
        players['X'] = request.sid
        role = 'X'
    elif players['O'] is None:
        players['O'] = request.sid
        role = 'O'
    
    # Tell their browser what role they got
    emit('assign_role', {'role': role})
    # Send them the current board so they aren't looking at a blank screen
    emit('update_board', {'board': board, 'turn': current_player})

# NEW: Free up the seat if someone closes the tab
@socketio.on('disconnect')
def handle_disconnect():
    if players['X'] == request.sid:
        players['X'] = None
    elif players['O'] == request.sid:
        players['O'] = None

@socketio.on('player_clicked')
def handle_move(data):
    global board, current_player, game_over
    
    # NEW SECURITY CHECK: Is the person clicking actually the current player?
    # If a spectator clicks, or if O clicks during X's turn, the server completely ignores it.
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

if __name__ == '__main__':
    socketio.run(app, debug=True)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
