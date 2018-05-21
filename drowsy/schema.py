"""
    drowsy.schema
    ~~~~~~~~~~~~~

    Classes for building REST API friendly, model based schemas.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from marshmallow.base import FieldABC, SchemaABC
from marshmallow.compat import basestring
from marshmallow.decorators import post_load
from marshmallow.schema import Schema, SchemaOpts
from marshmallow_sqlalchemy.fields import get_primary_keys
from marshmallow_sqlalchemy.schema import ModelSchema, ModelSchemaOpts
from mqlalchemy.utils import dummy_gettext
from drowsy.convert import ModelResourceConverter
from drowsy.fields import EmbeddableMixinABC


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

    """
    def __init__(self, meta):
        """Handle the meta class attached to a `ResourceSchema`.

        :param meta: The meta class attached to a
            :class:`~drowsy.resource.ResourceSchema`.

        """
        super(ResourceSchemaOpts, self).__init__(meta)
        self.id_keys = getattr(meta, 'id_keys', None)
        self.instance_cls = getattr(meta, 'instance_cls', None)


class ModelResourceSchemaOpts(ModelSchemaOpts, ResourceSchemaOpts):
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

    def __init__(self, meta):
        """Handle the meta class attached to a `ModelResourceSchema`.

        :param meta: The meta class attached to a
            :class:`~drowsy.resource.ModelResourceSchema`.

        """
        super(ModelResourceSchemaOpts, self).__init__(meta)
        # overwrite default model_converter from ModelSchemaOpts
        self.model_converter = getattr(
            meta, 'model_converter', ModelResourceConverter)
        # overwrite default model_converter from ResourceSchemaOpts
        self.instance_cls = getattr(
            meta, 'model', getattr(self, "instance_cls", None))


class ResourceSchema(Schema):
    """Schema meant to be used with a `Resource`.

    Enables sub-resource embedding, context processing, error
    translation, and more.

    """

    OPTIONS_CLASS = ResourceSchemaOpts

    def __init__(self,  extra=None, only=(), exclude=(), prefix='',
                 strict=False, many=False, context=None, load_only=(),
                 dump_only=(), partial=False, instance=None):
        """Sets additional member vars on top of `ResourceSchema`.

        Also runs :meth:`process_context` upon completion.

        :param extra: Additional attributes to be added to the
            serialized result.
        :type extra: dict or None
        :param only: Fields to be included in the serialized result.
        :type only: tuple or list
        :param exclude: Fields to be excluded from the serialized
            result.
        :type exclude: tuple or list
        :param str prefix: Prefix to be prepended to serialized field
            names.
        :param bool strict: Raises exceptions on validation if
            ``True``.
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
        :param instance: Object instance data should be loaded into.
            If ``None`` is provided, an instance will either be
            determined using the provided data via :meth:`get_instance`,
            or if that fails a new instance will be created.

        """
        super(ResourceSchema, self).__init__(
            extra=extra,
            only=only,
            exclude=exclude,
            prefix=prefix,
            strict=strict,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial)
        self.instance = instance
        self._fields_by_dump_to = None
        self._fields_by_load_from = None
        self.process_context()

    @property
    def fields_by_load_from(self):
        """Get a dictionary of fields with load_from as the keys.

        :return: Dictionary of fields with the keys coming from
            field.load_from.
        :rtype: dict

        """
        if (not hasattr(self, "_fields_by_load_from") or
                self._fields_by_load_from is None):
            self._fields_by_load_from = {}
            for key in self.fields:
                field = self.fields[key]
                self._fields_by_load_from[field.load_from or key] = field
        return self._fields_by_load_from

    @property
    def fields_by_dump_to(self):
        """Get a dictionary of fields with dump_to as the keys.

        :return: Dictionary of fields with the keys coming from
            field.dump_to.
        :rtype: dict

        """
        if (not hasattr(self, "_fields_by_dump_to") or
                self._fields_by_dump_to is None):
            self._fields_by_dump_to = {}
            for key in self.fields:
                field = self.fields[key]
                self._fields_by_dump_to[field.dump_to or key] = field
        return self._fields_by_dump_to

    def get_instance(self, data):
        """Used primarily to retrieve a pre-existing instance.

        Should use the provided ``data`` to locate the pre-existing
        instance, but not to populate it.

        :param dict data: Data associated with this instance.
        :return: An object instance.

        """
        return self.opts.instance_cls()

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
        if isinstance(items, basestring):
            items = [items]
        for item in items:
            split_names = item.split(".")
            if split_names:
                split_name = split_names.pop(0)
                if isinstance(self.fields.get(split_name, None),
                              EmbeddableMixinABC):
                    field = self.fields[split_name]
                    field.embedded = True
                    if (hasattr(field, "schema") and
                            isinstance(field.schema, ResourceSchema) and
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
    def make_instance(self, data):
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

    def load(self, data, instance=None, *args, **kwargs):
        """Deserialize the provided data into an object.

        :param dict data: Data to be loaded into an instance.
        :param instance: Object instance that data should be loaded
            into. If ``None`` is provided at this point or when the
            class was initialized, an instance will either be determined
            using the provided data via :meth:`get_instance`, or if that
            fails a new instance will be created.
        :return: An instance with the provided data loaded into it.

        """
        for key in data:
            if (key in self.fields and
                    isinstance(self.fields[key], (EmbeddableMixinABC,))):
                self.embed([key])
        # make sure self.instance isn't None
        if instance is not None:
            self.instance = instance
        elif self.instance is None:
            self.instance = self.get_instance(data)
            if self.instance is None:
                self.instance = self.opts.instance_cls()
        kwargs["instance"] = self.instance
        return super(ResourceSchema, self).load(
            data, *args, **kwargs)

    def process_context(self):
        """Override to modify a schema based on context."""
        pass


class ModelResourceSchema(ResourceSchema, ModelSchema):
    """Schema meant to be used with a `ModelResource`.

    Enables sub-resource embedding, context processing, error
    translation, and more.

    """

    OPTIONS_CLASS = ModelResourceSchemaOpts

    def __init__(self,  extra=None, only=(), exclude=(), prefix='',
                 strict=False, many=False, context=None, load_only=(),
                 dump_only=(), partial=False, instance=None, session=None):
        """Sets additional member vars on top of `ModelSchema`.

        Also runs :meth:`process_context` upon completion.

        :param extra: Additional attributes to be added to the
            serialized result.
        :type extra: dict or None
        :param only: Fields to be included in the serialized result.
        :type only: tuple or list
        :param exclude: Fields to be excluded from the serialized
            result.
        :type exclude: tuple or list
        :param str prefix: Prefix to be prepended to serialized field
            names.
        :param bool strict: Raises exceptions on validation if
            ``True``.
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
        :param session: SQLAlchemy database session.

        """
        super(ModelResourceSchema, self).__init__(
            extra=extra,
            only=only,
            exclude=exclude,
            prefix=prefix,
            strict=strict,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            instance=instance
        )
        # Though ModelSchema init does get called,
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

        """
        keys = self.id_keys
        filters = {
            key: data.get(key)
            for key in keys
        }
        if None not in filters.values():
            return self.session.query(
                self.opts.model
            ).filter_by(
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

    def load(self, data, session=None, instance=None, *args, **kwargs):
        """Deserialize the provided data into a SQLAlchemy object.

        :param dict data: Data to be loaded into an instance.
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
        kwargs["session"] = session
        kwargs["instance"] = instance
        return super(ModelResourceSchema, self).load(data, *args, **kwargs)
