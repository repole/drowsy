"""
    drowsy.converter
    ~~~~~~~~~~~~~~~~

    Convert SQLAlchemy models into Marshmallow schemas.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from inflection import camelize, underscore, pluralize
from marshmallow_sqlalchemy.convert import ModelConverter
from sqlalchemy.orm.descriptor_props import SynonymProperty
from drowsy.fields import APIUrl, Relationship


class ModelResourceConverter(ModelConverter):

    """Convert a model's fields for use in a `ModelResourceSchema`."""

    def _get_field_class_for_property(self, prop):
        """Determine what class to use for a field based on ``prop``.

        :param prop: A column property belonging to a sqlalchemy model.
        :type prop: :class:`~sqlalchemy.orm.properties.ColumnProperty`
        :return: A field class corresponding to the provided ``prop``.
        :rtype: type

        """
        if hasattr(prop, 'direction'):
            if prop.uselist:
                field_cls = Relationship
            else:
                field_cls = Relationship
        else:
            column = prop.columns[0]
            field_cls = self._get_field_class_for_column(column)
        return field_cls

    def _add_column_kwargs(self, kwargs, prop):
        """Update the provided kwargs based on the prop given.

        :param dict kwargs: A dictionary of kwargs to pass to the
            eventual field constructor. This argument is modified
            in place.
        :param prop: A column property used to determine how
            ``kwargs`` should be updated.
        :type prop: :class:`~sqlalchemy.orm.properties.ColumnProperty`

        """
        super(ModelResourceConverter, self)._add_column_kwargs(
            kwargs, prop.columns[0])
        # PENDING - use different error messages?
        # due to Marshmallow not having i18n support, may have
        # to use different error messages that don't have any
        # variables in them.

    def _add_relationship_kwargs(self, kwargs, prop):
        """Update the provided kwargs based on the relationship given.

        :param dict kwargs: A dictionary of kwargs to pass to the
            eventual field constructor. This argument is modified
            in place.
        :param prop: A relationship property used to determine how
            ``kwargs`` should be updated.
        :type prop:
            :class:`~sqlalchemy.orm.properties.RelationshipProperty`

        """
        nullable = True
        required = False
        for pair in prop.local_remote_pairs:
            if not pair[0].nullable:
                if prop.uselist is True:
                    nullable = False
                    required = False
                else:
                    for column in prop.local_columns:
                        if column.nullable is False:
                            nullable = False
                            required = True
                break
        kwargs.update({
            "nested": prop.mapper.class_.__name__ + 'Resource',
            "allow_none": nullable,
            "required": required,
            "many": prop.uselist
        })

    def property2field(self, prop, instance=True, **kwargs):
        """

        :param prop: A column or relationship property used to
            determine a corresponding field.
        :type prop: :class:`~sqlalchemy.orm.properties.ColumnProperty`
            or :class:`~sqlalchemy.orm.properties.RelationshipProperty`
        :param instance: ``True`` if this method should return an actual
            instance of a field, ``False`` to return the actual field
            class.
        :param kwargs: Keyword args to be used in the construction of
            the field.
        :return: Depending on the value of ``instance``, either a field
            or a field class.
        :rtype: :class:`~marshmallow.fields.Field` or type

        """

        field_class = self._get_field_class_for_property(prop)
        if not instance:
            return field_class
        field_kwargs = self._get_field_kwargs_for_property(prop)
        field_kwargs.update(kwargs)
        ret = field_class(**field_kwargs)
        return ret

    def _get_field_kwargs_for_property(self, prop):
        """Get a dict of kwargs to use for field construction.

        :param prop: A column or relationship property used to
            determine what kwargs should be passed to the
            eventual field constructor.
        :type prop: :class:`~sqlalchemy.orm.properties.ColumnProperty`
            or :class:`~sqlalchemy.orm.properties.RelationshipProperty`
        :return: A dict of kwargs to pass to the eventual field
            constructor.
        :rtype: dict

        """
        kwargs = self.get_base_kwargs()
        if hasattr(prop, 'columns'):
            self._add_column_kwargs(kwargs, prop)
        if hasattr(prop, 'direction'):  # Relationship property
            self._add_relationship_kwargs(kwargs, prop)
        if getattr(prop, 'doc', None):  # Useful for documentation generation
            kwargs['description'] = prop.doc
        return kwargs

    @staticmethod
    def _model_name_to_endpoint_name(model_name):
        """Given a model name, return an API endpoint name.

        For example, InvoiceLine becomes invoice_lines

        :param str model_name: The name of the model class.

        """
        return underscore(pluralize(model_name))

    def fields_for_model(self, model, *, include_fk=False,
                         include_relationships=False, fields=None,
                         exclude=None, base_fields=None, dict_cls=dict):
        """Generate fields for the provided model.

        :param model: The SQLAlchemy model the generated fields
            correspond to.
        :param bool include_fk: ``True`` if fields should be generated
            for foreign keys, ``False`` otherwise.
        :param bool include_relationships: ``True`` if relationship
            fields should be generated, ``False`` otherwise.
        :param fields: A collection of field names to generate.
        :type fields: :class:`~collections.Iterable` or None
        :param exclude: A collection of field names not to generate.
        :type exclude: :class:`~collections.Iterable` or None
        :param base_fields: Optional dict of default fields to include
            in the result.
        :type base_fields: dict or None
        :param dict_cls: Optional specific type of dict to use for
            the result.
        :return: Generated fields corresponding to each model property.
        :rtype: dict or the provided dict_cls

        """
        result = dict_cls()
        base_fields = base_fields or {}
        for prop in model.__mapper__.iterate_properties:
            key = self._get_field_name(prop)
            if self._should_exclude_field(
                    prop, fields=fields, exclude=exclude):  # pragma: no cover
                # Allow marshmallow to validate and exclude the field key.
                result[key] = None
                continue
            if isinstance(prop, SynonymProperty):  # pragma: no cover
                continue
            if hasattr(prop, "columns"):
                if not include_fk:
                    # Only skip a column if there is no overridden
                    # column which does not have a Foreign Key and
                    # it's not a PK
                    for column in prop.columns:
                        if column.primary_key or not column.foreign_keys:
                            break
                    else:
                        continue
            if not include_relationships and hasattr(prop, "direction"):
                continue  # pragma: no cover
            field = base_fields.get(key) or self.property2field(prop)
            if field:
                result[key] = field
        result["self"] = APIUrl(
            endpoint_name=self._model_name_to_endpoint_name(model.__name__))
        return result


class CamelModelResourceConverter(ModelResourceConverter):

    """Convert a model to a schema that uses camelCase field names."""

    def _add_column_kwargs(self, kwargs, prop):
        """Update the provided kwargs based on the prop given.

        :param dict kwargs: A dictionary of kwargs to pass to the
            eventual field constructor. This argument is modified
            in place.
        :param prop: A column property used to determine how
            ``kwargs`` should be updated.
        :type prop: :class:`~sqlalchemy.orm.properties.ColumnProperty`

        """
        super(CamelModelResourceConverter, self)._add_column_kwargs(
            kwargs, prop)
        kwargs["data_key"] = camelize(prop.key, uppercase_first_letter=False)

    def _add_relationship_kwargs(self, kwargs, prop):
        """Update the provided kwargs based on the relationship given.

        :param dict kwargs: A dictionary of kwargs to pass to the
            eventual field constructor. This argument is modified
            in place.
        :param prop: A relationship property used to determine how
            ``kwargs`` should be updated.
        :type prop:
            :class:`~sqlalchemy.orm.properties.RelationshipProperty`

        """
        super(CamelModelResourceConverter, self)._add_relationship_kwargs(
            kwargs, prop)
        kwargs["data_key"] = camelize(prop.key, uppercase_first_letter=False)

    @staticmethod
    def _model_name_to_endpoint_name(model_name):
        """Given a model name, return an API endpoint name.

        For example, InvoiceLine becomes invoiceLines

        :param str model_name: The name of the model class.

        """
        return camelize(pluralize(model_name), uppercase_first_letter=False)
