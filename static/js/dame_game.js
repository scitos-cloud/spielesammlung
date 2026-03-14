let boardState = null;
let validMoves = {};
let selectedPiece = null;
let lastMove = null;
let moveLog = [];
let captured = {w: [], b: []};
let pollTimer = null;
let gameFinished = false;

function init() {
    fetchState();
}

function fetchState() {
    fetch(`${GAME_BASE}/game/${GAME_ID}/state`)
        .then(r => r.json())
        .then(data => {
            if (data.move_log) {
                moveLog = data.move_log;
                renderMoveLog();
            }
            if (data.last_move) {
                lastMove = data.last_move;
            }
            if (data.captured) {
                captured = data.captured;
                renderCaptured();
            }
            if (data.finished) {
                gameFinished = true;
                showResult(data.winner);
                if (data.board) {
                    boardState = data.board;
                    renderBoard();
                }
                stopPolling();
                return;
            }
            boardState = data.board;
            validMoves = data.valid_moves || {};
            renderBoard();
            updateStatus(data.turn);
            if (!IS_AI && data.turn !== MY_COLOR && !gameFinished) {
                startPolling();
            } else {
                stopPolling();
            }
        });
}

function renderBoard() {
    const board = document.getElementById('board');
    board.innerHTML = '';
    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            const cell = document.createElement('div');
            cell.className = 'cell ' + ((r + c) % 2 === 0 ? 'light' : 'dark');
            cell.dataset.row = r;
            cell.dataset.col = c;

            // Highlight last move
            if (lastMove) {
                const isFrom = lastMove.from[0] === r && lastMove.from[1] === c;
                const isTo = lastMove.to[0] === r && lastMove.to[1] === c;
                if (isFrom || isTo) {
                    const aiMove = lastMove.player !== MY_COLOR;
                    cell.classList.add(aiMove ? 'last-move-ai' : 'last-move-own');
                }
            }

            const piece = boardState[r][c];
            if (piece) {
                const pieceEl = document.createElement('div');
                const color = piece.toLowerCase() === 'w' ? 'white' : 'black';
                const isKing = piece === piece.toUpperCase();
                pieceEl.className = `piece ${color}${isKing ? ' king' : ''}`;
                if (validMoves[`${r},${c}`] && !gameFinished) {
                    pieceEl.classList.add('clickable');
                }
                cell.appendChild(pieceEl);
            }

            if (selectedPiece && selectedPiece[0] === r && selectedPiece[1] === c) {
                cell.classList.add('selected');
            }

            if (selectedPiece) {
                const key = `${selectedPiece[0]},${selectedPiece[1]}`;
                const moves = validMoves[key] || [];
                for (const path of moves) {
                    const dest = path[path.length - 1];
                    if (dest[0] === r && dest[1] === c) {
                        cell.classList.add('highlight');
                        break;
                    }
                }
            }

            cell.addEventListener('click', () => onCellClick(r, c));
            board.appendChild(cell);
        }
    }
}

function renderMoveLog() {
    const logEl = document.getElementById('move-log');
    let html = '';
    for (const entry of moveLog) {
        const isAI = entry.player === 'b' && IS_AI;
        const playerLabel = isAI ? 'KI' : (entry.player === 'w' ? 'Weiss' : 'Schwarz');
        const cls = isAI ? 'log-entry ai' : 'log-entry';
        html += `<div class="${cls}">`;
        html += `<span class="log-nr">${entry.nr}.</span>`;
        html += `<span class="log-player">${playerLabel}</span>`;
        html += `<span class="log-notation">${entry.notation}</span>`;
        if (isAI) html += `<span class="log-ai-badge">KI</span>`;
        html += `</div>`;
    }
    logEl.innerHTML = html;
    logEl.scrollTop = logEl.scrollHeight;
}

function renderCaptured() {
    for (const color of ['w', 'b']) {
        const el = document.getElementById('captured-' + color);
        el.innerHTML = '';
        for (const p of captured[color]) {
            const piece = document.createElement('div');
            const pieceColor = p.toLowerCase() === 'w' ? 'white' : 'black';
            const isKing = p === p.toUpperCase();
            piece.className = `captured-piece ${pieceColor}${isKing ? ' king' : ''}`;
            el.appendChild(piece);
        }
    }
}

function onCellClick(r, c) {
    if (gameFinished) return;
    const piece = boardState[r][c];

    if (selectedPiece) {
        const key = `${selectedPiece[0]},${selectedPiece[1]}`;
        const moves = validMoves[key] || [];
        for (const path of moves) {
            const dest = path[path.length - 1];
            if (dest[0] === r && dest[1] === c) {
                makeMove(selectedPiece[0], selectedPiece[1], path);
                selectedPiece = null;
                return;
            }
        }
    }

    if (piece && validMoves[`${r},${c}`]) {
        selectedPiece = [r, c];
        renderBoard();
    } else {
        selectedPiece = null;
        renderBoard();
    }
}

function makeMove(fromRow, fromCol, path) {
    fetch(`${GAME_BASE}/game/${GAME_ID}/move`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({from_row: fromRow, from_col: fromCol, path: path})
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }
        selectedPiece = null;
        if (data.last_move) lastMove = data.last_move;
        if (data.move_log) { moveLog = data.move_log; renderMoveLog(); }
        if (data.captured) { captured = data.captured; renderCaptured(); }
        if (data.finished) {
            gameFinished = true;
            boardState = data.board;
            validMoves = {};
            renderBoard();
            showResult(data.winner);
            stopPolling();
        } else {
            fetchState();
        }
    });
}

function resign() {
    if (!confirm('Wirklich aufgeben?')) return;
    fetch(`${GAME_BASE}/game/${GAME_ID}/resign`, {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            gameFinished = true;
            showResult(data.winner);
            stopPolling();
            fetchState();
        });
}

function updateStatus(turn) {
    const status = document.getElementById('status');
    if (turn === MY_COLOR) {
        status.textContent = 'Du bist am Zug!';
        status.style.color = '#4caf50';
    } else {
        status.textContent = IS_AI ? 'KI denkt...' : 'Gegner ist am Zug...';
        status.style.color = '#7fc8f8';
    }
}

function showResult(winner) {
    const status = document.getElementById('status');
    const resignBtn = document.getElementById('resign-btn');
    resignBtn.style.display = 'none';
    if (winner === MY_COLOR) {
        status.textContent = 'Du hast gewonnen!';
        status.style.color = '#4caf50';
    } else {
        status.textContent = 'Du hast verloren!';
        status.style.color = '#e94560';
    }
}

function startPolling() {
    if (pollTimer) return;
    pollTimer = setInterval(fetchState, 2000);
}

function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

init();
