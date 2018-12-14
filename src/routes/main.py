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


def has_no_empty_params(rule):
    defaults = rule.defaults if rule.defaults is not None else ()
    arguments = rule.arguments if rule.arguments is not None else ()
    return len(defaults) >= len(arguments)


@bp.route('/admin')
@admin_required
def admin():
    import pmv
    links = []
    for rule in pmv.app.url_map.iter_rules():
        # Filter out rules we can't navigate to in a browser
        # and rules that require parameters
        if "GET" in rule.methods and has_no_empty_params(rule):
            url = url_for(rule.endpoint, **(rule.defaults or {}))
            links.append((url, rule.endpoint))

    return render_template('admin.html', title="Admin", users=db.get_users(), routes=links)
