import random
import uuid
from flask import render_template, request, jsonify, session
from flask_login import login_required
from hangman import hangman_bp
from hangman.words import WORDS

MAX_WRONG = 6
games = {}


def get_display(word, guessed):
    return [c if c in guessed else ('_' if c.isalpha() else c) for c in word]


@hangman_bp.route('/')
@login_required
def index():
    return render_template('hangman/index.html')


@hangman_bp.route('/api/new-game', methods=['POST'])
@login_required
def new_game():
    data = request.get_json(silent=True) or {}
    lang = data.get('lang', 'de')
    if lang not in WORDS:
        lang = 'de'
    word_list = WORDS[lang]
    word = random.choice(word_list).upper()
    game_id = str(uuid.uuid4())
    games[game_id] = {
        'word': word,
        'guessed': [],
        'wrong': 0,
        'status': 'playing',
        'lang': lang,
    }
    session['hangman_game_id'] = game_id
    return jsonify({
        'game_id': game_id,
        'display': get_display(word, []),
        'guessed': [],
        'wrong': 0,
        'max_wrong': MAX_WRONG,
        'status': 'playing',
        'lang': lang,
    })


@hangman_bp.route('/api/guess', methods=['POST'])
@login_required
def guess():
    data = request.get_json()
    game_id = data.get('game_id') or session.get('hangman_game_id')
    letter = data.get('letter', '').upper()

    if not game_id or game_id not in games:
        return jsonify({'error': 'Spiel nicht gefunden'}), 404

    game = games[game_id]

    if game['status'] != 'playing':
        return jsonify({'error': 'Spiel bereits beendet'}), 400

    if not letter or len(letter) != 1 or not letter.isalpha():
        return jsonify({'error': 'Ungueltiger Buchstabe'}), 400

    if letter in game['guessed']:
        return jsonify({'error': 'Buchstabe bereits geraten'}), 400

    game['guessed'].append(letter)

    if letter not in game['word']:
        game['wrong'] += 1

    display = get_display(game['word'], game['guessed'])

    if '_' not in display:
        game['status'] = 'won'
    elif game['wrong'] >= MAX_WRONG:
        game['status'] = 'lost'

    return jsonify({
        'game_id': game_id,
        'display': display,
        'guessed': game['guessed'],
        'wrong': game['wrong'],
        'max_wrong': MAX_WRONG,
        'status': game['status'],
        'word': game['word'] if game['status'] == 'lost' else None,
        'correct': letter in game['word'],
        'lang': game['lang'],
    })


@hangman_bp.route('/api/state/<game_id>')
@login_required
def state(game_id):
    if game_id not in games:
        return jsonify({'error': 'Spiel nicht gefunden'}), 404

    game = games[game_id]
    display = get_display(game['word'], game['guessed'])

    return jsonify({
        'game_id': game_id,
        'display': display,
        'guessed': game['guessed'],
        'wrong': game['wrong'],
        'max_wrong': MAX_WRONG,
        'status': game['status'],
        'word': game['word'] if game['status'] == 'lost' else None,
        'lang': game['lang'],
    })
