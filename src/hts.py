import sys
import os

from lexical import do, fatal


def main():
    if len(sys.argv) < 2:
        fatal('Give me your file.hts')
    if not sys.argv[1].endswith('.hts'):
        fatal('Invalid extension. I can understand only *.hts files')
    if not os.path.exists(sys.argv[1]):
        fatal('File not exists')
    with open(sys.argv[1]) as file:
        do(file.read())


if __name__ == '__main__':
    main()
