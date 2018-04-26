"""
    drowsy.utils
    ~~~~~~~~~~~~

    Utility functions for Drowsy.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
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
    :return: An error message with the supplied kwargs injected.
    :rtype: str

    """
    error = error_messages[key]
    msg = error if not callable(error) else error(**kwargs)
    if isinstance(msg, basestring):
        if callable(gettext):
            return gettext(msg, **kwargs)
        else:
            return msg % kwargs
    return msg


def get_field_by_dump_name(schema, dump_name):
    """Helper method to get a field from schema by dump name.

    :param schema: Instantiated schema.
    :param dump_name: Name as the field as it was serialized.
    :return: The schema field if found, None otherwise.

    """
    field = None
    if hasattr(schema, "fields_by_dump_to"):
        if dump_name in schema.fields_by_dump_to:
            field = schema.fields_by_dump_to[dump_name]
    else:
        for field_name in schema.fields:
            if schema.fields[field_name].dump_to == dump_name:
                field = schema.fields[field_name]
                break
    return field
