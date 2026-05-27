from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=bool(remember))
            user.last_login = datetime.utcnow()
            db.session.commit()
            next_page = request.args.get('next')
            flash(f'Bem-vindo(a), {user.name.split()[0]}!', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('E-mail ou senha inválidos. Tente novamente.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'student')
        student_id = request.form.get('student_id', '').strip() or None

        if not name or not email or not password:
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return render_template('auth/register.html')

        if password != confirm:
            flash('As senhas não coincidem.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Este e-mail já está cadastrado.', 'danger')
            return render_template('auth/register.html')

        user = User(name=name, email=email, role=role, student_id=student_id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f'Conta criada com sucesso! Bem-vindo(a), {name.split()[0]}!', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('auth/register.html')


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name).strip()
        current_user.bio = request.form.get('bio', '').strip()
        current_user.department = request.form.get('department', '').strip()

        new_password = request.form.get('new_password', '')
        if new_password:
            if len(new_password) < 6:
                flash('Nova senha deve ter pelo menos 6 caracteres.', 'danger')
                return redirect(url_for('auth.profile'))
            current_user.set_password(new_password)
            flash('Senha atualizada com sucesso.', 'success')

        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', user=current_user)