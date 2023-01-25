

def build_input(output_path):
    """
    Code for generating simulated_inputs.json file

    Parameters
    ----------
    output_path: string
        Path where the generated input file shall be saved.

    """

    import numpy as np
    import json
    import pandas as pd
    import os
    import re
    import sys

    print(os.getcwd())

    ''' LOAD BUILDING DATA
    This data is specific to the building model and will need to be created
    for each assessment. Data is formated as json structures or csv tables'''

    # 1. Building Model: Basic data about the building being assessed
    building_model = json.loads(open('building_model.json').read())

    #FZ#If number of stories is 1, change individual values to lists inorder to work with later code
    if building_model['num_stories'] == 1:
        for key in ['area_per_story_sf', 'edge_lengths', 'ht_per_story_ft', 'occupants_per_story', 'stairs_per_story', 'struct_bay_area_per_story']:
            building_model[key] = [building_model[key]]

    # 2. List of tenant units within the building and their basic attributes
    tenant_unit_list = pd.read_csv('tenant_unit_list.csv')


    # 3. List of component and damage states in the performance model
    comp_ds_list = pd.read_csv('comp_ds_list.csv')


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
        num_reals = len(damage_consequences["red_tag"])
        functionality = {'utilities' : {'electrical':[], 'water':[], 'gas':[]} } 

        for real in range(num_reals):
            functionality['utilities']['electrical'].append(0)
            functionality['utilities']['water'].append(0)
            functionality['utilities']['gas'].append(0)
    # 3. Simulated component damage per tenant unit for each realization of the monte carlo simulation
    sim_tenant_unit_damage = json.loads(open('simulated_damage.json').read())

    # Write in individual dictionaries part of larger 'damage' dictionary


    damage = {"tenant_units":sim_tenant_unit_damage}

    num_comps = []

    for tu in range(len(sim_tenant_unit_damage)):
        num_comps.append(sim_tenant_unit_damage[tu]['num_comps'])


    ''' LOAD SIMULATED DATA
    Various assessment otpions. Set to default options in the
    optional_inputs.m file. This file is expected to be in this input
    directory. This file can be customized for each assessment if desired.'''

    optional_inputs = json.load(open("optional_inputs.json"))
    functionality_options = optional_inputs['functionality_options']
    impedance_options = optional_inputs['impedance_options']
    regional_impact = optional_inputs['regional_impact']
    repair_time_options = optional_inputs['repair_time_options'] 

    ''' PULL ADDITIONAL ATTRIBUTES FROM THE STATIC DATA TABLES'''

    # Specify folder comtaining static tables
    # folder_static_tables = "C:/Users/Faraz Zaidi/Desktop/Python project draft worspace/Input file generation/static_tables"

    # Load required data tables

    component_attributes = pd.read_csv(os.path.join(os.path.dirname(__file__), '..', '..', 'static_tables', 'component_attributes.csv'))
    damage_state_attribute_mapping  = pd.read_csv(os.path.join(os.path.dirname(__file__), '..', '..', 'static_tables', 'damage_state_attribute_mapping.csv'))
    subsystems = pd.read_csv(os.path.join(os.path.dirname(__file__), '..', '..', 'static_tables', 'subsystems.csv'))
    tenant_function_requirements = pd.read_csv(os.path.join(os.path.dirname(__file__), '..', '..', 'static_tables', 'tenant_function_requirements.csv'))

    '''% Pull default tenant unit attributes for each tenant unit listed in the tenant_unit_list'''
    tenant_units_read = pd.read_csv('tenant_unit_list.csv')
    tenant_units={}
    for key in list(tenant_units_read.keys()):
        tenant_units[key] = tenant_units_read[key].tolist()

    # Empty dictionary for reading data corresponding to occupancy ID against each tenant
    for key in ['exterior', 'interior', 'occ_per_elev', 'is_elevator_required', 
                'is_electrical_required', 'is_water_required', 'is_hvac_required']:
        tenant_units[key] = []

    for tu in range(len(tenant_unit_list)):
        # List of binaries, 1 if occupany id matches between tenant_unit_list and tenant_function_requirements dataframes, 0 if it does not.
        fnc_requirements_filt = [] 
        
        for func_tu in range(len(tenant_function_requirements)):
            if tenant_function_requirements["occupancy_id"][func_tu] == tenant_unit_list["occupancy_id"][tu]:
                fnc_requirements_filt.append(1)
                
                # If occupant ID matches read and appen the value from respective columns of tenant_function_requirements dataframe
                tenant_units['exterior'].append(tenant_function_requirements["exterior"][func_tu])
                tenant_units['interior'].append(tenant_function_requirements["interior"][func_tu])
                tenant_units['occ_per_elev'].append(tenant_function_requirements["occ_per_elev"][func_tu])           
                
                # If elevator is required to begin with and tenant storey is higher than the maximum walkable storey, the elevator is marked as required for functinality purposes
                if (tenant_function_requirements["is_elevator_required"][func_tu] == 1 and tenant_function_requirements["max_walkable_story"][func_tu] < tenant_unit_list["story"][tu]):
                    tenant_units['is_elevator_required'].append(1)
                else:
                    tenant_units['is_elevator_required'].append(0)                
            
                tenant_units['is_electrical_required'].append(tenant_function_requirements["is_electrical_required"][func_tu])
                tenant_units['is_water_required'].append(tenant_function_requirements["is_water_required"][func_tu])
                tenant_units['is_hvac_required'].append(tenant_function_requirements["is_hvac_required"][func_tu])
            
            
            else:
                fnc_requirements_filt.append(0)
        if sum(fnc_requirements_filt) !=1:
            sys.exit('error!. Tenant Unit Requirements for This Occupancy Not Found')
            
                
    '''Pull default component and damage state attributes for each component in the comp_ds_list'''

    comp_idx=1

    # Empty dictionary to pull out attributes corresponding to each component
    comp_ds_info = {
                    'comp_id':[],
                    'comp_type_id' :[],
                    'comp_idx' :[],
                    'ds_seq_id' : [],
                    'ds_sub_id' :[],
                    'system' :[],
                    'subsystem_id' :[],
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
                    'affects_access' : [],
                    'damages_envelope_seal' : [],
                    'obstructs_interior_space' : [],
                    'impairs_system_operation' : [],
                    'fraction_area_affected' : [],
                    'area_affected_unit' : [],
                    'crew_size' : [],
                    'tmp_fix':[],
                    'tmp_fix_time' : [],
                    'requires_shoring' : [],
                    'permit_type' : [],
                    'redesign' : [],
                    'n1_redundancy' : [],
                    'parallel_operation' :[]
                    }

    for comp in range(len(comp_ds_list)):
        comp_ds_info["comp_id"].append(comp_ds_list["comp_id"][comp])
        comp_ds_info["comp_type_id"].append(comp_ds_list["comp_id"][comp][0:5])
        
        # defining component ID serial number. In the comp_ds_list, same component is listed more than once corresponding to each of its damage state
        if comp>0 and comp_ds_info["comp_id"][comp] != comp_ds_info["comp_id"][comp-1]:
            comp_idx += 1
        
        comp_ds_info["comp_idx"].append(comp_idx)
        
        comp_ds_info["ds_seq_id"].append(comp_ds_list["ds_seq_id"][comp])
        comp_ds_info["ds_sub_id"].append(comp_ds_list["ds_sub_id"][comp])
        
        
        # Search if the component exists in the list of fragilities 
        
        # Filter is defined. Values is 1 if condition meets and 0 otherwise
        comp_attribute_filt = []  
        for frag in range(len(component_attributes['fragility_id'])):

            if component_attributes['fragility_id'][frag] == comp_ds_info["comp_id"][comp]:
                comp_attribute_filt.append(1)

                # If occupant ID matches read and appen the value from respective columns of tenant_function_requirements dataframe
                comp_ds_info["system"].append(component_attributes['system_id'][frag])
                comp_ds_info["subsystem_id"].append(component_attributes['subsystem_id'][frag])
                comp_ds_info["unit"].append(component_attributes['unit'][frag])
                comp_ds_info["unit_qty"].append(component_attributes['unit_qty'][frag])
                comp_ds_info["service_location"].append(component_attributes['service_location'][frag])
                
            else:
                comp_attribute_filt.append(0)
        if sum(comp_attribute_filt) != 1:
            sys.exit('error!. Could not find component attrubutes')
            
        # Find idx of this damage state in the damage state attribute tables 
        
        # Filters are defined. Values is 1 if condition meets and 0 otherwise
        ds_comp_filt = []
        ds_seq_filt = []
        ds_sub_filt = []
        ds_attr_filt = []
        
        for frag_reg in range(len(damage_state_attribute_mapping["fragility_id_regex"])):
            
            # Mapping components with attributes - Cjecks are based on mapping, comp_id, seq_id and sub_id
            
            # Matching element ID using information contained in damage_state_attribute_mapping ["fragility_id_regex"]
            if re.search(damage_state_attribute_mapping["fragility_id_regex"][frag_reg], comp_ds_info["comp_id"][comp]) == None:
                ds_comp_filt.append(0)
            elif (re.search(damage_state_attribute_mapping["fragility_id_regex"][frag_reg], comp_ds_info["comp_id"][comp])).string == comp_ds_info["comp_id"][comp]:
                ds_comp_filt.append(1)
            else:
                ds_comp_filt.append(0)
                
            if damage_state_attribute_mapping["ds_index"][frag_reg] == comp_ds_info["ds_seq_id"][comp]:
                ds_seq_filt.append(1)
            else:
                ds_seq_filt.append(0)
            
            if comp_ds_info["ds_sub_id"][comp] == 1:
                if damage_state_attribute_mapping["sub_ds_index"][frag_reg] == 1 or pd.isna(damage_state_attribute_mapping["sub_ds_index"][frag_reg]) == True:
                    ds_sub_filt.append(1)
                elif damage_state_attribute_mapping["sub_ds_index"][frag_reg] == comp_ds_info["ds_sub_id"][comp]:
                    ds_sub_filt.append(1)  
                else:
                    ds_sub_filt.append(0) 
            
            elif damage_state_attribute_mapping["sub_ds_index"][frag_reg] == comp_ds_info["ds_sub_id"][comp]:
                ds_sub_filt.append(1)
            else:
                ds_sub_filt.append(0)

            # Checking if all comp_ID, seq_ID and sub_ID matches
            if ds_comp_filt[frag_reg] == 1 and ds_seq_filt[frag_reg] == 1 and ds_sub_filt[frag_reg] == 1:
                ds_attr_filt.append(1)
            else:
                ds_attr_filt.append(0)

        if sum(ds_attr_filt) != 1:
            sys.exit('error!. Could not find damage state attrubutes')
            

        for frag_reg in range(len(damage_state_attribute_mapping["fragility_id_regex"])):

            # Set Damage State attributes
        
            if ds_attr_filt[frag_reg] == 1:
                comp_ds_info["is_sim_ds"].append(damage_state_attribute_mapping["is_sim_ds"][frag_reg])
                comp_ds_info["safety_class"].append(damage_state_attribute_mapping["safety_class"][frag_reg])
                comp_ds_info["affects_envelope_safety"].append(damage_state_attribute_mapping["affects_envelope_safety"][frag_reg])
                comp_ds_info["ext_falling_hazard"].append(damage_state_attribute_mapping["exterior_falling_hazard"][frag_reg])
                comp_ds_info["int_falling_hazard"].append(damage_state_attribute_mapping["interior_falling_hazard"][frag_reg])
                comp_ds_info["global_hazardous_material"].append(damage_state_attribute_mapping["global_hazardous_material"][frag_reg])
                comp_ds_info["local_hazardous_material"].append(damage_state_attribute_mapping["local_hazardous_material"][frag_reg])
                comp_ds_info["affects_access"].append(damage_state_attribute_mapping["affects_access"][frag_reg])
                comp_ds_info["damages_envelope_seal"].append(damage_state_attribute_mapping["damages_envelope_seal"][frag_reg])
                comp_ds_info["obstructs_interior_space"].append(damage_state_attribute_mapping["obstructs_interior_space"][frag_reg])
                comp_ds_info["impairs_system_operation"].append(damage_state_attribute_mapping["impairs_system_operation"][frag_reg])
                comp_ds_info["fraction_area_affected"].append(damage_state_attribute_mapping["fraction_area_affected"][frag_reg])
                comp_ds_info["area_affected_unit"].append(damage_state_attribute_mapping["area_affected_unit"][frag_reg])
                comp_ds_info["crew_size"].append(damage_state_attribute_mapping["crew_size"][frag_reg])
                comp_ds_info["tmp_fix"].append(damage_state_attribute_mapping["has_tmp_fix"][frag_reg])
                comp_ds_info["tmp_fix_time"].append(damage_state_attribute_mapping["tmp_fix_time"][frag_reg])
                comp_ds_info["requires_shoring"].append(damage_state_attribute_mapping["requires_shoring"][frag_reg])
                comp_ds_info["permit_type"].append(damage_state_attribute_mapping["permit_type"][frag_reg])
                comp_ds_info["redesign"].append(damage_state_attribute_mapping["redesign"][frag_reg])            
            
        # Find idx of this damage state in the subsystem attribute tables 
        if comp_ds_info["subsystem_id"][comp] == 0: # No subsyestem
            comp_ds_info["n1_redundancy"].append(0)
            comp_ds_info["parallel_operation"].append(0)
        
        # Filter is defined. Values is 1 if condition meets and 0 otherwise    
        subsystem_filt = []
        
        for sub_id in range(len(subsystems["id"])):
            if subsystems["id"][sub_id] == comp_ds_info["subsystem_id"][comp]:
                subsystem_filt.append(1)
            else:
                subsystem_filt.append(0)
                 
            if subsystem_filt[sub_id] == 1:
                comp_ds_info["n1_redundancy"].append(subsystems["n1_redundancy"][sub_id])
                comp_ds_info["parallel_operation"].append(subsystems["parallel_operation"][sub_id])
        
        # Comment FZ - The next two lines are in addition to the actual code
        if sum(subsystem_filt) != 1 and comp_ds_info["subsystem_id"][comp] == 0:
            print ('Component ID ' + comp_ds_info["comp_id"][comp] + ' does not belong to a subsystem')        
            
        elif sum(subsystem_filt) != 1:
            sys.exit('error!. Could not find damage state attrubutes') 
        
        damage['comp_ds_table'] = comp_ds_info


    # converting to Python int and floats for creating .json file
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
                
    # Export output as simulated_inputs.json file
    simulated_inputs = {'building_model' : building_model, 'damage' : damage, 'damage_consequences' : damage_consequences, 'functionality' : functionality, 'functionality_options' : functionality_options, 'impedance_options' : impedance_options, 'regional_impact' : regional_impact, 'repair_time_options' : repair_time_options, 'tenant_units' : tenant_units}

    for inp in simulated_inputs:
        output_json_object = json.dumps(simulated_inputs)

    with open(output_path, "w") as outfile:
        outfile.write(output_json_object)       

if __name__ == '__main__':

    output_path = "simulated_inputs.json"

    build_input(output_path) 