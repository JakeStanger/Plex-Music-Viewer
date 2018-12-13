from functools import wraps

from flask_login import login_required
from werkzeug.local import LocalProxy
import database as db
from helper import throw_error, get_current_user


# @login_required
def require_permission(permission: db.Permission,
                       get_user_func: LocalProxy = get_current_user):  # TODO Require login here rather than on all functions
    """
    Decorating a function with this ensures the current
    user has db.Permission to load to page.
    :param permission:
    :param get_user_func:
    :return:
    """

    def permission_wrapper(func):
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


# @login_required
def admin_required(func, get_user=get_current_user):
    @wraps(func)
    def admin_wrapper(*args, **kwargs):
        user = get_user()
        if not user.is_admin:
            # logger.info("User %s attempted to send an admin-only request without admin privileges.")
            throw_error(401, "Only administrators can do this.")

        return func(*args, **kwargs)

    return admin_wrapper
