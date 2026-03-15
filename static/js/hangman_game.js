'use strict';

const API = typeof HANGMAN_BASE !== 'undefined' ? HANGMAN_BASE : '';
const CSRF = document.querySelector('meta[name="csrf-token"]')?.content || '';

const KEYBOARDS = {
  de: [
    ['Q','W','E','R','T','Z','U','I','O','P','Ü'],
    ['A','S','D','F','G','H','J','K','L','Ö','Ä'],
    ['Y','X','C','V','B','N','M'],
  ],
  en: [
    ['Q','W','E','R','T','Y','U','I','O','P'],
    ['A','S','D','F','G','H','J','K','L'],
    ['Z','X','C','V','B','N','M'],
  ],
};

const BODY_PARTS = ['bp-head','bp-body','bp-larm','bp-rarm','bp-lleg','bp-rleg'];

// ── State ───────────────────────────────────────────────────────────────────
let game = { id: null, display: [], guessed: [], wrong: 0, maxWrong: 6, status: 'idle', lang: 'de' };
let selectedLang = localStorage.getItem('hangman-lang') || 'de';
let stats = JSON.parse(localStorage.getItem('hangman-stats') || '{"played":0,"won":0,"streak":0,"best":0}');

// ── DOM ─────────────────────────────────────────────────────────────────────
const $start      = document.getElementById('start-screen');
const $game       = document.getElementById('game-screen');
const $wordDisp   = document.getElementById('word-display');
const $keyboard   = document.getElementById('keyboard');
const $banner     = document.getElementById('message-banner');
const $wrongList  = document.getElementById('wrong-letters');
const $wrongCount = document.getElementById('wrong-count');
const $maxWrong   = document.getElementById('max-wrong-count');
const $langTag    = document.getElementById('game-lang-tag');

// ── Screen switching ────────────────────────────────────────────────────────
function showScreen(screen) {
  $start.classList.toggle('active', screen === 'start');
  $game.classList.toggle('active', screen === 'game');
}

// ── Language picker ─────────────────────────────────────────────────────────
document.querySelectorAll('.lang-btn').forEach(btn => {
  if (btn.dataset.lang === selectedLang) btn.classList.add('active');
  else btn.classList.remove('active');
  btn.addEventListener('click', () => {
    selectedLang = btn.dataset.lang;
    localStorage.setItem('hangman-lang', selectedLang);
    document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });
});

// ── Keyboard ────────────────────────────────────────────────────────────────
function buildKeyboard(lang) {
  $keyboard.innerHTML = '';
  (KEYBOARDS[lang] || KEYBOARDS.de).forEach(row => {
    const div = document.createElement('div');
    div.className = 'key-row';
    row.forEach(letter => {
      const btn = document.createElement('button');
      btn.className = 'key-btn';
      btn.textContent = letter;
      btn.dataset.letter = letter;
      btn.addEventListener('click', () => guessLetter(letter));
      div.appendChild(btn);
    });
    $keyboard.appendChild(div);
  });
}

function updateKeyboard() {
  document.querySelectorAll('.key-btn').forEach(btn => {
    const l = btn.dataset.letter;
    const used = game.guessed.includes(l);
    btn.disabled = game.status !== 'playing' || used;
    btn.classList.toggle('correct', used && game.display.includes(l));
    btn.classList.toggle('wrong',   used && !game.display.includes(l));
  });
}

// ── Word display ────────────────────────────────────────────────────────────
function renderWord(revealed = []) {
  $wordDisp.innerHTML = '';
  game.display.forEach(ch => {
    const cell = document.createElement('div');
    if (ch === ' ') {
      cell.className = 'letter-cell space';
    } else {
      cell.className = 'letter-cell';
      if (ch !== '_') {
        cell.textContent = ch;
        if (revealed.includes(ch)) cell.classList.add('reveal');
      }
    }
    $wordDisp.appendChild(cell);
  });
}

// ── Hangman SVG ─────────────────────────────────────────────────────────────
function updateHangman() {
  BODY_PARTS.forEach((id, i) => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('visible', i < game.wrong);
  });
}

// ── Stats ───────────────────────────────────────────────────────────────────
function renderStats() {
  document.getElementById('stat-played').textContent = stats.played;
  document.getElementById('stat-won').textContent = stats.won;
  document.getElementById('stat-streak').textContent = stats.streak;
}

function recordResult(won) {
  stats.played++;
  if (won) { stats.won++; stats.streak++; if (stats.streak > stats.best) stats.best = stats.streak; }
  else { stats.streak = 0; }
  localStorage.setItem('hangman-stats', JSON.stringify(stats));
  renderStats();
}

// ── Banner ──────────────────────────────────────────────────────────────────
function showBanner(status, word) {
  $banner.className = 'banner-visible';
  if (status === 'won') {
    $banner.classList.add('won');
    const label = game.lang === 'de' ? 'Gewonnen!' : 'You won!';
    const errLabel = game.lang === 'de'
      ? `${game.wrong} von ${game.maxWrong} Fehlern`
      : `${game.wrong} of ${game.maxWrong} mistakes`;
    $banner.innerHTML = `<div>${label}</div>
      <div class="word-reveal">${word || game.display.join('')}</div>
      <div class="banner-sub">${errLabel}</div>`;
  } else {
    $banner.classList.add('lost');
    const label = game.lang === 'de' ? 'Verloren!' : 'You lost!';
    const sub = game.lang === 'de' ? 'Das Wort war:' : 'The word was:';
    $banner.innerHTML = `<div>${label}</div>
      <div class="banner-sub">${sub}</div>
      <div class="word-reveal">${word}</div>`;
  }
}

function hideBanner() { $banner.className = ''; $banner.innerHTML = ''; }

// ── Wrong letters ───────────────────────────────────────────────────────────
function updateWrongInfo() {
  const wrongs = game.guessed.filter(l => !game.display.includes(l));
  $wrongList.textContent = wrongs.length ? wrongs.join('  ') : '';
  $wrongCount.textContent = game.wrong;
  $maxWrong.textContent = game.maxWrong;
}

// ── Apply server state ──────────────────────────────────────────────────────
function applyState(data, revealed = []) {
  game.id       = data.game_id;
  game.display  = data.display;
  game.guessed  = data.guessed || [];
  game.wrong    = data.wrong ?? 0;
  game.maxWrong = data.max_wrong ?? 6;
  game.status   = data.status;
  game.lang     = data.lang || 'de';

  $langTag.textContent = game.lang.toUpperCase();
  renderWord(revealed);
  updateHangman();
  updateKeyboard();
  updateWrongInfo();
}

// ── API ─────────────────────────────────────────────────────────────────────
async function startNewGame() {
  try {
    const res = await fetch(API + '/api/new-game', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ lang: selectedLang }),
    });
    if (!res.ok) { window.location.reload(); return; }
    const data = await res.json();
    buildKeyboard(data.lang || selectedLang);
    applyState(data);
    hideBanner();
    localStorage.setItem('hangman-game-id', data.game_id);
    showScreen('game');
  } catch {
    // Network error
  }
}

async function guessLetter(letter) {
  if (game.status !== 'playing') return;
  const prev = [...game.display];
  try {
    const res = await fetch(API + '/api/guess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ game_id: game.id, letter }),
    });
    const data = await res.json();
    if (data.error) return;
    const revealed = data.display.filter((c, i) => c !== '_' && prev[i] === '_');
    applyState(data, revealed);
    if (data.status !== 'playing') {
      recordResult(data.status === 'won');
      showBanner(data.status, data.word);
    }
  } catch { /* offline */ }
}

async function restoreGame(gameId) {
  try {
    const res = await fetch(`${API}/api/state/${gameId}`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (data.error) throw new Error();
    buildKeyboard(data.lang || 'de');
    applyState(data);
    if (data.status !== 'playing') {
      showBanner(data.status, data.word);
    }
    showScreen('game');
  } catch {
    localStorage.removeItem('hangman-game-id');
    showScreen('start');
  }
}

// ── Physical keyboard ───────────────────────────────────────────────────────
document.addEventListener('keydown', e => {
  if (game.status !== 'playing') return;
  const letter = e.key.toUpperCase();
  if (/^[A-ZÜÖÄ]$/.test(letter)) guessLetter(letter);
});

// ── Button handlers ─────────────────────────────────────────────────────────
document.getElementById('btn-start').addEventListener('click', startNewGame);
document.getElementById('btn-new-game').addEventListener('click', () => {
  showScreen('start');
  renderStats();
});

// ── Init ────────────────────────────────────────────────────────────────────
renderStats();
const saved = localStorage.getItem('hangman-game-id');
if (saved) { restoreGame(saved); }
else { showScreen('start'); }
