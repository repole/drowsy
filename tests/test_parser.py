"""
    drowsy.tests.test_parser
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Parser tests for Drowsy.

    :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from pytest import raises
from drowsy.exc import OffsetLimitParseError, FilterParseError, ParseError
from .models import Album
from drowsy.parser import (
    QueryParamParser, ModelQueryParamParser, OffsetLimitInfo, SubfilterInfo,
    SortInfo)
import json


def test_missing_error_message_fail():
    """Test that failing with a bad error message is handled."""
    parser = ModelQueryParamParser(query_params={})
    with raises(AssertionError):
        parser.make_error(key="test")


def test_sortinfo_bad_attr_fail():
    """Test SortInfo fails when given a bad attr."""
    with raises(TypeError):
        SortInfo(attr=5, direction="ASC")


def test_sortinfo_bad_direction_fail():
    """Test SortInfo fails when given a bad direction."""
    with raises(ValueError):
        SortInfo(attr="test", direction="ASCdsfa")


def test_sortinfo_bad_direction_type_fail():
    """Test SortInfo fails when given a bad direction type."""
    with raises(TypeError):
        SortInfo(attr="test", direction=4)


def test_subfilterinfo_valid():
    """Test SubfilterInfo works with valid input."""
    sub_info = SubfilterInfo(
        offset=1,
        limit=100,
        sorts=[SortInfo("test", "ASC")],
        filters={}
    )
    assert sub_info.limit == 100
    assert sub_info.offset == 1
    assert len(sub_info.filters) == 0
    assert sub_info.sorts[0].attr == "test"
    assert sub_info.sorts[0].direction == "ASC"


def test_subfilterinfo_bad_limit_fail():
    """Test SubfilterInfo fails when given a bad offset/limit."""
    with raises(TypeError):
        SubfilterInfo(offset_limit_info="test")


def test_subfilterinfo_bad_sorts_fail():
    """Test SubfilterInfo fails when given bad sorts."""
    with raises(TypeError):
        SubfilterInfo(sorts="test")


def test_subfilterinfo_bad_filters_fail():
    """Test SubfilterInfo fails when given bad filters."""
    with raises(TypeError):
        SubfilterInfo(filters="test")


def test_offsetlimitinfo_bad_offset_fail():
    """Test that OffsetLimitInfo fails when given a bad offset."""
    with raises(ValueError):
        OffsetLimitInfo(offset=-1, limit=1)


def test_offsetlimitinfo_bad_offset_type_fail():
    """Test OffsetLimitInfo fails when given a bad offset type."""
    with raises(TypeError):
        OffsetLimitInfo(offset="test", limit=1)


def test_offsetlimitinfo_bad_limit_fail():
    """Test that OffsetLimitInfo fails when given a bad limit."""
    with raises(ValueError):
        OffsetLimitInfo(offset=1, limit=-1)


def test_offsetlimitinfo_bad_limit_type_fail():
    """Test that OffsetLimitInfo fails when given a bad limit type."""
    with raises(TypeError):
        OffsetLimitInfo(offset=1, limit="test")


def test_parser_context_dict():
    """Test parser context uses a dict properly."""
    parser = QueryParamParser(query_params={}, context={"a": "b"})
    assert parser.context.get("a") == "b"


def test_parser_context_callable():
    """Test parser context uses a callable properly."""
    parser = QueryParamParser(query_params={}, context=dict)
    assert isinstance(parser.context, dict)


def test_parser_context_setter():
    """Test parser context uses a callable properly."""
    parser = QueryParamParser(query_params={}, context={})
    parser.context = {"a": "b"}
    assert parser.context.get("a") == "b"


def test_invalid_complex_subfilters():
    """Test that bad complex filters fail properly."""
    parser = ModelQueryParamParser(query_params={
        "tracks._subfilter_": "{"
    })
    with raises(FilterParseError) as excinfo:
        parser.parse_filters(Album)
    assert excinfo.value.code == "invalid_complex_filters"


def test_parser_embeds():
    """Test embed parsing."""
    parser = QueryParamParser(query_params={"embeds": "a,b,c"})
    embeds = parser.parse_embeds()
    assert len(embeds) == 3
    assert embeds[0] == "a"
    assert embeds[1] == "b"
    assert embeds[2] == "c"


def test_parser_fields():
    """Test fields parsing."""
    parser = QueryParamParser(query_params={"fields": "a,b,c"})
    fields = parser.parse_fields()
    assert len(fields) == 3
    assert fields[0] == "a"
    assert fields[1] == "b"
    assert fields[2] == "c"


def test_parser_page_invalid_type():
    """Providing a non integer page should fail."""
    query_params = {"page": "test"}
    parser = QueryParamParser(query_params)
    with raises(OffsetLimitParseError) as excinfo:
        parser.parse_offset_limit()
    assert excinfo.value.code == "invalid_page_value"


def test_parser_no_page_max_size_fail():
    """Not providing a max page size with page > 1 should fail."""
    query_params = {"page": "2"}
    parser = QueryParamParser(query_params)
    with raises(OffsetLimitParseError) as excinfo:
        parser.parse_offset_limit()
    assert excinfo.value.code == "page_no_max"


def test_parser_bad_page_num():
    """Test that providing a negative page number fails."""
    query_params = {"page": "-1"}
    parser = QueryParamParser(query_params)
    with raises(OffsetLimitParseError) as excinfo:
        parser.parse_offset_limit()
    assert excinfo.value.code == "invalid_page_value"


def test_parser_offset_fail():
    """Make sure providing a bad offset query_param fails."""
    query_params = {"offset": "test"}
    parser = QueryParamParser(query_params)
    with raises(OffsetLimitParseError) as excinfo:
        parser.parse_offset_limit()
    assert excinfo.value.code == "invalid_offset_value"


def test_parser_offset_negative_fail():
    """Make sure providing a negative offset fails."""
    query_params = {"offset": "-1"}
    parser = QueryParamParser(query_params)
    with raises(OffsetLimitParseError) as excinfo:
        parser.parse_offset_limit()
    assert excinfo.value.code == "invalid_offset_value"


def test_parser_limit_fail():
    """Make sure providing a bad limit fails."""
    query_params = {"limit": "test"}
    parser = QueryParamParser(query_params)
    with raises(OffsetLimitParseError) as excinfo:
        parser.parse_offset_limit()
    assert excinfo.value.code == "invalid_limit_value"


def test_parser_limit_negative_fail():
    """Make sure providing a negative limit fails."""
    query_params = {"limit": "-1"}
    parser = QueryParamParser(query_params)
    with raises(OffsetLimitParseError) as excinfo:
        parser.parse_offset_limit()
    assert excinfo.value.code == "invalid_limit_value"


def test_parser_limit_override():
    """Ensure providing a page_max_size overrides a high limit."""
    query_params = {"limit": "1000"}
    parser = QueryParamParser(query_params)
    with raises(OffsetLimitParseError) as excinfo:
        parser.parse_offset_limit(30)
    assert excinfo.value.code == "limit_too_high"


def test_subfilter_parser():
    """Ensure basic subfilter parsing works."""
    query_params = {
        "album.tracks._subquery_": '{"track_id": 5}'
    }
    parser = ModelQueryParamParser(query_params)
    result = parser.parse_subfilters()
    expected_result = {"$and": [{"track_id": 5}]}
    assert expected_result == result["album.tracks"].filters


def test_subsorts_parser():
    """Ensure basic subsorts parsing works."""
    query_params = {
        "album.tracks._sorts_": "track_id,-name"
    }
    parser = ModelQueryParamParser(query_params)
    result = parser.parse_subfilters()
    assert len(result["album.tracks"].sorts) == 2
    assert result["album.tracks"].sorts[0].attr == "track_id"
    assert result["album.tracks"].sorts[0].direction == "ASC"
    assert result["album.tracks"].sorts[1].attr == "name"
    assert result["album.tracks"].sorts[1].direction == "DESC"


def test_sublimit_parser():
    """Ensure basic sublimit parsing works."""
    query_params = {
        "album.tracks._limit_": 5
    }
    parser = ModelQueryParamParser(query_params)
    result = parser.parse_subfilters()
    assert result["album.tracks"].limit == 5


def test_sublimit_parser_bad_value_fail():
    """Ensure basic sublimit parsing fails appropriately."""
    query_params = {
        "album.tracks._limit_": "test"
    }
    parser = ModelQueryParamParser(query_params)
    with raises(OffsetLimitParseError) as excinfo:
        parser.parse_subfilters()
    assert excinfo.value.code == "invalid_sublimit_value"


def test_sublimit_parser_bad_value_ignore():
    """Ensure non strict basic sublimit parsing ignores errors."""
    query_params = {
        "album.tracks._limit_": "test",
        "album.tracks._offset_": 5
    }
    parser = ModelQueryParamParser(query_params)
    result = parser.parse_subfilters(strict=False)
    assert result["album.tracks"].offset == 5


def test_suboffset_parser():
    """Ensure basic suboffset parsing works."""
    query_params = {
        "album.tracks._offset_": 5
    }
    parser = ModelQueryParamParser(query_params)
    result = parser.parse_subfilters()
    assert result["album.tracks"].offset == 5


def test_suboffset_parser_bad_value_fail():
    """Ensure basic suboffset parsing fails appropriately."""
    query_params = {
        "album.tracks._offset_": "test"
    }
    parser = ModelQueryParamParser(query_params)
    with raises(OffsetLimitParseError) as excinfo:
        parser.parse_subfilters()
    assert excinfo.value.code == "invalid_suboffset_value"


def test_root_complex_filters_parser():
    """Ensure basic root complex parsing works."""
    query_params = {
       "query": json.dumps({"title": "Big Ones"})
    }
    parser = ModelQueryParamParser(query_params)
    result = parser.parse_filters(Album)
    assert result["$and"][0]["title"] == "Big Ones"


def test_invalid_subresource_path_fail():
    """Ensure a bad subresource path fails."""
    query_params = {
        "album.tracks._sorts_.failhere": "track_id,-name"
    }
    parser = ModelQueryParamParser(query_params)
    with raises(ParseError) as excinfo:
        parser.parse_subfilters()
    assert excinfo.value.code == "invalid_subresource_path"


def test_invalid_subresource_path_ignore():
    """Ensure silent failure on subresource path when not strict."""
    query_params = {
        "album.tracks._sorts_.failhere": "track_id,-name"
    }
    parser = ModelQueryParamParser(query_params)
    result = parser.parse_subfilters(strict=False)
    assert len(result) == 0


def test_parse_filters_ignore_subresource():
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
    assert result["$and"][0]["title"] == "Big Ones"


def test_parse_multiple_complex_filters():
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
    assert result["$and"][0]["title"] == "Big Ones"
    assert result["$and"][1]["title"] == "Big Ones"


def test_parse_complex_json_non_dict_fail():
    """Ensure non dictionary json complex filters fail."""
    query_params = {
        "query": "[]"
    }
    parser = ModelQueryParamParser(query_params)
    with raises(FilterParseError) as excinfo:
        parser.parse_filters(Album)
    assert excinfo.value.code == "invalid_complex_filters"


def test_parse_filters_convert_key_names():
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
    assert result["$and"][0]["titleTest"]["$eq"] == "Big Ones"


def test_parse_complex_subquery():
    """Test a complex subquery is handled properly."""
    query_params = {
        "tracks._subquery_.playlists": json.dumps({
            "playlist_id": 5
        })
    }
    parser = ModelQueryParamParser(query_params)
    result = parser.parse_subfilters()
    filters = result["tracks"].filters
    assert filters["$and"][0]["playlists"]["playlist_id"] == 5


def test_parse_simple_subquery_fail():
    """Test a simple subquery fails with invalid input."""
    query_params = {
        "tracks._subquery_": 5
    }
    parser = ModelQueryParamParser(query_params)
    with raises(FilterParseError) as excinfo:
        parser.parse_subfilters()
    assert excinfo.value.code == "invalid_complex_filters"


def test_parse_simple_subquery():
    """Test a simple subquery is handled properly."""
    query_params = {
        "tracks._subquery_.playlists.playlist_id": 5
    }
    parser = ModelQueryParamParser(query_params)
    result = parser.parse_subfilters()
    filters = result["tracks"].filters
    assert filters["$and"][0]["playlists.playlist_id"]["$eq"] == 5
