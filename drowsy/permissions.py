"""
    drowsy.permissions
    ~~~~~~~~~~~~~~~~~~

    Classes for building permissions into an API.

    :copyright: (c) 2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""


class OpPermissionsABC(object):

    """Inherit from this class to implement permissions logic."""

    def __init__(self, **kwargs):
        """Stores any given kwargs on the permissions object."""
        self.kwargs = kwargs

    def check(self, operation, obj_data, instance=None, context=None,
              **kwargs):
        """Check if the given action is allowed.

        :param str operation: Action type. Options include ``"add"``,
            ``"remove"``, ``"create"`` for collections, and ``"set"``
            may be used as an alias for ``"add"`` in single object
            nested situations. Any actions that are part of custom
            defined field types will also need to be handled.
        :param obj_data: The user supplied data. Likely a dictionary
            for a child object.
        :param instance: An unmodified instance of the object with
            data yet to be loaded into it.
        :param context: The context of the current action. May include
            info such as the current user.
        :param kwargs: Any additional arguments that may be used for
            checking permissions.
        :raise PermissionError: Raised in cases where the provided
            action is not permissible in the current context.
        :return: `True` if no error is raised.

        """
        raise NotImplementedError


class AllowAllOpPermissions(OpPermissionsABC):

    """Allows any and all actions on a relationship."""

    def check(self, operation, obj_data, instance=None, context=None,
              **kwargs):
        """Check if the given action is allowed.

        Always returns `True`.

        :param str operation: Action type. Options include ``"add"``,
            ``"remove"``, ``"create"`` for collections, and ``"set"``
            may be used as an alias for ``"add"`` in single object
            nested situations. Any actions that are part of custom
            defined field types will also need to be handled.
        :param obj_data: The user supplied data. Likely a dictionary
            for a child object.
        :param instance: An unmodified instance of the object with
            data yet to be loaded into it.
        :param context: The context of the current action. May include
            info such as the current user.
        :param kwargs: Any additional arguments that may be used for
            checking permissions.
        :raise PermissionError: Raised in cases where the provided
            action is not permissible in the current context.
        :return: `True` if no error is raised.

        """
        return True
