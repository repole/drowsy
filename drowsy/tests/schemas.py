"""
    drowsy.tests.schemas
    ~~~~~~~~~~~~~~~~~~~~

    Schemas used for test purposes.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from drowsy.tests.models import *
from drowsy.schema import ModelResourceSchema


class InvoiceLineSchema(ModelResourceSchema):
    class Meta:
        model = InvoiceLine


class InvoiceSchema(ModelResourceSchema):
    class Meta:
        model = Invoice


class EmployeeSchema(ModelResourceSchema):
    class Meta:
        model = Employee


class CustomerSchema(ModelResourceSchema):
    class Meta:
        model = Customer


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
