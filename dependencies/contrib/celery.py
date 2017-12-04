"""
dependencies.contrib.celery
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module implements injectable Celery task definition.

:copyright: (c) 2016-2017 by Artem Malyshev.
:license: LGPL-3, see LICENSE for more details.
"""

from __future__ import absolute_import

import celery
from dependencies import Injector

__all__ = ['task', 'shared_task']

undefined = object()


class Signature(object):
    """
    Create Celery canvas signature with arguments collected from
    `Injector` subclass.
    """

    def __init__(
            self,
            name,
            app=None,
            immutable=undefined,
            options=undefined,
            subtask_type=undefined,
    ):

        self.name = name
        self.app = app
        self.immutable = immutable
        self.options = options
        self.subtask_type = subtask_type

    def __call__(self, args=None, kwargs=None, **ex):

        if 'options' not in ex and self.options is not undefined:
            ex['options'] = self.options
        if 'immutable' not in ex and self.immutable is not undefined:
            ex['immutable'] = self.immutable
        if 'subtask_type' not in ex and self.subtask_type is not undefined:
            ex['subtask_type'] = self.subtask_type
        return celery.canvas.Signature(
            task=self.name, app=self.app, args=args, kwargs=kwargs, **ex)


class Shortcut(Signature):
    """Create Celery canvas shortcut expression."""

    immutable_default = False

    def __call__(self, *args, **kwargs):

        return celery.canvas.Signature(
            task=self.name,
            app=self.app,
            args=args,
            kwargs=kwargs,
            immutable=(self.immutable_default
                       if self.immutable is undefined else self.immutable),
            options={} if self.options is undefined else self.options,
            subtask_type=(None if self.subtask_type is undefined else
                          self.subtask_type),
        )


class ImmutableShortcut(Shortcut):
    """Create immutable Celery canvas shortcut expression."""

    immutable_default = True


class TaskMixin(Injector):

    signature = Signature
    s = Shortcut
    si = ImmutableShortcut


def task(injector):
    """Create Celery task from injector class."""

    @injector.app.task(name=injector.name)
    def __task(*args, **kwargs):
        return injector.run(*args, **kwargs)

    return TaskMixin & injector


def shared_task(injector):
    """Create Celery shared task from injector class."""

    @celery.shared_task(name=injector.name)
    def __task(*args, **kwargs):
        return injector.run(*args, **kwargs)

    return TaskMixin & injector


# TODO:
#
# Assert injector has necessary attributes with custom error message.
#
# Support all arguments of the `task`.