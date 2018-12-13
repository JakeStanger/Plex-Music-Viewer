from flask import render_template, redirect, url_for, Blueprint
import database as db
from .decorators import admin_required

bp = Blueprint('main', __name__)


@bp.route('/error')
def error():
    return render_template('error.html', code=str(402), message="You do not have permission to view this page.")


@bp.route('/')
def index():
    return redirect(url_for('music.artist'))


@bp.route('/admin')
@admin_required
def admin():
    return render_template('admin.html', title="Admin", users=db.get_users())
