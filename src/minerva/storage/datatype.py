# -*- coding: utf-8 -*-
"""
Defines the data types recognized by Minerva.
"""
__docformat__ = "restructuredtext en"

__copyright__ = """
Copyright (C) 2008-2015 Hendrikx-ITC B.V.

Distributed under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3, or (at your option) any later
version.  The full license is in the file COPYING, distributed as part of
this software.
"""
import re
from datetime import datetime, tzinfo
import decimal
from functools import partial, reduce
import operator

import pytz


class ParseError(Exception):
    pass


class DataType():
    @classmethod
    def string_parser_config(cls, config):
        raise NotImplementedError()

    @classmethod
    def string_parser(cls, config):
        raise NotImplementedError()

    @classmethod
    def string_serializer(cls, config):
        raise NotImplementedError()

    @classmethod
    def deduce_parser_config(cls, value):
        """
        Returns a configuration that can be used to parse the provided value
        and values like it or None if the value can not be parsed.

        :param value: A string containing a value of this type
        :return: configuration dictionary
        """
        raise NotImplementedError()


def merge_dicts(x, y):
    z = x.copy()
    z.update(y)

    return z


class DataTypeBoolean(DataType):
    name = 'boolean'

    true_set = set(["1", "True", "true"])
    false_set = set(["0", "False", "false"])
    bool_set = true_set | false_set

    default_parser_config = {
        "null_value": "\\N",
        "true_value": "true",
        "false_value": "false"
    }

    default_serializer_config = {
        "null_value": "\\N",
        "true_value": "true",
        "false_value": "false"
    }

    @classmethod
    def string_parser_config(cls, config=None):
        if config is None:
            return cls.default_parser_config
        else:
            return merge_dicts(cls.default_parser_config, config)

    @classmethod
    def string_parser(cls, config):
        null_value = config["null_value"]
        true_value = config["true_value"]
        false_value = config["false_value"]

        if hasattr(true_value, '__iter__'):
            is_true = partial(operator.contains, true_value)
        elif isinstance(true_value, str):
            is_true = partial(operator.eq, true_value)

        if hasattr(false_value, '__iter__'):
            is_false = partial(operator.contains, false_value)
        elif isinstance(false_value, str):
            is_false = partial(operator.eq, false_value)

        def parse(value):
            if value == null_value:
                return None
            elif is_true(value):
                return True
            elif is_false(value):
                return False
            else:
                raise ParseError(
                    'invalid literal for data type boolean: {}'.format(value)
                )

        return parse

    @classmethod
    def string_serializer(cls, config=None):
        if config is not None:
            config = merge_dicts(cls.default_serializer_config, config)
        else:
            config = cls.default_serializer_config

        def serialize(value):
            if value is None:
                return config['null_value']
            elif value is True:
                return config['true_value']
            else:
                return config['false_value']

        return serialize

    @classmethod
    def deduce_parser_config(cls, value):
        if not isinstance(value, str):
            return None
        elif value in cls.bool_set:
            return merge_dicts(
                cls.default_parser_config,
                {
                    "true_value": cls.true_set,
                    "false_value": cls.false_set
                }
            )


def assure_tzinfo(tz):
    if isinstance(tz, tzinfo):
        return tz
    else:
        return pytz.timezone(tz)


class DataTypeTimestampWithTimeZone(DataType):
    name = 'timestamp with time zone'

    default_parser_config = {
        "null_value": "\\N",
        "timezone": "UTC",
        "format": "%Y-%m-%dT%H:%M:%S"
    }

    @classmethod
    def string_parser_config(cls, config=None):
        if config is None:
            return cls.default_parser_config
        else:
            return merge_dicts(cls.default_parser_config, config)

    @classmethod
    def string_parser(cls, config):
        """
        Return function that can parse a string representation of a
        TimestampWithTimeZone value.

        :param config: a dictionary with the form {"timezone", <tzinfo>,
        "format", <format_string>}
        :return: a function (str_value) -> value
        """
        null_value = config["null_value"]
        tz = assure_tzinfo(config["timezone"])
        format_str = config["format"]

        def parse(value):
            if value == null_value:
                return None
            else:
                return tz.localize(datetime.strptime(value, format_str))

        return parse

    @classmethod
    def string_serializer(cls, config):
        def serialize(value):
            return str(value)

        return serialize

    @classmethod
    def deduce_parser_config(cls, value):
        if value is None:
            return cls.default_parser_config


class DataTypeTimestamp(DataType):
    name = 'timestamp'

    default_parser_config = {
        "null_value": "\\N",
        "format": "%Y-%m-%dT%H:%M:%S"
    }

    default_serializer_config = {
        "format": "%Y-%m-%dT%H:%M:%S"
    }

    known_formats = [
        (
            re.compile("^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})$"),
            "%Y-%m-%dT%H:%M:%S"
        ),
        (
            re.compile("^([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})$"),
            "%Y-%m-%d %H:%M:%S"
        )
    ]

    @classmethod
    def string_parser_config(cls, config=None):
        if config is None:
            return cls.default_parser_config
        else:
            return merge_dicts(cls.default_parser_config, config)

    @classmethod
    def string_parser(cls, config):
        def parse(value):
            if value == config["null_value"]:
                return None
            else:
                return datetime.strptime(value, config["format"])

        return parse

    @classmethod
    def string_serializer(cls, config=None):
        if config is None:
            config = cls.default_serializer_config
        else:
            config = merge_dicts(cls.default_serializer_config, config)

        datetime_format = config["format"]

        def serialize(value):
            return value.strftime(datetime_format)

        return serialize

    @classmethod
    def deduce_parser_config(cls, value):
        if not isinstance(value, str):
            return None

        for regex, datetime_format in cls.known_formats:
            match = regex.match(value)

            if match is not None:
                return merge_dicts(
                    cls.default_parser_config,
                    {'format': datetime_format}
                )


class DataTypeSmallInt(DataType):
    name = 'smallint'

    min = -pow(2, 15)
    max = pow(2, 15) - 1

    default_parser_config = {
        "null_value": "\\N"
    }

    @classmethod
    def string_parser_config(cls, config=None):
        if config is None:
            return cls.default_parser_config
        else:
            return merge_dicts(cls.default_parser_config, config)

    @classmethod
    def string_parser(cls, config):
        null_value = config["null_value"]

        def parse(value):
            if value == null_value:
                return None
            else:
                return cls._parse(value)

        return parse

    regex = re.compile("^-?[1-9][0-9]*$")

    @classmethod
    def deduce_parser_config(cls, value):
        if not isinstance(value, str):
            return None

        if value == "":
            return merge_dicts(
                cls.default_parser_config,
                {'null_value': ''}
            )

        if not cls.regex.match(value):
            return None

        try:
            int_val = int(value)
        except ValueError:
            return None
        except TypeError:
            return None
        else:
            if cls.min <= int_val <= cls.max:
                return cls.default_parser_config

    @classmethod
    def string_serializer(cls, config):
        def serialize(value):
            return str(value)

        return serialize

    @classmethod
    def _parse(cls, value):
        if not value:
            return None

        int_val = int(value)

        if not (cls.min <= int_val <= cls.max):
            raise ValueError(
                "{0:d} is not in range {1:d} - {2:d}".format(
                    int_val, cls.min, cls.max
                )
            )

        return int_val


class DataTypeInteger(DataType):
    name = 'integer'

    min = -pow(2, 31)
    max = pow(2, 31) - 1

    default_parser_config = {
        "null_value": "\\N"
    }

    @classmethod
    def string_parser_config(cls, config=None):
        if config is None:
            return cls.default_parser_config
        else:
            return merge_dicts(cls.default_parser_config, config)

    @classmethod
    def string_parser(cls, config):
        def parse(value):
            if value == config["null_value"]:
                return None
            else:
                return cls._parse(value)

        return parse

    @classmethod
    def string_serializer(cls, config):
        def serialize(value):
            return str(value)

        return serialize

    @classmethod
    def deduce_parser_config(cls, value):
        if not isinstance(value, str):
            return None

        try:
            int_val = int(value)
        except ValueError:
            return None
        except TypeError:
            return None
        else:
            if cls.min <= int_val <= cls.max:
                return cls.default_parser_config

    @classmethod
    def _parse(cls, value):
        if not value:
            return None

        int_val = int(value)

        if not (cls.min <= int_val <= cls.max):
            raise ValueError(
                "{0:d} is not in range {1:d} - {2:d}".format(
                    int_val, cls.min, cls.max
                )
            )

        return int_val


class DataTypeBigint(DataType):
    name = 'bigint'

    min = -pow(2, 63)
    max = pow(2, 63) - 1

    default_parser_config = {
        "null_value": "\\N"
    }

    @classmethod
    def string_parser_config(cls, config=None):
        if config is None:
            return cls.default_parser_config
        else:
            return merge_dicts(cls.default_parser_config, config)

    @classmethod
    def string_parser(cls, config):
        null_value = config["null_value"]

        def parse(value):
            if value == null_value:
                return None
            else:
                return DataTypeBigint.parse(value)

        return parse

    @classmethod
    def string_serializer(cls, config):
        def serialize(value):
            return str(value)

        return serialize

    @classmethod
    def deduce_parser_config(cls, value):
        if not isinstance(value, str):
            return None

        try:
            int_val = int(value)
        except (TypeError, ValueError):
            return None
        else:
            if cls.min <= int_val <= cls.max:
                return cls.default_parser_config

    @classmethod
    def parse(cls, value):
        if not value:
            return None

        int_val = int(value)

        if not (cls.min <= int_val <= cls.max):
            raise ValueError("{0:d} is not in range {1:d} - {2:d}".format(
                int_val, cls.min, cls.max))

        return int_val


class DataTypeReal(DataType):
    name = 'real'

    default_parser_config = {
        "null_value": "\\N"
    }

    @classmethod
    def string_parser_config(cls, config=None):
        if config is None:
            return cls.default_parser_config
        else:
            return merge_dicts(cls.default_parser_config, config)

    @classmethod
    def string_parser(cls, config):
        def parse(value):
            """
            Parse value and return float value. If value is empty ('') or None,
            None is returned.
            :param value: string representation of a real value, e.g.; '34.00034',
            '343', ''
            :return: float value
            """
            if value == config["null_value"]:
                return None
            else:
                return float(value)

        return parse

    @classmethod
    def string_serializer(cls, config):
        def serialize(value):
            return str(value)

        return serialize

    @classmethod
    def deduce_parser_config(cls, value):
        if not isinstance(value, str):
            return None

        try:
            float(value)
        except ValueError:
            return None
        except TypeError:
            return None
        else:
            return cls.default_parser_config


class DataTypeDoublePrecision(DataType):
    name = 'double precision'

    default_parser_config = {
        "null_value": "\\N"
    }

    @classmethod
    def string_parser_config(cls, config=None):
        if config is None:
            return cls.default_parser_config
        else:
            return merge_dicts(cls.default_parser_config, config)

    @classmethod
    def string_parser(cls, config):
        def parse(value):
            if value == config["null_value"]:
                return None
            else:
                return float(value)

        return parse

    @classmethod
    def deduce_parser_config(cls, value):
        if not isinstance(value, str):
            return None

        try:
            float(value)
        except ValueError:
            return None
        except TypeError:
            return None
        else:
            return cls.default_parser_config

    @classmethod
    def string_serializer(cls, config):
        def serialize(value):
            return str(value)

        return serialize


class DataTypeNumeric(DataType):
    name = 'numeric'

    default_parser_config = {
        "null_value": "\\N"
    }

    @classmethod
    def string_parser_config(cls, config=None):
        if config is None:
            return cls.default_parser_config
        else:
            return merge_dicts(cls.default_parser_config, config)

    @classmethod
    def string_parser(cls, config):
        is_null = partial(operator.eq, config["null_value"])

        def parse(value):
            if is_null(value):
                return None
            else:
                try:
                    return decimal.Decimal(value)
                except decimal.InvalidOperation as exc:
                    raise ParseError(str(exc))

        return parse

    @classmethod
    def string_serializer(cls, config):
        def serialize(value):
            return str(value)

        return serialize

    @classmethod
    def deduce_parser_config(cls, value):
        try:
            decimal.Decimal(value)
        except decimal.InvalidOperation:
            return None
        except ValueError:
            return None
        except TypeError:
            return None
        else:
            return cls.default_parser_config


class DataTypeText(DataType):
    name = 'text'

    default_parser_config = {
        "null_value": "\\N"
    }

    @classmethod
    def string_parser_config(cls, config=None):
        if config is None:
            return cls.default_parser_config
        else:
            return merge_dicts(cls.default_parser_config, config)

    @classmethod
    def string_parser(cls, config):
        null_value = config["null_value"]

        def parse(value):
            if value == null_value:
                return None
            else:
                return value

        return parse

    @classmethod
    def string_serializer(cls, config):
        def serialize(value):
            return str(value)

        return serialize

    @classmethod
    def deduce_parser_config(cls, value):
        return cls.default_parser_config


# The set of types that are integer
INTEGER_TYPES = {
    DataTypeBigint,
    DataTypeInteger,
    DataTypeSmallInt
}

TYPE_ORDER = [
    DataTypeSmallInt,
    DataTypeInteger,
    DataTypeBigint,
    DataTypeReal,
    DataTypeDoublePrecision,
    DataTypeNumeric,
    DataTypeTimestamp,
    DataTypeText
]


TYPE_ORDER_RANKS = dict(
    (data_type, i)
    for i, data_type in enumerate(TYPE_ORDER)
)


def max_data_type(left, right):
    if TYPE_ORDER_RANKS[right] > TYPE_ORDER_RANKS[left]:
        return right
    else:
        return left


def max_data_types(current_data_types, new_data_types):
    return [
        max_data_type(current_data_type, new_data_type)
        for current_data_type, new_data_type
        in zip(current_data_types, new_data_types)
    ]


ORDERED_MATCH_FUNCS = [
    (data_type, data_type.deduce_parser_config)
    for data_type in TYPE_ORDER
]


class ParserDescriptor():
    def __init__(self, data_type, parser_config):
        self.data_type = data_type
        self.parser_config = parser_config

    def parser(self):
        return self.data_type.string_parser(self.parser_config)


def parser_descriptor_from_string(value):
    for data_type, deduce_parse_config in ORDERED_MATCH_FUNCS:
        parse_config = deduce_parse_config(value)

        if parse_config is not None:
            return ParserDescriptor(data_type, parse_config)

    raise ValueError("Unable to determine data type of: {0}".format(value))


all_data_types = [
    DataTypeBigint,
    DataTypeBoolean,
    DataTypeTimestamp,
    DataTypeTimestampWithTimeZone,
    DataTypeInteger,
    DataTypeSmallInt,
    DataTypeReal,
    DataTypeDoublePrecision,
    DataTypeNumeric,
    DataTypeText
]


type_map = {d.name: d for d in all_data_types}


def deduce_data_types(rows):
    """
    Return a list of the minimal required data types to store the values, in the
    same order as the values and thus matching the order of attribute_names.

    :rtype: collections.iterable[DataType]
    """
    return reduce(
        max_data_types,
        [
            [
                parser_descriptor_from_string(value).data_type
                for value in row
            ]
            for row in rows
        ]
    )


def load_data_format(format):
    data_type_name = format["datatype"]

    try:
        data_type = type_map[data_type_name]
    except KeyError:
        raise Exception("No such data type: {}".format(data_type_name))
    else:
        config = data_type.string_parser_config(format["string_format"])

        return data_type, data_type.string_parser(config)


copy_from_serializer_config = {
    DataTypeBigint: {
        'null_value': '\\N'
    },
    DataTypeBoolean: {
        'null_value': '\\N'
    },
    DataTypeTimestamp: {
        'null_value': '\\N'
    },
    DataTypeTimestampWithTimeZone: {
        'null_value': '\\N'
    },
    DataTypeInteger: {
        'null_value': '\\N'
    },
    DataTypeSmallInt: {
        'null_value': '\\N'
    },
    DataTypeReal: {
        'null_value': '\\N'
    },
    DataTypeDoublePrecision: {
        'null_value': '\\N'
    },
    DataTypeNumeric: {
        'null_value': '\\N'
    },
    DataTypeText: {
        'null_value': '\\N'
    }
}
