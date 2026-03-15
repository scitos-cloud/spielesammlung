/* Backgammon Game Client
 * Uses constants from template: BACKGAMMON_BASE, GAME_ID, MY_PLAYER, IS_AI, CSRF_TOKEN
 */

// Board layout from white's perspective (player 1)
// Top row L->R: points 13..18, bar, 19..24
// Bottom row L->R: points 12..7, bar, 6..1
const TOP_POINTS = [12, 13, 14, 15, 16, 17]; // indices 0-based
const TOP_POINTS_RIGHT = [18, 19, 20, 21, 22, 23];
const BOTTOM_POINTS = [11, 10, 9, 8, 7, 6];
const BOTTOM_POINTS_RIGHT = [5, 4, 3, 2, 1, 0];

let state = {
    board: new Array(24).fill(0),
    bar: [0, 0],
    off: [0, 0],
    current_player: 0,
    dice: [],
    dice_rolled: [],
    winner: 0,
    legal_moves: []
};
let selectedFrom = null;
let pollTimer = null;
let moveLog = [];
let aiHighlight = null; // {from, to} currently highlighted AI move

// --- API ---

function apiUrl(path) {
    return BACKGAMMON_BASE + path;
}

function fetchState() {
    return fetch(apiUrl('/game/' + GAME_ID + '/state'))
        .then(r => r.json())
        .then(data => {
            state = data;
            render();
            updatePolling();
        });
}

function sendMove(from, to, die) {
    return fetch(apiUrl('/game/' + GAME_ID + '/move'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CSRF_TOKEN
        },
        body: JSON.stringify({ from: from, to: to, die: die })
    })
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            updateStatus(data.error);
            return;
        }
        state = data.state;
        addMoveToLog(MY_PLAYER, from, to, die, false);
        selectedFrom = null;
        render();

        if (data.ai_moves && data.ai_moves.length > 0) {
            animateAIMoves(data.ai_moves);
        } else {
            updatePolling();
        }
    });
}

// --- AI move animation ---

async function animateAIMoves(aiMoves) {
    const aiPlayer = MY_PLAYER === 1 ? 2 : 1;
    updateStatus('KI spielt...');
    for (let i = 0; i < aiMoves.length; i++) {
        const m = aiMoves[i];
        // Highlight source and target on board
        aiHighlight = { from: m.from, to: m.to };
        render();
        await sleep(600);
        // Log with KI marker
        addMoveToLog(aiPlayer, m.from, m.to, m.die, true);
        aiHighlight = null;
    }
    await sleep(400);
    await fetchState();
}

// --- Rendering ---

function render() {
    renderBoard(state);
    renderDice(state.dice_rolled, state.dice);
    renderStatus();
    renderMoveLog();
}

function renderBoard(s) {
    const boardEl = document.getElementById('board');
    boardEl.innerHTML = '';
    boardEl.className = 'bg-board';

    // Top half: points 13-18, bar, 19-24, home
    TOP_POINTS.forEach(idx => {
        boardEl.appendChild(createPoint(idx, s, 'top'));
    });
    boardEl.appendChild(createBar(s, 'top'));
    TOP_POINTS_RIGHT.forEach(idx => {
        boardEl.appendChild(createPoint(idx, s, 'top'));
    });
    boardEl.appendChild(createHome(s, 'top'));

    // Middle separator
    const mid = document.createElement('div');
    mid.className = 'bg-middle';
    boardEl.appendChild(mid);

    // Bottom half: points 12-7, bar, 6-1, home
    BOTTOM_POINTS.forEach(idx => {
        boardEl.appendChild(createPoint(idx, s, 'bottom'));
    });
    boardEl.appendChild(createBar(s, 'bottom'));
    BOTTOM_POINTS_RIGHT.forEach(idx => {
        boardEl.appendChild(createPoint(idx, s, 'bottom'));
    });
    boardEl.appendChild(createHome(s, 'bottom'));
}

function createPoint(idx, s, half) {
    const el = document.createElement('div');
    const pointNum = idx + 1;
    const isLight = idx % 2 === 0;
    const dirClass = half === 'top' ? 'bg-point-top' : 'bg-point-bottom';
    el.className = 'bg-point ' + dirClass + ' ' + (isLight ? 'bg-point-light' : 'bg-point-dark');
    el.dataset.pointIdx = idx;

    // AI move highlight
    if (aiHighlight && (aiHighlight.from === idx || aiHighlight.to === idx)) {
        el.classList.add('ai-highlight');
    }

    // Point number
    const numEl = document.createElement('span');
    numEl.className = 'bg-point-number';
    numEl.textContent = pointNum;
    el.appendChild(numEl);

    // Checkers container
    const inner = document.createElement('div');
    inner.className = 'bg-point-inner';

    const val = s.board[idx];
    const count = Math.abs(val);
    const player = val > 0 ? 1 : (val < 0 ? 2 : 0);
    const displayCount = Math.min(count, 5);

    for (let i = 0; i < displayCount; i++) {
        const checker = document.createElement('div');
        checker.className = 'bg-checker ' + (player === 1 ? 'white-checker' : 'black-checker');

        // Show count on top checker if > 5
        if (i === displayCount - 1 && count > 5) {
            const countEl = document.createElement('span');
            countEl.className = 'bg-checker-count';
            countEl.textContent = count;
            checker.appendChild(countEl);
        }

        // Make top checker clickable if it's a legal from
        if (i === displayCount - 1 && isMyTurn() && player === MY_PLAYER && isLegalFrom(idx)) {
            checker.classList.add('clickable');
            checker.addEventListener('click', function(e) {
                e.stopPropagation();
                selectChecker(idx);
            });
        }

        if (selectedFrom === idx && i === displayCount - 1) {
            checker.classList.add('selected');
        }

        inner.appendChild(checker);
    }

    el.appendChild(inner);

    // Destination click
    if (selectedFrom !== null && isValidTarget(selectedFrom, idx)) {
        el.classList.add('valid-target');
        el.addEventListener('click', function() {
            makeMove(selectedFrom, idx);
        });
    } else {
        el.addEventListener('click', function(e) {
            if (e.target === el || e.target === inner || e.target === numEl) {
                clearSelection();
            }
        });
    }

    return el;
}

function createBar(s, half) {
    const el = document.createElement('div');
    el.className = 'bg-bar';

    // AI highlight for bar entry (from = -1)
    if (aiHighlight && aiHighlight.from === -1) {
        el.classList.add('ai-highlight');
    }

    // Top bar shows player 2 (black) bar checkers, bottom shows player 1 (white)
    const playerIdx = half === 'top' ? 1 : 0; // bar[0]=white, bar[1]=black
    const count = s.bar[playerIdx];
    const playerNum = playerIdx + 1;
    const checkerClass = playerNum === 1 ? 'white-checker' : 'black-checker';

    for (let i = 0; i < Math.min(count, 4); i++) {
        const checker = document.createElement('div');
        checker.className = 'bg-checker ' + checkerClass;

        if (count > 4 && i === Math.min(count, 4) - 1) {
            const countEl = document.createElement('span');
            countEl.className = 'bg-checker-count';
            countEl.textContent = count;
            checker.appendChild(countEl);
        }

        // Bar checkers clickable if legal from = -1
        if (i === Math.min(count, 4) - 1 && isMyTurn() && playerNum === MY_PLAYER && isLegalFrom(-1)) {
            checker.classList.add('clickable');
            checker.addEventListener('click', function(e) {
                e.stopPropagation();
                selectChecker(-1);
            });
        }

        if (selectedFrom === -1 && i === Math.min(count, 4) - 1 && playerNum === MY_PLAYER) {
            checker.classList.add('selected');
        }

        el.appendChild(checker);
    }

    return el;
}

function createHome(s, half) {
    const el = document.createElement('div');
    el.className = 'bg-home';

    // AI highlight for bearing off (to = -2)
    if (aiHighlight && aiHighlight.to === -2) {
        el.classList.add('ai-highlight');
    }

    // Top home = black off, bottom home = white off
    const playerIdx = half === 'top' ? 1 : 0;
    const count = s.off[playerIdx];
    const checkerClass = (playerIdx === 0) ? 'white-checker' : 'black-checker';

    for (let i = 0; i < Math.min(count, 15); i++) {
        const chip = document.createElement('div');
        chip.className = 'bg-home-checker ' + checkerClass;
        el.appendChild(chip);
    }

    const label = document.createElement('span');
    label.className = 'bg-home-label';
    label.textContent = count + '/15';
    el.appendChild(label);

    // Home area clickable as destination (to = -2 for bearing off)
    if (selectedFrom !== null && isValidTarget(selectedFrom, -2) && (
        (MY_PLAYER === 1 && half === 'bottom') || (MY_PLAYER === 2 && half === 'top')
    )) {
        el.classList.add('valid-target');
        el.addEventListener('click', function() {
            makeMove(selectedFrom, -2);
        });
    }

    return el;
}

// --- Dice rendering ---

function renderDice(rolled, remaining) {
    const area = document.getElementById('dice-area');
    area.innerHTML = '';

    if (!rolled || rolled.length === 0) return;

    // Track which rolled dice have been used
    const remainingCopy = remaining ? remaining.slice() : [];

    rolled.forEach(val => {
        const dieEl = createDie(val);
        const rIdx = remainingCopy.indexOf(val);
        if (rIdx === -1) {
            dieEl.classList.add('dice-used');
        } else {
            remainingCopy.splice(rIdx, 1);
        }
        area.appendChild(dieEl);
    });
}

function createDie(value) {
    const die = document.createElement('div');
    die.className = 'dice';

    // 3x3 grid for pip positions
    // Positions: TL TC TR ML MC MR BL BC BR
    const positions = {
        1: [false, false, false, false, true, false, false, false, false],
        2: [false, false, true, false, false, false, true, false, false],
        3: [false, false, true, false, true, false, true, false, false],
        4: [true, false, true, false, false, false, true, false, true],
        5: [true, false, true, false, true, false, true, false, true],
        6: [true, false, true, true, false, true, true, false, true]
    };

    const pips = positions[value] || positions[1];
    pips.forEach(show => {
        const pip = document.createElement('div');
        pip.className = 'pip' + (show ? '' : ' hidden');
        die.appendChild(pip);
    });

    return die;
}

// --- Status ---

function renderStatus() {
    const statusEl = document.getElementById('status');
    statusEl.className = '';

    if (state.winner) {
        if (state.winner === MY_PLAYER) {
            statusEl.textContent = 'Du hast gewonnen!';
            statusEl.className = 'bg-status winner';
        } else {
            statusEl.textContent = 'Du hast verloren!';
            statusEl.className = 'bg-status loser';
        }
        return;
    }

    if (isMyTurn()) {
        if (state.dice && state.dice.length > 0) {
            const diceStr = state.dice_rolled ? state.dice_rolled.join(', ') : '';
            statusEl.textContent = 'Dein Zug \u2014 W\u00fcrfel: ' + diceStr;
            if (state.legal_moves.length === 0) {
                statusEl.textContent += ' (keine Z\u00fcge m\u00f6glich)';
            }
        } else {
            statusEl.textContent = 'Dein Zug';
        }
    } else {
        if (IS_AI) {
            statusEl.textContent = 'KI denkt nach...';
        } else {
            statusEl.textContent = 'Warte auf Gegner...';
        }
    }
}

function updateStatus(msg) {
    document.getElementById('status').textContent = msg;
}

// --- Move history ---

function addMoveToLog(player, from, to, die, isAI) {
    const fromStr = from === -1 ? 'Bar' : (from + 1);
    const toStr = to === -2 ? 'Aus' : (to + 1);
    const playerStr = player === 1 ? 'W' : 'S';
    const prefix = isAI ? '\ud83e\udd16 ' : '';
    moveLog.push({
        text: prefix + playerStr + ': ' + fromStr + ' \u2192 ' + toStr + ' (' + die + ')',
        isAI: !!isAI
    });
    renderMoveLog();
}

function renderMoveLog() {
    const logEl = document.getElementById('move-log');
    if (!logEl) return;
    logEl.innerHTML = '';
    moveLog.forEach((entry, i) => {
        const div = document.createElement('div');
        div.className = 'log-entry' + (entry.isAI ? ' log-ai' : '');
        div.textContent = (i + 1) + '. ' + entry.text;
        logEl.appendChild(div);
    });
    logEl.scrollTop = logEl.scrollHeight;
}

// --- Game logic helpers ---

function isMyTurn() {
    return state.current_player === MY_PLAYER && !state.winner;
}

function isLegalFrom(fromIdx) {
    if (!state.legal_moves) return false;
    return state.legal_moves.some(m => m[0] === fromIdx);
}

function isValidTarget(fromIdx, toIdx) {
    if (!state.legal_moves) return false;
    return state.legal_moves.some(m => m[0] === fromIdx && m[1] === toIdx);
}

function getDieForMove(fromIdx, toIdx) {
    if (!state.legal_moves) return null;
    const move = state.legal_moves.find(m => m[0] === fromIdx && m[1] === toIdx);
    return move ? move[2] : null;
}

// --- Click handling ---

function selectChecker(fromIdx) {
    if (selectedFrom === fromIdx) {
        clearSelection();
        return;
    }
    selectedFrom = fromIdx;
    render();
}

function clearSelection() {
    if (selectedFrom !== null) {
        selectedFrom = null;
        render();
    }
}

function makeMove(from, to) {
    const die = getDieForMove(from, to);
    if (die === null) return;
    selectedFrom = null;
    sendMove(from, to, die);
}

// --- Highlights ---

function clearHighlights() {
    document.querySelectorAll('.valid-target').forEach(el => {
        el.classList.remove('valid-target');
    });
    document.querySelectorAll('.bg-checker.selected').forEach(el => {
        el.classList.remove('selected');
    });
}

// --- Polling ---

function updatePolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }

    if (state.winner) return;

    if (!IS_AI && state.current_player !== MY_PLAYER) {
        pollTimer = setInterval(fetchState, 2000);
    }
}

// --- Utility ---

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// --- Init ---

document.addEventListener('click', function(e) {
    if (!e.target.closest('.bg-point') && !e.target.closest('.bg-bar') &&
        !e.target.closest('.bg-home') && !e.target.closest('.bg-checker')) {
        clearSelection();
    }
});

// --- Help overlay ---

function toggleHelp() {
    const overlay = document.getElementById('help-overlay');
    overlay.classList.toggle('active');
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const overlay = document.getElementById('help-overlay');
        if (overlay.classList.contains('active')) {
            overlay.classList.remove('active');
        }
    }
});

fetchState();
