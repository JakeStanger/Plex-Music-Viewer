from flask_login import UserMixin
from enum import Enum


class Permission(Enum):
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
    def __init__(self, permission_level):
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

    def has_permission(self, permission):
        return self.permissions[permission]


class User(UserMixin):
    def __init__(self, index, username, hashed_password, music_perms, movie_perms, tv_perms, is_admin):
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

    def is_authenticated(self):
        return self.authenticated

    def set_authenticated(self, auth):
        self.authenticated = auth

    def has_permission(self, permission_type, permission):
        return {
            PermissionType.MUSIC: self.music_perms.has_permission(permission),
            PermissionType.MOVIE: self.movie_perms.has_permission(permission),
            PermissionType.TV: self.tv_perms.has_permission(permission)
        }.get(permission_type)
