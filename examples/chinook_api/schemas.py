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
        include_relationships = True


class ArtistSchema(ModelResourceSchema):
    class Meta:
        model = Artist
        include_relationships = True


class InvoiceLineSchema(ModelResourceSchema):
    class Meta:
        model = InvoiceLine
        include_relationships = True


class InvoiceSchema(ModelResourceSchema):
    class Meta:
        model = Invoice
        include_relationships = True


class EmployeeSchema(ModelResourceSchema):
    class Meta:
        model = Employee
        include_relationships = True


class CustomerSchema(ModelResourceSchema):
    class Meta:
        model = Customer
        include_relationships = True


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


class TrackPermissionsSchema(ModelResourceSchema):
    class Meta:
        model = Track
        include_relationships = True


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
