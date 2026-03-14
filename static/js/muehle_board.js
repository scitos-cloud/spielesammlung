// Board state
let boardState = [];
let currentPlayer = 1;
let stonesPlacedWhite = 0;
let stonesPlacedBlack = 0;
let pendingRemoval = false;
let gameStatus = 'active';
let winner = null;
let selectedPos = null;
let legalActions = [];
let waitingForAI = false;
let lastAction = null;

// Position elements
const circles = document.querySelectorAll('.pos-circle');
const svg = document.getElementById('board-svg');
const statusText = document.getElementById('status-text');
const phaseText = document.getElementById('phase-text');
const stonesInfo = document.getElementById('stones-info');
const stoneCounter = document.getElementById('stone-counter');

const POS_COORDS = {
    0:[50,50],    1:[300,50],   2:[550,50],
    3:[150,150],  4:[300,150],  5:[450,150],
    6:[250,250],  7:[300,250],  8:[350,250],
    9:[50,300],   10:[150,300], 11:[250,300],
    12:[350,300], 13:[450,300], 14:[550,300],
    15:[250,350], 16:[300,350], 17:[350,350],
    18:[150,450], 19:[300,450], 20:[450,450],
    21:[50,550],  22:[300,550], 23:[550,550]
};

const ADJACENCY = {
    0:[1,9],1:[0,2,4],2:[1,14],3:[4,10],4:[1,3,5,7],5:[4,13],
    6:[7,11],7:[4,6,8],8:[7,12],9:[0,10,21],10:[3,9,11,18],
    11:[6,10,15],12:[8,13,17],13:[5,12,14,20],14:[2,13,23],
    15:[11,16],16:[15,17,19],17:[12,16],18:[10,19],19:[16,18,20,22],
    20:[13,19],21:[9,22],22:[19,21,23],23:[14,22]
};

const MILLS = [
    [0,1,2],[2,14,23],[21,22,23],[0,9,21],
    [3,4,5],[5,13,20],[18,19,20],[3,10,18],
    [6,7,8],[8,12,17],[15,16,17],[6,11,15],
    [1,4,7],[9,10,11],[12,13,14],[16,19,22]
];

function getPhase(player) {
    const placed = player === 1 ? stonesPlacedWhite : stonesPlacedBlack;
    if (placed < 9) return 1;
    const count = boardState.filter(c => c === player).length;
    if (count === 3) return 3;
    return 2;
}

function isMyTurn() {
    return currentPlayer === MY_PLAYER && gameStatus === 'active' && !waitingForAI;
}

function updateBoard(state) {
    boardState = state.board;
    currentPlayer = state.current_player;
    stonesPlacedWhite = state.stones_placed_white;
    stonesPlacedBlack = state.stones_placed_black;
    pendingRemoval = state.pending_removal;
    gameStatus = state.status;
    winner = state.winner;
    selectedPos = null;
    if (state.last_action) lastAction = state.last_action;

    renderBoard();
    updateStatus();

    if (winner !== null && winner !== undefined) showGameOver();
}

function renderBoard() {
    circles.forEach(circle => {
        const pos = parseInt(circle.dataset.pos);
        circle.classList.remove('stone-white', 'stone-black', 'legal-target',
                                'selected', 'removable', 'mill-highlight', 'last-placed');
        if (boardState[pos] === 1) circle.classList.add('stone-white');
        else if (boardState[pos] === 2) circle.classList.add('stone-black');
    });
    drawLastMove();
    if (isMyTurn()) {
        computeLegalActions();
        highlightLegal();
    }
}

function drawLastMove() {
    svg.querySelectorAll('.last-move-indicator').forEach(el => el.remove());
    if (!lastAction) return;
    const act = lastAction.action;

    if (act === 'place') {
        const [cx, cy] = POS_COORDS[lastAction.to_pos];
        const ring = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        ring.setAttribute('cx', cx); ring.setAttribute('cy', cy); ring.setAttribute('r', 24);
        ring.setAttribute('class', 'last-move-indicator last-move-ring');
        svg.appendChild(ring);
    } else if (act === 'move' || act === 'fly') {
        const [x1, y1] = POS_COORDS[lastAction.from_pos];
        const [x2, y2] = POS_COORDS[lastAction.to_pos];
        drawArrow(x1, y1, x2, y2);
        const ring = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        ring.setAttribute('cx', x2); ring.setAttribute('cy', y2); ring.setAttribute('r', 24);
        ring.setAttribute('class', 'last-move-indicator last-move-ring');
        svg.appendChild(ring);
    } else if (act === 'remove') {
        const [cx, cy] = POS_COORDS[lastAction.to_pos];
        const size = 12;
        const cross = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        cross.setAttribute('class', 'last-move-indicator');
        const l1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        l1.setAttribute('x1', cx - size); l1.setAttribute('y1', cy - size);
        l1.setAttribute('x2', cx + size); l1.setAttribute('y2', cy + size);
        l1.setAttribute('class', 'last-move-cross');
        const l2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        l2.setAttribute('x1', cx + size); l2.setAttribute('y1', cy - size);
        l2.setAttribute('x2', cx - size); l2.setAttribute('y2', cy + size);
        l2.setAttribute('class', 'last-move-cross');
        cross.appendChild(l1); cross.appendChild(l2);
        svg.appendChild(cross);
    }
}

function drawArrow(x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1;
    const len = Math.sqrt(dx * dx + dy * dy);
    const ux = dx / len, uy = dy / len;
    const offset = 22;
    const sx = x1 + ux * offset, sy = y1 + uy * offset;
    const ex = x2 - ux * offset, ey = y2 - uy * offset;

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', sx); line.setAttribute('y1', sy);
    line.setAttribute('x2', ex); line.setAttribute('y2', ey);
    line.setAttribute('class', 'last-move-indicator last-move-arrow');
    svg.appendChild(line);

    const headLen = 14, headAngle = Math.PI / 6;
    const angle = Math.atan2(dy, dx);
    const p1x = ex - headLen * Math.cos(angle - headAngle);
    const p1y = ey - headLen * Math.sin(angle - headAngle);
    const p2x = ex - headLen * Math.cos(angle + headAngle);
    const p2y = ey - headLen * Math.sin(angle + headAngle);
    const head = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    head.setAttribute('points', `${ex},${ey} ${p1x},${p1y} ${p2x},${p2y}`);
    head.setAttribute('class', 'last-move-indicator last-move-arrowhead');
    svg.appendChild(head);
}

function computeLegalActions() {
    legalActions = [];
    if (pendingRemoval) {
        const opp = 3 - currentPlayer;
        const oppPositions = [];
        boardState.forEach((c, i) => { if (c === opp) oppPositions.push(i); });
        const nonMill = oppPositions.filter(p => !isInMill(p, opp));
        const targets = nonMill.length > 0 ? nonMill : oppPositions;
        targets.forEach(p => legalActions.push({action: 'remove', to_pos: p}));
        return;
    }
    const phase = getPhase(currentPlayer);
    if (phase === 1) {
        boardState.forEach((c, i) => {
            if (c === 0) legalActions.push({action: 'place', to_pos: i});
        });
    } else if (phase === 2) {
        boardState.forEach((c, i) => {
            if (c === currentPlayer) {
                ADJACENCY[i].forEach(adj => {
                    if (boardState[adj] === 0) legalActions.push({action: 'move', from_pos: i, to_pos: adj});
                });
            }
        });
    } else {
        boardState.forEach((c, i) => {
            if (c === currentPlayer) {
                boardState.forEach((c2, j) => {
                    if (c2 === 0) legalActions.push({action: 'fly', from_pos: i, to_pos: j});
                });
            }
        });
    }
}

function isInMill(pos, player) {
    return MILLS.some(mill => mill.includes(pos) && mill.every(p => boardState[p] === player));
}

function highlightLegal() {
    if (pendingRemoval) {
        legalActions.forEach(a => {
            const circle = document.querySelector(`[data-pos="${a.to_pos}"]`);
            if (circle) circle.classList.add('removable');
        });
        return;
    }
    const phase = getPhase(currentPlayer);
    if (phase === 1) {
        legalActions.forEach(a => {
            const circle = document.querySelector(`[data-pos="${a.to_pos}"]`);
            if (circle) circle.classList.add('legal-target');
        });
    } else if (selectedPos !== null) {
        legalActions.filter(a => a.from_pos === selectedPos).forEach(a => {
            const circle = document.querySelector(`[data-pos="${a.to_pos}"]`);
            if (circle) circle.classList.add('legal-target');
        });
        const selCircle = document.querySelector(`[data-pos="${selectedPos}"]`);
        if (selCircle) selCircle.classList.add('selected');
    }
}

function updateStatus() {
    if (gameStatus === 'finished') {
        statusText.textContent = winner === MY_PLAYER ? 'Du hast gewonnen!' : 'Du hast verloren.';
        phaseText.textContent = '';
    } else if (!isMyTurn()) {
        statusText.textContent = waitingForAI ? 'Computer denkt...' : 'Gegner ist am Zug...';
        phaseText.textContent = '';
    } else if (pendingRemoval) {
        statusText.textContent = 'Muehle! Entferne einen Gegnerstein.';
        phaseText.textContent = '';
    } else {
        const phase = getPhase(MY_PLAYER);
        if (phase === 1) {
            const placed = MY_PLAYER === 1 ? stonesPlacedWhite : stonesPlacedBlack;
            statusText.textContent = `Du bist am Zug — Stein ${placed + 1} von 9 setzen`;
        } else {
            statusText.textContent = 'Du bist am Zug.';
        }
        const phaseNames = {1: 'Setzen', 2: 'Ziehen', 3: 'Springen'};
        phaseText.textContent = `Phase: ${phaseNames[phase]}`;
    }

    const wPlaced = Math.min(stonesPlacedWhite, 9);
    const bPlaced = Math.min(stonesPlacedBlack, 9);
    const wOnBoard = boardState.filter(c => c === 1).length;
    const bOnBoard = boardState.filter(c => c === 2).length;
    stonesInfo.innerHTML =
        `Weiss: ${wPlaced}/9 gesetzt, ${wOnBoard} auf dem Brett<br>` +
        `Schwarz: ${bPlaced}/9 gesetzt, ${bOnBoard} auf dem Brett`;

    const myPhase = getPhase(MY_PLAYER);
    if (myPhase === 1 && gameStatus === 'active') {
        const placed = MY_PLAYER === 1 ? wPlaced : bPlaced;
        let dots = '';
        for (let i = 1; i <= 9; i++) {
            if (i <= placed) dots += '<span class="sc-dot sc-placed"></span>';
            else if (i === placed + 1 && isMyTurn() && !pendingRemoval) dots += '<span class="sc-dot sc-next"></span>';
            else dots += '<span class="sc-dot sc-empty"></span>';
        }
        stoneCounter.innerHTML = `<div class="sc-label">Steine: ${placed}/9</div><div class="sc-dots">${dots}</div>`;
        stoneCounter.style.display = '';
    } else {
        stoneCounter.style.display = 'none';
    }
}

function showGameOver() {
    const overlay = document.getElementById('game-over-overlay');
    const text = document.getElementById('game-over-text');
    text.textContent = winner === MY_PLAYER ? 'Du hast gewonnen!' : 'Du hast verloren!';
    overlay.style.display = 'flex';
}

// Click handler
circles.forEach(circle => {
    circle.addEventListener('click', () => {
        if (!isMyTurn()) return;
        const pos = parseInt(circle.dataset.pos);

        if (pendingRemoval) {
            if (legalActions.some(a => a.to_pos === pos)) sendAction({action: 'remove', to_pos: pos});
            return;
        }

        const phase = getPhase(currentPlayer);
        if (phase === 1) {
            if (boardState[pos] === 0) sendAction({action: 'place', to_pos: pos});
        } else {
            if (boardState[pos] === currentPlayer) {
                selectedPos = pos;
                renderBoard();
            } else if (selectedPos !== null && boardState[pos] === 0) {
                const actionType = phase === 2 ? 'move' : 'fly';
                const action = {action: actionType, from_pos: selectedPos, to_pos: pos};
                if (legalActions.some(a => a.action === actionType && a.from_pos === selectedPos && a.to_pos === pos)) {
                    sendAction(action);
                }
            }
        }
    });
});

function sendAction(action) {
    if (IS_VS_COMPUTER) {
        sendActionREST(action);
    } else if (typeof sendActionSocket === 'function') {
        sendActionSocket(action);
    }
}

function sendActionREST(action) {
    waitingForAI = true;
    updateStatus();

    fetch(`${MUEHLE_BASE}/game/${GAME_ID}/action`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CSRF_TOKEN,
        },
        body: JSON.stringify(action),
    })
    .then(r => r.json())
    .then(data => {
        waitingForAI = false;
        if (data.error) { console.error(data.error); return; }
        updateBoard(data.state);
    })
    .catch(err => {
        waitingForAI = false;
        console.error('Error:', err);
    });
}

function initBoard(state) {
    updateBoard(state);
}
