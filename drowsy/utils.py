"""
    drowsy.utils
    ~~~~~~~~~~~~

    Utility functions for Drowsy.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.


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
    :raise KeyError: If the ``error_messages`` dict does not contain
        the provided ``key``.
    :return: An error message with the supplied kwargs injected.
    :rtype: str

    """
    error = error_messages[key]
    msg = error if not callable(error) else error(**kwargs)
    if isinstance(msg, str):
        if callable(gettext):
            return gettext(msg, **kwargs)
        return msg % kwargs
    return msg


def get_field_by_data_key(schema, data_key):
    """Helper method to get a field from schema by data_key name.

    :param schema: Instantiated schema.
    :type schema: :class:`~marshmallow.schema.Schema`
    :param str data_key: Name as the field as it was serialized.
    :return: The schema field if found, None otherwise.
    :rtype: :class:`~marshmallow.fields.Field` or None

    """
    field = None
    if hasattr(schema, "fields_by_data_key"):
        if data_key in schema.fields_by_data_key:
            field = schema.fields_by_data_key[data_key]
    else:
        for field_name in schema.fields:
            field_data_name = schema.fields[field_name].data_key or field_name
            if field_data_name == data_key:
                field = schema.fields[field_name]
                break
    return field
