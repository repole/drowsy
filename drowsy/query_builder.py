"""
    drowsy.query_builder
    ~~~~~~~~~~~~~~~~~~~~

    Tools for building SQLAlchemy queries.

    :copyright: (c) 2016-2020 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from collections import defaultdict
from drowsy.fields import NestedRelated
from drowsy.log import Loggable
from drowsy.parser import SortInfo, SubfilterInfo
from drowsy.utils import get_field_by_data_key
from sqlalchemy import and_, func, or_
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import aliased, contains_eager
from sqlalchemy.orm.interfaces import MANYTOMANY, MANYTOONE, ONETOMANY
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
from mqlalchemy import apply_mql_filters, InvalidMQLException


class QueryBuilder(Loggable):

    """Utility class for building a SQLAlchemy query."""

    def row_number_supported(self, dialect, dialect_override=False):
        supported_dialects = ["mssql", "postgresql",
                              "oracle"]  # , "sqlite" TESTING
        return dialect_override or dialect in supported_dialects

    def _get_order_bys(self, record_class, sorts, convert_key_names_func):
        """Helper method for applying sorts.

        :param record_class: The type of model being sorted.
        :type record_class: :class:`~sqlalchemy.orm.util.AliasedClass`
            or SQLAlchemy model class.
        :param sorts: A list of sorts.
        :type sorts: list of :class:`~drowsy.parser.SortInfo`
        :param convert_key_names_func: Used to convert key names.
            See :func:`~drowsy.parser.parse_filters`.
        :type convert_key_names_func: callable
        :raise AttributeError: If a sort with an invalid attr name is
            provided.
        :return: A list of order_by parameters to be applied to a query.
        :rtype: list

        """
        result = list()
        for sort in sorts:
            attr_name = convert_key_names_func(sort.attr)
            if attr_name is not None and hasattr(record_class, attr_name):
                if sort.direction == "ASC":
                    result.append(getattr(record_class, attr_name).asc())
                else:
                    result.append(getattr(record_class, attr_name).desc())
            else:
                raise AttributeError("Invalid attribute.")
        return result

    def apply_sorts(self, query, sorts, convert_key_names_func=str):
        """Apply sorts to a provided query.

        :param query: A SQLAlchemy query; filters must already have been
            applied.
        :type query: :class:`~sqlalchemy.orm.query.Query`
        :param sorts: A list of sorts to apply to this query.
        :type sorts: list of :class:`~drowsy.parser.SortInfo`
        :param convert_key_names_func: Used to convert key names.
            See :func:`~drowsy.parser.parse_filters`.
        :type convert_key_names_func: callable
        :raise AttributeError: If a sort with an invalid attr name is
            provided.
        :raise ValueError: If a sort not of type
            :class:`~drowsy.parser.SortInfo` is provided, or if
            `query` isn't of a single model type.
        :return: A modified version of the provided query object.
        :rtype: :class:`~sqlalchemy.orm.query.Query`

        """
        if len(query.column_descriptions) == 1:
            record_class = query.column_descriptions[0]["expr"]
            order_bys = self._get_order_bys(
                record_class, sorts, convert_key_names_func)
            for order_by in order_bys:
                query = query.order_by(order_by)
        else:
            raise ValueError
        return query

    def apply_offset(self, query, offset):
        """Applies offset and limit to the query if appropriate.

        :param query: Any desired filters must already have been applied.
        :type query: :class:`~sqlalchemy.orm.query.Query`
        :param offset: Integer used to offset the query result.
        :type offset: int or None
        :raise ValueError: If a non ``None`` offset is provided
            that is converted to a negative integer.
        :raise TypeError: If a non ``None`` offset is provided
            of a non integer, or integer convertible, type.
        :return: A modified query object with an offset applied.
        :rtype: :class:`~sqlalchemy.orm.query.Query`

        """
        if offset is not None:
            offset = int(offset)
            if offset < 0:
                raise ValueError("offset can not be a negative integer.")
            query = query.offset(offset)
        return query

    def apply_limit(self, query, limit):
        """Applies limit to the query if appropriate.

        :param query: Any desired filters must already have been applied.
        :type query: :class:`~sqlalchemy.orm.query.Query`
        :param limit: Integer used to limit the number of results returned.
        :type limit: int or None
        :raise ValueError: If a non ``None`` limit is provided
            that is converted to a negative integer.
        :raise TypeError: If a non ``None`` offset is provided
            of a non integer, or integer convertible, type.
        :return: A modified query object with an limit applied.
        :rtype: :class:`~sqlalchemy.orm.query.Query`

        """
        if limit is not None:
            limit = int(limit)
            if limit < 0:
                raise ValueError("limit can not be a negative integer.")
            query = query.limit(limit)
        return query

    def apply_filters(self, query, model_class, filters, whitelist=None,
                      stack_size_limit=100, convert_key_names_func=str,
                      gettext=None):
        """Apply filters to a query using MQLAlchemy.

        :param query: A SQLAlchemy session or query.
        :param model_class: The model having filters applied to it.
        :param filters: The MQLAlchemy style filters to apply.
        :type filters: dict or None
        :param whitelist: Used to determine what attributes are
            acceptable to be queried.
        :type whitelist: callable, list, set, or None
        :param stack_size_limit: Used to limit the allowable complexity
            of the applied filters.
        :type stack_size_limit: int or None
        :param callable convert_key_names_func: Used to convert the
            attr names from user input (perhaps in camelCase) to the
            model format (likely in under_score format).
        :param gettext: Used to translate any errors.
        :type gettext: callable or None
        :raise InvalidMQLException: Raised in cases where invalid
            filters were supplied.
        :return: The query with filters applied.

        """
        return apply_mql_filters(
            query,
            model_class,
            filters=filters,
            whitelist=whitelist,
            stack_size_limit=stack_size_limit,
            convert_key_names_func=convert_key_names_func,
            gettext=gettext
        )


class ModelResourceQueryBuilder(QueryBuilder):

    """Class for building a SQLAlchemy query by using resources."""

    def build(self, query, resource, filters, subfilters, embeds=None,
              offset=None, limit=None, sorts=None, strict=True,
              stack_size_limit=100, dialect_override=False):
        """Apply joins, load options, and subfilters to a query.

        NOTE: This is heavily dependent on ModelResource, which is
        more tightly coupled than ideally it'd be. Should figure out
        how to better separate these concerns.

        :param query: A SQLAlchemy query.
        :param resource: Base resource containing the sub resources
            that are to be filtered.
        :type resource: :class:`~drowsy.resource.BaseModelResource`
        :param subfilters: Dictionary of filters, with the
            subresource dot separated name as the key.
        :type subfilters: dict or None
        :param embeds: List of subresources and fields to embed.
        :type embeds: list or None
        :param bool strict: If ``True``, will raise an exception when
            bad parameters are passed. If ``False``, will quietly ignore
            any bad input and treat it as if none was provided.
        :param stack_size_limit: Used to limit the allowable complexity
            of the applied filters.
        :type stack_size_limit: int or None
        :param bool dialect_override: ``True`` will override any
            SQL dialect limitations. Mainly used for testing.
        :return: query with joins, load options, and subresource
            filters applied as appropriate.
        :raise BadRequestError: Uses the provided resource to raise
            an error when subfilters or embeds are unable to be
            successfully applied.
        :raise ValueError: Due to programmer error. Generally
            Only raised if one of the above parameters is
            of the wrong type.

        """
        # apply filters
        # TODO - better planning for new MQLAlchemy
        try:
            query = self.apply_filters(
                query,
                resource.model,
                filters=filters,
                whitelist=resource.whitelist,
                stack_size_limit=stack_size_limit,
                convert_key_names_func=resource.convert_key_name,
                gettext=resource.context.get("gettext", None))
        except InvalidMQLException as exc:
            if strict:
                # TODO - this could be a whitelist permission issue
                # Currently will raise a BadRequest error...
                resource.fail("invalid_filters", exc=exc)
        query = resource.apply_required_filters(query)
        if subfilters or embeds:
            # more complex process.
            # don't apply offset/limit/sorts here
            # will need to be taken care of by apply_subquery_loads
            query = self.apply_subquery_loads(
                query=query,
                resource=resource,
                subfilters=subfilters,
                embeds=embeds,
                offset=offset,
                limit=limit,
                sorts=sorts,
                strict=strict,
                dialect_override=dialect_override
            )
        else:
            # simple query, apply offset/limit/sorts now
            if sorts:
                for sort in sorts:
                    if not isinstance(sort, SortInfo):
                        raise TypeError("Each sort must be of type SortInfo.")
                    try:
                        query = self.apply_sorts(
                            query, [sort], resource.convert_key_name)
                    except AttributeError:
                        if strict:
                            resource.fail("invalid_sort_field", field=sort.attr)
            try:
                query = self.apply_offset(query, offset)
            except ValueError:
                if strict:
                    resource.fail("invalid_offset_value", offset=offset)
            try:
                query = self.apply_limit(query, limit)
            except ValueError:
                if strict:
                    resource.fail("invalid_limit_value", limit=limit)
        return query

    def _get_partition_by_info(self, child, parent, relationship_name):
        """Get the partition_by needed for row_number in a subquery.

        Also returns the queryable and join condition to use for a
        MANYTOMANY relationship using an association table.

        :param child: The child entity being subqueried.
        :type child: :class:`~sqlalchemy.orm.util.AliasedClass`
        :param parent: The parent of the child entity.
        :type parent: :class:`~sqlalchemy.orm.util.AliasedClass` or
            SQLAlchemy model class.
        :param str relationship_name: Field name of the relationship.
        :raises ValueError: If the ``child``, ``parent``, and
            ``relationship_name`` can not be used to produce
            a valid result.
        :return: The partition_by, queryable, and join to use
            for a subquery join and row_number to limit
            subquery results.
        :rtype: tuple

        """
        relationship = getattr(parent, relationship_name)
        partition_by, queryable, join = (None, None, None)
        if relationship.prop.direction == MANYTOMANY:
            # For relationship Node.children:
            # Given assoc table to child join:
            # t_NodeToNode.ChildNodeId = Node.NodeId and
            # t_NodeToNode.ChildCompositeId = Node.CompositeId
            # and parent to assoc table join:
            # t_NodeToNode.NodeId = Node.NodeId and
            # t_NodeToNode.CompositeId = Node.CompositeId
            # We want to extract:
            # queryable: t_NodeToNode
            # join: child.node_id == t_NodeToNode.ChildNodeId and
            #       child.composite_id == t_NodeToNode.ChildCompositeId
            # partition_by: t_NodeToNode.NodeId,
            #               t_NodeToNode.CompositeId
            # This ultimately allows us to use row_number to limit
            # a subresource.
            primary_expressions = []
            secondary_expressions = []
            joins = []
            # Break the primaryjoin and secondaryjoin down
            # into lists of expressions.
            if isinstance(relationship.prop.primaryjoin, BinaryExpression):
                primary_expressions.append(relationship.prop.primaryjoin)
            elif isinstance(relationship.prop.primaryjoin, BooleanClauseList):
                primary_expressions = relationship.prop.primaryjoin.clauses
            if isinstance(relationship.prop.secondaryjoin, BinaryExpression):
                secondary_expressions.append(relationship.prop.secondaryjoin)
            elif isinstance(relationship.prop.secondaryjoin, BooleanClauseList):
                secondary_expressions = relationship.prop.secondaryjoin.clauses
            # default until proven otherwise:
            parent_expressions = secondary_expressions
            for expressions in (primary_expressions, secondary_expressions):
                for expression in expressions:
                    # Find the association table
                    # Then figure out the join condition
                    left_table = expression.left.table
                    right_table = expression.right.table
                    child_table = inspect(child).mapper.local_table
                    if left_table == child_table:
                        child_side = expression.left
                        assoc_side = expression.right
                        queryable = right_table
                        child_expressions = expressions
                    elif right_table == child_table:
                        child_side = expression.right
                        assoc_side = expression.left
                        queryable = left_table
                        child_expressions = expressions
                    else:
                        parent_expressions = expressions
                        continue
                    if child_expressions == primary_expressions:
                        parent_expressions = secondary_expressions
                    else:
                        parent_expressions = primary_expressions
                    child_insp = inspect(inspect(child).class_)
                    for column_key in child_insp.columns.keys():
                        if child_insp.columns[column_key].key == child_side.key:
                            child_condition = getattr(child, column_key)
                            joins.append(assoc_side == child_condition)
            # Now get the partition by...
            partition_by = []
            # First, figure out the join conditions
            for expression in parent_expressions:
                assoc_side = None
                if isinstance(expression, BinaryExpression):
                    # find if left or right is the assoc table
                    left_table = expression.left.table
                    right_table = expression.right.table
                    parent_table = inspect(parent).mapper.local_table
                    if left_table == parent_table:
                        # parent_side = expression.left
                        assoc_side = expression.right
                    elif right_table == parent_table:
                        # parent_side = expression.right
                        assoc_side = expression.left
                if assoc_side is None:
                    # Either no assoc_side was found, or
                    # this wasn't a BinaryExpression
                    raise ValueError  # pragma: no cover
                partition_by.append(assoc_side)
            if not joins or queryable is None or not partition_by:
                # To reach this, one of the following conditions
                # must be met:
                #
                # 1. partition_by is empty because parent_expressions
                #    was empty
                #
                # 2. queryable is None because child_expressions was
                #    empty.
                #
                # 3. joins is None because something unpredictable
                #    happened with the child_expressions.
                raise ValueError  # pragma: no cover
            if len(joins) == 1:
                join = joins[0]
            else:
                join = and_(*joins)
        elif relationship.prop.direction == ONETOMANY:
            # For relationship Album.tracks:
            # Given primary (assoc table to child):
            # Album.AlbumId = Track.AlbumId
            # We want to extract:
            # queryable: None
            # join: None
            # partition_by: track.album_id,
            # This ultimately allows us to use row_number to limit
            # a subresource.
            primary_expressions = []
            partition_by = []
            join = None
            queryable = None
            # First, figure out the join conditions
            if isinstance(relationship.prop.primaryjoin, BinaryExpression):
                primary_expressions.append(relationship.prop.primaryjoin)
            elif isinstance(relationship.prop.primaryjoin, BooleanClauseList):
                primary_expressions = relationship.prop.primaryjoin.clauses
            for expression in primary_expressions:
                # find if left or right is the parent side
                remote_side = relationship.prop.remote_side
                left_table = expression.left.table
                right_table = expression.right.table
                child_table = inspect(child).mapper.local_table
                if left_table == child_table and right_table == child_table:
                    if expression.left in remote_side:
                        child_side = expression.left
                    else:
                        child_side = expression.right
                elif left_table == child_table:
                    child_side = expression.left
                elif right_table == child_table:
                    child_side = expression.right
                else:
                    # Shouldn't ever get here...
                    raise ValueError  # pragma: no cover
                child_insp = inspect(inspect(child).class_)
                for column_key in child_insp.columns.keys():
                    if child_insp.columns[column_key].key == child_side.key:
                        partition_by.append(getattr(child, column_key))
                if not partition_by:
                    # Also shouldn't ever get here...
                    raise ValueError  # pragma: no cover
        return partition_by, queryable, join

    def _initiate_subquery(self, query, resource, offset, limit, sorts,
                           supported, strict=True):
        """Handles query limit/offset/sorts for different dialects.

        To apply a limit or offset to a query that intends to load
        nested results, we must either use row_number, or a multi query
        process to first grab results matching the parent table,
        and then a separate query to join to those results.

        :param query:
        :param resource:
        :param offset:
        :param limit:
        :param sorts:
        :return:

        """
        record_class = resource.model
        id_keys = None
        if sorts:
            order_bys = []
            for sort in sorts:
                try:
                    order_by = self._get_order_bys(
                        record_class, [sort], resource.convert_key_name)
                    order_bys.append(order_by)
                except AttributeError:
                    resource.fail()
        else:
            order_bys = []
            schema = resource.make_schema()
            id_keys = schema.id_keys
            for attr_name in id_keys:
                order_bys.append(
                    getattr(
                        record_class,
                        attr_name).asc()
                )
        if limit is not None and limit < 0:
            if strict:
                resource.fail("invalid_limit_value", limit=limit)
            limit = None
        if offset is not None and offset < 0:
            if strict:
                resource.fail("invalid_offset_value", offset=offset)
            limit = None
        if limit or offset:
            if supported:
                # Use row_number to figure out which rows to pull
                row_number = func.row_number().over(
                    order_by=order_bys
                ).label("row_number")
                query = query.add_column(row_number)
                # limit and offset handling
                start = 1
                if offset is not None:
                    start = offset + 1
                end = None
                if limit is not None:
                    end = start + limit - 1
                query = query.from_self()
                if start:
                    query = query.filter(row_number >= start)
                if end:
                    query = query.filter(row_number <= end)
                order_bys = [row_number]
            else:
                # Unable to use row_number, so unfortunately we have to
                # run an actual query with limit/offset/order applied,
                # and use those results to build our new query.
                # Super inefficient.
                temp_query = query
                for order_by in order_bys:
                    temp_query = temp_query.order_by(order_by)
                if limit:
                    temp_query = self.apply_limit(temp_query, limit)
                if offset:
                    temp_query = self.apply_offset(temp_query, offset)
                results = temp_query.all()
                if not id_keys:
                    schema = resource.make_schema()
                    id_keys = schema.id_keys
                if len(id_keys) > 1:
                    filters = []
                    for result in results:
                        conditions = []
                        for id_key in id_keys:
                            conditions.append(
                                getattr(record_class, id_key) ==
                                getattr(result, id_key)
                            )
                        filters.append(
                            and_(*conditions)
                        )
                    if filters:
                        query = query.filter(or_(*filters))
                else:
                    # in condition
                    id_key = id_keys[0]
                    values = [getattr(r, id_keys[0]) for r in results]
                    if values:
                        query = query.filter(
                            getattr(record_class, id_key).in_(values))
                query = query.from_self()
        for order_by in order_bys:
            query = query.order_by(order_by)
        return query

    def apply_subquery_loads(self, query, resource, subfilters, embeds=None,
                             offset=None, limit=None, sorts=None,
                             strict=True, stack_size_limit=100,
                             dialect_override=False):
        """Apply joins, load options, and subfilters to a query.

        NOTE: This is heavily dependent on ModelResource, which isn't
        a great indication of good design. Should figure out how to
        better separate these concerns.

        :param query: A SQLAlchemy query.
        :param resource: Base resource containing the sub resources
            that are to be filtered.
        :type resource: :class:`~drowsy.resource.BaseModelResource`
        :param subfilters: Dictionary of filters, with the
            subresource dot separated name as the key.
        :type subfilters: dict or None
        :param embeds: List of subresources and fields to embed.
        :type embeds: list or None
        :param bool strict: If ``True``, will raise an exception when
            bad parameters are passed. If ``False``, will quietly ignore
            any bad input and treat it as if none was provided.
        :param stack_size_limit: Used to limit the allowable complexity
            of the applied filters.
        :type stack_size_limit: int or None
        :param bool dialect_override: ``True`` will override any
            SQL dialect limitations. Mainly used for testing.
        :return: query with joins, load options, and subresource
            filters applied as appropriate.
        :raise BadRequestError: Uses the provided resource to raise
            an error when subfilters or embeds are unable to be
            successfully applied.
        :raise ValueError: Due to programmer error. Generally
            Only raised if one of the above parameters is
            of the wrong type.

        """
        embeds = embeds or []
        subfilters = subfilters or {}
        dialect_supported = self.row_number_supported(
            dialect=resource.session.bind.name,
            dialect_override=dialect_override)
        query = self._initiate_subquery(
            query, resource, offset, limit, sorts, dialect_supported, strict)
        root = {
            "children": [],
            "parent": None,
            "alias": resource.model,
            "limit": None,
            "offset": None,
            "order": None,
            "subquery": None,
            "name": "$root",
            "joined": False,
            "relationship_direction": None
        }
        model_count = defaultdict(int)
        root_resource = resource
        embeds = [e for e in embeds if e not in subfilters.keys()]
        subfilter_keys = embeds + list(subfilters.keys())
        for subfilter_key in subfilter_keys:
            resource = root_resource
            schema = resource.make_schema()
            split_subfilter_keys = subfilter_key.split(".")
            last_node = root
            subfilter_info = subfilters.get(subfilter_key)
            is_embed = subfilter_key not in subfilters.keys()
            if is_embed:
                user_supplied_offset = None
                user_supplied_limit = None
                user_supplied_filters = None
                user_supplied_sorts = None
            elif isinstance(subfilter_info, SubfilterInfo):
                user_supplied_offset = subfilter_info.offset
                user_supplied_limit = subfilter_info.limit
                user_supplied_filters = subfilter_info.filters
                user_supplied_sorts = subfilter_info.sorts
            else:
                raise ValueError(
                    "Each subfilter in subfilters must be a SubfilterInfo.")
            failed = False
            while split_subfilter_keys and not failed:
                failed = False
                split_key = split_subfilter_keys.pop(0)
                field = get_field_by_data_key(
                    schema=schema,
                    data_key=split_key)
                if isinstance(field, NestedRelated):
                    # TODO - Should this be field.name?
                    resource = resource.make_subresource(name=split_key)
                    schema = resource.make_schema()
                    for node in last_node["children"]:
                        if node["name"] == field.name:
                            # node already exists in last_node children
                            last_node = node
                            # no need to update it, skip the below else
                            break
                    else:
                        # Need to add this node to last_node children
                        resource_model = schema.opts.model
                        model_count[resource_model] += 1
                        # TODO - embedded_page_max_size for resources too?
                        if dialect_supported:
                            default_limit = resource.page_max_size
                        else:
                            default_limit = None
                        relationship = getattr(last_node["alias"], field.name)
                        relationship_direction = relationship.prop.direction
                        new_node = {
                            "parent": last_node,
                            "name": field.name,
                            "alias": aliased(
                                resource_model,
                                name=(
                                    resource_model.__name__ +
                                    str(model_count[resource_model])
                                )
                            ),
                            "subquery": None,
                            "limit": default_limit,
                            "limit_source": "default",
                            "offset": user_supplied_offset,
                            "sorts": user_supplied_sorts,
                            "children": [],
                            "joined": False,
                            "convert_key_name": resource.convert_key_name,
                            "whitelist": resource.whitelist,
                            "relationship_direction": relationship_direction
                        }
                        # This takes care of embedding when is_embed
                        new_node["subquery"] = resource.apply_required_filters(
                            query=resource.session.query(new_node["alias"]),
                            alias=new_node["alias"]
                        ).subquery(inspect(new_node["alias"]).name)
                        if default_limit is not None and (
                                user_supplied_limit is not None
                                and
                                user_supplied_limit > default_limit):
                            if strict:
                                root_resource.fail(
                                    "invalid_subresource_limit",
                                    supplied_limit=user_supplied_limit,
                                    max_limit=resource.page_max_size,
                                    subresource_key=subfilter_key)
                            user_supplied_limit = default_limit
                        elif user_supplied_limit is not None:
                            new_node["limit"] = user_supplied_limit
                            new_node["limit_source"] = "user"
                        last_node["children"].append(new_node)
                        last_node = new_node
                    if not split_subfilter_keys and not is_embed:
                        # Default subquery likely to be overridden below
                        # This will get used in situations where
                        # no limit or offset is provided, since
                        # row_number won't be needed for pagination.
                        subquery = resource.session.query(last_node["alias"])
                        subquery = resource.apply_required_filters(
                            subquery,
                            alias=last_node["alias"])
                        # Sort should only be provided with offset/limit
                        if strict and last_node["sorts"] is not None and (
                                last_node["offset"] is None and
                                last_node["limit"] is None):
                            root_resource.fail(
                                "invalid_subresource_sorts",
                                subresource_key=subfilter_key)
                        # Start figuring out if we need row_number
                        queryable = None
                        partition_by = None
                        join_condition = None
                        try:
                            partition_by, queryable, join_condition = (
                                self._get_partition_by_info(
                                    last_node["alias"],
                                    last_node["parent"]["alias"],
                                    last_node["name"]
                                )
                            )
                        except ValueError:  # pragma: no cover
                            # Currently have no way to test this.
                            # Open to suggestions...
                            if not strict:
                                failed = True
                                continue
                            root_resource.fail(
                                "invalid_subresource",
                                subresource_key=subfilter_key
                            )
                        # Check the status of the above partition_by
                        if partition_by is None and (
                                last_node["limit"] is not None or
                                last_node["offset"] is not None):
                            # This is a MANYTOONE and user supplied
                            # limit or offset. Fail if strict.
                            if strict:
                                root_resource.fail(
                                    "invalid_subresource_options",
                                    subresource_key=subfilter_key
                                )
                            # else will continue without any row_number
                        # Valid partition by generated,
                        # time to use row_number
                        if partition_by is not None and (
                                last_node["limit"] is not None or
                                # 1 is not None or  # testing
                                last_node["offset"] is not None):
                            if not dialect_supported and strict:
                                # dialect doesn't support limit/offset
                                # fail accordingly
                                root_resource.fail(
                                    "invalid_subresource_options",
                                    subresource_key=subfilter_key)
                                # if not strict, the below is skipped
                                # default subquery gets used
                            elif dialect_supported:
                                # NOTE - We're building up to using
                                # row_number for limiting/offsetting
                                # the subresource.
                                # Order by to be used in row_number
                                if last_node["sorts"]:
                                    # Use sorts from user if provided
                                    order_by = self._get_order_bys(
                                        last_node["alias"],
                                        last_node["sorts"],
                                        resource.convert_key_name
                                    )
                                else:
                                    # Otherwise use primary key(s)/schema ids
                                    order_by = []
                                    attr_names = schema.id_keys
                                    for attr_name in attr_names:
                                        order_by.append(
                                            getattr(
                                                last_node["alias"],
                                                attr_name).asc()
                                        )
                                q1 = resource.session.query(
                                    last_node["alias"],
                                    func.row_number().over(
                                        partition_by=partition_by,
                                        order_by=order_by
                                    ).label("row_number")
                                )
                                if queryable is not None:
                                    q1 = q1.join(
                                        queryable,
                                        join_condition
                                    )
                                q1 = q1.subquery("q1")
                                # limit and offset handling
                                start = 1
                                if last_node["offset"] is not None:
                                    start = last_node["offset"] + 1
                                end = None
                                if last_node["limit"] is not None:
                                    end = start + last_node["limit"] - 1
                                subquery = resource.session.query(q1).filter(
                                     q1.c.row_number >= start)
                                if end is not None:
                                    subquery = subquery.filter(
                                        q1.c.row_number <= end
                                    )
                        try:
                            subquery = resource.apply_required_filters(
                                subquery, alias=last_node["alias"])
                            last_node["subquery"] = (
                                self.apply_filters(
                                    query=subquery,
                                    model_class=last_node["alias"],
                                    whitelist=resource.whitelist,
                                    filters=user_supplied_filters,
                                    convert_key_names_func=(
                                        resource.convert_key_name),
                                    stack_size_limit=stack_size_limit
                                ).subquery(inspect(last_node["alias"]).name)
                            )
                        except InvalidMQLException as exc:
                            if not strict:
                                failed = True
                                continue
                            root_resource.fail(
                                "invalid_subresource_filters",
                                exc=exc,
                                subresource_key=subfilter_key)
                else:
                    if is_embed:
                        if not split_subfilter_keys:
                            # this is an embed ending in an attribute
                            # we're fine to continue
                            continue
                        else:
                            if not strict:
                                failed = True
                                continue
                            # strict mode
                            # invalid embed, fail accordingly.
                            root_resource.fail(
                                "invalid_embed",
                                embed=subfilter_key
                            )
                    else:
                        if not strict:
                            failed = True
                            continue
                        # subresource isn't valid, fail
                        root_resource.fail(
                            "invalid_subresource",
                            subresource_key=subfilter_key)
        # build options and joins
        subfilter_options = []
        nodes = list()
        node_queue = [root]
        while node_queue:
            node = node_queue.pop(0)
            nodes.append(node)
            for child in node["children"]:
                node_queue.append(child)
        for node in nodes:
            if node["name"] == "$root":
                continue
            relationship = getattr(inspect(node["parent"]["alias"]).class_,
                                   node["name"])
            left = node["parent"]["subquery"]
            if left is None:
                left = node["parent"]["alias"]
            join_info = relationship.prop._create_joins(
                source_selectable=inspect(left).selectable,
                dest_selectable=inspect(node["subquery"]).selectable,
                source_polymorphic=True,
                dest_polymorphic=True,
                of_type_mapper=inspect(node["alias"]).mapper)
            primaryjoin = join_info[0]
            secondaryjoin = join_info[1]
            secondary = join_info[4]
            if secondary is not None:
                query = query.outerjoin(secondary, primaryjoin)
                query = query.outerjoin(node["subquery"], secondaryjoin)
            else:
                query = query.outerjoin(node["subquery"], primaryjoin)
            if node["parent"] and node["parent"].get("option", None):
                node["option"] = node["parent"]["option"].contains_eager(
                    node["name"],
                    alias=node["subquery"])
            else:
                node["option"] = contains_eager(
                    node["name"],
                    alias=node["subquery"])
            if not node["children"]:
                subfilter_options.append(node["option"])
        if subfilter_options:
            query = query.options(*subfilter_options)
        return query
