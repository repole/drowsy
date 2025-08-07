"""
    tests.test_query_builder
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Query builder tests for Drowsy.

"""
# :copyright: (c) 2016-2025 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
from pytest import raises
from sqlalchemy import select
from sqlalchemy.inspection import inspect
from drowsy.exc import BadRequestError
from drowsy.query_builder import (
    manipulate_filters_to_list, QueryBuilder, ModelResourceQueryBuilder)
from drowsy.parser import SubfilterInfo, SortInfo
from tests.base import DrowsyDatabaseTests
from tests.models import (
    Album, CompositeOne, CompositeNode, Customer, Employee, Playlist, Track
)
from tests.resources import (
    AlbumResource, TrackResource, CompositeNodeResource,
    CompositeOneResource, CustomerResource, EmployeeResource,
    PlaylistResource
)


class TestDrowsyQueryBuilder(DrowsyDatabaseTests):

    """Test drowsy query building across all databases."""

    @staticmethod
    def test_apply_sorts_simple(db_session):
        """Test applying a single sort."""
        query_builder = QueryBuilder()
        query = select(Album)
        query = query_builder.apply_sorts(
            query=query,
            sorts=[SortInfo(attr="album_id", direction="ASC")]
        )
        results = db_session.execute(query).scalars().all()
        last_album_id = -1
        for result in results:
            assert result.album_id >= last_album_id
            last_album_id = result.album_id

    @staticmethod
    def test_apply_sorts_fail(db_session):
        """Test applying a single sort."""
        query_builder = QueryBuilder()
        query = select(Album)
        with raises(AttributeError):
            query_builder.apply_sorts(
                query=query,
                sorts=[SortInfo(attr="badattr", direction="ASC")]
            )

    @staticmethod
    def test_apply_limit_negative_limit_fail(db_session):
        """Test that a negative limit fails."""
        query_builder = QueryBuilder()
        query = select(Album)
        with raises(ValueError):
            query_builder.apply_limit(
                query=query,
                limit=-1)

    @staticmethod
    def test_apply_offset_negative_offset_fail(db_session):
        """Test that a negative offset fails."""
        query_builder = QueryBuilder()
        query = select(Album)
        with raises(ValueError):
            query_builder.apply_offset(
                query=query,
                offset=-1)

    @staticmethod
    def test_simple_subfilter(db_session):
        """Test applying a simple subfilter."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 5}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        albums = db_session.execute(query).scalars().all()
        for album in albums:
            assert len(album.tracks) <= 1
            if album.tracks:
                assert album.tracks[0].track_id == 5

    @staticmethod
    def test_apply_sorts_bad_query(db_session):
        """Test applying sorts with a bad query fails."""
        query_builder = QueryBuilder()
        query = select(Album, Track)
        with raises(ValueError):
            query_builder.apply_sorts(
                query,
                sorts=[])

    @staticmethod
    def test_subfilter_sorts_no_limit_offset_fail(db_session):
        """Check that subresource sorts without limit or offset fail."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True
            )
        assert excinf.value.code == "invalid_subresource_sorts"

    @staticmethod
    def test_simple_subfilter_limit_too_big(db_session):
        """Check that a limit too large on subresource fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Customer)
        subfilters = {
            "invoices": SubfilterInfo(
                offset=1,
                limit=10000
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=CustomerResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True
            )
        assert excinf.value.code == "invalid_subresource_limit"

    @staticmethod
    def test_subfilter_invalid_fail(db_session):
        """Check that bad subresource filters fail."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}}
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True
            )
        assert excinf.value.code == "filters_field_op_error"

    @staticmethod
    def test_subfilter_invalid_ignore(db_session):
        """Check that non strict bad subresource filters is ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(
                session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=False,
            strict=False
        )
        result = db_session.execute(query).scalars().all()
        assert len(result) > 0

    @staticmethod
    def test_subfilter_invalid_limit_fail(db_session):
        """Check subresource query with an invalid root limit fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True,
                limit=-1
            )
        assert excinf.value.code == "invalid_limit_value"

    @staticmethod
    def test_subfilter_invalid_limit_ignore(db_session):
        """Check subresource query with invalid root limit ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True,
                limit=-1,
                strict=False
            )
        assert query is not None

    @staticmethod
    def test_subfilter_invalid_sort_fail(db_session):
        """Check subresource query with an invalid root sort fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id")]
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                sorts=[SortInfo(attr="TEST")],
                subfilters=subfilters,
                embeds=[],
                dialect_override=True
            )
        assert excinf.value.code == "invalid_sort_field"

    @staticmethod
    def test_subfilter_invalid_sort_ignore(db_session):
        """Check subresource query with invalid root sort is ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id")]
            )
        }
        query = query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                sorts=[SortInfo(attr="TEST")],
                embeds=[],
                dialect_override=True,
                strict=False
            )
        assert query is not None

    @staticmethod
    def test_subfilter_root_sort(db_session):
        """Check subresource query with root sort works."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id")]
            )
        }
        query = query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                sorts=[SortInfo(attr="album_id", direction="DESC")],
                embeds=[],
                dialect_override=True,
                strict=False
            )
        result = db_session.execute(query).scalars().first()
        assert result.album_id == 347

    @staticmethod
    def test_subfilter_invalid_offset_fail(db_session):
        """Check subresource query with an invalid root offset fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True,
                offset=-1
            )
        assert excinf.value.code == "invalid_offset_value"

    @staticmethod
    def test_subfilter_invalid_offset_ignore(db_session):
        """Check subresource query with invalid root offset ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                sorts=[SortInfo(attr="track_id", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True,
                offset=-1,
                strict=False
            )
        assert query is not None

    @staticmethod
    def test_many_to_one_limit_fail(db_session):
        """Test a limit/offset on a many to one relationship fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Track)
        subfilters = {
            "album": SubfilterInfo(
                offset=1,
                limit=None
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=TrackResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True
            )
        assert excinf.value.code == "invalid_subresource_options"

    @staticmethod
    def test_subquery_embeds(db_session):
        """Test that a simple subquery can work alongside an embed."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "artist": SubfilterInfo(
                filters={"artist_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=["tracks", "artist"]
        )
        albums = db_session.execute(query).scalars().all()
        for album in albums:
            res = inspect(album)
            assert "tracks" not in res.unloaded
            if album.artist:
                assert album.artist.artist_id == 1

    @staticmethod
    def test_same_subquery_embeds(db_session):
        """Test that a simple subquery works with a duplicate embed."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=["tracks"]
        )
        albums = db_session.execute(query).scalars().all()
        for album in albums:
            res = inspect(album)
            assert "tracks" not in res.unloaded
            if album.tracks:
                assert len(album.tracks) == 1
                assert album.tracks[0].track_id == 1

    @staticmethod
    def test_simple_embeds(db_session):
        """Test that a simple embed works."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters={},
            embeds=["tracks"]
        )
        albums = db_session.execute(query).scalars().all()
        for album in albums:
            res = inspect(album)
            assert "tracks" not in res.unloaded

    @staticmethod
    def test_property_embeds(db_session):
        """Test that property embed works."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters={},
            embeds=["tracks.track_id"]
        )
        albums = db_session.execute(query).scalars().all()
        for album in albums:
            res = inspect(album)
            assert "tracks" not in res.unloaded

    @staticmethod
    def test_bad_embeds(db_session):
        """Test that a bad property embed fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(session=db_session),
                subfilters={},
                embeds=["tracks.track_id.playlistId"]
            )
        assert excinf.value.code == "invalid_embed"

    @staticmethod
    def test_bad_embeds_ignore(db_session):
        """Test that a non strict bad property embed is ignored."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters={},
            embeds=["tracks.track_id.playlistId"],
            strict=False
        )
        result = db_session.execute(query).scalars().all()
        assert len(result) > 0

    @staticmethod
    def test_too_complex(db_session):
        """Test that an overly complex query fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        with raises(BadRequestError) as excinf:
            query_builder.build(
                query=query,
                resource=AlbumResource(session=db_session),
                filters={"tracks.track_id": 5},
                subfilters={},
                stack_size_limit=1
            )
        assert excinf.value.code == "filters_too_complex"

    @staticmethod
    def test_no_op_error_message(db_session):
        """Test that filters trigger an error message with no $op."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        with raises(BadRequestError) as excinf:
            query_builder.build(
                query=query,
                resource=AlbumResource(session=db_session),
                filters={"tracks": {}},
                subfilters={},
                stack_size_limit=1
            )
        assert excinf.value.code == "filters_field_error"

    @staticmethod
    def test_bad_subfilters(db_session):
        """Test that a bad property subfilter fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(session=db_session),
                subfilters={
                    "tracks.track_id": SubfilterInfo(
                        filters={"track_id": 5}
                    )
                },
                embeds=[]
            )
        assert excinf.value.code == "invalid_subresource"

    @staticmethod
    def test_bad_subfilters_value(db_session):
        """Test that a bad property subfilter value fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        with raises(ValueError):
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(session=db_session),
                subfilters={
                    "tracks.track_id": "test"
                },
                embeds=[]
            )

    @staticmethod
    def test_non_strict_bad_subfilters(db_session):
        """Test bad subfitlers don't cause failure when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters={
                "tracks.track_id": SubfilterInfo(
                    filters={"track_id": 5}
                )
            },
            embeds=[],
            strict=False
        )
        albums = db_session.execute(query).scalars().all()
        assert len(albums) == 347
        # TODO - review whether we want this to not load subresource
        # for album in albums:
        #     res = inspect(album)
        #     assert "tracks" in res.unloaded)

    @staticmethod
    def test_whitelist_fail(db_session):
        """Test a missing whitelist key causes permission error."""
        from drowsy.exc import PermissionDeniedError
        query_builder = ModelResourceQueryBuilder()
        query = select(Employee)
        resource = EmployeeResource(session=db_session)
        with raises(PermissionDeniedError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=resource,
                subfilters={
                    "customers": SubfilterInfo(
                        filters={"phone": 5}
                    )
                },
                embeds=[],
                strict=True
            )
        assert excinf.value.code == "filters_permission_error"

    @staticmethod
    def test_self_referential_composite_id_subquery(db_session):
        """Test a self referential, composite id subquery"""
        query_builder = ModelResourceQueryBuilder()
        query = select(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": 1}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        composite_nodes = db_session.execute(query).unique().scalars().all()
        for composite_node in composite_nodes:
            res = inspect(composite_node)
            assert "children" not in res.unloaded
            for child in composite_node.children:
                assert child.node_id == 1

    @staticmethod
    def test_root_composite_id_limit_with_subquery(db_session):
        """Limit to a composite id root resource using subqueries."""
        query_builder = ModelResourceQueryBuilder()
        query = select(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": 6}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=db_session),
            subfilters=subfilters,
            limit=1,
            offset=0,
            embeds=[]
        )
        result = db_session.execute(query).unique().scalars().all()
        assert result is not None
        assert len(result) == 1
        assert result[0].node_id == 1
        assert len(result[0].children) == 1
        assert result[0].children[0].node_id == 6

    @staticmethod
    def test_root_limit_with_subquery(db_session):
        """Test applying a limit to a root resource using subqueries."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 2}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            limit=1,
            offset=1,
            embeds=[]
        )
        result = db_session.execute(query).scalars().all()
        assert result is not None
        assert len(result) == 1
        assert result[0].album_id == 2
        assert len(result[0].tracks) == 1
        assert result[0].tracks[0].track_id == 2

    @staticmethod
    def test_circular_relationship_fails(db_session):
        """Referencing the same relationship multiple times fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Playlist)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=5,
                sorts=[SortInfo(attr="name", direction="ASC")]
            ),
            "tracks.playlists": SubfilterInfo(
                filters={"playlist_id": {"$lte": 6}},
                limit=4,
                sorts=[SortInfo(attr="name", direction="ASC")]
            ),
            "tracks.playlists.tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=5,
                sorts=[SortInfo(attr="name", direction="ASC")]
            ),
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=PlaylistResource(session=db_session),
                subfilters=subfilters,
                embeds=[],
                limit=3,
                dialect_override=True
            )
        assert excinf.value.code == "invalid_subresource_multi_embed"

    @staticmethod
    def test_bad_subfilter_with_limit(db_session):
        """Test bad subfilter using a limit fails."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}},
                limit=1
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=True,
                strict=True
            )
        assert excinf.value.code == "filters_field_op_error"


class TestDrowsyQueryBuilderSqlite(DrowsyDatabaseTests):

    """Sqlite specific query builder tests."""

    backends = ['sqlite']

    @staticmethod
    def test_root_limit_with_subquery(db_session):
        """Apply limit to root resource with subqueries & no row_num."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": 2}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            limit=1,
            offset=1,
            embeds=[],
            dialect_override=False
        )
        result = db_session.execute(query).scalars().all()
        assert result is not None
        assert len(result) == 1
        assert result[0].album_id == 2
        assert len(result[0].tracks) == 1
        assert result[0].tracks[0].track_id == 2

    @staticmethod
    def test_root_composite_id_limit_with_subquery(db_session):
        """Limit composite id root using subqueries without row_num."""
        query_builder = ModelResourceQueryBuilder()
        query = select(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": 6}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=db_session),
            subfilters=subfilters,
            limit=1,
            offset=0,
            embeds=[],
            dialect_override=False
        )
        result = db_session.execute(query).scalars().unique().all()
        assert result is not None
        assert len(result) == 1
        assert result[0].node_id == 1
        assert len(result[0].children) == 1
        assert result[0].children[0].node_id == 6

    @staticmethod
    def test_root_and_nested_limit_offset(db_session):
        """Test offset and limit in both root and nested collections."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 15}},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=10,
            offset=1,
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                anon_1."AlbumId",
                anon_1."Title",
                anon_1."ArtistId",
                "Track1"."TrackId", 
                "Track1"."Name", 
                "Track1"."AlbumId" AS "AlbumId_1", 
                "Track1"."MediaTypeId", 
                "Track1"."GenreId", 
                "Track1"."Composer", 
                "Track1"."Milliseconds", 
                "Track1"."Bytes", 
                "Track1"."UnitPrice" 
            FROM 
                (
                    SELECT 
                        "Album"."AlbumId" AS "AlbumId", 
                        "Album"."Title" AS "Title", 
                        "Album"."ArtistId" AS "ArtistId", 
                        row_number() OVER (
                            ORDER BY "Album"."AlbumId" ASC) AS row_number 
                    FROM 
                        "Album"
                ) AS anon_1 
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
                                    PARTITION BY "Track1"."AlbumId" 
                                    ORDER BY "Track1"."TrackId" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1" 
                            WHERE 
                                "Track1"."TrackId" >= :TrackId_1
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1 
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "Track1" ON 
                    anon_1."AlbumId" = "Track1"."AlbumId" 
            WHERE 
                anon_1.row_number >= :row_number_3
                AND 
                anon_1.row_number <= :row_number_4
            ORDER BY 
                anon_1.row_number
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_simple_subfilter_limit_offset(db_session):
        """Test offset and limit in a subresource."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Album"."AlbumId", 
                "Album"."Title", 
                "Album"."ArtistId", 
                "Track1"."TrackId", 
                "Track1"."Name", 
                "Track1"."AlbumId" AS "AlbumId_1", 
                "Track1"."MediaTypeId", 
                "Track1"."GenreId", 
                "Track1"."Composer", 
                "Track1"."Milliseconds", 
                "Track1"."Bytes", 
                "Track1"."UnitPrice" 
            FROM 
                "Album" 
                LEFT OUTER JOIN (
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
                                    PARTITION BY "Track1"."AlbumId" 
                                    ORDER BY "Track1"."TrackId" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1" 
                            WHERE 
                                "Track1"."TrackId" >= :TrackId_1
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "Track1" ON "Album"."AlbumId" = "Track1"."AlbumId" 
            ORDER BY 
                "Album"."AlbumId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_subfilter_limit_offset_sorts(db_session):
        """Test subfiltering with sorts works with limit and offset."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
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
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Album"."AlbumId", 
                "Album"."Title", 
                "Album"."ArtistId", 
                "Track1"."TrackId", 
                "Track1"."Name", 
                "Track1"."AlbumId" AS "AlbumId_1", 
                "Track1"."MediaTypeId", 
                "Track1"."GenreId", 
                "Track1"."Composer", 
                "Track1"."Milliseconds", 
                "Track1"."Bytes", 
                "Track1"."UnitPrice" 
            FROM 
                "Album" 
                LEFT OUTER JOIN (
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
                                    PARTITION BY "Track1"."AlbumId" 
                                    ORDER BY "Track1"."Name" ASC, 
                                             "Track1"."TrackId"ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1" 
                            WHERE 
                                "Track1"."TrackId" >= :TrackId_1
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "Track1" ON "Album"."AlbumId" = "Track1"."AlbumId" 
            ORDER BY 
                "Album"."AlbumId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_non_strict_bad_sublimits(db_session):
        """Test bad sublimits don't cause failure when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Customer)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CustomerResource(session=db_session),
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
                "Customer"."CustomerId", 
                "Customer"."FirstName", 
                "Customer"."LastName", 
                "Customer"."Company", 
                "Customer"."Address", 
                "Customer"."City", 
                "Customer"."State", 
                "Customer"."Country", 
                "Customer"."PostalCode", 
                "Customer"."Phone", 
                "Customer"."Fax", 
                "Customer"."Email", 
                "Customer"."SupportRepId", 
                "Invoice1"."InvoiceId", 
                "Invoice1"."CustomerId" AS "CustomerId_1", 
                "Invoice1"."InvoiceDate", 
                "Invoice1"."BillingAddress", 
                "Invoice1"."BillingCity", 
                "Invoice1"."BillingState", 
                "Invoice1"."BillingCountry", 
                "Invoice1"."BillingPostalCode", 
                "Invoice1"."Total" 
            FROM 
                "Customer" 
                LEFT OUTER JOIN (
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
                                "Invoice1"."BillingAddress" AS "BillingAddress", 
                                "Invoice1"."BillingCity" AS "BillingCity", 
                                "Invoice1"."BillingState" AS "BillingState", 
                                "Invoice1"."BillingCountry" AS "BillingCountry", 
                                "Invoice1"."BillingPostalCode" AS "BillingPostalCode", 
                                "Invoice1"."Total" AS "Total", 
                                row_number() OVER (
                                    PARTITION BY "Invoice1"."CustomerId" 
                                    ORDER BY "Invoice1"."InvoiceId" ASC
                                ) AS row_number 
                            FROM 
                                "Invoice" AS "Invoice1"
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "Invoice1" ON 
                    "Invoice1"."CustomerId" = "Customer"."CustomerId" 
            ORDER BY 
                "Customer"."CustomerId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_self_ref_composite_id_subquery_with_limit(db_session):
        """Self referential a composite id subquery with a limit"""
        query_builder = ModelResourceQueryBuilder()
        query = select(CompositeNode)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": {"$in": [1, 2]}},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        # TODO - figure out why CompositeNode and CompositeNode1 flip
        # NodeId/NodeId_1 here...labeling is weird.
        # Happens on applying load options (contains_eager)
        expected_query = (
            """
            SELECT 
                "CompositeNode1"."NodeId",
                "CompositeNode1"."CompositeId",
                "CompositeNode"."NodeId" AS "NodeId_1", 
                "CompositeNode"."CompositeId" AS "CompositeId_1"
            FROM 
                "CompositeNode" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."NodeId" AS "NodeId", 
                        q1."CompositeId" AS "CompositeId", 
                        q1."NodeId_2" AS "NodeId_2", 
                        q1."CompositeId_2" AS "CompositeId_2", 
                        q1."ChildNodeId" AS "ChildNodeId", 
                        q1."ChildCompositeId" AS "ChildCompositeId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "CompositeNode1"."NodeId" AS "NodeId", 
                                "CompositeNode1"."CompositeId" AS 
                                    "CompositeId", 
                                "CompositeNodeToCompositeNode"."NodeId" AS 
                                    "NodeId_2", 
                                "CompositeNodeToCompositeNode"."CompositeId" AS 
                                    "CompositeId_2", 
                                "CompositeNodeToCompositeNode"."ChildNodeId" AS 
                                    "ChildNodeId", 
                                "CompositeNodeToCompositeNode".
                                    "ChildCompositeId" AS 
                                        "ChildCompositeId", 
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
                                JOIN "CompositeNodeToCompositeNode" ON 
                                    "CompositeNodeToCompositeNode".
                                        "ChildNodeId" = 
                                    "CompositeNode1"."NodeId" 
                                    AND 
                                    "CompositeNodeToCompositeNode".
                                        "ChildCompositeId" = 
                                    "CompositeNode1"."CompositeId" 
                            WHERE 
                                "CompositeNode1"."NodeId" IN (:NodeId_1, :NodeId_2)
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "CompositeNode1" ON 
                    "CompositeNode"."NodeId" = 
                    "CompositeNode1"."NodeId_2" 
                    AND 
                    "CompositeNode"."CompositeId" = 
                    "CompositeNode1"."CompositeId_2" 
            ORDER BY 
                "CompositeNode"."NodeId" ASC, 
                "CompositeNode"."CompositeId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "").replace(
            "__[POSTCOMPILE_NodeId_3]", ":NodeId_1,:NodeId_2")
        assert expected_query == result

    @staticmethod
    def test_multilevel_subfilter_limit(db_session):
        """Test subfiltering with sorts works with limit and offset."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=4,
                sorts=[SortInfo(attr="name", direction="ASC")]
            ),
            "tracks.playlists": SubfilterInfo(
                filters={"playlist_id": {"$gte": 6}},
                limit=5,
                sorts=[SortInfo(attr="name", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=3,
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                anon_1."AlbumId", 
                anon_1."Title", 
                anon_1."ArtistId", 
                "Track1"."TrackId", 
                "Track1"."Name", 
                "Track1"."AlbumId" AS "AlbumId_1", 
                "Track1"."MediaTypeId", 
                "Track1"."GenreId", 
                "Track1"."Composer", 
                "Track1"."Milliseconds", 
                "Track1"."Bytes", 
                "Track1"."UnitPrice", 
                "Playlist1"."PlaylistId", 
                "Playlist1"."Name" AS "Name_1" 
            FROM 
                (
                    SELECT 
                        "Album"."AlbumId" AS "AlbumId", 
                        "Album"."Title" AS "Title", 
                        "Album"."ArtistId" AS "ArtistId", 
                        row_number() OVER (
                            ORDER BY 
                                "Album"."AlbumId" ASC
                        ) AS row_number 
                    FROM 
                        "Album"
                ) AS anon_1 
                LEFT OUTER JOIN (
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
                                "Track1"."Milliseconds" AS 
                                    "Milliseconds", 
                                "Track1"."Bytes" AS "Bytes", 
                                "Track1"."UnitPrice" AS "UnitPrice", 
                                row_number() OVER (
                                    PARTITION BY "Track1"."AlbumId" 
                                    ORDER BY 
                                        "Track1"."Name" ASC,
                                        "Track1"."TrackId" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1" 
                            WHERE 
                                "Track1"."TrackId" >= :TrackId_1
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "Track1" ON 
                    anon_1."AlbumId" = "Track1"."AlbumId" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."PlaylistId" AS "PlaylistId", 
                        q1."Name" AS "Name", 
                        q1."PlaylistId_1" AS "PlaylistId_1", 
                        q1."TrackId" AS "TrackId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Playlist1"."PlaylistId" AS 
                                    "PlaylistId", 
                                "Playlist1"."Name" AS "Name", 
                                "PlaylistTrack"."PlaylistId" AS 
                                    "PlaylistId_1", 
                                "PlaylistTrack"."TrackId" AS 
                                    "TrackId", 
                                row_number() OVER (
                                    PARTITION BY "PlaylistTrack"."TrackId" 
                                    ORDER BY 
                                        "Playlist1"."Name" ASC,
                                        "Playlist1"."PlaylistId" ASC
                                ) AS row_number 
                            FROM 
                                "Playlist" AS "Playlist1" 
                                JOIN 
                                "PlaylistTrack" ON 
                                    "PlaylistTrack"."PlaylistId" = 
                                    "Playlist1"."PlaylistId" 
                            WHERE 
                                "Playlist1"."PlaylistId" >= :PlaylistId_2
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_3
                        AND 
                        q1.row_number <= :row_number_4
                ) AS "Playlist1" ON 
                    "Playlist1"."TrackId" = 
                    "Track1"."TrackId" 
            WHERE 
                anon_1.row_number >= :row_number_5
                AND 
                anon_1.row_number <= :row_number_6
            ORDER BY 
                anon_1.row_number
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_many_to_many_subresource_limit(db_session):
        """Many to many relationships with limits loaded properly."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Playlist)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=5,
                sorts=[SortInfo(attr="name", direction="ASC")]
            ),
            "tracks.playlists": SubfilterInfo(
                filters={"playlist_id": {"$lte": 6}},
                limit=4,
                sorts=[SortInfo(attr="name", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=PlaylistResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=3,
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Track1"."TrackId", 
                "Track1"."Name", 
                "Track1"."AlbumId", 
                "Track1"."MediaTypeId", 
                "Track1"."GenreId", 
                "Track1"."Composer", 
                "Track1"."Milliseconds", 
                "Track1"."Bytes", 
                "Track1"."UnitPrice", 
                "Playlist1"."PlaylistId", 
                "Playlist1"."Name" AS "Name_1",
                anon_1."PlaylistId" AS "PlaylistId_1", 
                anon_1."Name" AS "Name_2"
            FROM 
                (
                    SELECT 
                        "Playlist"."PlaylistId" AS "PlaylistId", 
                        "Playlist"."Name" AS "Name", 
                        row_number() OVER (
                            ORDER BY 
                                "Playlist"."PlaylistId" ASC
                        ) AS row_number 
                    FROM 
                        "Playlist"
                ) AS anon_1 
                LEFT OUTER JOIN (
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
                        q1."PlaylistId" AS "PlaylistId", 
                        q1."TrackId_1" AS "TrackId_1", 
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
                                "PlaylistTrack"."PlaylistId" AS "PlaylistId",
                                "PlaylistTrack"."TrackId" AS "TrackId_1", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "PlaylistTrack"."PlaylistId" 
                                    ORDER BY 
                                        "Track1"."Name" ASC,
                                        "Track1"."TrackId" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1" 
                                JOIN 
                                "PlaylistTrack" ON 
                                    "PlaylistTrack"."TrackId" = 
                                    "Track1"."TrackId" 
                            WHERE 
                                "Track1"."TrackId" >= :TrackId_2
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "Track1" ON 
                    "Track1"."PlaylistId" = anon_1."PlaylistId"
                LEFT OUTER JOIN (
                    SELECT 
                        q1."PlaylistId" AS "PlaylistId", 
                        q1."Name" AS "Name", 
                        q1."PlaylistId_2" AS "PlaylistId_2", 
                        q1."TrackId" AS "TrackId", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Playlist1"."PlaylistId" AS "PlaylistId", 
                                "Playlist1"."Name" AS "Name", 
                                "PlaylistTrack"."PlaylistId" AS "PlaylistId_2", 
                                "PlaylistTrack"."TrackId" AS "TrackId", 
                                row_number() OVER (
                                    PARTITION BY 
                                        "PlaylistTrack"."TrackId" 
                                    ORDER BY 
                                        "Playlist1"."Name" ASC,
                                        "Playlist1"."PlaylistId" ASC
                                ) AS row_number 
                            FROM 
                                "Playlist" AS "Playlist1" 
                                JOIN 
                                "PlaylistTrack" ON 
                                    "PlaylistTrack"."PlaylistId" = 
                                    "Playlist1"."PlaylistId" 
                            WHERE 
                                "Playlist1"."PlaylistId" <= :PlaylistId_3
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_3
                        AND 
                        q1.row_number <= :row_number_4
                ) AS "Playlist1" ON 
                    "Playlist1"."TrackId" = "Track1"."TrackId" 
            WHERE 
                anon_1.row_number >= :row_number_5
                AND 
                anon_1.row_number <= :row_number_6
            ORDER BY 
                anon_1.row_number
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_subresource_bad_dialect_fail(db_session):
        """Test a sublimit/offset fails with unsupported dialect."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                offset=1,
                limit=10
            )
        }
        with raises(BadRequestError) as excinf:
            query_builder.apply_subquery_loads(
                query=query,
                resource=AlbumResource(
                    session=db_session),
                subfilters=subfilters,
                embeds=[],
                dialect_override=False
            )
        assert excinf.value.code == "invalid_subresource_options"

    @staticmethod
    def test_composite_root_limit_with_subquery_limit(db_session):
        """Apply limit to both root + subresource with composite id."""
        query_builder = ModelResourceQueryBuilder()
        query = select(CompositeOne)
        subfilters = {
            "many": SubfilterInfo(
                filters={"many_id": 1},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeOneResource(session=db_session),
            subfilters=subfilters,
            limit=1,
            offset=1,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                anon_1."OneId", 
                anon_1."CompositeOneId", 
                "CompositeMany1"."ManyId", 
                "CompositeMany1"."OneId" AS "OneId_1", 
                "CompositeMany1"."CompositeOneId" AS "CompositeOneId_1"
            FROM 
                (
                    SELECT 
                        "CompositeOne"."OneId" AS "OneId", 
                        "CompositeOne"."CompositeOneId" AS "CompositeOneId", 
                        row_number() OVER (
                            ORDER BY 
                                "CompositeOne"."OneId" ASC, 
                                "CompositeOne"."CompositeOneId" ASC
                        ) AS row_number 
                    FROM 
                        "CompositeOne"
                ) AS anon_1 
                LEFT OUTER JOIN (
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
                            WHERE 
                                "CompositeMany1"."ManyId" = :ManyId_1
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "CompositeMany1" ON 
                    anon_1."OneId" = "CompositeMany1"."OneId" 
                    AND 
                    anon_1."CompositeOneId" = "CompositeMany1"."CompositeOneId"
            WHERE 
                anon_1.row_number >= :row_number_3
                AND 
                anon_1.row_number <= :row_number_4
            ORDER BY 
                anon_1.row_number
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_composite_id_subquery_one_to_many(db_session):
        """Test a composite id subquery with a many to one relation."""
        query_builder = ModelResourceQueryBuilder()
        query = select(CompositeOne)
        subfilters = {
            "many": SubfilterInfo(
                filters={"many_id": 1},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeOneResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "CompositeOne"."OneId", 
                "CompositeOne"."CompositeOneId", 
                "CompositeMany1"."ManyId", 
                "CompositeMany1"."OneId" AS "OneId_1", 
                "CompositeMany1"."CompositeOneId" AS "CompositeOneId_1"
            FROM 
                "CompositeOne" 
                LEFT OUTER JOIN (
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
                            WHERE 
                                "CompositeMany1"."ManyId" = :ManyId_1
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
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
        assert expected_query == result

    @staticmethod
    def test_self_ref_one_to_many_limit(db_session):
        """Self referential one to many subquery with a limit"""
        query_builder = ModelResourceQueryBuilder()
        query = select(Employee)
        subfilters = {
            "subordinates": SubfilterInfo(
                filters={"employee_id": {"$nin": [1, 2]}},
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=EmployeeResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                "Employee"."EmployeeId", 
                "Employee"."LastName", 
                "Employee"."FirstName", 
                "Employee"."Title", 
                "Employee"."ReportsTo", 
                "Employee"."BirthDate", 
                "Employee"."HireDate", 
                "Employee"."Address", 
                "Employee"."City", 
                "Employee"."State", 
                "Employee"."Country", 
                "Employee"."PostalCode",
                "Employee"."Phone", 
                "Employee"."Fax", 
                "Employee"."Email", 
                "Employee1"."EmployeeId" AS "EmployeeId_1", 
                "Employee1"."LastName" AS "LastName_1", 
                "Employee1"."FirstName" AS "FirstName_1", 
                "Employee1"."Title" AS "Title_1", 
                "Employee1"."ReportsTo" AS "ReportsTo_1", 
                "Employee1"."BirthDate" AS "BirthDate_1", 
                "Employee1"."HireDate" AS "HireDate_1", 
                "Employee1"."Address" AS "Address_1", 
                "Employee1"."City" AS "City_1", 
                "Employee1"."State" AS "State_1", 
                "Employee1"."Country" AS "Country_1", 
                "Employee1"."PostalCode" AS "PostalCode_1", 
                "Employee1"."Phone" AS "Phone_1", 
                "Employee1"."Fax" AS "Fax_1", 
                "Employee1"."Email" AS "Email_1"
            FROM 
                "Employee" 
                LEFT OUTER JOIN (
                    SELECT 
                        q1."EmployeeId" AS "EmployeeId", 
                        q1."LastName" AS "LastName", 
                        q1."FirstName" AS "FirstName", 
                        q1."Title" AS "Title", 
                        q1."ReportsTo" AS "ReportsTo", 
                        q1."BirthDate" AS "BirthDate", 
                        q1."HireDate" AS "HireDate", 
                        q1."Address" AS "Address", 
                        q1."City" AS "City", 
                        q1."State" AS "State", 
                        q1."Country" AS "Country", 
                        q1."PostalCode" AS "PostalCode", 
                        q1."Phone" AS "Phone", 
                        q1."Fax" AS "Fax", 
                        q1."Email" AS "Email", 
                        q1.row_number AS row_number 
                    FROM 
                        (
                            SELECT 
                                "Employee1"."EmployeeId" AS "EmployeeId", 
                                "Employee1"."LastName" AS "LastName", 
                                "Employee1"."FirstName" AS "FirstName", 
                                "Employee1"."Title" AS "Title", 
                                "Employee1"."ReportsTo" AS "ReportsTo", 
                                "Employee1"."BirthDate" AS "BirthDate", 
                                "Employee1"."HireDate" AS "HireDate", 
                                "Employee1"."Address" AS "Address", 
                                "Employee1"."City" AS "City", 
                                "Employee1"."State" AS "State", 
                                "Employee1"."Country" AS "Country", 
                                "Employee1"."PostalCode" AS "PostalCode", 
                                "Employee1"."Phone" AS "Phone", 
                                "Employee1"."Fax" AS "Fax", 
                                "Employee1"."Email" AS "Email", 
                                row_number() OVER (
                                    PARTITION BY "Employee1"."ReportsTo" 
                                    ORDER BY 
                                        "Employee1"."EmployeeId" ASC
                                ) AS row_number 
                            FROM 
                                "Employee" AS "Employee1" 
                            WHERE 
                                ("Employee1"."EmployeeId" NOT IN (
                                    :EmployeeId_1, :EmployeeId_2))
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "Employee1" ON 
                    "Employee"."EmployeeId" = "Employee1"."ReportsTo" 
            ORDER BY 
                "Employee"."EmployeeId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "").replace(
            "__[POSTCOMPILE_EmployeeId_2]", ":EmployeeId_1,:EmployeeId_2")
        assert expected_query == result

    @staticmethod
    def test_bad_subfilter_ignore_with_limit(db_session):
        """Bad subfilter using a limit gets ignored when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}},
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            dialect_override=True,
            strict=False
        )
        expected_query = (
            """
            SELECT 
                "Album"."AlbumId", 
                "Album"."Title", 
                "Album"."ArtistId", 
                "Track1"."TrackId", 
                "Track1"."Name", 
                "Track1"."AlbumId" AS "AlbumId_1", 
                "Track1"."MediaTypeId", 
                "Track1"."GenreId", 
                "Track1"."Composer", 
                "Track1"."Milliseconds", 
                "Track1"."Bytes", 
                "Track1"."UnitPrice"
            FROM 
                "Album" 
                LEFT OUTER JOIN (
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
                                    PARTITION BY "Track1"."AlbumId" 
                                    ORDER BY 
                                        "Track1"."TrackId" ASC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1"
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "Track1" ON "Album"."AlbumId" = "Track1"."AlbumId" 
            ORDER BY 
                "Album"."AlbumId" ASC
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_manipulate_filters_to_list_tuple():
        """Make sure tuple of filters is converted to list."""
        param = (1, 2, 3)
        result = manipulate_filters_to_list(param)
        assert isinstance(result, list)
        assert len(result) == 3

    @staticmethod
    def test_manipulate_filters_to_list_single():
        """Make single filter is converted to list."""
        param = "test"
        result = manipulate_filters_to_list(param)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "test"

    @staticmethod
    def test_subresource_sort_by_pk(db_session):
        """Sort by PK on subresource loaded properly."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=5,
                sorts=[SortInfo(attr="track_id", direction="DESC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=3,
            dialect_override=True
        )
        expected_query = (
            """
            SELECT 
                anon_1."AlbumId", 
                anon_1."Title", 
                anon_1."ArtistId", 
                "Track1"."TrackId", 
                "Track1"."Name", 
                "Track1"."AlbumId" AS "AlbumId_1", 
                "Track1"."MediaTypeId", 
                "Track1"."GenreId", 
                "Track1"."Composer", 
                "Track1"."Milliseconds",
                "Track1"."Bytes", 
                "Track1"."UnitPrice" 
            FROM 
                (
                    SELECT 
                        "Album"."AlbumId" AS "AlbumId", 
                        "Album"."Title" AS "Title", 
                        "Album"."ArtistId" AS "ArtistId", 
                        row_number() OVER (
                            ORDER BY "Album"."AlbumId" ASC) AS row_number 
                    FROM 
                        "Album"
                ) AS anon_1 
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
                                    PARTITION BY "Track1"."AlbumId" 
                                    ORDER BY "Track1"."TrackId" DESC
                                ) AS row_number 
                            FROM 
                                "Track" AS "Track1" 
                            WHERE 
                                "Track1"."TrackId" >= :TrackId_1
                        ) AS q1 
                    WHERE 
                        q1.row_number >= :row_number_1
                        AND 
                        q1.row_number <= :row_number_2
                ) AS "Track1" ON 
                    anon_1."AlbumId" = "Track1"."AlbumId" 
            WHERE 
                anon_1.row_number >= :row_number_3
                AND 
                anon_1.row_number <= :row_number_4
            ORDER 
                BY anon_1.row_number
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result

    @staticmethod
    def test_same_entity_grandchild_load(db_session):
        """Test loading strategy for same entity grand child works."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Playlist)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}}
            ),
            "tracks.playlists": SubfilterInfo(
                filters={"playlist_id": {"$lte": 6}}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=PlaylistResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=3
        )
        expected_query = (
            """
            SELECT 
                "Track1"."TrackId", 
                "Track1"."Name", 
                "Track1"."AlbumId", 
                "Track1"."MediaTypeId", 
                "Track1"."GenreId", 
                "Track1"."Composer", 
                "Track1"."Milliseconds", 
                "Track1"."Bytes",
                "Track1"."UnitPrice", 
                "Playlist1"."PlaylistId", 
                "Playlist1"."Name" AS "Name_1",
                anon_1."PlaylistId" AS "PlaylistId_1", 
                anon_1."Name" AS "Name_2"
            FROM 
                (
                    SELECT 
                        "Playlist"."PlaylistId" AS "PlaylistId", 
                        "Playlist"."Name" AS "Name",
                        row_number() OVER (ORDER BY "Playlist"."PlaylistId" ASC) AS row_number 
                    FROM 
                        "Playlist"
                ) AS anon_1 
                LEFT OUTER JOIN 
                "PlaylistTrack" AS "PlaylistTrack_1" ON 
                    anon_1."PlaylistId" = "PlaylistTrack_1"."PlaylistId" 
                LEFT OUTER JOIN 
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
                        "Track1"."UnitPrice" AS "UnitPrice" 
                    FROM 
                        "Track" AS "Track1" 
                    WHERE 
                        "Track1"."TrackId" >= :TrackId_1
                ) AS "Track1" ON 
                    "Track1"."TrackId" = "PlaylistTrack_1"."TrackId" 
                LEFT OUTER JOIN 
                "PlaylistTrack" AS "PlaylistTrack_2" ON 
                    "Track1"."TrackId" = "PlaylistTrack_2"."TrackId" 
                LEFT OUTER JOIN 
                (
                    SELECT 
                        "Playlist1"."PlaylistId" AS "PlaylistId", 
                        "Playlist1"."Name" AS "Name" 
                    FROM 
                        "Playlist" AS "Playlist1" 
                    WHERE 
                        "Playlist1"."PlaylistId" <= :PlaylistId_2
                ) AS "Playlist1" ON 
                    "Playlist1"."PlaylistId" = "PlaylistTrack_2"."PlaylistId" 
            WHERE 
                anon_1.row_number >= :row_number_1 
                AND 
                anon_1.row_number <= :row_number_2
            ORDER BY 
                anon_1.row_number
            """
        ).replace(" ", "").replace("\n", "")
        result = str(query).replace(" ", "").replace("\n", "")
        assert expected_query == result


class TestDrowsyQueryBuilderRowNumSupport(DrowsyDatabaseTests):

    """Query builder tests for dialects supporting row_number."""

    backends = ['sqlite', 'mssql', 'postgres']

    @staticmethod
    def test_root_and_nested_limit_offset(db_session):
        """Test offset and limit in both root and nested collections."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 15}},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=10,
            offset=1
        )
        results = db_session.execute(query).unique().scalars().all()
        assert len(results) == 10
        for album in results:
            assert len(album.tracks) <= 1
            for track in album.tracks:
                # root offset check
                assert album.album_id != 1
                if album.album_id == 2:
                    # subresource offset check
                    assert track.track_id == 16
                assert track.track_id >= 5

    @staticmethod
    def test_simple_subfilter_limit_offset(db_session):
        """Test offset and limit in a subresource."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        results = db_session.execute(query).unique().scalars().all()
        # offset test
        assert results[0].album_id == 1
        assert results[0].tracks[0].track_id == 7
        for album in results:
            assert len(album.tracks) <= 1
            for track in album.tracks:
                assert track.track_id >= 5

    @staticmethod
    def test_subfilter_limit_offset_sorts(db_session):
        """Test subfiltering with sorts works with limit and offset."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
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
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        results = db_session.execute(query).unique().scalars().all()
        assert len(results) == 347
        for album in results:
            # limit test
            assert len(album.tracks) <= 1
            if album.album_id == 1:
                # offset test
                assert album.tracks[0].name == "C.O.D."

    @staticmethod
    def test_non_strict_bad_sublimits(db_session):
        """Test bad sublimits don't cause failure when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Customer)
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CustomerResource(session=db_session),
            subfilters={
                "invoices": SubfilterInfo(
                    offset=1,
                    limit=10000
                )
            },
            embeds=[],
            strict=False
        )
        results = db_session.execute(query).unique().scalars().all()
        assert len(results) == 59
        assert results[0].customer_id == 1
        # offset check
        assert len(results[0].invoices) == 6
        assert results[0].invoices[0].invoice_id == 121

    @staticmethod
    def test_self_ref_composite_id_subquery_with_limit(db_session):
        """Self referential a composite id subquery with a limit"""
        query_builder = ModelResourceQueryBuilder()
        query = select(CompositeNode).filter(CompositeNode.node_id == 1)
        subfilters = {
            "children": SubfilterInfo(
                filters={"node_id": {"$in": [1, 2]}},
                offset=1,
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=CompositeNodeResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        results = db_session.execute(query).unique().scalars().all()
        assert len(results) == 1
        assert results[0].node_id == 1
        assert results[0].children[0].node_id == 2

    @staticmethod
    def test_multilevel_subfilter_limit(db_session):
        """Test subfiltering with sorts works with limit and offset."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=4,
                sorts=[SortInfo(attr="name", direction="ASC")]
            ),
            "tracks.playlists": SubfilterInfo(
                filters={"playlist_id": {"$gte": 6}},
                limit=5,
                sorts=[SortInfo(attr="name", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=3
        )
        results = db_session.execute(query).unique().scalars().all()
        assert len(results) == 3
        for album in results:
            # limit test
            assert len(album.tracks) <= 4
            for track in album.tracks:
                assert track.track_id >= 5
                # limit test
                assert len(track.playlists) <= 5
                for playlist in track.playlists:
                    assert playlist.playlist_id >= 6

    @staticmethod
    def test_many_to_many_subresource_limit(db_session):
        """Many to many relationships with limits loaded properly."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Playlist)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=5,
                sorts=[SortInfo(attr="name", direction="ASC")]
            ),
            "tracks.playlists": SubfilterInfo(
                filters={"playlist_id": {"$lte": 6}},
                limit=4,
                sorts=[SortInfo(attr="name", direction="ASC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=PlaylistResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=3
        )
        results = db_session.execute(query).unique().scalars().all()
        assert len(results) == 3
        for playlist in results:
            assert len(playlist.tracks) <= 5
            for track in playlist.tracks:
                assert track.track_id >= 5
                assert len(track.playlists) <= 4
                for pl in track.playlists:
                    assert pl.playlist_id <= 6

    @staticmethod
    def test_self_ref_one_to_many_limit(db_session):
        """Self referential one to many subquery with a limit"""
        query_builder = ModelResourceQueryBuilder()
        query = select(Employee)
        subfilters = {
            "subordinates": SubfilterInfo(
                filters={"employee_id": {"$nin": [1, 2]}},
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=EmployeeResource(session=db_session),
            subfilters=subfilters,
            embeds=[]
        )
        results = db_session.execute(query).unique().scalars().all()
        assert len(results) == 8
        for manager in results:
            assert len(manager.subordinates) <= 1
            for subordinate in manager.subordinates:
                assert subordinate.employee_id not in [1, 2]

    @staticmethod
    def test_bad_subfilter_ignore_with_limit(db_session):
        """Bad subfilter using a limit gets ignored when not strict."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$bad": 5}},
                limit=1
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            strict=False
        )
        results = db_session.execute(query).unique().scalars().all()
        assert len(results) > 0
        for album in results:
            assert len(album.tracks) <= 1

    @staticmethod
    def test_subresource_sort_by_pk(db_session):
        """Sort by PK on subresource loaded properly."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Album)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}},
                limit=5,
                sorts=[SortInfo(attr="track_id", direction="DESC")]
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=AlbumResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=3
        )
        results = db_session.execute(query).unique().scalars().all()
        assert len(results) == 3
        for album in results:
            assert len(album.tracks) <= 5
            last_track_id = None
            for track in album.tracks:
                assert track.track_id >= 5
                # Note that the actual order isn't guaranteed,
                # just that the ordering impacts which records 
                # get returned
                if track.album_id == 3:
                    assert track.track_id == 5
                elif track.album_id == 1:
                    assert track.track_id in (10, 11, 12, 13, 14)
                assert track.album_id != 2

    @staticmethod
    def test_same_entity_grandchild_load(db_session):
        """Test loading strategy for same entity grand child works."""
        query_builder = ModelResourceQueryBuilder()
        query = select(Playlist)
        subfilters = {
            "tracks": SubfilterInfo(
                filters={"track_id": {"$gte": 5}}
            ),
            "tracks.playlists": SubfilterInfo(
                filters={"playlist_id": {"$lte": 6}}
            )
        }
        query = query_builder.apply_subquery_loads(
            query=query,
            resource=PlaylistResource(session=db_session),
            subfilters=subfilters,
            embeds=[],
            limit=3
        )
        results = db_session.execute(query).unique().scalars().all()
        assert len(results) == 3
        for playlist in results:
            for track in playlist.tracks:
                assert track.track_id >= 5
                for pl in track.playlists:
                    assert pl.playlist_id <= 6
