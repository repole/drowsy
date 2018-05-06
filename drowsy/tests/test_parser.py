"""
    drowsy.tests.test_parser
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Parser tests for Drowsy.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from __future__ import unicode_literals
from drowsy.exc import OffsetLimitParseError, FilterParseError, ParseError
from drowsy.tests.base import DrowsyTests
from drowsy.tests.models import Album
from drowsy.parser import QueryParamParser, ModelQueryParamParser, \
    OffsetLimitInfo, SubfilterInfo, SortInfo
import json


class DrowsyParserTests(DrowsyTests):

    """Test drowsy query param parsing is working as expected."""

    def test_missing_error_message_fail(self):
        """Test that failing with a bad error message is handled."""
        parser = ModelQueryParamParser(query_params={})
        self.assertRaises(
            AssertionError,
            parser.fail,
            key="test"
        )

    def test_sortinfo_bad_attr_fail(self):
        """Test SortInfo fails when given a bad attr."""
        self.assertRaises(
            TypeError,
            SortInfo,
            attr=5,
            direction="ASC"
        )

    def test_sortinfo_bad_direction_fail(self):
        """Test SortInfo fails when given a bad direction."""
        self.assertRaises(
            ValueError,
            SortInfo,
            attr="test",
            direction="ASCdsfa"
        )

    def test_subfilterinfo_valid(self):
        """Test SubfilterInfo works with valid input."""
        sub_info = SubfilterInfo(
            offset=1,
            limit=100,
            sorts=[SortInfo("test", "ASC")],
            filters={}
        )
        self.assertTrue(sub_info.limit == 100)
        self.assertTrue(sub_info.offset == 1)
        self.assertTrue(len(sub_info.filters) == 0)
        self.assertTrue(sub_info.sorts[0].attr == "test")
        self.assertTrue(sub_info.sorts[0].direction == "ASC")

    def test_subfilterinfo_bad_limit_fail(self):
        """Test SubfilterInfo fails when given a bad offset/limit."""
        self.assertRaises(
            TypeError,
            SubfilterInfo,
            offset_limit_info="test"
        )

    def test_subfilterinfo_bad_sorts_fail(self):
        """Test SubfilterInfo fails when given bad sorts."""
        self.assertRaises(
            TypeError,
            SubfilterInfo,
            sorts="test"
        )

    def test_subfilterinfo_bad_filters_fail(self):
        """Test SubfilterInfo fails when given bad filters."""
        self.assertRaises(
            TypeError,
            SubfilterInfo,
            filters="test"
        )

    def test_offsetlimitinfo_bad_offset_fail(self):
        """Test that OffsetLimitInfo fails when given a bad offset."""
        self.assertRaises(
            TypeError,
            OffsetLimitInfo,
            offset="test",
            limit=1
        )

    def test_offsetlimitinfo_bad_limit_fail(self):
        """Test that OffsetLimitInfo fails when given a bad limit."""
        self.assertRaises(
            TypeError,
            OffsetLimitInfo,
            offset=1,
            limit="test"
        )

    def test_parser_context_dict(self):
        """Test parser context uses a dict properly."""
        parser = QueryParamParser(query_params={}, context={"a": "b"})
        self.assertTrue(parser.context.get("a") == "b")

    def test_parser_context_callable(self):
        """Test parser context uses a callable properly."""
        parser = QueryParamParser(query_params={}, context=dict)
        self.assertTrue(isinstance(parser.context, dict))

    def test_parser_context_setter(self):
        """Test parser context uses a callable properly."""
        parser = QueryParamParser(query_params={}, context={})
        parser.context = {"a": "b"}
        self.assertTrue(parser.context.get("a") == "b")

    def test_invalid_complex_subfilters(self):
        """Test that bad complex filters fail properly."""
        parser = ModelQueryParamParser(query_params={
            "tracks._subfilter_": "{"
        })
        self.assertRaisesCode(
            FilterParseError,
            "invalid_complex_filters",
            parser.parse_filters,
            Album)

    def test_parser_embeds(self):
        """Test embed parsing."""
        parser = QueryParamParser(query_params={"embeds": "a,b,c"})
        embeds = parser.parse_embeds()
        self.assertTrue(len(embeds) == 3)
        self.assertTrue(embeds[0] == "a")
        self.assertTrue(embeds[1] == "b")
        self.assertTrue(embeds[2] == "c")

    def test_parser_fields(self):
        """Test fields parsing."""
        parser = QueryParamParser(query_params={"fields": "a,b,c"})
        fields = parser.parse_fields()
        self.assertTrue(len(fields) == 3)
        self.assertTrue(fields[0] == "a")
        self.assertTrue(fields[1] == "b")
        self.assertTrue(fields[2] == "c")

    def test_page_invalid_type(self):
        """Providing a non integer page should fail."""
        query_params = {"page": "test"}
        parser = QueryParamParser(query_params)
        self.assertRaisesCode(
            OffsetLimitParseError,
            "invalid_page_value",
            parser.parse_offset_limit)

    def test_no_page_max_size_fail(self):
        """Not providing a max page size with page > 1 should fail."""
        query_params = {"page": "2"}
        parser = QueryParamParser(query_params)
        self.assertRaises(
            OffsetLimitParseError,
            parser.parse_offset_limit)

    def test_bad_page_num(self):
        """Test that providing a negative page number fails."""
        query_params = {"page": "-1"}
        parser = QueryParamParser(query_params)
        self.assertRaises(
            OffsetLimitParseError,
            parser.parse_offset_limit)

    def test_offset_fail(self):
        """Make sure providing a bad offset query_param fails."""
        query_params = {"offset": "test"}
        parser = QueryParamParser(query_params)
        self.assertRaises(
            OffsetLimitParseError,
            parser.parse_offset_limit
        )

    def test_limit_fail(self):
        """Make sure providing a bad limit query_param is ignored."""
        query_params = {"limit": "test"}
        parser = QueryParamParser(query_params)
        self.assertRaises(
            OffsetLimitParseError,
            parser.parse_offset_limit
        )

    def test_limit_override(self):
        """Ensure providing a page_max_size overrides a high limit."""
        query_params = {"limit": "1000"}
        parser = QueryParamParser(query_params)
        self.assertRaises(
            OffsetLimitParseError,
            parser.parse_offset_limit,
            30
        )

    def test_subfilter_parser(self):
        """Ensure basic subfilter parsing works."""
        query_params = {
            "album.tracks._subquery_": '{"track_id": 5}'
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_subfilters()
        expected_result = {"$and": [{"track_id": 5}]}
        self.assertDictEqual(expected_result, result["album.tracks"].filters)

    def test_subsorts_parser(self):
        """Ensure basic subsorts parsing works."""
        query_params = {
            "album.tracks._sorts_": "track_id,-name"
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_subfilters()
        self.assertTrue(len(result["album.tracks"].sorts) == 2)
        self.assertTrue(result["album.tracks"].sorts[0].attr == "track_id")
        self.assertTrue(result["album.tracks"].sorts[0].direction == "ASC")
        self.assertTrue(result["album.tracks"].sorts[1].attr == "name")
        self.assertTrue(result["album.tracks"].sorts[1].direction == "DESC")

    def test_sublimit_parser(self):
        """Ensure basic sublimit parsing works."""
        query_params = {
            "album.tracks._limit_": 5
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_subfilters()
        self.assertTrue(result["album.tracks"].limit == 5)

    def test_sublimit_parser_bad_value_fail(self):
        """Ensure basic sublimit parsing fails appropriately."""
        query_params = {
            "album.tracks._limit_": "test"
        }
        parser = ModelQueryParamParser(query_params)
        self.assertRaisesCode(
            OffsetLimitParseError,
            "invalid_sublimit_value",
            parser.parse_subfilters)

    def test_sublimit_parser_bad_value_ignore(self):
        """Ensure non strict basic sublimit parsing ignores errors."""
        query_params = {
            "album.tracks._limit_": "test",
            "album.tracks._offset_": 5
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_subfilters(strict=False)
        self.assertTrue(result["album.tracks"].offset == 5)

    def test_suboffset_parser(self):
        """Ensure basic suboffset parsing works."""
        query_params = {
            "album.tracks._offset_": 5
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_subfilters()
        self.assertTrue(result["album.tracks"].offset == 5)

    def test_suboffset_parser_bad_value_fail(self):
        """Ensure basic suboffset parsing fails appropriately."""
        query_params = {
            "album.tracks._offset_": "test"
        }
        parser = ModelQueryParamParser(query_params)
        self.assertRaisesCode(
            OffsetLimitParseError,
            "invalid_suboffset_value",
            parser.parse_subfilters)

    def test_root_complex_filters_parser(self):
        """Ensure basic root complex parsing works."""
        query_params = {
           "query": json.dumps({"title": "Big Ones"})
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_filters(Album)
        self.assertTrue(result["$and"][0]["title"] == "Big Ones")

    def test_invalid_subresource_path_fail(self):
        """Ensure a bad subresource path fails."""
        query_params = {
            "album.tracks._sorts_.failhere": "track_id,-name"
        }
        parser = ModelQueryParamParser(query_params)
        self.assertRaisesCode(
            ParseError,
            "invalid_subresource_path",
            parser.parse_subfilters)

    def test_invalid_subresource_path_ignore(self):
        """Ensure silent failure on subresource path when not strict."""
        query_params = {
            "album.tracks._sorts_.failhere": "track_id,-name"
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_subfilters(strict=False)
        self.assertTrue(len(result) == 0)

    def test_parse_filters_ignore_subresource(self):
        """Ensure filter parsing ignores any subresource paths."""
        query_params = {
            "query": json.dumps(
                {
                    "title": "Big Ones"
                }
            ),
            "tracks._sorts_": "name"
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_filters(Album)
        self.assertTrue(result["$and"][0]["title"] == "Big Ones")

    def test_parse_multiple_complex_filters(self):
        """Ensure multiple complex filters are treated properly."""
        query_params = {
            "query": [
                json.dumps(
                    {
                        "title": "Big Ones"
                    }
                ),
                json.dumps(
                    {
                        "title": "Big Ones"
                    }
                )
            ]
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_filters(Album)
        self.assertTrue(result["$and"][0]["title"] == "Big Ones")
        self.assertTrue(result["$and"][1]["title"] == "Big Ones")

    def test_parse_complex_json_non_dict_fail(self):
        """Ensure non dictionary json complex filters fail."""
        query_params = {
            "query": "[]"
        }
        parser = ModelQueryParamParser(query_params)
        self.assertRaisesCode(
            FilterParseError,
            "invalid_complex_filters",
            parser.parse_filters,
            Album
        )

    def test_parse_filters_convert_key_names(self):
        """Ensure parsing filters works with key name conversion."""
        def convert_key_names(key):
            if key == "titleTest":
                return "title"
            raise AttributeError
        query_params = {
            "titleTest": "Big Ones",
            "badkey": "test"
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_filters(
            Album,
            convert_key_names_func=convert_key_names)
        # Note that this is still titleTest
        # convert_key_names job here is only to be used
        # to verify that an attribute exists in the
        # provided model. Since titleTest is converted
        # to title, and title is an attribute in Album,
        # titleTest is part of the query, unlike badkey.
        self.assertTrue(result["$and"][0]["titleTest"]["$eq"] == "Big Ones")

    def test_parse_complex_subquery(self):
        """Test a complex subquery is handled properly."""
        query_params = {
            "tracks._subquery_.playlists": json.dumps({
                "playlist_id": 5
            })
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_subfilters()
        filters = result["tracks"].filters
        self.assertTrue(
            filters["$and"][0]["playlists"]["playlist_id"] == 5)

    def test_parse_simple_subquery_fail(self):
        """Test a simple subquery fails with invalid input."""
        query_params = {
            "tracks._subquery_": 5
        }
        parser = ModelQueryParamParser(query_params)
        self.assertRaisesCode(
            FilterParseError,
            "invalid_complex_filters",
            parser.parse_subfilters
        )

    def test_parse_simple_subquery(self):
        """Test a simple subquery is handled properly."""
        query_params = {
            "tracks._subquery_.playlists.playlist_id": 5
        }
        parser = ModelQueryParamParser(query_params)
        result = parser.parse_subfilters()
        filters = result["tracks"].filters
        self.assertTrue(
            filters["$and"][0]["playlists.playlist_id"]["$eq"] == 5)
