"""
    drowsy.query_builder
    ~~~~~~~~~~~~~~~~~~~~

    Tools for building SQLAlchemy queries.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
from collections import defaultdict
from drowsy.parser import SortInfo, SubfilterInfo, OffsetLimitInfo
from drowsy.fields import NestedRelated
from drowsy.utils import get_field_by_dump_name
from sqlalchemy import func, and_
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import aliased, contains_eager, joinedload, \
    RelationshipProperty
from sqlalchemy.orm.interfaces import MANYTOMANY, ONETOMANY
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList
from mqlalchemy import apply_mql_filters, InvalidMQLException


class QueryBuilder(object):

    """Utility class for building a SQLAlchemy query."""

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
        :raise ValueError: If a sort not of type
            :class:`~drowsy.parser.SortInfo` is provided.
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
        :raises ValueError: If
        :return:
        :rtype: list of SQLAlchemy partition by statements

        """
        relationship = getattr(parent, relationship_name)
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
            queryable = None
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
            # Figure out whether the primary or secondary join is used
            # on the child side.
            if relationship.prop.backref is None and (
                    relationship.prop.back_populates is not None):
                # is the backref side of the relationship.
                # secondary join is used for child to assoc.
                child_expressions = secondary_expressions
                parent_expressions = primary_expressions
            else:
                # not the backref side/no such side exists
                # primary join used for child to assoc.
                child_expressions = primary_expressions
                parent_expressions = secondary_expressions
            for expression in child_expressions:
                # Find the association table
                # Then figure out the join condition
                left_table = expression.left.table
                right_table = expression.right.table
                child_table = inspect(child).mapper.local_table
                if left_table == child_table:
                    child_side = expression.left
                    assoc_side = expression.right
                    queryable = right_table
                elif right_table == child_table:
                    child_side = expression.right
                    assoc_side = expression.left
                    queryable = left_table
                else:
                    raise ValueError
                child_insp = inspect(inspect(child).class_)
                for column_key in child_insp.columns.keys():
                    if child_insp.columns[column_key].key == child_side.key:
                        child_condition = getattr(child, column_key)
                        joins.append(assoc_side == child_condition)
            # Now get the partition by...
            partition_by = []
            # First, figure out the join conditions
            for expression in parent_expressions:
                if not isinstance(expression, BinaryExpression):
                    # Complex join not supported
                    raise ValueError
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
                else:
                    raise ValueError
                partition_by.append(assoc_side)
            if not joins:
                raise ValueError
            if queryable is None:
                raise ValueError
            if not partition_by:
                raise ValueError
            if len(joins) == 1:
                join = joins[0]
            else:
                join = and_(*joins)
            return partition_by, queryable, join
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
                # find if left or right is the assoc table
                left_table = expression.left.table
                right_table = expression.right.table
                child_table = inspect(child).mapper.local_table
                if left_table == child_table:
                    child_side = expression.left
                elif right_table == child_table:
                    child_side = expression.right
                else:
                    raise ValueError
                child_insp = inspect(inspect(child).class_)
                for column_key in child_insp.columns.keys():
                    if child_insp.columns[column_key].key == child_side.key:
                        partition_by.append(getattr(child, column_key))
                if not partition_by:
                    raise ValueError
            return partition_by, queryable, join
        else:
            return None, None, None

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

    def apply_offset_and_limit(self, query, offset, limit):
        """Applies offset and limit to the query if appropriate.

        :param query: Any desired filters must already have been applied.
        :type query: :class:`~sqlalchemy.orm.query.Query`
        :param offset: Integer used to offset the query result.
        :type offset: int or None
        :param limit: Integer used to limit the number of results returned.
        :type limit: int or None
        :raise ValueError: If a non `None` offset or limit is provided
            that can't be converted to an integer.
        :return: A modified query object with an offset and limit applied.
        :rtype: :class:`~sqlalchemy.orm.query.Query`

        """
        if offset is not None:
            offset = int(offset)
            query = query.offset(offset)
        if limit is not None:
            limit = int(limit)
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

    def apply_subquery_loads(self, query, resource, subfilters, embeds=None,
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
        :param bool strict: If `True`, will raise an exception when bad
            parameters are passed. If `False`, will quietly ignore any
            bad input and treat it as if none was provided.
        :param stack_size_limit: Used to limit the allowable complexity
            of the applied filters.
        :type stack_size_limit: int or None
        :param bool dialect_override: `True` will override any
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
        if embeds is None:
            embeds = []
        dialect = resource.session.bind.name
        supported_dialects = ["mssql", "postgresql",
                              "oracle"]  # , "sqlite" TESTING
        if dialect_override:
            supported_dialects.append(dialect)
        root = {
            "children": [],
            "parent": None,
            "alias": resource.model,
            "limit": None,
            "offset": None,
            "order": None,
            "subquery": None,
            "name": "$root",
            "joined": False
        }
        leaf_nodes = []
        model_count = defaultdict(int)
        root_resource = resource
        for subfilter_key in set().union(subfilters.keys(), embeds):
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
                raise ValueError
            failed = False
            while split_subfilter_keys and not failed:
                failed = False
                split_key = split_subfilter_keys.pop(0)
                field = get_field_by_dump_name(
                    schema=schema,
                    dump_name=split_key)
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
                        if dialect in supported_dialects:
                            default_limit = resource.page_max_size
                        else:
                            default_limit = None
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
                            "whitelist": resource.whitelist
                        }
                        # This takes care of embedding when is_embed
                        new_node["subquery"] = resource.apply_required_filters(
                            query=resource.session.query(new_node["alias"]),
                            alias=new_node["alias"]
                        ).subquery()
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
                        except ValueError:
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
                            if dialect not in supported_dialects and strict:
                                # dialect doesn't support limit/offset
                                # fail accordingly
                                root_resource.fail(
                                    "invalid_subresource_options",
                                    subresource_key=subfilter_key)
                                # if not strict, the below is skipped
                                # default subquery gets used
                            elif dialect in supported_dialects:
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
                                ).subquery()
                            )
                        except InvalidMQLException as exc:
                            if not strict:
                                failed = True
                                continue
                            root_resource.fail(
                                "invalid_subresource_filters",
                                exc=exc,
                                subresource_key=subfilter_key)
                        # If we made it this far, filters were
                        # successfully applied.
                        leaf_nodes.append(last_node)
                    elif not split_subfilter_keys and is_embed:
                        # TODO - New line below, verify
                        leaf_nodes.append(last_node)
                    elif split_subfilter_keys and is_embed:
                        # There's still another part of the
                        # subfilter to account for.
                        # e.g. split_key = "tracks"
                        # split_subfilter_keys = "track_id"
                        next_split_key = split_subfilter_keys[0]
                        next_field = get_field_by_dump_name(
                            schema=schema,
                            dump_name=next_split_key)
                        if not isinstance(next_field, NestedRelated):
                            leaf_nodes.append(last_node)
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
        # build options
        subfilter_info = []
        subfilter_options = []
        for node in leaf_nodes:
            flow = [node]
            while node["parent"] is not None:
                node = node["parent"]
                if node["name"] != "$root":
                    flow.insert(0, node)
            subfilter_info.append(flow)
        for subfilter in subfilter_info:
            options = None
            for node in subfilter:
                if not node["joined"]:
                    query = query.outerjoin(
                        node["subquery"],
                        getattr(node["parent"]["alias"], node["name"]))
                    node["joined"] = True
                if options is None:
                    options = contains_eager(
                        node["name"],
                        alias=node["subquery"])
                else:
                    options = options.contains_eager(
                        node["name"],
                        alias=node["subquery"])
            if options:
                subfilter_options.append(options)
        if subfilter_options:
            query = query.options(*subfilter_options)
        return query
