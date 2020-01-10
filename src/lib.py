from core import *

NONE = HTSObject()
NONE.i__class__ = 'NONE'

OPERATORS = {}

# -
Minus = HTSOperator()
Minus.i__name__ = '-'


def minus_do(a: HTSObject, b: HTSObject):
    return a.i__value__ - b.i__value__


Minus.i__name__ = lambda a, b: minus_do(a, b)
OPERATORS['-'] = Minus
