#!/usr/bin/env python
# encoding: utf-8
"""
set.py

Created by José Sánchez-Gallego on 18 Mar 2014.
Licensed under a 3-clause BSD license.

Revision history:
    18 Mar 2014 J. Sánchez-Gallego
      Initial version

"""

from __future__ import division
from __future__ import print_function
from .exposure import Exposure
from ..apoDB import TotoroDBConnection
from .. import log, config, site
from ..exceptions import TotoroError, EmptySet
from ..logic.mangaLogic import checkSet
from ..utils import getMinMaxIntervalSequence, getIntervalFromPoints, \
    calculateMean
import numpy as np
from copy import copy


totoroDB = TotoroDBConnection()
plateDB = totoroDB.plateDB
mangaDB = totoroDB.mangaDB
session = totoroDB.Session()


def getPlateSets(inp, format='plate_id', **kwargs):

    with session.begin(subtransactions=True):
        sets = session.query(mangaDB.Set).join(
            mangaDB.Exposure,
            plateDB.Exposure,
            plateDB.Observation,
            plateDB.PlatePointing,
            plateDB.Plate).filter(
                eval('plateDB.Plate.{0} == {1}'.format(format, inp))).all()

    return [Set(set.pk, **kwargs) for set in sets]


class Set(mangaDB.Set):

    def __new__(cls, input=None, format='pk', *args, **kwargs):

        if input is None:
            return mangaDB.Set.__new__(cls)

        base = cls.__bases__[0]

        with session.begin(subtransactions=True):
            instance = session.query(base).filter(
                eval('{0}.{1} == {2}'.format(base.__name__, format, input))
                ).one()

        instance.__class__ = cls

        return instance

    def __init__(self, inp=None, format='pk', mock=False,
                 silent=False, *args, **kwargs):

        self.isMock = mock
        if inp is None:
            self.isMock = True

        self.kwargs = kwargs

        if not self.isMock:
            self.totoroExposures = self.loadExposures(silent=silent)
        else:
            self.totoroExposures = []

        # Checks that the set has exposures.
        if not self.isMock:
            self._checkHasExposures()

        if not silent and not self.isMock:
            log.debug('Loaded set pk={0} (plate_id={1})'.format(
                      self.pk, self.plate.plate_id))

    def __repr__(self):
        return '<Totoro Set (pk={0}, status={1})'.format(
            self.pk, self.getQuality(flag=False)[0])

    def update(self, **kwargs):
        """Reloads the set."""

        newSelf = Set(self.pk, fromat='pk', silent=True, mock=self.isMock,
                      **self.kwargs)
        self = newSelf

        log.debug('Set pk={0} has been reloaded'.format(
                  self.pk))

    @staticmethod
    def fromExposures(exposures, **kwargs):
        """Creates a mock set for a list of Totoro.Exposures."""

        newSet = Set(mock=True, **kwargs)
        newSet.totoroExposures = list(exposures)

        return newSet

    def loadExposures(self, silent=False):

        from .exposure import Exposure

        return [Exposure(mangaExp.pk, format='pk', parent='mangaDB',
                         silent=silent)
                for mangaExp in self.exposures]

    def _checkHasExposures(self):
        if len(self.totoroExposures) == 0:
            raise EmptySet('set pk={0} has no exposures.'.format(self.pk))

    @classmethod
    def createMockSet(cls, ra=None, dec=None, silent=False, **kwargs):

        if ra is None or dec is None:
            raise TotoroError('ra and dec must be specified')

        newSet = Set(mock=True, silent=silent, ra=ra, dec=dec, **kwargs)

        if not silent:
            log.debug('Created mock set.'.format(newSet.pk))

        return newSet

    def addMockExposure(self, **kwargs):

        if self.complete is True:
            raise TotoroError('set is complete; not exposures can be added.')

        if 'ditherPosition' not in kwargs or kwargs['ditherPosition'] is None:
            kwargs['ditherPosition'] = self.getMissingDitherPositions()[0]

        newExposure = Exposure.createMockExposure(**kwargs)
        self.totoroExposures.append(newExposure)

    @property
    def plate(self):
        """Returns the plateDB.Plate object for this set."""

        self._checkHasExposures()
        return (self.exposures[0].platedbExposure.observation.
                plate_pointing.plate)

    @property
    def ra(self):
        return self.getCoordinates()[0]

    @property
    def dec(self):
        return self.getCoordinates()[1]

    def getCoordinates(self):

        if 'ra' in self.kwargs and 'dec' in self.kwargs:
            if (self.kwargs['ra'] is not None and
                    self.kwargs['dec'] is not None):
                return np.array(
                    [self.kwargs['ra'], self.kwargs['dec']], np.float)
        else:
            self._checkHasExposures()
            return self.totoroExposures[0].getCoordinates()

    def getHA(self, midPoint=False):
        """Returns the HA interval of the exposures in the set. If midPoint is
        set, the middle point of the exposures is used for the calculation."""

        validExposures = self.getValidExposures()
        if not midPoint or len(validExposures) == 1:
            expHAs = np.array([exp.getHA() for exp in validExposures])
            return getMinMaxIntervalSequence(expHAs)
        else:
            midPoints = np.array(
                [calculateMean(exposure.getHA())
                 for exposure in self.totoroExposures if exposure.valid])
            return np.array(getIntervalFromPoints(midPoints))

    def getHARange(self):
        """Returns the HA limits to add more exposures to the set."""

        haRange = self.getHA()
        return np.array([np.max(haRange) - 15., np.min(haRange) + 15.]) % 360.

    def getDitherPositions(self):
        """Returns a list of dither positions in the set."""

        return [exp.ditherPosition for exp in self.totoroExposures]

    def getMissingDitherPositions(self):
        """Returns a list of missing dither positions."""

        setDitherPositions = copy(config['set']['ditherPositions'])
        for dPos in self.getDitherPositions():
            if dPos.upper() in setDitherPositions:
                setDitherPositions.remove(dPos.upper())

        return setDitherPositions

    def getSN2Array(self):
        """Returns an array with the cumulated SN2 of the valid exposures in
        the set. The return format is [b1SN2, b2SN2, r1SN2, r2SN2]."""

        validExposures = []
        for exposure in self.totoroExposures:
            if exposure.valid:
                validExposures.append(exposure)

        if len(validExposures) == 0:
            return np.array([0.0, 0.0, 0.0, 0.0])
        else:
            return np.sum([exp.getSN2Array() for exp in validExposures],
                          axis=0)

    def getSN2Range(self):
        """Returns the SN2 range in which new exposures may be taken."""

        maxSN2Factor = config['set']['maxSN2Factor']

        sn2 = np.array([exp.getSN2Array() for exp in self.totoroExposures])
        sn2Average = np.array(
            [(np.mean(ss[0:2]), np.mean(ss[2:4])) for ss in sn2])

        minSN2Blue = np.max(sn2Average[:, 0]) / maxSN2Factor
        maxSN2Blue = np.min(sn2Average[:, 0]) * maxSN2Factor
        minSN2Red = np.max(sn2Average[:, 1]) / maxSN2Factor
        maxSN2Red = np.min(sn2Average[:, 1]) * maxSN2Factor

        if minSN2Red < config['SN2thresholds']['exposureRed']:
            minSN2Red = config['SN2thresholds']['exposureRed']
        if minSN2Blue < config['SN2thresholds']['exposureBlue']:
            minSN2Blue = config['SN2thresholds']['exposureBlue']

        return np.array([[minSN2Blue, maxSN2Blue], [minSN2Red, maxSN2Red]])

    def getSeeingRange(self):
        """Returns the seeing range in which new exposures may be taken."""

        maxSeeingRange = config['set']['maxSeeingRange']
        maxSeeing = config['exposure']['maxSeeing']
        seeings = np.array([exp.seeing for exp in self.totoroExposures])

        seeingRangeMin = np.max(seeings) - maxSeeingRange
        seeingRangeMax = np.min(seeings) + maxSeeingRange
        if seeingRangeMax > maxSeeing:
            seeingRangeMax = maxSeeing

        return np.array([seeingRangeMin, seeingRangeMax])

    def getQuality(self, **kwargs):
        """Returns the quality of the set."""

        return checkSet(self, silent=False, **kwargs)

    def getValidExposures(self):

        validExposures = []
        for exp in self.totoroExposures:
            if exp.valid is True:
                validExposures.append(exp)

        return validExposures

    def getAverageSeeing(self):

        seeings = []
        for exp in self.totoroExposures:
            if exp.valid:
                seeings.append(exp.seeing)

        return np.mean(seeings)

    def getLSTRange(self):

        ha0, ha1 = self.getHARange()

        lst0 = (ha0 + self.ra) % 360. / 15
        lst1 = (ha1 + self.ra) % 360. / 15

        return np.array([lst0, lst1])

    def getUTVisibilityWindow(self, date=None, format='str'):

        lst0, lst1 = self.getLSTRange()

        ut0 = site.localTime(lst0, date=date, utc=True,
                             returntype='datetime')
        ut1 = site.localTime(lst1, date=date, utc=True,
                             returntype='datetime')

        if format == 'str':
            return ('{0:%H:%M}'.format(ut0), '{0:%H:%M}'.format(ut1))
        else:
            return (ut0, ut1)

    @property
    def complete(self):
        if self.getQuality()[0] not in ['Incomplete']:
            return True
        else:
            return False
