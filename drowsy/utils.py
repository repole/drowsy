"""
    drowsy.utils
    ~~~~~~~~~~~~

    Utility functions for Drowsy.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from marshmallow.compat import basestring


def get_error_message(error_messages, key, gettext=None, **kwargs):
    """Get an error message based on a key name.

    If the error message is a callable, kwargs are passed
    to that callable.

    Assuming the resulting error message is a string,
    ``self.gettext`` will be passed that string along with any
    kwargs to potentially translate and fill in any template
    variables.

    :param dict error_messages: A dictionary of string or callable
        errors mapped to key names.
    :param str key: Key used to access the error messages dict.
    :param gettext: Optional callable that may be used to translate
        any error messages.
    :type gettext: callable or None
    :param dict kwargs: Any additional arguments that may be passed
        to a callable error message, or used to translate and/or
        format an error message string.

    """
    error = error_messages[key]
    msg = error if not callable(error) else error(**kwargs)
    if isinstance(msg, basestring):
        if callable(gettext):
            return gettext(msg, **kwargs)
        else:
            return msg % kwargs
    return msg
