"""
    drowsy.base
    ~~~~~~~~~~~

    Abstract base classes for Drowsy.

    Needed to avoid circular imports between resource and field.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
import collections.abc
from contextlib import suppress
from marshmallow.fields import Field, Nested, missing_
from marshmallow.utils import is_collection
from marshmallow.validate import ValidationError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.interfaces import ONETOMANY
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
from drowsy import resource_class_registry
from drowsy.exc import (
    BadRequestError, UnprocessableEntityError, MethodNotAllowedError,
    PermissionDeniedError, ResourceNotFoundError, MISSING_ERROR_MESSAGE)
from drowsy.log import Loggable
from drowsy.permissions import AllowAllOpPermissions
from drowsy.utils import get_error_message, get_field_by_data_key


class EmbeddableMixinABC(Field):

    """Mixin to make a field embeddable.

    Should subclass this and override :meth:`_serialize_unembedded` and
    :meth:`_deserialize_unembedded` to handle both situations for when
    the field isn't embedded.

    """

    def __init__(self, *args, **kwargs):
        """Defaults to setting ``embedded`` to ``False``."""
        self._embedded = False
        super(EmbeddableMixinABC, self).__init__(*args, **kwargs)

    @property
    def embedded(self):
        """Return ``True`` if the embedded field is currently active."""
        return self._embedded

    @embedded.setter
    def embedded(self, value):
        """Set the embedded property.

        :param bool value: If ``True``, the field will be included in
            the serialized output.

        """
        self._embedded = value

    def _deserialize_unembedded(self, value, *args, **kwargs):
        """Determine how to deserialize when the field isn't embedded.

        :param value: The value being deserialized.
        :param args: Any positional arguments that were passed to
            the deserializer method.
        :param kwargs: Any keyword arguments that were passed to
            the deserializer method.
        :return: A deserialized value for the field when not embedded.

        """
        raise NotImplementedError

    def _serialize_unembedded(self, attr, obj, *args, **kwargs):
        """Determine how to serialize when the field isn't embedded.

        :param str attr: The attribute or key to get from the object.
        :param str obj: The object to pull the key from.
        :param args: Any positional arguments that were passed to
            the serializer method.
        :param kwargs: Any keyword arguments that were passed to
            the serializer method.
        :return: A serialized value for the field when not embedded.

        """
        raise NotImplementedError

    def deserialize(self, value, *args, **kwargs):
        """Deserialize the provided value.

        Must be overridden in a full implementation of this class.

        :param value: The value to be deserialized.
        :param args: Any positional arguments to potentially be passed
            to the field's deserialization method.
        :param kwargs: Any keyword arguments to potentially be passed
            to the field's deserialization method.
        :raise ValidationError: If an invalid value is passed.
        :return: The deserialized value if embedded, otherwise
            a predetermined value for an unembedded case.

        """
        if not self.embedded:
            return self._deserialize_unembedded(value, *args, **kwargs)
        return super(EmbeddableMixinABC, self).deserialize(
            value, *args, **kwargs
        )

    def serialize(self, attr, obj, *args, **kwargs):
        """Return the field's serialized value if embedded.

        :param str attr: The attribute or key to get from the object.
        :param str obj: The object to pull the key from.
        :param args: Any positional arguments to potentially be passed
            to the field's serialization method.
        :param kwargs: Any keyword arguments to potentially be passed
            to the field's serialization method.
        :raise ValidationError: In case of formatting error.
        :return: The serialized value of the field if embedded,
            otherwise a predetermined value for an unembedded case.

        """
        if self.embedded:
            return super(EmbeddableMixinABC, self).serialize(
                attr, obj, *args, **kwargs)
        return self._serialize_unembedded(attr, obj, *args, **kwargs)


class NestedPermissibleABC(Nested, Loggable):

    """Abstract base class for a nested permissible field.

    Provided to make subclassing permissibles and nestables
    easier without being tied to SQLAlchemy.

    """

    default_error_messages = {
        "invalid_operation": "Unable to process entity.",
        "permission_denied": ("You do not have the appropriate permissions "
                              "to perform this action."),
        "invalid_remove": "Object not found in list; unable to be removed.",
        "invalid_add": "Object already in list; unable to add it again."
    }

    def __init__(self, nested, default=missing_, exclude=tuple(), only=None,
                 many=False, permissions_cls=None, **kwargs):
        """Initialize a nested field with permissions.

        :param nested: The Resource class or class name (string) to
            nest.
        :param default: Default value to use if attribute is missing.
        :param exclude: Fields to exclude.
        :type exclude: list, tuple, or None
        :param only: A tuple or string of the field(s) to marshal. If
            ``None``, all fields will be marshalled. If a field name
            (string) is given, only a single value will be returned as
            output instead of a dictionary. This parameter takes
            precedence over ``exclude``.
        :type only: tuple, str, or None
        :param bool many: Whether the field is a collection of objects.
        :param permissions_cls: The class of permissions to apply to
            this nested field. Defaults to allowing all nested
            operations.
        :param kwargs: The same keyword arguments that
            :class:`~marshmallow.fields.Field` receives.

        """
        super(NestedPermissibleABC, self).__init__(
            nested=nested,
            default=default,
            exclude=exclude,
            only=only,
            many=many,
            **kwargs)
        self._resource = None
        self.permissions_cls = permissions_cls or AllowAllOpPermissions

    def _get_resource_kwargs(self):
        """Get kwargs for creating a resource for this instance.

        :return: Dictionary of keyword argument to be passed
            to a resource initializer.
        :rtype: dict

        """
        return {
            "context": getattr(self.parent, 'context', {}),
            "parent_field": self
        }

    @property
    def resource(self):
        """The instance of the nested Resource object."""
        if not self._resource:
            # Inherit context from parent.
            context = getattr(self.parent, 'context', {})
            if isinstance(self.nested, BaseResourceABC):
                self._resource = self.nested
                self._resource.context.update(context)
            else:
                if isinstance(self.nested, type) and \
                        issubclass(self.nested, BaseResourceABC):
                    resource_cls = self.nested
                elif isinstance(self.nested, str):
                    resource_cls = resource_class_registry.get_class(
                        self.nested)
                else:
                    resource_cls = None
                if resource_cls:
                    self._resource = resource_cls(
                        **self._get_resource_kwargs())
            if not isinstance(self._resource, BaseResourceABC):
                raise ValueError(
                    "Nested fields must be passed a subclass of "
                    "BaseResourceABC.")
        return self._resource

    @property
    def schema(self):
        """The schema corresponding to this nested collection."""
        return self.resource.schema

    def _permissible(self, permissions, operation, obj_data, instance,
                     errors, index, strict):
        """Returns true of the operation being taken is allowed.

        :param permissions: An instance of a permissions object.
        :type permissions: :class:`~drowsy.permissions.OpPermissionsABC`
        :param str operation: The type of operation to check permissions
            on.
        :param dict obj_data: The user submitted data for the individual
            object.
        param instance: An instance of the object with data already
            loaded into it.
        :param index: index at which to insert the error messages
            into the errors dict. ``None`` if the operation is on
            a non list nested value or sub-object.
        :type index: int or None
        :param dict errors: The error dictionary to be modified.
        :param bool strict: ``True`` if an error should be raised.
        :raise ValidationError: When in strict mode if not
            permissible.
        :return: ``True`` if permissible, ``False`` otherwise.
        :rtype: bool

        """
        # TODO - raise PermissionDeniedError instead?
        # Currently bad permissions on a nested op will get treated like
        # any other validation error.
        permissible = permissions.check(
            operation=operation,
            obj_data=obj_data,
            instance=instance,
            context=self.context)
        if not permissible:
            simple_key = "permission_denied"
            key = simple_key + "_" + operation
            if key not in self.error_messages:
                key = simple_key
            self._handle_op_failure(
                key=key,
                errors=errors,
                index=index,
                strict=strict,
                operation=operation
            )
        return permissible

    def _parent_contains_child(self, parent, instance):
        """Checks if the parent already contains the given instance.

        Only the attr this field is related to is checked.

        :param parent: An object whose attr for this field may
            contain this instance as a child object.
        :param instance: A potential child object of the parent.
        :return: ``True`` if the parent attr already contains the
            instance, ``False`` otherwise.
        :rtype: bool

        """
        raise NotImplementedError

    def _get_identified_instance(self, obj_data):
        """Get a formed instance using the unique identifier of the obj.

        :param obj_data: Likely a dict, but could be any user provided
            data.
        :return: An instance based on the identifier contained in the
            user supplied data.

        """
        raise NotImplementedError

    def _perform_operation(self, operation, parent, instance, errors, index,
                           strict=True):
        """Perform an operation on the parent with a supplied instance.

        Example:
        If this field corresponds to the `tracks` collection of a parent
        `album` object, then the provided instance should be a `track`
        object, and the action might be to `"add"` or `"remove"` the
        provided `track` instance from the parent `album`.

        :param str operation:`"add"` or `"remove"` for collections, or
            `"set"` for one to one relations. May also be any custom
            operations manually defined.
        :param parent: Object containing the attribute the operation
            is being performed on.
        :param instance: A potential child object of the parent.
        :param index: If the relationship is of the many variety, the
            index at which this child was in the input.
        :type index: int or None
        :param dict errors: Dict of errors for this field. Any issue
            that arises while performing the intended operation will
            be added to this dict (at the provided index if supplied).
        :param bool strict: If ``True``, an exception will be raised for
            an encountered error. Otherwise, the error will simply be
            included in the provided `error` dict and things will
            proceed as normal.
        :raise ValidationError: If there's an error when in strict mode.
        :return: The corresponding attr for this field with the provided
            operation performed on it.

        """
        raise NotImplementedError

    def _load_existing_instance(self, obj_data, instance):
        """Deserialize the provided data into an existing instance.

        :param obj_data: Likely a dict, but could be any user provided
            data.
        :param instance: An instance perhaps fetched from a database.
            The data provided will be loaded into this instance.
        :return: Any errors that came up, and the instance.

        """
        raise NotImplementedError

    def _load_new_instance(self, obj_data):
        """Deserialize the provided data into a new instance.

        :param obj_data: Likely a dict, but could be any user provided
            data.
        :return: Any errors that came up, and the instance.

        """
        raise NotImplementedError

    def _get_permission_cls_kwargs(self):
        """Get any kwargs for initializing the permissions cls.

        May want to override this to provide more info to a custom
        permissions class.

        :return: A dictionary of key word arguments.
        :rtype: dict

        """
        return {}

    def _handle_op_failure(self, key, errors, index=None,
                           strict=True, **kwargs):
        """Generate a proper error for nested operations.

        :param str key: The error message key to use for failure.
        :param dict errors: The error dictionary to be modified.
        :param index: index at which to insert the error messages
            into the errors dict. ``None`` if the operation is on
            a non list nested field or sub-object.
        :type index: int or None
        :param bool strict: ``True`` if an error should be raised.
        :param kwargs: Any additional arguments to pass to
            :meth:`fail` when generating the error message.
        :raise ValidationError: When in strict mode.
        :return: ``None``

        """
        try:
            raise self.make_error(key, **kwargs)
        except ValidationError as exc:
            if index is not None:
                errors[index] = {"$op": exc.messages}
            else:
                errors["$op"] = exc.messages
            if strict:
                raise ValidationError(errors)

    def _deserialize(self, value, *args, **kwargs):
        """Deserialize data into a nested attribute.

        In the case of a nested field with many items, the behavior of
        this field varies in a few key ways depending on whether the
        parent form has ``partial`` set to ``True`` or ``False``.
        If ``True``, items can be explicitly added or removed from a
        collection, but the rest of the collection will remain
        intact.
        If ``False``, the collection will be set to an empty list, and
        only items included in the supplied data will in the
        collection.
        Important to note also that updates to items contained in this
        collection will be done so using ``partial=True``, regardless
        or what the value of the parent schema's ``partial`` attribute
        is. The only exception to this is in the creation of a new item
        to be placed in the nested collection, in which case
        ``partial=False`` is always used.

        :param value: Data for this field.
        :type value: list of dict or dict
        :return: The deserialized form of this nested field. In the
            case of a value that doesn't use a list, this is
            a single object (or ``None``). Otherwise a list of objects
            is returned.

        """
        permissions = self.permissions_cls(**self._get_permission_cls_kwargs())
        # Handle removing required in places where a SQLAlchemy
        # relationship will automatically fill in the value.
        relationship = getattr(self.parent.opts.model, self.name)
        child_model = self.schema.opts.model
        backref_name = relationship.prop.backref
        if backref_name:
            backref_name = backref_name[0]
        else:
            backref_name = relationship.prop.back_populates
        if backref_name:
            backref_field = self.schema.fields.get(backref_name)
            if backref_field:
                backref_field.required = False
        if relationship.prop.direction == ONETOMANY:
            # For relationship Album.tracks
            # we want to remove "required" for TrackSchema.album_id
            # and/or TrackSchema.album.
            primary_expressions = []
            # First, figure out the join conditions
            if isinstance(relationship.prop.primaryjoin, BinaryExpression):
                primary_expressions.append(relationship.prop.primaryjoin)
            elif isinstance(relationship.prop.primaryjoin, BooleanClauseList):
                primary_expressions = relationship.prop.primaryjoin.clauses
            for expression in primary_expressions:
                # find if left or right is the parent side
                remote_side = relationship.prop.remote_side
                left_table = expression.left.table
                right_table = expression.right.table
                child_table = inspect(child_model).mapper.local_table
                if left_table == child_table and right_table == child_table:
                    # Self referential one to many...
                    if expression.right in remote_side:
                        child_side = expression.right
                    else:
                        child_side = expression.left  # pragma: no cover
                elif left_table == child_table:
                    child_side = expression.left  # pragma: no cover
                    # tests hit the below condition, and what happens
                    # after is equivalent...no need for coverage
                elif right_table == child_table:
                    child_side = expression.right
                else:
                    # Shouldn't ever get here...
                    raise ValueError  # pragma: no cover
                child_insp = inspect(inspect(child_model).class_)
                for column_key in child_insp.columns.keys():
                    if child_insp.columns[column_key].key == child_side.key:
                        fk_field = self.schema.fields.get(column_key)
                        if fk_field:
                            fk_field.required = False
                        break
        result = None
        parent = self.parent.instance
        if self.many:
            obj_datum = value
            if not is_collection(value):
                raise self.make_error('type', input=value,
                                      type=value.__class__.__name__)
            else:
                nested_opts = self.parent.nested_opts or {}
                nested_opt = nested_opts.get(self.name)
                if nested_opt is not None and not nested_opt.partial:
                    # Full update of this collection, reset it to empty
                    setattr(parent, self.name, [])
        else:
            # Treat this like a list until it comes time to actually
            # to actually modify the value.
            obj_datum = [value]
        errors = {}
        # each item in value is a sub instance
        for i, obj_data in enumerate(obj_datum):
            if not isinstance(obj_data, dict):
                raise self.make_error(
                    'type',
                    input=obj_data,
                    type=obj_data.__class__.__name__)
            # check if there's an explicit operation included
            operation = None
            if hasattr(obj_data, "pop"):
                operation = obj_data.pop("$op", None)
            is_new_obj = False
            # check whether this data has value(s) for
            # the identifier columns.
            with suppress(TypeError):
                instance = self._get_identified_instance(obj_data)
            if instance is None:
                is_new_obj = True
            if operation is None:
                if self.many:
                    operation = "add"
                else:
                    operation = "set"
            if self._permissible(permissions=permissions,
                                 obj_data=obj_data,
                                 operation=operation,
                                 index=i if self.many else None,
                                 errors=errors,
                                 strict=True,
                                 instance=instance):
                loaded_instance = None
                if is_new_obj:
                    try:
                        # TODO - Need some check here to ensure that
                        # this is infact a newly created instance.
                        loaded_instance = self._load_new_instance(obj_data)
                        instance = loaded_instance
                        sub_errors = {}
                    except ValidationError as exc:
                        sub_errors = exc.messages
                else:
                    try:
                        loaded_instance = (
                            self._load_existing_instance(obj_data, instance))
                        sub_errors = {}
                    except ValidationError as exc:
                        sub_errors = exc.messages
                if sub_errors:
                    if self.many:
                        errors[i] = sub_errors
                    else:
                        errors = sub_errors
                    continue
                if (instance is None and self.many) or (
                        instance != loaded_instance):  # pragma: no cover
                    # This acts as a fail safe
                    try:
                        raise self.make_error("invalid_operation", **kwargs)
                    except ValidationError as exc:
                        errors[i] = exc.messages
                        if self.many:
                            errors[i] = sub_errors
                        else:
                            errors = sub_errors
                        continue
                result = self._perform_operation(
                    operation=operation,
                    parent=parent,
                    instance=loaded_instance,
                    index=i,
                    errors=errors,
                    strict=True)
        if errors:
            raise ValidationError(errors)
        return result or getattr(parent, self.name)


class ResourceABC(Loggable):

    """Abstract resource base class."""

    @property
    def options(self):
        """Get the available options for this resource.

        :return: A list of available options for this resource.
            Values can include GET, POST, PUT, PATCH, DELETE, HEAD, and
            OPTIONS.
        :rtype: list


        """
        raise NotImplementedError

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

    @property
    def schema(self):
        """The schema for this resource.

        Note that :meth:`make_schema` has the ability to set the
        schema as well.

        """
        raise NotImplementedError

    @property
    def context(self):
        """Return the schema context for this resource.

        :return: A dictionary containing any context info used for this
            resource.
        :rtype: dict

        """
        raise NotImplementedError

    def _get_schema_kwargs(self, schema_cls):
        """Get default kwargs for any new schema creation.

        :param schema_cls: The class of the schema being created.

        """
        raise NotImplementedError

    def make_schema(self, subfilters=None, fields=None, embeds=None,
                    partial=False, instance=None, strict=True):
        """Used to generate a schema for this request.

        :param subfilters: A dict of filters, with each key being
            the dot notation of the relationship they are to be
            applied to.
        :type subfilters: dict or None
        :param fields: Names of fields to be included in the result.
        :type fields: list or None
        :param embeds: A list of child resources (and/or their fields)
            to include in the response.
        :type embeds: collection or None
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


class BaseResourceABC(SchemaResourceABC, NestableResourceABC):

    """Base Schema Resource abstract class to inherit from."""

    _default_error_messages = {
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
        "invalid_subresource": "%(subresource_key)s is not a subresource.",
        "invalid_subresource_limit": ("The limit (%(supplied_limit)s) given "
                                      "for %(subresource_key)s subresource is "
                                      "too high. The max limit is "
                                      "%(max_limit)s."),
        "invalid_subresource_sorts": ("The subresource %(subresource_key)s "
                                      "can not have sorts applied without "
                                      "a limit or offset being supplied."),
        "permission_denied": "Permission denied.",
        "unexpected_error": "An unexpected error has occurred."
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

    def __init__(self, context=None, page_max_size=None,
                 error_messages=None, parent_field=None, *args,
                 **kwargs):
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
        :param parent_field: The field that owns this resource, if
            applicable. Likely some variety of
            :class:`NestedPermissibleABC`.
        :type parent_field: Field

        """
        self._page_max_size = page_max_size
        self.parent_field = parent_field
        if self._page_max_size is None and hasattr(self.opts, "page_max_size"):
            self._page_max_size = self.opts.page_max_size
        self._context = context
        self._schema = None
        # Set up error messages
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, '_default_error_messages', {}))
        if isinstance(self.opts.error_messages, dict):
            messages.update(self.opts.error_messages)
        messages.update(error_messages or {})
        self.error_messages = messages

    @property
    def schema(self):
        """The schema for this resource.

        Note that :meth:`make_schema` has the ability to set the
        schema as well.

        """
        if not self._schema:
            self.make_schema()
        return self._schema

    def make_schema(self, fields=None, subfilters=None, embeds=None,
                    partial=False, instance=None, strict=True):
        """Used to generate a schema for this request.

        Updates ``self.schema``, and returns the new schema as well.

        :param fields: Names of fields to be included in the result.
        :type fields: list or None
        :param subfilters: Filters to be applied to children of this
            resource. Each key in the dictionary should be a dot
            notation key corresponding to a subfilter.
        :type subfilters: dict or None
        :param embeds: A list of relationship and relationship field
            names to be included in the result.
        :type embeds: collection or None
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
        if isinstance(embeds, collections.abc.Iterable):
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
                        raise self.make_error("invalid_field", field=field)
                elif converted_field:
                    converted_fields.append(converted_field)
        if converted_fields:
            for embed_field in converted_embeds:
                embed = embed_field.split(".")[0]
                if embed not in converted_fields:
                    converted_fields.append(embed)
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
            except AttributeError:  # pragma: no cover
                # _get_embed_info should catch this
                # keeping here as a safeguard
                if strict:
                    raise self.make_error(
                        "invalid_embed",
                        embed=embed_name_mapping[converted_embed])
        self._schema = schema
        return schema

    def make_subresource(self, name):
        """Given a subresource name, construct a subresource.

        :param str name: Dumped name of field containing a subresource.
        :raise ValueError: If the name given isn't a valid subresource.
        :returns: A constructed :class:`~drowsy.resource.Resource`

        """
        # NOTE: No risk of BadRequestError here due to no embeds or
        # fields being passed to make_schema
        field = get_field_by_data_key(self.schema, data_key=name)
        if isinstance(field, NestedPermissibleABC):
            return field.resource
        raise ValueError("The provided name is not a valid subresource.")

    def make_error(self, key, errors=None, exc=None, **kwargs):
        """Returns an exception based on the ``key`` provided.

        :param str key: Failure type, used to choose an error message.
        :param errors: May be used by the raised exception.
        :type errors: dict or None
        :param exc: If another exception triggered this failure, it may
            be provided for a more informative failure.
        :type exc: :exc:`Exception` or None
        :param kwargs: Any additional arguments that may be used for
            generating an error message.
        :return: `UnprocessableEntityError` If ``key`` is
            ``"validation_failure"``. Note that in this case, errors
            should preferably be provided. In all other cases a
            `BadRequestError` is returned.

        """
        unproccessable_errors = {"validation_failure", "commit_failure",
                                 "invalid_collection_input"}
        if key in unproccessable_errors:
            return UnprocessableEntityError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                errors=errors or {},
                **kwargs)
        elif key == "resource_not_found":
            return ResourceNotFoundError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs
            )
        elif key == "method_not_allowed":
            return MethodNotAllowedError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs)
        elif key == "permission_denied":
            return PermissionDeniedError(
                code=key,
                errors=errors or {},
                message=self._get_error_message(key, **kwargs),
                **kwargs)
        else:
            return BadRequestError(
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
        schema = self.schema_cls(**self._get_schema_kwargs(self.schema_cls))
        split_keys = key.split(".")
        if len(split_keys) == 1 and split_keys[0] == "":
            return True
        while split_keys:
            key = split_keys.pop(0)
            if key in schema.fields:
                field = schema.fields[key]
                if field.load_only:
                    return False
                elif not split_keys:
                    return True
                elif isinstance(field, EmbeddableMixinABC):
                    schema.embed([key])
                if isinstance(field, Nested):
                    if isinstance(field, NestedPermissibleABC):
                        with suppress(ValueError, TypeError):
                            subresource = self.make_subresource(
                                field.data_key or key)
                            return subresource.whitelist(".".join(split_keys))
                    # attempting to use the subresource didn't work
                    # fall back to simply using the field's schema
                    schema = field.schema
            else:
                return False
        return True  # pragma no cover

    def convert_key_name(self, key):
        """Given a dumped key name, convert to the name of the field.

        :param str key: Name of the field as it was serialized, using
            dot notation for nested fields.
        :return: The key converted from it's dump form to its
            internally used form, or None if it can't successfully be
            converted.
        :rtype: str or None

        """
        schema = self.schema_cls(**self._get_schema_kwargs(self.schema_cls))
        split_keys = key.split(".")
        result_keys = []
        while split_keys:
            key = split_keys.pop(0)
            field = get_field_by_data_key(schema, key)
            if field is not None:
                result_keys.append(field.name)
                if not split_keys:
                    return ".".join(result_keys)
                if isinstance(field, EmbeddableMixinABC):
                    schema.embed([field.name])
                if isinstance(field, Nested):
                    if isinstance(field, NestedPermissibleABC):
                        with suppress(ValueError, TypeError):
                            subresource = self.make_subresource(
                                field.data_key or key)
                            result_keys += subresource.convert_key_name(
                                ".".join(split_keys)
                            ).split(".")
                            return ".".join(result_keys)
                    # attempting to use the subresource didn't work
                    # fall back to simply using the field's schema
                    schema = field.schema
                else:
                    return None
            else:
                # Invalid key name, no matching field found.
                return None
        # failsafe: should never reach this point
        return ".".join(result_keys)  # pragma: no cover

    @property
    def page_max_size(self):
        """Get the max number of resources to return.

        :return: The maximum number of resources to be
            included in a result.
        :rtype: int or None

        """
        if callable(self._page_max_size):
            return self._page_max_size(self)
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
            "context": self.context,
            "parent_resource": self
        }

    def _get_embed_info(self, embeds=None, strict=True):
        """Helper function that handles the supplied embeds.

        :param embeds: A list of relationship and relationship field
            names to be included in the result.
        :type embeds: collection or None
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
                    raise self.make_error("invalid_embed", embed=embed)
            elif converted_embed:
                # used so if a fields param is provided, embeds are
                # still included.
                # e.g. albums?fields=album_id,tracks.track_id
                #             &embeds=tracks.title
                # tracks.title will get added to fields to include.
                embed_fields.add(converted_embed.split(".")[0])
            converted_embeds.append(converted_embed)
        return converted_embeds, embed_name_mapping, embed_fields

