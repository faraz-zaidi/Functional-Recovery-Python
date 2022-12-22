'''
Other functionality functions
'''

def fn_building_safety(damage, building_model, damage_consequences, utilities,
                       functionality_options):
    '''Check damage that would cause the whole building to be shut down due to
     issues of safety
    
    Parameters
    ----------
    damage: dictionary
     contains per damage state damage, loss, and repair time data for each 
     component in the building
    
    damage_consequences: dictionary
     data structure containing simulated building consequences, such as red
     tags and repair costs ratios
     
    building_model: dictionary
     general attributes of the building model
     
    utilities: dictionary
     data structure containing simulated utility downtimes
     
    functionality_options: dictionary
     recovery time optional inputs such as various damage thresholds
    
    Returns
    -------
    recovery_day: dictionary
     simulation of the number of days each fault tree event is affecting building
     safety
     
    comp_breakdowns: dictionary
     simulation of each components contributions to each of the fault tree events 
     
    system_operation_day: dictionary
     simulation of recovery of operation for various systems in the building'''
    
    import numpy as np
    ## Initial Setup
    num_reals = len(damage_consequences['red_tag'])
    num_units = len(damage['tenant_units'])
    num_comps = len(damage['comp_ds_table']['comp_id'])
    
    ## Calculate effect of red tags and fire suppression system
    # Initialize parameters
    recovery_day = {'red_tag' : np.zeros(num_reals), 'hazardous_material' : np.zeros(num_reals)}
    system_operation_day = {'building' : {'fire' : 0}}
 
    # Check damage throughout the building
    comp_breakdowns = {'red_tag':np.empty([num_reals,num_comps,num_units])}
    system_operation_day['comp'] = {'fire' : np.empty([num_reals,num_comps,num_units])}
    for tu in range(num_units):
        # Grab tenant and damage info for this tenant unit
        repair_complete_day = damage['tenant_units'][tu]['recovery']['repair_complete_day']
        
        ## Red Tags
        # The day the red tag is resolved is the day when all damage (anywhere in building) that has
        # the potential to cause a red tag is fixed (ie max day)
        if any(damage['fnc_filters']['red_tag']):
            recovery_day['red_tag'] = np.fmax(recovery_day['red_tag'],
                                          np.array(damage_consequences['red_tag'])*np.nanmax(repair_complete_day[:,damage['fnc_filters']['red_tag']], axis=1))
   
        # Component Breakdowns
        
        
        comp_breakdowns['red_tag'][:,:,tu] = damage['fnc_filters']['red_tag'].reshape(1,len(damage['fnc_filters']['red_tag'])) * recovery_day['red_tag'].reshape(len(recovery_day['red_tag']),1)
        
        ## Day the fire suppression system is operating again (for the whole building)
        if np.sum(damage['fnc_filters']['fire_building']) > 0:
            # any major damage fails the system for the whole building so take the max
            system_operation_day['building']['fire'] = np.fmax(system_operation_day['building']['fire'], np.nanmax(repair_complete_day[:,damage['fnc_filters']['fire_building']], axis=1))
        
        # Consider utilities
        system_operation_day['building']['fire'] = np.fmax(system_operation_day['building']['fire'], np.array(utilities['water'])) # Assumes building does not have backup water supply
        
        # Component Breakdowns
        system_operation_day['comp']['fire'][:,:,tu] = damage['fnc_filters']['fire_building']*repair_complete_day
        
        ## Hazardous Materials
        # note: hazardous materials are accounted for in building functional
        #assessment here, but are not currently quantified in the component
        # breakdowns
        if any(damage['fnc_filters']['global_hazardous_material']):
            # Any global hazardous material shuts down the entire building
            recovery_day['hazardous_material'] = np.fmax(recovery_day['hazardous_material'], np.amax(repair_complete_day[:,damage['fnc_filters']['global_hazardous_material']], axis=1))

    
    ## Building Egress
    '''Calculate when falling hazards or racking of doors affects the building
    safety due to limited entrance and exit door access'''
    
    '''Simulate a random location of the doors on two sides of the building for
    each realization. Location is defined at the center of the door as a
    fraction of the building width on that side
    This is acting a random p value to determine if the unknown location of
    the door is within the falling hazard zone'''
    
    door_location = np.random.rand(num_reals , building_model['num_entry_doors'])
    
    # Assign odd doors to side 1 and even doors to side two
    door_numbers = np.linspace(1,building_model['num_entry_doors'], building_model['num_entry_doors'])
    door_side = np.ones(building_model['num_entry_doors'])
    door_side[np.remainder(door_numbers, 2) == 0] = 2
    door_side = door_side.astype('int')
    
    # Determine the quantity of falling hazard damage and when it will be resolved
    day_repair_fall_haz = np.zeros([num_reals,building_model['num_entry_doors']])
    fall_haz_comps_day_rep = np.zeros([num_reals,num_comps,num_units,building_model['num_entry_doors']])
    comp_affected_area = np.zeros([num_reals,num_comps,num_units])
    
    repair_complete_day_w_tmp = np.empty([num_reals,num_comps,num_units])
    for tu in range(num_units):
        repair_complete_day_w_tmp[:,:,tu] = damage['tenant_units'][tu]['recovery']['repair_complete_day_w_tmp']

    
    # Loop through component repair times to determine the day it stops affecting re-occupancy
    num_repair_time_increments = np.sum(damage['fnc_filters']['ext_fall_haz_all'])*num_units # possible unique number of loop increments
    edge_lengths = np.transpose(np.column_stack((np.array(building_model['edge_lengths']), np.array(building_model['edge_lengths']))))
    
    affected_ratio={}
    for side in range(4):
        affected_ratio['side_'+str(side+1)]=np.zeros([num_reals, num_units]) #FZ# Initiated with zeros. Check later if it works
    for i in range(num_repair_time_increments):
        # Calculate the falling hazards per side
        for tu in range(num_units):
            for side in range(4): # assumes there are 4 sides
                area_affected_lf_all_comps = damage['comp_ds_table']['fraction_area_affected'] * damage['comp_ds_table']['unit_qty'] * building_model['ht_per_story_ft'][tu] * damage['tenant_units'][tu]['qnt_damaged_side_'+str(side+1)] #FZ# +1 done to account for python indexing starting with 0. 
    
                area_affected_sf_all_comps = damage['comp_ds_table']['fraction_area_affected'] * damage['comp_ds_table']['unit_qty'] * damage['tenant_units'][tu]['qnt_damaged_side_' + str(side+1)]
    
                comp_affected_area[:,damage['fnc_filters']['ext_fall_haz_lf'],tu] = area_affected_lf_all_comps[:,damage['fnc_filters']['ext_fall_haz_lf']]
                comp_affected_area[:,damage['fnc_filters']['ext_fall_haz_sf'],tu] = area_affected_sf_all_comps[:,damage['fnc_filters']['ext_fall_haz_sf']]
    
                comp_affected_ft_this_story = comp_affected_area[:,:,tu] / building_model['ht_per_story_ft'][tu]
                affected_ft_this_story = np.sum(comp_affected_ft_this_story,axis = 1) # Assumes cladding components do not occupy the same perimeter space
                
                affected_ratio['side_'+str(side+1)][:,tu] = np.minimum((affected_ft_this_story)/ edge_lengths[side,tu],1)

    
        # Calculate the time increment for this loop
        delta_day = np.nanmin(np.nanmin(repair_complete_day_w_tmp[:,damage['fnc_filters']['ext_fall_haz_all'],:],axis =2), axis=1)
        delta_day[np.isnan(delta_day)] = 0
        if sum(delta_day) == 0:
            break # everything has been fixed
        
        
        # Go through each door to determine which is affected by falling
        # hazards
        for d in range(building_model['num_entry_doors']):
            # Combine affected areas of all stories above the first using SRSS
            # HARDCODED ASSUMPTIONS: DOORS ONLY ON TWO SIDES
            fall_haz_zone = np.minimum(np.sqrt(np.sum(affected_ratio['side_'+str(door_side[d])][:,1:num_units]**2, axis=1)),1)
    
            '''Augment the falling hazard zone with the door access zone
            add the door access width to the width of falling hazards to account
            for the width of the door (ie if any part of the door access zone is
            under the falling hazard, its a problem)'''
            door_access_zone = functionality_options['door_access_width_ft'] / building_model['edge_lengths'][0][door_side[d]-1] #FZ# -1 done to account for python indexing starting from zero
            total_fall_haz_zone = fall_haz_zone + 2*door_access_zone # this is approximating the probability the door is within the falling hazard zone
    
            '''Determine if current damage affects occupancy
            if the randonmly simulated door location is with falling hazard zone'''
            affects_door = door_location[:,door_side[d]-1] < total_fall_haz_zone #FZ# -1 done to account for python indexing starting from zero
    
            # Add days in this increment to the tally
            day_repair_fall_haz[:,d] = day_repair_fall_haz[:,d] + affects_door * delta_day
    
            # Add days to components that are affecting occupancy
            fall_haz_comps_day_rep[:,:,:,d] = fall_haz_comps_day_rep[:,:,:,d] + ((comp_affected_area.transpose(2,0,1) * damage['fnc_filters']['ext_fall_haz_all'].reshape(1, num_comps)) * (affects_door * delta_day).reshape(num_reals,1)).transpose(1,2,0) #FZ# Transpose and reshape done to align nd arrays
        
        
        # Change the comps for the next increment
        repair_complete_day_w_tmp = (repair_complete_day_w_tmp.transpose(2,0,1) - delta_day.reshape(num_reals,1)).transpose(1,2,0)
        repair_complete_day_w_tmp[repair_complete_day_w_tmp <= 0] = np.nan

    
    # Determine when racked doors are resolved
    day_repair_racked = np.zeros([num_reals, building_model['num_entry_doors']])
    side_1_count = 0
    side_2_count = 0
    for d in range(building_model['num_entry_doors']):
        if door_side[d] == 1:
            side_1_count = side_1_count + 1
            day_repair_racked[:,d] = functionality_options['door_racking_repair_day'] * (np.array(damage_consequences['racked_entry_doors_side_1']) >= side_1_count)
        else:
            side_2_count = side_2_count + 1
            day_repair_racked[:,d] = functionality_options['door_racking_repair_day'] * (np.array(damage_consequences['racked_entry_doors_side_2']) >= side_2_count)

    door_access_day = np.fmax(day_repair_racked, day_repair_fall_haz)
    
    '''Find the days until door egress is regained from resolution of both
    falling hazards or door racking'''
    cum_days = np.zeros(num_reals)
    recovery_day['entry_door_access'] = np.zeros(num_reals)
    door_access_day_nan = door_access_day #FZ# Be cautious! Numpy arrays are mutable
    door_access_day_nan[door_access_day_nan == 0] = np.nan
    num_repair_time_increments = np.array(building_model['num_entry_doors']) # possible unique number of loop increments
    for i in range(num_repair_time_increments):
        
        door_access_day[np.isnan(door_access_day)] = 0 #FZ# Line added to circumvent the issue of mutable numpy array
        
        num_accessible_doors = np.sum(door_access_day <= cum_days.reshape(num_reals,1), axis=1)
        
        if i==0:   
            door_access_day_nan[door_access_day_nan == 0] = np.nan #FZ# Line added to circumvent the issue of mutable numpy array
        
        sufficent_door_access_with_fs  = num_accessible_doors >= max(1,functionality_options['egress_threshold'] * building_model['num_entry_doors'])   # must have at least 1 functioning entry door or 50% of design egress
        sufficent_door_access_wo_fs = num_accessible_doors >= max(1,functionality_options['egress_threshold_wo_fs'] * building_model['num_entry_doors'])  # must have at least 1 functioning entry door or 75% of design egress when fire suppression system is down
        fire_system_failure = system_operation_day['building']['fire'] > cum_days
        entry_door_accessible = sufficent_door_access_with_fs * np.logical_not(fire_system_failure) + sufficent_door_access_wo_fs * fire_system_failure
        
        if i == 0: # just save on the initial loop #FZ# Made zero to account for python indexing starting from 0
            fs_operation_matters_for_entry_doors = 1*sufficent_door_access_with_fs - 1*sufficent_door_access_wo_fs

                
        delta_day = np.nanmin(door_access_day_nan,axis=1)
        delta_day[np.isnan(delta_day)] = 0
        door_access_day_nan = door_access_day_nan - delta_day.reshape(num_reals,1)
        cum_days = cum_days + delta_day
        
        recovery_day['entry_door_access'] = recovery_day['entry_door_access'] + delta_day * np.logical_not(entry_door_accessible)

    
    # Determine when Exterior Falling Hazards or doors actually contribute to re-occupancy
    recovery_day['falling_hazard'] = np.minimum(recovery_day['entry_door_access'], np.nanmax(day_repair_fall_haz, axis=1))
    recovery_day['entry_door_racking'] = np.minimum(recovery_day['entry_door_access'], np.nanmax(day_repair_racked,axis=1))
    
    # Component Breakdown
    comp_breakdowns['falling_hazard'] = (np.minimum(recovery_day['entry_door_access'], (np.nanmax(fall_haz_comps_day_rep, axis=3)).transpose(2,1,0))).transpose(2,1,0) #FZ# Transpose done to align the nd array fopr operation
    
    ## Determine when fire suppresion affects recovery
    if any(damage['fnc_filters']['fire_building']): # only safe this when fire system exists
        recovery_day['fire_egress'] = system_operation_day['building']['fire'] * fs_operation_matters_for_entry_doors
        comp_breakdowns['fire_egress'] = (system_operation_day['comp']['fire'].transpose(2,1,0) * fs_operation_matters_for_entry_doors).transpose(2,1,0)
        

    return recovery_day, comp_breakdowns, system_operation_day


def fn_story_access(damage, building_model, damage_consequences, 
                    system_operation_day, subsystems, functionality_options):
    
    '''Check each story for damage that would cause that story to be shut down due to
    issues of access
    
    Parameters
    ----------
    damage: dictionary
     contains per damage state damage, loss, and repair time data for each 
     component in the building
     
    building_model: dictionary
     general attributes of the building model
     
    damage_consequences: dictionary
     data structure containing simulated building consequences, such as red
     tags and repair costs ratios
     
    system_operation_day: dictionary
     simulation of recovery of operation for various systems in the building
     
    subsystems: DataFrame
     data table containing information about each subsystem's attributes
     
    functionality_options: dictionary
     recovery time optional inputs such as various damage thresholds
    
    Returns
    -------
    recovery_day: dictionary
     simulation of the number of days each fault tree event is affecting access
     in each story
     
    comp_breakdowns: dictionary
     simulation of each components contributions to each of the fault tree events''' 
    
    import numpy as np
    
    ## Initial Setup
    num_reals = len(damage_consequences['red_tag'])
    num_units = len(damage['tenant_units'])
    num_stories = len(damage['tenant_units'])
    num_comps = len(damage['comp_ds_table']['comp_id'])
    
    # Pre-allocate data
    recovery_day={}
    comp_breakdowns={}
    recovery_day['stairs'] = np.zeros([num_reals,num_units])
    recovery_day['stair_doors'] = np.zeros([num_reals,num_units])
    comp_breakdowns['stairs'] = np.zeros([num_reals,num_comps,num_units])
    recovery_day['fire_egress'] = np.zeros([num_reals,num_units])
    
    
    # Go through each story and check if there is sufficient story access (stairs and stairdoors)
    if num_stories == 1: 
        return recovery_day, comp_breakdowns # Re-occupancy of one story buildigns is not affected by stairway access

    
    # Augment damage filters with door data
    damage['fnc_filters']['stairs'] = np.append(damage['fnc_filters']['stairs'], np.array([False]))
    damage['fnc_filters']['fire_drops'] = np.append(damage['fnc_filters']['fire_drops'], np.array([False]))
    damage['fnc_filters']['fire_building'] = np.append(damage['fnc_filters']['fire_building'], np.array([False]))
    damage['fnc_filters']['stair_doors'] = np.append(np.zeros(num_comps), 1).astype(dtype=bool)
    
    # check if building has fire supprsion system
    # must have both the building level (pipes) and tenant level (drops)components
    fs_exists = np.logical_and(np.any(damage['fnc_filters']['fire_building']), np.any(damage['fnc_filters']['fire_drops']))
    
    ## Stairs
    # if stairs don't exist on a story, this will assume they are rugged (along with the stair doors)
    for tu in range(num_stories):
        # Augment damage matrix with door data
        damage['tenant_units'][tu]['num_comps'].append(building_model['stairs_per_story'][tu])
        racked_stair_doors = np.minimum(np.array(damage_consequences['racked_stair_doors_per_story'])[:,tu], building_model['stairs_per_story'][tu])
        damage['tenant_units'][tu]['qnt_damaged'] = (np.column_stack((np.array(damage['tenant_units'][tu]['qnt_damaged']), racked_stair_doors))).tolist() #FZ# Converted back to alist to keep it consistent with other objects in the dictionary damage['tenant_units'][tu]
        door_repair_day = 1*(racked_stair_doors > 0) * functionality_options['door_racking_repair_day']
        damage['tenant_units'][tu]['recovery']['repair_complete_day'] = np.column_stack((damage['tenant_units'][tu]['recovery']['repair_complete_day'], door_repair_day))
    
        # Quantify damaged stairs on this story
        repair_complete_day = damage['tenant_units'][tu]['recovery']['repair_complete_day']
        damaged_comps = np.array(damage['tenant_units'][tu]['qnt_damaged'])
        total_num_fs_drops = np.array(damage['tenant_units'][tu]['num_comps']) * damage['fnc_filters']['fire_drops']
    
        '''Replace story level repair day with building level for fire suppression system mains
        This includes loss of utility, so its not just about component
        damage, although its assigned to specific components. It would be
        better to add utilities to the damage matrix'''
        if fs_exists: # only do this if the building has a fire suppression system
            repair_complete_day[:,damage['fnc_filters']['fire_building']] = system_operation_day['building']['fire'].reshape(len(system_operation_day['building']['fire']),1)
            damaged_comps[:,damage['fnc_filters']['fire_building']] = system_operation_day['building']['fire'].reshape(len(system_operation_day['building']['fire']),1) > 0
            fire_access_day = np.zeros(num_reals) # day story becomes accessible from repair of fire suppression system
        
    
        # Make sure zero repair days are NaN
        repair_complete_day[repair_complete_day == 0] = np.nan
    
        '''Step through each unique component repair time and determine when
        stairs stop affecting story access'''
        stair_access_day = np.zeros(num_reals) # day story becomes accessible from repair of stairs
        stairdoor_access_day = np.zeros(num_reals) # day story becomes accessible from repair of doors
        filt_all = damage['fnc_filters']['stairs'] | damage['fnc_filters']['fire_drops'] | damage['fnc_filters']['stair_doors'] | damage['fnc_filters']['fire_building']
        num_repair_time_increments = sum(filt_all) # possible unique number of loop increments
        for i in range(num_repair_time_increments):
            # number of functioning stairs
            num_dam_stairs = np.sum(damaged_comps * damage['fnc_filters']['stairs'], axis=1) # assumes comps are not simeltaneous
            num_racked_doors = np.sum(damaged_comps * damage['fnc_filters']['stair_doors'], axis=1) # assumes comps are not simeltaneous
            functioning_stairs = building_model['stairs_per_story'][tu] - num_dam_stairs
            functioning_stairdoors = building_model['stairs_per_story'][tu] - num_racked_doors
    
            # Fraction of functioning fire sprinkler drops
            if fs_exists: # only do this if the building has a fire suppression system
                num_dam_fs_drops = np.sum(damaged_comps * damage['fnc_filters']['fire_drops'], axis=1) # assumes comps are not simeltaneous
                ratio_fs_drop_failed = np.nanmax(num_dam_fs_drops.reshape(len(num_dam_fs_drops),1) / total_num_fs_drops.reshape(1,len(total_num_fs_drops)),axis=1) # Does not does not properly account for
                                                                                                # components in multuple PGs
    
                # Determine if the fire sprinkler system is operation at this story
                sufficient_fs_drop = ratio_fs_drop_failed <= np.array(subsystems['redundancy_threshold'])[np.array(subsystems['handle']) == 'fs_drops']
                building_fs_operational = np.isnan(np.amax(repair_complete_day[:,damage['fnc_filters']['fire_building']], axis=1)) # has all damage been repaired 
                fs_operational = sufficient_fs_drop & building_fs_operational
            
    
            # Required egress with and without operational fire suppression system
            required_stairs_w_fs = max(1,functionality_options['egress_threshold'] * building_model['stairs_per_story'][tu]) 
            required_stairs_wo_fs = max(1,functionality_options['egress_threshold_wo_fs'] * building_model['stairs_per_story'][tu])
    
            # Determine Stair Access
            sufficient_stair_access_w_fs  = functioning_stairs >= required_stairs_w_fs
            sufficient_stair_access_wo_fs  = functioning_stairs >= required_stairs_wo_fs
            if fs_exists:
                sufficient_stair_access = (sufficient_stair_access_w_fs * fs_operational) | (sufficient_stair_access_wo_fs * np.logical_not(fs_operational))
            else:
                # If there are is fire sprinkler system, use the more stringent egress requirements
                sufficient_stair_access = sufficient_stair_access_wo_fs
            
    
            # Determine Stair Door Acces
            sufficient_stairdoor_access_w_fs  = functioning_stairdoors >= required_stairs_w_fs
            sufficient_stairdoor_access_wo_fs  = functioning_stairdoors >= required_stairs_wo_fs
            if fs_exists:
                sufficient_stairdoor_access = (sufficient_stairdoor_access_w_fs * fs_operational) | (sufficient_stairdoor_access_wo_fs * np.logical_not(fs_operational))
            else:
                # If there are is fire sprinkler system, use the more stringent egress requirements
                sufficient_stairdoor_access = sufficient_stairdoor_access_wo_fs
            
    
            # Add days in this increment to the tally
            delta_day = np.nanmin(repair_complete_day[:,filt_all], axis=1)
            delta_day[np.isnan(delta_day)] = 0
            stair_access_day = stair_access_day + np.logical_not(sufficient_stair_access)* delta_day
            stairdoor_access_day = stairdoor_access_day + np.logical_not(sufficient_stairdoor_access) * delta_day
    
            if fs_exists:
                # Determine when fs operation actually matters for egress and add to the tally
                fs_matters_for_stairs = sufficient_stair_access_w_fs & np.logical_not(sufficient_stair_access)
                fs_matters_for_stairdoors = sufficient_stairdoor_access_w_fs & np.logical_not(sufficient_stairdoor_access)
                fs_matters_for_access = fs_matters_for_stairs | fs_matters_for_stairdoors
                fire_access_day = fire_access_day + fs_matters_for_access * delta_day
            
    
            # Add days to components that are affecting occupancy
            contributing_stairs = ((damaged_comps * damage['fnc_filters']['stairs'] > 0) * np.logical_not(sufficient_stair_access.reshape(len(sufficient_stair_access),1))) # Count any damaged stairs for realization that have loss of story access
    
            # Find fire sprinklers component that are contributing
            if fs_exists:
                # Count any fire component, only if fs operation matters foraccess
                contributing_fire_comps = ((damaged_comps * 
                    (damage['fnc_filters']['fire_drops'] | damage['fnc_filters']['fire_building']).reshape(1,len(damage['fnc_filters']['fire_building']))) > 0) * fs_matters_for_access.reshape(len(fs_matters_for_access),1)
                contributing_comps = contributing_stairs | contributing_fire_comps
            else:
                contributing_comps = contributing_stairs
            
            contributing_comps = np.delete(contributing_comps, -1, axis=1) # remove added door column
            comp_breakdowns['stairs'][:,:,tu] = comp_breakdowns['stairs'][:,:,tu] + contributing_comps * delta_day.reshape(len(delta_day),1)
    
            # Change the comps for the next increment
            repair_complete_day = repair_complete_day - delta_day.reshape(len(delta_day),1)
            repair_complete_day[repair_complete_day <= 0] = np.nan
            fixed_comps_filt = np.isnan(repair_complete_day)
            damaged_comps[fixed_comps_filt] = 0
        
    
        # This story is not accessible if any story below has insufficient stair egress
        if tu == 0:
            recovery_day['stairs'][:,tu] = np.fmax(stair_access_day, recovery_day['stairs'][:,0])
        else:
            # also the story below is not accessible if there is insufficient stair egress at this story
            recovery_day['stairs'][:,(tu-1):tu+1] = np.ones([1,2]) * np.fmax(stair_access_day, np.nanmax(recovery_day['stairs'][:,0:tu], axis=1)).reshape(num_reals,1)
    
        # Damage to doors only affects this story
        recovery_day['stair_doors'][:,tu] = stairdoor_access_day
    
        '''Damage to fire sprinkler drops only affects this story (full building
        fire sprinkler damage is adopted at every story, earlier in this
        script)'''
        if fs_exists:
            recovery_day['fire_egress'][:,tu] = fire_access_day
   
    return recovery_day, comp_breakdowns


def fn_tenant_safety( damage, building_model, functionality_options, 
                     tenant_units):
    '''Check each tenant unit for damage that would cause that tenant unit 
    to be shut down due to issues of locay safety
    
    Parameters
    ----------
    damage: dictionary
     contains per damage state damage, loss, and repair time data for each 
     component in the building
     
    building_model: dictionary
     general attributes of the building model
     
    functionality_options: dictionary
     recovery time optional inputs such as various damage thresholds
     
    tenant_units: DataFrame
     attributes of each tenant unit within the building
    
    Returns
    -------
    recovery_day: dictionary
     simulation of the number of days each fault tree event is affecting safety
     in each tenant unit
    
    comp_breakdowns: dictionary
     simulation of each components contributions to each of the fault tree events''' 
    
    import numpy as np
    
    ##Initial Setup
    num_reals, num_comps = np.shape(damage['tenant_units'][0]['qnt_damaged'])
    num_units = len(damage['tenant_units'])
    comp_types_interior_check = np.unique(damage['comp_ds_table']['comp_type_id'][damage['fnc_filters']['int_fall_haz_all']])
    
    recovery_day={}
    recovery_day['exterior'] = np.zeros([num_reals, num_units])
    recovery_day['interior'] = np.zeros([num_reals, num_units])    
    recovery_day['hazardous_material'] = np.zeros([num_reals, num_units])     
    
    comp_breakdowns = {}
    comp_breakdowns['exterior'] = np.empty([num_reals,num_comps,num_units])
    comp_breakdowns['interior'] = np.empty([num_reals,num_comps,num_units])
    
    # go through each tenant unit and quantify the affect that each system has on reoccpauncy
    for tu in range(num_units):
        # Grab tenant and damage info for this tenant unit
        unit={}
        for key in list(tenant_units.keys()):
            unit[key] = tenant_units[key][tu]
        repair_complete_day_w_tmp = tuple(map(tuple,(damage['tenant_units'][tu]['recovery']['repair_complete_day_w_tmp']))) # day each component (and DS) is reparied of this TU
        #FZ# Made tuple to bypass the issue of mutable numpy array
        '''#Exterior Enclosure 
           Calculated the affected perimeter area of exterior components
           (assuming all exterior components have either lf or sf units)'''
        area_affected_all_linear_comps = damage['comp_ds_table']['fraction_area_affected'] * damage['comp_ds_table']['unit_qty'] * building_model['ht_per_story_ft'][tu] * damage['tenant_units'][tu]['qnt_damaged']
        area_affected_all_area_comps = damage['comp_ds_table']['fraction_area_affected'] * damage['comp_ds_table']['unit_qty'] * damage['tenant_units'][tu]['qnt_damaged']
        
        # construct a matrix of affected areas from the various damaged component types
        comp_affected_area = np.zeros([num_reals,num_comps])
        comp_affected_area[:,damage['fnc_filters']['exterior_safety_lf']] = area_affected_all_linear_comps[:,damage['fnc_filters']['exterior_safety_lf']]
        comp_affected_area[:,damage['fnc_filters']['exterior_safety_sf']] = area_affected_all_area_comps[:,damage['fnc_filters']['exterior_safety_sf']]
        
        '''Go each possible unique repair time contributing to interior safety check
           Find when enough repairs are complete such that interior damage no
           longer affects tenant safety'''
        comps_day_repaired = repair_complete_day_w_tmp # define as initial repair day considering tmp repairs
        comps_day_repaired = np.array(comps_day_repaired)
        ext_repair_day = np.zeros(num_reals)
        all_comps_day_repaired = np.zeros([num_reals,num_comps])
        num_repair_time_increments = np.sum(damage['fnc_filters']['exterior_safety_all']) # possible unique number of loop increments
        for i in range(num_repair_time_increments):
            
            # Quantify Affected Area
            area_affected = np.sum(comp_affected_area, axis=1) # Assumes cladding components do not occupy the same perimeter area
            percent_area_affected = area_affected / unit['perim_area'] #FZ# Fraction area
    
            # Check if this is sufficent enough to cause as tenant safety issue
            affects_occupancy = percent_area_affected > functionality_options['exterior_safety_threshold']
    
            # Determine step increment based on the component with the shortest repair time
            delta_day = np.nanmin(comps_day_repaired[:,damage['fnc_filters']['exterior_safety_all']], axis=1)
            delta_day[np.isnan(delta_day)] = 0
            
            # Add increment to the tally of days until the interior damage stops affecting occupancy
            ext_repair_day = ext_repair_day + affects_occupancy * delta_day
            
            # Add days to components that are affecting occupancy
            any_area_affected_all_comps = (damage['fnc_filters']['exterior_safety_all'] * comp_affected_area) > 0 # Count any component that contributes to the loss of occupancy regardless of by how much
            all_comps_day_repaired = all_comps_day_repaired + any_area_affected_all_comps * affects_occupancy.reshape(num_reals,1) * delta_day.reshape(num_reals,1)
            
            # Reduce compent damaged for the next increment based on what was repaired in this increment
            comps_day_repaired = comps_day_repaired - delta_day.reshape(num_reals,1)
            comps_day_repaired[comps_day_repaired <= 0] = np.nan
            fixed_comps_filt = np.isnan(comps_day_repaired)
            comp_affected_area[fixed_comps_filt] = 0

        
        # Save exterior recovery day for this tenant unit
        recovery_day['exterior'][:,tu] = ext_repair_day
        comp_breakdowns['exterior'][:,:,tu] = all_comps_day_repaired
        
        ## Interior Falling Hazards
        # Convert all component into affected areas
        area_affected_all_linear_comps = damage['comp_ds_table']['fraction_area_affected'] * damage['comp_ds_table']['unit_qty'] * building_model['ht_per_story_ft'][tu] * damage['tenant_units'][tu]['qnt_damaged']
        area_affected_all_area_comps   = damage['comp_ds_table']['fraction_area_affected'] * damage['comp_ds_table']['unit_qty'] * damage['tenant_units'][tu]['qnt_damaged']
        area_affected_all_bay_comps    = damage['comp_ds_table']['fraction_area_affected'] * building_model['struct_bay_area_per_story'][tu] * damage['tenant_units'][tu]['qnt_damaged']
        area_affected_all_build_comps  = damage['comp_ds_table']['fraction_area_affected'] * building_model['total_area_sf'] * damage['tenant_units'][tu]['qnt_damaged']
        
        # Checking damage that affects components in story below
        repair_complete_day_w_tmp_w_instabilities = repair_complete_day_w_tmp
        repair_complete_day_w_tmp_w_instabilities = np.array(repair_complete_day_w_tmp_w_instabilities) #FZ# coverted to array from tuple
        if tu > 0: #FZ# changes to zero to account for python indexing starting from 0.
            area_affected_below = damage['comp_ds_table']['fraction_area_affected'] * building_model['struct_bay_area_per_story'][tu-1] * damage['tenant_units'][tu-1]['qnt_damaged']
            area_affected_all_bay_comps[:,damage['fnc_filters']['vert_instabilities']] = np.fmax(area_affected_below[:,damage['fnc_filters']['vert_instabilities']], area_affected_all_bay_comps[:,damage['fnc_filters']['vert_instabilities']])
            repair_time_below = damage['tenant_units'][tu-1]['recovery']['repair_complete_day_w_tmp']
            repair_complete_day_w_tmp_w_instabilities[:,damage['fnc_filters']['vert_instabilities']] = np.fmax(repair_time_below[:,damage['fnc_filters']['vert_instabilities']],np.array(repair_complete_day_w_tmp)[:,damage['fnc_filters']['vert_instabilities']])
        
    
        # construct a matrix of affected areas from the various damaged component types
        comp_affected_area = np.zeros([num_reals,num_comps])
        comp_affected_area[:,damage['fnc_filters']['int_fall_haz_lf']] = area_affected_all_linear_comps[:,damage['fnc_filters']['int_fall_haz_lf']]
        comp_affected_area[:,damage['fnc_filters']['int_fall_haz_sf']] = area_affected_all_area_comps[:,damage['fnc_filters']['int_fall_haz_sf']]
        comp_affected_area[:,damage['fnc_filters']['int_fall_haz_bay']] = area_affected_all_bay_comps[:,damage['fnc_filters']['int_fall_haz_bay']]
        comp_affected_area[:,damage['fnc_filters']['int_fall_haz_build']] = area_affected_all_build_comps[:,damage['fnc_filters']['int_fall_haz_build']]
        
        '''Go each possible unique repair time contributing to interior safety check
        Find when enough repairs are complete such that interior damage no
        longer affects tenant safety'''
        comps_day_repaired = repair_complete_day_w_tmp_w_instabilities # define as initial repair day considering tmp repairs
        int_repair_day = np.zeros(num_reals)
        all_comps_day_repaired = np.zeros([num_reals,num_comps])
        num_repair_time_increments = np.sum(damage['fnc_filters']['int_fall_haz_all']) # possible unique number of loop increments
        for i in range(num_repair_time_increments):
            # Quantify Affected Area
            diff_comp_areas = np.empty([num_reals, len(comp_types_interior_check)])
            for cmp in range(len(comp_types_interior_check)):
                filt = damage['comp_ds_table']['comp_type_id'] == comp_types_interior_check[cmp] # check to see if it matches the first part of the ID (ie the type of comp)
                diff_comp_areas[:,cmp] = np.sum(comp_affected_area[:,filt], axis=1)
            
            area_affected = np.sqrt(np.sum(diff_comp_areas**2, axis=1)) # total area affected is the srss of the areas in the unit
            
            # Determine if current damage affects occupancy
            percent_area_affected = np.minimum(area_affected / unit['area'], 1)
            affects_occupancy = percent_area_affected > functionality_options['interior_safety_threshold']
            
            # Determine step increment based on the component with the shortest repair time
            delta_day = np.nanmin(comps_day_repaired[:,damage['fnc_filters']['int_fall_haz_all']], axis=1)
            delta_day[np.isnan(delta_day)] = 0
            
            # Add increment to the tally of days until the interior damage
            # stops affecting occupancy
            int_repair_day = int_repair_day + affects_occupancy * delta_day
            
            # Add days to components that are affecting occupancy
            any_area_affected_all_comps = (damage['fnc_filters']['int_fall_haz_all'] * comp_affected_area) > 0 # Count any component that contributes to the loss of occupancy regardless of by how much
            all_comps_day_repaired = all_comps_day_repaired + any_area_affected_all_comps * affects_occupancy.reshape(num_reals,1) * delta_day.reshape(num_reals,1)
            
            # Reduce compent damaged for the next increment based on what was repaired in this increment
            comps_day_repaired = comps_day_repaired - delta_day.reshape(num_reals,1)
            comps_day_repaired[comps_day_repaired <= 0] = np.nan
            fixed_comps_filt = np.isnan(comps_day_repaired)
            comp_affected_area[fixed_comps_filt] = 0
        
        
        # Save interior recovery day for this tenant unit
        recovery_day['interior'][:,tu] = int_repair_day
        comp_breakdowns['interior'][:,:,tu] = all_comps_day_repaired
        
        ''' Hazardous Materials
          note: hazardous materials are accounted for in building functional
          assessment here, but are not currently quantified in the component
          breakdowns'''
        if any(damage['fnc_filters']['local_hazardous_material']):
            # Any local hazardous material shuts down the entire tenant unit
            recovery_day['hazardous_material'][:,tu] = np.nanmax(repair_complete_day_w_tmp[:,damage['fnc_filters']['local_hazardous_material']], axis=1) 
        else:
            recovery_day['hazardous_material'][:,tu] = np.zeros(num_reals)
    
    return recovery_day, comp_breakdowns


def fn_extract_recovery_metrics( tenant_unit_recovery_day, 
                                 recovery_day, comp_breakdowns, comp_id):
    '''Reformant tenant level recovery outcomes into outcomes at the building level, 
    system level, and compoennt level
    
    Parameters
    ----------
    tenant_unit_recovery_day: array [num_reals x num_tenant_units]
     simulated recovery day of each tenant unit
     
    recovery_day: dictionary
     simulation of the number of days each fault tree event is affecting
     recovery
    comp_breakdowns: dictionary
     simulation of each components contributions to each of the fault tree events 
     
    comp_id: cell array [1 x num comp damage states]
     list of each fragility id associated with the per component damage
     state structure of the damage object. With of array is the same as the
     arrays in the comp_breakdowns structure
    
    Returns
    -------
    recovery['tenant_unit']['recovery_day']: array [num_reals x num_tenant_units]
    simulated recovery day of each tenant unit
    recovery['building_level']['recovery_day']: array [num_reals x 1]
    simulated recovery day of the building (all tenant units recovered)
    recovery['building_level']['initial_percent_affected']: array [num_reals x 1]
    simulated fraction of the building with initial loss of
    reoccupancy/function
    recovery['recovery_trajectory']['recovery_day']: array [num_reals x num recovery steps]
    simulated recovery trajectory y-axis
    recovery['recovery_trajectory']['percent_recovered']: array [1 x num recovery steps]
    recovery trajectory x-axis
    recovery['breakdowns']['system_breakdowns']: array [num fault tree events x target days]
    fraction of realizations affected by various fault tree events beyond
    specific target recovery days
    recovery['breakdowns']['component_breakdowns']: array [num components x target days]
    fraction of realizations affected by various components beyond
    specific target recovery days
    recovery['breakdowns']['perform_targ_days']: array [0 x target days]
    specific target recovery days
    recovery['breakdowns']['system_names']: array [num fault tree events x 1]
    name of each fault tree event
    recovery['breakdowns']['comp_names']: array [num components x 1]
    fragility IDs of each component'''
    
    import numpy as np
    
    recovery={'tenant_unit' : {}, 'building_level' : {}, 'recovery_trajectory' : {}, 'breakdowns' : {}}
    ## Initial Setup
    num_units = np.size(tenant_unit_recovery_day,1)
    
    ''' Post process tenant-level recovery times
      Overwrite NaNs in tenant_unit_day_functional
      Only NaN where never had functional loss, therefore set to zero'''
    tenant_unit_recovery_day[np.isnan(tenant_unit_recovery_day)] = 0
    
    ## Save building-level outputs to occupancy structure
    # Tenant Unit level outputs
    recovery['tenant_unit']['recovery_day'] = tenant_unit_recovery_day
    
    # Building level outputs
    recovery['building_level']['recovery_day'] = np.nanmax(tenant_unit_recovery_day, axis=1)
    recovery['building_level']['initial_percent_affected'] = np.mean(tenant_unit_recovery_day > 0, axis=1)
    
    ## Recovery Trajectory -- calcualte from the tenant breakdowns
    recovery['recovery_trajectory']['recovery_day'] = np.sort(np.column_stack((tenant_unit_recovery_day, tenant_unit_recovery_day)), axis=1)
    recovery['recovery_trajectory']['percent_recovered'] = np.sort(np.concatenate((np.arange(num_units), np.arange(1, num_units+1)))/num_units)
    
    ## Format and Save Component-level breakdowns
    # Find the day each ds of each component stops affecting recovery for any story
    
    # Combine among all fault tree events
    component_breakdowns_per_story = 0
    fault_tree_events_LV1 = list(comp_breakdowns.keys())
    for i in range(len(fault_tree_events_LV1)):
        fault_tree_events_LV2 = list(comp_breakdowns[fault_tree_events_LV1[i]].keys())
        for j in range(len(fault_tree_events_LV2)):
            component_breakdowns_per_story = np.fmax(component_breakdowns_per_story, 
                                                 comp_breakdowns[fault_tree_events_LV1[i]][fault_tree_events_LV2[j]])

    
    # Combine among all stories
    # aka time each component's DS affects recovery anywhere in the building
    component_breakdowns = np.nanmax(component_breakdowns_per_story,axis=2)
    
    ## Format and Save System-level breakdowns
    # Find the day each system stops affecting recovery for any story
    
    # Combine among all fault tree events
    system_breakdowns = {}
    fault_tree_events_LV1 = list(recovery_day.keys())
    for i in range(len(fault_tree_events_LV1)):
        fault_tree_events_LV2 = list(recovery_day[fault_tree_events_LV1[i]].keys())
        for j in range(len(fault_tree_events_LV2)):
            # Combine among all stories or tenant units to represent the events
            # effect anywhere in the building 
            if len(np.shape(recovery_day[fault_tree_events_LV1[i]][fault_tree_events_LV2[j]]))>1:
                building_recovery_day = np.nanmax(recovery_day[fault_tree_events_LV1[i]][fault_tree_events_LV2[j]], axis=1)
            else:
                building_recovery_day = recovery_day[fault_tree_events_LV1[i]][fault_tree_events_LV2[j]].reshape(len(recovery_day[fault_tree_events_LV1[i]][fault_tree_events_LV2[j]]),1)
            # Save per "system", which typically represents the fault tree level 2
            if fault_tree_events_LV2[j] in system_breakdowns.keys():
                # If this "system" has already been defined in another fault
                # tree branch, combine togeter by taking the max (i.e., max
                # days this system affects recovery anywhere in the building)
                system_breakdowns[fault_tree_events_LV2[j]] =  np.fmax(
                    system_breakdowns[fault_tree_events_LV2[j]],building_recovery_day.reshape(len(building_recovery_day),1))
            else:
                system_breakdowns[fault_tree_events_LV2[j]] = building_recovery_day.reshape(len(building_recovery_day),1)

    
    ## Format breakdowns as performance targets
    # Define performance targets
    perform_targ_days = np.array([0, 3, 7, 14, 30, 182, 365]) # Number of days for each performance target stripe
    system_names = list(system_breakdowns.keys())
    
    # pre-allocating variables
    comps = np.unique(comp_id)
    recovery['breakdowns']['system_breakdowns'] = np.zeros([len(system_names),len(perform_targ_days)])
    recovery['breakdowns']['component_breakdowns'] = np.zeros([len(comps),len(perform_targ_days)])
    
    # Calculate fraction of realization each system affects recovery for each
    # performance target time
    for s in range(len(system_names)):
        recovery['breakdowns']['system_breakdowns'][s,:] = np.mean(system_breakdowns[system_names[s]] > perform_targ_days, axis=0)

    
    # Calculate fraction of realization each component affects recovery for each
    # performance target time
    for c in range(len(comps)):
        comp_filt = comp_id == comps[c] # find damage states associated with this component
        recovery['breakdowns']['component_breakdowns'][c,:] = np.mean(np.nanmax(component_breakdowns[:,comp_filt], axis=1).reshape(len(component_breakdowns),1) > perform_targ_days, axis=0)

    
    # Save other variables
    recovery['breakdowns']['perform_targ_days'] = perform_targ_days
    recovery['breakdowns']['system_names'] = system_names
    recovery['breakdowns']['comp_names'] = comps
    
    return recovery
    
#########################functional recovery sub functions ############################################

def fn_building_level_system_operation( damage, damage_consequences, 
                                        building_model, utilities, 
                                        functionality_options):
    
    '''Calculate the day certain systems recovery building-level opertaions
    
    Parameters
    ----------
    damage: dictionary
      contains per damage state damage, loss, and repair time data for each 
      component in the building
     
    damage_consequences: dictionary
      dictionary containing simulated building consequences, such as red
      tags and repair costs ratios
     
    building_model: dictionary
      general attributes of the building model
    
    utilities: dictionary
      dictionary containing simulated utility downtimes
     
    functionality_options: dictionary
      recovery time optional inputs such as various damage thresholds
    
    Returns
    -------
    system_operation_day['building']: dictionary
      simulation of the day operation is recovered for various systems at the
      building level
     
    system_operation_day['comp']: dictionary
      simulation number of days each component is affecting building system
      operations'''
    
    import numpy as np
    
    system_operation_day = {'building' : {}, 'comp' : {}}
    ## Initial Setep
    num_stories = building_model['num_stories']
    num_reals = len(damage_consequences['red_tag'])
    num_comps = len(damage['comp_ds_table']['comp_id'])
    
    system_operation_day['building']['hvac_main'] = np.zeros(num_reals)
    
    system_operation_day['comp']['elev_quant_damaged'] = np.zeros([num_reals,num_comps])
    system_operation_day['comp']['elev_day_repaired'] = np.zeros([num_reals,num_comps])
    system_operation_day['comp']['electrical_main'] = np.zeros([num_reals,num_comps])
    system_operation_day['comp']['water_main'] = np.zeros([num_reals,num_comps])
    system_operation_day['comp']['hvac_main'] = np.zeros([num_reals,num_comps])
    system_operation_day['comp']['elevator_mcs'] = np.zeros([num_reals,num_comps])
    system_operation_day['comp']['hvac_mcs'] = np.zeros([num_reals,num_comps])
    
    ## Loop through each story/TU and quantify the building-level performance of each system (e.g. equipment that severs the entire building)
    for tu in range(num_stories):
        damaged_comps = np.array(damage['tenant_units'][tu]['qnt_damaged'])
        initial_damaged = damaged_comps > 0
        total_num_comps = np.array(damage['tenant_units'][tu]['num_comps'])
        repair_complete_day = damage['tenant_units'][tu]['recovery']['repair_complete_day']
        
        # Elevators
        # Assumed all components affect entire height of shaft
        system_operation_day['comp']['elev_quant_damaged'] = np.fmax(
            system_operation_day['comp']['elev_quant_damaged'], 
            damage['tenant_units'][tu]['qnt_damaged'] * 
            damage['fnc_filters']['elevators'])
        
        system_operation_day['comp']['elev_day_repaired'] = np.fmax(
            system_operation_day['comp']['elev_day_repaired'], 
            repair_complete_day * damage['fnc_filters']['elevators'])
        
        # Electrical
        system_operation_day['comp']['electrical_main'] = np.fmax(
            system_operation_day['comp']['electrical_main'], 
            repair_complete_day * damage['fnc_filters']['electrical_main'])
        
        # Motor Control system - Elevators
        system_operation_day['comp']['elevator_mcs'] = np.fmax(
            system_operation_day['comp']['elevator_mcs'], 
            repair_complete_day * damage['fnc_filters']['elevator_mcs'])
        
        # Water
        system_operation_day['comp']['water_main'] = np.fmax(
            system_operation_day['comp']['water_main'], 
            repair_complete_day * damage['fnc_filters']['water_main'])
        
        # HVAC Equipment and Distribution - Building Level
        # non redundant systems
        main_nonredundant_sys_repair_day = np.nanmax(
            repair_complete_day * damage['fnc_filters']['hvac_main_nonredundant'], axis=1) # any major damage to the nonredundant main building equipment fails the system for the entire building
        
        # Redundant systems
        # only fail system when a sufficient number of component have failed
        redundant_subsystems = np.unique(damage['comp_ds_table']['subsystem_id'][damage['fnc_filters']['hvac_main_redundant']])
        main_redundant_sys_repair_day = np.zeros(num_reals)
        
        for s in range(len(redundant_subsystems)): # go through each redundant subsystem
            this_redundant_sys = np.logical_and(damage['fnc_filters']['hvac_main_redundant'], damage['comp_ds_table']['subsystem_id'] == redundant_subsystems[s])
            n1_redundancy = max(damage['comp_ds_table']['n1_redundancy'][this_redundant_sys]) # should all be the same within a subsystem
    
            # go through each component in this subsystem and find number of damaged units
            comps = np.unique(damage['comp_ds_table']['comp_idx'][this_redundant_sys])
            num_tot_comps = np.zeros(len(comps))
            num_damaged_comps = np.zeros([num_reals,len(comps)])
            for c in range(len(comps)):
                this_comp = np.logical_and(this_redundant_sys, damage['comp_ds_table']['comp_idx'] == comps[c]);
                num_tot_comps[c] = max(total_num_comps * this_comp) # number of units across all ds should be the same
                num_damaged_comps[:,c] = np.nanmax(damaged_comps * this_comp, axis=1)
            
    
            # sum together multiple components in this subsystem
            subsystem_num_comps = sum(num_tot_comps)
            subsystem_num_damaged_comps = np.sum(num_damaged_comps, axis=1)
            ratio_damaged = subsystem_num_damaged_comps / subsystem_num_comps
            ratio_operating = 1 - ratio_damaged
    
            # Check failed component against the ratio of components required for system operation
            # system fails when there is an insufficient number of operating components
            if subsystem_num_comps == 0: # Not components at this level
                subsystem_failure = np.zeros(num_reals)
            elif subsystem_num_comps == 1: # Not actually redundant
                subsystem_failure = 1*(subsystem_num_damaged_comps == 0)
            elif n1_redundancy ==1:
                # These components are designed to have N+1 redundncy rates,
                # meaning they are designed to lose one component and still operate at
                # normal level
                subsystem_failure = 1*(subsystem_num_damaged_comps > 1)
            else:
                # Use a predefined ratio
                subsystem_failure = ratio_operating < functionality_options['required_ratio_operating_hvac_main']
            
    
            # Calculate recovery day and combine with other subsystems for this tenant unit
            # assumes all quantities in each subsystem are repaired at
            # once, which is true for our current repair schedule (ie
            # system level at each story)
            main_redundant_sys_repair_day = np.fmax(main_redundant_sys_repair_day, 
                np.nanmax(subsystem_failure.reshape(num_reals,1) * this_redundant_sys.reshape(1, num_comps) * repair_complete_day, axis=1))
        
    
        # Ducts
        duct_mains_repair_day = np.nanmax(repair_complete_day * damage['fnc_filters']['hvac_duct_mains'], axis=1) # any major damage to the main ducts fails the system for the entire building
    
        # Cooling piping
        cooling_piping_repair_day = np.nanmax(repair_complete_day * damage['fnc_filters']['hvac_cooling_piping'], axis=1) # any major damage to the piping fails the system for the entire building
    
        # Heating piping
        heating_piping_repair_day = np.nanmax(repair_complete_day * damage['fnc_filters']['hvac_heating_piping'], axis=1) # any major damage to the piping fails the system for the entire building
    
        # HVAC control Equipment
        # hvac control panel is currently embedded into the non-redundant equipment check
        
        # HVAC building level exhaust
        # this is embedded in the main equipment check
        
        # Motor Control system - HVAC
        # if seperate from the hvac control panel (only pulls in if defined as
        # part or the HVAC system -- using the component system attribute)
        hvac_mcs_repair_day = np.nanmax(repair_complete_day * damage['fnc_filters']['hvac_mcs'], axis=1) # any major damage fails the system for the whole building so take the max
        
        # Putting it all together
        # Currently not seperating heating equip from cooling equip (as they are currently the same, ie there are no boilers in P-58)
        main_equip_repair_day = np.fmax(main_nonredundant_sys_repair_day, main_redundant_sys_repair_day) # This includes hvac controls and exhaust
        heating_utility_repair_day = utilities['gas']
        heating_system_repair_day = np.fmax(main_equip_repair_day, np.fmax(duct_mains_repair_day, np.fmax(heating_utility_repair_day, heating_piping_repair_day)))
        cooling_utility_repair_day = utilities['electrical']
        cooling_system_repair_day = np.fmax(main_equip_repair_day, np.fmax(duct_mains_repair_day, np.fmax(cooling_utility_repair_day, cooling_piping_repair_day)))
        system_operation_day['building']['hvac_main'] = np.fmax( system_operation_day['building']['hvac_main'], 
                                                  np.fmax(hvac_mcs_repair_day,
                                                  np.fmax( heating_system_repair_day, cooling_system_repair_day))) # combine with damage from previous floors
    
        # HVAC Equipment and Distribution - Building Level
        nonredundant_comps_day = damage['fnc_filters']['hvac_main_nonredundant'] * initial_damaged * main_nonredundant_sys_repair_day.reshape(num_reals,1) # note these components anytime they cause specific system failure
        redundant_comps_day = damage['fnc_filters']['hvac_main_redundant'] * initial_damaged * main_redundant_sys_repair_day.reshape(num_reals,1)
        main_duct_comps_day = damage['fnc_filters']['hvac_duct_mains'] * initial_damaged * duct_mains_repair_day.reshape(num_reals,1)
        cooling_piping_comps_day = damage['fnc_filters']['hvac_cooling_piping'] * initial_damaged * cooling_piping_repair_day.reshape(num_reals,1)
        heating_piping_comps_day = damage['fnc_filters']['hvac_heating_piping'] * initial_damaged * heating_piping_repair_day.reshape(num_reals,1)
        hvac_mcs_comps_day = damage['fnc_filters']['hvac_mcs'] * initial_damaged * hvac_mcs_repair_day.reshape(num_reals,1)
        hvac_comp_recovery_day = np.fmax(np.fmax(np.fmax(np.fmax(np.fmax(nonredundant_comps_day, redundant_comps_day),
                                                      main_duct_comps_day), cooling_piping_comps_day),
                                                      heating_piping_comps_day),
                                                      hvac_mcs_comps_day)
        system_operation_day['comp']['hvac_main'] = np.fmax(system_operation_day['comp']['hvac_main'], hvac_comp_recovery_day)                        
    
    
    ## Calculate building level consequences for systems where any major main damage leads to system failure
    system_operation_day['building']['electrical_main'] = np.nanmax(system_operation_day['comp']['electrical_main'], axis=1)  # any major damage to the main equipment fails the system for the entire building
    system_operation_day['building']['water_main'] = np.nanmax(system_operation_day['comp']['water_main'], axis=1)  # any major damage to the main pipes fails the system for the entire building
    system_operation_day['building']['elevator_mcs'] = np.nanmax(system_operation_day['comp']['elevator_mcs'], axis=1) # any major damage fails the system for the whole building so take the max
    system_operation_day['building']['hvac_mcs'] = np.nanmax(system_operation_day['comp']['hvac_mcs'], axis=1) # any major damage fails the system for the whole building so take the max
    

    return system_operation_day


def fn_tenant_function( damage, building_model, system_operation_day, 
                        utilities, subsystems, tenant_units, 
                        functionality_options):
    
    '''Check each tenant unit for damage that would cause that tenant unit 
    to not be functional
    
    Parameters
    ----------
    damage: dictionary
      contains per damage state damage, loss, and repair time data for each 
      component in the building
    
    building_model: dictionary
      general attributes of the building model
      system_operation_day.building: struct
      simulation of the day operation is recovered for various systems at the
      building level
     
    system_operation_day.comp: dictionary
      simulation number of days each component is affecting building system
      operations
    
    utilities: dictionary
      data structure containing simulated utility downtimes
    
    subsystems: DataFrame
      data table containing information about each subsystem's attributes
    
    tenant_units: DataFrame
      attributes of each tenant unit within the building
    
    functionality_options: dictionary
      recovery time optional inputs such as various damage thresholds
    
    Returns
    -------
    recovery_day: dictionary
      simulation of the number of days each fault tree event is affecting
      function in each tenant unit
    
    comp_breakdowns: dictionary
      simulation of each components contributions to each of the 
      fault tree events''' 

    import numpy as np
    import sys
    def fn_quantify_hvac_subsystem_recovery_day(subsystem_filter, 
                                                total_num_comps, 
                                                repair_complete_day, 
                                                initial_damaged, 
                                                damaged_comps, 
                                                subsystem_threshold, 
                                                pg_id, is_sim_ds):
    
        # Determine the ratio of damaged components that affect system operation
        sub_sys_pg_id = np.unique(pg_id[subsystem_filter])
        num_comp = 0
        for c in range(len(sub_sys_pg_id)):
            sub_sys_pg_filt = np.logical_and(subsystem_filter, pg_id == sub_sys_pg_id[c])
            num_comp = num_comp + max(total_num_comps[sub_sys_pg_filt])

        tot_num_comp_dam = np.sum(damaged_comps * subsystem_filter, axis=1) # Assumes damage states are never simultaneous
        ratio_damaged = tot_num_comp_dam / num_comp  
        
        # Check to make sure its not simeltanous
        # Quantification of number of damaged comp
        if any(is_sim_ds[subsystem_filter]):
            sys.exit('PBEE_Recovery:Function','HVAC Function check does not handle performance groups with simultaneous damage states')

        
        # If ratio of component in this subsystem is greater than the
        # threshold, the system fails for this tenant unit
        subsystem_failure = ratio_damaged > subsystem_threshold
        
        # Calculate tenant unit recovery day for this subsystem
        subsystem_recovery_day = np.nanmax(subsystem_filter.reshape(1, num_comps) * subsystem_failure.reshape(num_reals,1) * repair_complete_day, axis=1)
        
        # Distrbute recovery day to the components affecting function for this subsystem
        subsystem_comp_recovery_day = subsystem_filter * initial_damaged * subsystem_recovery_day.reshape(num_reals,1)
                   
        return subsystem_recovery_day, subsystem_comp_recovery_day

    
    ## Initial Setup
    num_units = len(damage['tenant_units'])
    num_reals, num_comps = np.shape(np.array(damage['tenant_units'][0]['qnt_damaged']))
    num_stories = building_model['num_stories']
    
    recovery_day = {
        'elevators' : np.zeros([num_reals,num_units]),
        'exterior' : np.zeros([num_reals,num_units]),
        'interior' : np.zeros([num_reals,num_units]),
        'water' : np.zeros([num_reals,num_units]),
        'electrical' : np.zeros([num_reals,num_units]),
        'hvac' : np.zeros([num_reals,num_units])
        }
    
    comp_breakdowns = {
        'elevators' : np.zeros([num_reals,num_comps,num_units]),
        'water' : np.zeros([num_reals,num_comps,num_units]),
        'electrical' : np.zeros([num_reals,num_comps,num_units]),
        'hvac' : np.zeros([num_reals,num_comps,num_units]),
        'exterior' : np.zeros([num_reals,num_comps,num_units]),
        'interior' : np.zeros([num_reals,num_comps,num_units])
        }
    
    ## Go through each tenant unit, define system level performacne and determine tenant unit recovery time
    for tu in range(num_units):
        damaged_comps = np.array(damage['tenant_units'][tu]['qnt_damaged'])
        initial_damaged = damaged_comps > 0
        total_num_comps = np.array(damage['tenant_units'][tu]['num_comps'])
        unit={}
        for key in list(tenant_units.keys()):
            unit[key] = tenant_units[key][tu]        
        
        repair_complete_day = tuple(map(tuple,damage['tenant_units'][tu]['recovery']['repair_complete_day'])) #FZ# Made tuple to bypass the issue of mutable numpy array
        repair_complete_day_w_tmp = tuple(map(tuple, damage['tenant_units'][tu]['recovery']['repair_complete_day_w_tmp'])) #FZ# Made tuple to bypass the issue of mutable numpy array
        
        ## Elevators
        if unit['is_elevator_required'] == 1:
            comps_day_repaired= tuple(map(tuple,system_operation_day['comp']['elev_day_repaired'])) #FZ# Made tuple to bypass the issue of mutable numpy array
            comps_day_repaired = np.array(comps_day_repaired)
            comps_day_repaired[comps_day_repaired == 0] = np.nan
            comps_quant_damaged = tuple(map(tuple,system_operation_day['comp']['elev_quant_damaged'])) #FZ# Made tuple to bypass the issue of mutable numpy array
            comps_quant_damaged = np.array(comps_quant_damaged)
            elev_function_recovery_day = np.zeros(num_reals)
            elev_comps_day_fnc = np.zeros([num_reals,num_comps])
            num_repair_time_increments = sum(damage['fnc_filters']['elevators']) # possible unique number of loop increments
            # Loop through each unique repair time increment and determine when
            # stops affecting function
            for i in range(num_repair_time_increments):
                '''Take the max of component damage to determine the number of
                shafts/cabs that are damaged/non_operational
                This assumes that different elevator components are correlated'''
                num_damaged_elevs = np.nanmax(comps_quant_damaged, axis=1) # this assumes elevators are in one performance group if simeltaneous
                num_damaged_elevs = np.minimum(num_damaged_elevs, building_model['num_elevators']) # you can never have more elevators damaged than exist
                
                '''If elevators are in mutliple performance groups and those
                elevators have simultaneous damage states, it is not possible
                to count the number of damaged elevators without additional
                information'''
                num_elev_pgs = len(np.unique(damage['comp_ds_table']['comp_idx'][damage['fnc_filters']['elevators']]))
                is_sim_ds = any(damage['comp_ds_table']['is_sim_ds'][damage['fnc_filters']['elevators']])
                if (num_elev_pgs > 1) and is_sim_ds:
                    sys.exit('Error! PBEE_Recovery:Function','Elevator Function check does not handle multiple performance groups with simultaneous damage states')
                
    
                # quantifty the number of occupancy needing to use the elevators
                # all occupants above the first floor will try to use the elevators
                building_occ_per_elev = sum(building_model['occupants_per_story'][1:len(building_model['occupants_per_story'])]) / (building_model['num_elevators'] - num_damaged_elevs) 
                
                # elevator function check
                # do tenants have sufficient elevator access need based on
                # elevators that are still operational
                # affects_function = building_occ_per_elev > max(unit['occ_per_elev'])
                affects_function = building_occ_per_elev > unit['occ_per_elev'] #FZ# Check. Why max is done . Only a single value per unit
                # Add days in this increment to the tally
                delta_day = np.nanmin(comps_day_repaired[:,damage['fnc_filters']['elevators']], axis=1)
                delta_day[np.isnan(delta_day)] = 0
                elev_function_recovery_day = elev_function_recovery_day + affects_function * delta_day
                
                # Add days to components that are affecting occupancy
                any_elev_damage = comps_quant_damaged > 0 # Count any component that contributes to the loss of function regardless of by how much 
                elev_comps_day_fnc = elev_comps_day_fnc + any_elev_damage * affects_function.reshape(num_reals,1) * delta_day.reshape(num_reals,1)
    
                # Change the comps for the next increment
                comps_day_repaired = comps_day_repaired - delta_day.reshape(num_reals,1)
                comps_day_repaired[comps_day_repaired <= 0] = np.nan
                fixed_comps_filt = np.isnan(comps_day_repaired)
                comps_quant_damaged[fixed_comps_filt] = 0
            
            power_supply_recovery_day = np.fmax(np.fmax(system_operation_day['building']['elevator_mcs'], system_operation_day['building']['electrical_main']), utilities['electrical'])
            
            # Here was the problem in use of fmax. Changed to max
            recovery_day['elevators'][:,tu] = np.fmax(elev_function_recovery_day, power_supply_recovery_day) # electrical system and utility
            power_supply_recovery_day_comp = np.fmax(system_operation_day['comp']['elevator_mcs'], system_operation_day['comp']['electrical_main'])
            comp_breakdowns['elevators'][:,:,tu] = np.fmax(elev_comps_day_fnc, power_supply_recovery_day_comp)
        
        
        ## Exterior Enclosure 
        # Perimeter Cladding (assuming all exterior components have either lf or sf units)
        area_affected_lf_all_comps = damage['comp_ds_table']['fraction_area_affected'] * damage['comp_ds_table']['unit_qty'] * building_model['ht_per_story_ft'][tu] * damage['tenant_units'][tu]['qnt_damaged']
        area_affected_sf_all_comps = damage['comp_ds_table']['fraction_area_affected'] * damage['comp_ds_table']['unit_qty'] * damage['tenant_units'][tu]['qnt_damaged']
       
        comp_affected_area = np.zeros([num_reals,num_comps])
        comp_affected_area[:,damage['fnc_filters']['exterior_seal_lf']] = area_affected_lf_all_comps[:,damage['fnc_filters']['exterior_seal_lf']]
        comp_affected_area[:,damage['fnc_filters']['exterior_seal_sf']] = area_affected_sf_all_comps[:,damage['fnc_filters']['exterior_seal_sf']]
        
        comps_day_repaired = np.array(repair_complete_day)
        ext_function_recovery_day = np.zeros(num_reals)
        all_comps_day_ext = np.zeros([num_reals,num_comps])
        num_repair_time_increments = sum(damage['fnc_filters']['exterior_seal_all']) # possible unique number of loop increments
        # Loop through each unique repair time increment and determine when stops affecting function
        for i in range(num_repair_time_increments):
            # Determine the area of wall which has severe exterior encolusure damage 
            area_affected = np.sum(comp_affected_area, axis=1) # Assumes cladding components do not occupy the same perimeter area
            percent_area_affected = np.minimum(area_affected / unit['perim_area'], 1) # normalize it. #FZ# Should be fraction area?
            
            # Determine if current damage affects function for this tenant unit
            # if the area of exterior wall damage is greater than what is
            # acceptable by the tenant 
            affects_function = percent_area_affected > unit['exterior'] 
            
            # Add days in this increment to the tally
            delta_day = np.nanmin(comps_day_repaired[:,damage['fnc_filters']['exterior_seal_all']], axis=1)
            delta_day[np.isnan(delta_day)] = 0
            ext_function_recovery_day = ext_function_recovery_day + affects_function * delta_day
            # Add days to components that are affecting occupancy
            any_area_affected_all_comps = comp_affected_area > 0 # Count any component that contributes to the loss of occupance regardless of by how much
            all_comps_day_ext = all_comps_day_ext + any_area_affected_all_comps * affects_function.reshape(num_reals,1) * delta_day.reshape(num_reals,1)
            
            # Change the comps for the next increment
            # reducing damage for what has been repaired in this time increment
            comps_day_repaired = comps_day_repaired - delta_day.reshape(num_reals,1)
            comps_day_repaired[comps_day_repaired <= 0] = np.nan
            fixed_comps_filt = np.isnan(comps_day_repaired)
            comp_affected_area[fixed_comps_filt] = 0
        
        
        if unit['story'] == num_stories: # If this is the top story, check the roof for function
            # Roof structure (currently assuming all roofing components have equal unit
            # areas)
            damage_threshold = float(subsystems['redundancy_threshold'][subsystems['id'] == 21])
            num_comp_damaged = damage['fnc_filters']['roof_structure'] * damage['tenant_units'][tu]['qnt_damaged']
            num_roof_comps = damage['fnc_filters']['roof_structure'] * damage['tenant_units'][tu]['num_comps']
    
            comps_day_repaired = np.array(repair_complete_day)
            roof_structure_recovery_day = np.zeros(num_reals)
            all_comps_day_roof_struct = np.zeros([num_reals,num_comps])
            num_repair_time_increments = sum(damage['fnc_filters']['roof_structure']) # possible unique number of loop increments
            # Loop through each unique repair time increment and determine when stops affecting function
            for i in range(num_repair_time_increments):
                # Determine the area of roof affected 
                percent_area_affected = np.sum(num_comp_damaged, axis=1) / sum(num_roof_comps) # Assumes roof components do not occupy the same area of roof
                
                # Determine if current damage affects function for this tenant unit
                # if the area of exterior wall damage is greater than what is
                # acceptable by the tenant 
                affects_function = percent_area_affected >= damage_threshold 
    
                # Add days in this increment to the tally
                delta_day = np.nanmin(comps_day_repaired[:,damage['fnc_filters']['roof_structure']], axis=1)
                delta_day[np.isnan(delta_day)] = 0
                roof_structure_recovery_day = roof_structure_recovery_day + affects_function * delta_day
    
                # Add days to components that are affecting function
                any_area_affected_all_comps = num_comp_damaged > 0 # Count any component that contributes to the loss of function regardless of by how much
                all_comps_day_roof_struct = all_comps_day_roof_struct + any_area_affected_all_comps * affects_function.reshape(num_reals,1) * delta_day.reshape(num_reals,1)
    
                # Change the comps for the next increment
                # reducing damage for what has been repaired in this time increment
                comps_day_repaired = comps_day_repaired - delta_day.reshape(num_reals,1)
                comps_day_repaired[comps_day_repaired <= 0] = np.nan
                fixed_comps_filt = np.isnan(comps_day_repaired)
                num_comp_damaged[fixed_comps_filt] = 0

    
            # Roof weatherproofing (currently assuming all roofing components have 
            # equal unit areas)
            damage_threshold = float(subsystems['redundancy_threshold'][subsystems['id'] == 22])
            num_comp_damaged = damage['fnc_filters']['roof_weatherproofing'] * damage['tenant_units'][tu]['qnt_damaged']
            num_roof_comps = damage['fnc_filters']['roof_weatherproofing'] * damage['tenant_units'][tu]['num_comps']
    
            comps_day_repaired = np.array(repair_complete_day)
            roof_weather_recovery_day = np.zeros(num_reals)
            all_comps_day_roof_weather = np.zeros([num_reals,num_comps])
            num_repair_time_increments = sum(damage['fnc_filters']['roof_weatherproofing']) # possible unique number of loop increments
            # Loop through each unique repair time increment and determine when stops affecting function
            for i in range(num_repair_time_increments):
                # Determine the area of roof affected 
                percent_area_affected = np.sum(num_comp_damaged, axis=1) / sum(num_roof_comps) # Assumes roof components do not occupy the same area of roof
    
                # Determine if current damage affects function for this tenant unit
                # if the area of exterior wall damage is greater than what is
                # acceptable by the tenant 
                affects_function = percent_area_affected >= damage_threshold 
    
                # Add days in this increment to the tally
                delta_day = np.nanmin(comps_day_repaired[:,damage['fnc_filters']['roof_weatherproofing']], axis=1)
                delta_day[np.isnan(delta_day)] = 0
                roof_weather_recovery_day = roof_weather_recovery_day + affects_function * delta_day
    
                # Add days to components that are affecting function
                any_area_affected_all_comps = num_comp_damaged > 0 # Count any component that contributes to the loss of function regardless of by how much
                all_comps_day_roof_weather = all_comps_day_roof_weather + any_area_affected_all_comps * affects_function.reshape(num_reals,1) * delta_day.reshape(num_reals,1)
    
                # Change the comps for the next increment
                # reducing damage for what has been repaired in this time increment
                comps_day_repaired = comps_day_repaired - delta_day
                comps_day_repaired[comps_day_repaired <= 0] = np.nan
                fixed_comps_filt = np.isnan(comps_day_repaired)
                num_comp_damaged[fixed_comps_filt] = 0

    
            # Combine branches
            recovery_day['exterior'][:,tu] = np.fmax(ext_function_recovery_day,
                np.fmax(roof_structure_recovery_day,roof_weather_recovery_day));
            comp_breakdowns['exterior'][:,:,tu] = np.fmax(all_comps_day_ext,
                np.fmax(all_comps_day_roof_struct,all_comps_day_roof_weather));
        else: # this is not the top story so just use the cladding for tenant function
            recovery_day['exterior'][:,tu] = ext_function_recovery_day
            comp_breakdowns['exterior'][:,:,tu] = all_comps_day_ext
        
        ## Interior Area
        area_affected_lf_all_comps    = damage['comp_ds_table']['fraction_area_affected'] * damage['comp_ds_table']['unit_qty'] * building_model['ht_per_story_ft'][tu] * damage['tenant_units'][tu]['qnt_damaged']
        area_affected_sf_all_comps    = damage['comp_ds_table']['fraction_area_affected'] * damage['comp_ds_table']['unit_qty'] * damage['tenant_units'][tu]['qnt_damaged']
        area_affected_bay_all_comps   = damage['comp_ds_table']['fraction_area_affected'] * building_model['struct_bay_area_per_story'][tu] * damage['tenant_units'][tu]['qnt_damaged']
        area_affected_build_all_comps = damage['comp_ds_table']['fraction_area_affected'] * building_model['total_area_sf'] * damage['tenant_units'][tu]['qnt_damaged']
        
        repair_complete_day_w_tmp_w_instabilities = np.array(repair_complete_day_w_tmp)
        if tu > 0: #FZ# changed to 0 to account for python index starting from 0.
            area_affected_below = damage['comp_ds_table']['fraction_area_affected'] * building_model['struct_bay_area_per_story'][tu-1] * damage['tenant_units'][tu-1]['qnt_damaged']
            area_affected_bay_all_comps[:,damage['fnc_filters']['vert_instabilities']] = np.fmax(
                area_affected_below[:,damage['fnc_filters']['vert_instabilities']],area_affected_bay_all_comps[:,damage['fnc_filters']['vert_instabilities']])
            repair_time_below = damage['tenant_units'][tu-1]['recovery']['repair_complete_day_w_tmp']
            repair_complete_day_w_tmp_w_instabilities[:,damage['fnc_filters']['vert_instabilities']] = np.fmax(
                repair_time_below[:,damage['fnc_filters']['vert_instabilities']], np.array(repair_complete_day_w_tmp)[:,damage['fnc_filters']['vert_instabilities']])

    
        comp_affected_area = np.zeros([num_reals,num_comps])
        comp_affected_area[:,damage['fnc_filters']['interior_function_lf']] = area_affected_lf_all_comps[:,damage['fnc_filters']['interior_function_lf']]
        comp_affected_area[:,damage['fnc_filters']['interior_function_sf']] = area_affected_sf_all_comps[:,damage['fnc_filters']['interior_function_sf']]
        comp_affected_area[:,damage['fnc_filters']['interior_function_bay']] = area_affected_bay_all_comps[:,damage['fnc_filters']['interior_function_bay']]
        comp_affected_area[:,damage['fnc_filters']['interior_function_build']] = area_affected_build_all_comps[:,damage['fnc_filters']['interior_function_build']]
    
        frag_types_in_check = np.unique(damage['comp_ds_table']['comp_type_id'][damage['fnc_filters']['interior_function_all']])
        comps_day_repaired = repair_complete_day_w_tmp_w_instabilities
    
        int_function_recovery_day = np.zeros(num_reals)
        int_comps_day_repaired = np.zeros([num_reals,num_comps])
        num_repair_time_increments = sum(damage['fnc_filters']['interior_function_all']) # possible unique number of loop increments
        # Loop through each unique repair time increment and determine when stops affecting function
        for i in range(num_repair_time_increments):
            # Quantify the affected area (based on srss of differenct component
            # types)
            diff_comp_areas = np.empty([num_reals, len(frag_types_in_check)])
            for cmp in range(len(frag_types_in_check)):
                filt = damage['comp_ds_table']['comp_type_id'] == frag_types_in_check[cmp] # check to see if it matches the first part of the ID (ie the type of comp)
                diff_comp_areas[:,cmp] = np.sum(comp_affected_area[:,filt], axis=1)
            
            area_affected = np.sqrt(np.sum(diff_comp_areas**2, axis=1)) # total area affected is the srss of the areas in the unit
            percent_area_affected = np.minimum(area_affected / unit['area'], 1) # no greater than the total unit area
        
            # Determine if current damage affects function for this tenant unit
            # affects function if the area of interior damage is greater than what is
            # acceptable by the tenant 
            affects_function = percent_area_affected > unit['interior'] 
            
            # Add days in this increment to the tally
            delta_day = np.nanmin(comps_day_repaired[:,damage['fnc_filters']['interior_function_all']], axis=1)
            delta_day[np.isnan(delta_day)] = 0
            int_function_recovery_day = int_function_recovery_day + affects_function * delta_day
            
            # Add days to components that are affecting occupancy
            any_area_affected_all_comps = comp_affected_area > 0 # Count any component that contributes to the loss of occupance regardless of by how much
            int_comps_day_repaired = int_comps_day_repaired + any_area_affected_all_comps * affects_function.reshape(num_reals,1) * delta_day.reshape(num_reals,1)
            
            # Change the comps for the next increment
            # reducing damage for what has been repaired in this time increment
            comps_day_repaired = comps_day_repaired - delta_day.reshape(num_reals,1)
            comps_day_repaired[comps_day_repaired <= 0] = np.nan
            fixed_comps_filt = np.isnan(comps_day_repaired)
            comp_affected_area[fixed_comps_filt] = 0
            
        recovery_day['interior'][:,tu] = int_function_recovery_day
        comp_breakdowns['interior'][:,:,tu] = int_comps_day_repaired
        
        # Water and Plumbing System
        if unit['is_water_required'] == 1:
            # determine effect on funciton at this tenant unit
            # any major damage to the branch pipes (small diameter) failes for this tenant unit
            tenant_sys_recovery_day = np.nanmax(np.array(repair_complete_day) * damage['fnc_filters']['water_unit'], axis=1) 
            recovery_day['water'][:,tu] = np.fmax(system_operation_day['building']['water_main'],tenant_sys_recovery_day)
            
            # Consider effect of external water network
            utility_repair_day = utilities['water'];
            recovery_day['water'] = np.fmax(recovery_day['water'], np.array(utility_repair_day).reshape(num_reals,1))
            
            # distribute effect to the components
            comp_breakdowns['water'][:,:,tu] = np.fmax(system_operation_day['comp']['water_main'], np.array(repair_complete_day) * damage['fnc_filters']['water_unit'])
        


        
        ## Electrical Power System
        # Does not consider effect of backup systems
        if unit['is_electrical_required'] == 1:
            # determine effect on funciton at this tenant unit
            # any major damage to the unit level electrical equipment failes for this tenant unit
            tenant_sys_recovery_day = np.nanmax(np.array(repair_complete_day) * damage['fnc_filters']['electrical_unit'], axis=1)
            recovery_day['electrical'][:,tu] =np.fmax(system_operation_day['building']['electrical_main'], tenant_sys_recovery_day)
            
            # Consider effect of external water network
            utility_repair_day = utilities['electrical']
            recovery_day['electrical'] = np.fmax(recovery_day['electrical'], np.array(utility_repair_day).reshape(num_reals,1))
            
            # distribute effect to the components
            comp_breakdowns['electrical'][:,:,tu] = np.fmax(system_operation_day['comp']['electrical_main'], np.array(repair_complete_day) * damage['fnc_filters']['electrical_unit'])

        
        ## HVAC System
        # HVAC Equipment - Tenant Level
        if unit['is_hvac_required'] == 1:
            # Nonredundant equipment
            # any major damage to the equipment servicing this tenant unit fails the system for this tenant unit
            nonredundant_sys_repair_day = np.nanmax(np.array(repair_complete_day) * damage['fnc_filters']['hvac_unit_nonredundant'], axis=1)
    
            # Redundant systems
            # only fail system when a sufficient number of component have failed
            redundant_subsystems = np.unique(damage['comp_ds_table']['subsystem_id'][damage['fnc_filters']['hvac_unit_redundant']])
            redundant_sys_repair_day = np.zeros(num_reals)
            for s in range(len(redundant_subsystems)): # go through each redundant subsystem
                this_redundant_sys = np.logical_and(damage['fnc_filters']['hvac_unit_redundant'], damage['comp_ds_table']['subsystem_id'] == redundant_subsystems[s])
                n1_redundancy = max(damage['comp_ds_table']['n1_redundancy'][this_redundant_sys]) # should all be the same within a subsystem
                
                # go through each component in this subsystem and find number of damaged units
                comps = np.unique(damage['comp_ds_table']['comp_idx'][this_redundant_sys])
                num_tot_comps = np.zeros(len(comps))
                num_damaged_comps = np.zeros([num_reals,len(comps)])
                for c in range(len(comps)):
                    this_comp = np.logical_and(this_redundant_sys, damage['comp_ds_table']['comp_idx'] == comps[c])
                    num_tot_comps[c] = max(total_num_comps * this_comp) # number of units across all ds should be the same
                    num_damaged_comps[:,c] = np.nanmax(damaged_comps * this_comp, axis=1)
                
                    
                # sum together multiple components in this subsystem
                subsystem_num_comps = sum(num_tot_comps)
                subsystem_num_damaged_comps = np.sum(num_damaged_comps, axis=1)
                ratio_damaged = subsystem_num_damaged_comps / subsystem_num_comps
                ratio_operating = 1 - ratio_damaged
                
                # Check failed component against the ratio of components required for system operation
                # system fails when there is an insufficient number of operating components
                if subsystem_num_comps == 0: # Not components at this level
                    tenant_subsystem_failure = np.zeros(num_reals)
                elif subsystem_num_comps == 1: # Not actually redundant
                    tenant_subsystem_failure = subsystem_num_damaged_comps == 0
                elif n1_redundancy ==1:
                    # These components are designed to have N+1 redundncy rates,
                    # meaning they are designed to lose one component and still operate at
                    # normal level
                    tenant_subsystem_failure = subsystem_num_damaged_comps > 1
                else:
                    # Use a predefined ratio
                    tenant_subsystem_failure = ratio_operating < functionality_options['required_ratio_operating_hvac_unit']

                
                # Calculate recovery day and combine with other subsystems for this tenant unit
                # assumes all quantities in each subsystem are repaired at
                # once, which is true for our current repair schedule (ie
                # system level at each story)
                redundant_sys_repair_day = np.fmax(redundant_sys_repair_day,
                    np.nanmax(tenant_subsystem_failure.reshape(num_reals,1) * this_redundant_sys.reshape(1, num_comps) * np.array(repair_complete_day), axis=1))
    
            # Combine tenant level equipment with main building level equipment
            tenant_hvac_fnc_recovery_day = np.fmax(redundant_sys_repair_day, nonredundant_sys_repair_day)
            recovery_day['hvac'][:,tu] = np.fmax(tenant_hvac_fnc_recovery_day,system_operation_day['building']['hvac_main'])
            
            # distribute the the components affecting function
            # (note these components anytime they cause specific system failure)
            nonredundant_comps_day = damage['fnc_filters']['hvac_unit_nonredundant'] * initial_damaged * nonredundant_sys_repair_day.reshape(num_reals,1)
            redundant_comps_day = damage['fnc_filters']['hvac_unit_redundant'] * initial_damaged * redundant_sys_repair_day.reshape(num_reals,1)
            comp_breakdowns['hvac'][:,:,tu] = np.fmax(np.fmax(nonredundant_comps_day, redundant_comps_day), system_operation_day['comp']['hvac_main'])
    
            # HVAC Distribution - Tenant Level - subsystems
            subsystem_handle = ['hvac_duct_braches', 'hvac_in_line_fan', 'hvac_duct_drops', 'hvac_vav_boxes']
            for sub in range(len(subsystem_handle)):
                if sum(damage['fnc_filters']['hvac_duct_braches']) > 0:
                    subsystem_threshold = float(subsystems['redundancy_threshold'][subsystems['handle'] == subsystem_handle[sub]])
    
                    # Assess subsystem recovery day for this tenant unit
                    subsystem_recovery_day, subsystem_comp_recovery_day = fn_quantify_hvac_subsystem_recovery_day(
                        damage['fnc_filters'][subsystem_handle[sub]], total_num_comps, np.array(repair_complete_day), initial_damaged,
                        damaged_comps, subsystem_threshold, damage['comp_ds_table']['comp_idx'], damage['comp_ds_table']['is_sim_ds'])
    
                    # Compile with tenant unit performacne and component breakdowns
                    recovery_day['hvac'][:,tu] = np.fmax(recovery_day['hvac'][:,tu], subsystem_recovery_day)
                    comp_breakdowns['hvac'][:,:,tu] = np.fmax(comp_breakdowns['hvac'][:,:,tu], subsystem_comp_recovery_day)

    return recovery_day, comp_breakdowns    



