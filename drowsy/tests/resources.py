"""
    drowsy.tests.resources
    ~~~~~~~~~~~~~~~~~~~~~~

    Resources used for test purposes.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from drowsy.resource import ModelResource
from drowsy.tests.schemas import (
    AlbumSchema, ArtistSchema, CompositeNodeSchema, CustomerSchema,
    EmployeeSchema, GenreSchema, InvoiceLineSchema, InvoiceSchema,
    MediaTypeSchema, NodeSchema, PlaylistSchema, TrackSchema
)


def page_max_100(resource):
    """Always returns 100 as the page max size."""
    if resource is not None:
        return 100


class AlbumResource(ModelResource):
    class Meta:
        schema_cls = AlbumSchema


class InvoiceLineResource(ModelResource):
    class Meta:
        schema_cls = InvoiceLineSchema


class InvoiceResource(ModelResource):
    class Meta:
        schema_cls = InvoiceSchema
        page_max_size = page_max_100


class EmployeeResource(ModelResource):
    class Meta:
        schema_cls = EmployeeSchema
        error_messages = {
            "invalid_field": "Test invalid_field message."
        }


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
