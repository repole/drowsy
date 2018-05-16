"""
    drowsy.resource
    ~~~~~~~~~~~~~~~

    Base classes for building resources and model resources.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from marshmallow.compat import with_metaclass
from mqlalchemy import InvalidMQLException
from sqlalchemy.exc import SQLAlchemyError
import sys
from drowsy import resource_class_registry
from drowsy.fields import EmbeddableMixinABC, NestedRelated
from drowsy.query_builder import QueryBuilder, SortInfo
from drowsy.utils import get_error_message, get_field_by_dump_name
from drowsy.exc import (
    BadRequestError, UnprocessableEntityError, MethodNotAllowedError,
    ResourceNotFoundError, MISSING_ERROR_MESSAGE)


class ResourceCollection(list):

    """A simple list subclass that contains some extra meta info."""

    def __init__(self, resources, resources_available):
        """Initializes a resource collection.

        :param iterable resources: The resources that were fetched in
            a query.
        :param int resources_available: The total number of matching
            resources for a query. Used for pagination info.

        """
        self.resources_available = resources_available
        list.__init__(self, resources)

    @property
    def resources_fetched(self):
        """Simple alias for list length.

        :return: Number of resources that were fetched.
        :rtype: int

        """
        return self.__len__()


class ResourceABC(object):

    """Abstract resource base class."""

    def get(self, ident):
        """Get an instance of this resource.

        :param ident: Identifying info for the resource.
        :return: The resource itself if found.
        :raise ResourceNotFoundError: If no such resource exists.

        """
        raise NotImplementedError

    def post(self, data):
        """Create a resource with the supplied data.

        :param data: Data used to create the resource.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The created resource.

        """
        raise NotImplementedError

    def put(self, ident, data):
        """Replace the identified resource with the supplied one.

        :param ident: Identifying info for the resource.
        :param data: Data used to replace the resource.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The replaced resource.

        """
        raise NotImplementedError

    def patch(self, ident, data):
        """Update the identified resource with the supplied data.

        :param ident: Identifying info for the resource.
        :param data: Data used to update the resource.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The updated resource.

        """
        raise NotImplementedError

    def delete(self, ident):
        """Delete the identified resource.

        :param ident: Identifying info for the resource.
        :raise ResourceNotFoundError: If no such resource exists.
        :return: ``None``

        """
        raise NotImplementedError

    def get_collection(self):
        """Get a collection of resources."""
        raise NotImplementedError

    def post_collection(self, data):
        """Create multiple resources in the collection of resources.

        :param data: Data used to create the collection of resources.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: ``None``

        """
        raise NotImplementedError

    def put_collection(self, data):
        """Replace the entire collection of resources.

        :param data: Data used to replace the collection of resources.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: ``None``

        """
        raise NotImplementedError

    def patch_collection(self, data):
        """Update the collection of resources.

        :param data: Data used to update the collection of resources.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: ``None``

        """
        raise NotImplementedError

    def delete_collection(self):
        """Delete all members of the collection of resources."""
        raise NotImplementedError


class SchemaResourceABC(ResourceABC):

    """Abstract schema based resource class."""

    def _get_schema_kwargs(self, schema_cls):
        """Get default kwargs for any new schema creation.

        :param schema_cls: The class of the schema being created.

        """
        raise NotImplementedError

    def make_schema(self, subfilters=None, fields=None, embeds=None,
                    partial=False, instance=None, strict=True):
        """Used to generate a schema for this request.

        :param subfilters: A dict of MQLAlchemy filters, with each key
            being the dot notation of the relationship they are to be
            applied to.
        :type subfilters: dict or None
        :param fields: Names of fields to be included in the result.
        :type fields: list or None
        :param embeds: A list of child resources (and/or their fields)
            to include in the response.
        :type embeds: list or None
        :param bool partial: Whether partial deserialization is allowed.
        :param instance: Object to associate with the schema.
        :param bool strict: If ``True``, will raise an exception when
            bad parameters are passed. If ``False``, will quietly ignore
            any bad input and treat it as if none was provided.
        :raise BadRequestError: Invalid fields or embeds will result
            in a raised exception if strict is ``True``.
        :return: A schema with the supplied fields and embeds included.
        :rtype: :class:`~drowsy.schema.SchemaResourceABC`

        """
        raise NotImplementedError


class NestableResourceABC(ResourceABC):

    """Abstract nestable resource class."""

    def make_subresource(self, name):
        """Given a subresource name, construct a subresource.

        :param str name: Dumped name of field containing a subresource.
        :raise ValueError: If the name given isn't a valid subresource.
        :returns: A constructed :class:`~drowsy.resource.Resource`

        """
        raise NotImplementedError


class ResourceOpts(object):

    """Meta class options for use with a `SchemaResource`.

    A ``schema_cls`` option must be provided.

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


class BaseResourceABC(SchemaResourceABC, NestableResourceABC):

    OPTIONS_CLASS = ResourceOpts
    default_error_messages = {
        "validation_failure": "Unable to process entity.",
        "invalid_embed": "Invalid embed supplied: %(embed)s",
        "invalid_embeds": "Invalid embed supplied: %(embeds)s",
        "invalid_field": "Invalid field supplied: %(field)s",
        "invalid_fields": "Invalid fields supplied: %(fields)s",
        "invalid_filters": "Invalid filters supplied.",
        "commit_failure": "Unable to save the provided data.",
        "invalid_collection_input": "The provided input must be a list.",
        "resource_not_found": ("No resource matching the provided "
                               "identity could be found."),
        "invalid_sorts_type": "The sorts provided must be a list.",
        "invalid_sort_type": "The sort provided is invalid.",
        "invalid_sort_field": ("The sort provided for field %(field)s "
                               "is invalid."),
        "invalid_limit_value": ("The limit provided (%(limit)s) is not a "
                                "non negative integer."),
        "limit_too_high": ("The limit provided (%(limit)d) is greater than "
                           "the max page size allowed (%(max_page_size)d)."),
        "invalid_offset_value": ("The offset provided (%(offset)s) is not a "
                                 "non negative integer."),
        "method_not_allowed": ("The method (%(method)s) used to make this "
                               "request is not allowed for this resource."),
        "invalid_subresource_options": ("Limit and offset for this "
                                        "subresource are not supported: "
                                        "%(subresource_key)s"),
        "invalid_subresource_filters": ("The supplied filters for this "
                                        "subresource are invalid: "
                                        "%(subresource_key)s"),
        "invalid_subresource": "%(subresource_key)s is not a subresource.",
        "invalid_subresource_limit": ("The limit (%(supplied_limit)s) given "
                                      "for %(subresource_key)s subresource is "
                                      "too high. The max limit is "
                                      "%(max_limit)s."),
        "invalid_subresource_sorts": ("The subresource %(subresource_key)s "
                                      "can not have sorts applied without "
                                      "a limit or offset being supplied.")
    }

    class Meta(object):
        """Options object for a Resource.

        Example usage: ::

            class Meta:
                schema_cls = MyModelSchema
                error_messages = {
                    "validation_failure": "Fix your data."
                }

        Available options:

        - ``schema_cls``: The model schema this resource is built
          around.
        - ``error_messages``: A dict mapping an error message type to a
          string or callable.

        """

    @abc.abstractmethod
    def __init__(self, context=None, page_max_size=None,
                 error_messages=None, *args, **kwargs):
        """Creates a new instance of the model.

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

        """
        self._page_max_size = page_max_size
        if self._page_max_size is None and hasattr(self.opts, "page_max_size"):
            self._page_max_size = self.opts.page_max_size
        self._context = context
        # Set up error messages
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        if isinstance(self.opts.error_messages, dict):
            messages.update(self.opts.error_messages)
        messages.update(error_messages or {})
        self.error_messages = messages

    def make_schema(self, fields=None, subfilters=None, embeds=None,
                    partial=False, instance=None, strict=True):
        """Used to generate a schema for this request.

        :param fields: Names of fields to be included in the result.
        :type fields: list or None
        :param subfilters: Filters to be applied to children of this
            resource. Each key in the dictionary should be a dot
            notation key corresponding to a subfilter.
        :type subfilters: dict or None
        :param embeds: A list of relationship and relationship field
            names to be included in the result.
        :type embeds: list or None
        :param bool partial: Whether partial deserialization is allowed.
        :param instance: Object instance to associate with the schema.
        :param bool strict: If ``True``, will raise an exception when
            bad parameters are passed. If ``False``, will quietly ignore
            any bad input and treat it as if none was provided.
        :raise BadRequestError: Invalid fields or embeds will result
            in a raised exception if strict is ``True``.
        :return: A schema with the supplied fields and embeds included.
        :rtype: :class:`~drowsy.schema.ResourceSchema`

        """
        # parse embed information
        # combine subfilters with embeds to take care of implied embeds
        if isinstance(embeds, list):
            embeds_subfilters = [key for key in embeds]
            if isinstance(subfilters, dict):
                for key in subfilters:
                    for embed in embeds:
                        if key in embed:
                            break
                    else:
                        embeds_subfilters.append(key)
        elif isinstance(subfilters, dict):
            embeds_subfilters = [key for key in subfilters]
        else:
            embeds_subfilters = None
        converted_embeds, embed_name_mapping, embed_fields = (
            self._get_embed_info(embeds=embeds_subfilters, strict=strict))
        # fields
        converted_fields = []
        if fields:
            for field in fields:
                converted_field = self.convert_key_name(field)
                if converted_field is None:
                    if strict:
                        self.fail("invalid_field", field=field)
                elif converted_field:
                    converted_fields.append(converted_field)
        if converted_fields:
            for embed_field in embed_fields:
                if embed_field not in converted_fields:
                    converted_fields.append(embed_field)
            kwargs = self._get_schema_kwargs(self.schema_cls)
            kwargs.update(
                only=tuple(converted_fields),
                partial=partial,
                instance=instance
            )
            schema = self.schema_cls(**kwargs)
        else:
            kwargs = self._get_schema_kwargs(self.schema_cls)
            kwargs.update(
                partial=partial,
                instance=instance
            )
            schema = self.schema_cls(**kwargs)
        # actually attempt to embed now
        for converted_embed in converted_embeds:
            try:
                schema.embed([converted_embed])
            except AttributeError:
                if strict:
                    self.fail("invalid_embed",
                              embed=embed_name_mapping[converted_embed])
        return schema

    def make_subresource(self, name):
        """Given a subresource name, construct a subresource.

        :param str name: Dumped name of field containing a subresource.
        :raise ValueError: If the name given isn't a valid subresource.
        :returns: A constructed :class:`~drowsy.resource.Resource`

        """
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        field = get_field_by_dump_name(self.make_schema(), dump_name=name)
        if isinstance(field, NestedRelated):
            return field.resource_cls(
                **self._get_resource_kwargs(field.resource_cls)
            )
        raise ValueError("The provided name is not a valid subresource.")

    def fail(self, key, errors=None, exc=None, **kwargs):
        """Raises an exception based on the ``key`` provided.

        :param str key: Failure type, used to choose an error message.
        :param errors: May be used by the raised exception.
        :type errors: dict or None
        :param exc: If another exception triggered this failure, it may
            be provided for a more informative failure.
        :type exc: :exc:`Exception` or None
        :param kwargs: Any additional arguments that may be used for
            generating an error message.
        :raise UnprocessableEntityError: If ``key`` is
            ``"validation_failure"``. Note that in this case, errors
            should preferably be provided.
        :raise BadRequestError: The default error type raised in all
            other cases.

        """
        unproccessable_errors = {"validation_failure", "commit_failure",
                                 "invalid_collection_input"}
        if key in unproccessable_errors:
            raise UnprocessableEntityError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                errors=errors or {},
                **kwargs)
        elif key == "resource_not_found":
            raise ResourceNotFoundError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs
            )
        elif key == "method_not_allowed":
            raise MethodNotAllowedError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs)
        else:
            raise BadRequestError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs)

    def _get_error_message(self, key, **kwargs):
        """Get an error message based on a key name.

        If the error message is a callable, kwargs are passed
        to that callable.

        If ``self.context`` has a ``"gettext" key set to a callable,
        that callable will be passed the resulting string and any
        key word args for the sake of translation.

        :param str key: Key used to access the error messages dict.
        :param dict kwargs: Any additional arguments that may be passed
            to a callable error message, or used to translate and/or
            format an error message string.
        :raise AssertionError: If ``key`` does not exist in the
            error messages dict.
        :return: An error message as a string.
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

    @property
    def schema_cls(self):
        """Get the schema class associated with this resource.

        :return: The class of the schema associated with this resource.

        """
        return self.opts.schema_cls

    def whitelist(self, key):
        """Determine whether a field is valid to be queried.

        Uses the load_only property for the resource's schema fields
        to determine whether the field should be queryable. Also handles
        nested queries with the same logic.

        :param str key: Dot notation field name. For example, if trying
            to query an album, this may look something like
            ``"tracks.playlists.track_id"``.

        """
        split_keys = key.split(".")
        schema = self.schema_cls(**self._get_schema_kwargs(self.schema_cls))
        for i, key in enumerate(split_keys):
            if key in schema.fields:
                field = schema.fields[key]
                if field.load_only:
                    return False
                elif isinstance(field, EmbeddableMixinABC):
                    schema.embed([key])
                    if hasattr(field, "schema"):
                        schema = field.schema
                    else:
                        return False
                elif isinstance(field, NestedRelated):
                    schema = field.schema
                else:
                    if i != (len(split_keys) - 1):
                        return False
            else:
                return False
        return True

    def convert_key_name(self, key):
        """Given a dumped key name, convert to the name of the field.

        :param str key: Name of the field as it was serialized, using
            dot notation for nested fields.
        :return: The key converted from it's dump form to its
            internally used form.

        """
        # TODO - consider making this resource based
        # calling child resource.convert_key_name
        schema = self.schema_cls(**self._get_schema_kwargs(self.schema_cls))
        split_keys = key.split(".")
        result_keys = []
        for key in split_keys:
            field = get_field_by_dump_name(schema, key)
            if field is not None:
                result_keys.append(field.name)
                if isinstance(field, EmbeddableMixinABC):
                    schema.embed([key])
                    if hasattr(field, "schema"):
                        schema = field.schema
                if hasattr(field, "schema"):
                    schema = field.schema
            else:
                # Invalid key name, no matching field found.
                return None
        return ".".join(result_keys)

    @property
    def page_max_size(self):
        """Get the max number of resources to return.

        :return: The maximum number of resources to be
            included in a result.
        :rtype: int or None

        """
        if callable(self._page_max_size):
            if sys.version_info.major == 2:  # pragma: no cover
                func = self._page_max_size.__func__
            else:
                func = self._page_max_size
            return func(self)
        elif self._page_max_size is not None:
            if self._page_max_size == 0:
                return None
            else:
                return self._page_max_size

    @property
    def context(self):
        """Return the schema context for this resource.

        :return: A dictionary containing any context info used for this
            resource.
        :rtype: dict

        """
        if callable(self._context):
            return self._context()
        else:
            if self._context is None:
                self._context = {}
            return self._context

    @context.setter
    def context(self, val):
        """Set context to the provided value.

        :param val: Used to set the current context value.
        :type val: dict, callable, or None

        """
        self._context = val

    def _get_schema_kwargs(self, schema_cls):
        """Get default kwargs for any new schema creation.

        :param schema_cls: The class of the schema being created.
        :return: A dictionary of keyword arguments to be used when
            creating new schema instances.
        :rtype: dict

        """
        return {
            "context": self.context
        }

    def _get_resource_kwargs(self, resource_cls):
        """Get default kwargs for any new sub resource creation.

        :param resource_cls: The class of the resource being created.
        :return: A dictionary of keyword arguments to be used when
            creating child resources.
        :rtype: dict

        """
        return {
            "context": self.context
        }

    def _get_embed_info(self, embeds=None, strict=True):
        """Helper function that handles the supplied embeds.

        :param embeds: A list of relationship and relationship field
            names to be included in the result.
        :type embeds: list or None
        :param bool strict: If ``True``, will raise an exception when
            bad parameters are passed. If ``False``, will quietly ignore
            any bad input and treat it as if none was provided.
        :raise BadRequestError: If ``strict`` is ``True`` and ``embeds``
            are not valid.
        :return: A list of converted embed field names, a dict mapping
            their original name to their converted name, and a list of
            the top level embed fields to be included.
        :rtype: tuple

        """
        # embed converting
        # name mapping used purely for error purposes
        # key is converted name, value is orig attr name
        embed_name_mapping = {}
        converted_embeds = []
        embed_fields = set()
        if embeds is None:
            embeds = []
        for embed in embeds:
            converted_embed = self.convert_key_name(embed)
            embed_name_mapping[converted_embed] = embed
            if converted_embed is None:
                if strict:
                    self.fail("invalid_embed", embed=embed)
            elif converted_embed:
                # used so if a fields param is provided, embeds are
                # still included.
                # e.g. albums?fields=album_id,tracks.track_id
                #             &embeds=tracks.title
                # tracks.title will get added to fields to include.
                embed_fields.add(converted_embed.split(".")[0])
            converted_embeds.append(converted_embed)
        return converted_embeds, embed_name_mapping, embed_fields


class BaseModelResource(BaseResourceABC):

    """Model API Resources should inherit from this object."""

    def __init__(self, session, context=None, page_max_size=None,
                 error_messages=None):
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

        """
        super(BaseModelResource, self).__init__(
            context=context,
            page_max_size=page_max_size,
            error_messages=error_messages)
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

    def _get_resource_kwargs(self, resource_cls):
        """Get default kwargs for any new sub resource creation.

        :param resource_cls: The class of the resource being created.
        :return: A dictionary of keyword arguments to be used when
            creating child resources.
        :rtype: dict

        """
        result = super(BaseModelResource, self)._get_resource_kwargs(
            resource_cls
        )
        result["session"] = self.session
        return result

    def fail(self, key, errors=None, exc=None, **kwargs):
        """Raises an exception based on the ``key`` provided.

        :param str key: Failure type, used to choose an error message.
        :param errors: May be used by the raised exception.
        :type errors: dict or None
        :param exc: If another exception triggered this failure, it may
            be provided for a more informative failure. In the case of
            an ``InvalidMQLException`` being provided when ``key`` is
            ``"invalid_filters"``, that error message will override
            ``self.error_messages["invalid_filters"]``.
        :type exc: :exc:`Exception` or None
        :param kwargs: Any additional arguments that may be used for
            generating an error message.
        :raise UnprocessableEntityError: If ``key`` is
            ``"validation_failure"``. Note that in this case, errors
            should preferably be provided.
        :raise BadRequestError: The default error type raised in all
            other cases.

        """
        if key == "invalid_filters" or key == "invalid_subresource_filters":
            if isinstance(exc, InvalidMQLException):
                if "subquery_key" in kwargs:
                    message = kwargs["subquery_key"] + ": " + str(exc)
                else:
                    message = str(exc)
            else:
                message = self._get_error_message(key, **kwargs)
            raise BadRequestError(
                code=key,
                message=message,
                **kwargs)
        return super(BaseModelResource, self).fail(
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
        """Returns a QueryBuilder object.

        This exists mainly for inheritance purposes.

        """
        return QueryBuilder()

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
            filter_name = field.dump_to or field_name
            filters[filter_name] = ident[i]
        return filters

    def _get_instance(self, ident):
        """Given an identity, get the associated SQLAlchemy instance.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :raise ResourceNotFound: Raised in cases where invalid
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
                whitelist=self.whitelist,
                stack_size_limit=100,
                convert_key_names_func=self.convert_key_name,
                gettext=self.context.get("gettext", None))
            query = self.apply_required_filters(query)
        # TODO - Clean up exceptions after MQLAlchemy update.
        except (TypeError, ValueError, InvalidMQLException):
            self.fail("resource_not_found", ident=ident)
        return query.first()

    def apply_required_filters(self, query, alias=None):
        """Apply required filters on this query.

        Does nothing by default, but can be usefully overridden if you
        want to enforce certain filters on this resource. A simple
        example would be a notifications resource where a filter
        matching the currently logged in user is applied.

        :param query: An already partially constructed sqlalchemy query.
        :type query: :class:`~sqlalchemy.orm.query.Query`
        :param alias: Can optionally be used if this resource is being
            used as a subresource and an alias has been applied.
        :type alias:
        :return: A potentially modified query object.
        :rtype: :class:`~sqlalchemy.orm.query.Query`

        """
        return query

    def _get_query(self, session, filters, subfilters=None, embeds=None,
                   strict=True):
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
        if hasattr(session, "query"):
            query = session.query(self.model)
        else:
            query = session
        # apply filters
        # TODO - better planning for new MQLAlchemy
        try:
            query = self.query_builder.apply_filters(
                query,
                self.model,
                filters=filters,
                whitelist=self.whitelist,
                stack_size_limit=100,
                convert_key_names_func=self.convert_key_name,
                gettext=self.context.get("gettext", None))
        except InvalidMQLException as exc:
            if strict:
                self.fail("invalid_filters", exc=exc)
        # apply subfilters and embeds
        # errors handled with resource.fail in query_builder
        if subfilters:
            query = self.query_builder.apply_subquery_loads(
                query=query,
                resource=self,
                subfilters=subfilters,
                embeds=embeds
            )
        query = self.apply_required_filters(query)
        return query

    def get(self, ident, subfilters=None, fields=None, embeds=None,
            session=None, strict=True):
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
        :type embeds: list or None
        :param session: Optional sqlalchemy session override. May also
            be a partially formed SQLAlchemy query, allowing for
            sub-resource queries by using
            :meth:~`sqlalchemy.orm.query.Query.with_parent`.
        :type session: :class:`~sqlalchemy.orm.session.Session` or
            :class:`~sqlalchemy.orm.query.Query`
        :param bool strict: If ``True``, will raise an exception when
            bad parameters are passed. If ``False``, will quietly ignore
            any bad input and treat it as if none was provided.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise BadRequestError: Invalid fields or embeds will result
            in a raised exception if strict is set to ``True``.
        :return: The resource itself if found.
        :rtype: dict

        """
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
        except (ValueError, TypeError):
            self.fail("resource_not_found", ident=ident)
        instance = query.first()
        if instance is not None:
            return schema.dump(instance).data
        self.fail("resource_not_found", ident=ident)

    def post(self, data):
        """Create a new resource and store it in the db.

        :param dict data: Data used to create a new resource.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The created resource.
        :rtype: dict

        """
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        schema = self.make_schema(partial=False)
        instance = self.model()
        instance, errors = schema.load(
            data, session=self.session, instance=instance)
        if errors:
            self.session.rollback()
            self.fail("validation_failure", errors=errors)
        else:
            self.session.add(instance)
            try:
                self.session.commit()
            except SQLAlchemyError:
                self.session.rollback()
                self.fail("commit_failure")
            return schema.dump(instance).data

    def put(self, ident, data):
        """Replace the current object with the supplied one.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :param dict data: Data used to replace the resource.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The replaced resource.
        :rtype: dict

        """
        obj = data
        instance = self._get_instance(ident)
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        schema = self.make_schema(
            partial=False,
            instance=instance)
        instance, errors = schema.load(
            obj, session=self.session)
        if errors:
            self.session.rollback()
            self.fail("validation_failure", errors=errors)
        if instance:
            try:
                self.session.commit()
            except SQLAlchemyError:  # pragma: no cover
                self.session.rollback()
                self.fail("commit_failure")
            return schema.dump(instance).data

    def patch(self, ident, data):
        """Update the identified resource with the supplied data.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :param dict data: Data used to update the resource.
        :raise ResourceNotFoundError: If no such resource exists.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: The updated resource.
        :rtype: dict

        """
        obj = data
        instance = self._get_instance(ident)
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        schema = self.make_schema(
            partial=True,
            instance=instance)
        instance, errors = schema.load(
            obj, session=self.session)
        if errors:
            self.session.rollback()
            self.fail("validation_failure", errors=errors)
        if instance:
            try:
                self.session.commit()
            except SQLAlchemyError:  # pragma: no cover
                self.session.rollback()
                self.fail("commit_failure")
            return schema.dump(instance).data

    def delete(self, ident):
        """Delete the identified resource.

        :param ident: A value used to identify this resource.
            See :meth:`get` for more info.
        :raise ResourceNotFoundError: If no such resource exists.
        :return: ``None``

        """
        instance = self._get_instance(ident)
        if instance:
            self.session.delete(instance)
            try:
                self.session.commit()
            except SQLAlchemyError:  # pragma: no cover
                self.session.rollback()
                self.fail("commit_failure")
        else:
            self.fail("resource_not_found", ident=ident)

    def get_collection(self, filters=None, subfilters=None, fields=None,
                       embeds=None, sorts=None, offset=None, limit=None,
                       session=None, strict=True):
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
        :type embeds: list or None
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
        :raise BadRequestError: Invalid filters, sorts, fields,
            embeds, offset, or limit will result in a raised exception
            if strict is set to ``True``.
        :return: Resources meeting the supplied criteria.
        :rtype: :class:`ResourceCollection`

        """
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
        query = self._get_query(
            session=session,
            filters=filters,
            subfilters=subfilters,
            embeds=embeds)
        # sort
        if sorts:
            for sort in sorts:
                if not isinstance(sort, SortInfo):
                    raise TypeError("Each sort must be of type SortInfo.")
                try:
                    query = self.query_builder.apply_sorts(
                        query, [sort], self.convert_key_name)
                except AttributeError:
                    if strict:
                        self.fail("invalid_sort_field", field=sort.attr)
        # offset/limit
        if (limit is not None and
                isinstance(self.page_max_size, int) and
                limit > self.page_max_size):
            if strict:
                self.fail("limit_too_high",
                          limit=limit,
                          max_page_size=self.page_max_size)
            limit = self.page_max_size
        if not offset:
            offset = 0
        try:
            query = self.query_builder.apply_offset(query, offset)
        except ValueError:
            if strict:
                self.fail("invalid_offset_value", offset=offset)
        try:
            query = self.query_builder.apply_limit(query, limit)
        except ValueError:
            if strict:
                self.fail("invalid_limit_value", limit=limit)
        records = query.all()
        # get result
        dump = schema.dump(records, many=True)
        return ResourceCollection(dump.data, count)

    def post_collection(self, data):
        """Create multiple resources in the collection of resources.

        :param list data: List of resources to be created.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: ``None``

        """
        if not isinstance(data, list):
            self.fail("invalid_collection_input", data=data)
        for obj in data:
            # NOTE: No risk of BadRequestError here due to no embeds or
            # fields being passed to make_schema
            schema = self.make_schema(partial=False)
            instance, errors = schema.load(obj, self.session)
            if not errors:
                self.session.add(instance)
            else:
                self.session.rollback()
                self.fail("validation_failure", errors=errors)
        try:
            self.session.commit()
        except SQLAlchemyError:  # pragma: no cover
            self.session.rollback()
            self.fail("commit_failure")

    def put_collection(self, data):
        """Raises an error since this method has no obvious use.

        :param list data: A list of object data. Would theoretically
            be used to replace the entire collection.
        :raise MethodNowAllowedError: When not overridden.

        """
        self.fail("method_not_allowed", method="PUT", data=data)

    def patch_collection(self, data):
        """Update a collection of resources.

        Individual items may be updated accordingly as part of the
        request as well.

        :param list data: A list of object data. If the object contains
            a key ``$op`` set to ``"add"``, the object will be added to
            the collection; otherwise the object must already be in the
            collection. If ``$op`` is set to ``"remove"``, it is
            accordingly removed from the collection.
        :raise UnprocessableEntityError: If the supplied data cannot be
            processed.
        :return: ``None``

        """
        if not isinstance(data, list):
            self.fail("invalid_collection_input")
        for obj in data:
            if obj.get("$op") == "add":
                # basically a post
                # NOTE: No risk of BadRequestError here due to no embeds
                # or fields being passed to make_schema
                schema = self.make_schema(partial=False)
                instance, errors = schema.load(obj, self.session)
                if not errors:
                    self.session.add(instance)
                else:
                    self.session.rollback()
                    self.fail("validation_failure", errors=errors)
            elif obj.get("$op") == "remove":
                # basically a delete
                # NOTE: No risk of BadRequestError here due to no embeds
                # or fields being passed to make_schema
                schema = self.make_schema(partial=True)
                instance, errors = schema.load(obj, self.session)
                if not errors:
                    self.session.delete(instance)
                else:
                    self.session.rollback()
                    self.fail("validation_failure", errors=errors)
            else:
                # NOTE: No risk of BadRequestError here due to no embeds
                # or fields being passed to make_schema
                schema = self.make_schema(partial=True)
                instance, errors = schema.load(obj, self.session)
                if errors:
                    self.session.rollback()
                    self.fail("validation_failure", errors=errors)
        try:
            self.session.commit()
        except SQLAlchemyError:  # pragma: no cover
            self.session.rollback()
            self.fail("commit_failure")

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
        :return: ``None``

        """
        filters = filters or {}
        if session is None:
            session = self.session
        query = self._get_query(
            session=session,
            filters=filters,
            strict=strict)
        query.delete()
        try:
            self.session.commit()
        except SQLAlchemyError:  # pragma: no cover
            self.session.rollback()
            self.fail("commit_failure")


class ModelResource(with_metaclass(ResourceMeta, BaseModelResource)):
    __doc__ = BaseModelResource.__doc__
