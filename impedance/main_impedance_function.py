def main_impeding_factors(damage, impedance_options, repair_cost_ratio, inspection_trigger, systems, building_value, impeding_factor_medians, surge_factor):

    '''Calculate ATC-138 impeding times for each system given simulation of damage
    
    Parameters (taken from Dustin's MATLAB file)
    ----------
    damage: dictionary
      contains per damage state damage and loss data for each component in the building
    
    impedance_options: dictionary
      general impedance assessment user inputs such as mitigation factors
    
    repair_cost_ratio: array [num_reals x 1]
      total repair cost per realization normalized by building replacement
      value
    
    inspection_trigger: logical array [num_reals x 1]
      defines which realizations require inspection
    
    num_stories: int
      Total number of building stories
    
    systems: DataFrame
      data table containing information about each system's attributes
    
    building_value: number
      The replacement value of the building, in USD
   
    impeding_factor_medians: table
      median delays for various impeding factors
   
    surge_factor: number
      amplification factor for imepding times due to materials and labor
      impacts due to regional damage
    
    Returns
    -------
    impedingFactors.time_sys: array [num_reals x num_sys]
      Simulated total impeding time for each system
    
    impedingFactors.breakdown: Dictionary
      feilds: 'inspection', 'financing', 'eng_mob', 'design', 'permitting', 'contractor_mob'
      The simulated start day and complete day for each impeding factor,
      broken down per system where applicable
      
    
    Notes
    -----
    Correlation: Assuming factor-to-factor simulations are independent, but
    within a given factor, simulated system impedance time is fully
    correlated'''
    
    import numpy as np
    from scipy.stats import truncnorm
    from impedance import other_impedance_functions

    # Initialize parameters
    num_reals = len(inspection_trigger)
    num_sys = len(systems) # used height in MATLAB - Correlate with MATLAB at the time of running
    
    # Preallocate each impedance time
    duration={
    'inspection': np.zeros([num_reals, num_sys]),
    'financing': np.zeros([num_reals, num_sys]),
    'permitting': np.zeros([num_reals, num_sys]),
    'contractor_mob': np.zeros([num_reals, num_sys]),
    'eng_mob': np.zeros([num_reals, num_sys]),
    'design': np.zeros([num_reals, num_sys]),        
        }
    
    # System repair trigger
    # are there any repairs needed for this system
    # sys_repair_trigger = system_repair_time > 0
    
    # Create basic trucated standard normal distribution for later simulation
    th_low = -impedance_options['impedance_truncation']
    th_high = impedance_options['impedance_truncation']  
    mu = 0
    sigma = 1
    trunc_pd = truncnorm((th_low - mu)/sigma, (th_high - mu)/sigma, loc=mu, scale=sigma)
    beta = impedance_options['impedance_beta']
    
    # Parse through damage to determine which systems require repair
    rapid_permit_filt = np.array(damage['comp_ds_table']['permit_type']) == 'rapid'
    full_permiting_filt = np.array(damage['comp_ds_table']['permit_type']) == 'full'
    redesign_filt = np.array(damage['comp_ds_table']['redesign']) == 1
    
    
    sys_repair_trigger = {
        'any': np.zeros([num_reals, num_sys]),
        'rapid_permit' : np. zeros([num_reals, num_sys]),
        'full_permit' : np.zeros([num_reals, num_sys]),
        'redesign' : np. zeros([num_reals, num_sys]),
        }
    for sys in range(num_sys):
        sys_filt = np.array(damage['comp_ds_table']['system']) == sys+1 # +1 is done to coorrelate with python indexing starting from 0. 
        for tu in range(len(damage['tenant_units'])): 
            is_damaged = np.array(damage['tenant_units'][tu]['qnt_damaged']) > 0
            # Track if any damage exists that requires repair (assumes all
            # damage requires repair)
            sys_repair_trigger['any'][:,sys] = np.maximum(sys_repair_trigger['any'][:,sys] , np.amax((np.multiply( 1*(is_damaged) , 1*(sys_filt) )), axis=1))
            
            # Track if any damage exists that requires rapid permit per system
            sys_repair_trigger['rapid_permit'][:,sys] = np.maximum(sys_repair_trigger['rapid_permit'][:,sys] , np.amax((np.multiply( 1*(is_damaged) , ( 1*(sys_filt) & 1*(rapid_permit_filt)))), axis=1))
            
            # Track if any damage exists that requires full permit per system
            sys_repair_trigger['full_permit'][:,sys] = np.maximum(sys_repair_trigger['full_permit'][:,sys] , np.amax((np.multiply( 1*(is_damaged) , ( 1*(sys_filt) & 1*(full_permiting_filt)))), axis=1))            
            
            # Track if any systems require redesign
            sys_repair_trigger['redesign'][:,sys] = np.maximum(sys_repair_trigger['redesign'][:,sys] , np.amax((np.multiply( 1*(is_damaged) , ( 1*(sys_filt) & 1*(redesign_filt)))), axis=1))         



    # Simulate impedance time for each impedance factor 
    duration = {}
        
    if impedance_options['include_impedance']['inspection'] == True:
       
        duration['inspection'] = other_impedance_functions.fn_inspection(impedance_options['mitigation']['is_essential_facility'],
            impedance_options['mitigation']['is_borp_equivalent'], 
            surge_factor, sys_repair_trigger['any'], inspection_trigger,
            trunc_pd, beta, impeding_factor_medians)
    
    if impedance_options['include_impedance']['financing'] == True:
       
        duration['financing'] = other_impedance_functions.fn_financing(impedance_options['mitigation']['capital_available_ratio'],
            impedance_options['mitigation']['funding_source'], 
            surge_factor, sys_repair_trigger['any'], repair_cost_ratio,
            trunc_pd, beta, impeding_factor_medians)
        
    if impedance_options['include_impedance']['permitting'] == True:
       
        duration['permitting'] = other_impedance_functions.fn_permitting(num_reals,
            surge_factor, sys_repair_trigger, trunc_pd,
            beta, impeding_factor_medians)
    
    
    if impedance_options['include_impedance']['contractor'] == True:    
        duration['contractor_mob'] = other_impedance_functions.fn_contractor(num_sys, num_reals,
            surge_factor, sys_repair_trigger['any'],
            systems, impedance_options['mitigation']['is_contractor_on_retainer'])
    
    if impedance_options['include_impedance']['engineering'] == True:     
        
        [ duration['eng_mob'], duration['design'] ] = other_impedance_functions.fn_engineering( num_reals,
            repair_cost_ratio, building_value, surge_factor,
            sys_repair_trigger['redesign'],
            impedance_options['mitigation']['is_engineer_on_retainer'],
            impedance_options['system_design_time'],
            systems['imped_design_min_days'], systems['imped_design_max_days'],
            trunc_pd, beta, impeding_factor_medians)


    ## Aggregate experienced impedance time for each system/sequence and realization 
    # Figure out when each impeding factor finishes
    start_day = {'inspection' : np.zeros([num_reals,num_sys])}
    complete_day = {'inspection' : duration['inspection']}
    
    start_day['financing'] = complete_day['inspection'];
    complete_day['financing'] = start_day['financing'] + duration['financing'];
    
    start_day['eng_mob'] = np.maximum(complete_day['inspection'] ,start_day['financing']);
    complete_day['eng_mob'] = start_day['eng_mob'] + duration['eng_mob'];
    
    start_day['design'] = complete_day['eng_mob']
    complete_day['design'] = start_day['design'] + duration['design'];
    
    start_day['permitting'] = complete_day['design'];
    complete_day['permitting'] = start_day['permitting'] + duration['permitting'];
    
    start_day['contractor_mob'] = np.maximum(complete_day['inspection'], start_day['financing']);
    complete_day['contractor_mob'] = start_day['contractor_mob'] + duration['contractor_mob'];
    
    # Combine all impedance factors by system
    impede_factors = np.array(list(complete_day.keys()));
    impeding_factors = {'time_sys' : 0}
    for i in range(len(impede_factors)):
        impeding_factors['time_sys'] = np.maximum(impeding_factors['time_sys'],
            complete_day[impede_factors[i]])
    
    
    ## Format Impedance times for Gantt Charts                                                     
    
    impeding_factors['breakdowns']={'inspection':{'start_day': np.amax(start_day['inspection'],1), 
                                                  'complete_day': np.amax(complete_day['inspection'],1)}} 
    impeding_factors['breakdowns']['financing'] = {'start_day': np.amax(start_day['financing'],1), 
                                                  'complete_day': np.amax(complete_day['financing'],1)}                                    
                                    
    
                                                        
    select_sys = [1, 2, 4] # only for structure, exterior, and stairs
    impeding_factors['breakdowns']['eng_mob']={}
    impeding_factors['breakdowns']['design']={}
    for ss in select_sys:
        
        impeding_factors['breakdowns']['eng_mob'][str(systems['name'][ss-1])] = {'start_day' : start_day['eng_mob'][:,ss-1],
                                                                                  'complete_day' : complete_day['eng_mob'][:,ss-1]}
        
        impeding_factors['breakdowns']['design'][str(systems['name'][ss-1])] = {'start_day' : start_day['design'][:,ss-1],
                                                                                  'complete_day' : complete_day['design'][:,ss-1]}   
    impeding_factors['breakdowns']['permitting']={}
    impeding_factors['breakdowns']['contractor_mob']={}        
    for s in range(len(systems)):
        impeding_factors['breakdowns']['permitting'][str(systems['name'][s])] = {'start_day' : start_day['permitting'][:,s],
                                                                                  'complete_day' : complete_day['permitting'][:,s]}
    
        impeding_factors['breakdowns']['contractor_mob'][str(systems['name'][s])] = {'start_day' : start_day['contractor_mob'][:,s],
                                                                                  'complete_day' : complete_day['contractor_mob'][:,s]}
        
    return impeding_factors