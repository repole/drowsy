"""
    chinook_api.schemas
    ~~~~~~~~~~~~~~~~~~~

    Drowsy Schemas for the Chinook database.

"""
# :copyright: (c) 2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from drowsy.convert import CamelModelResourceConverter
from drowsy.schema import ModelResourceSchema
from .models import (
    Album, Artist, CompositeOne, CompositeMany, CompositeNode, Customer,
    Employee, Genre, Invoice, InvoiceLine, MediaType, Node, Playlist, Track
)


class AlbumSchema(ModelResourceSchema):
    class Meta:
        model = Album
        model_converter = CamelModelResourceConverter


class ArtistSchema(ModelResourceSchema):
    class Meta:
        model = Artist
        model_converter = CamelModelResourceConverter


class InvoiceLineSchema(ModelResourceSchema):
    class Meta:
        model = InvoiceLine
        model_converter = CamelModelResourceConverter


class InvoiceSchema(ModelResourceSchema):
    class Meta:
        model = Invoice
        model_converter = CamelModelResourceConverter


class EmployeeSchema(ModelResourceSchema):
    class Meta:
        model = Employee
        model_converter = CamelModelResourceConverter


class CustomerSchema(ModelResourceSchema):
    class Meta:
        model = Customer
        model_converter = CamelModelResourceConverter


class PlaylistSchema(ModelResourceSchema):
    class Meta:
        model = Playlist
        model_converter = CamelModelResourceConverter


class MediaTypeSchema(ModelResourceSchema):
    class Meta:
        model = MediaType
        model_converter = CamelModelResourceConverter


class GenreSchema(ModelResourceSchema):
    class Meta:
        model = Genre
        model_converter = CamelModelResourceConverter


class TrackSchema(ModelResourceSchema):
    class Meta:
        model = Track
        model_converter = CamelModelResourceConverter


class TrackPermissionsSchema(ModelResourceSchema):
    class Meta:
        model = Track
        model_converter = CamelModelResourceConverter


class NodeSchema(ModelResourceSchema):
    class Meta:
        model = Node
        model_converter = CamelModelResourceConverter


class CompositeNodeSchema(ModelResourceSchema):
    class Meta:
        model = CompositeNode
        model_converter = CamelModelResourceConverter


class CompositeOneSchema(ModelResourceSchema):
    class Meta:
        model = CompositeOne
        model_converter = CamelModelResourceConverter


class CompositeManySchema(ModelResourceSchema):
    class Meta:
        model = CompositeMany
        model_converter = CamelModelResourceConverter
