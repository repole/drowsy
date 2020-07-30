"""
    chinook_api.resources
    ~~~~~~~~~~~~~~~~~~~~~

    Resources used for Chinook API purposes.

"""
# :copyright: (c) 2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from drowsy.resource import ModelResource
from .schemas import (
    AlbumSchema, ArtistSchema, CompositeManySchema, CompositeOneSchema,
    CompositeNodeSchema, CustomerSchema, EmployeeSchema, GenreSchema,
    InvoiceLineSchema, InvoiceSchema, MediaTypeSchema, NodeSchema,
    PlaylistSchema, TrackSchema
)


class AlbumResource(ModelResource):
    class Meta:
        schema_cls = AlbumSchema


class InvoiceLineResource(ModelResource):
    class Meta:
        schema_cls = InvoiceLineSchema


class InvoiceResource(ModelResource):
    class Meta:
        schema_cls = InvoiceSchema


class EmployeeResource(ModelResource):
    class Meta:
        schema_cls = EmployeeSchema


class CustomerResource(ModelResource):
    class Meta:
        schema_cls = CustomerSchema


class PlaylistResource(ModelResource):
    class Meta:
        schema_cls = PlaylistSchema


class MediaTypeResource(ModelResource):
    class Meta:
        schema_cls = MediaTypeSchema


class GenreResource(ModelResource):
    class Meta:
        schema_cls = GenreSchema


class TrackResource(ModelResource):
    class Meta:
        schema_cls = TrackSchema


class ArtistResource(ModelResource):
    class Meta:
        schema_cls = ArtistSchema


class NodeResource(ModelResource):
    class Meta:
        schema_cls = NodeSchema


class CompositeNodeResource(ModelResource):
    class Meta:
        schema_cls = CompositeNodeSchema


class CompositeOneResource(ModelResource):
    class Meta:
        schema_cls = CompositeOneSchema


class CompositeManyResource(ModelResource):
    class Meta:
        schema_cls = CompositeManySchema
