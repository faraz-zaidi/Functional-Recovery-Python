def build_input(output_path):
    # """
    # Code for generating simulated_inputs.json file
    
    # Parameters
    # ----------
    # output_path: string
    #     Path where the generated input file shall be saved.
    
    # """

    import numpy as np
    import json
    import pandas as pd
    import os
    import re
    import sys
    
    print(os.getcwd())
    
    ''' PULL STATIC DATA
    If the location of this directory differs, updat the static_data_dir variable below. '''
    
    static_data_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'static_tables')
    

    component_attributes = pd.read_csv(os.path.join(static_data_dir, 'component_attributes.csv'))
    damage_state_attribute_mapping  = pd.read_csv(os.path.join(static_data_dir, 'damage_state_attribute_mapping.csv'))
    subsystems = pd.read_csv(os.path.join(static_data_dir, 'subsystems.csv'))
    tenant_function_requirements = pd.read_csv(os.path.join(static_data_dir, 'tenant_function_requirements.csv'))
    
    
    ''' LOAD BUILDING DATA
    This data is specific to the building model and will need to be created
    for each assessment. Data is formated as json structures or csv tables'''
    
    # 1. Building Model: Basic data about the building being assessed
    building_model = json.loads(open('building_model.json').read())
    
    # If number of stories is 1, change individual values to lists in order to work with later code
    if building_model['num_stories'] == 1:
        for key in ['area_per_story_sf', 'ht_per_story_ft', 'occupants_per_story', 'stairs_per_story', 'struct_bay_area_per_story']:
            building_model[key] = [building_model[key]]
    if building_model['num_stories'] == 1:
        for key in ['edge_lengths']:
            building_model[key] = [[building_model[key][0]], [building_model[key][1]]]
    
    # 2. List of tenant units within the building and their basic attributes
    tenant_unit_list = pd.read_csv('tenant_unit_list.csv')
    
    
    # 3. List of component and damage states ids associated with the damage
    comp_ds_list = pd.read_csv('comp_ds_list.csv')
    
    # 4. List of component and damage states in the performance model
    comp_population = pd.read_csv('comp_population.csv')
    comp_header = list(comp_population.columns)
    comp_list = np.array(comp_header[2:len(comp_header)])
    comp_list= np.char.replace(np.array(comp_list),'_','.')
    comp_list = comp_list.tolist()
    # Remove suffixes from repated entries
    for i in range(len(comp_list)):
        if len(comp_list[i]) > 10:
            comp_list[i]=comp_list[i][0:10]
    building_model['comps'] = {'comp_list' : comp_list} #FZ# Component list has been added to building model dictionary.
    
    # Go through each story and assign component populations
    drs = np.unique(np.array(comp_population['dir']))
    
    building_model['comps']['story'] = {}
    for s in range (building_model['num_stories']):
        building_model['comps']['story'][s] = {}
        for d in range(len(drs)):
            filt = np.logical_and(np.array(comp_population['story']) == s+1, np.array(comp_population['dir']) == drs[d])
            building_model['comps']['story'][s]['qty_dir_' + str(drs[d])] = comp_population.to_numpy()[filt,2:len(comp_header)].tolist()[0]
    
    
    # Set comp info table
    comp_info = {'comp_id': [], 'comp_idx': [], 'structural_system': [], 'structural_system_alt': [], 'structural_series_id': []}
    for c in range(len(comp_list)):
        # Find the component attributes of this component
        comp_attr_filt = component_attributes['fragility_id'] == comp_list[c]
        if np.logical_not(sum(comp_attr_filt) == 1):
            sys.exit('error!.Could not find component attrubutes')
        else:
            comp_attr = component_attributes.to_numpy()[comp_attr_filt,:]
        comp_info['comp_id'].append(comp_list[c])
        comp_info['comp_idx'].append(c) #FZ# or c+1. Review in line with latter part of the code
        comp_info['structural_system'].append(float(comp_attr[0,[component_attributes.columns.get_loc('structural_system')]]))
        comp_info['structural_system_alt'].append(float(comp_attr[0,[component_attributes.columns.get_loc('structural_system_alt')]]))
        comp_info['structural_series_id'].append(float(comp_attr[0,[component_attributes.columns.get_loc('structural_series_id')]]))
    
    building_model['comps']['comp_table'] = comp_info
    
    
    ''' LOAD SIMULATED DATA
    This data is specific to the building performance at the assessed hazard intensity 
    and will need to be created for each assessment. 
    Data is formated as json structures.'''
    
    # 1. Simulated damage consequences - various building and story level consequences of simulated data, for each realization of the monte carlo simulation.
    damage_consequences = json.loads(open('damage_consequences.json').read())
    
    # 2. Simulated utility downtimes for electrical, water, and gas networks for each realization of the monte carlo simulation.
    # If file exists load it 
    if os.path.exists('utility_downtime.json') == True:
        functionality = json.loads(open('utility_downtime.json').read())
    # else If no data exist, assume there is no consequence of network downtime
    else:
        num_reals = len(damage_consequences["repair_cost_ratio_total"])
        functionality = {'utilities' : {'electrical':[], 'water':[], 'gas':[]} } 
    
        for real in range(num_reals):
            functionality['utilities']['electrical'].append(0)
            functionality['utilities']['water'].append(0)
            functionality['utilities']['gas'].append(0)
    
    
    # 3. Simulated component damage per tenant unit for each realization of the monte carlo simulation
    sim_damage = json.loads(open('simulated_damage.json').read())
    
    # Write in individual dictionaries part of larger 'damage' dictionary 
    damage = {'story' : {}, 'tenant_units' : {}}
    
    if 'story' in list(sim_damage.keys()):
        for tu in range(len(sim_damage['tenant_units'])):
            damage['tenant_units'][tu] = sim_damage['tenant_units'][tu]
    
    
    if 'tenant_units' in list(sim_damage.keys()):
        for s in range(len(sim_damage['story'])):
            damage['story'][s] = sim_damage['story'][s]
        
    ''' OPTIONAL INPUTS
    Various assessment otpions. Set to default options in the
    optional_inputs.json file. This file is expected to be in this input
    directory. This file can be customized for each assessment if desired.'''
    
    optional_inputs = json.load(open("optional_inputs.json"))
    functionality_options = optional_inputs['functionality_options']
    impedance_options = optional_inputs['impedance_options']
    repair_time_options = optional_inputs['repair_time_options'] 
    
    # Preallocate tenant unit table
    tenant_units = tenant_unit_list;
    tenant_units['exterior'] = np.zeros(len(tenant_units))
    tenant_units['interior'] = np.zeros(len(tenant_units))
    tenant_units['occ_per_elev'] = np.zeros(len(tenant_units))
    tenant_units['is_elevator_required'] = np.zeros(len(tenant_units))
    tenant_units['is_electrical_required'] = np.zeros(len(tenant_units))
    tenant_units['is_water_potable_required'] = np.zeros(len(tenant_units))
    tenant_units['is_water_sanitary_required'] = np.zeros(len(tenant_units))
    tenant_units['is_hvac_ventilation_required'] = np.zeros(len(tenant_units))
    tenant_units['is_hvac_heating_required'] = np.zeros(len(tenant_units))
    tenant_units['is_hvac_cooling_required'] = np.zeros(len(tenant_units))
    tenant_units['is_hvac_exhaust_required'] = np.zeros(len(tenant_units))
    tenant_units['is_data_required'] = np.zeros(len(tenant_units))  
    '''Pull default tenant unit attributes for each tenant unit listed in the
    tenant_unit_list'''
    for tu in range(len(tenant_unit_list)):
        fnc_requirements_filt = tenant_function_requirements['occupancy_id'] == tenant_units['occupancy_id'][tu]
        if sum(fnc_requirements_filt) != 1:
            sys.exit('error! Tenant Unit Requirements for This Occupancy Not Found')
        
        tenant_units['exterior'][tu] = tenant_function_requirements['exterior'][fnc_requirements_filt]
        tenant_units['interior'][tu] = tenant_function_requirements['interior'][fnc_requirements_filt]
        tenant_units['occ_per_elev'][tu] = tenant_function_requirements['occ_per_elev'][fnc_requirements_filt]
        if (tenant_function_requirements['is_elevator_required'][fnc_requirements_filt] == 1)[1]  and (tenant_function_requirements['max_walkable_story'][fnc_requirements_filt] < tenant_units['story'][tu])[1]:
            tenant_units['is_elevator_required'][tu] = 1
        else:
            tenant_units['is_elevator_required'][tu] = 0
    
        tenant_units['is_electrical_required'][tu] = tenant_function_requirements['is_electrical_required'][fnc_requirements_filt]
        tenant_units['is_water_potable_required'][tu] = tenant_function_requirements['is_water_potable_required'][fnc_requirements_filt]
        tenant_units['is_water_sanitary_required'][tu] = tenant_function_requirements['is_water_sanitary_required'][fnc_requirements_filt]
        tenant_units['is_hvac_ventilation_required'][tu] = tenant_function_requirements['is_hvac_ventilation_required'][fnc_requirements_filt]
        tenant_units['is_hvac_heating_required'][tu] = tenant_function_requirements['is_hvac_heating_required'][fnc_requirements_filt]
        tenant_units['is_hvac_cooling_required'][tu] = tenant_function_requirements['is_hvac_cooling_required'][fnc_requirements_filt]
        tenant_units['is_hvac_exhaust_required'][tu] = tenant_function_requirements['is_hvac_exhaust_required'][fnc_requirements_filt]
        tenant_units['is_data_required'][tu] = tenant_function_requirements['is_data_required'][fnc_requirements_filt]    
    '''Pull default component and damage state attributes for each component 
    in the comp_ds_list'''
    
    ## Populate data for each damage state
    comp_ds_info = {'comp_id' : [], 
                    'comp_type_id' : [], 
                    'comp_idx' : [], 
                    'ds_seq_id' : [], 
                    'ds_sub_id' : [],
                    'system' : [],
                    'subsystem_id' : [],
                    'structural_system' : [],
                    'structural_system_alt' : [],
                    'structural_series_id' : [],
                    'unit' : [],
                    'unit_qty' : [],
                    'service_location' : [],
                    'is_sim_ds' : [],
                    'safety_class' : [],
                    'affects_envelope_safety' : [],
                    'ext_falling_hazard' : [],
                    'int_falling_hazard' : [],
                    'global_hazardous_material' : [],
                    'local_hazardous_material' : [],
                    'weakens_fire_break' : [],
                    'affects_access' : [],
                    'damages_envelope_seal' : [],
                    'obstructs_interior_space' : [],
                    'impairs_system_operation' : [],
                    'causes_flooding' : [],
                    'fraction_area_affected' : [],
                    'area_affected_unit' : [],
                    'crew_size' : [],
                    'permit_type' : [],
                    'redesign' : [],
                    'long_lead_time' : [],
                    'requires_shoring' : [],
                    'resolved_by_scaffolding' : [],
                    'tmp_repair_class' : [],
                    'tmp_repair_time_lower' : [],
                    'tmp_repair_time_upper' : [],
                    'tmp_repair_time_lower_qnty' : [],
                    'tmp_repair_time_upper_qnty' : [],
                    'tmp_crew_size' : [],
                    'n1_redundancy' : [],
                    'parallel_operation' :[],
                    'redundancy_threshold' : []
                    }
    
    for c in range(len(comp_ds_list)):
        
        # Find the component attributes of this component
        comp_attr_filt = component_attributes['fragility_id'] == comp_ds_list['comp_id'][c]
        if sum(comp_attr_filt) != 1:
            sys.exit('error! Could not find component attrubutes')
        else:
            # comp_attr = component_attributes[comp_attr_filt,:);
            comp_attr = component_attributes.to_numpy()[comp_attr_filt,:]   #FZ# Changed to numpy array to filter out
            comp_attr = pd.DataFrame(comp_attr, columns = list(component_attributes.columns)) #FZ# Changed back to DataFrame
                  
        ds_comp_filt = []
        for frag_reg in range(len(damage_state_attribute_mapping["fragility_id_regex"])):
        
            # Mapping components with attributes - Cjecks are based on mapping, comp_id, seq_id and sub_id
        
            # Matching element ID using information contained in damage_state_attribute_mapping ["fragility_id_regex"]
            if re.search(damage_state_attribute_mapping["fragility_id_regex"][frag_reg], comp_ds_list["comp_id"][c]) == None:
                ds_comp_filt.append(0)
            elif (re.search(damage_state_attribute_mapping["fragility_id_regex"][frag_reg], comp_ds_list["comp_id"][c])).string == comp_ds_list["comp_id"][c]:
                ds_comp_filt.append(1)
            else:
                ds_comp_filt.append(0)    
        
        ds_seq_filt = damage_state_attribute_mapping['ds_index'] == comp_ds_list['ds_seq_id'][c]
        if comp_ds_list['ds_sub_id'][c] == 1:
            ds_sub_filt = np.logical_or(damage_state_attribute_mapping['sub_ds_index'] ==1, damage_state_attribute_mapping['sub_ds_index'].isnull())
        else:
            ds_sub_filt = damage_state_attribute_mapping['sub_ds_index'] == comp_ds_list['ds_sub_id'][c]
        
        ds_filt = ds_comp_filt & ds_seq_filt & ds_sub_filt
        
        if sum(ds_filt) != 1:
            sys.exit('error!, Could not find damage state attrubutes')
        else:
            ds_attr = damage_state_attribute_mapping.to_numpy()[ds_filt,:] #FZ# Changed to numpy array to filter out
            ds_attr = pd.DataFrame(ds_attr, columns = list(damage_state_attribute_mapping.columns)) #FZ# Changed back to DataFrame
        
        ## Populate data for each damage state
        # Basic Component and DS identifiers
        comp_ds_info['comp_id'].append(comp_ds_list['comp_id'][c])
        comp_ds_info['comp_type_id'].append(comp_ds_list['comp_id'][c][0:5]) # first 5 characters indicate the type
        comp_ds_info['comp_idx'].append(c)
        comp_ds_info['ds_seq_id'].append(ds_attr['ds_index'][0])
        # comp_ds_info['ds_sub_id'][c] = str2double(strrep(ds_attr.sub_ds_index{1},'NA','1'))
        comp_ds_info['ds_sub_id'].append(ds_attr['sub_ds_index'][0])
        if np.isnan(comp_ds_info['ds_sub_id'][c]):
            comp_ds_info['ds_sub_id'][c] = 1.0
            
        # Set Component Attributes
        comp_ds_info['system'].append(comp_attr['system_id'][0])
        comp_ds_info['subsystem_id'].append(comp_attr['subsystem_id'][0])
        comp_ds_info['structural_system'].append(comp_attr['structural_system'][0])
        comp_ds_info['structural_system_alt'].append(comp_attr['structural_system_alt'][0]) # component_attributes.csv does not have structural_system_alt field 
        comp_ds_info['structural_series_id'].append(comp_attr['structural_series_id'][0])
        comp_ds_info['unit'].append(comp_attr['unit'][0]) #FZ# Check w.r.t. matlab output
        comp_ds_info['unit_qty'].append(comp_attr['unit_qty'][0])
        comp_ds_info['service_location'].append(comp_attr['service_location'][0]) #FZ# Check w.r.t. matlab output
                   
        # Set Damage State Attributes
        comp_ds_info['is_sim_ds'].append(ds_attr['is_sim_ds'][0])
        comp_ds_info['safety_class'].append(ds_attr['safety_class'][0])
        comp_ds_info['affects_envelope_safety'].append(ds_attr['affects_envelope_safety'][0])
        comp_ds_info['ext_falling_hazard'].append(ds_attr['exterior_falling_hazard'][0])
        comp_ds_info['int_falling_hazard'].append(ds_attr['interior_falling_hazard'][0])
        comp_ds_info['global_hazardous_material'].append(ds_attr['global_hazardous_material'][0])
        comp_ds_info['local_hazardous_material'].append(ds_attr['local_hazardous_material'][0])
        comp_ds_info['weakens_fire_break'].append(ds_attr['weakens_fire_break'][0])
        comp_ds_info['affects_access'].append(ds_attr['affects_access'][0])
        comp_ds_info['damages_envelope_seal'].append(ds_attr['damages_envelope_seal'][0])
        comp_ds_info['obstructs_interior_space'].append(ds_attr['obstructs_interior_space'][0])
        comp_ds_info['impairs_system_operation'].append(ds_attr['impairs_system_operation'][0])
        comp_ds_info['causes_flooding'].append(ds_attr['causes_flooding'][0])
        comp_ds_info['fraction_area_affected'].append(ds_attr['fraction_area_affected'][0])
        comp_ds_info['area_affected_unit'].append(ds_attr['area_affected_unit'][0])
        comp_ds_info['crew_size'].append(ds_attr['crew_size'][0])
        comp_ds_info['permit_type'].append(ds_attr['permit_type'][0])
        comp_ds_info['redesign'].append(ds_attr['redesign'][0])
        comp_ds_info['long_lead_time'].append(impedance_options['default_lead_time'] * ds_attr['long_lead'][0])
        comp_ds_info['requires_shoring'].append(ds_attr['requires_shoring'][0])
        comp_ds_info['resolved_by_scaffolding'].append(ds_attr['resolved_by_scaffolding'][0])
        comp_ds_info['tmp_repair_class'].append(ds_attr['tmp_repair_class'][0])
        comp_ds_info['tmp_repair_time_lower'].append(ds_attr['tmp_repair_time_lower'][0])
        comp_ds_info['tmp_repair_time_upper'].append(ds_attr['tmp_repair_time_upper'][0])
        
        if comp_ds_info['tmp_repair_class'][c] > 0: # only grab values for components with temp repair times
            time_lower_quantity = ds_attr['time_lower_quantity'][0]
            time_upper_quantity = ds_attr['time_upper_quantity'][0]
        
            comp_ds_info['tmp_repair_time_lower_qnty'].append(time_lower_quantity)
            comp_ds_info['tmp_repair_time_upper_qnty'].append(time_upper_quantity)
        else:
            comp_ds_info['tmp_repair_time_lower_qnty'].append(np.nan)
            comp_ds_info['tmp_repair_time_upper_qnty'].append(np.nan)
    
        comp_ds_info['tmp_crew_size'].append(ds_attr['tmp_crew_size'][0])
    
        # Subsystem attributes
        subsystem_filt = subsystems['id'] == comp_attr['subsystem_id'][0]
        if comp_ds_info['subsystem_id'][c] == 0:
            # No subsytem
            comp_ds_info['n1_redundancy'].append(0)
            comp_ds_info['parallel_operation'].append(0)
            comp_ds_info['redundancy_threshold'].append(0)
        elif sum(subsystem_filt) != 1:
            sys.exit('error! Could not find damage state attrubutes')
        else:
            # Set Damage State Attributes
            comp_ds_info['n1_redundancy'].append(np.array(subsystems['n1_redundancy'])[subsystem_filt][0])
            comp_ds_info['parallel_operation'].append(np.array(subsystems['parallel_operation'])[subsystem_filt][0])
            comp_ds_info['redundancy_threshold'].append(np.array(subsystems['redundancy_threshold'])[subsystem_filt][0])
    
    damage['comp_ds_table'] = comp_ds_info
    
    ## Check missing data
    # Engineering Repair Cost Ratio - Assume is the sum of all component repair
    # costs that require redesign
    if 'repair_cost_ratio_engineering' in damage_consequences.keys() == False:
        eng_filt = np.array(damage['comp_ds_table']['redesign']).astype(bool)
        damage_consequences['repair_cost_ratio_engineering'] = np.zeros(len(damage_consequences['repair_cost_ratio_total']))
        for s in range(len(sim_damage['story'])):
            damage_consequences['repair_cost_ratio_engineering'] = damage_consequences['repair_cost_ratio_engineering'] + np.sum(sim_damage['story'][s]['repair_cost'][:,eng_filt], axis = 1)
    

    # Covert to Python int and floats for creating .json file
    for key in list(damage['comp_ds_table'].keys()):
        for i in range(len(damage['comp_ds_table'][key])):
            if type(damage['comp_ds_table'][key][i]) == np.int64:
                damage['comp_ds_table'][key][i] = int(damage['comp_ds_table'][key][i])
            if type(damage['comp_ds_table'][key][i]) == np.float64:
                damage['comp_ds_table'][key][i] = float(damage['comp_ds_table'][key][i])            
    
    for key in list(tenant_units.keys()):
        for i in range(len(tenant_units[key])):
            if type(tenant_units[key][i]) == np.int64:
                tenant_units[key][i] = int(tenant_units[key][i])
            if type(tenant_units[key][i]) == np.float64:
                tenant_units[key][i] = float(tenant_units[key][i])  
    
    # Convert tenant_units dataframe to dictionary
    tenant_units_dict = {}
    for i in list(tenant_units.columns):
        tenant_units_dict[i] = list(tenant_units[i])
        
    tenant_units = tenant_units_dict
         
    # Export output as simulated_inputs.json file 
    
    simulated_inputs = {'building_model' : building_model, 'damage' : damage, 'damage_consequences' : damage_consequences, 'functionality' : functionality, 'functionality_options' : functionality_options, 'impedance_options' : impedance_options, 'repair_time_options' : repair_time_options, 'tenant_units' : tenant_units}
    
    for inp in simulated_inputs:
        output_json_object = json.dumps(simulated_inputs)
    
    # with open("simulated_inputs.json", "w") as outfile:
    #     outfile.write(output_json_object)
    
    with open(output_path, "w") as outfile:
        outfile.write(output_json_object)       

if __name__ == '__main__':

    output_path = "simulated_inputs.json"

    build_input(output_path)   
