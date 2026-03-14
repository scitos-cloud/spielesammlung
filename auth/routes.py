from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from extensions import db
from models import User
from auth import auth_bp


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Benutzername und Passwort erforderlich.')
            return redirect(url_for('auth.register'))
        if len(username) < 3:
            flash('Benutzername muss mindestens 3 Zeichen lang sein.')
            return redirect(url_for('auth.register'))
        if len(password) < 4:
            flash('Passwort muss mindestens 4 Zeichen lang sein.')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(username=username).first():
            flash('Benutzername bereits vergeben.')
            return redirect(url_for('auth.register'))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Registrierung erfolgreich!')
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard.index'))
        flash('Ungueltige Anmeldedaten.')
        return redirect(url_for('auth.login'))
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Abgemeldet.')
    return redirect(url_for('auth.login'))
