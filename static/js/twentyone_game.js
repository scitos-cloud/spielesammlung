const API = typeof TWENTYONE_BASE !== 'undefined' ? TWENTYONE_BASE : '';
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content || '';

const SUIT_SYMBOLS = {
    hearts: "\u2665", diamonds: "\u2666", clubs: "\u2663", spades: "\u2660", hidden: "",
};
const SUIT_COLORS = {
    hearts: "red", diamonds: "red", clubs: "black", spades: "black", hidden: "black",
};

const DEAL_DELAY = 3000;
const THINK_DELAY = 5000;
let busy = false;
let wins = { player: 0, dealer: 0, tie: 0 };

function playApplause() {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const duration = 2.5;
    const sampleRate = ctx.sampleRate;
    const length = sampleRate * duration;
    const buffer = ctx.createBuffer(2, length, sampleRate);
    for (let ch = 0; ch < 2; ch++) {
        const data = buffer.getChannelData(ch);
        for (let i = 0; i < length; i++) {
            const t = i / sampleRate;
            let sample = (Math.random() * 2 - 1);
            const envelope = Math.min(1, t * 4) * Math.max(0, 1 - t / duration);
            const burstFreq = 6 + t * 2;
            const burst = 0.4 + 0.6 * Math.pow(Math.max(0, Math.sin(t * burstFreq * Math.PI * 2)), 4);
            data[i] = sample * envelope * burst * 0.3;
        }
    }
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    const filter = ctx.createBiquadFilter();
    filter.type = "bandpass"; filter.frequency.value = 3000; filter.Q.value = 0.5;
    source.connect(filter); filter.connect(ctx.destination);
    source.start(); source.onended = () => ctx.close();
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function apiCall(endpoint, method = "POST") {
    const opts = { method };
    if (method === "POST") opts.headers = { 'X-CSRFToken': CSRF_TOKEN };
    const res = await fetch(API + endpoint, opts);
    return res.json();
}

function updateButtons(playing) {
    document.getElementById("btn-hit").disabled = busy || !playing;
    document.getElementById("btn-stand").disabled = busy || !playing;
    document.getElementById("btn-new").disabled = busy;
}

function renderCard(card) {
    const el = document.createElement("div");
    if (card.suit === "hidden") {
        el.className = "card card-hidden"; el.innerHTML = "?"; return el;
    }
    const color = SUIT_COLORS[card.suit];
    el.className = `card card-${color}`;
    const symbol = SUIT_SYMBOLS[card.suit];
    el.innerHTML = `
        <div class="card-corner top-left"><div class="card-rank">${card.rank}</div><div class="card-suit">${symbol}</div></div>
        <div class="card-center">${symbol}</div>
        <div class="card-corner bottom-right"><div class="card-rank">${card.rank}</div><div class="card-suit">${symbol}</div></div>`;
    return el;
}

function renderThinkingPlaceholder() {
    const el = document.createElement("div");
    el.className = "card card-thinking"; el.innerHTML = "\uD83E\uDD14"; return el;
}

function calcVisibleScore(cards) {
    let total = 0, aces = 0;
    for (const card of cards) {
        if (card.suit === "hidden") continue;
        total += card.value; if (card.rank === "A") aces++;
    }
    while (total > 21 && aces > 0) { total -= 10; aces--; }
    return total;
}

function setScore(id, score) { document.getElementById(id).textContent = `(${score})`; }

function updateWinCounter() {
    document.getElementById("wins-player").textContent = wins.player;
    document.getElementById("wins-dealer").textContent = wins.dealer;
    document.getElementById("wins-tie").textContent = wins.tie;
}

function showResult(state) {
    const message = document.getElementById("message");
    if (state.state === "finished") {
        message.textContent = state.message;
        message.className = "message " +
            (state.result === "player_win" ? "win" : state.result === "tie" ? "tie" : "lose");
        if (state.result === "player_win") { wins.player++; playApplause(); }
        else if (state.result === "dealer_win") { wins.dealer++; }
        else { wins.tie++; }
        updateWinCounter();
    } else { message.textContent = ""; message.className = "message"; }
}

async function newGame() {
    if (busy) return;
    busy = true; updateButtons(false);
    const dealerContainer = document.getElementById("dealer-cards");
    const playerContainer = document.getElementById("player-cards");
    dealerContainer.innerHTML = ""; playerContainer.innerHTML = "";
    setScore("dealer-score", 0); setScore("player-score", 0);
    document.getElementById("message").textContent = "";
    document.getElementById("message").className = "message";

    const state = await apiCall("/api/new");
    const playerCards = state.player.cards;
    const dealerCards = state.dealer.cards;

    playerContainer.appendChild(renderCard(playerCards[0]));
    setScore("player-score", calcVisibleScore([playerCards[0]]));
    await sleep(DEAL_DELAY);
    dealerContainer.appendChild(renderCard(dealerCards[0]));
    setScore("dealer-score", calcVisibleScore([dealerCards[0]]));
    await sleep(DEAL_DELAY);
    playerContainer.appendChild(renderCard(playerCards[1]));
    setScore("player-score", calcVisibleScore(playerCards.slice(0, 2)));
    await sleep(DEAL_DELAY);
    dealerContainer.appendChild(renderCard(dealerCards[1]));
    setScore("dealer-score", calcVisibleScore(dealerCards.slice(0, 2)));

    showResult(state);
    busy = false; updateButtons(state.state === "playing");
}

async function hit() {
    if (busy) return;
    busy = true; updateButtons(false);
    const state = await apiCall("/api/hit");
    const playerContainer = document.getElementById("player-cards");
    playerContainer.innerHTML = "";
    state.player.cards.forEach(card => playerContainer.appendChild(renderCard(card)));
    setScore("player-score", state.player.score);
    showResult(state);
    busy = false; updateButtons(state.state === "playing");
}

async function stand() {
    if (busy) return;
    busy = true; updateButtons(false);
    const state = await apiCall("/api/stand");
    const dealerContainer = document.getElementById("dealer-cards");
    const allDealerCards = state.dealer.cards;

    dealerContainer.innerHTML = "";
    dealerContainer.appendChild(renderCard(allDealerCards[0]));
    setScore("dealer-score", calcVisibleScore([allDealerCards[0]]));

    const placeholder1 = renderThinkingPlaceholder();
    dealerContainer.appendChild(placeholder1);
    await sleep(DEAL_DELAY);
    dealerContainer.replaceChild(renderCard(allDealerCards[1]), placeholder1);
    setScore("dealer-score", calcVisibleScore(allDealerCards.slice(0, 2)));

    for (let i = 2; i < allDealerCards.length; i++) {
        const placeholder = renderThinkingPlaceholder();
        dealerContainer.appendChild(placeholder);
        await sleep(THINK_DELAY);
        dealerContainer.replaceChild(renderCard(allDealerCards[i]), placeholder);
        setScore("dealer-score", calcVisibleScore(allDealerCards.slice(0, i + 1)));
    }

    setScore("player-score", state.player.score);
    setScore("dealer-score", state.dealer.score);
    showResult(state);
    busy = false; updateButtons(false);
}

newGame();
