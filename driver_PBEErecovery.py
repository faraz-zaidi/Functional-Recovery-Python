def run_analysis(model_name):
    """
    Main file for running the code

    Parameters
    ----------
    model_name: string
        Name of the model. Inputs are expected to be in a directory with this 
        name. Outputs will save to a directory with this name


    """

    import time
    start_time = time.time() # For runtime calculation

    ''' ######################  Caution ########################'''
    # Ignoring runtime warnings
    import warnings
    warnings.filterwarnings('ignore')
    ''' ########################################################'''


    ## 1. Import Python modules to be used
    import os
    import json
    import numpy as np
    import math
    import pandas as pd
    from scipy.stats import truncnorm


    ## 2. Define User Inputs

    #model_name = 'haseltonRCMF_4story' # 
    model_dir = 'inputs/'+model_name # Directory where the simulated inputs are located
    outputs_dir = 'outputs/'+model_name # Directory where the assessment outputs are saved


    ## 3.Import Packages
    from impedance import main_impedance_function
    from repair_schedule import main_repair_schedule
    from functionality import main_functionality_function
    from fn_preprocessing import fn_preprocessing

    ## 4. Load simulated inputs file
    f = open(os.path.join(os.path.dirname(__file__),model_dir, 'simulated_inputs.json'))

    simulated_inputs = json.load(f)

    # Convert each of the input groups into standalone dictionaries
    # sim_inp = list(simulated_inputs.keys())
    # for i in sim_inp:
    #     a = i
    #     locals()[a] = simulated_inputs[i]
    # The above was not good practice (and failed for me), so I replaced it with specific assignments
    building_model = simulated_inputs.get('building_model')
    damage = simulated_inputs.get('damage')
    damage_consequences = simulated_inputs.get('damage_consequences')
    functionality = simulated_inputs.get('functionality')
    functionality_options = simulated_inputs.get('functionality_options')
    impedance_options = simulated_inputs.get('impedance_options')
    regional_impact = simulated_inputs.get('regional_impact')
    repair_time_options = simulated_inputs.get('repair_time_options')
    tenant_units = simulated_inputs.get('tenant_units')

    end_time_load = time.time()   # For runtime calculation 

    ## 5. Load required static data
    systems = pd.read_csv(os.path.join(os.path.dirname(__file__), 'static_tables', 'systems.csv'))
    subsystems = pd.read_csv(os.path.join(os.path.dirname(__file__), 'static_tables', 'subsystems.csv'))
    impeding_factor_medians = pd.read_csv(os.path.join(os.path.dirname(__file__), 'static_tables', 'impeding_factors.csv'))


    ## 6. Combine compoment attributes into recovery filters to expidite recovery assessment
    damage['fnc_filters'] = fn_preprocessing(damage['comp_ds_table'])

    ## 7. Simulate ATC 138 Impeding Factors
    functionality['impeding_factors'] = main_impedance_function.main_impeding_factors(damage, impedance_options, 
                           np.array(damage_consequences['repair_cost_ratio']), 
                           np.array(damage_consequences['inpsection_trigger']), 
                           systems, building_model['building_value'], 
                           impeding_factor_medians, 
                           regional_impact['surge_factor'])

    ## 8. Construct the Building Repair Schedule  
    damage, functionality['worker_data'], functionality['building_repair_schedule'] = main_repair_schedule.main_repair_schedule(damage, building_model, np.array(damage_consequences['red_tag']), repair_time_options, systems, functionality['impeding_factors'], regional_impact['surge_factor'])


    # 9. Calculate the Recovery of Building Reoccupancy and Function 
    functionality['recovery'] = main_functionality_function.main_functionality(damage, building_model, 
                                                    damage_consequences, 
                                                    functionality['utilities'], 
                                                    functionality_options, 
                                                    tenant_units, subsystems)


    # 10. Save Outputs
    if os.path.exists(os.path.join(os.path.dirname(__file__),'outputs')) == False:
        os.mkdir(os.path.join(os.path.dirname(__file__),'outputs'))
    if os.path.exists(os.path.join(os.path.dirname(__file__),'outputs', model_name)) == False:
        os.mkdir(os.path.join(os.path.dirname(__file__),'outputs', model_name))

        
    fnc_keys_1 = list(functionality.keys())
    for k_1 in fnc_keys_1:
        if type(functionality[k_1]) == np.ndarray: 
            functionality[k_1] = functionality[k_1].tolist() 
        if type(functionality[k_1]) == dict:
            fnc_keys_2 = list(functionality[k_1].keys())    
       
            for k_2 in fnc_keys_2:
                if type(functionality[k_1][k_2]) == np.ndarray: 
                    functionality[k_1][k_2] = functionality[k_1][k_2].tolist()
                if type(functionality[k_1][k_2]) == dict:
                    fnc_keys_3 = list(functionality[k_1][k_2].keys())    
       
                    for k_3 in fnc_keys_3:
                        if type(functionality[k_1][k_2][k_3]) == np.ndarray: 
                            functionality[k_1][k_2][k_3] = functionality[k_1][k_2][k_3].tolist()
                        if type(functionality[k_1][k_2][k_3]) == dict:
                            fnc_keys_4 = list(functionality[k_1][k_2][k_3].keys())
     
                            for k_4 in fnc_keys_4:
                                if type(functionality[k_1][k_2][k_3][k_4]) == np.ndarray: 
                                    functionality[k_1][k_2][k_3][k_4] = functionality[k_1][k_2][k_3][k_4].tolist()
                                if type(functionality[k_1][k_2][k_3][k_4]) == dict:
                                    fnc_keys_5 = list(functionality[k_1][k_2][k_3][k_4].keys())
        
                                    for k_5 in fnc_keys_5:
                                        if type(functionality[k_1][k_2][k_3][k_4][k_5]) == np.ndarray: 
                                            functionality[k_1][k_2][k_3][k_4][k_5] = functionality[k_1][k_2][k_3][k_4][k_5].tolist()
                                        if type(functionality[k_1][k_2][k_3][k_4][k_5]) == dict:
                                            fnc_keys_6 = list(functionality[k_1][k_2][k_3][k_4][k_5].keys())

    output_json_object = json.dumps(functionality)

    with open(os.path.join(os.path.dirname(__file__),outputs_dir, "recovery_outputs.json"), "w") as outfile:
        outfile.write(output_json_object)

    end_time = time.time()

    print('time to run '+str(round(end_time - start_time,2))+'s')


if __name__ == '__main__':

    model_name = 'haseltonRCMF_4story'

    run_analysis(model_name)

