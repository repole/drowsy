"""
    tests.resources
    ~~~~~~~~~~~~~~~

    Resources used for test purposes.

"""
# :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from drowsy.resource import ModelResource
from .schemas import (
    AlbumCamelSchema, AlbumSchema, ArtistCamelSchema, ArtistSchema,
    CompositeOneSchema, CompositeOneCamelSchema, CompositeManySchema,
    CompositeManyCamelSchema, CompositeNodeCamelSchema, CompositeNodeSchema,
    CustomerCamelSchema, CustomerSchema, EmployeeCamelSchema, EmployeeSchema,
    GenreCamelSchema, GenreSchema, InvoiceLineCamelSchema, InvoiceLineSchema,
    InvoiceCamelSchema, InvoiceSchema, MediaTypeCamelSchema, MediaTypeSchema,
    NodeCamelSchema, NodeSchema, PlaylistCamelSchema, PlaylistSchema,
    TrackCamelSchema, TrackSchema
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
        options = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


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

    def get_required_filters(self, alias=None):
        model = alias or self.model
        if self.context.get("user") == "limited":
            # NOTE: Should split this out into a different test...
            filters = (model.track_id != 130, )
            return filters
        elif self.context.get("user") == "limited_single_filter":
            filters = model.track_id != 130
            return filters
        return None


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


class AlbumCamelResource(ModelResource):
    class Meta:
        schema_cls = AlbumCamelSchema


class InvoiceLineCamelResource(ModelResource):
    class Meta:
        schema_cls = InvoiceLineCamelSchema


class InvoiceCamelResource(ModelResource):
    class Meta:
        schema_cls = InvoiceCamelSchema
        page_max_size = page_max_100


class EmployeeCamelResource(ModelResource):
    class Meta:
        schema_cls = EmployeeCamelSchema
        error_messages = {
            "invalid_field": "Test invalid_field message."
        }


class CustomerCamelResource(ModelResource):
    class Meta:
        schema_cls = CustomerCamelSchema


class PlaylistCamelResource(ModelResource):
    class Meta:
        schema_cls = PlaylistCamelSchema


class MediaTypeCamelResource(ModelResource):
    class Meta:
        schema_cls = MediaTypeCamelSchema


class GenreCamelResource(ModelResource):
    class Meta:
        schema_cls = GenreCamelSchema


class TrackCamelResource(ModelResource):
    class Meta:
        schema_cls = TrackCamelSchema


class ArtistCamelResource(ModelResource):
    class Meta:
        schema_cls = ArtistCamelSchema


class NodeCamelResource(ModelResource):
    class Meta:
        schema_cls = NodeCamelSchema


class CompositeNodeCamelResource(ModelResource):
    class Meta:
        schema_cls = CompositeNodeCamelSchema


class CompositeOneCamelResource(ModelResource):
    class Meta:
        schema_cls = CompositeOneCamelSchema


class CompositeManyCamelResource(ModelResource):
    class Meta:
        schema_cls = CompositeManyCamelSchema
