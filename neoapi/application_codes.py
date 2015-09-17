from http_error_codes import (OK, CREATED, BAD_REQUEST, UNAUTHORIZED, FORBIDDEN, NOT_FOUND,
                              CONFLICT, INTERNAL_SERVER_ERROR, NOT_ALLOWED)
from flask import jsonify, make_response

BAD_FORMAT_VIOLATION = '4000', 'there is a problem with the request format', BAD_REQUEST
UNIQUE_KEY_VIOLATION = '4001', 'a uniqueness constraint is violated by the request', BAD_REQUEST
WRONG_TYPE_VIOLATION = '4002', 'the type key does not match the resource requested', BAD_REQUEST
PARAMETER_NOT_SUPPORTED_VIOLATION = '4003', 'a query parameter you tried to use is not supported for this endpoint', BAD_REQUEST
ENUMERATED_TYPE_VIOLATION = '4004', 'a value given for an enumerated type was unsupported', BAD_REQUEST
BAD_PARAMETER_VIOLATION = '4005', 'one or more of the attributes in your request is not part of the model', BAD_REQUEST
ATTEMPTED_CARDINALITY_VIOLATION = '4006', 'you tried to do something that would violate a cardinality constraint', BAD_REQUEST

RESOURCE_NOT_FOUND = '4040', 'the requested resource was not found on the server', NOT_FOUND

METHOD_NOT_ALLOWED = '4050', 'the http method you tried is not a legal operation on this resource', NOT_ALLOWED
FORBIDDEN_VIOLATION = '4030', 'the http method you tried is forbidden.', FORBIDDEN
UNAUTHORIZED_VIOLATION = '4010', 'missing or bad authorization', UNAUTHORIZED
BAD_AUTHENTICATION = '4011', 'bad authorization', UNAUTHORIZED
NO_AUTHENTICATION = '4012', 'no authorization header provided', UNAUTHORIZED

INTERNAL_SERVER_ERROR_VIOLATION = '5000', 'internal server error', INTERNAL_SERVER_ERROR
MULTIPLE_NODES_WITH_ID_VIOLATION = '5001', 'multiple nodes with the same id', INTERNAL_SERVER_ERROR_VIOLATION


def error_response(array_of_application_code_tuples):
    errors = list()
    for app_code_tuple in array_of_application_code_tuples:
        error = dict()
        error['status'] = app_code_tuple[2]
        error['code'] = app_code_tuple[0]
        error['title'] = app_code_tuple[1]
        errors.append(error)

    r = make_response(jsonify({'errors': errors}))
    r.status_code = app_code_tuple[2]
    r.headers['Content-Type'] = "application/vnd.api+json; charset=utf-8"

    return r


