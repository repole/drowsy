"""
    drowsy.exc
    ~~~~~~~~~~

    Exceptions for Drowsy.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""


class DrowsyError(Exception):

    """Exception that contains a simple message attribute."""

    def __init__(self, code, message, **kwargs):
        """Initializes a new error.

        :param str code: Error code for easier lookup.
        :param str message: Description of the error.
        :param dict kwargs: Any additional arguments may be stored along
            with the message as well.

        """
        self.code = code
        self.message = message
        self.kwargs = kwargs
        super(DrowsyError, self).__init__()


class UnprocessableEntityError(DrowsyError):

    """Exception for when provided data is unable to be deserialized."""

    def __init__(self, code, message, errors, **kwargs):
        """Initializes a new unprocessable entity error.

        :param str code: Error code for easier lookup.
        :param str message: Description of the error.
        :param dict errors: A field by field breakdown of errors.
        :param dict kwargs: Any additional arguments may be stored along
            with the message and errors as well.

        """
        self.errors = errors
        super(UnprocessableEntityError, self).__init__(code, message, **kwargs)


class BadRequestError(DrowsyError):

    """Exception for when a request is unable to be processed."""

    pass


class MethodNotAllowedError(DrowsyError):

    """Error for when a request is made with an unsupported method."""

    pass


class ResourceNotFoundError(DrowsyError):

    """Exception for when a requested resource cannot be found."""

    pass


class ParseError(DrowsyError):

    """Generic exception class for parsing errors."""

    pass


class OffsetLimitParseError(ParseError):

    """Generic exception class for offset or limit parsing errors."""

    pass


class FilterParseError(ParseError):

    """Generic exception class for filter parsing errors."""

    pass

