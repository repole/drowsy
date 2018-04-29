"""
    drowsy.router
    ~~~~~~~~~~~~~

    Tools for automatically routing API url paths to resources.

    Work in progress, should not be used as anything other than
    a proof of concept at this point.

    :copyright: (c) 2016-2018 by Nicholas Repole and contributors.
                See AUTHORS for more details.
    :license: MIT - See LICENSE for more details.
"""
import inflection
from marshmallow.fields import MISSING_ERROR_MESSAGE, Field, Nested
from mqlalchemy import convert_to_alchemy_type
from drowsy.parser import ModelQueryParamParser
from drowsy.exc import (
    BadRequestError, OffsetLimitParseError, FilterParseError,
    ResourceNotFoundError, UnprocessableEntityError, MethodNotAllowedError)
import drowsy.resource_class_registry as class_registry
from drowsy.utils import get_error_message
from drowsy.resource import BaseModelResource
from marshmallow_sqlalchemy.schema import ModelSchema


class ResourceRouterABC(object):

    """Abstract base class for a resource based automatic router."""

    default_error_messages = {
        "resource_not_found": ("No resource matching the provided "
                               "identity could be found."),
        "method_not_allowed": ("The method (%(method)s) used to make this "
                               "request is not allowed for this path."),
        # errors from offset/limit parser
        "invalid_limit_type": ("The limit provided (%(limit)s) can not be "
                               "converted to an integer."),
        "limit_too_high": ("The limit provided (%(limit)d) is greater than "
                           "the max page size allowed (%(max_page_size)d)."),
        "invalid_page_type": ("The page value provided (%(page)s) can not be "
                              "converted to an integer."),
        "page_no_max": "Page greater than 1 provided without a page max size.",
        "page_negative": "Page number can not be less than 1.",
        "invalid_offset_type": ("The offset provided (%(offset)s) can not be "
                                "converted to an integer."),
        "invalid_complex_filters": ("The complex filters query value must be "
                                    "set to a valid json dict.")
    }

    def __init__(self, resource, error_messages=None):
        """Sets up router error messages and translations.

        :param resource: A resource instance.
        :type resource: :class:`~drowsy.resource.Resource`
        :param error_messages: Optional dictionary of error messages,
            useful if you want to override the default errors.
        :type error_messages: dict or None

        """
        self.resource = resource
        # Set up error messages
        messages = {}
        for cls in reversed(self.__class__.__mro__):
            messages.update(getattr(cls, 'default_error_messages', {}))
        messages.update(error_messages or {})
        self.error_messages = messages

    @property
    def context(self):
        """Return the context used for this request."""
        return self.resource.context

    def fail(self, key, **kwargs):
        """Raises an exception based on the ``key`` provided.

        :param str key: Failure type, used to choose an error message.
        :param kwargs: Any additional arguments that may be used for
            generating an error message.
        :raise OffsetLimitParseError: Raised in cases where there was
            an issue parsing the offset, limit, or page value.
        :raise DrowsyError: Raised in all other cases.

        """
        if key == "resource_not_found":
            raise ResourceNotFoundError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs)
        elif key == "method_not_allowed":
            raise MethodNotAllowedError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs)
        else:
            raise BadRequestError(
                code=key,
                message=self._get_error_message(key, **kwargs),
                **kwargs)

    def _get_error_message(self, key, **kwargs):
        """Get an error message based on a key name.

        If the error message is a callable, kwargs are passed
        to that callable.

        If ``self.context`` has a ``"gettext" key set to a callable,
        that callable will be passed the resulting string and any
        key word args for the sake of translation.

        :param str key: Key used to access the error messages dict.
        :param dict kwargs: Any additional arguments that may be passed
            to a callable error message, or used to translate and/or
            format an error message string.

        """
        try:
            return get_error_message(
                error_messages=self.error_messages,
                key=key,
                gettext=self.context.get("gettext", None),
                **kwargs)
        except KeyError:
            class_name = self.__class__.__name__
            msg = MISSING_ERROR_MESSAGE.format(class_name=class_name, key=key)
            raise AssertionError(msg)

    def _get_schema_kwargs(self, schema_cls):
        """Get key word arguemnts for constructing a schema.

        :param schema_cls: The schema class being constructed.
        :return: A dictionary of arguments.
        :rtype: dict

        """
        result = {
            "context": self.context
        }
        return result

    def _get_resource_kwargs(self, resource_cls):
        """Get kwargs to be used for creating a new resource instance.

        :param resource_cls: The resource class to be created.
        :return: Arguments to be used to initialize a resource.
        :rtype: dict

        """
        result = {
            "context": self.context
        }
        return result

    def _get_path_info(self, path):
        """Break a url path into a series of resources, ids, and fields.

        /album/1/tracks/5/track_id would return a list containing:
        [AlbumResource, (1,), TrackResource, (5,), fields["track_id]]

        :param str path: The path portion of a requested URL
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :return: A list containing resources, ids, and fields in the
            order they're specified in a path.

        """
        resource = None
        split_path = path.split("/")
        result = []
        # remove empty string if path started with a slash
        if len(split_path) > 0 and split_path[0] == "":
            split_path.pop(0)
        while split_path:
            # pop the resource name
            # e.g. /albums/1/tracks/0 -> /1/tracks/0
            path_part = split_path.pop(0)
            if resource is None:
                resource = self.resource
                result.append(resource)
            else:
                attr_name = resource.convert_key_name(path_part)
                if attr_name is None:
                    self.fail("resource_not_found", path=path)
                schema_cls = resource.schema_cls
                schema = schema_cls(**self._get_schema_kwargs(schema_cls))
                field = schema.fields.get(attr_name)
                if field is not None:
                    if hasattr(field, "resource_cls"):
                        # this is a relationship
                        # get the sub-resource
                        resource = field.resource_cls(
                            **self._get_resource_kwargs(
                                field.resource_cls))
                        result.append(field)
                        if hasattr(field, "many") and not field.many:
                            continue
                    else:
                        # assume this is a property
                        # should be the last part of the path
                        # fail if not, otherwise return the result
                        if len(split_path):
                            self.fail("resource_not_found", path=path)
                        result.append(field)
                        return result
                else:
                    self.fail("resource_not_found", path=path)
            # check if this resource has an identifier or not
            id_keys = resource.schema_cls(
                **self._get_resource_kwargs(resource.schema_cls)).id_keys
            if len(split_path) == 0:
                # collection!
                return result
            elif len(split_path) < len(id_keys):
                # bad news everyone!
                # e.g. /resource/<key_one_of_two/
                # resource that has a multi key identifier;
                # only one provided
                self.fail("resource_not_found", path=path)
            else:
                # append the given identifier
                ident = ()
                for i in range(0, len(id_keys)):
                    ident = ident + (split_path.pop(0), )
                result.append(ident)
        return result

    def get(self, path, query_params=None, strict=True):
        """Generic API router for GET requests.

        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param query_params: Dictionary of query parameters, likely
            provided as part of a request. Defaults to an empty dict.
        :type query_params: dict or None
        :param bool strict: If `True`, bad query params will raise
            non fatal errors rather than ignoring them.
        :return: If this is a single entity query, an individual
            resource in dict form. If this is a collection query,
            a list of resources in dict form.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise BadRequestError: Invalid filters, sorts, fields,
            embeds, offset, or limit as defined in the provided query
            params will result in a raised exception if strict is set
            to `True`.

        """
        raise NotImplementedError

    def put(self, path, data):
        """Generic API router for PUT requests.

        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param data: A dict or list of dicts of entities to
            replace the current value with at the given path.
        :return: If this is a put to a subresource collection, the
            replaced subresource is returned.
            If this is a put to an individual resource then the
            replaced resource is returned.
            If this is a put to a field, the replaced field value is
            returned.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise MethodNotAllowedError: A put on a top level collection
            will raise this error.

        """
        raise NotImplementedError

    def patch(self, path, data):
        """Generic API router for PATCH requests.

        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param data: A dict or list of dicts of entities to
            add or remove at the given path.
        :return: If this is a patch to a resource collection, ``None``
            is returned.
            If this is a patch to a subresource collection, the
            updated subresource is returned.
            If this is a patch to an individual resource then the
            updated resource is returned.
            If this is a patch to a field, the updated field value is
            returned.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise MethodNotAllowedError: A patch at a valid path may return
            this due to permission issues.

        """
        raise NotImplementedError

    def post(self, path, data):
        """Generic API router for POST requests.

        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param data: A dict or list of dicts of new entities to
            add at the given path.
        :return: If this is a post to a top level resource, then the
            newly created resource or list of resources will be returned
            in dict or list of dicts form.
            If this is a post to a subresource, then the updated
            subresource data will be returned.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise MethodNotAllowedError: Posts to individual properties or
            resources will cause an error.

        """
        raise NotImplementedError

    def delete(self, path, query_params=None):
        """Generic API router for DELETE requests.

        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param query_params: Dictionary of query parameters, likely
            provided as part of a request. Defaults to an empty dict.
        :type query_params: dict or None
        :return: ``None`` if successful.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise BadRequestError: Invalid filters, sorts, fields,
            embeds, offset, or limit as defined in the provided query
            params will result in a raised exception if strict is set
            to `True`.
        :raise MethodNotAllowedError: If deleting the resource at the
            supplied path is not allowed.

        """
        raise NotImplementedError

    def dispatcher(self, method, path, query_params=None, data=None,
                   strict=True):
        """Route requests based on path and resource.

        :param str method: HTTP verb method used to make this request.
        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param dict query_params: Dictionary of query parameters, likely
            provided as part of a request.
        :param bool strict: If `True`, faulty pagination info, fields,
            or embeds will result in an error being raised rather than
            silently ignoring them.
        :param data: The data supplied as part of the incoming request
            body. Optional, and the format of this data may vary.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise BadRequestError: Invalid filters, sorts, fields,
            embeds, offset, or limit as defined in the provided query
            params will result in a raised exception if strict is set
            to `True`.
        :raise UnprocessableEntityError: On post, patch, put, and delete
            requests, if the corresponding action can not be completed,
            an exception will be raised.
        :return: Dependent on the method and whether the path refers to
            a collection or individual resource.

            * Get: An individual resource in dict form.
            * Post: The created resource in dict form if successful.
            * Patch: The updated resource in dict form if successful.
            * Put: The replaced resource in dict form if successful.
            * Delete: `None` if successful.
            * Get collection: A list of resources in dict form.
            * Patch collection: `None` if successful.
            * Post collection: A list of created resources in dict form.
            * Delete collection: `None` if successful.

        """
        if method.lower() == "get":
            return self.get(path, query_params, strict)
        elif method.lower() == "delete":
            return self.delete(path, query_params)
        elif method.lower() == "patch":
            return self.patch(path, data)
        elif method.lower() == "put":
            return self.patch(path, data)
        elif method.lower() == "post":
            return self.patch(path, data)
        else:
            self.fail("method_not_allowed", path=path, method=method.upper())


class ModelResourceRouter(ResourceRouterABC):

    """Utility class used to route incoming requests.

    Currently handles nested resources assuming they're of
    :class:`~drowsy.resource.ModelResource` type.

    """

    def __init__(self, resource=None, error_messages=None, context=None,
                 session=None):
        """Sets up router error messages and translations.

        :param resource: A resource instance. If none is provided,
            an attempt to dynamically create a resource upon dispatch
            using the provided path, context, and session will be made.
        :type resource: :class:`~drowsy.resource.ModelResource`
            or None
        :param error_messages: Optional dictionary of error messages,
            useful if you want to override the default errors.
        :type error_messages: dict or None


        """
        self._context = context
        self._session = session
        super(ModelResourceRouter, self).__init__(resource, error_messages)

    @property
    def context(self):
        """Return the schema context for this resource."""
        if self.resource is not None:
            return self.resource.context
        else:
            if callable(self._context):
                return self._context()
            else:
                if self._context is None:
                    self._context = {}
                return self._context

    @property
    def session(self):
        """Return the session for this resource."""
        if self.resource is not None:
            return self.resource.session
        else:
            if self._session is not None:
                return self._session
            return None

    def _get_schema_kwargs(self, schema_cls):
        """Get key word arguemnts for constructing a schema.

        :param schema_cls: The schema class being constructed.
        :return: A dictionary of arguments.
        :rtype: dict

        """
        result = super(ModelResourceRouter, self)._get_schema_kwargs(
            schema_cls)
        if issubclass(schema_cls, ModelSchema):
            result["session"] = self.session
        return result

    def _get_resource_kwargs(self, resource_cls):
        """Get kwargs to be used for creating a new resource instance.

        :param resource_cls: The resource class to be created.
        :return: Arguments to be used to initialize a resource.
        :rtype: dict

        """
        result = super(ModelResourceRouter, self)._get_resource_kwargs(
            resource_cls)
        if issubclass(resource_cls, BaseModelResource):
            result["session"] = self.session
        return result

    def _deduce_resource(self, path):
        """Get a resource class based on the supplied path.

        :param str path: The url path for this resource.

        """
        if self.resource is None:
            split_path = path.split("/")
            if len(split_path) > 0 and split_path[0] == "":
                split_path.pop(0)
            if split_path:
                resource_class_name = inflection.camelize(
                    inflection.singularize(split_path[0]))+"Resource"
                resource_cls = class_registry.get_class(resource_class_name)
                self.resource = resource_cls(
                    **self._get_resource_kwargs(resource_cls))
        return self.resource

    def _get_path_objects(self, path):
        """Extract resource objects and identities from the path.

        This is pretty messy and should get cleaned up eventually.

        :param path: The input resource path.
        :return: A dict with the following keys defined:

            * parent_resource
            * resource
            * instance
            * path_part
            * query_session
            * ident
            * field

        :rtype: dict

        """
        path_parts = self._get_path_info(path)
        parent_resource = None
        resource = None
        instance = None
        path_part = None
        field = None
        query_session = None
        ident = None
        while path_parts:
            path_part = path_parts.pop(0)
            if isinstance(path_part, BaseModelResource):
                resource = path_part
                query_session = resource.session.query(resource.model)
            elif isinstance(path_part, Field) and hasattr(
                    path_part, "resource_cls"):
                # subresource
                parent_resource = resource
                resource = path_part.resource_cls(
                    **self._get_resource_kwargs(path_part.resource_cls))
                query_session = resource.session.query(
                    resource.model).with_parent(
                    instance, path_part.name)
                if hasattr(path_part, "many") and not path_part.many:
                    instance = query_session.first()
            elif isinstance(path_part, Field):
                # resource property
                if len(path_parts):
                    self.fail("resource_not_found", path=path)
                field = path_part
            elif isinstance(path_part, tuple):
                # resource instance
                ident = path_part
                only_field_left = len(path_parts) == 1 and (
                    isinstance(path_parts[0], Field) and not hasattr(
                        path_parts[0], "resource_cls"))
                if path_parts and not only_field_left:
                    id_keys = resource.schema_cls(
                        **self._get_resource_kwargs(
                            resource.schema_cls)).id_keys
                    for i, id_key in enumerate(id_keys):
                        model_attr = getattr(resource.model, id_key)
                        target_type = type(model_attr.property.columns[0].type)
                        value = convert_to_alchemy_type(ident[i], target_type)
                        query_session = query_session.filter(
                            model_attr == value)
                    instance = query_session.first()
                    if instance is None:
                        self.fail("resource_not_found", path=path)
                # if this is the end of the path, don't need instance
        # TODO - This is pretty ugly. Needs to be tightened up.
        return {
            "parent_resource": parent_resource,
            "resource": resource,
            "instance": instance,
            "path_part": path_part,
            "query_session": query_session,
            "ident": ident,
            "field": field
        }

    def _subfield_update(self, method, data, parent_resource,
                         resource, path_part, ident, query_session):
        """TODO

        :param method:
        :param data:
        :param parent_resource:
        :param resource:
        :param path_part:
        :param ident:
        :param query_session:
        :return:

        """
        if isinstance(path_part, Field) and hasattr(
                    path_part, "resource_cls"):
            relation_name = path_part.load_from or path_part.name
            if isinstance(data, list):
                # Will attempt to add multiple items to the relation
                try:
                    if method.lower() == "put":
                        temp_data = parent_resource.get(
                            ident, session=query_session)
                        temp_data[relation_name] = data
                        data = temp_data
                        result = parent_resource.put(ident=ident, data=data)
                    else:
                        data = {
                            relation_name: data
                        }
                        result = parent_resource.patch(ident=ident, data=data)
                    return result[relation_name]
                except UnprocessableEntityError as e:
                    reformatted_error = UnprocessableEntityError(
                        message=e.message,
                        code=e.kwargs.get("code", None),
                        errors=e.errors[relation_name]
                    )
                    raise reformatted_error
            else:
                if hasattr(path_part, "many") and path_part.many:
                    # Relationship is a list, so treat this as
                    # adding another object to the list.
                    data = {
                        relation_name: [data]
                    }
                    try:
                        result = parent_resource.patch(
                            ident=ident, data=data)
                        return result[relation_name]
                    except UnprocessableEntityError as e:
                        reformatted_error = UnprocessableEntityError(
                            message=e.message,
                            code=e.kwargs.get("code", None),
                            errors=e.errors[relation_name][0]
                        )
                        raise reformatted_error
                else:
                    # Relationship is one to one, so treat this as
                    # setting the value to an object.
                    data = {
                        relation_name: data
                    }
                    try:
                        result = parent_resource.patch(
                            ident=ident, data=data)
                        return result[relation_name]
                    except UnprocessableEntityError as e:
                        reformatted_error = UnprocessableEntityError(
                            message=e.message,
                            code=e.kwargs.get("code", None),
                            errors=e.errors[relation_name]
                        )
                        raise reformatted_error
        elif isinstance(path_part, Field):
            # Post/Put/Patch to a single field.
            # Set the value, and return it.
            field_name = path_part.load_from or path_part.name
            data = {
                field_name: data
            }
            try:
                result = resource.patch(
                    ident=ident, data=data)
                return result[field_name]
            except UnprocessableEntityError as e:
                reformatted_error = UnprocessableEntityError(
                    message=e.message,
                    code=e.kwargs.get("code", None),
                    errors=e.errors[field_name]
                )
                raise reformatted_error

    def put(self, path, data):
        """Generic API router for PUT requests.

        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param data: A dict or list of dicts of entities to
            replace the current value with at the given path.
        :return: If this is a put to a subresource collection, the
            replaced subresource is returned.
            If this is a put to an individual resource then the
            replaced resource is returned.
            If this is a put to a field, the replaced field value is
            returned.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise MethodNotAllowedError: A put on a top level collection
            will raise this error.

        """
        if self.resource is None:
            self._deduce_resource(path)
        path_objs = self._get_path_objects(path)
        parent_resource = path_objs.get("parent_resource", None)
        resource = path_objs.get("resource", None)
        path_part = path_objs.get("path_part", None)
        ident = path_objs.get("ident", None)
        query_session = path_objs.get("query_session", None)
        if resource is None:
            self.fail("resource_not_found", path=path)
        if isinstance(path_part, BaseModelResource):
            # put collection
            return resource.put_collection(data=data)
        elif isinstance(path_part, tuple):
            return resource.put(ident, data=data)
        else:
            # Dealing with a subresource, so this is treated
            # more as a patch/update to that subresource.
            result = self._subfield_update(
                method="put",
                data=data,
                parent_resource=parent_resource,
                resource=resource,
                path_part=path_part,
                ident=ident,
                query_session=query_session)
            if result:
                return result
        self.fail("method_not_allowed", path=path, method="PUT")

    def patch(self, path, data):
        """Generic API router for PATCH requests.

        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param data: A dict or list of dicts of entities to
            add or remove at the given path.
        :return: If this is a patch to a resource collection, ``None``
            is returned.
            If this is a patch to a subresource collection, the
            updated subresource is returned.
            If this is a patch to an individual resource then the
            updated resource is returned.
            If this is a patch to a field, the updated field value is
            returned.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise MethodNotAllowedError: A patch at a valid path may return
            this due to permission issues.

        """
        if self.resource is None:
            self._deduce_resource(path)
        path_objs = self._get_path_objects(path)
        parent_resource = path_objs.get("parent_resource", None)
        resource = path_objs.get("resource", None)
        path_part = path_objs.get("path_part", None)
        ident = path_objs.get("ident", None)
        query_session = path_objs.get("query_session", None)
        if resource is None:
            self.fail("resource_not_found", path=path)
        if isinstance(path_part, BaseModelResource):
            # patch collection
            return resource.patch_collection(data=data)
        elif isinstance(path_part, tuple):
            return resource.patch(ident, data=data)
        else:
            # Dealing with a subresource, so this is treated
            # more as a patch/update to that subresource.
            result = self._subfield_update(
                method="patch",
                data=data,
                parent_resource=parent_resource,
                resource=resource,
                path_part=path_part,
                ident=ident,
                query_session=query_session)
            if result:
                return result
        self.fail("method_not_allowed", path=path, method="PATCH")

    def post(self, path, data):
        """Generic API router for POST requests.

        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param data: A dict or list of dicts of new entities to
            add at the given path.
        :return: If this is a post to a top level resource, then the
            newly created resource or list of resources will be returned
            in dict or list of dicts form.
            If this is a post to a subresource, then the updated
            subresource data will be returned.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise MethodNotAllowedError: Posts to individual properties or
            resources will cause an error.

        """
        if self.resource is None:
            self._deduce_resource(path)
        path_objs = self._get_path_objects(path)
        parent_resource = path_objs.get("parent_resource", None)
        resource = path_objs.get("resource", None)
        path_part = path_objs.get("path_part", None)
        ident = path_objs.get("ident", None)
        query_session = path_objs.get("query_session", None)
        if resource is None:
            self.fail("resource_not_found", path=path)
        if isinstance(path_part, BaseModelResource):
            # normal post to resource
            if isinstance(data, list):
                return resource.post_collection(data=data)
            else:
                return resource.post(data=data)
        else:
            # Dealing with a subresource, so this is treated
            # more as a patch/update to that subresource.
            result = self._subfield_update(
                method="post",
                data=data,
                parent_resource=parent_resource,
                resource=resource,
                path_part=path_part,
                ident=ident,
                query_session=query_session)
            if result:
                return result
        self.fail("method_not_allowed", path=path, method="POST")

    def get(self, path, query_params=None, strict=True):
        """Generic API router for GET requests.

        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param query_params: Dictionary of query parameters, likely
            provided as part of a request. Defaults to an empty dict.
        :type query_params: dict or None
        :param bool strict: If `True`, bad query params will raise
            non fatal errors rather than ignoring them.
        :return: If this is a single entity query, an individual
            resource or `None`. If this is a collection query, a list
            of resources. If it's an instance field query, the raw
            field value.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise BadRequestError: Invalid filters, sorts, fields,
            embeds, offset, or limit as defined in the provided query
            params will result in a raised exception if strict is set
            to `True`.

        """
        if self.resource is None:
            self._deduce_resource(path)
        path_objs = self._get_path_objects(path)
        resource = path_objs.get("resource", None)
        path_part = path_objs.get("path_part", None)
        query_session = path_objs.get("query_session", None)
        ident = path_objs.get("ident", None)
        if resource is None:
            self.fail("resource_not_found", path=path)
        parser = ModelQueryParamParser(query_params, context=self.context)
        fields = parser.parse_fields()
        embeds = parser.parse_embeds()
        # last path_part determines what type of request this is
        if isinstance(path_part, Field) and not hasattr(
                path_part, "resource_cls"):
            # Simple property, such as album_id
            # return only the value
            field_name = path_part.load_from or path_part.name
            result = resource.get(
                ident=ident,
                fields=[field_name],
                strict=strict,
                session=query_session)
            if result is not None and field_name in result:
                return result[field_name]
            self.fail("resource_not_found", path=path)
        if isinstance(path_part, Field) or isinstance(
                path_part, BaseModelResource):
            # resource collection
            # any non subresource field would already have been handled
            if not (isinstance(path_part, Nested) and not path_part.many):
                try:
                    offset_limit_info = parser.parse_offset_limit(
                        resource.page_max_size)
                    offset = offset_limit_info.offset
                    limit = offset_limit_info.limit
                    filters = parser.parse_filters(
                        resource.model,
                        convert_key_names_func=resource.convert_key_name)
                except (OffsetLimitParseError, FilterParseError) as e:
                    if strict:
                        key = e.code
                        self.fail(key=key, **e.kwargs)
                    offset, limit, filters = None, None, None
                sorts = parser.parse_sorts()
                return resource.get_collection(
                    filters=filters,
                    fields=fields,
                    embeds=embeds,
                    sorts=sorts,
                    offset=offset,
                    limit=limit,
                    session=query_session,
                    strict=strict)
            else:
                result = resource.get_collection(
                    fields=fields,
                    embeds=embeds,
                    session=query_session,
                    strict=strict)
                if len(result) != 1:
                    self.fail("resource_not_found", path=path)
                return result[0]
        elif isinstance(path_part, tuple):
            # path part is a resource identifier
            # individual instance
            return resource.get(
                ident=path_part,
                fields=fields,
                embeds=embeds,
                strict=strict,
                session=query_session)
        self.fail("resource_not_found", path=path)

    def delete(self, path, query_params=None):
        """Generic API router for DELETE requests.

        :param str path: The resource path specified. This should not
            include the root ``/api`` or any versioning info.
        :param query_params: Dictionary of query parameters, likely
            provided as part of a request. Defaults to an empty dict.
        :type query_params: dict or None
        :return: ``None`` if successful.
        :raise ResourceNotFoundError: If no resource can be found at
            the provided path.
        :raise BadRequestError: Invalid filters, sorts, fields,
            embeds, offset, or limit as defined in the provided query
            params will result in a raised exception if strict is set
            to `True`.
        :raise MethodNotAllowedError: If deleting the resource at the
            supplied path is not allowed.

        """
        if self.resource is None:
            self._deduce_resource(path)
        path_objs = self._get_path_objects(path)
        resource = path_objs.get("resource", None)
        path_part = path_objs.get("path_part", None)
        query_session = path_objs.get("query_session", None)
        ident = path_objs.get("ident", None)
        if resource is None:
            self.fail("resource_not_found", path=path)
        parser = ModelQueryParamParser(query_params, context=self.context)
        # last path_part determines what type of request this is
        if isinstance(path_part, Field) and not hasattr(
                path_part, "resource_cls"):
            # Simple property, such as album_id
            # return only the value
            field_name = path_part.load_from or path_part.name
            data = {
                field_name: None
            }
            result = resource.patch(
                ident=ident,
                data=data,
                session=query_session)
            if result is not None and field_name in result:
                return result[field_name]
            self.fail("resource_not_found", path=path)
        if isinstance(path_part, Field) or isinstance(
                path_part, BaseModelResource):
            # resource collection
            # any non subresource field would already have been handled
            if not (isinstance(path_part, Nested) and not path_part.many):
                filters = parser.parse_filters(
                    resource.model,
                    convert_key_names_func=resource.convert_key_name)
                return resource.delete_collection(
                    filters=filters,
                    session=query_session)
            else:
                return resource.delete_collection(
                    session=query_session)
        elif isinstance(path_part, tuple):
            # path part is a resource identifier
            # individual instance
            return resource.delete(
                ident=path_part,
                session=query_session)
        self.fail("resource_not_found", path=path)
