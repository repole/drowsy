"""
    drowsy.parser
    ~~~~~~~~~~~~~

    Functions for parsing query info from url parameters.

    :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from drowsy.utils import get_error_message
from drowsy.exc import (
    ParseError, FilterParseError, OffsetLimitParseError,
    MISSING_ERROR_MESSAGE)
from drowsy.log import Loggable
import json


class SortInfo(Loggable):
    """Used to transport info regarding sorts around."""

    def __init__(self, attr=None, direction="ASC"):
        """Instantiates a SortInfo object.

        :param str attr: Name of the attr to be sorted on.
        :param str direction: Must be ``"ASC"`` or ``"DESC"``.
        :raise ValueError: If ``direction`` is not ``"ASC"``,
            ``"DESC"``, or ``None``.
        :raise TypeError: If any of the provided parameters
            are not of the specified type.

        """
        if not isinstance(attr, str):
            raise TypeError("attr must be a string.")
        if not isinstance(direction, str):
            raise TypeError("direction must be a string.")
        if direction != "DESC" and direction != "ASC":
            raise ValueError("direction must be ASC or DESC.")
        self.attr = attr
        self.direction = direction


class OffsetLimitInfo(Loggable):
    """Used to transport info regarding offsets and limits around."""

    def __init__(self, offset=None, limit=None):
        """Instantiates a OffsetLimitInfo object.

        :param offset: Offset to be applied.
        :type offset: int or None
        :param limit: Limit to be applied.
        :type limit: int or None
        :raise ValueError: If ``offset`` or ``limit`` is not a positive
            number or ``None``.
        :raise TypeError: If any of the provided parameters
            are not of the specified type.

        """
        self._offset = None
        self._limit = None
        self.offset = offset
        self.limit = limit

    @property
    def offset(self):
        """Get an offset value.

        :return: An offset value.
        :rtype: int or None

        """
        return self._offset

    @offset.setter
    def offset(self, value):
        """Set an offset value.

        :param value: The value of an offset. If not None, must be a
            non negative int.
        :type value: int or None
        :raise TypeError: If a non int or None value is given.
        :raise ValueError: If the provided value is a negative integer.
        :return: None
        :rtype: None

        """
        if not isinstance(value, int) and value is not None:
            raise TypeError("offset must be an int or None.")
        if value is not None and value < 0:
            raise ValueError("offset must be a positive value.")
        self._offset = value

    @property
    def limit(self):
        """Get a limit value.

        :return: An limit value.
        :rtype: int or None

        """
        return self._limit

    @limit.setter
    def limit(self, value):
        """Set a limit value.

        :param value: The value of a limit. If not None, must be a
            non negative int.
        :type value: int or None
        :raise TypeError: If a non int or None value is given.
        :raise ValueError: If the provided value is a negative integer.
        :return: None
        :rtype: None

        """
        if not isinstance(value, int) and value is not None:
            raise TypeError("limit must be an int or None.")
        if value is not None and value < 0:
            raise ValueError("limit must be a positive value.")
        self._limit = value


class SubfilterInfo(OffsetLimitInfo):

    """Object used to transport info regarding subqueries around."""

    def __init__(self, offset=None, limit=None, filters=None, sorts=None):
        """Instantiates a SubfilterInfo object.

        :param offset: Offset to be applied.
        :type offset: int or None
        :param limit: Limit to be applied.
        :type limit: int or None
        :param filters: Filters to be applied.
        :type filters: dict or None
        :param sorts: Any sorts that are to be applied.
        :type sorts: list of SortInfo or None
        :raise ValueError: If ``offset`` or ``limit`` is not a positive
            number or ``None``.
        :raise TypeError: If any of the provided parameters
            are not of the specified type.

        """
        self._filters = None
        self._sorts = None
        self.filters = filters
        self.sorts = sorts
        super(SubfilterInfo, self).__init__(offset, limit)

    @property
    def filters(self):
        """Get the filters to be applied to a subresource.

        :return: A dictionary of filters for a subresource.
        :rtype: dict or None

        """
        return self._filters

    @filters.setter
    def filters(self, value):
        """Set an offset value.

        :param value: Filters to be applied to the subresource.
        :type value: dict or None
        :raise TypeError: If a non dict or None value is given.
        :return: None
        :rtype: None

        """
        if not isinstance(value, dict) and value is not None:
            raise TypeError("filters must be a dict or None.")
        self._filters = value

    @property
    def sorts(self):
        """Get the sorts to be applied to a subresource.

        :return: A collection of sorts for a subresource.
        :rtype: list or None

        """
        return self._sorts

    @sorts.setter
    def sorts(self, value):
        """Set the sorts to be used for the subresource.

        :param value: Sorts to be applied to the subresource.
        :type value: dict or None
        :raise TypeError: If a non list or None value is given.
        :return: None
        :rtype: None

        """
        if not isinstance(value, list) and value is not None:
            raise TypeError("sorts must be a list or None.")
        self._sorts = value


class QueryParamParser(Loggable):

    """Utility class used to parse query parameters."""

    default_error_messages = {
        "invalid_limit_value": ("The limit provided (%(limit)s) is not a "
                                "non negative integer."),
        "invalid_sublimit_value": ("The limit (%(limit)s) provided for the "
                                   "subresource (%(subresource)s) is not a "
                                   "non negative integer."),
        "invalid_offset_value": ("The offset provided (%(offset)s) is not a "
                                 "non negative integer."),
        "invalid_suboffset_value": ("The offset (%(offset)s) provided for the "
                                    "subresource (%(subresource)s) is not a "
                                    "non negative integer."),
        "limit_too_high": ("The limit provided (%(limit)s) is greater than "
                           "the max page size allowed (%(max_page_size)s)."),
        "invalid_page_value": ("The page value provided (%(page)s) is not a "
                               "positive integer."),
        "page_no_max": "Page greater than 1 provided without a page max size.",
        "page_negative": "Page number can not be less than 1.",
        "invalid_subsorts_value": ("The sorts provided (%(sort)s) for the "
                                   "subresource (%(subresource)s) are not "
                                   "valid."),
        "invalid_complex_filters": ("The complex filters query value for "
                                    "%(qparam)s must be set to a valid json "
                                    "dict."),
        "invalid_subresource_path": ("The subresource path provided "
                                     "(%(subresource_path)s) is not valid.")
    }

    def __init__(self, query_params=None, error_messages=None, context=None):
        """Sets up error messages, translations, and query params.

        :param query_params: Query params potentially containing
            filters, embeds, fields, and sorts.
        :type query_params: dict or None
        :param error_messages: Optional dictionary of error messages,
            useful if you want to override the default errors.
        :type error_messages: dict or None
        :param context: Optional dictionary of context information.
            If error messages should be translated, context should
            include a ``"gettext"`` key set to a callable that takes
            in a string and any kwargs and returns a translated string.
        :type context: dict, callable, or None

        """
        self.query_params = query_params or {}
        self._context = context
        # Set up error messages
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    @property
    def context(self):
        """Return the context for this request.

        :rtype: dict, callable, or None

        """
        if callable(self._context):
            return self._context()
        else:
            return self._context or {}

    @context.setter
    def context(self, val):
        """Set context to the provided value.

        :param val: Used to set the current context value.
        :type val: dict, callable, or None

        """
        self._context = val

    def fail(self, key, **kwargs):
        """Raises an exception based on the ``key`` provided.

        :param str key: Failure type, used to choose an error message.
        :param kwargs: Any additional arguments that may be used for
            generating an error message.
        :raise FilterParseError: Raised in cases where there was an
            issue parsing a filter.
        :raise OffsetLimitParseError: Raised in cases where there was
            an issue parsing the offset, limit, or page value.
        :raise ParseError: Raised in all other cases.

        """
        offset_limit_parse_keys = {
            "invalid_limit_value", "limit_too_high", "invalid_offset_value",
            "invalid_page_value", "page_no_max", "page_negative",
            "invalid_sublimit_value", "invalid_suboffset_value"}
        if key in offset_limit_parse_keys:
            raise OffsetLimitParseError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs)
        elif key == "invalid_complex_filters":
            raise FilterParseError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs)
        else:
            raise ParseError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs)

    def _parse_sorts_helper(self, sorts):
        """Reusable code for parsing sorts from a string.

        :param sorts: A comma split string with attrnames and
            sort directions as + or -. If neither + or - is
            provided, ASC is assumed.
            As an example, sorts might look like:
            ``"+artist.name,-album.name"``.
        :return: A list of sorts to be applied to a result.
        :rtype: list of :class:`SortInfo`

        """
        result = []
        split_sorts = sorts.split(",")
        for sort in split_sorts:
            direction = "ASC"
            attr_name = sort
            if sort.startswith("-"):
                attr_name = sort[1:]
                direction = "DESC"
            result.append(SortInfo(attr=attr_name, direction=direction))
        return result

    def _get_error_message(self, key, **kwargs):
        """Get an error message based on a key name.

        If the error message is a callable, kwargs are passed
        to that callable.

        Assuming the resulting error message is a string,
        if ``self.context`` includes a ``"gettext"`` callable, it
        will be passed that string along with any kwargs to potentially
        translate and fill in any template variables.

        :param str key: Key used to access the error messages dict.
        :param dict kwargs: Any additional arguments that may be passed
            to a callable error message, or used to translate and/or
            format an error message string.
        :raise AssertionError: When the ``self.error_message`` dict
            does not contain the provided ``key``.
        :return: An error message
        :rtype: str

        """
        try:
            return get_error_message(
                error_messages=self.error_messages,
                key=key,
                gettext=self.context.get("gettext", None),
                **kwargs)
        except KeyError:
            class_name = self.__class__.__name__
            msg = MISSING_ERROR_MESSAGE.format(class_name=class_name, key=key)
            raise AssertionError(msg)

    def parse_fields(self, fields_query_name="fields"):
        """Parse from query params the fields to include in the result.

        :param str fields_query_name: The name of the key used to check
            for fields in the provided ``query_params``.
        :return: A list of fields to be included in the response.
        :rtype: list of str

        """
        fields = self.query_params.get(fields_query_name)
        if fields:
            return fields.split(",")
        else:
            return []

    def parse_embeds(self, embeds_query_name="embeds"):
        """Parse sub-resource embeds from query params.

        :param str embeds_query_name: The name of the key used to check
            for an embed in the provided ``query_params``.
        :return: A list of embeds to include in the response.
        :rtype: list of str

        """
        embeds = self.query_params.get(embeds_query_name)
        if embeds:
            return embeds.split(",")
        else:
            return []

    def parse_offset_limit(self, page_max_size=None, page_query_name="page",
                           offset_query_name="offset",
                           limit_query_name="limit", strict=True):
        """Parse offset and limit from the provided query params.

        :param page_max_size: If page is provided, ``page_max_size``
            limits the number of results returned. Otherwise, if using
            limit and offset values from the ``query_params``,
            ``page_max_size`` sets a max number of records to allow.
        :type page_max_size: int or None
        :param str page_query_name: The name of the key used to check
            for a page value in the provided ``query_params``. If page
            is provided, it is used along with the ``page_max_size`` to
            determine the offset that should be applied to the query. If
            a page number  other than 1 is provided, a ``page_max_size``
            must also be provided.
        :param str offset_query_name: The name of the key used to check
            for an offset value in the provided ``query_params``.
        :param str limit_query_name: The name of the key used to check
            for a limit value in the provided ``query_params``.
        :param strict: If ``True``, exceptions will be raised for
            invalid input. Otherwise, invalid input will be ignored.
        :raise OffsetLimitParseError: Applicable if using strict mode
            only. If the provided limit is greater than page_max_size,
            or an invalid page, offset, or limit value is provided, then
            an :exc:`OffsetLimitParseError` is raised.
        :return: An offset and limit value for this query.
        :rtype: :class:`OffsetLimitInfo`

        """
        # parse limit
        limit = page_max_size
        if limit_query_name is not None:
            if self.query_params.get(limit_query_name):
                try:
                    limit = int(self.query_params.get(limit_query_name))
                    if limit < 0:
                        raise ValueError
                except (ValueError, TypeError):
                    if strict:
                        self.fail(
                            key="invalid_limit_value",
                            limit=self.query_params.get(limit_query_name))
        # parse page
        page = self.query_params.get(page_query_name, None)
        if page is not None:
            try:
                page = int(page)
                if page < 1:
                    raise ValueError
            except (ValueError, TypeError):
                page = None
                if strict:
                    self.fail(
                        "invalid_page_value",
                        page=self.query_params.get(page_query_name, None))
            if page > 1 and page_max_size is None and limit is None:
                page = None
                if strict:
                    self.fail("page_no_max")
        # defaults
        offset = 0
        if offset_query_name is not None:
            if self.query_params.get(offset_query_name):
                try:
                    offset = int(self.query_params.get(offset_query_name))
                    if offset < 0:
                        raise ValueError
                except (ValueError, TypeError):
                    offset = 0
                    if strict:
                        self.fail(
                            "invalid_offset_value",
                            offset=self.query_params.get(offset_query_name))
        if page_max_size and limit > page_max_size:
            # make sure an excessively high limit can't be set
            limit = page_max_size
            if strict:
                self.fail("limit_too_high",
                          limit=self.query_params.get(limit_query_name, None),
                          max_page_size=page_max_size)
        if page is not None and page > 1:
            if limit is not None and page_max_size is None:
                page_max_size = limit
            offset = (page - 1) * page_max_size
        return OffsetLimitInfo(limit=limit, offset=offset)

    def parse_sorts(self, sort_query_name="sort"):
        """Parse sorts from provided the query params.

        :param str sort_query_name: The name of the key used to check
            for sorts in the provided ``query_params``.
        :return: The sorts that should be applied.
        :rtype: list of :class:`SortInfo`

        """
        if sort_query_name in self.query_params:
            return self._parse_sorts_helper(self.query_params[sort_query_name])
        return []


class ModelQueryParamParser(QueryParamParser):

    """Param parser with added ability to parse MQLAlchemy filters."""

    def _parser_helper(self, parse_type, subqueries, key, key_parts, key_value,
                       subkey_name, strict=True):
        """Used to help parse offset, limit, and sorts.

        The logic is overwhelmingly similar, so rather than repeat
        code, it's broken out into this helper function.

        :param str parse_type: Can be one of three values:
            ``"limit"``, ``"offset"``, or ``"sorts"``.
        :param dict subqueries: Holds :class:`SubfilterInfo` in a dict
            where each key is a resource path.
        :param str key: The name of this query parameter, for example:
            ``tracks.playlists._limit_``
        :param list key_parts: The above key split into a list by ``.``.
        :param key_value: The value of the query parameter for the
            provided key.
        :param str subkey_name: The name of the portion of the key
            that we're searching for. By default, this can be
            ``"_limit_"``, ``"_offset_"``, or ``"_sorts_"``.
        :param bool strict: If ``True``, exceptions will be raised for
            invalid input. Otherwise, invalid input will be ignored.
        :raise OffsetLimitParseError: Raised in cases where there was
            an issue parsing an offset or limit if ``strict`` is
            ``True``.
        :raise ParseError: Raised if ``strict`` is ``True`` and
            the ``parse_type`` is ``"sorts"`` and there is an issue
            parsing.
        :return: None, but the subqueries parameter may be modified.
        :rtype: None

        """
        subquery_path_parts = []
        value = key_value
        try:
            if parse_type == "limit" or parse_type == "offset":
                value = int(key_value)
            elif parse_type == "sorts":
                value = self._parse_sorts_helper(key_value)
        except (ValueError, TypeError):
            if strict:
                code = "invalid_sub" + parse_type + "_value"
                kwargs = {
                    parse_type: key_value,
                    "subresource": key
                }
                self.fail(code, **kwargs)
            return
        while key_parts:
            key_part = key_parts.pop(0)
            if not key_part == subkey_name:
                subquery_path_parts.append(key_part)
            else:
                if key_parts:
                    if strict:
                        self.fail(
                            "invalid_subresource_path",
                            subresource_path=key)
                    else:
                        break
                else:
                    subitem_path = ".".join(subquery_path_parts)
                    if not isinstance(
                            subqueries.get(subitem_path),
                            SubfilterInfo):
                        subqueries[subitem_path] = SubfilterInfo()
                    setattr(subqueries[subitem_path], parse_type, value)

    def parse_subfilters(self, subquery_name="_subquery_",
                         sublimit_name="_limit_", suboffset_name="_offset_",
                         subsorts_name="_sorts_", strict=True):
        """Parse nested resource subfilters, limits, offsets, and sorts.

        Note that subquery parsing does limited checking on the
        validity of the subquery itself.

        Given a query param "album.artist._subquery_.tracks.track_id"
        with value "5", the resulting subfilters returned would be:

        .. code-block:: python

            result = {
                "album.artist": SubfilterInfo(
                    filters={
                        "$and": ["tracks.track_id": {"eq": 5}]
                    }
                )
            }

        :param str subquery_name: The name of the key used to check
            for a subquery value in the provided ``query_params``.
        :param str sublimit_name: The name of the key used to check
            for a sublimit value in the provided ``query_params``.
        :param str suboffset_name: The name of the key used to check
            for a suboffset value in the provided ``query_params``.
        :param str subsorts_name: The name of the key used to check
            for a subsorts value in the provided ``query_params``.
        :param bool strict: If ``True``, exceptions will be raised for
            invalid input. Otherwise, invalid input will be ignored.
        :raise FilterParseError: Malformed complex queries or
            invalid ``query_params`` will result in an
            :exc:`~drowsy.exc.FilterParseError` being raised if
            ``strict`` is ``True``.
        :raise OffsetLimitParseError: Raised in cases where there was
            an issue parsing an offset or limit if ``strict`` is
            ``True``.
        :raise ParseError: Raised if ``strict`` is ``True`` and
            there is an issue parsing the provided sorts for a
            subfilter.
        :return: A dictionary containing subqueries that can be passed
            to mqlalchemy for query filtering.
        :rtype: dict of str, SubfilterInfo

        """
        subqueries = {}
        for key in self.query_params.keys():
            value = self.query_params[key]
            key_parts = key.split(".")
            subquery_path_parts = []
            sub_attr_path_parts = []
            subitem_found = False
            subitem_path = None
            if key.find(subquery_name) > -1:
                # walk down the subquery to see how it ends
                while key_parts:
                    key_part = key_parts.pop(0)
                    if not key_part == subquery_name:
                        if subitem_found:
                            # Given key album.artist.subquery.tracks,
                            # This portion of the code will eventually
                            # produce ["tracks"]
                            sub_attr_path_parts.append(key_part)
                        else:
                            # Given key album.artist.subquery.tracks,
                            # This portion of the code will eventually
                            # produce ["album", "artist"]
                            subquery_path_parts.append(key_part)
                    else:
                        # This is officially a subquery
                        # Create a subquery with a key equal
                        # to the path leading up to this point.
                        # Given key album.artist.subquery.tracks,
                        # the resulting subquery key will be
                        # "album.artist"
                        subitem_path = ".".join(subquery_path_parts)
                        if subqueries.get(subitem_path) is None:
                            subqueries[subitem_path] = SubfilterInfo(
                                filters={"$and": []}
                            )
                            subitem_found = True
                # get an individual filter type object for the
                # subquery child key. Given query param
                # album.artist.$subquery.tracks.track_id = 5,
                # the result will be {"tracks.track_id": {"eq": 5}}
                item_filters = self._get_item_filter(
                    attr_name=".".join(sub_attr_path_parts),
                    value=value,
                    strict=strict
                )
                # returns in list form to enable multiple filters
                # for a single key
                if subitem_path:
                    for item in item_filters:
                        subqueries[subitem_path].filters["$and"].append(item)
            elif key.find(suboffset_name) > -1:
                self._parser_helper(
                    parse_type="offset",
                    subqueries=subqueries,
                    key=key,
                    key_parts=key_parts,
                    key_value=value,
                    subkey_name=suboffset_name,
                    strict=strict
                )
            elif key.find(sublimit_name) > -1:
                self._parser_helper(
                    parse_type="limit",
                    subqueries=subqueries,
                    key=key,
                    key_parts=key_parts,
                    key_value=value,
                    subkey_name=sublimit_name,
                    strict=strict
                )
            elif key.find(subsorts_name) > -1:
                self._parser_helper(
                    parse_type="sorts",
                    subqueries=subqueries,
                    key=key,
                    key_parts=key_parts,
                    key_value=value,
                    subkey_name=subsorts_name,
                    strict=strict
                )
        return subqueries

    def _get_item_filter(self, attr_name, value, strict=True):
        """Parse query param into a set of filters as dictionaries.

        :param str attr_name: The name of the query param to parse.
        :param value: The value of that query param.
        :type value: str or list of str
        :param bool strict: If ``True``, exceptions will be raised for
            invalid input. Otherwise, invalid input will be ignored.
        :raise FilterParseError: Malformed complex queries or
            invalid ``query_params`` will result in an
            :exc:`~drowsy.exc.FilterParseError` being raised if
            ``strict`` is ``True``.
        :return: List of filters as dictionaries.
        :rtype: list of dict

        """
        # how much to remove from end of key to get the attr_name.
        # default values:
        chop_len = 0
        key = attr_name
        comparator = "$eq"
        if key.endswith("-gt"):
            chop_len = 3
            comparator = "$gt"
        elif key.endswith("-gte"):
            chop_len = 4
            comparator = "$gte"
        elif key.endswith("-eq"):
            chop_len = 3
            comparator = "$eq"
        elif key.endswith("-lte"):
            chop_len = 4
            comparator = "$lte"
        elif key.endswith("-lt"):
            chop_len = 3
            comparator = "$lt"
        elif key.endswith("-ne"):
            chop_len = 3
            comparator = "$ne"
        elif key.endswith("-like"):
            chop_len = 5
            comparator = "$like"
        if chop_len != 0:
            attr_name = key[:(-1 * chop_len)]
        if not isinstance(value, list):
            value = [value]
        result = []
        for item in value:
            if isinstance(item, str) and item.startswith("{"):
                try:
                    query = json.loads(item)
                    if attr_name:
                        result.append(
                            {attr_name: query})
                    else:
                        result.append(query)
                except (TypeError, ValueError):
                    if strict:
                        self.fail("invalid_complex_filters", qparam=attr_name)
            else:
                if attr_name:
                    result.append(
                        {attr_name: {comparator: item}})
                else:
                    self.fail("invalid_complex_filters", qparam=attr_name)
        return result

    def parse_filters(self, model_class, complex_query_name="query",
                      only_parse_complex=False, convert_key_names_func=str,
                      subquery_name="_subquery_", sublimit_name="_limit_",
                      suboffset_name="_offset_", subsorts_name="_sorts_",
                      strict=True):
        """Convert request params into MQLAlchemy friendly search.

        :param model_class: The SQLAlchemy class being queried.
        :param str complex_query_name: The name of the key used to check
            for a complex query value in the provided ``query_params``.
            Note that the complex query should be a json dumped
            dictionary value.
        :param bool only_parse_complex: Set to ``True`` if all simple
            filters in the query params should be ignored.
        :param convert_key_names_func: If provided, should take in a dot
            separated attr name and transform it such that the result is
            the corresponding dot separated attribute in the
            ``model_class`` being queried.
            Useful if, for example, you want to allow users to provide
            an attr name in one format (say camelCase) and convert it
            to the naming format used for your model objects (likely
            underscore).
        :type convert_key_names_func: callable or None
        :param subquery_name: Query param name used to trigger a
            subquery. Query params that include this name will be
            ignored.
        :type subquery_name: str or None
        :param sublimit_name: Query param name used to trigger a
            subquery resource limit. Query params that include this
            name will be ignored.
        :type sublimit_name: str or None
        :param suboffset_name: Query param name used to trigger a
            subquery resource offset. Query params that include this
            name will be ignored.
        :type suboffset_name: str or None
        :param subsorts_name: Query param name used to trigger a
            subquery sort. Query params that include this name will be
            ignored.
        :type subsorts_name: str or None
        :param bool strict: If ``True``, exceptions will be raised for
            invalid input. Otherwise, invalid input will be ignored.
        :raise FilterParseError: Malformed complex queries or
            invalid ``query_params`` will result in an
            :exc:`~drowsy.exc.FilterParseError` being raised if
            ``strict`` is ``True``.
        :return: A dictionary containing filters that can be passed
            to mqlalchemy for query filtering.
        :rtype: dict

        """
        # use an $and query to enable multiple queries for the same
        # attribute.
        result = {"$and": []}
        for key in self.query_params.keys():
            if (subquery_name in key or
                    sublimit_name in key or
                    suboffset_name in key or
                    subsorts_name in key):
                continue
            if key == complex_query_name:
                complex_query_list = []
                if isinstance(self.query_params[key], list):
                    complex_query_list = self.query_params[key]
                else:
                    complex_query_list.append(self.query_params[key])
                for complex_query in complex_query_list:
                    try:
                        query = json.loads(complex_query)
                        if not isinstance(query, dict):
                            raise ValueError
                        result["$and"].append(query)
                    except (TypeError, ValueError):
                        if strict:
                            self.fail("invalid_complex_filters", qparam=key)
            elif not only_parse_complex:
                # how much to remove from end of key to get the attr_name.
                # default values:
                value = self.query_params[key]
                item_filters = self._get_item_filter(attr_name=key,
                                                     value=value)
                attr_name = list(item_filters[0].keys())[0]
                attr_check = None
                try:
                    c_attr_name = convert_key_names_func(attr_name)
                    if c_attr_name:
                        attr_check = c_attr_name.split(".")
                        if attr_check:
                            attr_check = attr_check[0]
                except AttributeError:
                    attr_check = None
                if attr_check and hasattr(model_class, attr_check):
                    # ignore any top level invalid params
                    for item in item_filters:
                        result["$and"].append(item)
        if len(result["$and"]) == 0:
            return {}
        return result
