"""
    drowsy.resource
    ~~~~~~~~~~~~~~~

    Base classes for building resources and model resources.

"""
# :copyright: (c) 2016-2021 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
import math
from marshmallow.exceptions import ValidationError
from mqlalchemy import (
    InvalidMqlException, MqlFieldError, MqlFieldPermissionError, MqlTooComplex)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import inspect
from drowsy import resource_class_registry
from drowsy.base import BaseResourceABC
from contextlib import suppress
from drowsy.exc import (
    BadRequestError, PermissionValidationError, PermissionDeniedError)
from drowsy.fields import (
    EmbeddableMixinABC, NestedPermissibleABC, Relationship)
from drowsy.log import Loggable
from drowsy.query_builder import ModelResourceQueryBuilder


class PaginationInfo(Loggable):

    """Pagination meta info container."""

    def __init__(self, resources_available, page_size=None, current_page=None):
        """Initializes pagination info container.

        :param int resources_available: The total number of matching
            resources for a query. Used for pagination info.
        :param page_size: The current page number for the result.
        :type page_size: int or None
        :param current_page: The current page number for the result.
        :type current_page: int or None

        """
        self.resources_available = resources_available
        self._page_size = None
        self._current_page = None
        self.page_size = page_size
        self.current_page = current_page

    @property
    def page_size(self):
        """Get the number of resources included in a result collection.

        :return: The size of each page in a result collection.
        :rtype: int or None

        """
        return self._page_size

    @page_size.setter
    def page_size(self, value):
        """Set the number of resources included in a result collection.

        :return: The size of each page in a result collection.
        :rtype: int or None

        """
        if not isinstance(value, int) and value is not None:
            raise TypeError("page_size must be an integer or None.")
        if value is None or value > 0:
            self._page_size = value
        else:
            raise ValueError(
                "page_size must be an integer greater than 0 or None.")

    @property
    def current_page(self):
        """Get the current page of this resource collection.

        :return: The current page of this resource collection.
        :rtype: int or None

        """
        return self._current_page

    @current_page.setter
    def current_page(self, value):
        """Set the current page of this resource collection.

        :param value: A positive integer or ``None``. Page numbering
            starts at 1, not 0.
        :type value: int or None
        :return: None

        """
        if not isinstance(value, int) and value is not None:
            raise TypeError("current_page must be an integer or None.")
        if value is None or value > 0:
            self._current_page = value
        else:
            raise ValueError(
                "current_page must be an integer greater than 0 or None.")

    @property
    def first_page(self):
        """Get the first page number of this resource collection.

        :return: ``1`` if pagination is being used, otherwise ``None``.
        :rtype: int or None

        """
        if self.page_size is not None:
            return 1
        return None

    @property
    def last_page(self):
        """Get the last page number of this resource collection.

        :return: The number of the last page if pagination is being
            used, otherwise ``None``.
        :rtype: int or None

        """
        if self.page_size is not None:
            return math.ceil(self.resources_available/(self.page_size * 1.0))
        return None

    @property
    def previous_page(self):
        """Get the previous page number based on the current page.

        :return: The current page number - 1 if pagination is being
            used, and if the current page isn't the first page.
        :rtype: int or None

        """
        if self.current_page is not None and self.page_size is not None:
            if self.current_page > self.first_page:
                return self.current_page - 1
        return None

    @property
    def next_page(self):
        """Get the next page number based on the current page number.

        :return: The current page number + 1 if pagination is being
            used, and if the current page isn't the last page.
        :rtype: int or None

        """
        if self.current_page is not None and self.page_size is not None:
            if self.current_page < self.last_page:
                return self.current_page + 1
        return None


class ResourceCollection(list, PaginationInfo):

    """A simple list subclass that contains some extra meta info."""

    def __init__(self, resources, resources_available, page_size=None,
                 current_page=None):
        """Initializes a resource collection.

        :param iterable resources: The resources that were fetched in
            a query.
        :param int resources_available: The total number of matching
            resources for a query. Used for pagination info.
        :param page_size: The current page number for the result.
        :type page_size: int or None
        :param current_page: The current page number for the result.
        :type current_page: int or None

        """
        list.__init__(self, resources)
        PaginationInfo.__init__(
            self, resources_available, page_size, current_page)

    @property
    def resources_fetched(self):
        """Simple alias for list length.

        :return: Number of resources that were fetched.
        :rtype: int

        """
        return self.__len__()


class ResourceOpts(object):

    """Meta class options for use with a `SchemaResource`.

    A ``schema_cls`` option must be provided.

    An ``options`` option may be provided as a list in order to
    explicitly state what actions may be taken on this resource, with
    GET, POST, PUT, PATCH, DELETE, HEAD, and OPTIONS as possible values.

    An ``error_messages`` option may be provided as a `dict` in order
    to override some or all of the default error messages for a
    resource.

    A ``page_max_size`` option may be provided as an `int`, `callable`,
    or ``None`` to specify default page size for this resource. If given
    a `callable`, it should the resource itself as an argument.

    Example usage:

    .. code-block:: python

        class UserResource(ModelResource):
            class Meta:
                schema_cls = UserSchema
                options = ["GET", "POST", "PUT", "PATCH]
                error_messages = {
                    "validation_failure": "Fix your data."
                }
                page_max_size = 100

    """

    def __init__(self, meta):
        """Handle the meta class attached to a `ModelResource`.

        :param meta: The meta class attached to a
            :class:`~drowsy.resource.ModelResource`.

        """
        self.schema_cls = getattr(meta, "schema_cls", None)
        self.error_messages = getattr(meta, "error_messages", None)
        self.page_max_size = getattr(meta, "page_max_size", None)
        self.options = getattr(
            meta,
            "options",
            ["GET", "POST", "PATCH", "PUT", "DELETE", "HEAD", "OPTIONS"])


class ResourceMeta(type):

    """Meta class inherited by `ModelResource`.

    This is ultimately responsible for attaching an ``opts`` object to
    :class:`ModelResource`, as well as registering that class with the
    ``resource_class_registry``.

    """

    def __new__(mcs, name, bases, attrs):
        """Sets up meta class options for a given ModelResource class.

        :param mcs: This :class:`ResourceMeta` class.
        :param str name: Class name of the
            :class:`~drowsy.resource.ModelResource` that this meta
            class is attached to.
        :param tuple bases: Base classes the associated class inherits
            from.
        :param dict attrs: Dictionary of info pertaining to the class
            this meta class is attached to. Includes the __module__ the
            class is in, the __qualname__ of the class, and potentially
            __doc__ for the class.

        """
        klass = super(ResourceMeta, mcs).__new__(mcs, name, bases, attrs)
        meta = getattr(klass, 'Meta')
        klass.opts = klass.OPTIONS_CLASS(meta)
        return klass

    def __init__(cls, name, bases, attrs):
        """Initializes the meta class for a ``ModelResource`` class.

        :param cls: This :class:`ResourceMeta` class.
        :param name: Class name of the
            :class:`~drowsy.resource.ModelResource` that this meta
            class is attached to.
        :param tuple bases: Base classes the associated class inherits
            from.
        :param dict attrs: Dictionary of info pertaining to the class
            this meta class is attached to. Includes the __module__ the
            class is in, the __qualname__ of the class, and potentially
            __doc__ for the class.

        """
        super(ResourceMeta, cls).__init__(name, bases, attrs)
        resource_class_registry.register(name, cls)


class BaseModelResource(BaseResourceABC):

    """Model API Resources should inherit from this object."""

    OPTIONS_CLASS = ResourceOpts

    _default_error_messages = {
        "filters_field_op_error": ("A value of `%(value)s` was provided for "
                                   "the field `%(field)s` using `%(op)s`."),
        "filters_field_error": ("A value of `%(value)s` was provided for the "
                                "field `%(field)s`."),
        "filters_permission_error": ("You do not have permission to filter "
                                     "the field `%(field)s`."),
        "filters_too_complex": ("The filters provided can not be processed "
                                "due to being overly complex."),
        "invalid_subresource_multi_embed": (
            "The attempt to embed %(subresource_key)s resulted in an error. "
            "This subresource is of the same relationship as a previously "
            "embedded subresource.")
    }

    def __init__(self, session, context=None, page_max_size=None,
                 error_messages=None, parent_field=None):
        """Creates a new instance of the model.

        :param session: Database session to use for any resource
            actions.
        :type session: :class:`~sqlalchemy.orm.session.Session` or
            callable
        :param context: Context used to alter the schema used for this
            resource. For example, may contain the current
            authorization status of the current request. If errors
            should be translated, context should include a ``"gettext"``
            key referencing a callable that takes in a string and any
            keyword args.
        :type context: dict, callable, or None
        :param page_max_size: Used to determine the maximum number of
            results to return by :meth:`get_collection`. Defaults to
            the ``page_max_size`` from the resource's ``opts`` if
            ``None`` is passed in. To explicitly allow no limit,
            pass in ``0``. If given a ``callable``, it should accept
            the resource itself as its first and only argument.
        :type page_max_size: int, callable, or None
        :param error_messages: May optionally be provided to override
            the default error messages for this resource.
        :type error_messages: dict or None
        :param parent_field: The field that owns this resource, if
            applicable. Likely some variety of
            :class:`NestedPermissibleABC`.
        :type parent_field: Field

        """
        super(BaseModelResource, self).__init__(
            context=context,
            page_max_size=page_max_size,
            error_messages=error_messages,
            parent_field=parent_field)
        self._session = session

    def _get_schema_kwargs(self, schema_cls):
        """Get default kwargs for any new schema creation.

        :param schema_cls: The class of the schema being created.
        :return: A dictionary of keyword arguments to be used when
            creating new schema instances.
        :rtype: dict

        """
        result = super(BaseModelResource, self)._get_schema_kwargs(schema_cls)
        result["session"] = self.session
        return result

    def make_error(self, key, errors=None, exc=None, **kwargs):
        """Returns an exception based on the ``key`` provided.

        :param str key: Failure type, used to choose an error message.
        :param errors: May be used by the raised exception.
        :type errors: dict or None
        :param exc: If another exception triggered this failure, it may
            be provided for a more informative failure. In the case of
            an ``InvalidMqlException`` being provided, the
            ``exc.message`` will be used as part of the error message
            here.
        :type exc: :exc:`Exception` or None
        :param kwargs: Any additional arguments that may be used for
            generating an error message.
        :return: `UnprocessableEntityError` If ``key`` is
            ``"validation_failure"``. Note that in this case, errors
            should preferably be provided. In all other cases a
            `BadRequestError` is returned.

        """
        filter_exceptions = (MqlFieldError, InvalidMqlException, MqlTooComplex)
        if isinstance(exc, filter_exceptions):
            if kwargs.get("subresource_key"):
                prefix = kwargs["subresource_key"] + ": "
            else:
                prefix = ""
            if isinstance(exc, MqlFieldError):
                if exc.op:
                    kwargs["op"] = exc.op
                kwargs["value"] = exc.filter
                kwargs["field"] = exc.data_key
                message = prefix + self._get_error_message(key, **kwargs)
                message += " " + exc.message
                if isinstance(exc, MqlFieldPermissionError):
                    return PermissionDeniedError(
                        code=key,
                        message=message,
                        errors={},
                        **kwargs)
            else:
                message = self._get_error_message(key, **kwargs)
            return BadRequestError(
                code=key,
                message=message,
                **kwargs)
        return super(BaseModelResource, self).make_error(
            key=key,
            errors=errors,
            exc=exc,
            **kwargs
        )

    @property
    def model(self):
        """Get the model class associated with this resource."""
        return self.schema_cls.opts.model

    @property
    def session(self):
        """Get a db session to use for this request."""
        if callable(self._session):
            return self._session()
        else:
            return self._session

    @session.setter
    def session(self, val):
        """Set session to the provided value.

        :param val: Used to set the current session.
        :type val: dict, callable, or None

        """
        self._session = val

    @property
    def query_builder(self):
        """Returns a ModelResourceQueryBuilder object.

        This exists mainly for inheritance purposes.

        """
        return ModelResourceQueryBuilder()

    def _convert_nested_opts(self, nested_opts):
        """Converts the key names for user supplied nested opts.

        :param dict nested_opts: Dictionary of nested load options.
        :return: An equivalent dictionary with key names converted from
            the user supplied key to one that can be used internally.

        """
        if not isinstance(nested_opts, dict):
            raise TypeError("Supplied nested_opts must be a dict.")
        new_nested_opts = {}
        for key in nested_opts:
            new_nested_opts[self.convert_key_name(key)] = nested_opts[key]
        return new_nested_opts

    def _get_ident_filters(self, ident):
        """Generate MQLAlchemy filters using a resource identity.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.

        """
        filters = {}
        if not (isinstance(ident, tuple) or
                isinstance(ident, list)):
            ident = (ident,)
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        schema = self.make_schema()
        for i, field_name in enumerate(schema.id_keys):
            field = schema.fields.get(field_name)
            filter_name = field.data_key or field_name
            filters[filter_name] = ident[i]
        return filters

    def _get_instance(self, ident):
        """Given an identity, get the associated SQLAlchemy instance.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :raise ResourceNotFoundError: Raised in cases where invalid
            filters were supplied.
        :return: An instance of this resource type.

        """
        filters = self._get_ident_filters(ident)
        query = self.session.query(self.model)
        try:
            query = self.query_builder.apply_filters(
                query,
                model_class=self.model,
                filters=filters,
                nested_conditions=self.get_required_nested_filters,
                whitelist=self.whitelist,
                stack_size_limit=100,
                convert_key_names_func=self.convert_key_name,
                gettext=self.context.get("gettext", None))
            query = self.apply_required_filters(query)
        except (TypeError, ValueError, InvalidMqlException, BadRequestError):
            # NOTE - BadRequestError only an issue on filters,
            # e.g. a bad ident provided.
            raise self.make_error("resource_not_found", ident=ident)
        return query.first()

    def get_required_filters(self, alias=None):
        """Build any required filters for this resource.

        Does nothing by default, but can be usefully overridden if you
        want to enforce certain filters on this resource. A simple
        example would be a notifications resource where a filter
        matching the currently logged in user is applied.

        e.g.::

            model = alias or self.model
            return model.user_id == self.context.get("user_id")

        :param alias: Can optionally be supplied if this resource is
            being used as a subresource and an alias has been applied.
        :return: Any valid SQL expression(s), to be passed directly into
            :meth:`~sqlalchemy.orm.query.Query.filter`. If multiple
            expressions, they may be returned in a list or tuple.
            Defaults to ``None``.

        """
        return None

    def get_required_nested_filters(self, key):
        """For a given dot separated data key, return required filters.

        Uses :meth:`get_required_filters` from child resources.

        :param str key: Dot notation field name. For example, if trying
            to query an album, this may look something like
            ``"tracks.playlists"``.
        :return: Any valid SQL expression(s), to be passed directly
            into :meth:`~sqlalchemy.orm.query.Query.filter`. If multiple
            expressions, they may be returned in a list or tuple.
            Defaults to ``None``.

        """
        schema = self.schema_cls(**self._get_schema_kwargs(self.schema_cls))
        resource = self
        split_keys = key.split(".")
        if len(split_keys) == 1 and split_keys[0] == "":
            return None
        while split_keys:
            key = split_keys.pop(0)
            if key in schema.fields:
                field = schema.fields[key]
                if isinstance(field, EmbeddableMixinABC):
                    schema.embed([key])
                if isinstance(field, NestedPermissibleABC):
                    with suppress(ValueError, TypeError):
                        resource = resource.make_subresource(
                            field.data_key or key)
                        if not split_keys:
                            if hasattr(resource,
                                       "get_required_filters") and callable(
                                resource.get_required_filters
                            ):
                                return resource.get_required_filters()
                            # Subresource doesn't use required filtering
                            return None  # pragma: no cover
                        # not the final resource, continue traversing
                        schema = resource.schema
                        continue
                    # attempting to use the subresource didn't work
                    # Note - We have the following options:
                    # 1. Error out
                    # 2. Fail quietly and return None
                    return None  # pragma: no cover
                else:
                    # Note - Could be an error
                    # Defaulting to failing quietly
                    return None  # pragma: no cover

    def apply_required_filters(self, query, alias=None):
        """Apply required filters on this query.

        Applies the result of :meth:`get_required_filters` directly to
        the provided ``query``.

        If you're looking to define any required filters for a
        resource, you'll want to override :meth:`get_required_filters`
        rather than this method. Doing so ensures those filters are
        applied when the resource is used as a child resource as well.

        :param query: An already partially constructed sqlalchemy query.
        :type query: :class:`~sqlalchemy.orm.query.Query`
        :param alias: Can optionally be used if this resource is being
            used as a subresource and an alias has been applied.
        :return: A potentially modified query object.
        :rtype: :class:`~sqlalchemy.orm.query.Query`

        """
        filters = self.get_required_filters(alias=alias)
        if filters is not None:
            if isinstance(filters, list) or isinstance(filters, tuple):
                if filters:
                    # this looks redundant, but it's checking if
                    # the collection is empty rather than None
                    return query.filter(*filters)
            else:
                return query.filter(filters)
        return query

    def _get_query(self, session, filters, subfilters=None, embeds=None,
                   limit=None, offset=None, sorts=None, strict=True):
        """Used to generate a query for this request.

        :param session: See :meth:`get` for more info.
        :type session: :class:`~sqlalchemy.orm.session.Session` or
            :class:`~sqlalchemy.orm.query.Query`
        :param filters: MQLAlchemy filters to be applied on this query.
        :type filters: dict or None
        :param subfilters: MQLAlchemy filters to be applied to child
            objects of this query. Each key in the dictionary should
            be a dot notation key corresponding to a subfilter.
        :type subfilters: dict or None
        :param embeds: A list of relationship and relationship field
            names to be included in the result.
        :type embeds: list or None
        :param bool strict: If ``True``, will raise an exception when
            bad parameters are passed. If ``False``, will quietly ignore
            any bad input and treat it as if none was provided.
        :raise BadRequestError: Invalid filters or embeds will
            result in a raised exception if ``strict`` is ``True``.
        :return: A query with load options applied based on the supplied
            ``embeds`` and filters applied based on the supplied
            ``filters``.
        :rtype: :class:`~drowsy.schema.ModelResourceSchema`,
            :class:`~sqlalchemy.orm.query.Query`

        """
        if hasattr(session, "query") and callable(session.query):
            query = session.query(self.model)
        else:
            query = session
        # apply filters
        # Note that required filters are applied by query builder too
        query = self.query_builder.build(
            query=query,
            resource=self,
            filters=filters,
            subfilters=subfilters,
            embeds=embeds,
            offset=offset,
            limit=limit,
            sorts=sorts,
            strict=strict,
            stack_size_limit=100,
            dialect_override=None)
        return query

    @property
    def options(self):
        """Get the available options for this resource.

        :return: A list of available options for this resource.
            Values can include GET, POST, PUT, PATCH, DELETE, HEAD, and
            OPTIONS.
        :rtype: list

        """
        return self.opts.options

    def _check_method_allowed(self, method):
        """Check if a given method is valid for this resource.

        Note that OPTIONS is always allowed.

        :param str method: Should be one of GET, POST, PUT, PATCH,
            DELETE, HEAD, or OPTIONS.
        :return: ``True`` if the supplied ``method`` is allowed.
        :raise MethodNowAllowedError: When the supplied ``method``
            is not allowed.

        """
        if method.upper() in self.options or (
                method.upper() == "OPTIONS"):
            return True
        raise self.make_error("method_not_allowed", method=method.upper())

    def get(self, ident, subfilters=None, fields=None, embeds=None,
            session=None, strict=True, head=False):
        """Get the identified resource.

        :param ident: A value used to identify this resource. If the
            schema associated with this resource has multiple
            ``id_keys``, this value may be a list or tuple.
        :param subfilters: A dict of MQLAlchemy filters, with each key
            being the dot notation of the relationship they are to be
            applied to.
        :type subfilters: dict or None
        :param fields: Names of fields to be included in the result.
        :type fields: list or None
        :param embeds: A list of relationship and relationship field
            names to be included in the result.
        :type embeds: collection or None
        :param session: Optional sqlalchemy session override. May also
            be a partially formed SQLAlchemy query, allowing for
            sub-resource queries by using
            :meth:~`sqlalchemy.orm.query.Query.with_parent`.
        :type session: :class:`~sqlalchemy.orm.session.Session` or
            :class:`~sqlalchemy.orm.query.Query`
        :param bool strict: If ``True``, will raise an exception when
            bad parameters are passed. If ``False``, will quietly ignore
            any bad input and treat it as if none was provided.
        :param bool head: If this was a HEAD request. Doesn't affect
            anything here, but supplied in case there's desire to
            override the method.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise BadRequestError: Invalid fields or embeds will result
            in a raised exception if strict is set to ``True``.
        :raise MethodNotAllowedError: If this method hasn't been marked
            as allowed in the meta class options.
        :return: The resource itself if found.
        :rtype: dict

        """
        self._check_method_allowed("GET" if not head else "HEAD")
        filters = self._get_ident_filters(ident)
        if session is None:
            session = self.session
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        schema = self.make_schema(
            fields=fields,
            subfilters=subfilters,
            embeds=embeds,
            strict=strict)
        try:
            query = self._get_query(
                session=session,
                filters=filters,
                subfilters=subfilters,
                embeds=embeds)
        except BadRequestError as exc:
            if exc.code == "filters_field_op_error":
                if exc.kwargs.get("subresource_key") is None:
                    # This error is due to a bad ID key provided.
                    exc = self.make_error("resource_not_found", ident=ident)
            raise exc
        except (ValueError, TypeError, InvalidMqlException):  # pragma: no cover
            raise self.make_error("unexpected_error")
        instance = query.all()
        if instance:
            return schema.dump(instance[0])
        raise self.make_error("resource_not_found", ident=ident)

    def post(self, data, nested_opts=None):
        """Create a new resource and store it in the db.

        :param dict data: Data used to create a new resource.
        :param dict|None nested_opts: Any explicit nested load options.
            These can be used to control whether a nested resource
            collection should be replaced entirely or only modified.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :raise MethodNotAllowedError: If this method hasn't been marked
            as allowed in the meta class options.
        :return: The created resource.
        :rtype: dict

        """
        self._check_method_allowed("POST")
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        schema = self.make_schema(partial=False)
        nested_opts = nested_opts or {}
        try:
            instance = schema.load(
                data,
                session=self.session,
                nested_opts=self._convert_nested_opts(nested_opts),
                action="create")
        except PermissionValidationError:
            self.session.rollback()
            raise self.make_error("permission_denied")
        except ValidationError as exc:
            self.session.rollback()
            raise self.make_error("validation_failure", errors=exc.messages)
        self.session.add(instance)
        try:
            self.session.commit()
        except SQLAlchemyError:  # pragma: no cover
            self.session.rollback()
            raise self.make_error("commit_failure")
        ident = []
        for key in schema.id_keys:
            ident.append(getattr(instance, key))
        ident = tuple(ident)
        return self.get(ident, embeds=self._get_embed_history(schema))

    def put(self, ident, data, nested_opts=None):
        """Replace the current object with the supplied one.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :param dict data: Data used to replace the resource.
        :param dict|None nested_opts: Any explicit nested load options.
            These can be used to control whether a nested resource
            collection should be replaced entirely or only modified.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :raise MethodNotAllowedError: If this method hasn't been marked
            as allowed in the meta class options.
        :return: The replaced resource.
        :rtype: dict

        """
        self._check_method_allowed("PUT")
        nested_opts = nested_opts or {}
        instance = self._get_instance(ident)
        if not instance:
            raise self.make_error("resource_not_found", ident=ident)
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        schema = self.make_schema(
            partial=False,
            instance=instance)
        try:
            schema.load(
                data,
                instance=instance,
                session=self.session,
                nested_opts=self._convert_nested_opts(nested_opts),
                action="update")
        except PermissionValidationError:
            self.session.rollback()
            raise self.make_error("permission_denied")
        except ValidationError as exc:
            self.session.rollback()
            raise self.make_error("validation_failure", errors=exc.messages)
        try:
            self.session.commit()
        except SQLAlchemyError:  # pragma: no cover
            self.session.rollback()
            raise self.make_error("commit_failure")
        return self.get(ident, embeds=self._get_embed_history(schema))

    def patch(self, ident, data, nested_opts=None):
        """Update the identified resource with the supplied data.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :param dict data: Data used to update the resource.
        :param dict|None nested_opts: Any explicit nested load options.
            These can be used to control whether a nested resource
            collection should be replaced entirely or only modified.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :raise MethodNotAllowedError: If this method hasn't been marked
            as allowed in the meta class options.
        :return: The updated resource.
        :rtype: dict

        """
        # Refactor - Only three lines here different from put.
        # TODO - deleting a subresource calls patch, odd error potential
        self._check_method_allowed("PATCH")
        nested_opts = nested_opts or {}
        instance = self._get_instance(ident)
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        schema = self.make_schema(
            partial=True,
            instance=instance)
        try:
            schema.load(
                data,
                instance=instance,
                session=self.session,
                nested_opts=self._convert_nested_opts(nested_opts),
                action="update")
        except PermissionValidationError:
            self.session.rollback()
            raise self.make_error("permission_denied")
        except ValidationError as exc:
            self.session.rollback()
            raise self.make_error("validation_failure", errors=exc.messages)
        try:
            self.session.commit()
        except SQLAlchemyError:  # pragma: no cover
            self.session.rollback()
            raise self.make_error("commit_failure")
        return self.get(ident, embeds=self._get_embed_history(schema))

    def _get_embed_history(self, schema, data_key=None):
        """Figure out what fields were embedded from write operation.

        We perform a GET after an individual resource write in order to
        safely make sure only accessible data is returned, but need to
        reverse engineer which fields were embedded along the way.

        :param schema: The schema used to deserialize data. May have
            been modified during that process.
        :type schema: :class:`~drowsy.schema.ResourceSchema`
        :param str|None data_key: Dot notation data key, can be provided
            if checking a specific data_key rather than the whole
            schema.

        """
        results = set()
        key = data_key or ""
        found = False
        for field_key in schema.fields:
            field = schema.fields[field_key]
            if isinstance(field, Relationship) and field.embedded:
                child_key = field.data_key or field.name
                children = self._get_embed_history(field.schema, child_key)
                for child in children:
                    if key:
                        results.add(".".join([key, child]))
                    else:
                        results.add(child)
                found = True
        if not found and key:
            results.add(key)
        return results

    def delete(self, ident):
        """Delete the identified resource.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise MethodNotAllowedError: If this method hasn't been marked
            as allowed in the meta class options.
        :return: ``None``

        """
        self._check_method_allowed("DELETE")
        instance = self._get_instance(ident)
        if instance:
            schema = self.make_schema(
                partial=True,
                instance=instance)
            try:
                schema.check_permission(
                    data={}, instance=instance, action="delete")
            except PermissionValidationError:
                raise self.make_error("permission_denied")
            self.session.delete(instance)
            try:
                self.session.commit()
            except SQLAlchemyError:  # pragma: no cover
                self.session.rollback()
                raise self.make_error("commit_failure")
        else:
            raise self.make_error("resource_not_found", ident=ident)

    def get_collection(self, filters=None, subfilters=None, fields=None,
                       embeds=None, sorts=None, offset=None, limit=None,
                       session=None, strict=True, head=False):
        """Get a collection of resources.

        :param filters: MQLAlchemy filters to be applied on this query.
        :type filters: dict or None
        :param subfilters: A dict of MQLAlchemy filters, with each key
            being the dot notation of the relationship they are to be
            applied to.
        :type subfilters: dict or None
        :param fields: Names of fields to be included in the result.
        :type fields: list or None
        :param embeds: A list of relationship and relationship field
            names to be included in the result.
        :type embeds: collection or None
        :param sorts: Sorts to be applied to this query.
        :type sorts: list of :class:`SortInfo`, or None
        :param offset: Standard SQL offset to be applied to the query.
        :type offset: int or None
        :param limit: Standard SQL limit to be applied to the query.
        :type limit: int or None
        :param session: Optional sqlalchemy session override. See
            :meth:`get` for more info.
        :type session: :class:`~sqlalchemy.orm.session.Session` or
            :class:`~sqlalchemy.orm.query.Query`
        :param bool strict: If ``True``, will raise an exception when
            bad parameters are passed. If ``False``, will quietly ignore
            any bad input and treat it as if none was provided.
        :param bool head: If this was a HEAD request. Doesn't affect
            anything here, but supplied in case there's desire to
            override the method.
        :raise BadRequestError: Invalid filters, sorts, fields,
            embeds, offset, or limit will result in a raised exception
            if strict is set to ``True``.
        :raise MethodNotAllowedError: If this method hasn't been marked
            as allowed in the meta class options.
        :return: Resources meeting the supplied criteria.
        :rtype: :class:`ResourceCollection`

        """
        self._check_method_allowed("GET" if not head else "HEAD")
        if filters is None:
            filters = {}
        if session is None:
            session = self.session
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        schema = self.make_schema(
            fields=fields,
            subfilters=subfilters,
            embeds=embeds,
            strict=strict)
        count = self._get_query(
            session=session,
            filters=filters
        ).count()
        # set up offset/limit
        if (limit is not None and
                isinstance(self.page_max_size, int) and
                limit > self.page_max_size):
            if strict:
                raise self.make_error(
                    "limit_too_high",
                    limit=limit,
                    max_page_size=self.page_max_size)
            limit = self.page_max_size
        if not offset:
            offset = 0
        query = self._get_query(
            session=session,
            filters=filters,
            subfilters=subfilters,
            embeds=embeds,
            limit=limit,
            offset=offset,
            sorts=sorts,
            strict=strict)
        records = query.all()
        # get result
        dump = schema.dump(records, many=True)
        return ResourceCollection(dump, count)

    def post_collection(self, data, nested_opts=None):
        """Create multiple resources in the collection of resources.

        :param list data: List of resources to be created.
        :param dict|None nested_opts: Any explicit nested load options.
            These can be used to control whether a nested resource
            collection should be replaced entirely or only modified.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :raise MethodNotAllowedError: If this method hasn't been marked
            as allowed in the meta class options.
        :return: ``None``

        """
        self._check_method_allowed("POST")
        nested_opts = nested_opts or {}
        if not isinstance(data, list):
            raise self.make_error("invalid_collection_input", data=data)
        errors = {}
        validation_failure = False
        permission_failure = False
        for i, obj in enumerate(data):
            # NOTE: No risk of BadRequestError here due to no embeds or
            # fields being passed to make_schema
            schema = self.make_schema(partial=False)
            try:
                instance = schema.load(
                    obj,
                    session=self.session,
                    nested_opts=self._convert_nested_opts(nested_opts),
                    action="create")
                self.session.add(instance)
            except PermissionValidationError as exc:
                errors[i] = exc.messages
                permission_failure = True
            except ValidationError as exc:
                errors[i] = exc.messages
                validation_failure = True
        if permission_failure:
            self.session.rollback()
            raise self.make_error("permission_denied", errors=errors)
        elif validation_failure:
            self.session.rollback()
            raise self.make_error("validation_failure", errors=errors)
        try:
            self.session.commit()
        except SQLAlchemyError:  # pragma: no cover
            self.session.rollback()
            raise self.make_error("commit_failure")

    def put_collection(self, data, nested_opts=None):
        """Raises an error since this method has no obvious use.

        :param list data: A list of object data. Would theoretically
            be used to replace the entire collection.
        :param dict|None nested_opts: Any explicit nested load options.
            These can be used to control whether a nested resource
            collection should be replaced entirely or only modified.
        :raise MethodNowAllowedError: When not overridden.

        """
        raise self.make_error("method_not_allowed", method="PUT", data=data)

    def patch_collection(self, data, nested_opts=None):
        """Update a collection of resources.

        Individual items may be updated accordingly as part of the
        request as well.

        :param list data: A list of object data. If the object contains
            a key ``$op`` set to ``"add"``, the object will be added to
            the collection; otherwise the object must already be in the
            collection. If ``$op`` is set to ``"remove"``, it is
            accordingly removed from the collection.
        :param dict|None nested_opts: Any explicit nested load options.
            These can be used to control whether a nested resource
            collection should be replaced entirely or only modified.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :raise MethodNotAllowedError: If this method hasn't been marked
            as allowed in the meta class options.
        :return: ``None``

        """
        self._check_method_allowed("PATCH")
        nested_opts = nested_opts or {}
        errors = {}
        permission_failure = False
        validation_failure = False
        if not isinstance(data, list):
            raise self.make_error("invalid_collection_input")
        for i, obj in enumerate(data):
            try:
                if obj.get("$op") == "add":
                    # basically a post
                    # NOTE: No risk of BadRequestError here due to no embeds
                    # or fields being passed to make_schema
                    schema = self.make_schema(partial=False)
                    action = "create"
                elif obj.get("$op") == "remove":
                    # basically a delete
                    schema = self.make_schema(partial=True)
                    action = "delete"
                else:
                    schema = self.make_schema(partial=True)
                    action = "update"
                instance = schema.load(
                    obj,
                    session=self.session,
                    nested_opts=self._convert_nested_opts(nested_opts),
                    action=action)
                if action == "create":
                    self.session.add(instance)
                if action == "delete":
                    if inspect(instance).persistent:
                        self.session.delete(instance)
                    else:
                        # NOTE - Not sure how to handle.
                        # Should probably have schema.load raise a
                        # validation error when deleting a non
                        # persistent object.
                        # Biggest hold up is proper i18n support there.
                        pass
            except PermissionValidationError as exc:
                errors[i] = exc.messages
                permission_failure = True
            except ValidationError as exc:
                errors[i] = exc.messages
                validation_failure = True
        if permission_failure:
            self.session.rollback()
            raise self.make_error("permission_denied", errors=errors)
        elif validation_failure:
            self.session.rollback()
            raise self.make_error("validation_failure", errors=errors)
        try:
            self.session.commit()
        except SQLAlchemyError:  # pragma: no cover
            self.session.rollback()
            raise self.make_error("commit_failure")

    def delete_collection(self, filters=None, session=None, strict=True):
        """Delete all filter matching members of the collection.

        :param filters: MQLAlchemy style filters.
        :type filters: dict or None
        :param session: See :meth:`get` for more info.
        :type session: :class:`~sqlalchemy.orm.session.Session` or
            :class:`~sqlalchemy.orm.query.Query`
        :param bool strict: If ``True``, will raise an exception when
            bad parameters are passed. If ``False``, will quietly ignore
            any bad input and treat it as if none was provided.
        :raise UnprocessableEntityError: If the deletions are unable to
            be processed.
        :raise MethodNotAllowedError: If this method hasn't been marked
            as allowed in the meta class options.
        :return: ``None``

        """
        self._check_method_allowed("DELETE")
        filters = filters or {}
        if session is None:
            session = self.session
        query = self._get_query(
            session=session,
            filters=filters,
            strict=strict)
        instances = query.all()
        with self.session.no_autoflush:
            for instance in instances:
                # NOTE: No risk of BadRequestError here due to no embeds
                # or fields being passed to make_schema
                schema = self.make_schema(partial=True)
                try:
                    schema.check_permission(data={}, instance=instance,
                                            action="delete")
                except PermissionValidationError:
                    self.session.rollback()
                    raise self.make_error("permission_denied")
                self.session.delete(instance)
        try:
            self.session.commit()
        except SQLAlchemyError:  # pragma: no cover
            self.session.rollback()
            raise self.make_error("commit_failure")


class ModelResource(BaseModelResource, metaclass=ResourceMeta):
    pass
