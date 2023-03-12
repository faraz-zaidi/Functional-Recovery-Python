def fn_calculate_reoccupancy(damage, damage_consequences, utilities, 
                         building_model, subsystems, functionality_options, 
                         tenant_units, impeding_temp_repairs):
    '''Calcualte the loss and recovery of building re-occupancy 
    % based on global building damage, local component damage, and extenernal factors
    %
    % Parameters
    % ----------
    % damage: dictionary
    %   contains per damage state damage, loss, and repair time data for each 
    %   component in the building
    % damage_consequences: dictionary
    %   data structure containing simulated building consequences, such as red
    %   tags and repair costs ratios
    % utilities: dictionary
    %   data structure containing simulated utility downtimes
    % building_model: dictionary
    %   general attributes of the building model
    % subsystems: DataFrame
    %   attributes of building subsystems; data provided in static tables
    %   directory
    % functionality_options: dictionary
    %   recovery time optional inputs such as various damage thresholds
    % tenant_units: DataFrame
    %   attributes of each tenant unit within the building
    %
    % Returns
    % -------
    % reoccupancy: dictionary
    %   contains data on the recovery of tenant- and building-level reoccupancy, 
    %   recovery trajectorires, and contributions from systems and components''' 
    
    ## Initial Set Up
    import numpy as np
    # Import packages
    
    from functionality import other_functionality_functions    
        
    ## Stage 1: Quantify the effect that component damage has on the building safety
    recovery_day={}
    comp_breakdowns={}
    
    recovery_day['building_safety'], comp_breakdowns['building_safety'] = other_functionality_functions.fn_building_safety(damage, building_model, 
                                                                                                                    damage_consequences, utilities, functionality_options
                                                                                                                    ,impeding_temp_repairs)
    
    ## Stage 2: Quantify the accessibility of each story in the building
    recovery_day['story_access'], comp_breakdowns['story_access'] = other_functionality_functions.fn_story_access( damage, 
                                                                                    building_model, damage_consequences, 
                                                                                    functionality_options)
    
    # Delete added door column to damage ['comps'] and damage[qnt_damaged]
    if len(damage['tenant_units']) !=1: #FZ# Story is accessible on day zero for 1 story building
        for i in range(len(damage['tenant_units'])):
            # damage['tenant_units'][i]['num_comps'].pop(-1) 
            damage['tenant_units'][i]['recovery']['repair_complete_day'] = damage['tenant_units'][i]['recovery']['repair_complete_day'][:,0:len(damage['comp_ds_table']['comp_id'])]
            for j in range(len(damage['tenant_units'][0]['qnt_damaged'])):
                damage['tenant_units'][i]['qnt_damaged'][j].pop(-1)
        
        # damage['fnc_filters']['fire_building'] = damage['fnc_filters']['fire_building'][0:len(damage['comp_ds_table']['comp_id'])]
        # damage['fnc_filters']['fire_drops'] =  damage['fnc_filters']['fire_drops'][0:len(damage['comp_ds_table']['comp_id'])]     
        damage['fnc_filters']['stairs'] = damage['fnc_filters']['stairs'][0:len(damage['comp_ds_table']['comp_id'])]   
        damage['fnc_filters']['stair_doors'] = damage['fnc_filters']['stair_doors'][0:len(damage['comp_ds_table']['comp_id'])]
    
    ## Stage 3: Quantify the effect that component damage has on the safety of each tenant unit
    recovery_day['tenant_safety'], comp_breakdowns['tenant_safety'] = other_functionality_functions.fn_tenant_safety( damage, building_model, functionality_options, tenant_units)
    
    ## Combine Check to determine the day the each tenant unit is reoccupiable
    # Check the day the building is Safe
    day_building_safe = np.fmax(recovery_day['building_safety']['red_tag'],
                        np.fmax(recovery_day['building_safety']['shoring'],
                        np.fmax(recovery_day['building_safety']['hazardous_material'],
                        np.fmax(recovery_day['building_safety']['entry_door_access'],
                        recovery_day['building_safety']['fire_suppression']))))
    # Check the day each story is accessible
    day_story_accessible = np.fmax(recovery_day['story_access']['stairs'], recovery_day['story_access']['stair_doors'])
    
    # Check the day each tenant unit is safe
    day_tenant_unit_safe = np.fmax(recovery_day['tenant_safety']['interior'], np.fmax(recovery_day['tenant_safety']['exterior'], recovery_day['tenant_safety']['hazardous_material']))
    
    # Combine checks to determine when each tenant unit is re-occupiable
    day_tenant_unit_reoccupiable = np.fmax(np.fmax(day_building_safe.reshape(len(day_building_safe),1), day_story_accessible), day_tenant_unit_safe)
    
    ## Reformat outputs into occupancy data strucutre
    reoccupancy = other_functionality_functions.fn_extract_recovery_metrics(day_tenant_unit_reoccupiable, 
                                              recovery_day, comp_breakdowns, 
                                              damage['comp_ds_table']['comp_id'],
                                              damage_consequences['simulated_replacement'])

    return reoccupancy