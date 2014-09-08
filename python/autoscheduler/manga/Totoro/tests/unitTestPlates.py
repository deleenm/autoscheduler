#!/usr/bin/env python
# encoding: utf-8
"""
unitTestPlates.py

Created by José Sánchez-Gallego on 27 Aug 2014.
Licensed under a 3-clause BSD license.

Revision history:
    27 Aug 2014 J. Sánchez-Gallego
      Initial version

"""

from __future__ import division
from __future__ import print_function
import unittest
from Totoro.dbclasses import Plate


class plateTestCase(unittest.TestCase):

    def testPlateLoadWithPK(self):

        platePK = 11147
        plate = Plate(platePK, sets=False)

        self.assertEqual(plate.plate_id, 7990)

    def testPlateLoadWithPlateID(self):

        plateID = 7815
        plate1 = Plate(plateID, format='plate_id', sets=False)
        plate2 = Plate.fromPlateID(plateID, sets=False)

        self.assertEqual(plate1.comment, '060-25_MGA')
        self.assertEqual(plate2.location_id, 3760)

    def testPlateCoordinates(self):

        plateID = 7815
        plate = Plate.fromPlateID(plateID, sets=False)

        self.assertAlmostEqual(plate.coords[0], 317.95449707, places=4)
        self.assertAlmostEqual(plate.coords[1], 10.1960287094, places=4)

    def testIsPlugged(self):

        plate = Plate.fromPlateID(7443, sets=False)
        self.assertEqual(plate.isPlugged, False)

    def testMangadbExposures(self):

        plate = Plate.fromPlateID(7815, sets=False)
        self.assertEqual(len(plate.getMangadbExposures()), 18)
        self.assertEqual(len(plate.getMangadbExposures()),
                         len(plate.getScienceExposures()))


if __name__ == '__main__':
    unittest.main()
