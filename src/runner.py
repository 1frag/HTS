from queue import Queue
from threading import Thread


class Runner(Thread):
    def __init__(self, to_runner: Queue, to_lexical: Queue):
        super().__init__()
        self.to_runner = to_runner
        self.to_lexical = to_lexical
        self.__storage = {}

    def run(self):
        """ Слушатель очереди (==Интерпретатор)
            Понимает команды:
                ('START'),
                ('SET', <str>, <Object>),
                ('EVAL', <Object>, <Operator>, <Object>),
                ('EVAL', <Operator>, <Object>),
                ('END'),
        """
        while True:
            cmd = self.to_runner.get(True)
            if cmd[0] == 'SET':
                self.set(*cmd[1:])
            elif cmd[0] == 'EVAL' and len(cmd) == 4:
                self.eval2(*cmd[1:])
            elif cmd[0] == 'EVAL' and len(cmd) == 3:
                self.eval1(*cmd[1:])
            elif cmd[0] == 'START':
                print('Ok! Program started')
            elif cmd[0] == 'END':
                return print('Bue!')

    def set(self, obj1: str, obj2):
        self.__storage[obj1] = obj2
        self.to_lexical.put_nowait('DONE')

    def eval2(self, obj1, op, obj2):
        self.to_lexical.put_nowait(map_ops2.get(op)(obj1, obj2))

    def eval1(self, op, obj1):
        self.to_lexical.put_nowait(map_ops1.get(op)(obj1))


map_ops1 = map_ops2 = {}
