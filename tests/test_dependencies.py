"""Dependencies test suite."""

import inspect
from textwrap import dedent

import pytest

from dependencies import Injector, DependencyError


def test_lambda_dependency():
    """Inject lambda function."""

    class Foo(object):
        def __init__(self, add):
            self.add = add
        def do(self, x):
            return self.add(x, x)

    class Summator(Injector):
        foo = Foo
        add = lambda x, y: x + y

    assert Summator.foo.do(1) == 2


def test_function_dependency():
    """Inject regular function."""

    class Foo(object):
        def __init__(self, add):
            self.add = add
        def do(self, x):
            return self.add(x, x)

    def plus(x, y):
        return x + y

    class Summator(Injector):
        foo = Foo
        add = plus

    assert Summator.foo.do(1) == 2


def test_inline_dependency():
    """Inject method defined inside Injector subclass."""

    class Foo(object):
        def __init__(self, add):
            self.add = add
        def do(self, x):
            return self.add(x, x)

    class Summator(Injector):
        foo = Foo
        def add(x, y):
            return x + y

    assert Summator.foo.do(1) == 2


def test_class_dependency():
    """
    Inject class.

    Instantiate class from the same scope and inject its instance.
    """

    class Foo(object):
        def __init__(self, add, bar):
            self.add = add
            self.bar = bar
        def do(self, x):
            return self.add(self.bar.go(x), self.bar.go(x))

    class Bar(object):
        def __init__(self, mul):
            self.mul = mul
        def go(self, x):
            return self.mul(x, x)

    class Summator(Injector):
        foo = Foo
        bar = Bar
        add = lambda x, y: x + y
        mul = lambda x, y: x * y

    assert Summator.foo.do(2) == 8


def test_redefine_dependency():
    """
    We can redefine dependency by inheritance from the `Injector`
    subclass.
    """

    class Foo(object):
        def __init__(self, add):
            self.add = add
        def do(self, x):
            return self.add(x, x)

    class Summator(Injector):
        foo = Foo
        add = lambda x, y: x + y

    class WrongSummator(Summator):
        add = lambda x, y: x - y

    assert WrongSummator.foo.do(1) == 0


def test_injector_deny_multiple_inheritance():
    """`Injector` may be used in single inheritance only."""

    class Foo(object):
        pass

    with pytest.raises(DependencyError):
        class Foo(Injector, Foo):
            pass


@pytest.mark.parametrize('code', [
    # Declarative injector.
    """
    class Bar(Injector):
        def __eq__(self, other):
            return False
    """,
    # Let notation.
    """
    class Foo(Injector):
        pass

    Foo.let(__eq__=lambda self, other: False)
    """,
    # Attribute assignment.
    """
    class Foo(Injector):
        pass

    Foo.__eq__ = lambda self, other: False
    """,
])
def test_deny_magic_methods_injection(code):
    """`Injector` doesn't accept magic methods."""

    scope = {'Injector': Injector}

    with pytest.raises(DependencyError):
        exec(dedent(code), scope)


def test_attribute_error():
    """Raise attribute error if we can't find dependency."""

    class Foo(Injector):
        pass

    with pytest.raises(AttributeError):
        Foo.test


def test_circle_dependencies():
    """
    Throw `DependencyError` if class needs a dependency named same as
    class.
    """

    with pytest.raises(DependencyError):

        class Foo(object):
            def __init__(self, foo):
                self.foo = foo

        class Summator(Injector):
            foo = Foo

        Summator.foo            # Will fail with maximum recursion depth.


def test_circle_dependencies_message():
    """
    Show correct error message if class needs a dependency named same
    as class.
    """

    with pytest.raises(DependencyError) as excinfo:

        class Foo(object):
            def __init__(self, foo):
                self.foo = foo

        class Summator(Injector):
            foo = Foo

    assert str(excinfo.value).startswith("'foo' is a circle dependency in the <class")
    assert str(excinfo.value).endswith(".Foo'> constructor")


def test_complex_circle_dependencies():
    """
    Throw `DependencyError` in the case of complex dependency recursion.

    One class define an argument in its constructor.  We have second
    class in the container named for this dependency.  This class
    define an argument in its constructor named like first class in
    the container.  We have mutual recursion in this case.
    """

    with pytest.raises(DependencyError):

        class Foo(object):
            def __init__(self, bar):
                self.bar = bar

        class Bar(object):
            def __init__(self, foo):
                self.foo = foo

        class Test(Injector):
            foo = Foo
            bar = Bar

        Test.foo                # Will fail with maximum recursion depth.


def test_complex_circle_dependencies_in_different_classes():
    """
    Detect complex circle dependencies separated in different classes.
    """

    with pytest.raises(DependencyError):

        class Foo(object):
            def __init__(self, bar):
                self.bar = bar

        class Bar(object):
            def __init__(self, foo):
                self.foo = foo

        class First(Injector):
            foo = Foo

        class Second(First):
            bar = Bar

        Second.foo              # Will fail with maximum recursion depth.


def test_complex_circle_dependencies_with_let_binding():
    """Detect complex circle dependencies with `let` binding."""

    with pytest.raises(DependencyError):

        class Foo(object):
            def __init__(self, bar):
                self.bar = bar

        class Bar(object):
            def __init__(self, foo):
                self.foo = foo

        Injector.let(foo=Foo, bar=Bar).foo  # Will fail with maximum recursion depth.


def test_complex_circle_dependencies_long_circle():
    """
    Detect complex dependencies recursion with circles longer then two
    constructors.
    """

    with pytest.raises(DependencyError):

        class Foo(object):
            def __init__(self, bar):
                self.bar = bar

        class Bar(object):
            def __init__(self, baz):
                self.baz = baz

        class Baz(object):
            def __init__(self, foo):
                self.foo = foo

        class Test(Injector):
            foo = Foo
            bar = Bar
            baz = Baz

        Test.foo                # Will fail with maximum recursion depth.


def test_override_keyword_argument_if_dependency_was_specified():
    """
    Use specified dependency for constructor keyword arguments if
    dependency with desired name was mentioned in the injector.
    """

    class Foo(object):
        def __init__(self, add, y=1):
            self.add = add
            self.y = y
        def do(self, x):
            return self.add(x, self.y)

    class Summator(Injector):
        foo = Foo
        add = lambda x, y: x + y
        y = 2

    assert Summator.foo.do(1) == 3


def test_preserve_keyword_argument_if_dependency_was_missed():
    """
    Use constructor keyword arguments if dependency with desired name
    was missed in the injector.
    """

    class Foo(object):
        def __init__(self, add, y=1):
            self.add = add
            self.y = y
        def do(self, x):
            return self.add(x, self.y)

    class Summator(Injector):
        foo = Foo
        add = lambda x, y: x + y

    assert Summator.foo.do(1) == 2


def test_preserve_missed_keyword_argument_in_the_middle():
    """
    Use default keyword argument and override following keyword
    argument since it was specified in the constructor.
    """

    class Foo(object):
        def __init__(self, x, y=1, z=2):
            self.x = x
            self.y = y
            self.z = z

        def do(self):
            return self.x + self.y + self.z

    class Container(Injector):
        foo = Foo
        x = 5
        z = 1

    assert Container.foo.do() == 7


@pytest.mark.parametrize('code', [
    # Declarative injector.
    """
    class Summator(Injector):
        foo = Foo
        args = (1, 2, 3)
    """,
    # Let notation.
    """
    Injector.let(foo=Foo, args=(1, 2, 3))
    """,
    # Attribute assignment.
    """
    class Summator(Injector):
        args = (1, 2, 3)

    Summator.foo = Foo
    """,
])
def test_deny_arbitrary_argument_list(code):
    """Raise `DependencyError` if constructor have *args argument."""

    class Foo(object):
        def __init__(self, *args):
            self.args = args

    scope = {'Injector': Injector, 'Foo': Foo}

    with pytest.raises(DependencyError) as exc_info:
        exec(dedent(code), scope)

    assert str(exc_info.value).startswith("<class 'test_dependencies.")
    assert str(exc_info.value).endswith(
        "Foo'>.__init__ have arbitrary argument list"
    )


@pytest.mark.parametrize('code', [
    # Declarative injector.
    """
    class Summator(Injector):
        foo = Foo
        kwargs = {'start': 5}
    """,
    # Let notation.
    """
    Injector.let(foo=Foo, kwargs = {'start': 5})
    """,
    # Attribute assignment.
    """
    class Summator(Injector):
        kwargs = {'start': 5}

    Summator.foo = Foo
    """,
])
def test_deny_arbitrary_keyword_arguments(code):
    """Raise `DependencyError` if constructor have **kwargs argument."""

    class Foo(object):
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    scope = {'Injector': Injector, 'Foo': Foo}

    with pytest.raises(DependencyError) as exc_info:
        exec(dedent(code), scope)

    assert str(exc_info.value).startswith("<class 'test_dependencies.")
    assert str(exc_info.value).endswith(
        "Foo'>.__init__ have arbitrary keyword arguments"
    )


@pytest.mark.parametrize('code', [
    # Declarative injector.
    """
    class Summator(Injector):
        foo = Foo
        args = (1, 2, 3)
        kwargs = {'start': 5}
    """,
    # Let notation.
    """
    Injector.let(foo=Foo, args=(1, 2, 3), kwargs={'start': 5})
    """,
    # Attribute assignment.
    """
    class Summator(Injector):
        args = (1, 2, 3)
        kwargs = {'start': 5}

    Summator.foo = Foo
    """,
])
def test_deny_arbitrary_positional_and_keyword_arguments_together(code):
    """
    Raise `DependencyError` if constructor have *args and **kwargs
    argument.
    """

    class Foo(object):
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    scope = {'Injector': Injector, 'Foo': Foo}

    with pytest.raises(DependencyError) as exc_info:
        exec(dedent(code), scope)

    assert str(exc_info.value).startswith("<class 'test_dependencies.")
    assert str(exc_info.value).endswith(
        "Foo'>.__init__ have arbitrary argument list and keyword arguments"
    )


def test_attribute_error_with_keyword_arguments_present():
    """
    Reraise argument error when keyword arguments specify another
    dependencies defaults.
    """

    class Foo(object):
        def __init__(self, one, two=2):
            self.one = one
            self.two = two

    class Bar(Injector):
        foo = Foo

    with pytest.raises(AttributeError):
        Bar.foo


def test_injectable_without_its_own_init():
    """
    Inject dependencies into object subclass which doesn't specify its
    own `__init__`.
    """

    class Foo(object):
        def do(self):
            return 1

    class Baz(Injector):
        foo = Foo

    assert Baz.foo.do() == 1


def test_injectable_with_parent_init():
    """
    Inject dependencies into object which parent class define
    `__init__`.
    """

    class Foo(object):
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class Bar(Foo):
        def add(self):
            return self.x + self.y

    class Baz(Injector):
        bar = Bar
        x = 1
        y = 2

    assert Baz.bar.add() == 3


def test_injectable_with_parent_without_init():
    """
    Inject dependencies into object which parent doesn't define
    `__init__`.
    """

    class Foo(object):
        pass

    class Bar(Foo):
        def add(self):
            return 3

    class Baz(Injector):
        bar = Bar

    assert Baz.bar.add() == 3


def test_let_factory():
    """
    `Injector` subclass can produce its own subclasses with `let`
    factory.
    """

    class Foo(Injector):
        pass

    assert issubclass(Foo.let(), Foo)


def test_let_factory_overwrite_dependencies():
    """
    `Injector.let` produce `Injector` subclass with overwritten
    dependencies.
    """

    class Foo(Injector):
        bar = 1

    assert Foo.let(bar=2).bar == 2


def test_let_factory_resolve_not_overwritten_dependencies():
    """`Injector.let` can resolve dependencies it doesn't touch."""

    class Foo(Injector):
        bar = 1

    assert Foo.let(baz=2).bar == 1


def test_do_not_redefine_let_with_inheritance():
    """We can't specify `let` attribute in the `Injector` subclass."""

    with pytest.raises(DependencyError):
        class Foo(Injector):
            let = 2


def test_do_not_redefine_let_with_let():
    """We can't specify `let` attribute with `let` argument."""

    class Foo(Injector):
        pass

    with pytest.raises(DependencyError):
        Foo.let(let=1)


def test_let_factory_attribute_error():
    """
    `Injector.let` will raise `AttributeError` on missing dependency.
    """

    class Foo(Injector):
        pass

    with pytest.raises(AttributeError):
        Foo.let().x


def test_let_factory_on_injector_directly():
    """
    Dependencies can be specified with `let` factory applied to
    `Injector` derectly.
    """

    class Foo(object):
        def __init__(self, bar):
            self.bar = bar

    class Bar(object):
        def __init__(self, baz):
            self.baz = baz

    assert Injector.let(foo=Foo, bar=Bar, baz=1).foo.bar.baz == 1


def test_do_not_instantiate_dependencies_ended_with_cls():
    """
    Do not call class constructor, if it stored with name ended
    `_cls`.

    For example, `logger_cls`.
    """

    class Foo(object):
        pass

    class Bar(Injector):
        foo_cls = Foo

    assert inspect.isclass(Bar.foo_cls)


def test_do_not_instantiate_injector():
    """Deny injector instantiation."""

    with pytest.raises(DependencyError):
        Injector()


def test_do_not_instantiate_injector_subclasses():
    """Deny injector subclasses instantiation."""

    class Foo(Injector):
        pass

    with pytest.raises(DependencyError):
        Foo()


def test_ignore_injector_instantiation_signature():
    """
    Raise `DependencyError` for instantiation with any arguments.  Do
    not use `TypeError` here.
    """

    with pytest.raises(DependencyError):
        Injector(1)

    with pytest.raises(DependencyError):
        Injector(x=1)


def test_show_common_class_attributes_with_dir():
    """`dir` show common class attributes."""

    class Common(object):
        pass

    class Foo(Injector):
        pass

    dir(Common) == dir(Foo)


def test_show_injected_dependencies_with_dir():
    """
    `dir` should show injected dependencies and hide
    `__dependencies__` container.
    """

    class Foo(Injector):
        x = 1

    assert 'x' in dir(Foo)
    assert '__dependencies__' not in dir(Foo)


def test_show_injected_dependencies_with_dir_once():
    """Do not repeat injected dependencies in the inheritance chain."""

    class Foo(Injector):
        x = 1

    class Bar(Foo):
        x = 2

    assert dir(Bar).count('x') == 1


def test_show_let_dependencies_with_dir():
    """`dir` show dependencies injected with `let`."""

    assert 'x' in dir(Injector.let(x=1))

    class Foo(Injector):
        pass

    assert 'x' in dir(Foo.let(x=1))


def test_mutable_injector():
    """We can extend existed `Injector` by attribute assignment."""

    class Foo(object):
        def __init__(self, bar):
            self.bar = bar

    class Bar(object):
        pass

    class Baz(Injector):
        pass

    Baz.foo = Foo
    Baz.bar = Bar

    assert isinstance(Baz.foo, Foo)


def test_mutable_injector_let_expression():
    """
    We can extend `Injector` created with `let` expression by
    attribute assignment.
    """

    class Foo(object):
        def __init__(self, bar):
            self.bar = bar

    class Bar(object):
        pass

    Baz = Injector.let()

    Baz.foo = Foo
    Baz.bar = Bar

    assert isinstance(Baz.foo, Foo)


def test_mutable_injector_deny_to_modify_injector():
    """Deny to modify `Injector` itself."""

    with pytest.raises(DependencyError):
        Injector.foo = 1


def test_unregister_dependency():
    """We can unregister dependency from `Injector` subclasses."""

    class Foo(object):
        def __init__(self, bar):
            self.bar = bar

    class Bar(object):
        pass

    class Baz(Injector):
        foo = Foo
        bar = Bar

    del Baz.bar

    with pytest.raises(AttributeError):
        Baz.foo


def test_unregister_dependency_let_expression():
    """We can unregister dependency from `let` expression results."""

    class Foo(object):
        def __init__(self, bar):
            self.bar = bar

    class Bar(object):
        pass

    Baz = Injector.let(foo=Foo, bar=Bar)

    del Baz.bar

    with pytest.raises(AttributeError):
        Baz.foo


def test_unregister_missing_dependency():
    """
    Throw `AttributeError` if someone tries to delete missing
    dependency.
    """

    with pytest.raises(AttributeError):
        del Injector.foo

    class Foo(Injector):
        pass

    with pytest.raises(AttributeError):
        del Foo.foo


def test_unregister_do_not_use_object_constructor():
    """
    We shouldn't touch/run object `__init__` during it unregistration.
    """

    class Foo(object):
        def __init__(self):
            raise Exception

    class Bar(Injector):
        foo = Foo

    del Bar.foo


def test_deny_let_redefinition_with_attribute_assignment():
    """Deny `let` method redefinition with attribute assignment in `Injector` subclass."""

    class Foo(Injector):
        pass

    with pytest.raises(DependencyError):
        Foo.let = lambda cls, **kwargs: None


# TODO: check circles on assignment
#
# TODO: deny to remove let from injector
#
# TODO: hide dependencies library KeyError from stack trace
#
# TODO: test all exception messages
#
# TODO: raise exception if init argument have class as its default
# value and its name does not ends with _cls suffix.
#
# def __init__(self, x=CustomClass) - raise error
#
# def __init__(self, x_cls=CustomClass) - work as usual
#
# TODO: test case below
#
# class Container(Injector):
#     x = CustomClass
#     x_cls = x
#
# What spec should be stored in that case?
#
# TODO: Add decorator based container modification
#
# class Container(Injector):
#     pass
#
# @Container.as.foo
# class Foo:
#     def __init__(self, x, y):
#         self.x = x
#         self.y = y
#
# TODO: Lazy injection marker for nested containers.  For example we
# have host and port in Database constructor.  We have host and port
# in the Cache constructor.  It is nice to have the possibility use
# simple `host` and `port` arguments in each class and specify this as
# hierarchy in the injector.
