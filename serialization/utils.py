from .base import SerializerMeta, SerializerAttribTrivial


# pylint: disable=redefined-builtin


def register_trivial_attrib_serializer(cls, id):
    SerializerMeta(f"Serializer{cls.__name__}", (SerializerAttribTrivial,), {"ID": id, "CLASS": cls})


def register_trivial_child_serializer(cls, id, parent_serializer):
    SerializerMeta(f"Serializer{cls.__name__}", (parent_serializer,), {"ID": id, "CLASS": cls})
