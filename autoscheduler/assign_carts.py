from __future__ import print_function, division
import numpy as np
import os

# ASSIGN_CARTS
# DESCRIPTION: Assigns all survey plate choices to cartridges
# INPUT: apogee_choices -- dictionary list containing all APOGEE-II plate choices for tonight
#		 manga_choices -- dictionary list containing all MaNGA plate choices for tonight
#		 eboss_choices -- dictionary list containing all eBOSS plate choices for tonight
# OUTPUT: plugplan -- dictionary list containing all plugging choices for tonight
def assign_carts(apogee_choices, manga_choices, eboss_choices):
	# Create database connection
	if (os.path.dirname(os.path.realpath(__file__))).find('utah.edu') >= 0: from sdss.internal.database.connections.UtahLocalConnection import db
	else: from sdss.internal.database.connections.APODatabaseUserLocalConnection import db
	session = db.Session()
		
	# Read in all available cartridges
	allcarts = session.execute("SET SCHEMA 'platedb'; "+
			"SELECT crt.number FROM platedb.cartridge AS crt "+
			"ORDER BY crt.number").fetchall()
	plugplan = []
	for c in allcarts:
		plugplan.append({'cart': c[0], 'cartsurveys': 0, 'oldplate': 0, 'plate': 0, 'obsmjd': float(0.0), 'exposure_length': float(0.0), 'first_backup': 0, 'second_backup': 0})
		if c[0] < 10: plugplan[-1]['cartsurveys'] = 1
		if c[0] >= 10: plugplan[-1]['cartsurveys'] = 2
		if c[0] == 2: plugplan[-1]['cartsurveys'] = 3
	
	# Read in all plates that are currently plugged
	currentplug = session.execute("SET SCHEMA 'platedb'; "+
		"SELECT crt.number, plt.pk "+
		"FROM (((((platedb.active_plugging AS ac "+
			"JOIN platedb.plugging AS plg ON (ac.plugging_pk=plg.pk)) "+
			"LEFT JOIN platedb.cartridge AS crt ON (plg.cartridge_pk=crt.pk)) "+
			"LEFT JOIN platedb.plate AS plt ON (plg.plate_pk=plt.pk)) "+
			"LEFT JOIN platedb.plate_to_survey AS p2s ON (p2s.plate_pk=plt.pk)) "+
			"LEFT JOIN platedb.plate_pointing as pltg ON (pltg.plate_pk=plt.pk)) "+
		"ORDER BY crt.number").fetchall()
	for c,p in currentplug:
		wcart = [x for x in range(len(plugplan)) if plugplan[x]['cart'] == c][0]
		plugplan[wcart]['oldplate'] = p
		
	# Save MaNGA choices to cartridges (since they are the most dependent)
	# TO-DO
	
	# Save APOGEE-II choices to cartridges
	apgsaved = np.zeros(len(apogee_choices))
	# First loop: assign plates to carts which are already plugged
	for i in range(len(apogee_choices)):
		wplate = [x for x in range(len(plugplan)) if apogee_choices[i]['plate'] == plugplan[x]['oldplate']]
		if len(wplate) == 0: continue
		# Save new values to plugplan
		plugplan[wplate[0]]['plate'] = apogee_choices[i]['plate']
		plugplan[wplate[0]]['first_backup'] = apogee_choices[i]['first_backup']
		plugplan[wplate[0]]['second_backup'] = apogee_choices[i]['second_backup']
		plugplan[wplate[0]]['obsmjd'] = apogee_choices[i]['obstime']
		plugplan[wplate[0]]['exposure_length'] = apogee_choices[i]['explength']
		apgsaved[i] = 1
	# Second loop: assign plates to carts which are replugs
	for i in range(len(apogee_choices)):
		if apgsaved[i] == 1: continue
		carts_avail = [x for x in range(len(plugplan)) if plugplan[x]['plate'] == 0 and (plugplan[x]['cartsurveys'] == 1 or plugplan[x]['cartsurveys'] == 3)]
		if len(carts_avail) == 0: continue
		# Save new values to plugplan
		plugplan[carts_avail[0]]['plate'] = apogee_choices[i]['plate']
		plugplan[carts_avail[0]]['first_backup'] = apogee_choices[i]['first_backup']
		plugplan[carts_avail[0]]['second_backup'] = apogee_choices[i]['second_backup']
		plugplan[carts_avail[0]]['obsmjd'] = apogee_choices[i]['obstime']
		plugplan[carts_avail[0]]['exposure_length'] = apogee_choices[i]['explength']
	
	return plugplan
		