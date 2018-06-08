"""
    drowsy.fields
    ~~~~~~~~~~~~~

    Marshmallow fields used in resource schemas.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from marshmallow.compat import basestring
from marshmallow.fields import Field, missing_
from marshmallow.utils import get_value
from marshmallow_sqlalchemy.fields import Related, ensure_list
from sqlalchemy.inspection import inspect
from drowsy.base import EmbeddableMixinABC, NestedPermissibleABC


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


class NestedRelated(NestedPermissibleABC, Related):

    """A nested relationship field for use in `ModelResourceSchema`."""

    def __init__(self, nested, default=missing_, exclude=tuple(), only=None,
                 many=False, column=None, permissions_cls=None, **kwargs):
        """Initialize a nested related field.

        :param nested: The Schema class or class name (string) to nest,
            or ``"self"`` to nest a :class:`~marshmallow.schema.Schema`
            within itself.
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
        :param list columns: Optional column names on related model.
            If not provided, the primary key(s) of the related model
            will be used.
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
        columns = [
            self.related_model.__mapper__.columns[key_name]
            for key_name in self.schema.id_keys
        ]
        return [
            self.related_model.__mapper__.get_property_by_column(column)
            for column in columns
        ]

    def _get_resource_kwargs(self):
        """Get kwargs for creating a resource for this instance.

        :return: Dictionary of keyword argument to be passed
            to a resource initializer.
        :rtype: dict

        """
        result = super(NestedRelated, self)._get_resource_kwargs()
        result["session"] = self.session
        return result

    def _parent_contains_child(self, parent, instance, relationship_name):
        """Checks if the parent relation contains the given instance.

        Only the relationship this field is related to is checked.

        :param parent: An object whose relationship for this field may
            contain this instance as a child object.
        :param instance: A potential child object of the parent.
        :param str relationship_name: The name of the relationship
            we're checking on `parent`.
        :return: ``True`` if the parent attr already contains the
            instance, ``False`` otherwise.
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

    def _get_identified_instance(self, obj_data):
        """Get a formed instance using the unique identifier of the obj.

        :param obj_data: Likely a dict, but could be any user provided
            data.
        :return: A SQLAlchemy object instance based on the identifier
            contained in the user supplied data, or ``None`` if no
            instance could be found.

        """
        with self.session.no_autoflush:
            # If the parent object hasn't yet been persisted,
            # autoflush can cause an error since it is yet
            # to be fully formed.
            # TODO - Someway of enforcing schema type?
            return self.schema.get_instance(data=obj_data)

    def _perform_operation(self, operation, parent, instance, errors, index,
                           strict=True):
        """Perform an operation on the parent with a supplied instance.

        Example:
        If this field corresponds to the `tracks` collection of a parent
        ``album`` object, then the provided instance should be a
        ``track`` object, and the action might be to ``"add"`` or
        ``"remove"`` the provided ``track`` instance from the parent
        ``album``.

        :param str operation: ``"add"`` or ``"remove"`` for collections,
            or ``"set"`` for one to one relations. May also be any
            custom operations manually defined.
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
            included in the provided ``errors`` dict and things will
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
