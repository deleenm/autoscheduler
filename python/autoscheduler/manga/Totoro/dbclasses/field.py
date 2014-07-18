#!/usr/bin/env python
# encoding: utf-8
"""
field.py

Created by José Sánchez-Gallego on 17 Feb 2014.
Licensed under a 3-clause BSD license.

Revision history:
    17 Feb 2014 J. Sánchez-Gallego
      Initial version

"""

from __future__ import division
from __future__ import print_function
from ..exceptions import TotoroNotImplemented
from astropysics import coords
from .. import log
from .. import mangaSampleDB, Session
from .plate import Plate
from .baseDBClass import BaseDBClass
from ..utils import mlhalimit
from .. import dustMap

session = Session()


class Fields(list):

    def __init__(self, inp=None, format='pk', rejectCompleted=True,
                 **kwargs):

        if inp is None:

            _fields = self._getDataFromDB()

            list.__init__(
                self, [Field(values, format='dict', autocomplete=False)
                       for values in _fields])

            log.info('{0} fields acquired'.format(len(_fields)))

            if rejectCompleted:
                nFields = len(_fields)
                _incompleteFields = list(self)
                _incompleteFields[:] = [xx for xx in self
                                        if xx.complete is True]

                list.__init__(self, _incompleteFields)

                log.info('{0} fields rejected because '.format(
                         nFields - len(_incompleteFields)) +
                         'they where completed.')

        else:

            raise TotoroNotImplemented('creating Fields instances from pk'
                                       'or location_id not yet implemented.')

    @staticmethod
    def _getDataFromDB():

        with session.begin():
            fields = session.query(mangaSampleDB.Field).all()

        fieldData = [{cc.name: getattr(field, cc.name)
                      for cc in field.__table__.columns}
                     for field in fields]

        return fieldData

    # def removeDone(self):

    #     fieldPKs = np.array([ff.fieldPK for ff in self])
    #     doneFields = fieldPKs[np.where(areFieldsDone(fieldPKs))]

    #     for fieldPK in doneFields:
    #         self.deleteField(fieldPK)

    # def deleteField(self, fieldPK):

    #     fieldPKs = [ff.fieldPK for ff in self]

    #     if fieldPK not in fieldPKs:
    #         raise TotoroError('fieldPK not found.')

    #     idx = fieldPKs.index(fieldPK)

    #     self.pop(idx)

    # def plugFields(self, jdStart, jdEnd, nCartridges=MAX_CARTRIDGES()):

    #     # Needs improvement to minimise repluggings.

    #     # Testing this method
    #     # for field in self:
    #     #     field.plugged = False

    #     checkPoints = time.Time(np.linspace(jdStart.jd, jdEnd.jd, nCartridges),
    #                             format='jd', scale='utc')

    #     fieldsToPlug = []
    #     for checkPoint in checkPoints:
    #         priorities, orderFields = self.getPriorities(checkPoint)

    #         for ii in range(len(orderFields)):
    #             fieldToPlug = self[orderFields[ii]]
    #             if fieldToPlug.ID not in fieldsToPlug:
    #                 fieldsToPlug.append(fieldToPlug.ID)
    #                 break

    #     mjd = int(jdStart.mjd)
    #     log.info('MJD {0} - Plugging fields {1}'.format(
    #         mjd, fieldsToPlug))

    #     for field in self:
    #         if field.fieldPK in fieldsToPlug:
    #             field.plugged = True
    #             field.nPluggings += 1
    #         else:
    #             field.plugged = False

    # def getPriorities(self, tt, sortedIndices=True):
    #     """Returns a list with the priorities of the fields.

    #     This method returns a list with the priority of each field in the
    #     object. If ``sortIndices=True``, a list of indices sorted from higher
    #     to lower priority is also returned.

    #     """

    #     lst = jd2lmst(tt)
    #     priorities = [ff.getPriority(lst) for ff in self]
    #     order = np.argsort(priorities)[::-1]

    #     if sortedIndices:
    #         return (priorities, order)
    #     else:
    #         return priorities

    # def getOptimumField(self, tt):
    #     lst = jd2lmst(tt)
    #     plugged = [ff for ff in self if ff.plugged is True]
    #     priorities = [ff.getPriority(lst) for ff in self
    #                   if ff.plugged is True and ff.isComplete() is False]
    #     order = np.argsort(priorities)[::-1]
    #     return plugged[order[0]]


class Field(BaseDBClass):

    _complete = None
    plates = []

    def __init__(self, inp, format='pk', autocomplete=True,
                 plates=True, **kwargs):

        self.__DBClass__ = mangaSampleDB.Field
        super(Field, self).__init__(inp, format=format,
                                    autocomplete=autocomplete)

        self.checkField()

        self.coords = coords.ICRSCoordinates(self.center_ra, self.center_dec)
        self.dust = dustMap(self.center_ra, self.center_dec)
        self.mlhalimit = mlhalimit(self.center_dec)

        if plates:
            self.loadPlatesFromDB()

    def checkField(self):
        """Checks that all key columns/attributes are present."""

        columns = ['pk', 'location_id', 'center_ra', 'center_dec']
        if False in map(lambda xx: hasattr(self, xx), columns):
            raise 'one or more nedeed columns are missing in field instance.'

    def loadPlatesFromDB(self):

        with session.begin():
            platePKs = session.query(
                mangaSampleDB.FieldToPlate.platedb_plate_pk).filter(
                mangaSampleDB.FieldToPlate.field_pk == self.pk)

        if platePKs.count() == 0:
            return
        else:
            for platePK in platePKs:
                self.plates.append(Plate(platePK.pk, format='pk',
                                         autocomplete=True, pluggings=True))

    @property
    def complete(self):
        if self._complete is not None:
            return self._complete
        else:
            if len(self.plates) != 0 and \
                    all([plate.complete for plate in self.plates]):
                return True
            else:
                return False

    @complete.setter
    def complete(self, value):
        self._complete = value

    # @property
    # def HAlimit(self):
    #     if self._HAlimit is None:
    #         self._HAlimit = self.getHAlimit()
    #     return self._HAlimit

    # @HAlimit.setter
    # def HAlimit(self, value):
    #     self._HAlimit = value

    # def getHAlimit(self):
    #     return 0.0

    # def isComplete(self):
    #     return self.plugging.complete

    # def _isHAvalid(self, HA, HArange=None):

    #     if HArange is None:
    #         HArange = self.visibilityWindow

    #     if np.abs(HA) < HArange:
    #         return True
    #     else:
    #         return False

    # def getPriority(self, LST):

    #     # HA = LST - self.centre.ra

    #     # if HA.hour < self.visibilityWindow[0].hour or HA > self.visibilityWindow[1]:
    #     #     return 0.

    #     # airMass = computeAirmass(self.centre.dec.deg, HA.deg)
    #     # skyPriority = 1. / (airMass ** ALPHA_RED() * self.iIncrease)
    #     # skyPriority *= SKY_PRIORITY()

    #     # completionPriority = self.getCompletion()
    #     # completionPriority *= COMPLETION_PRIORITY()

    #     return 0.0 # skyPriority + completionPriority

    # def getCompletion(self):

    #     snRed = np.mean(self.plugging.SN_Red)
    #     snBlue = np.mean(self.plugging.SN_Red)

    #     if snRed == 0.0:
    #         redCompletion = 0.0
    #     else:
    #         redCompletion = R_SN2() / snRed

    #     if snBlue == 0.0:
    #         blueCompletion = 0.0
    #     else:
    #         blueCompletion = B_SN2() / snBlue

    #     if redCompletion >= 1. and blueCompletion >= 1.:
    #         return 1.

    #     completion = np.mean([redCompletion, blueCompletion])

    #     return completion

    # def observe(self, startTime, until=None):

    #     if until is None:
    #         until = self.dateHAlimits(startTime)

    #     availableTime = (until - startTime).sec
    #     nExposures = int(availableTime / ONE_EXPOSURE)

    #     if nExposures < 1:
    #         return None

    #     if nExposures > 3:
    #         nExposures = 3

    #     lstStart = jd2lmst(startTime)
    #     log.info('Starting observation of field locID={0} '.format(
    #         self.locationID) + '({1:.4f}, {2:.4f})'.format(
    #         self.fieldPK, self.centre.ra, self.centre.dec) +
    #         ' at LST={0:.4f} h'.format(lstStart.hour))

    #     # setsWithMissingDithers = self.plugging.getIncompleteSets()

    #     # tDelta = time.TimeDelta(ONE_EXPOSURE.hour * 3600, format='sec')
    #     # tDeltaSet = tDelta * NDITHERS()

    #     # if len(setsWithMissingDithers) > 0:
    #     #     endTime = startTime + tDelta
    #     #     lstEnd = jd2lmst(endTime)
    #     #     for ss in setsWithMissingDithers:
    #     #         limits = ss.HAlimits
    #     #         if self.isHAinRange(lstStart, limits) and \
    #     #                 self.isHAinRange(lstEnd, limits):
    #     #             ss.fixMissingDither(lstStart)
    #     #             return endTime

    #     return self.plugging.addSet(startTime=startTime, nExposures=nExposures)

    # def dateHAlimits(self, tt):

    #     mjd = int(tt.mjd)
    #     ha0Time = lmst2time(self.centre.ra.hour, mjd)
    #     delta = time.TimeDelta(self.HAlimits.hour * 3600 * uu.second)
    #     return delta + ha0Time

    # # def getCompletionTime(self, HA=0, direction='both'):

    # #     haArray = [0]

    # #     if direction == 'both':
    # #         for ii in range(1, 10):
    # #             haArray += [ii, -ii]
    # #     elif direction == 'forward':
    # #         for ii in range(1, 20):
    # #             haArray += [ii]
    # #     elif direction == 'backwards':
    # #         for ii in range(1, 20):
    # #             haArray += [-ii]

    # #     haArray = np.array(haArray, dtype=float)
    # #     haArray = HA + 15. * haArray * EXPTIME() / 3600. / EFFICIENCY()

    # #     airmasses = computeAirmass(self.plateCentre.dec.deg, haArray)

    # #     snRed = self.SN2_Red + np.cumsum(
    # #         AVG_SN_RED() / airmasses ** ALPHA_RED() / self.iIncrease)
    # #     snBlue = self.SN2_Blue + np.cumsum(
    # #         AVG_SN_BLUE() / airmasses ** ALPHA_BLUE() / self.gIncrease)

    # #     if snBlue[-1] < B_SN2() or snRed[-1] < R_SN2():
    # #         return None

    # #     idxRed = np.where(snRed >= R_SN2())[0][0]
    # #     idxBlue = np.where(snBlue >= B_SN2())[0][0]
    # #     idx = np.max([idxRed, idxBlue])

    # #     nExp = idx + 1
    # #     nExp = np.int(np.ceil(np.float(nExp) / NDITHERS()) * NDITHERS())

    # #     return nExp

    # # def addExposure(self, **kwargs):
    # #     """Adds an exposure to the field."""
    # #     self.exposures.append(Exposure(**kwargs))
    # #     self._updateCompletion()

    # def isDone(self):
    #     """Returns True if all the pluggings for the field are flagged good."""
    #     return areFielsdDone(self.fieldPK)

    # @property
    # def ID(self):
    #     return self.fieldPK

    # @ID.setter
    # def ID(self, value):
    #     self.fieldPK = value

    # def __repr__(self):
    #     return(
    #         '<Totoro.Field (designID={0:d}, RA={1:.4f}, Dec={2:.4f})>'.format(
    #             self.locationID, self.centre.ra, self.centre.dec)
    #         )
