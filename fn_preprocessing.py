
def fn_preprocessing(comp_ds_table):
    '''Function for filtering damage data to be applied in the main code
    
    Parameters
    ----------
    comp_ds_table: DataFrame
      various component attributes by damage state for each component 
      within the performance model. Can be populated from the 
      component_attribites.csv and damage_state_attribute_mapping.csv 
      databases in the static_tables directory.  Each row of the table 
      corresponds to each column of the simulated component damage arrays 
      within damage.tenant_units.
    
    Returns
    -------
    fnc_filters: dictionary
      logical filters controlling the function and reoccupancy 
      consequences of various component damage states. Primarily used to
      expidite the assessment in the functionality module. Each field is a 
      [1xn] array where n represents the damage state of each component 
      populated in the builing and corresponding to the columns of the 
      simulated component damage arrays within damage.tenant_units.'''


    ## Combine compoment attributes into recovery filters to expidite recovery assessment
    # combine all damage state filters that have the potential to affect
    # function, other than structural safety damage (for repair prioritization)
    
    # Convert damage['comp_ds_table'] lists to numpy arrays
    import numpy as np    
    
    comp_ds_table_keys = list(comp_ds_table.keys())
    
    for key in comp_ds_table_keys:
        comp_ds_table[key] = np.array(comp_ds_table[key])
    
    fnc_filters={}
    
    fnc_filters['affects_function'] = comp_ds_table['affects_envelope_safety'].astype('bool') | comp_ds_table['ext_falling_hazard'].astype('bool') | comp_ds_table['int_falling_hazard'].astype('bool') | comp_ds_table['global_hazardous_material'].astype('bool') | comp_ds_table['local_hazardous_material'].astype('bool') | comp_ds_table['affects_access'].astype('bool') | comp_ds_table['damages_envelope_seal'].astype('bool') | comp_ds_table['obstructs_interior_space'].astype('bool') | comp_ds_table['impairs_system_operation'].astype('bool')    
    
    # Define when building has resolved its red tag (when all repairs are complete that may affect red tags)
    # get any components that have the potential to cause red tag
    fnc_filters['red_tag'] = comp_ds_table['safety_class'] > 0 
    
    # fire suppresion system damage that affects entire building
    fnc_filters['fire_building'] = np.logical_and(comp_ds_table['system'] == 9, np.logical_and(comp_ds_table['service_location'] == 'building' , comp_ds_table['impairs_system_operation'] == 1))
    
    # fire suppresion damage that affects each tenant unit
    fnc_filters['fire_drops'] = np.logical_and(comp_ds_table['subsystem_id'] == 23, comp_ds_table['impairs_system_operation'] == 1)
    
    # Hazardous materials
    fnc_filters['global_hazardous_material'] = comp_ds_table['global_hazardous_material'].astype('bool')
    fnc_filters['local_hazardous_material'] = comp_ds_table['local_hazardous_material'].astype('bool')
    
    # Stairs
    fnc_filters['stairs'] = np.logical_and(comp_ds_table['affects_access'] == 1, comp_ds_table['system'] == 4)
    
    # Exterior enclosure damage
    fnc_filters['exterior_safety_lf'] = np.logical_and(comp_ds_table['unit'] == 'lf', comp_ds_table['affects_envelope_safety'] == 1) # Components with perimeter linear feet units
    fnc_filters['exterior_safety_sf'] = np.logical_and(comp_ds_table['unit'] == 'sf' , comp_ds_table['affects_envelope_safety'] == 1) # Components with perimeter square feet units
    fnc_filters['exterior_safety_all'] = fnc_filters['exterior_safety_lf'] | fnc_filters['exterior_safety_sf']
    
    # Exterior Falling hazards
    fnc_filters['ext_fall_haz_lf'] = np.logical_and(comp_ds_table['unit'] =='lf', comp_ds_table['ext_falling_hazard'] == 1) # Components with perimeter linear feet units
    fnc_filters['ext_fall_haz_sf'] = np.logical_and(comp_ds_table['unit'] == 'sf', comp_ds_table['ext_falling_hazard'] == 1) # Components with perimeter square feet units
    fnc_filters['ext_fall_haz_all'] = fnc_filters['ext_fall_haz_lf'] | fnc_filters['ext_fall_haz_sf']
    
    # Exterior enclosure envelope seal damage
    fnc_filters['exterior_seal_lf'] = np.logical_and(comp_ds_table['unit'] == 'lf', comp_ds_table['damages_envelope_seal'] == 1) # Components with perimeter linear feet units
    fnc_filters['exterior_seal_sf'] = np.logical_and(comp_ds_table['unit'] == 'sf', comp_ds_table['damages_envelope_seal'] == 1) # Components with perimeter square feet units
    fnc_filters['exterior_seal_all'] = fnc_filters['exterior_seal_lf'] | fnc_filters['exterior_seal_sf']
    
    # Roofing components
    fnc_filters['roof_structure'] = np.logical_and(comp_ds_table['subsystem_id'] == 21, comp_ds_table['damages_envelope_seal'] == 1)
    fnc_filters['roof_weatherproofing'] = np.logical_and(comp_ds_table['subsystem_id'] == 22, comp_ds_table['damages_envelope_seal'] == 1)
    
    # Interior falling hazards
    fnc_filters['int_fall_haz_lf'] = np.logical_and(comp_ds_table['int_falling_hazard'] == 1, comp_ds_table['unit'] == 'lf') # Interior components with perimeter feet units
    fnc_filters['int_fall_haz_sf'] = np.logical_and(comp_ds_table['int_falling_hazard'] == 1, np.logical_or(comp_ds_table['unit'] == 'sf', comp_ds_table['unit'] == 'each')) # Interior components with area feet units (or each, which is just lights, which we take care of with the fraction affected area, which is probably not the best way to do it)
    fnc_filters['int_fall_haz_bay'] = np.logical_and(comp_ds_table['int_falling_hazard'] == 1, comp_ds_table['area_affected_unit'] == 'bay') # structural damage that does not cause red tags but affects function
    fnc_filters['int_fall_haz_build'] = np.logical_and(comp_ds_table['int_falling_hazard'] == 1, comp_ds_table['area_affected_unit'] == 'building') # structural damage that does not cause red tags but affects funciton (this one should only be tilt-ups)
    fnc_filters['int_fall_haz_all'] = fnc_filters['int_fall_haz_lf'] | fnc_filters['int_fall_haz_sf'] | fnc_filters['int_fall_haz_bay'] | fnc_filters['int_fall_haz_build'] 
    fnc_filters['vert_instabilities'] = np.logical_and(comp_ds_table['system'] == 1, comp_ds_table['int_falling_hazard'] == 1) # Flag structural damage that causes interior falling hazards
    
    # Interior function damage 
    fnc_filters['interior_function_lf'] = np.logical_and(comp_ds_table['obstructs_interior_space'] == 1, comp_ds_table['unit'] == 'lf'); 
    fnc_filters['interior_function_sf'] = np.logical_and(comp_ds_table['obstructs_interior_space'] == 1, np.logical_or(comp_ds_table['unit'] == 'sf', comp_ds_table['unit'] == 'each')) 
    fnc_filters['interior_function_bay'] = np.logical_and(comp_ds_table['obstructs_interior_space'] == 1, comp_ds_table['area_affected_unit'] == 'bay')
    fnc_filters['interior_function_build'] = np.logical_and(comp_ds_table['obstructs_interior_space'] == 1, comp_ds_table['area_affected_unit'] == 'building')  
    fnc_filters['interior_function_all'] = fnc_filters['interior_function_lf'] | fnc_filters['interior_function_sf'] | fnc_filters['interior_function_bay'] | fnc_filters['interior_function_build']  
    
    # Elevators
    fnc_filters['elevators'] = np.logical_and(comp_ds_table['system'] == 5, np.logical_and(comp_ds_table['impairs_system_operation'], comp_ds_table['subsystem_id'] != 2))
    fnc_filters['elevator_mcs'] = np.logical_and(comp_ds_table['system'] == 5, np.logical_and(comp_ds_table['impairs_system_operation'], comp_ds_table['subsystem_id'] == 2))
    
    # Electrical system
    fnc_filters['electrical_main'] = np.logical_and(comp_ds_table['system'] == 7, np.logical_and(comp_ds_table['subsystem_id'] == 1, np.logical_and(comp_ds_table['service_location'] == 'building', comp_ds_table['impairs_system_operation'] == 1)))
    fnc_filters['electrical_unit'] = np.logical_and(comp_ds_table['system'] == 7, np.logical_and(comp_ds_table['subsystem_id'] == 1, np.logical_and(comp_ds_table['service_location'] == 'unit', comp_ds_table['impairs_system_operation'] == 1)))
    
    # Water and Plumbing
    fnc_filters['water_main'] = np.logical_and(comp_ds_table['system'] == 6, np.logical_and(comp_ds_table['service_location'] == 'building', comp_ds_table['impairs_system_operation'] == 1))
    fnc_filters['water_unit'] = np.logical_and(comp_ds_table['system'] == 6, np.logical_and(comp_ds_table['service_location'] == 'unit', comp_ds_table['impairs_system_operation'] == 1))
    
    # HVAC
    hvac_equip = np.logical_and(comp_ds_table['system'] == 8, np.isin(comp_ds_table['subsystem_id'],[15,16,17,18,19,20]))
    fnc_filters['hvac_main'] = np.logical_and(hvac_equip, np.logical_and(comp_ds_table['service_location'] == 'building', comp_ds_table['impairs_system_operation'] == 1))
    fnc_filters['hvac_main_nonredundant'] = np.logical_and(fnc_filters['hvac_main'], comp_ds_table['parallel_operation'] == 0)
    fnc_filters['hvac_main_redundant'] = np.logical_and(fnc_filters['hvac_main'], comp_ds_table['parallel_operation'] == 1)
    
    
    fnc_filters['hvac_duct_mains'] = np.logical_and(comp_ds_table['system'] == 8, np.logical_and(comp_ds_table['subsystem_id'] == 4, np.logical_and(comp_ds_table['service_location'] == 'building', comp_ds_table['impairs_system_operation'] == 1)))
    
    fnc_filters['hvac_cooling_piping'] = np.logical_and(comp_ds_table['system'] == 8, np.logical_and(comp_ds_table['subsystem_id'] == 11, comp_ds_table['impairs_system_operation'] == 1))
    fnc_filters['hvac_heating_piping'] = np.logical_and(comp_ds_table['system'] == 8, np.logical_and(comp_ds_table['subsystem_id'] == 10, comp_ds_table['impairs_system_operation'] == 1))
    
    fnc_filters['hvac_unit'] = np.logical_and(hvac_equip, np.logical_and(comp_ds_table['service_location'] == 'unit', comp_ds_table['impairs_system_operation'] == 1))
    fnc_filters['hvac_unit_nonredundant'] = np.logical_and(fnc_filters['hvac_unit'], comp_ds_table['parallel_operation'] == 0)
    fnc_filters['hvac_unit_redundant'] = np.logical_and(fnc_filters['hvac_unit'], comp_ds_table['parallel_operation'] == 1)
    
    fnc_filters['hvac_duct_braches'] = np.logical_and(comp_ds_table['system'] == 8, np.logical_and(comp_ds_table['subsystem_id'] == 4, np.logical_and(comp_ds_table['service_location'] == 'unit', comp_ds_table['impairs_system_operation'] == 1)))
    fnc_filters['hvac_in_line_fan'] = np.logical_and(comp_ds_table['system'] == 8, np.logical_and(comp_ds_table['subsystem_id'] == 5, np.logical_and(comp_ds_table['service_location'] == 'unit', comp_ds_table['impairs_system_operation'] == 1)))
    fnc_filters['hvac_duct_drops'] = np.logical_and(comp_ds_table['system'] == 8, np.logical_and(comp_ds_table['subsystem_id'] == 6, np.logical_and(comp_ds_table['service_location'] == 'unit', comp_ds_table['impairs_system_operation'] == 1)))
    
    fnc_filters['hvac_vav_boxes'] = np.logical_and(comp_ds_table['system'] == 8, np.logical_and(comp_ds_table['subsystem_id'] == 7, np.logical_and(comp_ds_table['service_location'] == 'unit', comp_ds_table['impairs_system_operation'] == 1)))
    fnc_filters['hvac_mcs'] = np.logical_and(comp_ds_table['system'] == 8, np.logical_and(comp_ds_table['impairs_system_operation'] ==1, comp_ds_table['subsystem_id'] == 2))
    
    
    # %% Flip orientation of fnc_filters to match orientation of damage data [reals x ds]
    # names = fieldnames(fnc_filters);
    # for fn = 1:length(names)
    #     tmp_fnc_filt.(names{fn}) = fnc_filters.(names{fn})';
    # end
    # fnc_filters = tmp_fnc_filt;
    
    return fnc_filters