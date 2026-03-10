from flask import Flask, render_template, url_for, redirect, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError, DataRequired, EqualTo
from models import db, bcrypt, User, Ticket
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
import os
import random

load_dotenv()

app = Flask(__name__)
bcrypt.init_app(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Secret key loaded from environment variable so it's never hardcoded in source code (OWASP A02)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-dev-key-change-in-production')

# Session cookie settings to protect against common attacks (OWASP A02)
app.config['SESSION_COOKIE_HTTPONLY'] = True   # Stops JavaScript from reading the session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Helps prevent cross-site request forgery
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'  # HTTPS only in production

db.init_app(app)
CSRFProtect(app)  # Makes csrf_token() available in all templates for non-form POST requests

# Rate limiter using the requester's IP address to track attempts (OWASP A07)
limiter = Limiter(get_remote_address, app=app, default_limits=[])

login_manager = LoginManager(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Add security headers to every response to protect against common browser-based attacks (OWASP A05)
@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'  # Stops the app being embedded in iframes (clickjacking)
    response.headers['X-Content-Type-Options'] = 'nosniff'  # Stops browsers guessing file types
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'  # Limits URL info shared with third parties
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'  # Forces HTTPS on live deployment
    # Only allow scripts and styles from this app and the Bootstrap CDN
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' cdn.jsdelivr.net; "
        "style-src 'self' cdn.jsdelivr.net; "
        "font-src 'self' cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "object-src 'none';"
    )
    return response

class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    confirm_password = PasswordField(
            'Confirm Password',
            validators=[
                InputRequired(),
                EqualTo('password', message='Passwords must match')
            ],
            render_kw={"placeholder": "Confirm Password"}
        )
    
    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            flash('Username already exists. Please choose a different one or log in.', 'danger')
            raise ValidationError(
                'That username already exists. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=8, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')

class ChangePasswordForm(FlaskForm):
    """Form for updating user passwords securely."""
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired()])
    confirm_password = PasswordField("Confirm New Password", validators=[
        DataRequired(), EqualTo("new_password", message="Passwords must match")
    ])
    submit = SubmitField("Update Password")

def bulk_seed():
    # Creating users
    if User.query.count() == 0:
        admin = User(username='admin', password=bcrypt.generate_password_hash('admin123').decode('utf-8'), role='admin')
        users = [
                User(
                    username=f"user{i}",
                    password=bcrypt.generate_password_hash(f"password{i}"),
                    role="user"
                )
                for i in range(1, 11)
            ]
        db.session.bulk_save_objects(users)        
        db.session.add(admin)
        db.session.commit()

    users = User.query.all()

    # Creating tickets
    priorities = ["High", "Medium", "Low"]
    statuses = ["Open", "In Progress", "Resolved"]
    tickets = [
        Ticket(
            title=f"Sample Ticket {i}",
            description=f"This is the description for ticket {i}.",
            priority=random.choice(priorities),
            status=random.choice(statuses),
            user_id=random.choice(users).id
        )
        for i in range(1, 11)
    ]
    db.session.bulk_save_objects(tickets)
    db.session.commit()

@app.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    query = Ticket.query.filter_by(is_deleted=False)
    if not current_user.is_admin():
        query = query.filter_by(user_id=current_user.id)

    status = request.args.get('status')
    priority = request.args.get('priority')

    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)

    tickets = query.all()
    return render_template('dashboard.html', tickets=tickets)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])  # Block brute force attacks - max 5 login attempts per minute (OWASP A07)
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if not user or not bcrypt.check_password_hash(user.password, form.password.data):
            flash('Invalid username or password. Please try again.', 'danger')
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
    return render_template('login.html', form=form)

@app.errorhandler(429)
def too_many_requests(_):
    # Shown when a user exceeds 5 login attempts in a minute
    flash('Too many login attempts. Please wait a minute before trying again.', 'danger')
    return render_template('login.html', form=LoginForm()), 429


@app.route('/login-success')
@login_required
def loginSuccess():
    return render_template('login-success.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('Logout successful!', 'success')
    return redirect(url_for('login'))


@ app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/new_ticket', methods=['GET', 'POST'])
@login_required
def new_ticket():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        priority = request.form['priority']

        new_ticket = Ticket(title=title, description=description, priority=priority, user_id=current_user.id)
        db.session.add(new_ticket)
        db.session.commit()

        flash('Ticket created successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('new_ticket.html')


@app.route('/edit_ticket/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def edit_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    # Ensure only the owner or admin can edit (OWASP A01)
    if not (current_user.is_admin() or ticket.user_id == current_user.id):
        abort(403)

    if request.method == 'POST':
        ticket.title = request.form['title']
        ticket.description = request.form['description']
        # Only allow admins to update status
        if current_user.is_admin():
            ticket.status = request.form.get('status', ticket.status)

        db.session.commit()
        flash('Ticket updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_ticket.html', ticket=ticket)

@app.route('/delete_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def delete_ticket(ticket_id):
    """Allows users to delete their own tickets and admins to delete any ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)

    if current_user.is_admin() or ticket.user_id == current_user.id:
        ticket.is_deleted = True  # Soft delete so moderation and audits can still take place
        db.session.commit()
        flash("Ticket successfully deleted!", "success")
    else:
        flash("You do not have permission to delete this ticket.", "danger")

    return redirect(url_for('dashboard'))

@app.route('/account_settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Incorrect current password.", "danger")
            return redirect(url_for("account_settings"))

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash("Password updated successfully.", "success")
        return redirect(url_for("account_settings"))
    return render_template("account_settings.html", form=form, user=current_user)

@app.route('/view_ticket/<int:ticket_id>')
@login_required
def view_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not (current_user.is_admin() or ticket.user_id == current_user.id):
        abort(403)  # Proper 403 instead of silent redirect (OWASP A01)
    return render_template('view_ticket.html', ticket=ticket)

# Custom error pages so users see a message instead of a HTTP error (OWASP A01/A05)
@app.errorhandler(403)
def forbidden(_):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found(_):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(_):
    return render_template('500.html'), 500


@app.route('/admin/users')
@login_required
def admin_users():
    # Only admins can access this page (OWASP A01)
    if not current_user.is_admin():
        abort(403)
    query = User.query.filter_by(is_deleted=False)
    role = request.args.get('role')
    if role in ('user', 'admin'):
        query = query.filter_by(role=role)
    users = query.all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/<int:user_id>/toggle_role', methods=['POST'])
@login_required
def toggle_role(user_id):
    if not current_user.is_admin():
        abort(403)
    user = User.query.get_or_404(user_id)
    # Prevent admins from demoting themselves
    if user.id == current_user.id:
        flash("You can't change your own role.", 'warning')
        return redirect(url_for('admin_users'))
    user.role = 'user' if user.role == 'admin' else 'admin'
    db.session.commit()
    flash(f"{user.username}'s role updated to {user.role}.", 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin():
        abort(403)
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You can't delete your own account here.", 'warning')
        return redirect(url_for('admin_users'))
    user.is_deleted = True  # Soft delete keeps the audit trail intact
    db.session.commit()
    flash(f"{user.username} has been removed.", 'success')
    return redirect(url_for('admin_users'))


if __name__ == "__main__":
    with app.app_context():
        # db.drop_all()
        db.create_all()
        if User.query.count() == 0 and Ticket.query.count() == 0:
            bulk_seed()
    app.run()