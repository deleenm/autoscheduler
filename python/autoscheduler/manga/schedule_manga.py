from __future__ import print_function, division
from Totoro.scheduler import Plugger
from Totoro.dbclasses import getPlugged
from Totoro import config


def schedule_manga(schedule, errors, plan=False, loud=True):
    plates = []
    if plan:
        try:
            manga_obj = Plugger(startDate=schedule['manga_start'],
                                endDate=schedule['manga_end'])
            manga_output = manga_obj.getASOutput()
            manga_cart_order = manga_output.pop('cart_order')

            for k, v in manga_output.iteritems():
                plates.append({'plateid': v, 'cart': k})

        except Exception as e:
            errors.append('MANGA: %s' % e)

    else:
        try:
            manga_obj = getPlugged()
            manga_output = [(plate.getActiveCartNumber(), plate.plate_id)
                            for plate in manga_obj]

            # Creates the cart order list. We put plugged plates at the end of
            # the list.
            if len(manga_obj) > 0:
                usedCarts = zip(*manga_output)[0]
            else:
                usedCarts = []
            allCarts = (config['apogeeCarts'] + config['offlineCarts'] +
                        [cart for cart in config['mangaCarts']
                         if cart not in config['offlineCarts']])
            manga_cart_order = []
            for cart in allCarts:
                if cart not in usedCarts:
                    manga_cart_order.append(cart)
            manga_cart_order += usedCarts

            for k, v in dict(manga_output).iteritems():
                plates.append({'plateid': v, 'cart': k})

        except Exception as e:
            errors.append('MANGA: %s' % e)

        # Get raw output from MaNGA submodule
        #manga_obj = Nightly(startDate=schedule['manga_start'], endDate=schedule['manga_end'])
        #manga_output = manga_obj.getOutput()

        # Massage the MaNGA 'plates' output into a usable format
        #for plate_id, plate_data in manga_output['plates'].iteritems():
            #plate_dict = {}
            #plate_dict['plateid'] = plate_id
            #if 'cartridge' in plate_data.keys():
                #plate_dict['cart'] = plate_data['cartridge']
            #else: plate_dict['cart'] = -1
            #plate_dict['complete'] = plate_data['complete']
            #plate_dict['HARange'] = list(plate_data['HARange'])
            #plate_dict['SN2'] = list(plate_data['SN2'])
            ## Completed Sets for this plate
            #plate_dict['sets'] = []
            #for set_pk, set_data in plate_data['sets'].iteritems():
            #   set_dict = {}
            #   set_dict['setpk'] = set_pk
            #   set_dict['complete'] = set_data['complete']
            #   set_dict['averageSeeing'] = set_data['averageSeeing']
            #   set_dict['SN2'] = list(set_data['SN2'])
            #   set_dict['SN2Range'] = [list(set_data['SN2Range'][0]), list(set_data['SN2Range'][1])]
            #   set_dict['seeingRange'] = list(set_data['seeingRange'])
#
            #   haRange = set_data['HARange']
            #   set_dict['HARange'] = haRange if haRange is False else list(set_data['HARange'])
#
            #   set_dict['missingDithers'] = list(set_data['missingDithers'])
            #   set_dict['exposures'] = []
            #   # Exposures contained within dither set
            #   for exp_pk, exp_data in set_data['exposures'].iteritems():
            #       exp_dict = {}
            #       exp_dict['exp_pk'] = exp_pk
            #       exp_dict['valid'] = exp_data['valid']
            #       exp_dict['ditherPosition'] = exp_data['ditherPosition']
            #       exp_dict['HARange'] = list(exp_data['obsHARange'])
            #       exp_dict['seeing'] = exp_data['seeing']
            #       exp_dict['SN2'] = list(exp_data['SN2'])
            #       set_dict['exposures'].append(exp_dict)
            #   plate_dict['sets'].append(set_dict)
            #plates.append(plate_dict)

    manga_formatted = plates

    return manga_formatted, manga_cart_order
