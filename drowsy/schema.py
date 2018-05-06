"""
    drowsy.schema
    ~~~~~~~~~~~~~

    Classes for building REST API friendly, model based schemas.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from marshmallow.base import FieldABC, SchemaABC
from marshmallow_sqlalchemy.fields import get_primary_keys
from marshmallow_sqlalchemy.schema import ModelSchema, ModelSchemaOpts
from mqlalchemy.utils import dummy_gettext
from drowsy.convert import ModelResourceConverter
from drowsy.fields import EmbeddableMixinABC


class ModelResourceSchemaOpts(ModelSchemaOpts):
    """Meta class options for use with a ``ModelResourceSchema``.

    Defaults ``model_converter`` to
    :class:`~drowsy.convert.ModelResourceConverter`.

    Defaults ``id_keys`` to ``None``, resulting in the model's
    primary keys being used as identifier fields.

    Example usage:

    .. code-block:: python

        class UserSchema(ModelResourceSchema):
            class Meta:
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
        self.id_keys = getattr(meta, 'id_keys', None)
        self.model_converter = getattr(
            meta, 'model_converter', ModelResourceConverter)


class ModelResourceSchema(ModelSchema):
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
            instance=instance,
            session=session)
        self.fields_by_dump_to = {}
        for key in self.fields:
            field = self.fields[key]
            if field.dump_to:
                self.fields_by_dump_to[field.dump_to] = field
            else:
                self.fields_by_dump_to[field.name] = field
        self.fields_by_load_from = {}
        for key in self.fields:
            field = self.fields[key]
            if field.load_from:
                self.fields_by_load_from[field.load_from] = field
            else:
                self.fields_by_load_from[field.name] = field
        self.process_context()

    def get_instance(self, data):
        """Retrieve an existing record by primary key(s).

        :param dict data: Data associated with this instance.

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

    def embed(self, items):
        """Embed the list of field names provided.

        :param list items: A list of embeddable sub resources or
            sub resource fields.

        """
        for item in items:
            split_names = item.split(".")
            parent = self
            for split_name in split_names:
                if isinstance(parent, ModelSchema):
                    if isinstance(parent.fields.get(split_name, None),
                                  EmbeddableMixinABC):
                        field = parent.fields[split_name]
                        field.embedded = True
                        if hasattr(field, "process_context"):
                            field.process_context()
                        if hasattr(field, "schema"):
                            parent = field.schema
                        else:
                            parent = None
                    else:
                        if split_name in parent.fields:
                            parent.exclude = tuple()
                            if parent.only is None:
                                parent.only = tuple()
                            parent.only = parent.only + tuple([split_name])
                        else:
                            break

    @property
    def id_keys(self):
        """Get the fields used to identify a resource instance."""
        if (hasattr(self.opts, "id_keys") and
                isinstance(self.opts.id_keys, list)):
            return self.opts.id_keys
        else:
            return [col.key for col in get_primary_keys(self.opts.model)]

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
                self.instance = self.opts.model()
        return super(ModelResourceSchema, self).load(
            data, session, instance, *args, **kwargs)

    def process_context(self):
        """Override to modify a schema based on context."""
        pass

    def translate_error(self, value, **variables):
        """Override to modify a schema based on context.

        :param value: An error string to be translated.

        """
        if self.context.get("gettext", None) is None:
            parent = self.root
            if isinstance(parent, FieldABC):
                if hasattr(parent, "root"):
                    parent = parent.root
            if isinstance(parent, SchemaABC):
                if hasattr(parent, "translate_error"):
                    return parent.translate_error(value, **variables)
        elif callable(self.context.get("gettext", None)):
            return self.context["gettext"](value, **variables)
        return dummy_gettext(value, **variables)
