"""
    drowsy.tests.test_query_builder
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Query builder tests for Drowsy.

    :copyright: (c) 2016-2019 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
from drowsy.exc import BadRequestError
from drowsy.query_builder import QueryBuilder, ModelResourceQueryBuilder
from drowsy.parser import SubfilterInfo, SortInfo
from drowsy.tests.base import DrowsyTests
from drowsy.tests.models import (
    Album, CompositeOne, CompositeNode, Track, Customer
)
from drowsy.tests.resources import (
    AlbumResource, TrackResource, CompositeNodeResource,
    CompositeOneResource, CustomerResource
)
from sqlalchemy.inspection import inspect


class DrowsyQueryBuilderTests(DrowsyTests):

    """Test drowsy query building."""

    def test_apply_sorts_simple(self):
        """Test applying a single sort."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        query = query_builder.apply_sorts(
            query=query,
            sorts=[SortInfo(attr="album_id", direction="ASC")]
        )
        results = query.all()
        last_album_id = -1
        for result in results:
            self.assertTrue(result.album_id >= last_album_id)
            last_album_id = result.album_id

    def test_apply_sorts_fail(self):
        """Test applying a single sort."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        self.assertRaises(
            AttributeError,
            query_builder.apply_sorts,
            query=query,
            sorts=[SortInfo(attr="badattr", direction="ASC")]
        )

    def test_apply_limit_negative_limit_fail(self):
        """Test that a negative limit fails."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        self.assertRaises(
            ValueError,
            query_builder.apply_limit,
            query=query,
            limit=-1
        )

    def test_apply_offset_negative_offset_fail(self):
        """Test that a negative offset fails."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album)
        self.assertRaises(
            ValueError,
            query_builder.apply_offset,
            query=query,
            offset=-1
        )

    def test_simple_subfilter(self):
        """Test applying a simple subfilter."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 5}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[]
        )
        albums = query.all()
        for album in albums:
            self.assertTrue(len(album.tracks) <= 1)
            if album.tracks:
                self.assertTrue(album.tracks[0].track_id == 5)

    def test_apply_sorts_bad_query(self):
        """Test applying sorts with a bad query fails."""
        query_builder = QueryBuilder()
        query = self.db_session.query(Album, Track)
        self.assertRaises(
            ValueError,
            query_builder.apply_sorts,
            query,
            sorts=[]
        )

    def test_simple_subfilter_limit_offset(self):
        """Test offset and limit in a subresource."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Album"."AlbumId" AS "Album_AlbumId", 
                "Album"."Title" AS "Album_Title", 
                "Album"."ArtistId" AS "Album_ArtistId", 
                "Track1"."TrackId" AS "Track1_TrackId", 
                "Track1"."Name" AS "Track1_Name", 
                "Track1"."AlbumId" AS "Track1_AlbumId", 
                "Track1"."MediaTypeId" AS "Track1_MediaTypeId", 
                "Track1"."GenreId" AS "Track1_GenreId", 
                "Track1"."Composer" AS "Track1_Composer", 
                "Track1"."Milliseconds" AS "Track1_Milliseconds", 
                "Track1"."Bytes" AS "Track1_Bytes", 
                "Track1"."UnitPrice" AS "Track1_UnitPrice" 
            FROM 
                "Album" 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        q1."TrackId" AS "TrackId", 
                        q1."Name" AS "Name", 
                        q1."AlbumId" AS "AlbumId", 
                        q1."MediaTypeId" AS "MediaTypeId", 
                        q1."GenreId" AS "GenreId", 
                        q1."Composer" AS "Composer", 
                        q1."Milliseconds" AS "Milliseconds", 
                        q1."Bytes" AS "Bytes", 
                        q1."UnitPrice" AS "UnitPrice", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Track1"."TrackId" AS "TrackId", 
                                "Track1"."Name" AS "Name", 
                                "Track1"."AlbumId" AS "AlbumId", 
                                "Track1"."MediaTypeId" AS "MediaTypeId", 
                                "Track1"."GenreId" AS "GenreId", 
                                "Track1"."Composer" AS "Composer", 
                                "Track1"."Milliseconds" AS "Milliseconds", 
                                "Track1"."Bytes" AS "Bytes", 
                                "Track1"."UnitPrice" AS "UnitPrice", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "Track1"."AlbumId" 
                                    ORDER BY 
                                        "Track1"."TrackId" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1"
                        ) AS q1, 
                        "Track" AS "Track1" 
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ? 
                        AND 
                        "Track1"."TrackId" >= ?
                ) AS "Track1" ON 
                    "Album"."AlbumId" = "Track1"."AlbumId" 
            ORDER BY 
                "Album"."AlbumId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        self.assertTrue(expected_query == result)

    def test_subfilter_limit_offset_sorts(self):
        """Test subfiltering with sorts works with limit and offset."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                offset=1,
                limit=1,
                sorts=[SortInfo(attr="name", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Album"."AlbumId" AS "Album_AlbumId", 
                "Album"."Title" AS "Album_Title", 
                "Album"."ArtistId" AS "Album_ArtistId", 
                "Track1"."TrackId" AS "Track1_TrackId", 
                "Track1"."Name" AS "Track1_Name", 
                "Track1"."AlbumId" AS "Track1_AlbumId", 
                "Track1"."MediaTypeId" AS "Track1_MediaTypeId", 
                "Track1"."GenreId" AS "Track1_GenreId", 
                "Track1"."Composer" AS "Track1_Composer", 
                "Track1"."Milliseconds" AS "Track1_Milliseconds", 
                "Track1"."Bytes" AS "Track1_Bytes", 
                "Track1"."UnitPrice" AS "Track1_UnitPrice" 
            FROM 
                "Album" 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        q1."TrackId" AS "TrackId", 
                        q1."Name" AS "Name", 
                        q1."AlbumId" AS "AlbumId", 
                        q1."MediaTypeId" AS "MediaTypeId", 
                        q1."GenreId" AS "GenreId", 
                        q1."Composer" AS "Composer", 
                        q1."Milliseconds" AS "Milliseconds", 
                        q1."Bytes" AS "Bytes", 
                        q1."UnitPrice" AS "UnitPrice", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Track1"."TrackId" AS "TrackId", 
                                "Track1"."Name" AS "Name", 
                                "Track1"."AlbumId" AS "AlbumId", 
                                "Track1"."MediaTypeId" AS "MediaTypeId", 
                                "Track1"."GenreId" AS "GenreId", 
                                "Track1"."Composer" AS "Composer", 
                                "Track1"."Milliseconds" AS "Milliseconds", 
                                "Track1"."Bytes" AS "Bytes", 
                                "Track1"."UnitPrice" AS "UnitPrice", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "Track1"."AlbumId" 
                                    ORDER BY 
                                        "Track1"."Name" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1"
                        ) AS q1, 
                        "Track" AS "Track1" 
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ? 
                        AND 
                        "Track1"."TrackId" >= ?
                ) AS "Track1" ON 
                    "Album"."AlbumId" = "Track1"."AlbumId" 
            ORDER BY 
                "Album"."AlbumId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        self.assertTrue(expected_query == result)

    def test_subfilter_sorts_no_limit_offset_fail(self):
        """Check that subresource sorts without limit or offset fail."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource_sorts",
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )

    def test_simple_subfilter_limit_too_big(self):
        """Check that a limit too large on subresource fails."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Customer)
        subfilters = {
            "invoices": SubfilterInfo(
                offset=1,
                limit=10000
            )
        }
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource_limit",
            query_builder.apply_subquery_loads,
            query=query,
            resource=CustomerResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )

    def test_subfilter_invalid_fail(self):
        """Check that bad subresource filters fail."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}}
            )
        }
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource_filters",
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )

    def test_subfilter_invalid_ignore(self):
        """Check that non strict bad subresource filters is ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=False,
            strict=False
        )
        result = query.all()
        self.assertTrue(len(result) > 0)

    def test_many_to_one_limit_fail(self):
        """Test a limit/offset on a many to one relationship fails."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Track)
        subfilters = {
            "album": SubfilterInfo(
                offset=1,
                limit=None
            )
        }
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource_options",
            query_builder.apply_subquery_loads,
            query=query,
            resource=TrackResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )

    def test_subresource_bad_dialect_fail(self):
        """Test a sublimit/offset fails with unsupported dialect."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                offset=1,
                limit=10
            )
        }
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource_options",
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(
                session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=False
        )

    def test_non_strict_bad_sublimits(self):
        """Test bad sublimits don't cause failure when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Customer)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CustomerResource(session=self.db_session),
            subfilters={
                "invoices": SubfilterInfo(
                    offset=1,
                    limit=10000
                )
            },
            embeds=[],
            strict=False,
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Customer"."CustomerId" AS "Customer_CustomerId", 
                "Customer"."FirstName" AS "Customer_FirstName", 
                "Customer"."LastName" AS "Customer_LastName", 
                "Customer"."Company" AS "Customer_Company", 
                "Customer"."Address" AS "Customer_Address", 
                "Customer"."City" AS "Customer_City", 
                "Customer"."State" AS "Customer_State", 
                "Customer"."Country" AS "Customer_Country", 
                "Customer"."PostalCode" AS "Customer_PostalCode", 
                "Customer"."Phone" AS "Customer_Phone", 
                "Customer"."Fax" AS "Customer_Fax", 
                "Customer"."Email" AS "Customer_Email", 
                "Customer"."SupportRepId" AS "Customer_SupportRepId", 
                "Invoice1"."InvoiceId" AS "Invoice1_InvoiceId", 
                "Invoice1"."CustomerId" AS "Invoice1_CustomerId", 
                "Invoice1"."InvoiceDate" AS "Invoice1_InvoiceDate", 
                "Invoice1"."BillingAddress" AS "Invoice1_BillingAddress", 
                "Invoice1"."BillingCity" AS "Invoice1_BillingCity", 
                "Invoice1"."BillingState" AS "Invoice1_BillingState", 
                "Invoice1"."BillingCountry" AS "Invoice1_BillingCountry", 
                "Invoice1"."BillingPostalCode" AS "Invoice1_BillingPostalCode", 
                "Invoice1"."Total" AS "Invoice1_Total" 
            FROM 
                "Customer" 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        q1."InvoiceId" AS "InvoiceId", 
                        q1."CustomerId" AS "CustomerId", 
                        q1."InvoiceDate" AS "InvoiceDate", 
                        q1."BillingAddress" AS "BillingAddress", 
                        q1."BillingCity" AS "BillingCity", 
                        q1."BillingState" AS "BillingState", 
                        q1."BillingCountry" AS "BillingCountry", 
                        q1."BillingPostalCode" AS "BillingPostalCode", 
                        q1."Total" AS "Total", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Invoice1"."InvoiceId" AS "InvoiceId", 
                                "Invoice1"."CustomerId" AS "CustomerId", 
                                "Invoice1"."InvoiceDate" AS "InvoiceDate", 
                                "Invoice1"."BillingAddress" AS 
                                    "BillingAddress", 
                                "Invoice1"."BillingCity" AS "BillingCity", 
                                "Invoice1"."BillingState" AS "BillingState", 
                                "Invoice1"."BillingCountry" AS 
                                    "BillingCountry", 
                                "Invoice1"."BillingPostalCode" AS 
                                    "BillingPostalCode", 
                                "Invoice1"."Total" AS "Total", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "Invoice1"."CustomerId" 
                                    ORDER BY 
                                        "Invoice1"."InvoiceId" ASC
                                ) AS row_number 
                            FROM 
                                "Invoice" AS "Invoice1"
                        ) AS q1 
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ?
                ) AS "Invoice1" ON 
                    "Invoice1"."CustomerId" = "Customer"."CustomerId" 
            ORDER BY 
                "Customer"."CustomerId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        self.assertTrue(expected_query == result)

    def test_subquery_embeds(self):
        """Test that a simple subquery can work alongside an embed."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "artist": SubfilterInfo(
                filters={"artist_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters=subfilters,
            embeds=["tracks", "artist"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            self.assertTrue("tracks" not in res.unloaded)
            if album.artist:
                self.assertTrue(album.artist.artist_id == 1)

    def test_same_subquery_embeds(self):
        """Test that a simple subquery works with a duplicate embed."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters=subfilters,
            embeds=["tracks"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            self.assertTrue("tracks" not in res.unloaded)
            if album.tracks:
                self.assertTrue(len(album.tracks) == 1)
                self.assertTrue(album.tracks[0].track_id == 1)

    def test_simple_embeds(self):
        """Test that a simple embed works."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={},
            embeds=["tracks"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            self.assertTrue("tracks" not in res.unloaded)

    def test_property_embeds(self):
        """Test that property embed works."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={},
            embeds=["tracks.track_id"]
        )
        albums = query.all()
        for album in albums:
            res = inspect(album)
            self.assertTrue("tracks" not in res.unloaded)

    def test_bad_embeds(self):
        """Test that a bad property embed fails."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        self.assertRaisesCode(
            BadRequestError,
            "invalid_embed",
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={},
            embeds=["tracks.track_id.playlistId"]
        )

    def test_bad_embeds_ignore(self):
        """Test that a non strict bad property embed is ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={},
            embeds=["tracks.track_id.playlistId"],
            strict=False
        )
        result = query.all()
        self.assertTrue(len(result) > 0)

    def test_bad_subfilters(self):
        """Test that a bad property subfilter fails."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        self.assertRaisesCode(
            BadRequestError,
            "invalid_subresource",
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={
                "tracks.track_id": SubfilterInfo(
                    filters={"track_id": 5}
                )
            },
            embeds=[]
        )

    def test_bad_subfilters_value(self):
        """Test that a bad property subfilter value fails."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        self.assertRaises(
            ValueError,
            query_builder.apply_subquery_loads,
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={
                "tracks.track_id": "test"
            },
            embeds=[]
        )

    def test_non_strict_bad_subfilters(self):
        """Test bad subfitlers don't cause failure when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=self.db_session),
            subfilters={
                "tracks.track_id": SubfilterInfo(
                    filters={"track_id": 5}
                )
            },
            embeds=[],
            strict=False
        )
        albums = query.all()
        self.assertTrue(len(albums) == 347)
        # TODO - review whether we want this to not load subresource
        # for album in albums:
        #     res = inspect(album)
        #     self.assertTrue("tracks" in res.unloaded)

    def test_self_referential_composite_id_subquery(self):
        """Test a self referential, composite id subquery"""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[]
        )
        composite_nodes = query.all()
        for composite_node in composite_nodes:
            res = inspect(composite_node)
            self.assertTrue("children" not in res.unloaded)
            for child in composite_node.children:
                self.assertTrue(child.node_id == 1)

    def test_composite_id_subquery_with_limit(self):
        """Test a composite id subquery with a limit"""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": 1},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "CompositeNode"."NodeId" AS "CompositeNode_NodeId", 
                "CompositeNode"."CompositeId" AS "CompositeNode_CompositeId", 
                "CompositeNode1"."NodeId" AS "CompositeNode1_NodeId", 
                "CompositeNode1"."CompositeId" AS "CompositeNode1_CompositeId" 
            FROM 
                "CompositeNode" 
                LEFT OUTER JOIN 
                "CompositeNodeToCompositeNode" AS 
                        "CompositeNodeToCompositeNode_1" ON 
                    "CompositeNodeToCompositeNode_1"."NodeId" = 
                        "CompositeNode"."NodeId" 
                    AND 
                    "CompositeNodeToCompositeNode_1"."CompositeId" = 
                        "CompositeNode"."CompositeId" 
                LEFT OUTER JOIN 
                    (
                        SELECT 
                            q1."NodeId" AS "NodeId", 
                            q1."CompositeId" AS "CompositeId", 
                            q1.row_number AS row_number 
                        FROM 
                        (
                            SELECT 
                                "CompositeNode1"."NodeId" AS "NodeId", 
                                "CompositeNode1"."CompositeId" AS 
                                    "CompositeId", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "CompositeNodeToCompositeNode".
                                            "NodeId", 
                                        "CompositeNodeToCompositeNode".
                                            "CompositeId" 
                                    ORDER BY 
                                        "CompositeNode1"."NodeId" ASC, 
                                        "CompositeNode1"."CompositeId" ASC
                                ) AS row_number 
                            FROM 
                                "CompositeNode" AS "CompositeNode1" 
                                JOIN 
                                "CompositeNodeToCompositeNode" ON 
                                    "CompositeNodeToCompositeNode".
                                        "NodeId" = "CompositeNode1"."NodeId" 
                                    AND 
                                    "CompositeNodeToCompositeNode".
                                        "CompositeId" = 
                                            "CompositeNode1"."CompositeId" 
                                    AND 
                                    "CompositeNodeToCompositeNode".
                                        "ChildNodeId" = 
                                            "CompositeNode1"."NodeId" 
                                    AND 
                                    "CompositeNodeToCompositeNode".
                                        "ChildCompositeId" = 
                                            "CompositeNode1"."CompositeId"
                        ) AS q1, 
                        "CompositeNode" AS "CompositeNode1" 
                        WHERE 
                            q1.row_number >= ? 
                            AND 
                            q1.row_number <= ? 
                            AND 
                            "CompositeNode1"."NodeId" = ?
                    ) AS "CompositeNode1" ON 
                        "CompositeNodeToCompositeNode_1"."ChildNodeId" = 
                            "CompositeNode1"."NodeId" 
                        AND 
                        "CompositeNodeToCompositeNode_1"."ChildCompositeId" = 
                            "CompositeNode1"."CompositeId" 
            ORDER BY 
                "CompositeNode"."NodeId" ASC, 
                "CompositeNode"."CompositeId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        self.assertTrue(expected_query == result)

    def test_composite_id_subquery_one_to_many(self):
        """Test a composite id subquery with a many to one relation."""
        query_builder = ModelResourceQueryBuilder()
        query = self.db_session.query(CompositeOne)
        subfilters = {
            "many": SubfilterInfo(
                filters={"many_id": 1},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeOneResource(session=self.db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "CompositeOne"."OneId" AS "CompositeOne_OneId", 
                "CompositeOne"."CompositeOneId" AS 
                    "CompositeOne_CompositeOneId", 
                "CompositeMany1"."ManyId" AS "CompositeMany1_ManyId", 
                "CompositeMany1"."OneId" AS "CompositeMany1_OneId", 
                "CompositeMany1"."CompositeOneId" AS 
                    "CompositeMany1_CompositeOneId" 
            FROM 
                "CompositeOne" 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        q1."ManyId" AS "ManyId", 
                        q1."OneId" AS "OneId", 
                        q1."CompositeOneId" AS "CompositeOneId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "CompositeMany1"."ManyId" AS "ManyId", 
                                "CompositeMany1"."OneId" AS "OneId", 
                                "CompositeMany1"."CompositeOneId" AS 
                                    "CompositeOneId", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "CompositeMany1"."OneId", 
                                        "CompositeMany1"."CompositeOneId" 
                                    ORDER BY 
                                        "CompositeMany1"."ManyId" ASC
                                ) AS row_number 
                            FROM 
                                "CompositeMany" AS "CompositeMany1"
                        ) AS q1, 
                        "CompositeMany" AS "CompositeMany1" 
                    WHERE 
                        q1.row_number >= ? 
                        AND 
                        q1.row_number <= ? 
                        AND 
                        "CompositeMany1"."ManyId" = ?
                ) AS "CompositeMany1" ON 
                    "CompositeOne"."OneId" = "CompositeMany1"."OneId" 
                    AND 
                    "CompositeOne"."CompositeOneId" = 
                        "CompositeMany1"."CompositeOneId" 
            ORDER BY 
                "CompositeOne"."OneId" ASC, 
                "CompositeOne"."CompositeOneId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        self.assertTrue(expected_query == result)
