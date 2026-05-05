from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os
import random
from threading import Lock

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60)

board = [''] * 9
current_player = 'X'
game_over = False

players = {'X': None, 'O': None}

wallpapers = ['bg1.jpg', 'bg2.jpg', 'bg3.jpg', 'bg4.jpg', 'bg5.jpg', 'bg6.jpg']
qotsa_wallpaper = 'qotsa.jpg'

def choose_wallpaper():
    # 10% chance for qotsa.jpg, equal chance for the rest
    if random.random() < 0.1:
        return qotsa_wallpaper
    else:
        return random.choice(wallpapers)

shared_wallpaper = choose_wallpaper()

lock = Lock()

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

def broadcast_custom_turns():
    global current_player

    # Send to players
    for role, sid in players.items():
        if sid:
            if role == current_player:
                msg = "Your turn b0ss"
            else:
                msg = f"waiting for {current_player}"
            socketio.emit('update_board', {'board': board, 'turn_msg': msg}, to=sid)

    # Send ONLY to spectators
    all_clients = list(socketio.server.manager.get_participants('/', None))
    for sid in all_clients:
        if sid not in players.values():
            socketio.emit(
                'update_board',
                {'board': board, 'turn_msg': f"waiting for {current_player}"},
                to=sid
            )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/test-static')
def test_static():
    import os
    static_files = os.listdir(app.static_folder)
    return f"Static files found: {static_files}"

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
def handle_disconnect(reason=None):
    global game_over

    if players['X'] == request.sid:
        players['X'] = None
        game_over = True
    elif players['O'] == request.sid:
        players['O'] = None
        game_over = True

    socketio.emit('announce_winner', {'msg': "Opponent disconnected."})

@socketio.on('player_clicked')
def handle_move(data):
    global board, current_player, game_over

    with lock:
        if players.get(current_player) != request.sid or game_over:
            return

        square_index = data.get('index')

        # ✅ Safe index check
        if not isinstance(square_index, int) or square_index < 0 or square_index > 8:
            return

        if board[square_index] == '':
            board[square_index] = current_player
            winner = check_winner()

            if winner:
                game_over = True
                socketio.emit('update_board', {'board': board, 'turn_msg': "Game Over!"})

                if winner == 'Tie':
                    socketio.emit('announce_winner', {'msg': "wow both of you suck it is a tie."})
                else:
                    winner_sid = players[winner]
                    socketio.emit('announce_winner', {'msg': "wow congratulations you won."}, to=winner_sid)

                    loser_role = 'O' if winner == 'X' else 'X'
                    loser_sid = players.get(loser_role)
                    if loser_sid:
                        socketio.emit('announce_winner', {'msg': "wow you suck you lost."}, to=loser_sid)

                    socketio.emit('announce_winner', {'msg': f"Player {winner} won"}, include_self=False)
            else:
                current_player = 'O' if current_player == 'X' else 'X'
                broadcast_custom_turns()

@socketio.on('reset_game')
def reset():
    global board, current_player, game_over, shared_wallpaper

    board = [''] * 9
    current_player = 'X'
    game_over = False

    shared_wallpaper = choose_wallpaper()
    print(f"New Wallpaper Selected: {shared_wallpaper}")

    socketio.emit('new_round', {'wallpaper': shared_wallpaper})
    broadcast_custom_turns()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9999))
    print(f"Starting Tic-Tac-Toe server on port {port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
