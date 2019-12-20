import sys
import os
from queue import Queue

from runner import Runner
from lexical import do, fatal


def main():
    with_running = int(sys.argv[2] if len(sys.argv) > 2 else True)
    if len(sys.argv) < 2:
        fatal('Give me your file.hts')
    if not sys.argv[1].endswith('.hts'):
        fatal('Invalid extension. I can understand only *.hts files')
    if not os.path.exists(sys.argv[1]):
        fatal('File not exists')
    with open(sys.argv[1]) as file:
        to_runner, to_lexical = Queue(), Queue()
        do(file.read(), to_runner, to_lexical, with_running)
        Runner(to_runner, to_lexical).start()


if __name__ == '__main__':
    main()
