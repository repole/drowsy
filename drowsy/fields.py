"""
    drowsy.fields
    ~~~~~~~~~~~~~

    Marshmallow fields used in model resource schemas.

    :copyright: (c) 2016 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from marshmallow.compat import basestring
from marshmallow.fields import Field, Nested, missing_
from marshmallow.utils import is_collection, get_value
from marshmallow.validate import ValidationError
from marshmallow_sqlalchemy.fields import Related, ensure_list
from drowsy import resource_class_registry
from sqlalchemy.inspection import inspect


class EmbeddableMixin(object):

    """Mixin to make a field embeddable.

    Should subclass this and override :meth:`serialize` and potentially
    add some logic for when the ``embedded`` value changes as well.

    """
    def __init__(self, *args, **kwargs):
        """Defaults to setting ``embedded`` to ``False``."""
        self._embedded = False
        super(EmbeddableMixin, self).__init__(*args, **kwargs)

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

    def serialize(self, *args, **kwargs):
        """Return the field's serialized value if embedded."""
        if self.embedded:
            return super(EmbeddableMixin, self).serialize(*args, **kwargs)
        else:
            return "Embeddable"

    # TODO - Deserialize? Handle passing in strings for a field.


class NestedRelated(Nested, Related):

    """A nested relationship field for use in a `ModelSchema`."""

    def __init__(self, nested, default=missing_, exclude=tuple(), only=None,
                 many=False, column=None, resource_cls=None, **kwargs):
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
        :param resource_cls: Either the class or the name of the
            resource class associated with this relationship. Useful for
            dynamic nested routing.
        :param kwargs: The same keyword arguments that
            :class:`~marshmallow.fields.Field` receives.

        """
        super(NestedRelated, self).__init__(
            nested=nested,
            default=default,
            exclude=exclude,
            only=only,
            many=many,
            **kwargs)
        self._resource_cls = resource_cls
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
        else:
            return super(NestedRelated, self).related_keys

    @property
    def resource_cls(self):
        """Get the nested resource class."""
        if isinstance(self._resource_cls, basestring):
            return resource_class_registry.get_class(self._resource_cls)
        else:
            return self._resource_cls

    @property
    def schema(self):
        """The schema corresponding to this relationship."""
        result = super(NestedRelated, self).schema
        # TODO - self.root?
        result.root = self.root
        result.parent = self
        return result

    def _deserialize(self, value, *args, **kwargs):
        """Deserialize data into a SQLAlchemy relationship field.

        In the case of a relationship with many items, the behavior of
        this field varies in a few key ways depending on whether the
        parent form has `partial` set to `True` or `False`.
        If `True`, items can be explicitly added or removed from a
        relationship, but the rest of the relationship will remain
        intact.
        If `False`, the relationship will be set to an empty list, and
        only items included in the supplied data will in the
        relationship.
        Important to note also that updates to items contained in this
        relationship will be done so using ``partial=True``, regardless
        or what the value of the parent schema's ``partial`` attribute
        is. The only exception to this is in the creation of a new item
        to be placed in the relationship, in which case
        ``partial=False`` is always used.

        :param value: Data for this field.
        :type value: list of dictionaries or dict
        :return: The deserialized form of this relationship. In the
            case of a relationship that doesn't use a list, this is
            a single SQLAlchemy object (or `None`). Otherwise a list
            of SQLAlchemy objects is returned.

        """
        strict = self.parent.strict
        result = None
        parent = self.parent.instance
        if self.many:
            data = value
            if not is_collection(value):
                self.fail('type', input=value, type=value.__class__.__name__)
            else:
                if not self.parent.partial:
                    setattr(parent, self.name, [])
        else:
            # Treat this like a list relation until it comes time
            # to actually modify the relationship.
            data = [value]
        errors = {}
        # each item in value is a sub instance
        for i, obj in enumerate(data):
            # check if there's an explicit operation included
            if hasattr(obj, "pop"):
                operation = obj.pop("$op", None)
            else:
                operation = None
            # check wheather this data has value(s) for
            # the indentifier columns.
            has_identifier = True
            for column in self.related_keys:
                if column.key not in obj:
                    has_identifier = False
            if has_identifier:
                with self.session.no_autoflush:
                    # If the parent object hasn't yet been persisted,
                    # autoflush can cause an error since it is yet
                    # to be fully formed.
                    instance = self.session.query(
                        self.related_model).filter_by(**{
                            column.key: obj.get(column.key)
                            for column in self.related_keys
                        }).first()
            else:
                instance = None
            instance_is_in_relation = False
            if instance is None:
                # New object, try to create it.
                instance, sub_errors = self.schema.load(
                    obj,
                    session=self.session,
                    instance=self.related_model(),
                    partial=False,
                    many=False)
                if sub_errors:
                    if self.many:
                        errors[i] = sub_errors
                    else:
                        errors = sub_errors
                    if strict:
                        raise ValidationError(errors, data=value)
                    else:
                        continue
            else:
                # Try loading this data using the nested schema
                loaded_instance, sub_errors = self.schema.load(
                    obj,
                    session=self.session,
                    instance=instance,
                    partial=True,
                    many=False)
                with_parentable = False
                if self.parent.instance is not None:
                    if inspect(self.parent.instance).persistent:
                        with_parentable = True
                if not sub_errors and loaded_instance == instance:
                    # Instance with this primary key exists
                    # Data provided validates
                    # Now check to see if this instance is already
                    # in the parent relationship.
                    if with_parentable:
                        in_relation_instance = self.session.query(
                            self.related_model).with_parent(
                                self.parent.instance).filter_by(**{
                                    column.key: obj.get(column.key)
                                    for column in self.related_keys
                                }).first()
                        if in_relation_instance == instance:
                            instance_is_in_relation = True
                    else:
                        if isinstance(getattr(parent, self.name), list):
                            if instance in getattr(parent, self.name):
                                instance_is_in_relation = True
                        elif getattr(parent, self.name) == instance:
                            instance_is_in_relation = True
                else:
                    # error
                    if self.many:
                        errors[i] = sub_errors
                    else:
                        errors = sub_errors
                    if strict:
                        raise ValidationError(errors, data=value)
                    else:
                        continue
            if not sub_errors and instance is not None and self.many:
                if operation == "remove":
                    if instance_is_in_relation:
                        if self.parent.partial:
                            # no need to remove if not partial, as the
                            # list will already be empty.
                            relation = getattr(parent, self.name)
                            relation.remove(instance)
                    # TODO - elif strict: error
                elif operation is None or operation == "add":
                    if not instance_is_in_relation:
                        relation = getattr(parent, self.name)
                        relation.append(instance)
                # TODO - elif strict: error
                result = getattr(parent, self.name)
            elif not sub_errors and not self.many:
                setattr(parent, self.name, instance)
                result = instance
        if errors:
            raise ValidationError(errors, data=value)
        return result


class EmbeddableRelationshipMixin(EmbeddableMixin):

    """Defaults to returning a relationship's URL if not embedded."""

    def get_url(self, obj):
        """Get the URL for this relationship."""
        url = ""
        if self.parent and "self" in self.parent.fields:
            url += self.parent.fields["self"].serialize("self", obj)
        relationship_name = self.dump_to or self.name
        url += "/" + relationship_name
        return url

    def deserialize(self, value, *args, **kwargs):
        """Return the field's deserialized value."""
        if value == self.get_url(self.parent.instance):
            return getattr(self.parent.instance, self.name)
        else:
            return super(EmbeddableMixin, self).deserialize(
                value, *args, **kwargs
            )

    def serialize(self, attr, obj, *args, **kwargs):
        """Return the field's serialized value if embedded."""
        if self.embedded:
            return super(EmbeddableMixin, self).serialize(
                attr, obj, *args, **kwargs)
        else:
            return self.get_url(obj)


class Relationship(EmbeddableRelationshipMixin, NestedRelated):

    """Default relationship field.

    When serialized, returns the relationship's assumed URL if not
    embedded. Otherwise, returns the nested values of the relationship.

    """

    pass


class APIUrl(Field):

    """Text field, displays the url of the resource it's attached to."""

    def __init__(self, endpoint_name, *args, **kwargs):
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
