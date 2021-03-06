# -*- coding: utf-8 -*-
# Author: Florian Mayer <florian.mayer@bitsrc.org>

""" Offer a callable object that dispatches based on arbitrary conditions
and function signature. That means, whenever it is called, it finds the
registered methods that match the input's signature and then checks for
user-defined conditions. """

from __future__ import absolute_import

import inspect

from itertools import izip

def matches_types(fun, types, args, kwargs):
    return all(
        isinstance(obj, cls) for obj, cls in izip(
            arginize(fun, args, kwargs), types
        )
    )

def arginize(fun, a, kw):
    """ Turn args and kwargs into args by considering the function
    signature. """
    args, varargs, keywords, defaults = correct_argspec(fun)
    if varargs is not None or keywords is not None:
        raise ValueError
    names = args[len(a):]
    return list(a) + [kw[name] for name in names]


def correct_argspec(fun):
    """ Remove first argument if method is bound. """
    args, varargs, keywords, defaults = inspect.getargspec(fun)
    if inspect.ismethod(fun):
        args = args[1:]
    return args, varargs, keywords, defaults 


def matches_signature(fun, a, kw):
    """ Check whether function can be called with a as args and kw as kwargs.
    """
    args, varargs, keywords, defaults = correct_argspec(fun)
    if varargs is None and len(a) > len(args):
        return False
    skw = set(kw)
    sargs = set(args[len(a):])
    
    # There mayn't be unexpected parameters unless there is a **kwargs
    # in fun's signature.
    if keywords is None and skw - sargs != set():
        return False
    rest = set(args[len(a):])  - set(kw)
    
    # If there are any arguments that weren't passed but do not have
    # defaults, the signature does not match.
    defs = set() if defaults is None else set(defaults)
    if rest > defs:
        return False
    return True


class ConditionalDispatch(object):
    def __init__(self):
        self.funcs = []
        self.nones = []
    
    def add_dec(self, condition):
        def _dec(fun):
            self.add(fun, condition)
            return fun
        return _dec
    
    def add(self, fun, condition=None, types=None):
        """ Add fun to ConditionalDispatch under the condition that the
        arguments must match. If condition is left out, the function is 
        executed for every input that matches the signature. Functions are
        considered in the order they are added, but ones with condition=None
        are considered as the last: that means, a function with condition None
        serves as an else branch for that signature.
        conditions must be mutually exclusive because otherwise which will
        be executed depends on the order they are added in. Function signatures
        of fun and condition must match (if fun is bound, the bound parameter
        needs to be left out in condition). """
        if condition is None:
            self.nones.append((fun, types))
        elif correct_argspec(fun) != correct_argspec(condition):
            raise ValueError(
                "Signature of condition must match signature of fun."
            )
        else:
            self.funcs.append((fun, condition, types))
    
    def __call__(self, *args, **kwargs):
        matched = False
        for fun, condition, types in self.funcs:
            if (matches_signature(fun, args, kwargs) and
                (types is None or matches_types(fun, types, args, kwargs))):
                matched = True
                if condition(*args, **kwargs):
                    return fun(*args, **kwargs)
        for fun, types in self.nones:
            if (matches_signature(fun, args, kwargs) and
                (types is None or matches_types(fun, types, args, kwargs))):
                return fun(*args, **kwargs)
        
        if matched:
            raise TypeError(
                "Your input did not fulfill the condition for any function."
            )
        else:
            raise TypeError(
                "There are no functions matching your input parameter "
                "signature."
            )
