import sys

from nose.tools import eq_

from gbab.smoother import Smoother

def test_smooth_one_field():
    smoother = Smoother()

    vals = [(1, 2), (3, 5), (2, 4), (1, 1)]
    smoothed = smoother.smooth(vals, 2, [0])
    eq_([(2.0, 2), (2.0, 5), (1.5, 4), (1.5, 1)], smoothed)

    vals = [(1, 2), (3, 5), (2, 4), (5, 1)]
    smoothed = smoother.smooth(vals, 3, [0])
    eq_([(2.0, 2), (3.0, 5), (3.0, 4), (3.0, 1)], smoothed)

    vals = [(1, 2), (3, 5), (2, 4), (5, 1)]
    smoothed = smoother.smooth(vals, 1, [0])
    eq_([(1.0, 2), (3.0, 5), (2.0, 4), (5.0, 1)], smoothed)

def test_empty():
    smoother = Smoother()
    eq_([], smoother.smooth([], 3, [1, 3]))
