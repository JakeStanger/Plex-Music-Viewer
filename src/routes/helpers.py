import json
from functools import wraps
from flask import jsonify, request, make_response
from jsonpickle import encode
from flask_login import login_required
from werkzeug.local import LocalProxy
import database as db
from helper import throw_error, get_current_user


def require_permission(permission: db.Permission,
                       get_user_func: LocalProxy = get_current_user):
    """
    Decorating a function with this ensures the current
    user has db.Permission to load to page.
    :param permission:
    :param get_user_func:
    :return:
    """

    def permission_wrapper(func):
        @login_required
        @wraps(func)
        def permission_inner(*args, **kwargs):
            user = get_user_func()
            if user.has_permission(permission):
                return func(*args, **kwargs)
            else:
                # logger.info('User %s attempted to send request but did not have permission %s.'
                #             % (user.username, permission))
                throw_error(401, "Missing permission <b>%s</b>." % permission)

        return permission_inner

    return permission_wrapper


def admin_required(func, get_user=get_current_user):
    @login_required
    @wraps(func)
    def admin_wrapper(*args, **kwargs):
        user = get_user()
        if not user.is_admin:
            # logger.info("User %s attempted to send an admin-only request without admin privileges.")
            throw_error(401, "Only administrators can do this.")

        return func(*args, **kwargs)

    return admin_wrapper


def get_json_response(obj, max_depth: int = 2, append: dict = None):
    encoded = encode(obj, unpicklable=False, max_depth=max_depth)
    if append:
        encoded = json.loads(encoded)
        for key in append:
            encoded[key] = append[key]
        encoded = encode(encoded, unpicklable=False, max_depth=2)

    response = make_response(encoded, 200)
    response.mimetype = 'application/json'
    return response


def wants_html():
    return 'text/html' in request.accept_mimetypes
