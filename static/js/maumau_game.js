/* ============================================================
   Mau-Mau Game Client
   ============================================================ */

(function() {
    'use strict';

    var SUIT_SYMBOLS = { H: '\u2665', D: '\u2666', C: '\u2663', S: '\u2660' };
    var SUIT_NAMES = { H: 'Herz', D: 'Karo', C: 'Kreuz', S: 'Pik' };
    var VALUE_DISPLAY = {
        '2':'2','3':'3','4':'4','5':'5','6':'6','7':'7','8':'8','9':'9',
        'T':'10','J':'J','Q':'Q','K':'K','A':'A'
    };

    var socket;
    var gameState = null;
    var myPlayerId = USER_ID;
    var pendingJackCard = null;
    var pendingJackCardEl = null;
    var animating = false;

    // --- Helpers ---
    function cardSuit(card) { return card[card.length - 1]; }
    function cardValue(card) { return card.slice(0, -1); }
    function cardColor(card) {
        var s = cardSuit(card);
        return (s === 'H' || s === 'D') ? 'red' : 'black';
    }
    function cardDisplayValue(card) {
        return VALUE_DISPLAY[cardValue(card)] || cardValue(card);
    }
    function suitSymbol(suit) { return SUIT_SYMBOLS[suit] || suit; }

    function renderCardHTML(card) {
        var v = cardDisplayValue(card);
        var s = cardSuit(card);
        var sym = suitSymbol(s);
        return '<div class="card-corner card-corner-tl"><span>' + v + '</span><span>' + sym + '</span></div>' +
               '<span class="card-center-suit">' + sym + '</span>' +
               '<div class="card-corner card-corner-br"><span>' + v + '</span><span>' + sym + '</span></div>';
    }

    // --- Init ---
    function init() {
        socket = io('/maumau', { path: (typeof SCRIPT_ROOT !== 'undefined' ? SCRIPT_ROOT : '') + '/socket.io/' });

        socket.on('connect', function() {
            socket.emit('join_game', {
                room_code: ROOM_CODE,
                user_id: USER_ID,
                username: USERNAME
            });
        });

        socket.on('game_state', function(state) {
            gameState = state;
            render();
        });

        socket.on('ai_move', function(data) {
            handleAiMove(data);
        });

        socket.on('draw_result', function(data) {
            if (data.player_id === myPlayerId) {
                setStatus('Du hast ' + data.draw_count + ' Karte(n) gezogen');
            } else {
                setStatus(data.player_name + ' zieht ' + data.draw_count + ' Karte(n)');
            }
        });

        socket.on('game_over', function(data) {
            showGameOver(data);
        });

        socket.on('log_entry', function(data) {
            addLogEntry(data.text, data.type, data.time);
        });

        socket.on('error', function(data) {
            setStatus('Fehler: ' + data.message);
        });

        // Draw pile click
        document.getElementById('draw-pile').addEventListener('click', function() {
            if (animating) return;
            if (!gameState || gameState.status !== 'playing') return;
            if (gameState.current_player_id !== myPlayerId) {
                setStatus('Du bist nicht dran!');
                return;
            }
            socket.emit('draw_card', {});
        });

        // Suit modal buttons
        document.querySelectorAll('.maumau-suit-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                var suit = this.getAttribute('data-suit');
                document.getElementById('suit-modal').style.display = 'none';
                var card = pendingJackCard;
                var cardEl = pendingJackCardEl;
                pendingJackCard = null;
                pendingJackCardEl = null;
                animateHumanPlay(cardEl, card, function() {
                    socket.emit('play_card', { card: card, wished_suit: suit });
                });
            });
        });
    }

    // --- Render ---
    function render() {
        if (!gameState) return;

        renderOpponents();
        renderTopCard();
        renderDeckCount();
        renderPlayerHand();
        renderGameInfo();
    }

    function renderOpponents() {
        var area = document.getElementById('opponents-area');
        area.innerHTML = '';

        gameState.players.forEach(function(p) {
            if (p.id === myPlayerId) return;

            var div = document.createElement('div');
            div.className = 'maumau-opponent';
            div.id = 'opponent-' + p.id;
            if (gameState.current_player_id === p.id) {
                div.classList.add('active');
            }

            var html = '<div class="maumau-opponent-name">' + escapeHtml(p.name);
            if (p.type === 'ai') html += ' <small>(KI)</small>';
            html += '</div>';

            html += '<div class="maumau-opponent-cards">';
            var showCount = Math.min(p.card_count, 10);
            for (var i = 0; i < showCount; i++) {
                html += '<div class="maumau-opponent-card-back"></div>';
            }
            html += '</div>';

            html += '<div class="maumau-opponent-card-count">' + p.card_count + ' Karte(n)</div>';

            if (p.said_mau && p.card_count === 1) {
                html += '<div class="maumau-mau-indicator">MAU!</div>';
            }

            div.innerHTML = html;
            area.appendChild(div);
        });
    }

    function renderTopCard() {
        var topCardEl = document.getElementById('top-card');
        if (gameState.top_card) {
            var card = gameState.top_card;
            var col = cardColor(card);
            topCardEl.className = 'maumau-card card-' + col;
            topCardEl.innerHTML = renderCardHTML(card);
        } else {
            topCardEl.className = 'maumau-card';
            topCardEl.innerHTML = '';
        }
    }

    function renderDeckCount() {
        document.getElementById('deck-count').textContent = gameState.deck_count;
    }

    function renderPlayerHand() {
        var handEl = document.getElementById('player-hand');
        handEl.innerHTML = '';

        var myPlayer = gameState.players.find(function(p) { return p.id === myPlayerId; });
        if (!myPlayer || !myPlayer.hand) return;

        var isMyTurn = gameState.current_player_id === myPlayerId;
        var playerArea = document.getElementById('player-area');
        if (isMyTurn) {
            playerArea.classList.add('active-turn');
        } else {
            playerArea.classList.remove('active-turn');
        }

        myPlayer.hand.forEach(function(card) {
            var div = document.createElement('div');
            var col = cardColor(card);
            div.className = 'maumau-hand-card card-' + col;
            div.setAttribute('data-card', card);

            div.innerHTML = renderCardHTML(card);

            var playable = isMyTurn && canPlayCard(card);
            if (isMyTurn) {
                if (playable) {
                    div.classList.add('playable');
                } else {
                    div.classList.add('not-playable');
                }
            }

            div.addEventListener('click', function() {
                if (animating) return;
                if (!isMyTurn) {
                    setStatus('Du bist nicht dran!');
                    return;
                }
                if (!playable) {
                    setStatus('Diese Karte kannst du nicht spielen!');
                    return;
                }
                playCard(card, this);
            });

            handEl.appendChild(div);
        });

        if (myPlayer.said_mau && myPlayer.hand.length === 1) {
            setStatus('MAU! Noch eine Karte!');
        }
    }

    function renderGameInfo() {
        var currentPlayer = gameState.players[gameState.current_player_index];
        var turnEl = document.getElementById('turn-indicator');
        if (currentPlayer.id === myPlayerId) {
            turnEl.textContent = 'Dein Zug!';
        } else {
            turnEl.textContent = currentPlayer.name + ' ist dran';
        }

        var dirEl = document.getElementById('direction-indicator');
        dirEl.textContent = gameState.direction === 1 ? 'Richtung: Im Uhrzeigersinn' : 'Richtung: Gegen den Uhrzeigersinn';

        var wishedEl = document.getElementById('wished-suit-display');
        if (gameState.wished_suit) {
            wishedEl.style.display = 'block';
            var sym = suitSymbol(gameState.wished_suit);
            var col = (gameState.wished_suit === 'H' || gameState.wished_suit === 'D') ? '#d32f2f' : '#ddd';
            wishedEl.innerHTML = 'Gewuenscht: <span style="color:' + col + ';">' + sym + ' ' + SUIT_NAMES[gameState.wished_suit] + '</span>';
        } else {
            wishedEl.style.display = 'none';
        }

        var pendingEl = document.getElementById('pending-draw-display');
        if (gameState.pending_draw > 0) {
            pendingEl.style.display = 'block';
            pendingEl.textContent = 'Muss ziehen: ' + gameState.pending_draw + ' Karten!';
        } else {
            pendingEl.style.display = 'none';
        }
    }

    // --- Card Playability Check ---
    function canPlayCard(card) {
        if (!gameState) return false;
        var topCard = gameState.top_card;
        if (!topCard) return true;

        var playVal = cardValue(card);
        var playSuit = cardSuit(card);
        var topVal = cardValue(topCard);
        var topSuit = cardSuit(topCard);

        if (gameState.pending_draw > 0) {
            return playVal === '7';
        }

        if (playVal === 'J') return true;

        if (gameState.wished_suit) {
            return playSuit === gameState.wished_suit || playVal === 'J';
        }

        return playSuit === topSuit || playVal === topVal;
    }

    // --- Play Card ---
    function playCard(card, cardEl) {
        if (cardValue(card) === 'J') {
            pendingJackCard = card;
            pendingJackCardEl = cardEl || null;
            document.getElementById('suit-modal').style.display = 'flex';
            return;
        }
        animateHumanPlay(cardEl, card, function() {
            socket.emit('play_card', { card: card });
        });
    }

    // --- Human Play Animation ---
    function animateHumanPlay(cardEl, card, callback) {
        animating = true;

        var floatingCard = document.getElementById('floating-card');
        var discardEl = document.getElementById('discard-pile');
        var tableRect = document.getElementById('game-table').getBoundingClientRect();
        var endRect = discardEl.getBoundingClientRect();

        var col = cardColor(card);
        floatingCard.className = 'maumau-floating-card card-' + col;
        floatingCard.innerHTML = renderCardHTML(card);

        if (cardEl) {
            var startRect = cardEl.getBoundingClientRect();
            floatingCard.style.left = (startRect.left - tableRect.left + startRect.width / 2 - 40) + 'px';
            floatingCard.style.top  = (startRect.top  - tableRect.top  + startRect.height / 2 - 57) + 'px';
            cardEl.style.visibility = 'hidden';
        } else {
            var playerArea = document.getElementById('player-area');
            var areaRect = playerArea.getBoundingClientRect();
            floatingCard.style.left = (areaRect.left - tableRect.left + areaRect.width / 2 - 40) + 'px';
            floatingCard.style.top  = (areaRect.top  - tableRect.top  + 20) + 'px';
        }

        floatingCard.style.transition = 'none';
        floatingCard.style.display = 'flex';
        floatingCard.offsetHeight; // force reflow

        floatingCard.style.transition = 'all 0.5s ease-in-out';
        floatingCard.style.left = (endRect.left - tableRect.left + endRect.width / 2 - 40) + 'px';
        floatingCard.style.top  = (endRect.top  - tableRect.top  + endRect.height / 2 - 57) + 'px';

        setTimeout(function() {
            floatingCard.style.display = 'none';
            animating = false;
            if (callback) callback();
        }, 550);
    }

    // --- AI Move Animation ---
    function handleAiMove(data) {
        animating = true;
        setStatus(data.player_name + ' spielt ' + formatCard(data.card));

        var opponentEl = document.getElementById('opponent-' + data.player_id);
        var discardEl = document.getElementById('discard-pile');
        var floatingCard = document.getElementById('floating-card');

        if (opponentEl && discardEl) {
            var startRect = opponentEl.getBoundingClientRect();
            var endRect = discardEl.getBoundingClientRect();
            var tableRect = document.getElementById('game-table').getBoundingClientRect();

            floatingCard.style.display = 'flex';
            floatingCard.className = 'maumau-floating-card';

            if (data.card) {
                var col = cardColor(data.card);
                floatingCard.className = 'maumau-floating-card card-' + col;
                floatingCard.innerHTML = renderCardHTML(data.card);
            } else {
                floatingCard.className = 'maumau-floating-card card-back-float';
                floatingCard.innerHTML = '';
            }

            floatingCard.style.left = (startRect.left - tableRect.left + startRect.width / 2 - 40) + 'px';
            floatingCard.style.top = (startRect.top - tableRect.top + startRect.height / 2 - 57) + 'px';
            floatingCard.style.transition = 'none';

            floatingCard.offsetHeight;

            floatingCard.style.transition = 'all 0.8s ease-in-out';
            floatingCard.style.left = (endRect.left - tableRect.left + endRect.width / 2 - 40) + 'px';
            floatingCard.style.top = (endRect.top - tableRect.top + endRect.height / 2 - 57) + 'px';

            setTimeout(function() {
                floatingCard.style.display = 'none';
                animating = false;
            }, 900);
        } else {
            setTimeout(function() {
                animating = false;
            }, 200);
        }
    }

    // --- Game Over ---
    function showGameOver(data) {
        var modal = document.getElementById('gameover-modal');
        var title = document.getElementById('gameover-title');
        var msg = document.getElementById('gameover-message');
        var celebration = document.getElementById('celebration');

        if (data.winner_id === myPlayerId) {
            title.textContent = 'MAU-MAU! Du gewinnst!';
            title.style.color = '#27ae60';
            msg.textContent = 'Herzlichen Glueckwunsch! Alle Karten abgelegt!';

            celebration.innerHTML = '';
            var colors = ['#e74c3c', '#3498db', '#27ae60', '#f39c12', '#9b59b6', '#1abc9c'];
            for (var i = 0; i < 30; i++) {
                var confetti = document.createElement('div');
                confetti.className = 'maumau-confetti';
                confetti.style.left = Math.random() * 100 + '%';
                confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
                confetti.style.animationDelay = Math.random() * 1 + 's';
                confetti.style.animationDuration = (1.5 + Math.random()) + 's';
                celebration.appendChild(confetti);
            }
        } else {
            title.textContent = 'Spiel vorbei';
            title.style.color = '#e74c3c';
            msg.textContent = data.winner_name + ' gewinnt das Spiel!';
        }

        modal.style.display = 'flex';
    }

    // --- Move Log ---
    function addLogEntry(text, type, time) {
        var container = document.getElementById('game-log-entries');
        if (!container) return;

        var entry = document.createElement('div');
        entry.className = 'maumau-log-entry maumau-log-entry-' + (type || 'info');

        var timeSpan = document.createElement('span');
        timeSpan.className = 'log-time';
        timeSpan.textContent = time || '';

        entry.appendChild(timeSpan);
        entry.appendChild(document.createTextNode(text));

        container.appendChild(entry);
        container.scrollTop = container.scrollHeight;
    }

    // --- Utility ---
    function setStatus(msg) {
        document.getElementById('status-bar').textContent = msg;
    }

    function formatCard(card) {
        return cardDisplayValue(card) + suitSymbol(cardSuit(card));
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    // --- Start ---
    document.addEventListener('DOMContentLoaded', init);
})();
