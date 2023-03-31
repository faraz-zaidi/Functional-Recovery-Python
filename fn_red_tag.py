def fn_red_tag( calculate_red_tag, damage, comps, simulated_replacement):
    '''Perform the ATC-138 functional recovery time assessement given similation
    of component damage for a single shaking intensity
    
    Parameters
    ----------
    calculate_red_tag: logical
      flag to indicate whether on not to calculate red tags based on
      component damage. Typically assumed to be FALSE for small wood light
      frame type structures.
    damage: dictionary
      contains per damage state damage and loss data for each component in the building
    comps: dictionary
      data structure component population info
    simulated_replacement: array [num reals x 1]
      Time 
    
    Returns
    -------
    red_tag: logical array [num_reals x 1]
      indicates the realizations that have a red tag
    red_tag_impact: logical array [num_reals x num_comp_ds]
      indicates the realizations of various component damage states that
      contribute to the cause of red tag
    inspection_tag: logical array [num_reals x 1]
      indicates the realizations that require inspection'''
    
    import numpy as np
    
    def simulate_tagging(damage, comps, sc_ids, sc_thresholds):
        
        red_tag_impact = np.zeros(np.shape(damage['tenant_units'][0]['qnt_damaged'])) # num reals by num comp_ds
        
        num_reals = len(red_tag_impact)
        # Go through each structural system and calc the realizations where the
        # building is red tagged
        
        sc_tag = np.zeros([num_reals,len(sc_ids)])
        for sc in range(len(sc_ids)):
            
            story_tag = np.zeros([num_reals,len(damage['story'])])
            
            for s in range(len(damage['story'])):
                sc_filt = np.array(damage['comp_ds_table']['safety_class']) >= sc_ids[sc]
                
                dir_tag = np.zeros([num_reals, 3])
                for direc in [1,2,3]: # Fix assume there are three direction, where direction 3 = nondirectional
                    sc_dmg = np.array(damage['story'][s]['qnt_damaged_dir_' + str(direc)]) * sc_filt
                    num_comps = np.array(comps['story'][s]['qty_dir_' + str(direc)])
        
                    # For each structural system
                    structural_systems = np.unique(np.array(damage['comp_ds_table']['structural_system'] + damage['comp_ds_table']['structural_system_alt']))
                    structural_systems = np.delete(structural_systems, 0) # do not include components not assigned to a structural system
                    
                    sys_tag = np.zeros([num_reals, len(structural_systems)]).astype(bool)
                    
                    for sys in range(len(structural_systems)):
                        ss_filt_ds = np.logical_or(np.array(damage['comp_ds_table']['structural_system']) == structural_systems[sys], np.array(damage['comp_ds_table']['structural_system_alt']) == structural_systems[sys])
                        ss_filt_comp = np.logical_or(np.array(comps['comp_table']['structural_system']) == structural_systems[sys], np.array(comps['comp_table']['structural_system_alt']) == structural_systems[sys])
        
                        # Check damage among each series within this structural system
                        series = np.unique(np.array(damage['comp_ds_table']['structural_series_id'])[ss_filt_ds])
                        ser_dmg = np.zeros([num_reals,len(series)])
                        ser_qty = np.zeros([num_reals,len(series)])
                        for ser in range(len(series)):
                            ser_filt_ds = np.array(damage['comp_ds_table']['structural_series_id']) == series[ser] 
                            ser_filt_comp = np.array(comps['comp_table']['structural_series_id']) == series[ser] 
        
                            # Total damage within this series and system
                            ser_dmg[:,ser] = np.sum(sc_dmg[:,ser_filt_ds & ss_filt_ds], axis=1)
        
                            # Total number of components within this series and system
                            ser_qty[:,ser] = np.sum(num_comps[ser_filt_comp & ss_filt_comp])
        
                        # Check if this system is causing a red tag
                        sys_dmg = np.nanmax(ser_dmg, axis = 1)
                        sys_qty = np.nanmax(ser_qty, axis = 1)
                        sys_ratio = sys_dmg / sys_qty
                        sys_tag[:,sys] = sys_ratio > sc_thresholds[sc]
                        
                        '''Calculate the impact that each component has on red tag
                        (boolean, 1 = affects red tag, 0 = does not affect)
                        Take all damage that is part of this system at this story
                        in this direction that is damaged to this safety class
                        level, only where damage exceeds tagging threshold'''
                        red_tag_impact = np.fmax(red_tag_impact, 1*sys_tag[:,sys].reshape(len(sys_tag),1) * ss_filt_ds.reshape(1,len(ss_filt_ds)) * sc_filt.reshape(1,len(ss_filt_ds)) * (sc_dmg>0))
                    
                    
                    # Combine across all systems in this direction
                    dir_tag[:,direc-1] = np.nanmax(sys_tag, axis = 1) #FZ# -1 done to account for python ndexing starting from zero
                
        
                # Combine across all directions at this story
                story_tag[:,s] = np.nanmax(dir_tag, axis = 1)
    
            
            # Combine across all stories for this safety class
            sc_tag[:,sc] = np.nanmax(story_tag, axis = 1)
       
        # Combine all safety class checks into one simulated red tag
        red_tag =  np.nanmax(sc_tag, axis = 1)
        
        return red_tag, red_tag_impact
    
    ##Initial Setup
    '''Check to see if any components need the red tag check
    if none of the components are assinged to structural systems, then
    skip the red tag calc'''
    if any(comps['comp_table']['structural_system']) == False:
        calculate_red_tag = False
    else:
        calculate_red_tag = True
    
    ## Method
    if calculate_red_tag == True:
        # Simulate Red Tags
        sc_ids = np.array([1, 2, 3, 4])
        sc_thresholds = np.array([0.5, 0.25, 0.1, 0])
        red_tag, red_tag_impact = simulate_tagging(damage, comps, sc_ids, sc_thresholds)
    
        # Inspection is flagged for 50% of the red tag thresholds
        inspection_tag = simulate_tagging(damage, comps, sc_ids, 0.5*sc_thresholds)[0]
    
    else:
        
        # Do not calculate red tags based on component damage
        num_reals, num_comp_ds = np.shape(np.array(damage['tenant_units'][0]['qnt_damaged']))
        red_tag = np.zeros(num_reals)
        red_tag_impact = np.zeros([num_reals,num_comp_ds])
        inspection_tag = np.zeros(num_reals)
    
    
    # Account for global red tag cases
    replace_case = np.logical_not(np.isnan(np.array(simulated_replacement)))
    red_tag[replace_case] = 1
    
    return red_tag, red_tag_impact, inspection_tag
    
    
