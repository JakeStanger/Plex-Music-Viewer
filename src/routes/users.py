from json import dumps

from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
import database as db
from .decorators import admin_required

bp = Blueprint('users', __name__)


@bp.route("/login", methods=['GET', 'POST'])
def login():
    import pmv
    display_flash = False

    if request.method == 'POST':
        username = request.form.get('username').lower()
        password = request.form.get('password')
        remember = request.form.get('remember') is not None
        user = pmv.get_user(username)

        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember)
                return redirect(request.args.get('next') or url_for('main.index'))
            else:
                flash("Incorrect password", category='error')
                display_flash = True
        else:
            flash("Incorrect username", category='error')
            display_flash = True

    return render_template('accounts.html', title="Log in", force_display=display_flash)


@bp.route('/signup', methods=['POST'])
def sign_up():
    import pmv
    username = request.form['username'].lower()
    password = request.form['password']
    remember = request.form.get('remember') is not None

    db.add_user(username, generate_password_hash(password))
    # TODO Add some proper validation, redirecting for signup
    # if len(data) == 0:
    user = pmv.get_user(username)
    login_user(user, remember)
    return redirect(url_for('main.index'))
    # else:
    #   return dumps({'error': str(data[0])})


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


@bp.route('/delete_user/<string:username>', methods=['POST', 'DELETE'])
@admin_required
def delete_user(username):
    db.delete_user_by_username(username)
    db.session().commit()

    if request.method == 'POST':
        flash("User '%s' successfully deleted." % username, category='success')
        return redirect(request.referrer)
    else:
        return dumps({'message': 'User %s successfully deleted' % username}) \



@bp.route('/delete_user_by_id/<int:key>', methods=['POST', 'DELETE'])
@admin_required
def delete_user_by_id(key: int, restore=False):
    """
    Marks the user with the given ID as deleted.
    Does not actually delete the user from the database
    so that it is possible to restore them. This also
    allows for hard account suspension.
    :param key: The user ID
    :param restore: If this is set to True, undelete the user.
    :return:
    """
    db.delete_user_by_id(key, restore)

    message = "User with ID %r' successfully %s." % (key, "restored" if restore else 'deleted')
    if request.method == 'POST':
        flash(message, category='success')
        return redirect(request.referrer)
    else:
        return dumps({'message': message})


@admin_required
def restore_user_by_id(key: int):
    """
    Alias for :func:`delete_user_by_id<app.delete_user_by_id>`.
    Restore is passed as True.
    """
    delete_user_by_id(key, True)


# TODO URGENT - Rewrite this to be more dynamic - only update given values
@admin_required
def edit_user_by_id(key: int):
    form = request.form

    db.edit_user_by_id(key, form)

    db.session().commit()

    message = "User with ID %r' successfully edited." % key
    if request.method == 'POST':
        flash(message, category='success')
        return redirect(request.referrer)
    else:
        return dumps({'message': message})


@bp.route('/edit_user', methods=['POST'])
@bp.route('/edit_user/<username>', methods=['POST'])
@admin_required
def edit_user(username=None):  # TODO Add editing by username
    action = request.form.get('action')
    if action:  # If handling an AJAX request from table
        if action == 'edit':
            edit_user_by_id(request.form.get('id'))

        elif action == 'delete':
            delete_user_by_id(request.form.get('id'))

        elif action == 'restore':
            delete_user_by_id(request.form.get('id'), True)

        return dumps(request.form)
