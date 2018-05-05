"""
    drowsy.fields
    ~~~~~~~~~~~~~

    Marshmallow fields used in resource schemas.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from marshmallow.compat import basestring
from marshmallow.fields import Field, Nested, missing_
from marshmallow.utils import is_collection, get_value
from marshmallow.validate import ValidationError
from marshmallow_sqlalchemy.fields import Related, ensure_list
from sqlalchemy.inspection import inspect
from drowsy import resource_class_registry
from drowsy.permissions import AllowAllOpPermissions


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

        :param bool value: If `True`, the field will be included in
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

        :param str attr: The attibute or key to get from the object.
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


class NestedPermissibleABC(Nested):

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
                 many=False, resource_cls=None,
                 permissions_cls=None, **kwargs):
        """Initialize a nested field with permissions.

        :param nested: The Schema class or class name (string) to nest,
            or ``"self"`` to nest a :class:`~marshmallow.schema.Schema`
            within itself.
        :param default: Default value to use if attribute is missing.
        :param exclude: Fields to exclude.
        :type exclude: list, tuple, or None
        :param only: A tuple or string of the field(s) to marshal. If
            `None`, all fields will be marshalled. If a field name
            (string) is given, only a single value will be returned as
            output instead of a dictionary. This parameter takes
            precedence over ``exclude``.
        :type only: tuple, str, or None
        :param bool many: Whether the field is a collection of objects.
        :param resource_cls: Either the class or the name of the
            resource class associated with this nested field. Useful for
            dynamic nested routing.
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
        self._resource_cls = resource_cls
        self.permissions_cls = permissions_cls or AllowAllOpPermissions

    @property
    def resource_cls(self):
        """Get the nested resource class."""
        if isinstance(self._resource_cls, basestring):
            return resource_class_registry.get_class(self._resource_cls)
        return self._resource_cls

    @property
    def schema(self):
        """The schema corresponding to this nested collection."""
        result = super(NestedPermissibleABC, self).schema
        # TODO - self.root?
        # NOTE - root and parent were removed from schemas in
        # marshmallow. May want to rethink this.
        result.root = self.root
        result.parent = self
        return result

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
            into the errors dict. `None` if the operation is on
            a non list nested value or sub-object.
        :type index: int or None
        :param dict errors: The error dictionary to be modified.
        :param bool strict: `True` if an error should be raised.
        :raise ValidationError: When in strict mode if not
            permissible.
        :return: `True` if permissible, `False` otherwise.
        :rtype: bool

        """
        permissible = permissions.check(
            operation=operation,
            obj_data=obj_data,
            instance=instance,
            context=self.context)
        if not permissible:
            key = "permission_denied"
            detailed_key = key + "_" + operation
            if detailed_key in self.error_messages:
                key = detailed_key
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
        :return: `True` if the parent attr already contains the
            instance, `False` otherwise.
        :rtype: bool

        """
        raise NotImplementedError

    def _has_identifier(self, obj_data):
        """Determine if the provided data has a unique identifier.

        :param obj_data: Likely a dict, but could be any user provided
            data.
        :return: `True` or `False`.
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
        :param bool strict: If `True`, an exception will be raised for
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
            into the errors dict. `None` if the operation is on
            a non list nested field or sub-object.
        :type index: int or None
        :param bool strict: `True` if an error should be raised.
        :param kwargs: Any additional arguments to pass to
            :meth:`fail` when generating the error message.
        :raise ValidationError: When in strict mode.
        :return: `None`

        """
        try:
            self.fail(key, **kwargs)
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
        parent form has `partial` set to `True` or `False`.
        If `True`, items can be explicitly added or removed from a
        collection, but the rest of the collection will remain
        intact.
        If `False`, the collection will be set to an empty list, and
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
            a single object (or `None`). Otherwise a list of objects
            is returned.

        """
        permissions = self.permissions_cls(**self._get_permission_cls_kwargs())
        strict = self.parent.strict
        result = None
        parent = self.parent.instance
        if self.many:
            obj_datum = value
            if not is_collection(value):
                self.fail('type', input=value, type=value.__class__.__name__)
            else:
                if not self.parent.partial:
                    setattr(parent, self.name, [])
        else:
            # Treat this like a list until it comes time to actually
            # to actually modify the value.
            obj_datum = [value]
        errors = {}
        # each item in value is a sub instance
        for i, obj_data in enumerate(obj_datum):
            if not isinstance(obj_data, dict):
                self.fail('type', input=obj_data, type=obj_data.__class__.__name__)
            # check if there's an explicit operation included
            loaded_instance = None
            if hasattr(obj_data, "pop"):
                operation = obj_data.pop("$op", None)
            else:
                operation = None
            is_new_obj = False
            # check whether this data has value(s) for
            # the indentifier columns.
            try:
                if self._has_identifier(obj_data):
                    instance = self._get_identified_instance(obj_data)
                else:
                    instance = None
            except TypeError:
                # Upon deserialization, UnprocessableEntity will get
                # raised.
                # TODO - Should sure this up.
                instance = None
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
                                 index=i,
                                 errors=errors,
                                 strict=strict,
                                 instance=instance):
                if is_new_obj:
                    loaded_instance, sub_errors = self._load_new_instance(
                        obj_data)
                    instance = loaded_instance
                else:
                    loaded_instance, sub_errors = self._load_existing_instance(
                        obj_data, instance)
                if sub_errors:
                    if self.many:
                        errors[i] = sub_errors
                    else:
                        errors = sub_errors
                    if strict:
                        raise ValidationError(errors)
                    else:
                        continue
            # TODO - not sure if this is appropriate error handling
            if (instance is None and self.many) or instance != loaded_instance:
                try:
                    self.fail("invalid_operation", **kwargs)
                except ValidationError as e:
                    errors[i] = e.messages
                    if strict:
                        raise ValidationError(errors)
            result = self._perform_operation(
                operation=operation,
                parent=parent,
                instance=loaded_instance,
                index=i,
                errors=errors,
                strict=strict)
        if errors:
            raise ValidationError(errors)
        return result


class NestedRelated(NestedPermissibleABC, Related):

    """A nested relationship field for use in a `ModelSchema`."""

    def __init__(self, nested, default=missing_, exclude=tuple(), only=None,
                 many=False, column=None, resource_cls=None,
                 permissions_cls=None, **kwargs):
        """Initialize a nested related field.

        :param nested: The Schema class or class name (string) to nest,
            or ``"self"`` to nest a :class:`~marshmallow.schema.Schema`
            within itself.
        :param default: Default value to use if attribute is missing.
        :param exclude: Fields to exclude.
        :type exclude: list, tuple, or None
        :param only: A tuple or string of the field(s) to marshal. If
            `None`, all fields will be marshalled. If a field name
            (string) is given, only a single value will be returned as
            output instead of a dictionary. This parameter takes
            precedence over ``exclude``.
        :type only: tuple, str, or None
        :param bool many: Whether the field is a collection of objects.
        :param list columns: Optional column names on related model.
            If not provided, the primary key(s) of the related model
            will be used.
        :param resource_cls: Either the class or the name of the
            resource class associated with this relationship. Useful for
            dynamic nested routing.
        :param permissions_cls: The class of permissions to apply to
            this relationship. Defaults to allowing all relationship
            operation. May be used to limit the operations that can
            be done.
        :param kwargs: The same keyword arguments that
            :class:`~marshmallow.fields.Field` receives.

        """
        super(NestedRelated, self).__init__(
            nested=nested,
            default=default,
            exclude=exclude,
            only=only,
            many=many,
            resource_cls=resource_cls,
            permissions_cls=permissions_cls,
            **kwargs)
        self.columns = ensure_list(column or [])

    @property
    def model(self):
        """The model associated with this relationship."""
        schema = self.parent
        return schema.opts.model

    @property
    def related_keys(self):
        """Gets a list of id keys associated with this nested obj.

        Note the hierarchy of id keys to return:

        1. If the attached schema for this nested field has an id_keys
           attr, use those keys.
        2. Else, if this field had a columns arg passed when
           initialized, use those column names.
        3. Else, use the primary key columns.

        """
        # schema here is for this nested field, not the parent.
        if hasattr(self.schema, "id_keys"):
            columns = [
                self.related_model.__mapper__.columns[key_name]
                for key_name in self.schema.id_keys
            ]
            return [
                self.related_model.__mapper__.get_property_by_column(column)
                for column in columns
            ]
        return super(NestedRelated, self).related_keys

    def _parent_contains_child(self, parent, instance, relationship_name):
        """Checks if the parent relation contains the given instance.

        Only the relationship this field is related to is checked.

        :param parent: An object whose relationship for this field may
            contain this instance as a child object.
        :param instance: A potential child object of the parent.
        :param str relationship_name: The name of the relationship
            we're checking on `parent`.
        :return: `True` if the parent attr already contains the
            instance, `False` otherwise.
        :rtype: bool

        """
        with_parentable = False
        if self.parent.instance is not None:
            if inspect(self.parent.instance).persistent:
                if self.many:
                    with_parentable = True
                elif getattr(self.parent.instance, relationship_name):
                    with_parentable = True
        if with_parentable:
            in_relation_instance = self.session.query(
                self.related_model).with_parent(
                    self.parent.instance,
                    property=relationship_name).filter_by(**{
                        column.key: getattr(instance, column.key)
                        for column in self.related_keys
                    }).first()
            if in_relation_instance == instance:
                return True
            return False
        else:
            if isinstance(getattr(parent, self.name), list):
                if instance in getattr(parent, self.name):
                    return True
                else:
                    return False
            elif getattr(parent, self.name) == instance:
                return True
            return False

    def _has_identifier(self, obj_data):
        """Determine if the provided data has a unique identifier.

        :param obj_data: Likely a dict, but could be any user provided
            data.
        :return: `True` or `False`.
        :rtype: bool

        """
        has_identifier = True
        for column in self.related_keys:
            field = self.schema.declared_fields.get(column.key)
            if not field:
                return False
            key = field.load_from or column.key
            if key not in obj_data:
                has_identifier = False
        return has_identifier

    def _get_identified_instance(self, obj_data):
        """Get a formed instance using the unique identifier of the obj.

        :param obj_data: Likely a dict, but could be any user provided
            data.
        :return: A SQLAlchemy object instance based on the identifier
            contained in the user supplied data, or `None` if no
            instance could be found.

        """
        with self.session.no_autoflush:
            # If the parent object hasn't yet been persisted,
            # autoflush can cause an error since it is yet
            # to be fully formed.
            instance = self.session.query(
                self.related_model).filter_by(**{
                    column.key: obj_data.get(
                        self.schema.fields[column.key].load_from or
                        column.key)
                    for column in self.related_keys
                }).first()
        return instance

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
        :param bool strict: If `True`, an exception will be raised for
            an encountered error. Otherwise, the error will simply be
            included in the provided `error` dict and things will
            proceed as normal.
        :raise ValidationError: If there's an error when in strict mode.
        :return: The corresponding attr for this field with the provided
            operation performed on it.

        """
        is_instance_in_relation = self._parent_contains_child(
            parent, instance, self.name)
        # Permissions were good, load caused no problems
        # Now perform the actual operation.
        if operation == "remove":
            if is_instance_in_relation:
                if self.parent.partial:
                    # no need to remove if not partial, as the
                    # list will already be empty.
                    relation = getattr(parent, self.name)
                    relation.remove(instance)
            elif strict:
                self._handle_op_failure(
                    "invalid_remove",
                    errors=errors,
                    index=index,
                    strict=strict)
        elif operation is None or operation == "add" or (
                operation == "set" and not self.many):
            if not is_instance_in_relation:
                if self.many:
                    relation = getattr(parent, self.name)
                    relation.append(instance)
                else:
                    setattr(parent, self.name, instance)
            elif operation == "add" and strict:
                self._handle_op_failure(
                    "invalid_add",
                    errors=errors,
                    index=index,
                    strict=strict)
        elif strict:
            self._handle_op_failure(
                "invalid_operation",
                errors=errors,
                index=index,
                strict=strict)
        return getattr(parent, self.name)

    def _load_existing_instance(self, obj_data, instance):
        """Deserialize the provided data into an existing instance.

        :param obj_data: Likely a dict, but could be any user provided
            data.
        :param instance: A SQLAlchemy object instance. The data provided
            will be loaded into this instance.
        :return: Any errors that came up, and the instance.

        """
        return self.schema.load(
            obj_data,
            session=self.session,
            instance=instance,
            partial=True,
            many=False)

    def _load_new_instance(self, obj_data):
        """Deserialize the provided data into a new SQLAlchemy instance.

        :param obj_data: Likely a dict, but could be any user provided
            data.
        :return: Any errors that came up, and the instance.

        """
        return self.schema.load(
            obj_data,
            session=self.session,
            instance=self.related_model(),
            partial=False,
            many=False)


class EmbeddableRelationshipMixin(EmbeddableMixinABC):

    """Defaults to returning a relationship's URL if not embedded."""

    def get_url(self, obj):
        """Get the URL for this relationship.

        :param obj: TODO

        """
        url = ""
        if self.parent and "self" in self.parent.fields:
            url += self.parent.fields["self"].serialize("self", obj)
        relationship_name = self.dump_to or self.name
        url += "/" + relationship_name
        return url

    def _deserialize_unembedded(self, value, *args, **kwargs):
        """Determine how to deserialize when the field isn't embedded.

        :param value: The value being deserialized.
        :param args: Any positional arguments that were passed to
            the deserializer method.
        :param kwargs: Any keyword arguments that were passed to
            the deserializer method.
        :return: The attr of the parent instance unmodified.

        """
        return getattr(self.parent.instance, self.name)

    def _serialize_unembedded(self, attr, obj, *args, **kwargs):
        """Determine how to serialize when the field isn't embedded.

        :param str attr: The attibute or key to get from the object.
        :param str obj: The object to pull the key from.
        :param args: Any positional arguments that were passed to
            the serializer method.
        :param kwargs: Any keyword arguments that were passed to
            the serializer method.
        :return: The url for this relationship.

        """
        return self.get_url(obj)

    def deserialize(self, value, *args, **kwargs):
        """Return the field's deserialized value.

        :param value: The value provided by the user for this field.
            If it's the field's URL, the value is essentially ignored.

        """
        # This isn't exactly perfect, seeing as someone could
        # POST/PATCH/PUT with a string that isn't a valid url,
        # and it would simply be ignored rather than raising
        # an error.
        if self.required and not self.parent.partial:
            self.embedded = True
        elif isinstance(value, basestring):
            self.embedded = False
        return super(EmbeddableRelationshipMixin, self).deserialize(
            value, *args, **kwargs
        )


class Relationship(EmbeddableRelationshipMixin, NestedRelated):

    """Default relationship field.

    When serialized, returns the relationship's assumed URL if not
    embedded. Otherwise, returns the nested values of the relationship.

    """

    pass


class APIUrl(Field):

    """Text field, displays the url of the resource it's attached to."""

    def __init__(self, endpoint_name, *args, **kwargs):
        """TODO

        :param endpoint_name:
        :param args:
        :param kwargs:
        :return:

        """
        super(APIUrl, self).__init__(*args, **kwargs)
        self.endpoint_name = endpoint_name

    def serialize(self, attr, obj, accessor=None):
        """Serialize an API url.

        :param str attr: The attribute name of this field. Unused.
        :param str obj: The object to pull any needed info from.
        :param accessor: Function used to pull values from ``obj``.
            Defaults to :func:`~marshmallow.utils.get_value`.
        :type accessor: callable or None
        :raise ValidationError: In case of formatting problem.
        :return: The serialized API url value.

        """
        # TODO - Better safety checking
        accessor_func = accessor or get_value
        id_keys = self.parent.id_keys
        result = "/" + self.endpoint_name
        for column in id_keys:
            if hasattr(obj, column):
                val = accessor_func(column, obj, missing_)
                result += "/" + str(val)
        return result
