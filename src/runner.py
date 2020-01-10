from enum import Enum, auto
from typing import Optional, Union, List
from copy import deepcopy

from lib import *
from core import *

# лень бросать эксепшен я просто верну эту чертовшину
THE_END_OF_PROGRAM = '5rtfgvdhjajdyva wmnmovudyglaw'


class Node:
    def __init__(self, dct: Union[dict, list], is_empty=False):
        self.next, self.parent = None, None
        if is_empty:
            return
        if isinstance(dct, list):
            self.type = 'KEYWORD'
            self.value = dct[0]
            self.ktype = dct[1]
            return
        for k, v in dct.items():
            setattr(self, k, v)
        if isinstance(dct.get('cmds'), list):
            cmds_nodes = list(map(lambda x: Node(x), dct['cmds']))
            self.first_child = cmds_nodes[0]
            for i in range(len(cmds_nodes) - 1):
                cmds_nodes[i].parent = self
                cmds_nodes[i].next = cmds_nodes[i + 1]
        if isinstance(dct.get('body'), list):
            body_nodes = list(map(lambda x: Node(x), dct['body']))
            self.first_child = body_nodes[0]
            for i in range(len(body_nodes) - 1):
                body_nodes[i].parent = self
                body_nodes[i].next = body_nodes[i + 1]

    def like_object(self):
        print(self.__dict__)
        if self.ktype.startswith('const_'):
            o = HTSObject()
            o.i__class__ = self.ktype.replace('const_', '')
            o.i__value__ = self.value
            if self.ktype == 'const_bool':
                if self.value in ['true', 'True']:
                    o.i__value__ = True
                else:
                    o.i__value__ = False
            return o
        raise RuntimeError()

    def safe_next(self):
        if hasattr(self, 'first_child'):
            return self.first_child
        if self.parent is None:
            raise Exception('Моя ошибка в какой то момент '
                            'не проставил пэранта новосозданной ноде')
        if self.next is None:
            if self.parent.next is None:
                return THE_END_OF_PROGRAM
            return self.parent.nexr
        return self.next


class RunTime:
    table_with_vars = {}

    def run(self, program: dict):
        """ Получили структурированный json начинается работа в рантайме """
        main = Node(program)
        now: Node = main
        while now is not None:
            if getattr(now, 'type') == 'DECL_VAR':
                this_var = Variable(
                    name=getattr(now, 'name'),
                    deep=getattr(now, 'deep'),
                    last_type={
                        'str': LatestType.STR,
                        'int': LatestType.INT,
                        'bool': LatestType.BOOL,
                        'float': LatestType.FLOAT,
                    }[getattr(now, 'end')],
                )
                self.table_with_vars[getattr(now, 'name')] = this_var
                now = now.safe_next()
            elif getattr(now, 'type') == 'calculation_tree':
                self.exec(now)
                now = now.safe_next()
            elif getattr(now, 'type') == 'SCOPE{}':
                now = now.safe_next()

    def exec(self, line: Node):
        """ Работа со типом calculation_tree """

        def apply(obj_: Optional[HTSObject], attachment: Union[Node, HTSObject]) -> HTSObject:
            if obj_ is None:
                return attachment.like_object()
            if getattr(attachment, 'ktype', None) in '-+%/*':
                setattr(obj_, 'with_op', getattr(attachment, 'ktype'))
                return obj_
            if not hasattr(attachment, 'with_op'):
                print(attachment.__dict__, obj_.i__class__)
                raise RuntimeError('Нужен оператор а так получается object от object(а)')
            op = getattr(attachment, 'with_op')
            obj_ = {
                '+': lambda a, b: a + b,
                '-': lambda a, b: a - b,
                '*': lambda a, b: a * b,
                '/': lambda a, b: a / b,
                '%': lambda a, b: a % b,
            }[op](obj_,
                  attachment if isinstance(attachment, HTSObject) else attachment.like_object())
            return obj_

        def list_to_node(lst: list):
            n = Node({}, is_empty=True)
            n.first_child = lst[0]
            nlst: List[Node] = list(map(lambda x: Node(x), lst))
            for m in range(len(lst) - 1):
                nlst[m].parent = n
                nlst[m].next = nlst[m + 1]
            return n

        def init_list(node):
            """ Парсинг + Выполнение кода вида [a, b, ...] """
            result_ = []
            now_ = node.first_child
            while now_ is not None:
                if getattr(now_, 'ktype', None) == ',':
                    result_.append([])
                else:
                    result_[-1].append(deepcopy(now_))
                now_ = now_.next
            for lst in result_:
                n = Node({}, is_empty=True)
                n.first_child = lst[0]
                for m in range(len(lst) - 1):
                    lst[m].parent = node
                    lst[m].next = lst[m + 1]
                yield self.exec(n)

        result = None
        now = line.first_child
        if getattr(now, 'ktype', None) == '-':
            now = Node({}, is_empty=True)
            now.next = line.first_child
            now.value = NONE
        while now is not None:
            print('BEGIN')
            if getattr(now, 'type') == 'SCOPE()':
                print('1')
                obj = self.exec(now)
            elif getattr(now, 'type') == 'SCOPE[]':
                print('2')
                obj = list(init_list(now))
            elif getattr(now, 'type') == 'STATEMENT':
                print('3')
                obj = list_to_node(now.body)
            else:
                print('4')
                obj = now
            now = now.safe_next()
            print('END')
            result = apply(result, obj)
        return result


class LatestType(Enum):
    STR = auto()
    INT = auto()
    FLOAT = auto()
    BOOL = auto()


class Variable:
    def __init__(self, name: str, deep: int, last_type: LatestType):
        self.name = name
        self.deep = deep
        self.last_type = last_type
