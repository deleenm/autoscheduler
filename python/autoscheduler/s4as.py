# ---- SDSS-IV AUTOSCHEDULER ----
# DESCRIPTION: Wrapping layer to all 3 surveys' scheduling modules
#__author__ = 'Ben Thompson <b.a.thompson1@tcu.edu>'

# Import necessary modules
from __future__ import print_function, division
from autoscheduler import night_schedule, assign_carts
import autoscheduler.apogee as apg
import autoscheduler.eboss as ebo
import autoscheduler.manga as man
from time import time
import os

def run_scheduler(plan=False, mjd=-1, surveys=['apogee','eboss','manga'], loud=True):
	as_start_time = time()
	errors = []
	
	# Read in schedule file
	pwd = os.path.dirname(os.path.realpath(__file__))
	schedule_start_time = time()
	schedule = night_schedule.read_schedule(pwd, errors, mjd=mjd, surveys=surveys, loud=loud, plan=plan)
	schedule_end_time = time()
	if loud: print("[PY] Schedule read in complete (%.3f sec)" % (schedule_end_time - schedule_start_time))
	
	# Schedule surveys for tonight
	apogee_choices, manga_choices, eboss_choices = [], [], []
	# Schedule APOGEE-II

	if schedule['bright_start'] > 0:
                if schedule['manga_end'] > schedule['bright_end'] or schedule['eboss_end'] > schedule['bright_end']:
                        apogee_choices = apg.schedule_apogee(schedule, errors, plan=plan, loud=loud, twilight=True)
                else:
                        apogee_choices = apg.schedule_apogee(schedule, errors, plan=plan, loud=loud, twilight=False)
               
        else:
                apogee_choices = apg.schedule_apogee(schedule, errors, plan=plan, loud=loud, twilight=True)

	# Schedule MaNGA
	(manga_choices,manga_cart_order) = man.schedule_manga(schedule, errors, plan=plan, loud=loud)
	# Schedule eBOSS
	if schedule['eboss'] > 0:
		eboss_choices = ebo.schedule_eboss(schedule, errors, plan=plan, loud=loud)
	
	# Take results and assign to carts
	apgcart, mancart, ebocart = assign_carts.assign_carts(apogee_choices, manga_choices, eboss_choices, 
							      errors, manga_cart_order,loud=loud)
	
	as_end_time = time()
	if loud: print("[PY] run_scheduler complete in (%.3f sec)" % ((as_end_time - as_start_time)))
	
	plan = dict()
	# Reformat schedule dict for output
	plan['schedule'] = dict()
	plan['schedule']['mjd'] = schedule['jd'] - 2400000
	if schedule['bright_start'] > 0:
		plan['schedule']['apg_start'] = schedule['bright_start'] - 2400000
		plan['schedule']['apg_end'] = schedule['bright_end'] - 2400000
	if schedule['manga_start'] > 0:
		plan['schedule']['man_start'] = schedule['manga_start'] - 2400000
		plan['schedule']['man_end'] = schedule['manga_end'] - 2400000
	if schedule['eboss_start'] > 0:
		plan['schedule']['ebo_start'] = schedule['eboss_start'] - 2400000
		plan['schedule']['ebo_end'] = schedule['eboss_end'] - 2400000
	# Return cart assignments for chosen plates
	plan['apogee'] = apgcart
	plan['manga'] = mancart
	plan['eboss'] = ebocart
	plan['errors'] = errors
	return plan


