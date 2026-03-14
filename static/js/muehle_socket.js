// SocketIO client for multiplayer Muehle games (namespace /muehle)
const socket = io('/muehle');

socket.on('connect', () => {
    socket.emit('join_game', {game_id: GAME_ID});
});

socket.on('state_update', (state) => {
    updateBoard(state);
});

socket.on('error', (data) => {
    console.error('Server error:', data.message);
});

function sendActionSocket(action) {
    socket.emit('player_action', {
        game_id: GAME_ID,
        action: action.action,
        from_pos: action.from_pos !== undefined ? action.from_pos : null,
        to_pos: action.to_pos !== undefined ? action.to_pos : null,
    });
}
