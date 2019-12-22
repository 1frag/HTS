import os
import sys
import re

from sty import (
    Style, RgbFg, fg
)
from pprint import pprint
from typing import List, Any, Union
from enum import auto, Enum
from queue import Queue


def do(code, to_runner, to_lexical, with_running=True):
    def present():
        nonlocal sc
        fg.some_color = Style(RgbFg(102, 153, 204))
        print(fg.some_color)
        from json import dumps
        print(dumps(eval(str(sc.program))))
        print(fg.rs)

    try:
        to_runner.put_nowait(('START',))
        sc = SourceCode(code)  # type: SourceCode
        if with_running:
            sc.present(to_runner, to_lexical)  # запустить код
        else:
            present()  # показать обработанные данные
    finally:
        to_runner.put_nowait(('END',))


class LexicalError(Exception):
    pass


class SourceCode:

    def __init__(self, code: str):
        self.codes = [code, ]  # type: List[Any]
        self._prepare()
        self._parse_comment_and_string()
        self._parse_words()
        self.program = self._parse_brackets()
        self._assert_correct_for()
        self._assert_correct_if()
        self._get_specific_statements()
        self._get_other_statements()

    def _get_other_statements(self):
        def decl_var(lst):
            if len(lst) < 2:
                raise LexicalError('Ожидалось имя переменной')
            name = lst[-1][0]
            lst[-1:] = []
            _ctp = [Word.INT, Word.STR, Word.FLOAT, Word.BOOL]
            if lst[-1][1] not in [Word.INT, Word.STR, Word.FLOAT, Word.BOOL]:
                raise LexicalError(f'Невалидный тип {lst[-1][1]} '
                                   f'должен быть один из {_ctp}')
            for it in lst[:-1]:
                if it[1] != Word.ARRAY:
                    raise LexicalError(f'Промежуточный тип не может быть {it[1]}')
            return {
                'type': 'DECL_VAR',
                'name': name,
                'atype': {
                    'deep': len(lst) - 1,  # количество array до хранимого типа
                    'end': lst[-1][1],  # тот самый последний хранимый тип
                }
            }

        def apply_var(lst):
            if lst[0][1] != Word.VAR_NAME:
                raise LexicalError(f'Недопустимое слово, '
                                   f'ожидалось имя переменной')
            if lst[1][1] != Word.APPLY:
                raise LexicalError('Недопустимое слово, ожидалось =')
            return {
                'type': 'APPLY_VAR',
                'for_what': lst[0][0],
                'value': eval_value(lst[2:]),
            }

        def eval_value(lst):
            return {
                'type': 'calculation_tree',
                'cmds': CalculationTree(lst),
            }

        def which(lst):
            """ Отличает:   декларацию переменной (есть type Word)
                            присваивание переменной значение (есть APPLY Word)
                            значение (остальное)
            """
            word_types = [Word.INT, Word.FLOAT, Word.STR, Word.ARRAY]
            candidates = [False, False, True]
            for nde in lst:
                if isinstance(nde, dict):
                    continue  # it is value
                if nde[1] == Word.APPLY:
                    candidates[::2] = True, False
                if nde[1] in word_types:
                    candidates[1::] = True, False
            if candidates.count(True) != 1:
                raise LexicalError('Неоднозначное выражение')
            ind = candidates.index(True)
            colourful(lst, ind, candidates)
            return [apply_var, decl_var, eval_value][ind](lst)

        def inner(node):
            if node['type'] == 'STATEMENT':
                new_item = which(node['body'])
                node.clear()
                node.update(new_item)
            else:
                colourful(node['type'])
                for ch in node['body']:
                    inner(ch)

            if node['type'] == 'FOR':
                node['using_var'] = decl_var(node['using_var'])
                node['iter_obj'] = eval_value(node['iter_obj'])
            elif node['type'] == 'IF':
                node['condition'] = eval_value(node['condition'])

        inner(self.program)

    def _get_specific_statements(self):

        def cleanup(lst):
            for item in lst:
                if isinstance(item, list) and item[1] == Word.SEMI:
                    pass
                else:
                    yield item

        def parse_br_in_for(node):
            colourful(node)
            for ind, elem in enumerate(node['body']):
                if elem[1] == Word.IN:
                    return node['body'][:ind], node['body'][ind + 1:]
            raise LexicalError('For must contains word `in`')

        def inner(node):
            if node.info[1] in [Word.QW_OPEN, Word.SQB_OPEN, Word.BR_OPEN]:
                for k in range(len(node.child)):
                    node.child[k] = inner(node.child[k])
                ind = 0
                while ind < len(node.child):
                    if isinstance(node.child[ind], dict):
                        # бывший фор или иф, - пролетает
                        ind += 1
                        continue
                    if node.child[ind][1] == Word.FOR:
                        using_var, iter_obj = parse_br_in_for(node.child[ind + 1]['body'][0])
                        node.child[ind] = {  # rewrite `for`-node
                            'type': 'FOR',
                            'using_var': using_var,
                            'iter_obj': iter_obj,
                            'body': node.child[ind + 2]['body'],
                        }
                        for _ in range(2):  # remove () and {}
                            del node.child[ind + 1]
                    elif node.child[ind][1] == Word.IF:
                        node.child[ind] = {  # rewrite `if`-node
                            'type': 'IF',
                            'condition': node.child[ind + 1]['body'],
                            'body': node.child[ind + 2]['body'],
                        }
                        for _ in range(2):  # remove () and {}
                            del node.child[ind + 1]
                    else:
                        make, j = [node.child[ind], ], ind + 1
                        print(node.child)
                        while j < len(node.child):
                            make.append(node.child[j])
                            cp = node.child[j]
                            del node.child[j]
                            if not isinstance(cp, list):
                                continue
                            if cp[1] == Word.SEMI:
                                break

                        node.child[ind] = {
                            'type': 'STATEMENT',
                            'body': list(cleanup(make)),
                        }
                # ind += 1
                return {
                    'type': {
                        Word.BR_OPEN: 'SCOPE()',
                        Word.SQB_OPEN: 'SCOPE{}',
                        Word.QW_OPEN: 'SCOPE[]',
                    }[node.info[1]],
                    'body': node.child,
                }
            else:
                return node.info

        self.program = inner(self.program)

    def present(self, to_runner: Queue, to_lexical: Queue):  # top-level function
        def _present(node):  # recursive method
            if not node.child:
                pass
            else:
                for nd in node.child:
                    _present(nd)

        to_runner.put_nowait(('START',))
        _present(self.program)
        to_runner.put_nowait(('END',))

    def _prepare(self):
        self.codes[0] = self.codes[0].replace('{', '{;')
        self.codes[0] = self.codes[0].replace('}', '};')
        self.codes[0] = self.codes[0].replace('[', ' [ ')
        self.codes[0] = self.codes[0].replace(']', ' ] ')

    def _parse_comment_and_string(self):
        blocks, i, bgn, code = [], 0, 0, self.codes[-1]

        def put(begin, end, type_):  # [...) like range
            nonlocal bgn, blocks, code
            blocks.append((code[bgn:begin], 'CODE'))
            blocks.append((code[begin:end], type_))
            bgn = end
            return end + 1

        while i < len(code):
            if code[i] == '~':
                if code[i:i + 3] == '~~~':
                    if '~~~' not in code[i + 3:]:
                        raise LexicalError("todo:")
                    else:
                        j = i + 6 + code[i + 3:].index('~~~')
                        i = put(i, j, 'COMMENT')
                else:
                    t = safe_get(code[i + 1:], '~', -1)
                    n = safe_get(code[i + 1:], '\n', t + 1)
                    if n > t:
                        i = put(i, i + t + 2, 'COMMENT')
                    else:
                        raise LexicalError("todo:")
            elif code[i] == '"':
                colourful(f'{code[i+1:]=}')
                if '"' in code[i + 1:]:
                    i = put(i, i + code[i + 1:].index('"') + 2, 'STR')
                else:
                    raise LexicalError("todo:")
            elif code[i] == "'":
                t = safe_get(code[i + 1:], "'", -1)
                n = safe_get(code[i + 1:], '\n', t + 1)
                if n > t:
                    i = put(i, i + t + 2, 'STR')
                else:
                    raise LexicalError("todo:")
            else:
                i += 1
        blocks.append((code[bgn:], 'CODE'))
        self.codes.append(blocks)

    def _parse_words(self):
        orig_code = self.codes[-1]  # type: str
        blocks = list()

        def gen():
            nonlocal orig_code
            for code, tp_ in orig_code:
                if tp_ == 'STR':
                    yield [code, ';STR;']
                    continue
                if tp_ == 'COMMENT':
                    continue
                left = 0
                for i, c in enumerate(code):
                    if c in ' \t\n':
                        if left != i:
                            yield [None, code[left:i]]
                        left = i + 1
                    elif code[i:i + 2] == '==':
                        continue
                    elif code[i - 1:i + 1] == '==':
                        left = i + 1
                        yield [None, '==']
                    elif c in '{}()-+/*=;,':
                        if left != i:
                            yield [None, code[left:i]]
                        left = i + 1
                        yield [None, c]

        for info, word in gen():
            if word == '':
                continue
            tp = {
                'for': Word.FOR,
                ';': Word.SEMI,
                '*': Word.STAR,
                '/': Word.SLESH,
                '[': Word.QW_OPEN,
                ']': Word.QW_CLOSE,
                '{': Word.SQB_OPEN,
                '}': Word.SQB_CLOSE,
                '+': Word.PLUS,
                ',': Word.COMMA,
                '-': Word.MINUS,
                '==': Word.EQ,
                '=': Word.APPLY,
                'if': Word.IF,
                '(': Word.BR_OPEN,
                ')': Word.BR_CLOSE,
                'int': Word.INT,
                'float': Word.FLOAT,
                'bool': Word.BOOL,
                'str': Word.STR,
                'array': Word.ARRAY,
                'in': Word.IN,
                ';STR;': Word.CONST_STR,
            }.get(word, Word.WORD)
            if tp == Word.WORD:
                info, tp = self._specialize_word(word)
            blocks.append([info, tp])
        self.codes.append(blocks)

    @staticmethod
    def _specialize_word(word: str):
        """ distinguishes nums, vars """
        if word in ['true', 'false', 'True', 'False']:
            return word.lower(), Word.CONST_BOOL
        elif num := re.match(r'^([0-9]+)(?:\.([0-9]+))?$', word):
            if num.group(2):
                return float(word), Word.CONST_FLOAT
            return int(word), Word.CONST_INT
        elif re.match(r'^[a-zA-Z][a-z_A-Z0-9]*$', word):
            return str(word), Word.VAR_NAME
        green_print(word, f'"{word=}"')
        raise LexicalError("todo:")

    def _parse_brackets(self):
        """ distinguishes {BRACES} and (PARENTHESES) """

        class Node:
            def __init__(self, kind, rebel, *, parent=None):
                self.parent = parent
                self.child = []
                self.kind = kind
                self.info = rebel

            @property
            def breakpoint(self):
                return {
                    'PARENTHESES': Word.BR_CLOSE,
                    'BRACES': Word.SQB_CLOSE,
                    'QUADROB': Word.QW_CLOSE,
                }.get(self.kind, None)

            def __repr__(self):
                return f'Node({self.kind=}, {self.info=})'

            def as_dict(self):
                for_child = []
                for ch in self.child:
                    for_child.append(ch.as_dict())
                return {
                    'type': self.kind,
                    'comm': for_child,
                    'info': self.info,
                }

        cur = Node('MAIN', rebel=[None, Word.SQB_OPEN])

        for info, tp in self.codes[-1]:
            if tp == Word.BR_OPEN:
                new_item = Node('PARENTHESES', parent=cur, rebel=[info, tp])
                cur.child.append(new_item)
                cur = new_item
            elif tp == Word.SQB_OPEN:
                new_item = Node('BRACES', parent=cur, rebel=[info, tp])
                cur.child.append(new_item)
                cur = new_item
            elif tp == Word.QW_OPEN:
                new_item = Node('QUADROB', parent=cur, rebel=[info, tp])
                cur.child.append(new_item)
                cur = new_item
            elif tp == cur.breakpoint:
                cur = cur.parent
            else:
                new_item = Node('STATEMENT' if tp != Word.SEMI else ';', parent=cur,
                                rebel=[info, tp])
                cur.child.append(new_item)
        if cur.kind != 'MAIN':
            raise LexicalError("todo:")
        return cur

    class AssertStructure:
        """ for assert: <SOME_WORD>(<PARENTHESES>){BRACES} e.g. <for>, <if> """
        struct_name = None

        def __init__(self, sn):
            self.struct_name = sn

        def check_parentheses(self, nde):
            raise NotImplementedError  # this method must be override

        @staticmethod
        def check_value(nde, begin_from):
            list_of_av_for_value = list(map(lambda o: getattr(Word, o), [
                'BR_CLOSE', 'BR_OPEN', 'MINUS', 'PLUS', 'VAR_NAME', 'CONST_INT',
                'SQB_OPEN', 'SLESH', 'STAR', 'SQB_CLOSE', 'CONST_STR', 'EQ',
            ]))  # todo: It's true?

            assert len(nde.child) >= begin_from
            for chi in nde.child[begin_from:]:
                if chi.info[1] not in list_of_av_for_value:
                    pprint(f'{chi.info[1]=} not in {list_of_av_for_value=}')
                    pprint(list(map(lambda x: x.info, nde.child[begin_from:])))
                    raise LexicalError("todo:")  # invalid type node for <value>

        def validate(self, node):
            for i, ch in enumerate(node.child):
                if ch.info[1] == self.struct_name:
                    try:
                        if node.child[i - 1].kind != ';':
                            raise LexicalError("todo:")
                        if node.child[i + 1].kind != 'PARENTHESES':
                            raise LexicalError("todo:")
                        if node.child[i + 2].kind != 'BRACES':
                            raise LexicalError("todo:")
                        if node.child[i + 3].kind != ';':
                            raise LexicalError("todo:")
                    except IndexError:
                        raise LexicalError("todo:")
                    self.check_parentheses(node.child[i + 1])

            for ch in node.child:
                self.validate(ch)

    def _assert_correct_for(self):
        def check_parentheses(self_, nde):
            """  True if child like
            <TYPE>  <NAME> in <VALUE>  ~or~
                    <NAME> in <VALUE>"""
            list_of_types = [
                Word.INT, Word.FLOAT, Word.STR, Word.ARRAY,
                # todo: check my remarkable memory
            ]
            list_of_av_for_value = map(lambda o: getattr(Word, o), [
                'BR_CLOSE', 'BR_OPEN', 'MINUS', 'PLUS',  # todo: It's true?
                'SQB_OPEN', 'SLESH', 'STAR', 'SQB_CLOSE',
            ])

            # todo: change assert to raise LexicalError

            if nde.child[2].info[1] == Word.IN:
                bg = 1
            elif nde.child[1].info[1] == Word.IN:
                bg = 0
            else:
                raise LexicalError("todo: in for expected in on 1"
                                   " or 2 place but is's absent")

            assert nde.child[bg].info[1] == Word.VAR_NAME
            assert True if bg == 0 else nde.child[bg - 1].info[1] in list_of_types
            self_.check_value(nde, 2 + bg)

        sas = SourceCode.AssertStructure(Word.FOR)
        sas.check_parentheses = lambda nde: check_parentheses(sas, nde)
        sas.validate(self.program)

    def _assert_correct_if(self):
        sas = SourceCode.AssertStructure(Word.IF)
        sas.check_parentheses = lambda nde: sas.check_value(nde, 0)
        sas.validate(self.program)


class CalculationTree:
    class Node:
        def __init__(self, value=None):
            self.value = value
            self.children = None
            self.next_node = None
            self.across_op = None
            self.params = None

    def __init__(self, cmds):
        if len(cmds) == 0:
            raise LexicalError('Пустое выражение')
        self.cmds = cmds
        self.start_node = CalculationTree.Node()
        self.make_nodes()

    def make_nodes(self):
        def create_node(cur):
            """ Создает корректный Node в зависимости от типа cur """
            if isinstance(cur, dict) and cur['type'] == 'SCOPE()':
                new_node = CalculationTree.Node()
                assert cur['body'][0] == 'STATEMENT'
                inner(cur['body'][0]['body'], new_node)
                return new_node
            else:
                assert isinstance(cur, list)
                assert len(cur) == 2
                assert cur[1] in [Word.CONST_FLOAT, Word.CONST_STR,
                                  Word.CONST_INT, Word.CONST_BOOL,
                                  Word.VAR_NAME]
                # todo: возможно необходио передавать и cur[1]
                return CalculationTree.Node(cur[0])

        def as_params(cur: CalculationTree.Node, next_node: CalculationTree.Node):
            """ В случае если next_node скобки тогда доопределяет cur
            для вызова с этими параметрами
            """
            if not (isinstance(next_node, dict) and
                    next_node['type'] == 'SCOPE()'):
                return False
            cur.params = next_node  # todo: parse params
            return True

        def as_operator(cur: CalculationTree.Node, next_node: CalculationTree.Node):
            assert isinstance(next_node, list)
            assert len(next_node) == 2
            assert next_node[1] in [Word.PLUS, Word.MINUS, Word.STAR, Word.SLESH]
            cur.across_op = next_node[1]

        def inner(child: list, parent: CalculationTree.Node):
            parent.children = child[0]
            ind = 0
            while ind < len(child):
                new_node = create_node(child[ind])
                if ind:
                    child[ind - 1].next = new_node
                if (len(child) > ind + 1) and as_params(new_node, child[ind + 1]):
                    ind += 1
                if len(child) > ind + 1:
                    as_operator(new_node, child[ind + 1])
                ind += 2

        inner(self.cmds[0], self.start_node)


class Word(Enum):
    def __repr__(self):
        return f'"{self.value}"'

    FOR = 'for'
    SEMI = ';'
    STAR = '*'
    SLESH = '/'
    PLUS = '+'
    MINUS = '-'
    EQ = '=='
    IF = 'if'
    COMMA = ','
    BR_OPEN = '('
    BR_CLOSE = ')'
    APPLY = '='
    QW_OPEN = '['
    QW_CLOSE = ']'
    WORD = '_word'  # @deprecated
    INT = 'int'
    FLOAT = 'float'
    BOOL = 'bool'
    STR = 'str'
    ARRAY = 'array'
    CONST_BOOL = 'some_bool'
    CONST_STR = 'const_str'
    CONST_FLOAT = 'const_float'
    CONST_INT = 'const_int'
    VAR_NAME = 'var_name'
    SQB_OPEN = '{'
    SQB_CLOSE = '}'
    IN = 'in'


def safe_get(str_: Union[str, list], subs: Any, default=None):
    # todo: add in str
    try:
        return str_.index(subs)
    except ValueError:
        return default


# todo: We need better debug functions that those:
def fatal(message):
    fg.orange = Style(RgbFg(255, 150, 50))
    print(''.join([fg.orange, message, fg.rs]))
    sys.exit(1)


def green_print(*args):
    fg.orange = Style(RgbFg(0, 255, 0))
    print(fg.orange, *args, fg.rs)


def colourful(*args):
    fg.orange = Style(RgbFg(152, 150, 50))
    print(fg.orange, *args, fg.rs)
