#
"""Retry Logic Decorator"""
#from __future__ import print_function
import itertools
import time

def retry(delays=(0, 1, 2, 4, 8, 16),
          exception=Exception,
          report=lambda *args: None):
    """Retry decorator"""
    def wrapper(function):
        def wrapped(*args, **kwargs):
            problems = []
            for delay in itertools.chain(delays, [ None ]):
                try:
                    return function(*args, **kwargs)
                except exception as problem:
                    if hasattr(problem, "code") and problem.code == 403:
                        raise
                    problems.append(problem)
                    if delay is None:
                        report("retry failed definitely: {}".format(problems))
                        raise
                    else:
                        report("retry failed: {} -- delaying for {}s".format(problem, delay))
                        time.sleep(delay)
        return wrapped
    return wrapper
