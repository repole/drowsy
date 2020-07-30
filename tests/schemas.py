"""
    tests.schemas
    ~~~~~~~~~~~~~

    Schemas used for test purposes.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from drowsy.convert import CamelModelResourceConverter
from drowsy.fields import Relationship
from drowsy.permissions import DisallowAllOpPermissions
from drowsy.schema import ModelResourceSchema
from .models import (
    Album, Artist, CompositeOne, CompositeMany, CompositeNode, Customer,
    Employee, Genre, Invoice, InvoiceLine, MediaType, Node, Playlist, Track
)
from marshmallow import fields
from marshmallow_sqlalchemy.schema import SQLAlchemyAutoSchema


class InvoiceLineSchema(ModelResourceSchema):
    class Meta:
        model = InvoiceLine
        include_relationships = True


class InvoiceSchema(ModelResourceSchema):
    class Meta:
        model = Invoice
        include_relationships = True
    invoice_lines = fields.Nested("InvoiceLineSchema", many=True)


class EmployeeSchema(ModelResourceSchema):
    class Meta:
        model = Employee
        include_relationships = True


class CustomerSchema(ModelResourceSchema):
    class Meta:
        model = Customer
        include_relationships = True
    phone = fields.String(load_only=True)


class PlaylistSchema(ModelResourceSchema):
    class Meta:
        model = Playlist
        include_relationships = True


class MediaTypeSchema(ModelResourceSchema):
    class Meta:
        model = MediaType
        include_relationships = True


class GenreSchema(ModelResourceSchema):
    class Meta:
        model = Genre
        include_relationships = True


class TrackSchema(ModelResourceSchema):
    class Meta:
        model = Track
        include_relationships = True

    def check_permission(self, data, instance, action):
        """Checks if this action is permissible to attempt.

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
        if data.get("track_id") == 1 and data.get("name") == "Denied":
            raise self.make_error("permission_denied")


class TrackPermissionsSchema(ModelResourceSchema):
    class Meta:
        model = Track
        include_relationships = True
    album = Relationship(
        "AlbumResource", many=False, permissions_cls=DisallowAllOpPermissions)


class AlbumSchema(ModelResourceSchema):
    class Meta:
        model = Album
        include_relationships = True
        id_keys = ["album_id"]
        error_messages = {
            "permission_denied": "Overrides original error."
        }

    def check_permission(self, data, instance, action):
        """Checks if this action is permissible to attempt.

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
        if data.get("title") == "Denied" or (
                instance is not None and instance.album_id == 340 and
                action == "delete"):
            raise self.make_error("permission_denied")


class ArtistSchema(ModelResourceSchema):
    class Meta:
        model = Artist
        include_relationships = True
    albums = Relationship(
        "AlbumResource", many=True, permissions_cls=DisallowAllOpPermissions)


class NodeSchema(ModelResourceSchema):
    class Meta:
        model = Node
        include_relationships = True


class CompositeNodeSchema(ModelResourceSchema):
    class Meta:
        model = CompositeNode
        include_relationships = True


class CompositeOneSchema(ModelResourceSchema):
    class Meta:
        model = CompositeOne
        include_relationships = True


class CompositeManySchema(ModelResourceSchema):
    class Meta:
        model = CompositeMany
        include_relationships = True


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
        super(TestCamelModelResourceConverter, self)._add_relationship_kwargs(
            kwargs, prop)
        kwargs.update({
            "nested": prop.mapper.class_.__name__ + 'CamelResource'
        })


class InvoiceLineCamelSchema(ModelResourceSchema):
    class Meta:
        model = InvoiceLine
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class InvoiceCamelSchema(ModelResourceSchema):
    class Meta:
        model = Invoice
        include_relationships = True
        model_converter = TestCamelModelResourceConverter
    invoice_lines = fields.Nested(
        "InvoiceLineCamelSchema", many=True, data_key="invoiceLines")


class EmployeeCamelSchema(ModelResourceSchema):
    class Meta:
        model = Employee
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class CustomerCamelSchema(ModelResourceSchema):
    class Meta:
        model = Customer
        include_relationships = True
        model_converter = TestCamelModelResourceConverter
    phone = fields.String(load_only=True, data_key="phone")


class PlaylistCamelSchema(ModelResourceSchema):
    class Meta:
        model = Playlist
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class MediaTypeCamelSchema(ModelResourceSchema):
    class Meta:
        model = MediaType
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class GenreCamelSchema(ModelResourceSchema):
    class Meta:
        model = Genre
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class TrackCamelSchema(ModelResourceSchema):
    class Meta:
        model = Track
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class AlbumCamelSchema(ModelResourceSchema):
    class Meta:
        model = Album
        include_relationships = True
        model_converter = TestCamelModelResourceConverter
        id_keys = ["album_id"]


class ArtistCamelSchema(ModelResourceSchema):
    class Meta:
        model = Artist
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class NodeCamelSchema(ModelResourceSchema):
    class Meta:
        model = Node
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class CompositeNodeCamelSchema(ModelResourceSchema):
    class Meta:
        model = CompositeNode
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class CompositeOneCamelSchema(ModelResourceSchema):
    class Meta:
        model = CompositeOne
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class CompositeManyCamelSchema(ModelResourceSchema):
    class Meta:
        model = CompositeMany
        include_relationships = True
        model_converter = TestCamelModelResourceConverter


class MsAlbumSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Album
        include_relationships = True
        load_instance = True
    album_id = fields.Integer(data_key="albumId")


class AlbumBadIdKeysSchema(ModelResourceSchema):
    class Meta:
        model = Album
        include_relationships = True
        id_keys = ["test"]
