"""
    drowsy.schema
    ~~~~~~~~~~~~~

    Classes for building REST API friendly, model based schemas.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from marshmallow.decorators import post_load
from marshmallow.exceptions import ValidationError
from marshmallow.schema import Schema, SchemaOpts
from marshmallow.utils import EXCLUDE
from marshmallow_sqlalchemy.fields import get_primary_keys
from marshmallow_sqlalchemy.schema import (
    SQLAlchemyAutoSchema, SQLAlchemyAutoSchemaOpts)
from sqlalchemy import inspect
from drowsy.convert import ModelResourceConverter
from drowsy.exc import MISSING_ERROR_MESSAGE, PermissionValidationError
from drowsy.fields import EmbeddableMixinABC
from drowsy.log import Loggable
from drowsy.utils import get_error_message


class NestedOpts(object):

    """Options for how to load a nested schema.

    Currently only used to determine whether an entire nested collection
    should be replaced, or appended/removed from on load.

    """

    def __init__(self, partial=False):
        """Initialize load options for a nested schema.

        :param bool partial: ``True`` if the entire nested collection
            should be replaced on load.

        """
        self.partial = partial


class ResourceSchemaOpts(SchemaOpts):
    """Meta class options for use with a ``ModelResourceSchema``.

        `instance_cls`` must be set.

        Defaults ``id_keys`` to ``None``, meaning the actual
        resource class using these opts must manually override
        its member ``id_keys`` property.

        Example usage:

        .. code-block:: python

            class UserSchema(ResourceSchema):
                class Meta:
                    # Use username to identify a user resource
                    # rather than user_id.
                    id_keys = ["username"]
                    # Give a class to be used for initializing
                    # new instances for this resource.
                    instance_cls = User
                    # Custom schema level error messages
                    error_messages = {
                        "permission_denied": "Don't do that."
                    }

    """
    def __init__(self, meta, ordered=False):
        """Handle the meta class attached to a `ResourceSchema`.

        :param meta: The meta class attached to a
            :class:`~drowsy.resource.ResourceSchema`.
        :param bool ordered: If `True`, order serialization output
            according to the order in which fields were declared.
            Output of `Schema.dump` will be a `collections.OrderedDict`.

        """
        super(ResourceSchemaOpts, self).__init__(meta, ordered)
        self.id_keys = getattr(meta, 'id_keys', None)
        self.instance_cls = getattr(meta, 'instance_cls', None)
        self.error_messages = getattr(meta, "error_messages", None)


class ModelResourceSchemaOpts(SQLAlchemyAutoSchemaOpts, ResourceSchemaOpts):
    """Meta class options for use with a ``ModelResourceSchema``.

    Defaults ``model_converter`` to
    :class:`~drowsy.convert.ModelResourceConverter`.

    Defaults ``id_keys`` to ``None``, resulting in the model's
    primary keys being used as identifier fields.

    Overwrites ``instance_cls`` from :class:`ResourceSchemaOpts`
    to ``model``.

    Example usage:

    .. code-block:: python

        class UserSchema(ModelResourceSchema):
            class Meta:
                # Note that model will overwrite instance_cls
                model = User
                # Use username to identify a user resource
                # rather than user_id.
                id_keys = ["username"]
                # Alternate converter to dump/load with camel case.
                model_converter = CamelModelResourceConverter

    """

    def __init__(self, meta, ordered=False):
        """Handle the meta class attached to a `ModelResourceSchema`.

        :param meta: The meta class attached to a
            :class:`~drowsy.resource.ModelResourceSchema`.
        :param bool ordered: If `True`, order serialization output
            according to the order in which fields were declared.
            Output of `Schema.dump` will be a `collections.OrderedDict`.

        """
        super(ModelResourceSchemaOpts, self).__init__(meta, ordered)
        # overwrite default converter from SQLAlchemyAutoSchemaOpts
        self.model_converter = getattr(
            meta, 'model_converter', ModelResourceConverter)
        # overwrite default instance_cls from ResourceSchemaOpts
        self.instance_cls = getattr(
            meta, 'model', getattr(self, "instance_cls", None))


class ResourceSchema(Schema, Loggable):
    """Schema meant to be used with a `Resource`.

    Enables sub-resource embedding, context processing, error
    translation, and more.

    """

    _default_error_messages = {
        "item_already_exists": "The item being created already exists.",
        "permission_denied": "You do not have permission to take that action.",
        "invalid_identifier": "The identifier for this resource is invalid."
    }

    OPTIONS_CLASS = ResourceSchemaOpts

    opts = None  # type: ResourceSchemaOpts

    def __init__(self,  only=None, exclude=(), many=False, context=None,
                 load_only=(), dump_only=(), partial=False, instance=None,
                 parent_resource=None, nested_opts=None, error_messages=None):
        """Sets additional member vars on top of `ResourceSchema`.

        Also runs :meth:`process_context` upon completion.

        :param only: Fields to be included in the serialized result.
        :type only: tuple or list or None
        :param exclude: Fields to be excluded from the serialized
            result.
        :type exclude: tuple or list
        :param bool many: ``True`` if loading a collection of items.
        :param context: Dictionary of values relevant to the current
            execution context. Should have a `gettext` key and
            `callable` value for that key if you're intending to
            translate error messages.
        :type context: dict or None
        :param load_only: Fields to be skipped during serialization.
        :type load_only: tuple or list
        :param tuple|list dump_only: Fields to be skipped during
            deserialization.
        :param bool partial: Ignores missing fields when deserializing
            if ``True``.
        :param instance: Object instance data should be loaded into.
            If ``None`` is provided, an instance will either be
            determined using the provided data via :meth:`get_instance`,
            or if that fails a new instance will be created.
        :param parent_resource: The parent resource that owns this
            schema.
        :type parent_resource: :class:`~drowsy.base.BaseResourceABC` or
            None
        :param nested_opts: Dictionary of :class:`NestedOpts`, where the
            top level key is a field name for a nested field, and the
            value for that key is a :class:`NestedOpts` instance. Used
            to determine if the entire nested collection is to be
            replaced, or simply appended to/removed from on load.
        :type nested_opts: dict<str, NestedOpts>

        """
        super(ResourceSchema, self).__init__(
            only=only,
            exclude=exclude,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial)
        self.parent_resource = parent_resource
        self.instance = instance
        self._fields_by_data_key = None
        self.nested_opts = nested_opts
        self.embedded = {}
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, '_default_error_messages', {}))
        if isinstance(self.opts.error_messages, dict):
            messages.update(self.opts.error_messages)
        messages.update(error_messages or {})
        self.error_messages = messages
        self.process_context()

    def make_error(self, key, data=None, **kwargs):
        """Raises an exception based on the ``key`` provided.

        :param str key: Failure type, used to choose an error message.
        :param data: The data that caused this issue
        :type data: dict or None
        :param kwargs: Any additional arguments that may be used for
            generating an error message.
        :return: `PermissionValidationError` exception if ``key`` is
            ``"permission_denied"``, otherwise a `ValidationError`.

        """
        if key == "permission_denied":
            return PermissionValidationError(
                message=self._get_error_message(key, **kwargs),
                data=data)
        else:
            return ValidationError(
                message=self._get_error_message(key, **kwargs),
                data=data)

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
    def fields_by_data_key(self):
        """Get a dictionary of fields with data_key as the keys.

        :return: Dictionary of fields with the keys coming from
            field.data_key.
        :rtype: dict

        """
        if (not hasattr(self, "_fields_by_data_key") or
                self._fields_by_data_key is None):
            self._fields_by_data_key = {}
            for key in self.fields:
                field = self.fields[key]
                self._fields_by_data_key[field.data_key or key] = field
        return self._fields_by_data_key

    def get_instance(self, data):
        """Used primarily to retrieve a pre-existing instance.

        Should use the provided ``data`` to locate the pre-existing
        instance, but not to populate it.

        :param dict data: Data associated with this instance.
        :return: An object instance if it already exists, or None.
        :raise ValidationError: If the ``id_keys`` in ``data`` are of
            the wrong type.

        """
        return None

    def embed(self, items):
        """Embed the list of field names provided.

        :param items: A list or single instance of embeddable
            sub resources or sub resource fields.
        :type items: list or str
        :return: None
        :rtype: None
        :raise AttributeError: If the schema does not contain
            the specified field to embed.

        """
        if isinstance(items, str):
            items = [items]
        for item in items:
            split_names = item.split(".")
            if split_names:
                split_name = split_names.pop(0)
                if isinstance(self.fields.get(split_name, None),
                              EmbeddableMixinABC):
                    field = self.fields[split_name]
                    field.embedded = True
                    if hasattr(field, "schema"):
                        if (isinstance(field.schema, ResourceSchema) and
                                split_names):
                            field.schema.process_context()
                            field.schema.embed([".".join(split_names)])
                else:
                    # NOTE: Since we have no way of telling how far
                    # down the chain we are, a top level attr could
                    # be passed, causing it to be treated like only.
                    if split_name in self.fields:
                        self.exclude = tuple()
                        self.only = self.only or tuple()
                        self.only += tuple([split_name])
                    else:
                        raise AttributeError(
                            "'{}' schema has no field '{}'".format(
                                self, split_name))

    @property
    def id_keys(self):
        """Get the fields used to identify a resource instance.

        :return: List of attribute names that serve as identifiers
            for each instance of this resource.
        :rtype: list of str

        """
        if (hasattr(self.opts, "id_keys") and
                isinstance(self.opts.id_keys, list)):
            return self.opts.id_keys
        return []

    @post_load
    def make_instance(self, data, **kwargs):
        """Deserialize the provided data into an object instance.

        :param data: The data to be deserialized into an instance.
        :return: An object instance with the provided data
            deserialized into it.

        """
        instance = self.instance or self.get_instance(data)
        if instance is not None:
            for key, value in data.items():
                setattr(instance, key, value)
            return instance
        return self.opts.instance_cls(**data)

    def load(self, data, *, many=None, instance=None, nested_opts=None,
             action=None, **kwargs):
        """Deserialize the provided data into an object.

        :param dict|list<dict> data: Data to be loaded into an instance.
        :param bool|None many: `True` if loading a collection. `None`
            defers to the schema default, other values will act as an
            override.
        :param instance: Object instance that data should be loaded
            into. If ``None`` is provided at this point or when the
            class was initialized, an instance will either be determined
            using the provided data via :meth:`get_instance`, or if that
            fails a new instance will be created.
        :param nested_opts: Dictionary of :class:`NestedOpts`, where the
            top level key is a field name for a nested field, and the
            value for that key is a :class:`NestedOpts` instance. Used
            to determine if the entire nested collection is to be
            replaced, or simply appended to/removed from on load.
            Overwrites the value set in the schema initializer.
        :type nested_opts: dict<str, NestedOpts>
        :param str|None action: Used as part of a permissions check.
            Possible values include `"create"` if a new object is
            being created, `"update"` is an existing object is being
            updated, or `"delete"` if the object is to be deleted.
            If `None` is provided, the method will deduce the action
            based on whether an existing instance is found in the
            database (`"update"`) or not (`"create"`). If loading a
            collection, any value passed will be applied to all
            objects.
        :return: An instance with the provided data loaded into it.
        :raise ValidationError: If any errors are encountered.
        :raise PermissionValidationError: If any of the actions being
            taken are not allowed.

        """
        # inherit nested opts from parent if not already set
        many = many if many is not None else self.many
        supplied_action = action
        if not many:
            data = [data]
        self.nested_opts = nested_opts or self.nested_opts
        if (not self.nested_opts and
                self.parent_resource and
                getattr(self.parent_resource, "parent_field", None) and
                getattr(self.parent_resource.parent_field, "parent", None) and
                getattr(self.parent_resource.parent_field.parent,
                        "nested_opts", None)):
            self.nested_opts = {}
            parent_schema = self.parent_resource.parent_field.parent
            parent_nested_opts = parent_schema.nested_opts
            for key in parent_nested_opts:
                child_key = ".".join(key.split(".")[1:])
                if child_key:
                    self.nested_opts[child_key] = parent_nested_opts[key]
        results = []
        errors = {}
        failure = False
        for i, obj in enumerate(data):
            # embeds
            for data_key in obj:
                field = self.fields_by_data_key.get(data_key)
                if field and isinstance(field, (EmbeddableMixinABC,)):
                    self.embed([field.name])
            try:
                # Handle self.instance and determine the action type
                self.instance = instance or self.get_instance(obj)
                persistent = False
                if self.instance is not None and inspect(
                        self.instance).persistent:
                    persistent = True
                if supplied_action is None:
                    if self.instance is None or not persistent:
                        action = "create"
                    else:
                        action = "update"
                else:
                    action = supplied_action
                if action == "create" and persistent:
                    self.handle_preexisting_create(obj)
                self.check_permission(obj, instance, action)
                if self.instance is None:
                    self.instance = self.opts.instance_cls()
                kwargs["instance"] = self.instance
                kwargs["unknown"] = EXCLUDE
                result = super(ResourceSchema, self).load(
                    obj, many=False, **kwargs)
                results.append(result)
            except PermissionValidationError as exc:
                if many:
                    # Limit returned error info to only the permission
                    # problem.
                    exc.valid_data = []
                    exc.messages = {i: exc.messages}
                    exc.data = data
                # Always hard break on a PermissionValidationError
                raise exc
            except ValidationError as exc:
                results.append({})
                errors[i] = exc.messages
                failure = True
        if not many:
            results = results[0]
            errors = errors.get(0)
            data = data[0]
        if not failure:
            return results
        else:
            raise ValidationError(message=errors, data=data,
                                  valid_data=results)

    def handle_preexisting_create(self, data):
        """Handles trying to create an object that already exists.

        You'll have to override this if you want to treat the
        ``"create"`` action like ``"update"`` on a pre-existing object.

        :param dict data: The user supplied data that triggered this
            issue.
        :return: None
        :raise ValidationError: If not allowed.

        """
        raise self.make_error("item_already_exists", data=data)

    def check_permission(self, data, instance, action):
        """Checks if this action is permissible to attempt.

        Does nothing by default, but can be overridden to check if a
        create, update, or delete action is permissible before
        performing any other validation or attempting the action.

        :param dict data: The user supplied data to be deserialized.
        :param instance: A pre-existing instance the data is to be
            deserialized into. Should be ``None`` if not updating an
            existing object.
        :param str action: Either ``"create"``, ``"update"``, or
            ``"delete"``.
        :return: None
        :raise PermissionValidationError: If the action being taken is
            not allowed.

        """
        pass

    def process_context(self):
        """Override to modify a schema based on context."""
        pass


class ModelResourceSchema(ResourceSchema, SQLAlchemyAutoSchema):
    """Schema meant to be used with a `ModelResource`.

    Enables sub-resource embedding, context processing, error
    translation, and more.

    """

    OPTIONS_CLASS = ModelResourceSchemaOpts

    opts = None  # type: ModelResourceSchemaOpts

    def __init__(self,  only=None, exclude=(), many=False, context=None,
                 load_only=(), dump_only=(), partial=False, instance=None,
                 parent_resource=None, nested_opts=None, session=None):
        """Sets additional member vars on top of `SQLAlchemyAutoSchema`.

        Also runs :meth:`process_context` upon completion.

        :param only: Fields to be included in the serialized result.
        :type only: tuple or list or None
        :param exclude: Fields to be excluded from the serialized
            result.
        :type exclude: tuple or list
        :param bool many: ``True`` if loading a collection of items.
        :param context: Dictionary of values relevant to the current
            execution context. Should have a `gettext` key and
            `callable` value for that key if you're intending to
            translate error messages.
        :type context: dict or None
        :param load_only: Fields to be skipped during serialization.
        :type load_only: tuple or list
        :param dump_only: Fields to be skipped during deserialization.
        :type dump_only: tuple or list
        :param bool partial: Ignores missing fields when deserializing
            if ``True``.
        :param instance: SQLAlchemy model instance data should be loaded
            into. If ``None`` is provided, an instance will either be
            determined using the provided data via :meth:`get_instance`,
            or if that fails a new instance will be created.
        :param parent_resource: The parent resource that owns this
            schema.
        :type parent_resource: :class:`~drowsy.base.ModelResource` or
            None
        :param nested_opts: Dictionary of :class:`NestedOpts`, where the
            top level key is a field name for a nested field, and the
            value for that key is a :class:`NestedOpts` instance. Used
            to determine if the entire nested collection is to be
            replaced, or simply appended to/removed from on load.
        :type nested_opts: dict<str, NestedOpts>
        :param session: SQLAlchemy database session.

        """
        super(ModelResourceSchema, self).__init__(
            only=only,
            exclude=exclude,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            instance=instance,
            parent_resource=parent_resource,
            nested_opts=nested_opts
        )
        # Though SQLAlchemyAutoSchema init does get called,
        # the session portion of things doesn't make
        # it through to that point, so we set it here.
        # If Marshmallow's Schema class played nice with
        # super and args+kwargs, this wouldn't be needed.
        self.session = session or self.opts.sqla_session

    def get_instance(self, data):
        """Retrieve an existing record by primary key(s).

        :param dict data: Data associated with this instance.
        :return: An instance fetched from the database
            using the value of the ``id_keys`` in ``data``.
        :raise ValidationError: If the ``id_keys`` in ``data`` are of
            the wrong type.

        """
        id_data_keys = {self.fields[k].data_key or k for k in self.id_keys}
        if set(id_data_keys).issubset(data.keys()):
            # data includes primary key columns
            # attempt to generate filters
            try:
                filters = {
                    pair[0]: self.fields[pair[0]].deserialize(data[pair[1]])
                    for pair in zip(self.id_keys, id_data_keys)
                }
            except ValidationError:
                raise self.make_error("invalid_identifier", data=data)
            query = self.session.query(
                self.opts.model
            )
            if self.parent_resource:
                query = self.parent_resource.apply_required_filters(query)
            return query.filter_by(
                **filters
            ).first()
        return None

    @property
    def id_keys(self):
        """Get the fields used to identify a resource instance.

        :return: List of attribute names that serve as identifiers
            for each instance of this resource.
        :rtype: list of str

        """
        result = super(ModelResourceSchema, self).id_keys
        if not result:
            return [col.key for col in get_primary_keys(self.opts.model)]
        return result

    def load(self, data, *, many=None, instance=None, nested_opts=None,
             action=None, session=None, **kwargs):
        """Deserialize the provided data into a SQLAlchemy object.

        :param dict|list<dict> data: Data to be loaded into an instance.
        :param session: Optional database session. Will be used in place
            of ``self.session`` if provided.
        :param instance: SQLAlchemy model instance data should be loaded
            into. If ``None`` is provided at this point or when the
            class was initialized, an instance will either be determined
            using the provided data via :meth:`get_instance`, or if that
            fails a new instance will be created.
        :return: An instance with the provided data loaded into it.

        """
        # Adding things to kwargs to play nice with super...
        kwargs["session"] = session or self.session
        kwargs["instance"] = instance
        kwargs["unknown"] = EXCLUDE
        with kwargs["session"].no_autoflush:
            # prevent bad child data from causing a premature flush
            return super(ModelResourceSchema, self).load(
                data, many=many, action=action, nested_opts=nested_opts,
                **kwargs)
