from __future__ import print_function, division
from time import time
import os
import sqlalchemy
import numpy as np
from sdss.apogee.plate_completion import completion

# DESCRIPTION: APOGEE Plate Object
class apgplate(object):
	# Identifying plate information
	def __init__(self,plate=None):
		if plate is None: 
			raise Exception("Somehow tried to make plate object without a plate")
		#properties we get from plate object
		self.plate = plate
		self.name = plate.name
		self.locationid = plate.location_id
		self.plateid = plate.plate_id
		self.platepk = plate.pk
		self.ddict= plate.design.designDictionary
		#plate_loc is physical location, and may never be used
		self.plate_loc = plate.location.label
		
		#NOTE FROM JOHN: ddict contains RA, DEC, and survey info
		#if this runs slowly, use ddict to set these
		self._ra = None
		self._dec = None
		self._ha = None
		self._maxha = None
		self._minha = None
		self._manual_priority = None
		self._plugged = None

		self._exp_time = None
		self._lead_survey = None
		self._coobs = None

		#catch values not set properly
		if 'apogee_design_type' in self.ddict:
			self.cadence = self.ddict['apogee_design_type']
			self.driver = self.ddict['apogee_design_driver']
			self.vplan = int(self.ddict['apogee_n_design_visits'])
			self.apgver = 100*int(self.ddict['apogee_short_version']) + 10*int(self.ddict['apogee_med_version']) + int(self.ddict['apogee_long_version'])
		else:
			self.cadence = 'default'
			self.driver = 'default'
			self.vplan = 3
			self.apgver = 999

		#properties requiring plate_completion method
		self.vdone = 0
		self.sn = 0.0
		self.hist = ''

		#ben sets these but doesn't use them outside of get_plates; not needed?
		# self.snql = 0.0
		# self.snred = 0.0
		# self.reduction = ''

		#properties not set in get_plates
		self.priority = 0.0
		self.stack = 0


#----------------------------
#properties
#----------------------------
	@property 
	def ra(self):
		if self._ra is None:
			self._ra = float(self.plate.firstPointing.center_ra)
		return self._ra

	@property 
	def dec(self):
		if self._dec is None:
			self._dec = float(self.plate.firstPointing.center_dec)
		return self._dec

	@property 
	def ha(self):
		if self._ha is None:
			self._ha = float(self.plate.firstPointing.platePointing(self.plate.plate_id).hour_angle)
		return self._ha

	@property 
	def maxha(self):
		if self._maxha is None:
			self._maxha = float(self.plate.firstPointing.platePointing(self.plate.plate_id).ha_observable_max) + 7.5
		return self._maxha

	@property 
	def minha(self):
		if self._minha is None:
			self._minha = float(self.plate.firstPointing.platePointing(self.plate.plate_id).ha_observable_min) - 7.5
		return self._minha

	@property 
	def manual_priority(self):
		if self._manual_priority is None:
			self._manual_priority = float(self.plate.firstPointing.platePointing(self.plate.plate_id).priority)
		return self._manual_priority

	@property 
	def plugged(self):
		if self._plugged is None:
			self._plugged = 0
			for p in self.plate.pluggings:
				if len(p.activePlugging) >0:
					self._plugged = p.cartridge.number
		return self._plugged

	@property 
	def lead_survey(self):
		if self._lead_survey is None:
			if self.plate.currentSurveyMode is None:
				self._lead_survey = 'apg'
			elif self.plate.currentSurveyMode.label == 'APOGEE lead': 
				self._lead_survey = 'apg'
			else: 
				self._lead_survey = 'man'
		return self._lead_survey	

	@property 
	def exp_time(self):
		if self._exp_time is None:
			if "apogee_exposure_time" in self.ddict: 
				self._exp_time = float(self.ddict['apogee_exposure_time'])
			elif self.lead_survey == 'apg': 
				self._exp_time = 500.0
			else: self._exp_time = 450.0
		return self._exp_time

	@property 
	def coobs(self):
		if self._coobs is None:
			if 'MANGA' in self.ddict['instruments']:
				self._coobs = True
			else: self._coobs = False
		return self._coobs

#----------------------------
#useful methods
#----------------------------
	# Determine most recent observation time
	def maxhist(self):
		obsstr = self.hist.split(',')
		if len(obsstr) == 0 or obsstr[0] == '': return float(0.0)
		obshist = [float(x) for x in obsstr if x != '']
		return max(obshist)
		
	# Determine first observation time
	def minhist(self):
		obsstr = self.hist.split(',')
		if len(obsstr) == 0 or obsstr[0] == '': return float(0.0)
		obshist = [float(x) for x in obsstr if x != '']
		return min(obshist)
		
	# Determine plate completion percentage (from algorithm in the SDSS python module)
	def pct(self):
		return completion(self.vplan, self.vdone, self.sn, self.cadence)

	# def pct(self):
	# 	''' Computes completion percentage of APOGEE-II plate '''
	#     # Something is wrong here...
	# 	if self.vplan == 0: return 1

	# 	try:
	# 		# 90% of completion percentage is from number of visits
	# 		visit_completion = 0.9 * min([1, self.vdone / self.vplan])
	# 		# 10% of completion percentage is from S/N
	# 		sn_completion = 0.1 * calculateSnCompletion(self.vplan, self.sn)
	# 		return visit_completion + sn_completion
	# 	except:
	# 		raise RuntimeError("ERROR: unable to calculate completion for vplan: %d, vdone: %d, sn: %d\n%s" %\
	# 			(self.vplan, self.vdone, self.sn, sys.exc_info()))


def get_plates(errors, plan=False, loud=True, session=None, atapo=True, allPlates=False):
	'''DESCRIPTION: Reads in APOGEE-II plate information from platedb
	INPUT: None
	OUTPUT: apg -- list of objects with all APOGEE-II plate information'''
	if session is None:
		# Create database connection
		if (os.path.dirname(os.path.realpath(__file__))).find('utah.edu') >= 0: 
			from sdss.internal.database.connections.UtahLocalConnection import db
		else: 
			from sdss.internal.database.connections.APODatabaseUserLocalConnection import db
		session = db.Session()
	from sdss.internal.database.apo.platedb import ModelClasses as pdb
	from sdss.internal.database.apo.apogeeqldb import ModelClasses as qldb

	try:
		acceptedStatus=session.query(pdb.PlateStatus).filter(pdb.PlateStatus.label=="Accepted").one()
	except sqlalchemy.orm.exc.NoResultFound:
		raise Exception("Could not find 'Accepted' status in plate_status table")

	try:
		survey=session.query(pdb.Survey).filter(pdb.Survey.label=="APOGEE-2").one()
	except sqlalchemy.orm.exc.NoResultFound:
		raise Exception("Could not find 'APOGEE-2' survey in survey table")

	try:
		plateLoc=session.query(pdb.PlateLocation).filter(pdb.PlateLocation.label=="APO").one()
	except sqlalchemy.orm.exc.NoResultFound:
		raise Exception("Could not find 'APO' location in plate_location table")

	# Pull all relevant plate information for APOGEE plates
	with session.begin():
		if plan:
			plates=session.query(pdb.Plate)\
				   .join(pdb.PlateToSurvey, pdb.Survey)\
				   .join(pdb.PlateLocation)\
				   .join(pdb.PlateToPlateStatus,pdb.PlateStatus)\
				   .filter(pdb.Survey.pk == survey.pk)\
				   .filter(pdb.Plate.location==plateLoc)\
				   .filter(pdb.PlateStatus.pk ==acceptedStatus.pk).all()
		elif allPlates:
			plates=session.query(pdb.Plate)\
			   .join(pdb.PlateToSurvey, pdb.Survey)\
			   .filter(pdb.Survey.pk == survey.pk).all()
		else:
			plates=session.query(pdb.Plate)\
				   .join(pdb.PlateToSurvey, pdb.Survey)\
				   .join(pdb.Plugging,pdb.Cartridge)\
				   .join(pdb.ActivePlugging)\
				   .filter(pdb.Survey.pk == survey.pk)\
				   .order_by(pdb.Cartridge.number).all()

	#create the list of apg plate objects
	apg = list()
	for plate in plates:
		tmpPlate=apgplate(plate)
		if allPlates: apg.append(tmpPlate)
		else: 
			if tmpPlate.lead_survey == 'apg':
				apg.append(tmpPlate)


	with session.begin():
		#returns list of tuples (mjd,plateid,qrRed,fullRed)
		exposures=session.query(sqlalchemy.func.floor(pdb.Exposure.start_time/86400+.3),pdb.Plate.plate_id,\
			qldb.Quickred.snr_standard,qldb.Reduction.snr)\
		.join(pdb.Survey).join(pdb.ExposureFlavor)\
		.join(pdb.Observation).join(pdb.PlatePointing).join(pdb.Plate)\
		.outerjoin(qldb.Quickred).outerjoin(qldb.Reduction)\
		.filter(pdb.Survey.label == 'APOGEE-2' ).filter(pdb.ExposureFlavor.label == 'Object').all()


	exposures_tab = np.array(exposures)
	fullRedCheck = np.copy([exposures_tab[:,0],exposures_tab[:,1],[x[3] if x[3] is not None else x[2] for x in exposures_tab]]).swapaxes(0,1)

	good_exp = fullRedCheck[fullRedCheck[:,2]>10]

	plateidDict = dict()

	for i,p in enumerate(apg): 
		plateidDict[p.plateid] = i

	for p in apg:
		if p.hist != '' and p.vdone != 0: continue
		repeat = []
		#find plates that share location and cohort
		for pl in apg:
			if p.plateid == pl.plateid: continue
			if p.locationid == pl.locationid:
				if p.apgver == pl.apgver: repeat.append(pl.plateid)
		if repeat != []:
			repeat.append(p.plateid)		
			plateExps = good_exp[np.in1d(good_exp[:,1], repeat)]
			dates = np.unique(plateExps[:,0])
			for d in dates:
				day = plateExps[plateExps[:,0] == d]
				if day.shape[0] >= 2: 
					for r in repeat:
						apg[plateidDict[r]].hist += '{},'.format(d)
						apg[plateidDict[r]].vdone += 1
						apg[plateidDict[r]].sn += float(np.sum(day[:,2]**2))
		else:
			plateExps = good_exp[good_exp[:,1] == p.plateid]
			dates = np.unique(plateExps[:,0])
			for d in dates:
				day = plateExps[plateExps[:,0] == d]
				if day.shape[0] >= 2: 
					p.hist += '{},'.format(d)
					p.vdone += 1
					p.sn += float(np.sum(day[:,2]**2))

	return apg