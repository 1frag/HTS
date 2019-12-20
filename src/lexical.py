import os
import sys
import re

from sty import (
    Style, RgbFg, fg
)
from pprint import pprint
from typing import List, Any
from enum import auto, Enum


def main():
    if len(sys.argv) < 2:
        fatal('Give me your file.hts')
    if not sys.argv[1].endswith('.hts'):
        fatal('Invalid extension. I can understand only *.hts files')
    if not os.path.exists(sys.argv[1]):
        fatal('File not exists')
    with open(sys.argv[1]) as file:
        do(file.read())


def do(code):
    sc = SourceCode(code)  # type: SourceCode

    def present():
        nonlocal sc
        fg.some_color = Style(RgbFg(102, 153, 204))
        print(fg.some_color)
        pprint(sc.program.as_dict())
        print(fg.some_color)

    present()


class LexicalError(Exception):
    pass


class SourceCode:

    def __init__(self, code: str):
        self.codes = [code, ]  # type: List[Any]
        self.result = {}
        self._prepare()
        self._parse_comment_and_string()
        self._parse_words()
        self.program = self._parse_brackets()
        self._assert_correct_for()
        self._assert_correct_if()

    def _prepare(self):
        try:
            ind = self.codes[0].index('{') + 13
            self.codes[0] = ';'.join([self.codes[0][:ind], self.codes[0][ind:]])
            self.codes[0] = self.codes[0].replace('}', '};')
        except ValueError:
            fatal('Not found {')

    def _parse_comment_and_string(self):
        blocks, i, bgn, code = [], 0, 0, self.codes[-1]

        def put(begin, end, type_):  # [...) like range
            nonlocal bgn, blocks, code
            colourful(code[begin:end])
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
                if ind := safe_get(code[i + 1:], '"'):
                    i = put(i, i + ind + 2, 'STR')
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
                    green_print('Comment had been ignored by lexical module', code)
                    continue
                left = 0
                for i, c in enumerate(code):
                    if c in ' \t\n':
                        if left != i:
                            yield [None, code[left:i]]
                        left = i + 1
                    elif c in '{}()-+=/*;':
                        if left != i:
                            yield [None, code[left:i]]
                        left = i + 1
                        yield [None, c]

        for info, word in gen():
            print(f'>>>{(info, word)=}')
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
                '-': Word.MINUS,
                '=': Word.EQ,
                'if': Word.IF,
                '(': Word.BR_OPEN,
                ')': Word.BR_CLOSE,
                'int': Word.INT,
                'float': Word.FLOAT,
                'str': Word.STR,
                'array': Word.ARRAY,
                'in': Word.IN,
                ';STR;': Word.CONST_STR,
            }.get(word, Word.WORD)
            if tp == Word.WORD:
                info, tp = self._specialize_word(word)
            blocks.append([info, tp])
            print(f'<<<{(info, tp)=}')
        self.codes.append(blocks)
        from pprint import pprint
        pprint(f'{self.codes[-1]}')

    @staticmethod
    def _specialize_word(word):
        """ distinguishes nums, vars """
        if num := re.match(r'^([0-9]+)(?:\.([0-9]+))?$', word):
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
                }.get(self.kind, None)

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

        for info, tp in self.codes[-1][0:]:
            print(f'{info=}, {tp=}')
            if tp == Word.BR_OPEN:
                new_item = Node('PARENTHESES', parent=cur, rebel=[info, tp])
                cur.child.append(new_item)
                cur = new_item
            elif tp == Word.SQB_OPEN:
                new_item = Node('BRACES', parent=cur, rebel=[info, tp])
                cur.child.append(new_item)
                cur = new_item
            elif tp == cur.breakpoint:
                cur = cur.parent
            else:
                new_item = Node('STATEMENT', parent=cur,
                                rebel=[info, tp])
                cur.child.append(new_item)
        if cur.kind != 'MAIN':
            raise LexicalError("todo:")
        return cur

    class AssertStructure:
        """ for assert: <SOME_WORD>(<PARENTHESES>){BRACES} e.g. <for>, <if> """
        struct_name = None

        def check_parentheses(self, nde):
            raise NotImplementedError  # this method must be override

        @staticmethod
        def check_value(nde, begin_from):
            list_of_av_for_value = map(lambda o: getattr(Word, o), [
                'BR_CLOSE', 'BR_OPEN', 'MINUS', 'PLUS',  # todo: It's true?
                'SQB_OPEN', 'SLESH', 'STAR', 'SQB_CLOSE',
            ])

            assert len(nde.child) >= begin_from
            for chi in nde.child[begin_from:]:
                if chi.info[1] not in list_of_av_for_value:
                    raise LexicalError("todo:")  # invalid type node for <value>

        def validate(self, node):
            for i, ch in enumerate(node.child):
                if ch.info[1] == self.struct_name:
                    # todo: check out of range
                    if node.child[i + 1].kind != 'PARENTHESES':
                        raise LexicalError("todo:")
                    if node.child[i + 2].kind != 'BRACES':
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
            assert True if bg == 0 else nde.child[bg-1].info[1] in list_of_types
            self_.check_value(nde, 2 + bg)

        sas = SourceCode.AssertStructure()
        sas.check_parentheses = check_parentheses
        sas.validate(self.program)

    def _assert_correct_if(self):
        sas = SourceCode.AssertStructure()
        sas.check_parentheses = lambda nde: sas.check_value(nde, 0)
        sas.validate(self.program)


class Word(Enum):
    FOR = auto()            # for
    SEMI = auto()           # ;
    STAR = auto()           # *
    SLESH = auto()          # /
    PLUS = auto()           # +
    MINUS = auto()          # -
    EQ = auto()             # =
    IF = auto()             # if
    BR_OPEN = auto()        # (
    BR_CLOSE = auto()       # )
    QW_OPEN = auto()        # [
    QW_CLOSE = auto()       # ]
    WORD = auto()           # <letter> + <letter or digit or _>*
    INT = auto()            # int
    FLOAT = auto()          # float
    STR = auto()            # str
    ARRAY = auto()          # array
    CONST_STR = auto()      # "<utf-8>*" or '<utf-8>*'
    CONST_FLOAT = auto()    # <digit>+.<digit>+
    CONST_INT = auto()      # <digit>+
    VAR_NAME = auto()       # <letter> + <letter or digit or _>*
    SQB_OPEN = auto()       # {
    SQB_CLOSE = auto()      # }
    IN = auto()             # in


def safe_get(str_: str, subs, default=None):
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


if __name__ == '__main__':
    main()
