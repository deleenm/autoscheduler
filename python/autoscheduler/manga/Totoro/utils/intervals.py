#!/usr/bin/env python
# encoding: utf-8
"""
intervals.py

Created by José Sánchez-Gallego on 4 Aug 2014.
Licensed under a 3-clause BSD license.

Revision history:
    4 Aug 2014 J. Sánchez-Gallego
      Initial version

"""

from __future__ import division
from __future__ import print_function
import numpy as np
from ..exceptions import TotoroError
import itertools


def getIntervalIntersectionLength(aa, bb, wrapAt=360):
    """Returns the length of the instersection between two intervals aa and bb.
    """

    intersection = getIntervalIntersection(aa, bb, wrapAt=wrapAt)

    if intersection is False:
        return 0.0
    else:
        return (intersection[1] - intersection[0]) % wrapAt


def getIntervalIntersection(aa, bb, wrapAt=360):
    """Returns the intersection between two intervals."""

    if (bb[1] - bb[0]) % wrapAt > (aa[1] - aa[0]) % wrapAt:
        aa, bb = bb, aa

    if isPointInInterval(bb[0], aa) and isPointInInterval(bb[1], aa):
        return np.array([bb[0], bb[1]])

    if not isPointInInterval(bb[0], aa) and not isPointInInterval(bb[1], aa):
        return False

    if isPointInInterval(bb[0], aa):
        return np.array([bb[0], aa[1]])

    if isPointInInterval(bb[1], aa):
        return np.array([aa[0], bb[1]])


def isPointInInterval(point, ival, wrapAt=360):
    """Returns True if point in interval."""

    return (point - ival[0]) % wrapAt <= (ival[1] - ival[0]) % wrapAt


def isIntervalInsideOther(aa, bb, wrapAt=360, onlyOne=False):
    """Checks if the interval aa (a numpy.ndarray of length 2) is inside bb."""

    p1 = ((aa[0] - bb[0]) % wrapAt < (bb[1]-bb[0]) % wrapAt)
    p2 = ((aa[1] - bb[0]) % wrapAt < (bb[1]-bb[0]) % wrapAt)

    if p1 and p2:
        return True
    elif onlyOne and (p1 or p2):
        return True

    return False


def intervalLength(aa, wrapAt=360.):
    return (aa[1] - aa[0]) % wrapAt


def getMinMaxIntervalSequence(intervals, wrapAt=360):

    if intervals.shape[0] < 1:
        raise TotoroError('input needs to be an Nx2 array with N>=1.')
    elif intervals.shape[0] == 1:
        return np.array(intervals[0])

    firstTwo = intervals[0:2, :]
    rest = intervals[2:, :]

    interval1 = firstTwo[0, :]
    length1 = intervalLength(interval1, wrapAt=wrapAt)

    interval2 = firstTwo[1, :]
    length2 = intervalLength(interval2, wrapAt=wrapAt)

    if (isIntervalInsideOther(interval1, interval2) or
            isIntervalInsideOther(interval2, interval1)):
        newInterval = interval1 if length1 > length2 else interval2
    else:
        tmpInt1 = [interval1[0], interval2[1]]
        tmpLength1 = intervalLength(tmpInt1, wrapAt=wrapAt)
        tmpInt2 = [interval2[0], interval1[1]]
        tmpLength2 = intervalLength(tmpInt2, wrapAt=wrapAt)

        if (isPointInInterval(interval1[0], interval2) or
                isPointInInterval(interval1[1], interval2)):
            newInterval = tmpInt1 if tmpLength1 > tmpLength2 else tmpInt2
        else:
            newInterval = tmpInt1 if tmpLength1 < tmpLength2 else tmpInt2

    if rest.shape[0] == 0:
        return newInterval
    else:
        return getMinMaxIntervalSequence(
            np.append([newInterval], rest, axis=0))


def calculateMean(interval, wrapAt=360.):

    return (interval[0] + ((interval[1] - interval[0]) % wrapAt) / 2.) % wrapAt


def getIntervalFromPoints(points, wrapAt=360.):

    points = np.array(points) % wrapAt

    if len(points) == 1:
        return points

    validExtremes = []
    for permutation in itertools.permutations(points, 2):
        isValid = True
        for point in points:
            if not isPointInInterval(point, permutation):
                isValid = False
        if isValid:
            validExtremes.append(permutation)

    lengths = np.array(
        [intervalLength(interval) for interval in validExtremes])
    # print(validExtremes, lengths)
    return validExtremes[np.argmin(lengths)]
