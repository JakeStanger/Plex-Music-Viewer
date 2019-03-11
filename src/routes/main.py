from flask import render_template, redirect, url_for, Blueprint
import database as db
from .helpers import admin_required

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
    routes = sorted([rule for rule in pmv.app.url_map.iter_rules()], key=lambda rule: rule.endpoint)

    return render_template('admin.html', title="Admin", users=db.get_users(), routes=routes)


# ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__',
#         '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__',
#         '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
#         '__subclasshook__', '__weakref__', '_argument_weights', '_converters', '_regex', '_static_weights', '_trace',
#         'alias', 'arguments', 'bind', 'build', 'build_compare_key', 'build_only', 'compile', 'defaults', 'empty',
#         'endpoint', 'get_converter', 'get_empty_kwargs', 'get_rules', 'host', 'is_leaf', 'map', 'match',
#         'match_compare_key', 'methods', 'provide_automatic_options', 'provides_defaults_for', 'redirect_to',
#         'refresh', 'rule', 'strict_slashes', 'subdomain', 'suitable_for']
