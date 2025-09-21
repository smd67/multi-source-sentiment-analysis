"""
This module is a test driver for tracing.
"""

from decorators import span_decorator  # pylint: disable=import-error


@span_decorator
def foo_1():
    print("Performing operation foo_1...")


@span_decorator
def foo_2():
    print("Performing operation foo_2...")


@span_decorator
def foo_3():
    print("Performing operation foo_3...")


@span_decorator
def foo_4():
    print("Performing operation foo_4...")


@span_decorator
def main():
    print("Performing some operation...")
    foo_1()
    foo_2()
    foo_3()
    foo_4()


if __name__ == "__main__":
    main()
