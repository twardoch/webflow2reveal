# this_file: py/src/webflow2reveal/__main__.py

import fire
from .compiler import convert

def main():
    fire.Fire(convert)

if __name__ == "__main__":
    main()
