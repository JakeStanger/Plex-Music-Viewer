from flask_login import UserMixin
from enum import Enum


class Permission(Enum):
    """
    Based on the Unix octal permissions system except it goes to 63 instead of 7.
    A permission level is given to a user based on the sum of the below values.

    For example: `45 = 32 + 8 + 4 + 1`

    So a permission level of 45 would grant permission to delete, upload, edit and view.
    A user with level 45 would *not* have permission to transcode, edit or view.

    """
    DELETE = 32
    TRANSCODE = 16
    UPLOAD = 8
    EDIT = 4
    DOWNLOAD = 2
    VIEW = 1


class PermissionType(Enum):
    MUSIC = 0
    MOVIE = 1
    TV = 2


class PermissionSet:
    """
    A representation of the user's permissions.

    Avoids having to calculate based on the number value each time.
    Instead you can simply check if the user has a specific permission.
    """
    def __init__(self, permission_level: int):
        self.permission_level = permission_level

        self.permissions = {}
        for p in Permission:
            if permission_level >= p.value:
                self.permissions[p] = True
                permission_level -= p.value
            else:
                self.permissions[p] = False

    def __repr__(self):
        return "<%r>" % self.permission_level

    def has_permission(self, permission: Permission) -> bool:
        return self.permissions[permission]


class User(UserMixin):
    def __init__(self, index: int, username: str, hashed_password: str,
                 music_perms: int, movie_perms: int, tv_perms: int, is_admin):
        self.index = index

        # Aliases
        self.id = username
        self.username = username

        self.hashed_password = hashed_password
        self.authenticated = False

        self.music_perms = PermissionSet(music_perms)
        self.movie_perms = PermissionSet(movie_perms)
        self.tv_perms = PermissionSet(tv_perms)
        self.is_admin = is_admin == 1

    def __repr__(self):
        return "<%d - %s>" % (self.index, self.id)

    def is_authenticated(self) -> bool:
        return self.authenticated

    def set_authenticated(self, auth: bool):
        self.authenticated = auth

    def has_permission(self, permission_type: PermissionType, permission: Permission):
        return {
            PermissionType.MUSIC: self.music_perms.has_permission(permission),
            PermissionType.MOVIE: self.movie_perms.has_permission(permission),
            PermissionType.TV: self.tv_perms.has_permission(permission)
        }.get(permission_type)
