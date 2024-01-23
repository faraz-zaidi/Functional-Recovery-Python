# -*- coding: utf-8 -*-
"""
Code for generating optional_inputs.json file

"""

import json
optional_inputs = {
# impedance Options
"impedance_options" : {
    
    
"include_impedance":       {
                            "inspection" : True,
                            "financing" : True,
                            "permitting" : True,
                            "engineering" : True,
                            "contractor" : True,
                            "long_lead" : False
                            },
"system_design_time" :      {
                            "f" : 0.04,
                            "r" : 200,
                            "t" : 1.3,
                            "w" : 8
                            },
"eng_design_min_days" : 14,
"eng_design_max_days" : 365,
"mitigation"  :             {
                            "is_essential_facility" : False,
                            "is_borp_equivalent" : False,
                            "is_engineer_on_retainer" : False,
                            "contractor_relationship" : 'none',
                            "contractor_retainer_time" : 3,
                            "funding_source" : 'private',
                            "capital_available_ratio" : 0.02
                            },
"impedance_beta" : 0.6,
"impedance_truncation" : 2,
"default_lead_time" : 182,
"demand_surge":              {
                            "include_surge" : 1,
                            "is_dense_urban_area" : 1,
                            "site_pga" : 1,
                            "pga_de": 1
                            },

"scaffolding_lead_time" : 5,
"scaffolding_erect_time" : 2,
"door_racking_repair_day" : 3,
"flooding_cleanup_day" : 5,
"flooding_repair_day" : 90
                            },
                      

# Repir Schedule Options
"repair_time_options" : {
    
 "max_workers_per_sqft_story"  : 0.001,
 "max_workers_per_sqft_story_temp_repair"  : 0.005,
 "max_workers_per_sqft_building" : 0.00025,
 "max_workers_building_min" :  20,
 "max_workers_building_max" :  260,
 "allow_tmp_repairs" : 1,
 "allow_shoring" : 1
                         },

# Functionality Assessment Options
"functionality_options" : {  
    
"calculate_red_tag" : 1,
"red_tag_clear_time" : 7,
"red_tag_clear_beta" : 0.6,
"include_local_stability_impact" : 1,
"include_flooding_impact": 1,
"egress_threshold" : 0.5,
"fire_watch" : False,
"local_fire_damamge_threshold" : 0.25,
"min_egress_paths" : 2,
"exterior_safety_threshold" : 0.1,
"interior_safety_threshold" : 0.25,
"door_access_width_ft" : 9,
"habitability_requirements": {"electrical" : 0,
                             "water_potable" : 0,
                             "water_sanitary" : 0,
                             "hvac_ventilation" : 0,
                             "hvac_heating" : 0,
                             "hvac_cooling" : 0,
                             "hvac_exhaust" : 0                       
                             },
"water_pressure_max_story" : 4,
"heat_utility" : 'gas',
                        }

                }


with open("optional_inputs.json", "w") as outfile:
    json.dump(optional_inputs, outfile)
   
