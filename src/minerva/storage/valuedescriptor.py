from minerva.storage.datatype import all_data_types


class ValueDescriptor:
    name_to_data_type = {d.name: d for d in all_data_types}

    def __init__(
            self, name, data_type, parser_config=None, serializer_config=None):
        self.name = name
        self.data_type = data_type
        self.parser_config = parser_config
        self.serializer_config = serializer_config

        self.parse_string = data_type.string_parser(
            data_type.string_parser_config(parser_config)
        )

        self.serialize_to_string = data_type.string_serializer(
            serializer_config
        )

    def parse(self, value):
        return self.parse_string(value)

    def serialize(self, value):
        return self.serialize_to_string(value)

    def to_config(self):
        return {
            'name': self.name,
            'data_type': self.data_type.name,
            'parser_config': self.parser_config,
            'serializer_config': self.serializer_config
        }

    @staticmethod
    def load_from_config(config):
        return ValueDescriptor(
            config['name'],
            ValueDescriptor.name_to_data_type[config['data_type']],
            config.get('parser_config'),
            config.get('serializer_config')
        )