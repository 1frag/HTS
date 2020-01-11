from enum import Enum, auto


class LatestType(Enum):
    STR = auto()
    INT = auto()
    FLOAT = auto()
    BOOL = auto()


class HTSObject:
    i__class__ = None
    i__value__ = None

    with_op = None
    with_fun = None
    ktype = None

    def __sub__(self, other):
        r = HTSObject()
        if self.i__class__ != self.i__class__:
            raise NotImplementedError("Язык не поддерживает вычитание "
                                      "между объектами разных классов")
        r.i__value__ = self.i__value__ - other.i__value__
        r.i__class__ = self.i__class__
        return r

    def __add__(self, other):
        r = HTSObject()
        if self.i__class__ != self.i__class__:
            raise NotImplementedError("Язык не поддерживает сложение "
                                      "между объектами разных классов")
        r.i__value__ = self.i__value__ + other.i__value__
        r.i__class__ = self.i__class__
        return r

    def __mul__(self, other):
        r = HTSObject()
        if self.i__class__ != self.i__class__:
            raise NotImplementedError("Язык не поддерживает умножение "
                                      "между объектами разных классов")
        r.i__value__ = self.i__value__ * other.i__value__
        r.i__class__ = self.i__class__
        return r

    def __idiv__(self, other):
        r = HTSObject()
        if self.i__class__ != self.i__class__:
            raise NotImplementedError("Язык не поддерживает деление "
                                      "между объектами разных классов")
        r.i__value__ = self.i__value__ / other.i__value__
        r.i__class__ = self.i__class__
        return r

    def __imod__(self, other):
        r = HTSObject()
        if self.i__class__ != self.i__class__:
            raise NotImplementedError("Язык не поддерживает `%` "
                                      "между объектами разных классов")
        r.i__value__ = self.i__value__ % other.i__value__
        r.i__class__ = self.i__class__
        return r

    def __and__(self, other):
        if isinstance(self.i__value__, list):
            self.i__value__.append(other)
        else:
            self.i__value__ = [self.i__value__, other]


class HTSOperator:
    i__name__ = None
    i__do__ = None


def box():
    def i__max():
        r = HTSObject()
        r.i__class__ = 'fun'
        r.i__value__ = 'qwertyuio'
        return r

    return {
        'max': i__max(),
    }
