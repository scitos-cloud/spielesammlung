'use strict';

const API_BASE = typeof HANGMAN_BASE !== 'undefined' ? HANGMAN_BASE : '';

// ── Constants ──────────────────────────────────────────────────────────────
const KEYBOARD_ROWS = [
  ['Q', 'W', 'E', 'R', 'T', 'Z', 'U', 'I', 'O', 'P', 'Ü'],
  ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Ö', 'Ä'],
  ['Y', 'X', 'C', 'V', 'B', 'N', 'M'],
];

const BODY_PART_IDS = ['bp-head', 'bp-body', 'bp-larm', 'bp-rarm', 'bp-lleg', 'bp-rleg'];

// ── State ──────────────────────────────────────────────────────────────────
let state = {
  gameId: null,
  display: [],
  guessed: [],
  wrong: 0,
  maxWrong: 6,
  status: 'idle',
};

let stats = JSON.parse(localStorage.getItem('hangman-stats') || '{"played":0,"won":0,"streak":0,"best":0}');

// ── DOM Refs ───────────────────────────────────────────────────────────────
const startScreen    = document.getElementById('start-screen');
const gameArea       = document.getElementById('game-area');
const wordDisplay    = document.getElementById('word-display');
const keyboard       = document.getElementById('keyboard');
const messageBanner  = document.getElementById('message-banner');
const newGameBtn     = document.getElementById('new-game-btn');
const wrongLetters   = document.getElementById('wrong-letters');
const loadingEl      = document.getElementById('loading');
const statsPlayed    = document.getElementById('stat-played');
const statsWon       = document.getElementById('stat-won');
const statsStreak    = document.getElementById('stat-streak');

// ── Keyboard ───────────────────────────────────────────────────────────────
function buildKeyboard() {
  keyboard.innerHTML = '';
  KEYBOARD_ROWS.forEach((row) => {
    const rowDiv = document.createElement('div');
    rowDiv.className = 'key-row';
    row.forEach((letter) => {
      const btn = document.createElement('button');
      btn.className = 'key-btn';
      btn.textContent = letter;
      btn.dataset.letter = letter;
      btn.setAttribute('aria-label', `Buchstabe ${letter}`);
      btn.addEventListener('click', () => onLetterClick(letter));
      rowDiv.appendChild(btn);
    });
    keyboard.appendChild(rowDiv);
  });
}

function updateKeyboard() {
  document.querySelectorAll('.key-btn').forEach((btn) => {
    const l = btn.dataset.letter;
    btn.disabled = state.status !== 'playing' || state.guessed.includes(l);
    btn.classList.toggle('correct', state.guessed.includes(l) && state.display.includes(l));
    btn.classList.toggle('wrong',   state.guessed.includes(l) && !state.display.includes(l));
  });
}

// ── Word Display ───────────────────────────────────────────────────────────
function renderWord(display, newlyRevealed = []) {
  wordDisplay.innerHTML = '';
  display.forEach((char) => {
    const cell = document.createElement('div');
    if (char === ' ') {
      cell.className = 'letter-cell space';
    } else {
      cell.className = 'letter-cell';
      if (char !== '_') {
        cell.textContent = char;
        if (newlyRevealed.includes(char)) cell.classList.add('reveal');
      }
    }
    wordDisplay.appendChild(cell);
  });
}

// ── Hangman SVG ────────────────────────────────────────────────────────────
function updateHangman(wrong) {
  BODY_PART_IDS.forEach((id, idx) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('visible', idx < wrong);
  });
}

// ── Stats ──────────────────────────────────────────────────────────────────
function renderStats() {
  statsPlayed.textContent = stats.played;
  statsWon.textContent    = stats.won;
  statsStreak.textContent = stats.streak;
}

function saveStats(won) {
  stats.played++;
  if (won) {
    stats.won++;
    stats.streak++;
    if (stats.streak > stats.best) stats.best = stats.streak;
  } else {
    stats.streak = 0;
  }
  localStorage.setItem('hangman-stats', JSON.stringify(stats));
  renderStats();
}

// ── Message Banner ─────────────────────────────────────────────────────────
function showMessage(status, word) {
  messageBanner.className = '';
  if (status === 'won') {
    messageBanner.classList.add('won');
    messageBanner.innerHTML = `
      <div>Gewonnen!</div>
      <div class="word-reveal">${word || state.display.join('')}</div>
      <div style="font-size:0.85rem;margin-top:4px;font-weight:400;color:var(--text-muted)">
        ${state.wrong} von ${state.maxWrong} Fehlern
      </div>`;
  } else {
    messageBanner.classList.add('lost');
    messageBanner.innerHTML = `
      <div>Verloren!</div>
      <div style="font-size:0.85rem;margin-top:4px;font-weight:400">Das Wort war:</div>
      <div class="word-reveal">${word}</div>`;
  }
}

function hideMessage() {
  messageBanner.className = '';
  messageBanner.innerHTML = '';
}

// ── API Calls ──────────────────────────────────────────────────────────────
async function startNewGame() {
  setLoading(true);
  try {
    const res = await fetch(API_BASE + '/api/new-game', { method: 'POST' });
    const data = await res.json();
    applyState(data);
    localStorage.setItem('hangman-game-id', data.game_id);
    showGameArea();
  } catch {
    alert('Fehler beim Starten des Spiels. Bitte Verbindung pruefen.');
  } finally {
    setLoading(false);
  }
}

async function sendGuess(letter) {
  const prevDisplay = [...state.display];
  try {
    const res = await fetch(API_BASE + '/api/guess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: state.gameId, letter }),
    });
    const data = await res.json();
    if (data.error) return;

    const newlyRevealed = data.display.filter((c, i) => c !== '_' && prevDisplay[i] === '_');
    applyState(data, newlyRevealed);

    if (data.status !== 'playing') {
      saveStats(data.status === 'won');
      showMessage(data.status, data.word);
    }
  } catch {
    // Offline or server error
  }
}

async function restoreGame(gameId) {
  try {
    const res = await fetch(`${API_BASE}/api/state/${gameId}`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (data.error) throw new Error();
    applyState(data);
    showGameArea();
  } catch {
    localStorage.removeItem('hangman-game-id');
    showStartScreen();
  }
}

// ── State Management ───────────────────────────────────────────────────────
function applyState(data, newlyRevealed = []) {
  state.gameId    = data.game_id;
  state.display   = data.display;
  state.guessed   = data.guessed || [];
  state.wrong     = data.wrong ?? 0;
  state.maxWrong  = data.max_wrong ?? 6;
  state.status    = data.status;

  renderWord(state.display, newlyRevealed);
  updateHangman(state.wrong);
  updateKeyboard();

  const wrongs = state.guessed.filter((l) => !state.display.includes(l));
  wrongLetters.textContent = wrongs.length ? `Falsch: ${wrongs.join('  ')}` : '';
}

// ── View Switching ─────────────────────────────────────────────────────────
function showGameArea() {
  startScreen.hidden = true;
  gameArea.hidden    = false;
  hideMessage();
}

function showStartScreen() {
  startScreen.hidden = false;
  gameArea.hidden    = true;
}

function setLoading(on) {
  loadingEl.style.display = on ? 'block' : 'none';
  newGameBtn.disabled = on;
}

// ── Input Handling ─────────────────────────────────────────────────────────
function onLetterClick(letter) {
  if (state.status !== 'playing') return;
  sendGuess(letter);
}

document.addEventListener('keydown', (e) => {
  if (state.status !== 'playing') return;
  const letter = e.key.toUpperCase();
  if (/^[A-ZÜÖÄ]$/.test(letter)) sendGuess(letter);
});

newGameBtn.addEventListener('click', startNewGame);
document.getElementById('new-game-start-btn')?.addEventListener('click', startNewGame);

// ── Init ───────────────────────────────────────────────────────────────────
buildKeyboard();
renderStats();

const savedGameId = localStorage.getItem('hangman-game-id');
if (savedGameId) {
  restoreGame(savedGameId);
} else {
  showStartScreen();
}
