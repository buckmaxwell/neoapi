__author__ = 'max'

from neomodel import StructuredNode


class SerializableStructuredNodeBase(StructuredNode):
    """
    Base class for SerializableStructuredNode.

    NOTE: Currently this class is rather sparse, but I am going to gradually move methods from Serializable
    Structured node into this class, so that SSN will be more of an interface that shows off the public methods.
    """
    @classmethod
    def get_collection_query(cls, request_args):
        def create_argument_dictionary(request_args):
            """
            This method takes request.args of format,
                {
                 'filter[post]':'1,2',
                 'filter[author]':'1',
                 'sort':'age,name'
                 }
            and turns it into a dictionary of the format,

                {
                 'filters': {
                             'post': ['1','2'],
                             'author': ['1']
                             },
                'sort': ['age', 'name']
                }
            """

            result = dict()
            for x in request_args.keys():
                tup = x.split('[')
                if len(tup) > 1:
                    if tup[0] not in result:
                        result[tup[0]] = dict()

                    top_level_key = result[tup[0]]
                    top_level_key[tup[1].strip(']')] = request_args[x].split(',')
                else:
                    result[tup[0]] = request_args[x].split(',')

            return result

        def create_filter_by_string(arg_dic):
            result = ''
            if 'filter' in arg_dic:
                for k in arg_dic['filter'].keys():

                    gt, gte, lt, lte, et, like= [], [], [], [], [], []
                    for item in arg_dic['filter'][k]:
                        if not len(item):  # don't bother with an empty item
                            continue
                        if item[0] == '>':
                            if item[1] == '=':
                                gte.append(item[2:])
                            else:
                                gt.append(item[1:])
                        elif item[0] == '<':
                            if item[1] == '=':
                                lte.append(item[2:])
                            else:
                                lt.append(item[1:])
                        elif item[0] == '~':
                            like.append(item[1:])
                        else:
                            et.append(item)

                    if et:
                        result += ' AND n.{k} IN {the_list}'.format(k=k, the_list=[x.encode('utf8') for x in et])
                    for gt_item in gt:
                        result += ' AND n.{k} > {gt_i}'.format(k=k, gt_i=repr(gt_item.encode('utf8')))
                    for gte_item in gte:
                        result += ' AND n.{k} >= {gte_i}'.format(k=k, gte_i=repr(gte_item.encode('utf8')))
                    for lt_item in lt:
                        result += ' AND n.{k} < {lt_i}'.format(k=k, lt_i=repr(lt_item.encode('utf8')))
                    for lte_item in lte:
                        result += 'AND n.{k} <= {lte_i}'.format(k=k, lte_i=repr(lte_item.encode('utf8')))
                    for like_item in like:
                        result += 'AND n.{k} STARTS WITH {like_i}'.format(k=k, like_i=repr(like_item.encode('utf8')))
            return result

        def create_return_string(arg_dic):
            result = 'RETURN distinct(n)'  # => default
            if 'sort' in arg_dic:
                result = 'RETURN '
                for i, x in enumerate(arg_dic['sort']):
                    if len(x.split('func(')) == 2:  # grab function if it is a function
                        the_function = x.split('func(')[1].strip(')')
                        if the_function[0] == '-':
                            result += '{fv}'.format(fv=getattr(cls, the_function[1:])['ret'])
                        else:
                            result += '{fv}'.format(fv=getattr(cls, the_function)['ret'])
                        if i != len(arg_dic['sort'])-1:
                            result += ', '
            return result

        def create_secondary_match(arg_dic):
            result = ''  # => default
            if 'sort' in arg_dic:
                for i, x in enumerate(arg_dic['sort']):
                    if len(x.split('func(')) == 2:  # grab function if it is a function
                        the_function = x.split('func(')[1].strip(')')
                        if the_function[0] == '-':
                            result += 'OPTIONAL MATCH {fv} '.format(fv=getattr(cls, the_function[1:])['match'])
                        else:
                            result += 'OPTIONAL MATCH {fv} '.format(fv=getattr(cls, the_function)['match'])
            return result

        def create_order_by_string(cls, arg_dic):
            result = ''  # default is no order by
            if 'sort' in arg_dic:
                result = 'ORDER BY '
                for i, x in enumerate(arg_dic['sort']):
                    if len(x.split('func(')) == 2:  # grab function if it is a function
                        the_function = x.split('func(')[1].strip(')')
                        if the_function[0] == '-':
                            result += '{fv} DESC'.format(fv=getattr(cls, the_function[1:])['order_by'])
                        else:
                            result += '{fv}'.format(fv=getattr(cls, the_function)['order_by'])

                    elif x[0] == '-':
                        result += 'n.{x} DESC'.format(x=x[1:])
                    else:
                        result += 'n.{x}'.format(x=x)
                    if i != len(arg_dic['sort'])-1:
                        result += ', '

            return result

        def get_offset_and_limit(arg_dic):
            o, l = 0, 20  # default
            if 'page' in arg_dic:
                o = int(arg_dic['page'].get('offset', [0])[0])
                l = int(arg_dic['page'].get('limit', [o+20])[0])

            return o, l

        arg_dic = create_argument_dictionary(request_args)
        filter_string = create_filter_by_string(arg_dic)
        order_by_string = create_order_by_string(cls, arg_dic)
        secondary_match = create_secondary_match(arg_dic)
        return_string = create_return_string(arg_dic)
        offset, limit = get_offset_and_limit(arg_dic)

        query = """
        MATCH (n) WHERE n:{label}
        AND n.active {filter_string}
        {secondary_match}
        {return_string} {order_by_string} SKIP {offset} LIMIT {limit}""".format(
            label=cls.__name__,
            offset=offset,
            limit=limit,
            secondary_match=secondary_match,
            return_string=return_string,
            filter_string=filter_string,
            order_by_string=order_by_string
        )

        return query







