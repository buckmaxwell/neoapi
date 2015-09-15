from neomodel import (Property, StructuredNode, StringProperty, DateProperty, AliasProperty, UniqueProperty,
                      DateTimeProperty, RelationshipFrom, BooleanProperty, Relationship, DoesNotExist, ZeroOrOne,
                      DeflateError)
from py2neo.cypher.error.statement import ParameterMissing
import os
import http_error_codes
from flask import jsonify, make_response
from neomodel import db
import application_codes
from .errors import WrongTypeError
from datetime import datetime
import hashlib

base_url = os.environ.get('BASE_API_URL', 'http://localhost:5000/v1')
CONTENT_TYPE = "application/vnd.api+json; charset=utf-8"


class SerializableStructuredNode(StructuredNode):
    """
    This class extends NeoModel's StructuredNode class. It adds a series of functions in order to allow for \
    creation of json responses that conform to the jsonapi specification found at http://jsonapi.org/
    """
    hashed = []
    secret = []
    dates = []
    enums = dict()
    updated = DateTimeProperty(default=datetime.now())
    created = DateTimeProperty(default=datetime.now())
    active = BooleanProperty(default=True)

    def get_self_link(self):
        return '{base_url}/{type}/{id}'.format(base_url=base_url, type=self.type, id=self.id)

    @classmethod
    def get_class_link(cls):
        return '{base_url}/{type}'.format(base_url=base_url, type=cls.type)

    @classmethod
    def resource_collection_response(cls, offset=0, limit=20):

        query = "MATCH (n) WHERE n:{label} AND n.active RETURN n ORDER BY n.id SKIP {offset} LIMIT {limit}".format(
            label=cls.__name__,
            offset=offset,
            limit=limit)

        results, meta = db.cypher_query(query)
        data = dict()
        data['data'] = list()
        data['links'] = dict()

        data['links']['self'] = "{class_link}?page[offset]={offset}&page[limit]={limit}".format(
            class_link=cls.get_class_link(),
            offset=offset,
            limit=limit
        )

        data['links']['first'] = "{class_link}?page[offset]={offset}&page[limit]={limit}".format(
            class_link=cls.get_class_link(),
            offset=0,
            limit=limit
        )

        if int(offset) - int(limit) > 0:
            data['links']['prev'] = "{class_link}?page[offset]={offset}&page[limit]={limit}".format(
                class_link=cls.get_class_link(),
                offset=int(offset)-int(limit),
                limit=limit
            )

        if len(cls.nodes) > int(offset) + int(limit):
            data['links']['next'] = "{class_link}?page[offset]={offset}&page[limit]={limit}".format(
                class_link=cls.get_class_link(),
                offset=int(offset)+int(limit),
                limit=limit
            )

        data['links']['last'] = "{class_link}?page[offset]={offset}&page[limit]={limit}".format(
            class_link=cls.get_class_link(),
            offset=len(cls.nodes) - (len(cls.nodes) % int(limit)),
            limit=limit
        )



        list_of_nodes = [cls.inflate(row[0]) for row in results]
        for this_node in list_of_nodes:
            data['data'].append(this_node.get_resource_object())
        r = make_response(jsonify(data))
        r.status_code = http_error_codes.OK
        r.headers['Content-Type'] = CONTENT_TYPE
        return r

    def individual_resource_response(self, included=[]):
        data = dict()
        data['data'] = self.get_resource_object()
        data['links'] = {'self': self.get_self_link()}
        data['included'] = self.get_included_from_list(included)
        r = make_response(jsonify(data))
        r.status_code = http_error_codes.OK
        r.headers['Content-Type'] = CONTENT_TYPE
        return r

    def get_path_resources(self, path):
        response = list()
        if path:
            nodes = eval('self.{part}.all()'.format(part=path[0]))
            for n in nodes:
                if n.get_resource_object() not in response:
                    response.append(n.get_resource_object())
                response += n.get_path_resources(path[1:])

        return response

    def get_included_from_list(self, included):
        response = list()
        props = self.defined_properties()
        included = [x.split('.') for x in included]
        for attr_name in props.keys():
            if not isinstance(props[attr_name], Property):  # is attribute
                for path in included:
                    if attr_name == path[0]:
                        response += self.get_path_resources(path)

        return response

    def get_resource_object(self):
        response = dict()
        response['id'] = self.id
        response['type'] = self.type
        response['attributes'] = dict()
        response['relationships'] = dict()
        props = self.defined_properties()
        for attr_name in props.keys():
            if isinstance(props[attr_name], Property): # is attribute
                if attr_name not in self.secret:
                    response['attributes'][attr_name] = getattr(self, attr_name)

            else:  # is relationship
                response['relationships'][attr_name] = dict()

                # links
                response['relationships'][attr_name]['links'] = {
                    'self': '{base_url}/{type}/{id}/relationships/{attr_name}'.format(
                                                                                    base_url=base_url,
                                                                                    type=self.type,
                                                                                    id=self.id,
                                                                                    attr_name=attr_name),
                    'related': '{base_url}/{type}/{id}/{attr_name}'.format(
                                                                base_url=base_url,
                                                                type=self.type,
                                                                id=self.id,
                                                                attr_name=attr_name)
                }

                # data
                related_node_or_nodes = eval('self.{attr_name}.all()'.format(attr_name=attr_name))

                if not eval("type(self.{related_collection_type})".format(related_collection_type=attr_name)) == ZeroOrOne:
                    response['relationships'][attr_name]['data'] = list()
                    for the_node in related_node_or_nodes:
                        if the_node.active:
                            response['relationships'][attr_name]['data'].append({'type': the_node.type, 'id': the_node.id})
                elif related_node_or_nodes:
                    the_node = related_node_or_nodes[0]
                    response['relationships'][attr_name]['data'] = {'type': the_node.type, 'id': the_node.id}
                else:
                    response['relationships'][attr_name]['data'] = None

        return response

    def relationship_collection_response(self, related_collection_type, offset=0, limit=20):
        try:
            response = dict()
            response['included'] = list()
            total_length = eval('len(self.{related_collection_type})'.format(
                related_collection_type=related_collection_type)
            )
            response['links'] = {
                'self': '{base_url}/{type}/{id}/relationships/{related_collection_type}?page[offset]={offset}&page[limit]={limit}'.format(
                    base_url=base_url,
                    type=self.type,
                    id=self.id,
                    related_collection_type=related_collection_type,
                    offset=offset,
                    limit=limit
                ),
                'related': '{base_url}/{type}/{id}/{related_collection_type}'.format(
                                                            base_url=base_url,
                                                            type=self.type,
                                                            id=self.id,
                                                            related_collection_type=related_collection_type),
                'first': '{base_url}/{type}/{id}/relationships/{related_collection_type}?page[offset]={offset}&page[limit]={limit}'.format(
                    base_url=base_url,
                    type=self.type,
                    id=self.id,
                    related_collection_type=related_collection_type,
                    offset=0,
                    limit=limit
                ),
                'last': "{base_url}/{type}/{id}/relationships/{related_collection_type}?page[offset]={offset}&page[limit]={limit}".format(
                    base_url=base_url,
                    type=self.type,
                    id=self.id,
                    related_collection_type=related_collection_type,
                    offset=total_length - (total_length % int(limit)),
                    limit=limit
                )

            }

            if int(offset) - int(limit) > 0:
                response['links']['prev'] = "{base_url}/{type}/{id}/relationships/{related_collection_type}?page[offset]={offset}&page[limit]={limit}".format(
                    base_url=base_url,
                    type=self.type,
                    id=self.id,
                    related_collection_type=related_collection_type,
                    offset=int(offset) - int(limit),
                    limit=limit
                )

            if total_length > int(offset) + int(limit):
                response['links']['next'] = "{base_url}/{type}/{id}/relationships/{related_collection_type}?page[offset]={offset}&page[limit]={limit}".format(
                    base_url=base_url,
                    type=self.type,
                    id=self.id,
                    related_collection_type=related_collection_type,
                    offset=int(offset) + int(limit),
                    limit=limit
                )

            # data
            relation_type = eval('self.{related_collection_type}.definition'.format(
                related_collection_type=related_collection_type)).get('relation_type')

            results, columns = self.cypher(
                "START a=node({self}) MATCH a-[:{relation_type}]-(b) RETURN b SKIP {offset} LIMIT {limit}".format(
                    self=self._id, relation_type=relation_type, offset=offset, limit=limit
                )
            )
            related_node_or_nodes = [self.inflate(row[0]) for row in results]

            if not eval("type(self.{related_collection_type})".format(related_collection_type=related_collection_type)) == ZeroOrOne:
                response['data'] = list()
                for the_node in related_node_or_nodes:
                    if the_node.active:
                        response['data'].append({'type': the_node.type, 'id': the_node.id})
                        response['included'].append(the_node.get_resource_object())
            elif related_node_or_nodes:
                the_node = related_node_or_nodes[0]
                response['data'] = {'type': the_node.type, 'id': the_node.id}
                response['included'].append(the_node.get_resource_object())
            else:
                response['data'] = None

            r = make_response(jsonify(response))
            r.status_code = http_error_codes.OK
            r.headers['Content-Type'] = CONTENT_TYPE
        except AttributeError:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])
        return r

    def set_related_resources_collection_inactive(self, related_collection_type):
        try:
            # data
            relation_type = eval('self.{related_collection_type}.definition'.format(
                related_collection_type=related_collection_type)).get('relation_type')

            results, columns = self.cypher(
                "START a=node({self}) MATCH a-[:{relation_type}]-(b) RETURN b".format(
                    self=self._id, relation_type=relation_type
                )
            )
            related_node_or_nodes = [self.inflate(row[0]) for row in results]

            for n in related_node_or_nodes:
                n.deactivate()

            r = make_response('')
            r.status_code = http_error_codes.NO_CONTENT
            r.headers['Content-Type'] = CONTENT_TYPE
        except AttributeError:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])
        return r

    def set_individual_related_resource_inactive(self, related_collection_type, related_resource):
        # data
        related_node_or_nodes = eval('self.{related_collection_type}.search(id=related_resource)'.format(related_collection_type=related_collection_type), )

        if len(related_node_or_nodes) == 1:
            the_node = related_node_or_nodes[0]
            the_node.deactivate()
            r = make_response('')
            r.status_code = http_error_codes.NO_CONTENT
            r.headers['Content-Type'] = CONTENT_TYPE
        else:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])
        return r

    def related_resources_collection_response(self, related_collection_type, included, offset=0, limit=20):
        try:
            response = dict()
            response['included'] = list()
            total_length = eval('len(self.{related_collection_type})'.format(
                related_collection_type=related_collection_type)
            )
            response['links'] = {
                'self': '{base_url}/{type}/{id}/{related_collection_type}?page[offset]={offset}&page[limit]={limit}'.format(
                    base_url=base_url,
                    type=self.type,
                    id=self.id,
                    related_collection_type=related_collection_type,
                    offset=offset,
                    limit=limit
                ),
                'first': '{base_url}/{type}/{id}/{related_collection_type}?page[offset]={offset}&page[limit]={limit}'.format(
                    base_url=base_url,
                    type=self.type,
                    id=self.id,
                    related_collection_type=related_collection_type,
                    offset=0,
                    limit=limit
                ),
                'last': "{base_url}/{type}/{id}/{related_collection_type}?page[offset]={offset}&page[limit]={limit}".format(
                    base_url=base_url,
                    type=self.type,
                    id=self.id,
                    related_collection_type=related_collection_type,
                    offset=total_length - (total_length % int(limit)),
                    limit=limit
                )

            }

            if int(offset) - int(limit) > 0:
                response['links']['prev'] = "{base_url}/{type}/{id}/{related_collection_type}?page[offset]={offset}&page[limit]={limit}".format(
                    base_url=base_url,
                    type=self.type,
                    id=self.id,
                    related_collection_type=related_collection_type,
                    offset=int(offset) - int(limit),
                    limit=limit
                )

            if total_length > int(offset) + int(limit):
                response['links']['next'] = "{base_url}/{type}/{id}/{related_collection_type}?page[offset]={offset}&page[limit]={limit}".format(
                    base_url=base_url,
                    type=self.type,
                    id=self.id,
                    related_collection_type=related_collection_type,
                    offset=int(offset) + int(limit),
                    limit=limit
                )

            # data
            relation_type = eval('self.{related_collection_type}.definition'.format(
                related_collection_type=related_collection_type)).get('relation_type')

            results, columns = self.cypher(
                "START a=node({self}) MATCH a-[:{relation_type}]-(b) RETURN b SKIP {offset} LIMIT {limit}".format(
                    self=self._id, relation_type=relation_type, offset=offset, limit=limit
                )
            )
            related_node_or_nodes = [self.inflate(row[0]) for row in results]

            if not eval("type(self.{related_collection_type})".format(related_collection_type=related_collection_type)) == ZeroOrOne:
                response['data'] = list()
                for the_node in related_node_or_nodes:
                    if the_node.active:
                        response['data'].append(the_node.get_resource_object())
                        for n in the_node.get_included_from_list(included):
                            if n not in response['included']:
                                response['included'].append(n)
            elif related_node_or_nodes:
                the_node = related_node_or_nodes[0]
                response['data'].append(the_node.get_resource_object())
            else:
                response['data'] = None

            r = make_response(jsonify(response))
            r.status_code = http_error_codes.OK
            r.headers['Content-Type'] = CONTENT_TYPE
        except AttributeError:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])
        except SyntaxError:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])
        return r

    def related_resources_individual_response(self, related_collection_type, related_resource, included=[]):
        response = dict()
        response['links'] = {
            'self': '{base_url}/{type}/{id}/{related_collection_type}/{related_resource}'.format(
                                                                            base_url=base_url,
                                                                            type=self.type,
                                                                            id=self.id,
                                                                            related_collection_type=related_collection_type,
                                                                            related_resource=related_resource),
        }

        # data
        related_node_or_nodes = eval('self.{related_collection_type}.search(id=related_resource)'.format(related_collection_type=related_collection_type), )

        if len(related_node_or_nodes) == 1:
            the_node = related_node_or_nodes[0]
            response['data'] = the_node.get_resource_object()
            response['included'] = the_node.get_included_from_list(included)
            r = make_response(jsonify(response))
            r.status_code = http_error_codes.OK
            r.headers['Content-Type'] = CONTENT_TYPE
        else:
            response['data'] = None
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])

        return r

    def delete_relationship_collection(self, related_collection_type):
        related_node_or_nodes = eval('self.{related_collection_type}.all()'.format(
                related_collection_type=related_collection_type
        ))
        for node in related_node_or_nodes:
            eval('self.{related_collection_type}.disconnect(node)'.format(
                related_collection_type=related_collection_type
            ))
        r = make_response('')
        r.status_code = http_error_codes.NO_CONTENT
        r.headers['Content-Type'] = CONTENT_TYPE

        return r

    def delete_individual_relationship(self, related_collection_type, related_resource):
        related_node_or_nodes = eval('self.{related_collection_type}.search(id=related_resource)'.format(
                related_collection_type=related_collection_type
        ))
        for node in related_node_or_nodes:
            eval('self.{related_collection_type}.disconnect(node)'.format(
                related_collection_type=related_collection_type
            ))
        r = make_response('')
        r.status_code = http_error_codes.NO_CONTENT
        r.headers['Content-Type'] = CONTENT_TYPE

        return r

    def individual_relationship_response(self, related_collection_type, related_resource, included=[]):
        response = dict()
        response['links'] = {
            'self': '{base_url}/{type}/{id}/relationships/{related_collection_type}/{related_resource}'.format(
                                                                            base_url=base_url,
                                                                            type=self.type,
                                                                            id=self.id,
                                                                            related_collection_type=related_collection_type,
                                                                            related_resource=related_resource),
            'related': '{base_url}/{type}/{id}/{related_collection_type}/{related_resource}'.format(
                                                        base_url=base_url,
                                                        type=self.type,
                                                        id=self.id,
                                                        related_collection_type=related_collection_type,
                                                        related_resource=related_resource)
        }

        # data
        related_node_or_nodes = eval('self.{related_collection_type}.search(id=related_resource)'.format(related_collection_type=related_collection_type), )

        if len(related_node_or_nodes) == 1:
            the_node = related_node_or_nodes[0]
            response['data'] = {'type': the_node.type, 'id': the_node.id}
            response['included'] = [the_node.get_resource_object()] + the_node.get_included_from_list(included)
            r = make_response(jsonify(response))
            r.status_code = http_error_codes.OK
            r.headers['Content-Type'] = CONTENT_TYPE
        else:
            response['data'] = None
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])

        return r

    def deactivate(self):
        self.active = False
        self.save()

    @classmethod
    def get_resource_or_collection(cls, request_args, id=None):
        if id:
            try:
                this_resource = cls.nodes.get(id=id, active=True)

                try:
                    included = request_args.get('include').split(',')
                except:
                    included = []
                r = this_resource.individual_resource_response(included)

            except DoesNotExist:
                r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])
        else:
            if request_args.get('include'):
                r = application_codes.error_response([application_codes.PARAMETER_NOT_SUPPORTED_VIOLATION])
            else:

                try:

                    r = cls.resource_collection_response(
                        request_args.get('page[offset]', 0),
                        request_args.get('page[limit]', 20)
                    )
                except Exception as e:
                    print str(type(e)) + str(e)
        return r

    @classmethod
    def create_resource(cls, request_json):
        response = dict()
        new_resource, location = None, None
        try:
            data = request_json['data']
            if data['type'] != cls.type:
                raise WrongTypeError('type must match the type of the resource being created.')

            attributes = data.get('attributes')
            if attributes:
                for x in attributes.keys():
                    if x in cls.dates:
                        dt = datetime.strptime(attributes[x], '%Y-%m-%d')
                        attributes[x] = dt

                new_resource = cls(**attributes)
                new_resource.save()

                enum_keys = new_resource.enums.keys()
                for key in attributes.keys():
                    if key in enum_keys:
                        if attributes[key] in new_resource.enums[key]:
                            setattr(new_resource, key, attributes[key])
                        else:
                            raise EnumeratedTypeError
                    else:
                        setattr(new_resource, key, attributes[key])
                    new_resource.save()

                for r in new_resource.hashed:
                    unhashed = getattr(new_resource, r)
                    setattr(new_resource, r, hashlib.sha256(unhashed).hexdigest())
                    new_resource.save()

            relationships = data.get('relationships')
            if relationships:
                for relation_name in relationships.keys():
                    relations = relationships.get(relation_name)
                    if relations:
                        relations = relations['data']
                        if isinstance(relations, list):
                            for relation in relations:
                                the_type = relation['type']  # must translate type to cls
                                the_id = relation['id']
                                the_class = cls.get_class_from_type(the_type)
                                new_resources_relation = the_class.nodes.get(id=the_id, active=True)
                                eval('new_resource.{relation_name}.connect(new_resources_relation)'.format(
                                    relation_name=relation_name)
                                )
                                new_resource.save()
                        else:
                            relation = relations
                            the_type = relation['type']
                            the_id = relation['id']
                            the_class = cls.get_class_from_type(the_type)
                            new_resources_relation = the_class.nodes.get(id=the_id, active=True)
                            eval('new_resource.{relation_name}.connect(new_resources_relation)'.format(
                                relation_name=relation_name)
                            )
                            new_resource.save()

            response['data'] = new_resource.get_resource_object()
            response['links'] = {'self': new_resource.get_self_link()}
            status_code = http_error_codes.CREATED
            location = new_resource.get_self_link()

            r = make_response(jsonify(response))
            r.headers['Content-Type'] = "application/vnd.api+json; charset=utf-8"
            if location and new_resource:
                r.headers['Location'] = location

            r.status_code = status_code

        except UniqueProperty:
            r = application_codes.error_response([application_codes.UNIQUE_KEY_VIOLATION])
            try:
                new_resource.delete()
            except:
                pass

        except DoesNotExist:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])
            try:
                new_resource.delete()
            except:
                pass

        except WrongTypeError as e:
            r = application_codes.error_response([application_codes.WRONG_TYPE_VIOLATION])
            try:
                new_resource.delete()
            except:
                pass

        except KeyError as e:
            r = application_codes.error_response([application_codes.BAD_FORMAT_VIOLATION])
            print e
            try:
                new_resource.delete()
            except:
                pass

        except EnumeratedTypeError:
            r = application_codes.error_response([application_codes.ENUMERATED_TYPE_VIOLATION])
            try:
                new_resource.delete()
            except:
                pass

        except ParameterMissing:
            r = application_codes.error_response([application_codes.BAD_PARAMETER_VIOLATION])
            try:
                new_resource.delete()
            except:
                pass

        return r

    @classmethod
    def update_resource(cls, request_json, id):
        response = dict()
        try:
            this_resource = cls.nodes.get(id=id, active=True)
            data = request_json['data']
            if data['type'] != cls.type:
                raise WrongTypeError('type must match the type of the resource being updated.')

            attributes = data.get('attributes')
            if attributes:

                for x in attributes.keys():
                    if x in cls.dates:
                        dt = datetime.strptime(attributes[x], '%Y-%m-%d')
                        attributes[x] = dt

                this_resource.updated = datetime.now()

                this_resource.save()

                enum_keys = this_resource.enums.keys()
                for key in attributes.keys():
                    if key in enum_keys:
                        if attributes[key] in this_resource.enums[key]:
                            setattr(this_resource, key, attributes[key])
                        else:
                            raise EnumeratedTypeError
                    else:
                        setattr(this_resource, key, attributes[key])
                    this_resource.save()

                for r in this_resource.hashed:
                    unhashed = getattr(this_resource, r)
                    setattr(this_resource, r, hashlib.sha256(unhashed).hexdigest())
                    this_resource.save()

            relationships = data.get('relationships')
            if relationships:
                for relation_name in relationships.keys():
                    relations = relationships.get(relation_name)

                    for related_resource in eval('this_resource.{relation_name}.all()'.format(relation_name=relation_name)):
                        eval('this_resource.{relation_name}.disconnect(related_resource)'.
                             format(relation_name=relation_name))

                    if relations:
                        relations = relations['data']
                        if isinstance(relations, list):
                            for relation in relations:
                                the_type = relation['type']
                                the_id = relation['id']
                                the_class = cls.get_class_from_type(the_type)
                                new_resources_relation = the_class.nodes.get(id=the_id, active=True)
                                eval('this_resource.{relation_name}.connect(new_resources_relation)'.format(
                                    relation_name=relation_name)
                                )
                        else:
                            relation = relations
                            the_type = relation['type']
                            the_id = relation['id']
                            the_class = cls.get_class_from_type(the_type)
                            new_resources_relation = the_class.nodes.get(id=the_id, active=True)
                            eval('this_resource.{relation_name}.connect(new_resources_relation)'.format(
                                relation_name=relation_name)
                            )
                this_resource.updated = datetime.now()
                this_resource.save()

            response['data'] = this_resource.get_resource_object()
            response['links'] = {'self': this_resource.get_self_link()}
            status_code = http_error_codes.OK
            location = this_resource.get_self_link()
            r = make_response(jsonify(response))
            r.headers['Content-Type'] = "application/vnd.api+json; charset=utf-8"
            if location and this_resource:
                r.headers['Location'] = location
            r.status_code = status_code

        except UniqueProperty as e:
            print str(e)
            r = application_codes.error_response([application_codes.UNIQUE_KEY_VIOLATION])

        except DoesNotExist:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])

        except WrongTypeError as e:
            r = application_codes.error_response([application_codes.WRONG_TYPE_VIOLATION])

        except KeyError as e:
            r = application_codes.error_response([application_codes.BAD_FORMAT_VIOLATION])

        except EnumeratedTypeError:
            r = application_codes.error_response([application_codes.ENUMERATED_TYPE_VIOLATION])

        except ParameterMissing:
            r = application_codes.error_response([application_codes.BAD_PARAMETER_VIOLATION])

        return r

    @classmethod
    def set_resource_inactive(cls, id):
        try:
            this_resource = cls.nodes.get(id=id, active=True)
            this_resource.deactivate()
            #this_resource.active = False
            #this_resource.save()
            r = make_response('')
            r.headers['Content-Type'] = "application/vnd.api+json; charset=utf-8"
            r.status_code = http_error_codes.NO_CONTENT
        except DoesNotExist:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])

        return r

    @classmethod
    def get_relationship(cls, request_args, id, related_collection_name, related_resource=None):
        try:
            included = request_args.get('include').split(',')
        except:
            included = []
        try:
            offset = request_args.get('page[offset]', 0)
            limit = request_args.get('page[limit]', 20)
            this_resource = cls.nodes.get(id=id, active=True)
            if not related_resource:
                if request_args.get('include'):
                    r = application_codes.error_response([application_codes.PARAMETER_NOT_SUPPORTED_VIOLATION])
                else:
                    r = this_resource.relationship_collection_response(related_collection_name, offset, limit)
            else:
                r = this_resource.individual_relationship_response(related_collection_name, related_resource, included)

        except DoesNotExist:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])
        return r

    @classmethod
    def delete_relationship(cls, id, related_collection_name, related_resource=None):
        try:
            this_resource = cls.nodes.get(id=id, active=True)
            if not related_resource:
                r = this_resource.delete_relationship_collection(related_collection_name)
            else:
                r = this_resource.delete_individual_relationship(related_collection_name, related_resource)
        except DoesNotExist:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])
        return r

    @classmethod
    def get_related_resources(cls, request_args, id, related_collection_name, related_resource=None):
        try:
            included = request_args.get('include').split(',')
        except:
            included = []
        try:
            this_resource = cls.nodes.get(id=id, active=True)
            if not related_resource:
                offset = request_args.get('page[offset]', 0)
                limit = request_args.get('page[limit]', 20)
                r = this_resource.related_resources_collection_response(related_collection_name, included, offset, limit)
            else:
                r = this_resource.related_resources_individual_response(related_collection_name, related_resource, included)

        except DoesNotExist:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])

        return r

    @classmethod
    def set_related_resources_inactive(cls, id, related_collection_name, related_resource=None):
        try:
            this_resource = cls.nodes.get(id=id, active=True)
            if not related_resource:
                r = this_resource.set_related_resources_collection_inactive(related_collection_name)
            else:
                r = this_resource.set_individual_related_resource_inactive(related_collection_name, related_resource)

        except DoesNotExist:
            r = application_codes.error_response([application_codes.RESOURCE_NOT_FOUND])

        return r

    @classmethod
    def get_class_from_type(cls, the_type):
        for the_cls in cls.__base__.__subclasses__():
            if the_cls.type == the_type:
                return the_cls
        return None


class EnumeratedTypeError(Exception):
    pass





