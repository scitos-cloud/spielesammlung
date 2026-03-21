import string
import random
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from extensions import db
from models import MauMauRoom, MauMauGameLog, MauMauGameLogPlayer
from maumau import maumau_bp


def generate_room_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        existing = MauMauRoom.query.filter_by(room_code=code).first()
        if not existing:
            return code


@maumau_bp.route('/')
@login_required
def lobby():
    available_rooms = MauMauRoom.query.filter_by(status='waiting').order_by(
        MauMauRoom.created_at.desc()
    ).all()
    return render_template('maumau/lobby.html', rooms=available_rooms)


@maumau_bp.route('/create', methods=['POST'])
@login_required
def create_game():
    num_ai = int(request.form.get('num_ai', 1))
    max_humans = int(request.form.get('max_humans', 1))

    total = num_ai + max_humans
    if total < 2 or total > 4:
        flash('Spieleranzahl muss zwischen 2 und 4 liegen.')
        return redirect(url_for('maumau.lobby'))

    if num_ai < 0 or num_ai > 3:
        flash('KI-Spieler muessen zwischen 0 und 3 liegen.')
        return redirect(url_for('maumau.lobby'))

    if max_humans < 1 or max_humans > 4:
        flash('Menschliche Spieler muessen zwischen 1 und 4 liegen.')
        return redirect(url_for('maumau.lobby'))

    room_code = generate_room_code()
    room = MauMauRoom(
        room_code=room_code,
        status='waiting',
        host_id=current_user.id,
        num_ai_players=num_ai,
        max_human_players=max_humans,
    )
    db.session.add(room)
    db.session.commit()

    if max_humans == 1:
        return redirect(url_for('maumau.play_game', room_code=room_code))

    return redirect(url_for('maumau.waiting_room', room_code=room_code))


@maumau_bp.route('/join', methods=['POST'])
@login_required
def join_game():
    room_code = request.form.get('room_code', '').strip().upper()
    if not room_code:
        flash('Bitte einen Raumcode eingeben.')
        return redirect(url_for('maumau.lobby'))

    room = MauMauRoom.query.filter_by(room_code=room_code).first()
    if not room:
        flash('Raum nicht gefunden.')
        return redirect(url_for('maumau.lobby'))

    if room.status != 'waiting':
        flash('Dieser Raum ist nicht mehr verfuegbar.')
        return redirect(url_for('maumau.lobby'))

    return redirect(url_for('maumau.waiting_room', room_code=room_code))


@maumau_bp.route('/waiting/<room_code>')
@login_required
def waiting_room(room_code):
    room = MauMauRoom.query.filter_by(room_code=room_code).first()
    if not room:
        flash('Raum nicht gefunden.')
        return redirect(url_for('maumau.lobby'))

    return render_template('maumau/waiting.html', room=room)


@maumau_bp.route('/game/<room_code>')
@login_required
def play_game(room_code):
    room = MauMauRoom.query.filter_by(room_code=room_code).first()
    if not room:
        flash('Raum nicht gefunden.')
        return redirect(url_for('maumau.lobby'))

    return render_template('maumau/game.html', room=room)


@maumau_bp.route('/logbook')
@login_required
def logbook():
    player_entries = MauMauGameLogPlayer.query.filter_by(
        user_id=current_user.id
    ).order_by(MauMauGameLogPlayer.id.desc()).all()

    logs = []
    for entry in player_entries:
        game_log = entry.game_log
        if game_log is None:
            continue
        game_data = game_log.get_game_data()

        all_players = MauMauGameLogPlayer.query.filter_by(
            gamelog_id=game_log.id
        ).all()
        opponents = [p for p in all_players if p.id != entry.id]

        duration_str = ''
        if game_log.started_at and game_log.ended_at:
            delta = game_log.ended_at - game_log.started_at
            minutes = int(delta.total_seconds() // 60)
            seconds = int(delta.total_seconds() % 60)
            duration_str = f'{minutes}m {seconds}s'

        logs.append({
            'date': game_log.started_at,
            'opponents': opponents,
            'result': entry.result,
            'duration': duration_str,
            'rounds': game_data.get('rounds', 0),
            'room_code': game_log.room_id,
        })

    return render_template('maumau/logbook.html', logs=logs)


@maumau_bp.route('/rules')
@login_required
def rules():
    return render_template('maumau/rules.html')
