# -*- coding: utf-8 -*
"""Serialization tests."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from prismatic import serialization as s

address_serializer = s.Serializer({
    'city': s.Field('city', s.String),
    'postcode': s.Field('postcode', s.String),
    'country': s.Field('country', s.String),
})

person_serializer = s.Serializer({
    'name': s.Field('first_name', s.String),
    'surname': s.Field('last_name', s.String, nullable=True),
    'fullname': s.Callable(lambda p: '%s %s' % (p.first_name, p.last_name)),
    'email': s.Field('email_address', s.String, readonly=True),
    'registered': s.Field('registration_date', s.Date, createonly=True),
    'lastLogin': s.Field('last_login', s.DateTime),
    'dates': s.Field('dates', s.Array(s.Date)),
    'transactions': {
        'quantity': s.Field('transactions', s.Integer),
        'savings': s.Field('savings_amount', s.Decimal),
    },
    'address': s.MapField('address', address_serializer, nullable=True),
    'active': s.Field('active', s.Boolean),
})


class Person(object):
    pass


class Address(object):
    pass


def create_test_person(email=None):
    person = Person()
    person.first_name = 'Emanuel'
    person.last_name = 'Andjelic'
    person.email_address = email or 'contact@squirrel.me'
    person.registration_date = date(2014, 3, 12)
    person.last_login = datetime(2015, 3, 18, 16, 23, 8)
    person.dates = [date(2015, 3, 1), date(2015, 3, 2), date(2015, 3, 3)]
    person.transactions = 11
    person.savings_amount = Decimal(800.91)
    person.active = True

    address = Address()
    address.city = 'London'
    address.postcode = None
    address.country = 'UK'
    person.address = address

    return person


def test_serialize_should_handle_person():
    person = create_test_person()

    assert person_serializer.serialize(person) == {
        'name': 'Emanuel',
        'surname': 'Andjelic',
        'fullname': 'Emanuel Andjelic',
        'email': 'contact@squirrel.me',
        'registered': '2014-03-12',
        'lastLogin': '2015-03-18T16:23:08',
        'dates': ['2015-03-01', '2015-03-02', '2015-03-03'],
        'transactions': {
            'quantity': 11,
            'savings': 800.91,
        },
        'address': {
            'city': 'London',
            'postcode': None,
            'country': 'UK',
        },
        'active': True,
    }


def test_serialize_all_should_handle_people():
    people = [
        create_test_person('test1@squirrel.me'),
        create_test_person('test2@squirrel.me'),
        create_test_person('test3@squirrel.me'),
    ]

    serialized_people = person_serializer.serialize_all(people)

    assert len(serialized_people) == 3
    assert serialized_people[0]['email'] == 'test1@squirrel.me'
    assert serialized_people[1]['email'] == 'test2@squirrel.me'
    assert serialized_people[2]['email'] == 'test3@squirrel.me'


def test_serialize_should_raise_on_invalid_fields():
    invalid_serializer = s.Serializer({'firstName': 'bar'})
    person = create_test_person()

    with pytest.raises(TypeError):
        invalid_serializer.serialize(person)


def test_deserialize_should_handle_person():
    person = create_test_person()
    person_json = {
        'name': 'Manny',
        'surname': None,
        'registered': '2014-09-01',
        'dates': ['2015-03-18'],
        'transactions': {
            'quantity': 12,
            'savings': 1100.22,
        },
        'address': {
            'country': 'Croatia',
        },
        'active': False,
    }

    person_serializer.deserialize(person, person_json, create=True)
    assert person.first_name == 'Manny'
    assert not person.last_name
    assert person.registration_date == date(2014, 9, 1)
    assert len(person.dates) == 1
    assert person.dates[0] == date(2015, 3, 18)
    assert person.transactions == 12
    assert person.savings_amount == Decimal(1100.22)
    assert person.address.country == 'Croatia'
    assert not person.active


def test_deserialize_should_remove_nested_field():
    person = create_test_person()
    person_json = {'address': None}

    person_serializer.deserialize(person, person_json)

    assert person.address is None


def test_deserialize_should_raise_on_unknown_attributes():
    person = create_test_person()

    with pytest.raises(s.SerializationError):
        person_serializer.deserialize(person, {'unknownkey': 'Random value'})


def test_deserialize_should_raise_on_invalid_fields():
    invalid_serializer = s.Serializer({'firstName': 'bar'})
    person = create_test_person()

    with pytest.raises(TypeError):
        invalid_serializer.deserialize(person, {'firstName': 'Random value'})


def test_abstract_serializer_should_be_abstract():
    with pytest.raises(NotImplementedError):
        s.AbstractSerializer().serialize(None)
    with pytest.raises(NotImplementedError):
        s.AbstractSerializer().deserialize(None, None)


class Point:
    """Sample model for testing fields."""

    def __init__(self, x, y):
        self.x, self.y = x, y


def test_field_should_serialize_attribute():
    point = Point(x=3, y=-9)
    x_field = s.Field('x', s.Decimal, readonly=True)
    y_field = s.Field('y', s.Integer, createonly=True)
    assert x_field.serialize(point) == Decimal(3)
    assert y_field.serialize(point) == -9


def test_field_should_not_serialize_missing_attribute():
    point = Point(x=3, y=-9)
    field = s.Field('z', s.Decimal)

    with pytest.raises(AttributeError):
        assert field.serialize(point)


def test_field_should_serialize_null_attribute():
    point = Point(x=None, y=None)
    field = s.Field('x', s.String)
    assert field.serialize(point) is None


def test_field_should_deserialize_attribute():
    point = Point(x=3, y=-9)
    field = s.Field('y', s.Integer)
    field.deserialize(point, 27)
    assert point.y == 27


def test_field_should_not_deserialize_missing_attribute():
    point = Point(x=3, y=-9)
    field = s.Field('z', s.Integer)

    with pytest.raises(AttributeError):
        field.deserialize(point, 27)


def test_field_should_not_deserialize_null_when_non_nullable():
    point = Point(x=3, y=-9)
    field = s.Field('y', s.Integer, nullable=False)

    with pytest.raises(s.SerializationError):
        field.deserialize(point, None)


def test_field_should_deserialize_null():
    point = Point(x=3, y=-9)
    field = s.Field('y', s.Integer)
    field.deserialize(point, None)
    assert point.y is None


def test_field_should_not_deserialize_readonly():
    point = Point(x=3, y=-9)
    field = s.Field('y', s.Integer, readonly=True)

    # Should work if the value is not changed
    field.deserialize(point, -9)

    # Should raise otherwise
    with pytest.raises(s.SerializationError):
        field.deserialize(point, 27)


def test_field_should_not_deserialize_createonly_when_not_creating():
    point = Point(x=3, y=-9)
    field = s.Field('y', s.Integer, createonly=True)

    # Should work if the value is not changed
    field.deserialize(point, -9)

    # Should work in create mode
    field.deserialize(point, 27, create=True)
    assert point.y == 27

    # Should fail otherwise
    with pytest.raises(s.SerializationError):
        field.deserialize(point, 81)


def test_map_field_should_serialize_nested_fields():
    nested_point = Point(x=Point(x=1, y=2), y=Point(x=3, y=4))
    field = s.MapField('y', s.Serializer({
        'yx': s.Field('x', s.Integer),
        'yy': s.Field('y', s.Integer),
    }))

    assert field.serialize(nested_point) == {'yx': 3, 'yy': 4}


def test_map_field_should_serialize_nulls():
    nested_point = Point(x=None, y=None)
    field = s.MapField('y', s.Serializer({'yx': s.Field('x', s.Integer)}))

    assert field.serialize(nested_point) is None


def test_map_field_should_convert_dicts_to_serializers():
    # Implicit conversion to make the syntax nicer
    field = s.MapField('y', {'yx': s.Field('x', s.Integer)})
    assert isinstance(field.mapping, s.AbstractSerializer)


def test_map_field_should_deserialize_nested_fields():
    nested_point = Point(x=Point(x=1, y=2), y=Point(x=3, y=4))
    field = s.MapField('y', s.Serializer({
        'yx': s.Field('x', s.Integer, nullable=True),
        'yy': s.Field('y', s.Integer),
    }))

    field.deserialize(nested_point, {'yx': None, 'yy': 9})
    assert nested_point.y.x is None
    assert nested_point.y.y == 9


def test_map_field_should_raise_when_deserializing_null():
    nested_point = Point(x=Point(x=1, y=2), y=Point(x=3, y=4))
    field = s.MapField('y', s.Serializer({
        'yx': s.Field('x', s.Integer, nullable=True),
        'yy': s.Field('y', s.Integer),
    }))

    with pytest.raises(s.SerializationError):
        field.deserialize(nested_point, None)


def test_map_field_should_deserialize_null_when_nullable():
    nested_point = Point(x=Point(x=1, y=2), y=Point(x=3, y=4))
    field = s.MapField('y', s.Serializer({
        'yx': s.Field('x', s.Integer, nullable=True),
        'yy': s.Field('y', s.Integer),
    }), nullable=True)

    field.deserialize(nested_point, None)
    assert nested_point.x is not None
    assert nested_point.y is None


def test_map_field_should_raise_when_modifying_null_models():
    nested_point = Point(x=None, y=None)
    field = s.MapField('y', s.Serializer({
        'yy': s.Field('y', s.Integer),
    }))

    with pytest.raises(s.SerializationError):
        field.deserialize(nested_point, {'yy': 9})


def test_map_field_should_propagate_create_flag():
    nested_point = Point(x=Point(x=1, y=2), y=Point(x=3, y=4))
    field = s.MapField('y', s.Serializer({
        'yx': s.Field('x', s.Integer, createonly=True),
        'yy': s.Field('y', s.Integer, createonly=True),
    }))

    # Should work if the value is not changed
    field.deserialize(nested_point, {'yy': 4})

    # Should work in create mode
    field.deserialize(nested_point, {'yy': 9}, create=True)
    assert nested_point.y.y == 9

    # Should raise otherwise
    with pytest.raises(s.SerializationError):
        field.deserialize(nested_point, {'yy': 99})


def test_converter_should_be_abstract():
    with pytest.raises(NotImplementedError):
        s.Converter().model_to_json(None)
    with pytest.raises(NotImplementedError):
        s.Converter().json_to_model(None)


def test_string_should_convert_to_json():
    field = s.String()

    assert field.model_to_json('Łódź') == 'Łódź'
    assert field.model_to_json('123456789') == '123456789'
    assert field.model_to_json('') == ''


def test_string_should_convert_to_model():
    field = s.String()

    assert field.json_to_model('Łódź') == 'Łódź'
    assert field.model_to_json('123456789') == '123456789'
    assert field.json_to_model('   should trim   ') == 'should trim'


def test_string_should_reject_empty():
    field = s.String()

    with pytest.raises(s.SerializationError):
        field.json_to_model('')

    with pytest.raises(s.SerializationError):
        field.json_to_model('   ')


def test_string_should_allow_empty_when_configured():
    field = s.String(allow_empty=True)

    assert field.json_to_model('') == ''


def test_boolean_should_convert_to_json():
    field = s.Boolean()

    assert field.model_to_json(True) is True
    assert field.model_to_json(False) is False


def test_boolean_should_convert_to_model():
    field = s.Boolean()

    assert field.json_to_model(True) is True
    assert field.json_to_model(False) is False


def test_integer_should_convert_to_json():
    field = s.Integer()

    assert field.model_to_json(999999) == 999999
    assert field.model_to_json(-10.0 / 3) == -3
    assert field.model_to_json(0) == 0


def test_integer_should_convert_to_model():
    field = s.Integer()

    assert field.json_to_model(999999) == 999999
    assert field.json_to_model(-10.0 / 3) == -3
    assert field.json_to_model(0) == 0


def test_integer_should_raise_on_invalid_input():
    field = s.Integer()

    with pytest.raises(s.SerializationError):
        field.json_to_model('')

    with pytest.raises(s.SerializationError):
        field.json_to_model([])

    with pytest.raises(s.SerializationError):
        field.json_to_model('loads')


def test_decimal_should_convert_to_json():
    field = s.Decimal()

    assert field.model_to_json(Decimal('999999')) == 999999.0
    assert field.model_to_json(Decimal('-0.99')) == -0.99
    assert field.model_to_json(Decimal('0')) == 0


def test_decimal_should_convert_to_model():
    field = s.Decimal()

    assert field.json_to_model(999999.0) == Decimal('999999')
    assert field.json_to_model(-0.99) == Decimal.from_float(-0.99)
    assert field.json_to_model(0) == Decimal('0')


def test_decimal_should_raise_on_invalid_input():
    field = s.Decimal()

    with pytest.raises(s.SerializationError):
        field.json_to_model('')

    with pytest.raises(s.SerializationError):
        field.json_to_model('123.45')

    with pytest.raises(s.SerializationError):
        field.json_to_model('lots')


def test_date_should_convert_to_json():
    field = s.Date()

    assert field.model_to_json(date(2015, 1, 1)) == '2015-01-01'
    assert field.model_to_json(date(2014, 12, 31)) == '2014-12-31'
    assert field.model_to_json(date(2012, 2, 29)) == '2012-02-29'


def test_date_should_convert_to_model():
    field = s.Date()

    assert field.json_to_model('2015-01-01') == date(2015, 1, 1)
    assert field.json_to_model('2014-12-31') == date(2014, 12, 31)
    assert field.json_to_model('2012-02-29') == date(2012, 2, 29)


def test_date_should_raise_on_invalid_input():
    field = s.Date()

    with pytest.raises(s.SerializationError):
        field.json_to_model('')

    with pytest.raises(s.SerializationError):
        field.json_to_model('yesterday')

    with pytest.raises(s.SerializationError):
        # Not a leap year
        field.json_to_model('2014-02-29')


def test_date_time_should_convert_to_json():
    field = s.DateTime()

    assert field.model_to_json(datetime(2015, 1, 1, 16, 16, 37, 1)) == '2015-01-01T16:16:37'
    assert field.model_to_json(datetime(2014, 12, 31)) == '2014-12-31T00:00:00'
    assert field.model_to_json(datetime(2012, 2, 29, 23, 59, 59)) == '2012-02-29T23:59:59'


def test_date_time_should_convert_to_model():
    field = s.DateTime()

    assert field.json_to_model('2015-01-01T16:16:37.000001') == datetime(2015, 1, 1, 16, 16, 37, 1)
    assert field.json_to_model('2014-12-31T00:00:00') == datetime(2014, 12, 31)
    assert field.json_to_model('2012-02-29T23:59:59') == datetime(2012, 2, 29, 23, 59, 59)


def test_date_time_should_raise_on_invalid_input():
    field = s.DateTime()

    with pytest.raises(s.SerializationError):
        field.json_to_model('')

    with pytest.raises(s.SerializationError):
        # Not a leap year
        field.json_to_model('2014-02-29T00:00:00')

    with pytest.raises(s.SerializationError):
        # Use Date field instead
        field.json_to_model('2015-01-01')


def test_array_should_convert_to_json():
    field = s.Array(s.Date())

    assert field.model_to_json([]) == []
    assert field.model_to_json([date(2001, 1, 1)]) == ['2001-01-01']
    assert field.model_to_json([date(2002, 2, 2), date(2001, 1, 1)]) == ['2002-02-02', '2001-01-01']


def test_array_should_convert_to_model():
    field = s.Array(s.Date())

    assert field.json_to_model([]) == []
    assert field.json_to_model(['2001-01-01']) == [date(2001, 1, 1)]
    assert field.json_to_model(['2002-02-02', '2001-01-01']) == [date(2002, 2, 2), date(2001, 1, 1)]


def test_array_should_raise_on_invalid_input():
    field = s.Array(s.Date())

    with pytest.raises(s.SerializationError):
        field.json_to_model('')

    with pytest.raises(s.SerializationError):
        field.json_to_model('2014-01-01')

    with pytest.raises(s.SerializationError):
        field.json_to_model(123)


def test_callable_should_serialize():
    field = s.Callable(lambda name: 'Hello, %s!' % name)

    assert field.serialize(None) == 'Hello, None!'
    assert field.serialize('Adam') == 'Hello, Adam!'
    assert field.serialize(123) == 'Hello, 123!'


def test_callable_should_do_nothing_on_deserialize():
    field = s.Callable(None)

    # Should not touch the None model at all (would raise otherwise)
    field.deserialize(None, 'Crazy value')
