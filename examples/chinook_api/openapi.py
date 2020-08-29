"""
    chinook_api.openapi
    ~~~~~~~~~~~~~~~~~~~

    Generate an OpenAPI compliant spec.

"""
# :copyright: (c) 2020 by Nicholas Repole and contributors.
#             See AUTHORS for more details.
# :license: MIT - See LICENSE for more details.
import apispec
from apispec.exceptions import DuplicateComponentNameError
from apispec.ext.marshmallow import MarshmallowPlugin
from contextlib import suppress
from .schemas import *
from .resources import *
from inspect import isclass
from marshmallow.fields import String
from drowsy.schema import ModelResourceSchema
from drowsy.fields import NestedRelated, APIUrl
import inflection

ma_plugin = MarshmallowPlugin()

spec = apispec.APISpec(
    title="Swagger Docs",
    version="0.1.1",
    openapi_version="3.0.2",
    plugins=[ma_plugin]
)


def nestedrelated2properties(self, field, **kwargs):
    """Handle NestedRelated Drowsy field.

    Only needed due to potential use of `many=True`, whereas Nested
    fields are often embedded in List fields. This is pretty hacky,
    and basically just moves around properties that `nested2properties`
    generated.

    :param MarshmallowPlugin self: This method will end up bound to a
        MarshmallowPlugin instance.
    :param field: The marshmallow field being converted.
    :return: A dict of properties to be included in our spec.
    :rtype: dict

    """
    ret = kwargs.get("ret", {})
    if isinstance(field, NestedRelated):
        if field.many:
            if "$ref" in ret:
                # will be moving $ref to items, pop it from ret
                schema_dict = {"$ref": ret.pop("$ref")}
            elif isinstance(ret.get("allOf", []), list):
                # case where allOf is needed on a list reference
                # would have to be some polymorphism situation...
                # Honestly not sure if this is necessary, or valid.
                all_of = ret.get("allOf", [])
                if len(all_of) > 1:
                    schema_dict = {"allOf": ret.pop("allOf")}
                elif len(all_of) == 1:
                    schema_dict = all_of[0]
                else:
                    schema_dict = {}
            else:
                schema_dict = self.resolve_nested_schema(field.schema)
            ret["type"] = "array"
            ret["items"] = {}
            if schema_dict:
                ret["items"].update(schema_dict)
    return ret


ma_plugin.converter.add_attribute_function(nestedrelated2properties)
ma_plugin.map_to_openapi_type(String)(APIUrl)


def populate_spec():
    """Builds out the global `spec` with info about our API.

    This is pretty messy, and you'll probably want to make some tweaks
    depending on what you want your spec to look like.

    One challenge with Drowsy based APIs and Swagger is that the
    optional ability to embed nested relationships is hard (impossible?)
    to represent with Swagger. The result is swagger-ui traversing
    ALL possible embeds for every endpoint, which can get pretty messy,
    and involve some null values showing up for circular references.

    """
    global_vars = globals().copy().items()
    # Generate resources and schemas based on global vars
    # will be used for building components and paths
    # You should probably do this in a less generic/messy way...
    schemas = []
    resources = []
    for key, val in global_vars:
        if isclass(val) and issubclass(
                val, ModelResourceSchema) and key != 'ModelResourceSchema':
            schemas.append(val)
        if isclass(val) and issubclass(
                val, ModelResource) and key != "ModelResource":
            resources.append(val)
    # build components for error types
    field_errors = {
        "type": "object",
        "description": "A field by field breakdown of errors."
    }
    spec.components.schema(name="FieldErrors", component=field_errors)
    field_errors_array = {
        "type": "array",
        "items": {"$ref": "#/components/schemas/FieldErrors"}
    }
    spec.components.schema(name="FieldErrorsArray", component=field_errors_array)
    unprocessable_entity_error = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"},
            "errors": {"$ref": "#/components/schemas/FieldErrors"}
        }
    }
    spec.components.schema(name="UnprocessableEntityError", component=unprocessable_entity_error)
    unprocessable_array_error = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"},
            "errors": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/FieldErrors"}
            }
        }
    }
    spec.components.schema(name="UnprocessableArrayError", component=unprocessable_array_error)
    method_not_allowed = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"}
        }
    }
    spec.components.schema(name="MethodNotAllowed", component=method_not_allowed)
    resource_not_found = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"}
        }
    }
    spec.components.schema(name="ResourceNotFound", component=resource_not_found)
    bad_request_error = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"}
        }
    }
    spec.components.schema(name="BadRequestError", component=bad_request_error)
    # build schema components
    for schema in schemas:
        name = schema.__name__
        if name.endswith("Schema"):
            name = name[0:-len("Schema")]
        with suppress(DuplicateComponentNameError):
            spec.components.schema(name=name, schema=schema)
    # Build paths and responses
    # common error responses will be repeatedly used...
    bad_request_resp = {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/BadRequestError"
                }
            }
        }
    }
    method_not_allowed_resp = {
        "description": "Method Not Allowed",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/MethodNotAllowed"
                }
            }
        }
    }
    resource_not_found_resp = {
        "description": "Resource Not Found",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/ResourceNotFound"
                }
            }
        }
    }
    unprocessable_entity_resp = {
        "description": "Unprocessable Entity",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/UnprocessableEntityError"
                }
            }
        }
    }
    unprocessable_array_resp = {
        "description": "Unprocessable Entity",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/UnprocessableArrayError"
                }
            }
        }
    }
    # common parameters that will be reused...
    param_filters = {
        "in": "query",
        "name": "filters",
        "schema": {
            "type": "string"
        },
        "required": False,
        "description": "Dumped JSON filters in the format of MQLAlchemy."
    }
    param_offset = {
        "in": "query",
        "name": "offset",
        "schema": {
            "type": "integer"
        },
        "required": False,
        "description": "Offset results, can be used instead of page."
    }
    param_limit = {
        "in": "query",
        "name": "limit",
        "schema": {
            "type": "integer"
        },
        "required": False,
        "description": "Limit the number of results returned."
    }
    param_page = {
        "in": "query",
        "name": "page",
        "schema": {
            "type": "integer"
        },
        "required": False,
        "description": "Page number, may also require limit to be set."
    }
    param_fields = {
        "in": "query",
        "name": "fields",
        "schema": {
            "type": "string"
        },
        "required": False,
        "description": "Comma separated list of fields to include."
    }
    param_embeds = {
        "in": "query",
        "name": "embeds",
        "schema": {
            "type": "string"
        },
        "required": False,
        "description": "Comma separated list of subresources to embed."
    }
    param_sort = {
        "in": "query",
        "name": "sort",
        "schema": {
            "type": "string"
        },
        "required": False,
        "description": ("Comma separated list of fields to sort by."
                        "Defaults to ASC, place a `-` in front of the field "
                        "to sort DESC.")
    }
    # Build paths for each resource type
    for resource_cls in resources:
        name = resource_cls.__name__
        if name.endswith("Resource"):
            name = name[0:-len("Resource")]
        resource = resource_cls(session=None)
        # collection prefix for collection resource access
        collection_path = name[:1].lower() + name[1:] if name else ''
        collection_path = "/api/" + inflection.pluralize(collection_path)
        collection_operations = {}
        id_keys = resource.schema.id_keys
        item_params = []
        identifiers = []
        for key in id_keys:
            data_key = resource.schema.fields[key].data_key or key
            identifiers.append(data_key)
            param = ma_plugin.converter.field2parameter(
                resource.schema.fields[key], name=data_key, default_in="path")
            param["required"] = True
            item_params.append(param)
        item_path = "/".join(
            [collection_path] + ["{" + i + "}" for i in identifiers])
        item_operations = {}
        options = ["get", "post", "patch", "put", "delete"]
        resource_options = set([o.lower() for o in resource.options])
        for option in options:
            if option not in resource_options:
                continue
            responses = {}
            collection_responses = {}
            collection_params = []
            if option in ("get", "head", "delete"):
                collection_params.append(param_filters)
                if option != "delete":
                    collection_params.append(param_offset)
                    collection_params.append(param_limit)
                    collection_params.append(param_page)
                    collection_params.append(param_fields)
                    collection_params.append(param_embeds)
                    collection_params.append(param_sort)
            if option == "get":
                responses["200"] = {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": name + "Schema"
                        }
                    }
                }
                collection_responses["200"] = {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": name + "Schema"
                            }
                        }
                    }
                }
            elif option in ("post", "patch", "put"):
                success_code = "201" if option.lower() == "post" else "200"
                description = "Created" if success_code == "201" else "OK"
                responses[success_code] = {
                    "description": description,
                    "content": {
                        "application/json": {
                            "schema": name + "Schema"
                        }
                    }
                }
                responses["433"] = unprocessable_entity_resp
                if option != "put":
                    collection_responses["204"] = {
                        "description": "No content."
                    }
                    collection_responses["433"] = unprocessable_array_resp
            elif option == "delete":
                responses["204"] = {"description": "No content."}
                responses["433"] = unprocessable_entity_resp
                collection_responses["204"] = responses["204"]
                collection_responses["433"] = unprocessable_array_resp
            elif option == "options":
                responses["200"] = {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/HttpOptionsResponse"
                            }
                        }
                    }
                }
                collection_responses["200"] = responses["200"]
            elif option == "head":
                responses["200"] = {"description": "No content."}
            if option != "options":
                responses["400"] = bad_request_resp
                responses["405"] = method_not_allowed_resp
                collection_responses["400"] = bad_request_resp
                collection_responses["405"] = method_not_allowed_resp
            if option not in ["options", "post"]:
                # most methods can have a resource not found...
                responses["404"] = resource_not_found_resp
            item_operations[option] = {"responses": responses}
            if item_params:
                item_operations[option]["parameters"] = item_params
            collection_operations[option] = {"responses": collection_responses}
            if collection_params:
                collection_operations[option]["parameters"] = collection_params
        spec.path(path=item_path, operations=item_operations)
        spec.path(path=collection_path, operations=collection_operations)


populate_spec()
