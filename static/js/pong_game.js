/* ============================================================
   Pong Game Client
   ============================================================ */

(function() {
    'use strict';

    var canvas = document.getElementById('pong-canvas');
    var ctx = canvas.getContext('2d');
    var overlay = document.getElementById('pong-overlay');
    var overlayTitle = document.getElementById('overlay-title');
    var overlayMessage = document.getElementById('overlay-message');
    var startBtn = document.getElementById('start-btn');
    var scorePlayerEl = document.getElementById('score-player');
    var scoreAiEl = document.getElementById('score-ai');

    // --- Constants ---
    var W = 800;
    var H = 500;
    var PADDLE_W = 12;
    var PADDLE_H = 80;
    var BALL_R = 8;
    var PADDLE_MARGIN = 20;
    var WIN_SCORE = 10;
    var BALL_SPEED_INITIAL = 5;
    var BALL_SPEED_INCREMENT = 0.3;
    var BALL_SPEED_MAX = 12;

    // --- Difficulty presets ---
    var DIFFICULTY = {
        easy:   { aiSpeed: 2.5, aiReaction: 0.4 },
        medium: { aiSpeed: 4.0, aiReaction: 0.7 },
        hard:   { aiSpeed: 5.5, aiReaction: 0.95 }
    };

    // --- Game state ---
    var difficulty = 'medium';
    var running = false;
    var animFrameId = null;
    var scorePlayer = 0;
    var scoreAi = 0;

    var paddle1 = { x: PADDLE_MARGIN, y: H / 2 - PADDLE_H / 2, w: PADDLE_W, h: PADDLE_H };
    var paddle2 = { x: W - PADDLE_MARGIN - PADDLE_W, y: H / 2 - PADDLE_H / 2, w: PADDLE_W, h: PADDLE_H };
    var ball = { x: W / 2, y: H / 2, vx: 0, vy: 0, speed: BALL_SPEED_INITIAL };

    var mouseY = H / 2;
    var touchActive = false;

    // --- Difficulty buttons ---
    var diffBtns = document.querySelectorAll('.pong-diff-btn');
    diffBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            diffBtns.forEach(function(b) { b.classList.remove('active'); });
            btn.classList.add('active');
            difficulty = btn.getAttribute('data-diff');
        });
    });

    // --- Input ---
    canvas.addEventListener('mousemove', function(e) {
        var rect = canvas.getBoundingClientRect();
        var scaleY = H / rect.height;
        mouseY = (e.clientY - rect.top) * scaleY;
    });

    canvas.addEventListener('touchmove', function(e) {
        e.preventDefault();
        touchActive = true;
        var rect = canvas.getBoundingClientRect();
        var scaleY = H / rect.height;
        mouseY = (e.touches[0].clientY - rect.top) * scaleY;
    }, { passive: false });

    canvas.addEventListener('touchstart', function(e) {
        e.preventDefault();
        touchActive = true;
        var rect = canvas.getBoundingClientRect();
        var scaleY = H / rect.height;
        mouseY = (e.touches[0].clientY - rect.top) * scaleY;
    }, { passive: false });

    // --- Start ---
    startBtn.addEventListener('click', function() {
        startGame();
    });

    function startGame() {
        scorePlayer = 0;
        scoreAi = 0;
        updateScore();
        overlay.classList.add('hidden');
        resetBall(1);
        running = true;
        if (animFrameId) cancelAnimationFrame(animFrameId);
        loop();
    }

    function showOverlay(title, message) {
        overlayTitle.textContent = title;
        overlayMessage.textContent = message;
        startBtn.textContent = 'Nochmal spielen';
        overlay.classList.remove('hidden');
        running = false;
    }

    function updateScore() {
        scorePlayerEl.textContent = scorePlayer;
        scoreAiEl.textContent = scoreAi;
    }

    // --- Ball reset ---
    function resetBall(dir) {
        ball.x = W / 2;
        ball.y = H / 2;
        ball.speed = BALL_SPEED_INITIAL;
        var angle = (Math.random() * 0.8 - 0.4); // -0.4 to 0.4 radians
        ball.vx = dir * ball.speed * Math.cos(angle);
        ball.vy = ball.speed * Math.sin(angle);
        paddle1.y = H / 2 - PADDLE_H / 2;
        paddle2.y = H / 2 - PADDLE_H / 2;
    }

    // --- AI ---
    function updateAI() {
        var diff = DIFFICULTY[difficulty];
        var targetY = ball.y;

        // Only react when ball is moving towards AI
        if (ball.vx > 0) {
            // Predict where ball will arrive
            var timeToReach = (paddle2.x - ball.x) / ball.vx;
            var predictedY = ball.y + ball.vy * timeToReach;

            // Bounce prediction
            while (predictedY < 0 || predictedY > H) {
                if (predictedY < 0) predictedY = -predictedY;
                if (predictedY > H) predictedY = 2 * H - predictedY;
            }

            targetY = predictedY;

            // Add imprecision based on difficulty
            var noise = (1 - diff.aiReaction) * 100;
            targetY += (Math.random() - 0.5) * noise;
        }

        var center = paddle2.y + PADDLE_H / 2;
        var delta = targetY - center;

        if (Math.abs(delta) > 4) {
            var move = delta > 0 ? diff.aiSpeed : -diff.aiSpeed;
            paddle2.y += move;
        }

        // Clamp
        if (paddle2.y < 0) paddle2.y = 0;
        if (paddle2.y + PADDLE_H > H) paddle2.y = H - PADDLE_H;
    }

    // --- Collision ---
    function collidePaddle(paddle) {
        if (ball.x - BALL_R < paddle.x + paddle.w &&
            ball.x + BALL_R > paddle.x &&
            ball.y + BALL_R > paddle.y &&
            ball.y - BALL_R < paddle.y + paddle.h) {

            // Calculate hit position (-1 to 1)
            var hitPos = (ball.y - (paddle.y + paddle.h / 2)) / (paddle.h / 2);
            var angle = hitPos * Math.PI / 3; // max 60 degrees

            // Increase speed
            ball.speed = Math.min(ball.speed + BALL_SPEED_INCREMENT, BALL_SPEED_MAX);

            var dir = (paddle === paddle1) ? 1 : -1;
            ball.vx = dir * ball.speed * Math.cos(angle);
            ball.vy = ball.speed * Math.sin(angle);

            // Push ball out of paddle
            if (dir === 1) {
                ball.x = paddle.x + paddle.w + BALL_R;
            } else {
                ball.x = paddle.x - BALL_R;
            }
        }
    }

    // --- Update ---
    function update() {
        // Move player paddle
        var targetY = mouseY - PADDLE_H / 2;
        paddle1.y += (targetY - paddle1.y) * 0.15;
        if (paddle1.y < 0) paddle1.y = 0;
        if (paddle1.y + PADDLE_H > H) paddle1.y = H - PADDLE_H;

        // AI
        updateAI();

        // Move ball
        ball.x += ball.vx;
        ball.y += ball.vy;

        // Top/bottom bounce
        if (ball.y - BALL_R <= 0) {
            ball.y = BALL_R;
            ball.vy = Math.abs(ball.vy);
        }
        if (ball.y + BALL_R >= H) {
            ball.y = H - BALL_R;
            ball.vy = -Math.abs(ball.vy);
        }

        // Paddle collision
        collidePaddle(paddle1);
        collidePaddle(paddle2);

        // Score
        if (ball.x < -BALL_R) {
            scoreAi++;
            updateScore();
            if (scoreAi >= WIN_SCORE) {
                showOverlay('Niederlage!', 'Der Computer gewinnt ' + scoreAi + ':' + scorePlayer + '.');
                return;
            }
            resetBall(1);
        }

        if (ball.x > W + BALL_R) {
            scorePlayer++;
            updateScore();
            if (scorePlayer >= WIN_SCORE) {
                showOverlay('Sieg!', 'Du gewinnst ' + scorePlayer + ':' + scoreAi + '!');
                return;
            }
            resetBall(-1);
        }
    }

    // --- Draw ---
    function draw() {
        // Background
        ctx.fillStyle = '#0a0a1a';
        ctx.fillRect(0, 0, W, H);

        // Center line
        ctx.setLineDash([8, 8]);
        ctx.strokeStyle = 'rgba(255,255,255,0.15)';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(W / 2, 0);
        ctx.lineTo(W / 2, H);
        ctx.stroke();
        ctx.setLineDash([]);

        // Paddles
        ctx.fillStyle = '#ecf0f1';
        ctx.shadowColor = 'rgba(233,69,96,0.4)';
        ctx.shadowBlur = 12;
        roundRect(ctx, paddle1.x, paddle1.y, paddle1.w, paddle1.h, 4);
        ctx.fill();

        ctx.shadowColor = 'rgba(127,200,248,0.4)';
        roundRect(ctx, paddle2.x, paddle2.y, paddle2.w, paddle2.h, 4);
        ctx.fill();
        ctx.shadowBlur = 0;

        // Ball
        ctx.fillStyle = '#e94560';
        ctx.shadowColor = '#e94560';
        ctx.shadowBlur = 16;
        ctx.beginPath();
        ctx.arc(ball.x, ball.y, BALL_R, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
    }

    function roundRect(ctx, x, y, w, h, r) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
    }

    // --- Game loop ---
    function loop() {
        if (!running) return;
        update();
        draw();
        animFrameId = requestAnimationFrame(loop);
    }

    // --- Initial draw ---
    draw();

})();
