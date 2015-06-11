# -*- coding: utf-8 -*
"""Serialization to and from JSON dicts.

Serialization is managed by a mapping that acts as a template:

    Serializer({
        'name': Field('first_name', String),
        'surname': Field('last_name', String, readonly=True),
        'fullname': Callable(lambda p: '%s %s' % (p.first_name, p.last_name)),
        'address': {
            'country': Field('address_country', s.String),
        }
    })

It does support nested serializers.
"""

import decimal
from datetime import datetime


class SerializationError(Exception):
    pass


class Converter(object):
    """Abstract converter between Python and JSON basic types."""

    def model_to_json(self, model_value):
        raise NotImplementedError('To be implemented in subclasses')

    def json_to_model(self, json_value):
        raise NotImplementedError('To be implemented in subclasses')


class String(Converter):
    """String conversion."""

    def __init__(self, allow_empty=False):
        super(String, self).__init__()
        self.allow_empty = allow_empty

    def model_to_json(self, model_value):
        # Same type in Python and JSON
        return str(model_value)

    def json_to_model(self, json_value):
        # Same type in Python and JSON
        model_value = str(json_value).strip()

        if self.allow_empty or len(model_value) > 0:
            return model_value
        else:
            raise SerializationError('Empty string not allowed')


class Boolean(Converter):
    """Boolean conversion."""

    def model_to_json(self, model_value):
        # Same type in Python and JSON
        return bool(model_value)

    def json_to_model(self, json_value):
        # Same type in Python and JSON
        return bool(json_value)


class Integer(Converter):
    """Integer conversion."""

    def model_to_json(self, model_value):
        # Number in JSON
        return int(model_value)

    def json_to_model(self, json_value):
        # Integer in Python
        try:
            return int(json_value)
        except (ValueError, TypeError) as e:
            raise SerializationError(e)


class Decimal(Converter):
    """Fixed point decimal conversion."""

    def model_to_json(self, model_value):
        # Number in JSON
        return float(model_value)

    def json_to_model(self, json_value):
        # Decimal in Python
        try:
            return decimal.Decimal.from_float(json_value)
        except TypeError as e:
            raise SerializationError(e)


class Date(Converter):
    """Date conversion."""

    def model_to_json(self, model_value):
        # RFC 3339 string in JSON
        return model_value.isoformat()

    def json_to_model(self, json_value):
        # datetime.date in Python
        try:
            return datetime.strptime(json_value, '%Y-%m-%d').date()
        except ValueError as e:
            raise SerializationError(e)


class DateTime(Converter):
    """Date and time conversion."""

    def model_to_json(self, model_value):
        # RFC 3339 string in JSON
        return model_value.isoformat()

    def json_to_model(self, json_value):
        # datetime.datetime in Python
        try:
            return datetime.strptime(json_value, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            # Try again without microseconds
            try:
                return datetime.strptime(json_value, '%Y-%m-%dT%H:%M:%S')
            except ValueError as e:
                raise SerializationError(e)


class Array(Converter):
    """Array conversion (immutable lists like Python tuples)."""

    def __init__(self, converter):
        # Support types from classes, instances, and callables
        if not isinstance(converter, Converter):
            converter = converter()
        self.converter = converter

    def model_to_json(self, model_values):
        return [self.converter.model_to_json(value) for value in model_values]

    def json_to_model(self, json_values):
        if isinstance(json_values, str):
            # Strings are iterable but shouldn't be accepted
            raise SerializationError('String cannot be converted to an array')

        try:
            return [self.converter.json_to_model(value) for value in json_values]
        except TypeError as e:
            raise SerializationError(e)


class AbstractSerializer(object):
    """Abstract JSON serialization class."""

    def serialize(self, model):
        raise NotImplementedError('To be implemented in subclasses')

    def deserialize(self, model, json_value, create=False):
        raise NotImplementedError('To be implemented in subclasses')

    def serialize_all(self, models):
        return [self.serialize(model) for model in models]


class Field(AbstractSerializer):
    """Serializes a model attribute using one of the basic types."""

    def __init__(self, model_attr, converter, readonly=False, createonly=False, nullable=True):
        self.model_attr = model_attr
        self.readonly = readonly
        self.createonly = createonly
        self.nullable = nullable

        # Support types from classes, instances, and callables
        if not isinstance(converter, Converter):
            converter = converter()
        self.converter = converter

    def serialize(self, model):
        model_value = getattr(model, self.model_attr)
        if model_value is not None:
            return self.converter.model_to_json(model_value)
        else:
            return None

    def deserialize(self, model, json_value, create=False):
        # Also makes sure that the attribute exists (raises otherwise)
        old_json_value = self.serialize(model)

        if self.readonly or (self.createonly and not create):
            # Compare new value with serialized old value
            if json_value != old_json_value:
                raise SerializationError(
                    "Cannot change read-only attribute '%s'" % self.model_attr)
        else:
            model_value = None
            if json_value is not None:
                model_value = self.converter.json_to_model(json_value)

            if model_value is None and not self.nullable:
                raise SerializationError(
                    "Cannot assign null to non-nullable attribute '%s'" % self.model_attr)

            setattr(model, self.model_attr, model_value)


class MapField(AbstractSerializer):
    """Serializes a model attribute as a nested object."""

    def __init__(self, model_attr, mapping, nullable=False):
        self.model_attr = model_attr
        self.nullable = nullable

        # Covert unknown mappings to Serializers
        if not isinstance(mapping, AbstractSerializer):
            mapping = Serializer(mapping)
        self.mapping = mapping

    def serialize(self, model):
        model_value = getattr(model, self.model_attr)
        if model_value is not None:
            return self.mapping.serialize(model_value)
        else:
            return None

    def deserialize(self, model, json_value, create=False):
        model_value = getattr(model, self.model_attr)

        if json_value is not None:
            if model_value is not None:
                self.mapping.deserialize(model_value, json_value, create)
            else:
                raise SerializationError(
                    "Cannot modify a null nested field '%s'" % self.model_attr)
        else:
            if self.nullable:
                setattr(model, self.model_attr, None)
            else:
                raise SerializationError(
                    "Cannot assign null to non-nullable attribute '%s'" % self.model_attr)


class Callable(AbstractSerializer):
    """Generic serialization field based on any callable."""

    def __init__(self, callable):
        self.callable = callable

    def serialize(self, model):
        return self.callable(model)

    def deserialize(self, model, json_value, create=False):
        # Not deserialized
        pass


class Serializer(AbstractSerializer):
    """Root serialization mapping."""

    def __init__(self, mapping):
        self.mapping = mapping

    def serialize(self, model):
        return self._serialize_nested(model, self.mapping)

    def _serialize_nested(self, model, mapping):
        json_obj = {}
        for key in mapping:
            if isinstance(mapping[key], AbstractSerializer):
                # Fields handle their own serialization
                json_obj[key] = mapping[key].serialize(model)
            elif isinstance(mapping[key], dict):
                # Dicts are recursive
                json_obj[key] = self._serialize_nested(model, mapping[key])
            else:
                raise TypeError("Invalid field '%s'" % key)

        return json_obj

    def deserialize(self, model, json_value, create=False):
        self._deserialize_nested(model, json_value, self.mapping, create)

    def _deserialize_nested(self, model, json_obj, mapping, create):
        unknown_keys = set(json_obj.keys()) - set(mapping.keys())
        if unknown_keys:
            raise SerializationError(
                "Properties '%s' are not valid for this resource" % ', '.join(unknown_keys))

        for key in mapping:
            if key not in json_obj:
                # Ignore missing keys for partial update
                continue

            if isinstance(mapping[key], AbstractSerializer):
                # Fields handle their own deserialization
                mapping[key].deserialize(model, json_obj[key], create=create)
            elif isinstance(mapping[key], dict):
                # Dicts are recursive
                self._deserialize_nested(model, json_obj[key], mapping[key], create)
            else:
                raise TypeError("Invalid field for '%s'" % key)
