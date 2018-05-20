"""
    drowsy.tests.schemas
    ~~~~~~~~~~~~~~~~~~~~

    Schemas used for test purposes.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from drowsy.convert import CamelModelResourceConverter
from drowsy.schema import ModelResourceSchema
from drowsy.tests.models import (
    Album, Artist, CompositeNode, Customer, Employee,
    Genre, Invoice, InvoiceLine, MediaType, Node,
    Playlist, Track
)
from marshmallow import fields


class InvoiceLineSchema(ModelResourceSchema):
    class Meta:
        model = InvoiceLine


class InvoiceSchema(ModelResourceSchema):
    class Meta:
        model = Invoice
    invoice_lines = fields.Nested("InvoiceLineSchema", many=True)


class EmployeeSchema(ModelResourceSchema):
    class Meta:
        model = Employee


class CustomerSchema(ModelResourceSchema):
    class Meta:
        model = Customer
    phone = fields.String(load_only=True)


class PlaylistSchema(ModelResourceSchema):
    class Meta:
        model = Playlist


class MediaTypeSchema(ModelResourceSchema):
    class Meta:
        model = MediaType


class GenreSchema(ModelResourceSchema):
    class Meta:
        model = Genre


class TrackSchema(ModelResourceSchema):
    class Meta:
        model = Track


class AlbumSchema(ModelResourceSchema):
    class Meta:
        model = Album


class ArtistSchema(ModelResourceSchema):
    class Meta:
        model = Artist


class NodeSchema(ModelResourceSchema):
    class Meta:
        model = Node


class CompositeNodeSchema(ModelResourceSchema):
    class Meta:
        model = CompositeNode


class TestCamelModelResourceConverter(CamelModelResourceConverter):

    """Convert a model's fields for use in a `ModelResourceSchema`."""

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
            "nested": prop.mapper.class_.__name__ + 'CamelResource',
            "allow_none": nullable,
            "required": required,
            "many": prop.uselist
        })


class InvoiceLineCamelSchema(ModelResourceSchema):
    class Meta:
        model = InvoiceLine
        model_converter = TestCamelModelResourceConverter


class InvoiceCamelSchema(ModelResourceSchema):
    class Meta:
        model = Invoice
        model_converter = TestCamelModelResourceConverter
    invoice_lines = fields.Nested(
        "InvoiceLineCamelSchema", many=True, dump_to="invoiceLines",
        load_from="invoiceLines")


class EmployeeCamelSchema(ModelResourceSchema):
    class Meta:
        model = Employee
        model_converter = TestCamelModelResourceConverter


class CustomerCamelSchema(ModelResourceSchema):
    class Meta:
        model = Customer
        model_converter = TestCamelModelResourceConverter
    phone = fields.String(load_only=True, dump_to="phone", load_from="phone")


class PlaylistCamelSchema(ModelResourceSchema):
    class Meta:
        model = Playlist
        model_converter = TestCamelModelResourceConverter


class MediaTypeCamelSchema(ModelResourceSchema):
    class Meta:
        model = MediaType
        model_converter = TestCamelModelResourceConverter


class GenreCamelSchema(ModelResourceSchema):
    class Meta:
        model = Genre
        model_converter = TestCamelModelResourceConverter


class TrackCamelSchema(ModelResourceSchema):
    class Meta:
        model = Track
        model_converter = TestCamelModelResourceConverter


class AlbumCamelSchema(ModelResourceSchema):
    class Meta:
        model = Album
        model_converter = TestCamelModelResourceConverter


class ArtistCamelSchema(ModelResourceSchema):
    class Meta:
        model = Artist
        model_converter = TestCamelModelResourceConverter


class NodeCamelSchema(ModelResourceSchema):
    class Meta:
        model = Node
        model_converter = TestCamelModelResourceConverter


class CompositeNodeCamelSchema(ModelResourceSchema):
    class Meta:
        model = CompositeNode
        model_converter = TestCamelModelResourceConverter
