
"""
Other repair schedule functions called by the main repair schedule function
"""
import numpy as np

def fn_allocate_workers_stories(total_worker_days, required_workers_per_story, 
                                average_crew_size, max_crews_building, 
                                max_workers_per_building):

    '''For a given building system, allocate crews to each story to
    determine the system level repair time on each story; not considering
    impeding factors or construction constraints with other systems.
      
      
    Parameters
    ----------
    total_worker_days: [num reals x num stories]
      The total worker days needed to repair damage each story for this
      sequence
      
    required_workers_per_story: array [num reals x num stories]
      Number of workers required to repair damage in each story
      
    average_crew_size: array [num reals x num stories]
      Average crew size required to repair damage in each story
      
    max_crews_building: logical array [num reals x 1]
      maximum number of crews allowed in the building for this system
      
    max_workers_per_building: int
      maximum number of workers allowed in the buildings at a given time
      
    Returns
    -------
    repair_start_day: matrix [num reals x num stories]
      The number of days from the start of repair of this system until the repair of this system 
      starts on each story
      
    repair_complete_day: matrix [num reals x num stories]
      The number of days from the start of repair of this system until each story is
      repaired for damage in this system
      
    max_workers_per_story: matrix [num reals x num stories]
      number of workers required for the repair of this story and system as
      
    Notes
    -----'''
    import sys
    
    ## Initial Setup
    num_reals, num_stories = np.shape(total_worker_days)
    repair_complete_day = np.zeros([num_reals,num_stories])
    repair_start_day = np.empty([num_reals,num_stories])
    repair_start_day[:] = np.nan
    max_workers_per_story = np.zeros([num_reals,num_stories])
    
    ## Allocate workers to each story
    # Loop through iterations of time reduce damage on each story based on assigned workers
    iter = 0;
    while sum(sum(total_worker_days)) > 0.01:
        iter = iter + 1; 
        if iter > 1000: # keep the while loop pandemic contained
            # error('PBEE_Recovery:RepairSchedule', 'Could not converge worker allocations for among stories in sequence');
            sys.exit('Error! could not converge worker allocations for among stories in sequence')
    
        # Determine the available workers in the building
        available_workers_in_building = max_workers_per_building * np.ones([num_reals])
        assigned_workers_per_story = np.zeros([num_reals,num_stories])
        assigned_crews_per_story = np.zeros([num_reals,num_stories]) 
    
        # Define where needs repair
        needs_repair = total_worker_days > 0
    
        # Defined Required Workers
        required_workers_per_story = needs_repair * required_workers_per_story
        
        '''Assign Workers to each story -- assumes that we wont drop the number
        of crews in order to meet worker per sqft limitations, and instead
        wait until more workers are made available'''
        
        for s in range(num_stories):
            # Are there enough workers to assign a crew
            sufficient_workers = required_workers_per_story[:,s] <= available_workers_in_building
            
            # Assign Workers to this story
            assigned_workers_per_story[sufficient_workers,s] = required_workers_per_story[sufficient_workers,s]
            assigned_crews_per_story[:,s] = assigned_workers_per_story[:,s] / average_crew_size[:,s]
            assigned_crews_per_story[np.isnan(assigned_crews_per_story)] = 0
            num_crews_in_building = np.sum(assigned_crews_per_story, axis=1)
            exceeded_max_crews = num_crews_in_building > max_crews_building
            assigned_workers_per_story[exceeded_max_crews,s] = 0 # don't assign workers if we have exceeded the number of crews allowed in the building
            
            # Define Available Workers
            available_workers_in_building = available_workers_in_building - assigned_workers_per_story[:,s]  
        
        
        # Define the start of repairs for each story
        start_repair_filt = np.isnan(repair_start_day) & (assigned_workers_per_story > 0)
        
        max_day_completed_so_far = np.transpose(np.multiply(np.amax(repair_complete_day, axis=1), np.ones([num_stories,num_reals]))) #FZ# transpose done fto align the arrays for operation
        
        
        
        
        repair_start_day[start_repair_filt] =  max_day_completed_so_far[start_repair_filt]
        
        
        
        
        
        # Calculate the time associated with this increment of the while loop
        in_progress = assigned_workers_per_story > 0 # stories where work is being done
        total_repair_days = np.empty(np.shape(in_progress)) 
        total_repair_days[:] = np.inf # pre-allocate with inf's becuase we take a min later
        total_repair_days[in_progress] = total_worker_days[in_progress] / assigned_workers_per_story[in_progress]
        delta_days = np.amin(total_repair_days,axis=1) # time increment is whatever in-progress story that finishes first 
        delta_days[np.isinf(delta_days)] = 0 # Replace infs from real that has no repair with zero       
        delta_worker_days = np.transpose(np.multiply(np.transpose(assigned_workers_per_story), delta_days)) # time increment is whatever in-progress story that finishes first #FZ# transpose done fto align the arrays for operation
        total_worker_days[in_progress] = np.maximum(total_worker_days[in_progress] - delta_worker_days[in_progress], 0)
        indx_neg_remaining = total_worker_days < 0.001 # find instances of remaining time that are excessively small and don't represent realistic amount of work
        total_worker_days[indx_neg_remaining] = 0  # zero remaining work that is negligible as defined above
        
        # Define Start and Stop of Repair for each story in each sequence
        repair_complete_day = repair_complete_day + np.transpose(np.multiply(delta_days, np.transpose(1*needs_repair))) #FZ# transpose done fto align the arrays for operation
         
        # Max Crew Size for use in later function
        max_workers_per_story = np.maximum(max_workers_per_story , assigned_workers_per_story)
    
    return repair_start_day, repair_complete_day, max_workers_per_story
    




def fn_calc_system_repair_time(damage, systems, max_workers_per_building, max_workers_per_story):
    ''' From Dustin's work
    Determine the repair time for each system if repaired in isolation 
      
       Parameters
       ----------
       damage: dictionary
         contains per damage state damage and loss data for each component in the building
         
       systems: DataFrame
         data table containing information about each system's attributes
         
       max_workers_per_building: int
         maximum number of workers allowed in the building at once
         
       max_workers_per_story: array [1 x num_stories]
         maximum number of workers allowed in each story at once
      
       Returns
       -------
       schedule['per_system'][sys]['repair_start_day'] [num reals x num stories]
         The number of days from the start of repair of a specifc system until
         the start of repair of each story for that given system (i.e. the day 
         of the start of repairs relative the to start of this system ... e.g.
         story 1 should always be zero)
         
       schedule['per_system'][sys]['repair_complete_day'] [num reals x num stories]
         The number of days from the start of repair of a specifc system until
         each story is fully repaired for that given system.
         
       schedule['per_system'][sys]['max_num_workers_per_story'] [num reals x num stories]
         The number of workers required to repair each story of this system
         
       schedule['system_totals']['repair_days'] [num reals x num systems]
         The number of days required to repair each system in isolation
         
       schedule['system_totals']['num_workers'] [num reals x num systems]
         The number of workers required for the repair of each system
      
       Notes
       -----'''
    
    ## Initial Setup
    # Import Packages
    from repair_schedule import other_repair_schedule_functions
    
    def fn_repair_sequence_parameters(damage, sys, num_du_per_crew, 
                                      max_crews_per_comp_type, 
                                      max_workers_per_story, 
                                      max_workers_per_building):
        
        '''Define crew sizes, workers, and repair times for each story of a given
        system. Based on worker limiations, and component worker days data from
        the FEMA P-58 assessment.'''
        
        # Define Initial Parameters
        num_stories = len(damage['tenant_units']) 
        num_reals, num_comps = np.size(damage['tenant_units'][0]['worker_days'],0), np.size(damage['tenant_units'][0]['worker_days'],1)
        sequence_filt = np.array(damage['comp_ds_table']['system']) == sys # identifies which ds indices are in this seqeunce.
        comp_types = np.unique(np.array(damage['comp_ds_table']['comp_idx'])[sequence_filt]) # Types of components in this system
        
        # Pre-allocatate variables
        total_worker_days = np.zeros([num_reals,num_stories])
        is_damaged_building = np.zeros([num_reals,num_comps], dtype=bool)
        num_damaged_comp_types = np.zeros([num_reals,num_stories])
        num_damaged_units = np.zeros([num_reals,num_stories])
        average_crew_size = np.zeros([num_reals,num_stories])
        
        for s in range(num_stories):
            # Define damage properties of this system at this story
            num_damaged_units[:,s] = np.sum((1*sequence_filt) * damage['tenant_units'][s]['qnt_damaged'], axis=1) #FZ# Total number of damaged components of one system in one storey
            is_damaged = np.array(damage['tenant_units'][s]['qnt_damaged']) > 0 #FZ# checking for which components in which realizations are damaged
            is_damaged_building = is_damaged_building | is_damaged              #FZ# compiling for all stories. if there is damage at any story, building is damaged
            
            for c in range(len(comp_types)):
                num_damaged_comp_types[:,s] = num_damaged_comp_types[:,s] + np.any((1* np.array(damage['comp_ds_table']['comp_idx']) == comp_types[c]) * (1*is_damaged), axis=1) #FZ# number of types of components damaged in a storey in each realization
            
        
            # Caluculate total worker days per story per sequences
            total_worker_days[:,s] = np.sum(np.array(damage['tenant_units'][s]['worker_days'])[:,sequence_filt], axis=1) # perhaps consider doing when we first set up this damage data structure
            
            # Determine the required crew size needed for these repairs
            repair_time_per_comp = np.array(damage['tenant_units'][s]['worker_days']) / np.array(damage['comp_ds_table']['crew_size'])
            average_crew_size[:,s] = total_worker_days[:,s] / np.sum(repair_time_per_comp[:,sequence_filt], axis=1)
        
            
        # Define the number of crews needed based on the extent of damage
        num_crews = np.ceil(num_damaged_units / num_du_per_crew)
        num_crews = np.minimum(num_crews, max_crews_per_comp_type * num_damaged_comp_types)
        num_crews = np.minimum(num_crews, np.ceil(num_damaged_units)) # Safety check: num crews should never be greater than the number of damaged components
        
        # Round up total worker days to the nearest day to speed up the worker 
        # allocation loop and implicitly consider change of trade delays
        total_worker_days = np.ceil(total_worker_days)
        
        # Round crew sizes such that we have a realistic size (still implicitly
        # averaged based on type of damage)
        average_crew_size[np.isnan(average_crew_size)] = 0
        average_crew_size = np.round(average_crew_size)
        
        # Limit the number of crews based on the space limitations at this story
        # and the assumed crew size
        worker_upper_lim = np.minimum(max_workers_per_story , max_workers_per_building)
        max_num_crews_per_story = np.fmax(np.floor(worker_upper_lim / average_crew_size), 1)
        num_crews = np.minimum(num_crews, max_num_crews_per_story) 
        
        # Calculate the total number of workers per story for this system
        num_workers = average_crew_size* num_crews
        
        # Repeat calc of number of uniquely damaged component types for the whole building
        num_damaged_comp_types = np.zeros([num_reals])
        
        for c in range(len(comp_types)):
            num_damaged_comp_types = num_damaged_comp_types + np.any( (1* np.array(damage['comp_ds_table']['comp_idx']) == comp_types[c]) * (1*is_damaged_building), axis=1)                                                
                                                                   
        max_crews_building = max_crews_per_comp_type * num_damaged_comp_types
            
        return total_worker_days, num_workers, average_crew_size, max_crews_building
    
    # General Varaible
    num_reals = len(damage['tenant_units'][0]['worker_days']);
    schedule = {'system_totals' : {'repair_days' : np.zeros([num_reals,len(systems)])}}
    schedule['system_totals']['num_workers'] = np.zeros([num_reals,len(systems)])
    
    ## Allocate workers to each story for each system
    # Repair finish times assumes all sequences start on day zero
    schedule['per_system']={}    
    for sys in range(len(systems)):
        schedule['per_system'][sys]={}
        # Define the Crew workers and total workers days for this sequence
        # in arrays of [num reals by num stories]
        total_worker_days, num_workers, average_crew_size, max_crews_building = fn_repair_sequence_parameters(damage,
            systems['id'][sys], 
            systems['num_du_per_crew'][sys],
            systems['max_crews_per_comp_type'][sys],
            max_workers_per_story,
            max_workers_per_building
        )
        # Allocate workers to each story and determine the total days until
        # repair is complete for each story and sequence

        
        AA,BB,CC = other_repair_schedule_functions.fn_allocate_workers_stories(total_worker_days, num_workers, 
                                      average_crew_size, max_crews_building, 
                                      max_workers_per_building)

        schedule['per_system'][sys]['repair_start_day']=AA
        schedule['per_system'][sys]['repair_complete_day']=BB
        schedule['per_system'][sys]['max_num_workers_per_story']=CC
    
        # How many days does it take to complete each system in isloation
        schedule['system_totals']['repair_days'][:,sys] = np.amax(schedule['per_system'][sys]['repair_complete_day'], axis=1)
        schedule['system_totals']['num_workers'][:,sys] = np.amax(schedule['per_system'][sys]['max_num_workers_per_story'], axis=1)
 
        
    return schedule


def fn_simulate_tmp_repair_times( damage, inpsection_complete_day, beta_temp, surge_factor ):
    '''Simulate temporary repair times for each componet (where applicable) per
    realization
    
    Parameters
    ----------
    damage: dictionary
     contains per damage state damage and loss data for each component in the building
    
    inpsection_complete_day: array [num_reals x 1]
     simulated day after the earthquake that inpection in completed 
    
    beta_temp: number
     lognormal standard deviation defining the uncertianty in all temporary
     repair times
    
    surge_factor: number
     amplification factor for temporary repair time based on a post disaster surge
     in demand for skilled trades and construction supplies
    
    
    Returns
    -------
    tmp_repair_complete_day: array [num_reals x num_comp]
     contains the day (after the earthquake) the temporary repair time is 
     resolved per damage state damage and realization. Inf represents that
     there is not temporary repair time available for a given components
     damage.
    
    Notes
    -----
     Currently simulate tmp repair times independently between components but correlated between stories'''
    
    from scipy.stats import truncnorm
    # Initialize Parameters
    num_tenant_units = len(damage['tenant_units'])
    num_reals, num_comps = np.shape(damage['tenant_units'][0]['qnt_damaged'])   
    #  Create basic trucated standard normal distribution for later simulation
    th_low = -2 # Truncate below -2 standard deviations
    th_high = 2 # Truncate above +2 standard deviations
    mu = 0
    sigma = 1
    trunc_pd = truncnorm((th_low - mu)/sigma, (th_high - mu)/sigma, loc=mu, scale=sigma)   
    
    # Determine which damage states require shoring
    shoring_filt = np.array(damage['comp_ds_table']['requires_shoring'])
    
    tmp_repair_filt = np.array(damage['comp_ds_table']['tmp_fix']) & np.logical_not(np.array(damage['comp_ds_table']['requires_shoring']))
    
    ## Go through damage and determine which relization have shoring repairs
    is_shoring_damage = np.zeros(num_reals, dtype=bool)
    for tu in range(num_tenant_units):
        is_shoring_damage = is_shoring_damage | np.array(np.amax(np.array(damage['tenant_units'][tu]['qnt_damaged'])*shoring_filt, axis = 1), dtype=bool)

    ## Simulate temporary repair times
    # simulate shoring time (assumes correlated throughout whole building)
    shoring_time_med = max(surge_factor * np.array(damage['comp_ds_table']['tmp_fix_time'])* shoring_filt) # median shoring time for the building is the max among all components
    prob_sim = np.random.rand(num_reals) # assumes components are correlated
    x_vals_std_n = trunc_pd.ppf(prob_sim) # Truncated lognormal distribution (via standard normal simulation)
    sim_shoring_time = np.ceil(np.exp(x_vals_std_n * beta_temp + np.log(shoring_time_med))) # assume it takes whole days to temporarily fix things
    
    # Find the time to perform all shoring in the building
    building_shoring_time = sim_shoring_time * is_shoring_damage
    
    # Simulate temp repair and clean up time
    # assumes tmp repair times are independent between components but correlated between stories
    tmp_repair_time = np.array(surge_factor * np.array(damage['comp_ds_table']['tmp_fix_time']) * tmp_repair_filt, dtype=float)
    tmp_repair_time[tmp_repair_time == 0] = np.inf # convert zero day times to inf to not affect building repair time logic
    prob_sim = np.random.rand(num_reals, num_comps) # This assumes components are indepednant
    x_vals_std_n = trunc_pd.ppf(prob_sim) # Truncated lognormal distribution (via standard normal simulation)
    sim_tmp_repair_time = np.ceil(np.exp(x_vals_std_n * beta_temp + np.log(tmp_repair_time))) # assume it takes whole days to temporarily fix things
    
    # Combine to find total temp repair complete data for each component damage
    # state (all stories and tenant units)
    # clean up occurs after all shoring is complete which occurs after
    # inspection is complete
    tmp_repair_complete_day = np.transpose(inpsection_complete_day + building_shoring_time + np.transpose(sim_tmp_repair_time))  # temp repairs dont start until after inspection
    
    return tmp_repair_complete_day

def fn_prioritize_systems( systems, damage, tmp_repair_complete_day):
    '''Determine the priority of worker allocation for each system and realization
    based on default table priorities, whether they have the potential to 
    affect function and whether they are resolved by temporary repairs.
       
    Parameters
    ----------
    systems: DataFrame
      data table containing information about each system's attributes
      
    damage: dictionary
      contains per damage state damage and loss data for each component in the building
      
    tmp_repair_complete_day: array [num_reals x num_comp]
      contains the day (after the earthquake) the temporary repair time is 
      resolved per damage state damage and realization. Inf represents that
      there is not temporary repair time available for a given components
      damage.
       
    Returns
    -------
    sys_idx_priority_matrix: index array [num reals x num systems]
      row index to filter system matrices to be prioritized for each
      realiztion. Priority is left to right.
    
    Notes
    ------
    The checks done here are only able to implicitly check for which systems
    affect funtion the most (this prioritizes which have the potential to
    affect function). To explicitly check which systems have the biggest
    impact on function and prioritize those, this check would need to be
    coupled with the function assessment'''
    
    ## Initial Setup
    # initialize variables
    num_sys = len(systems)
    # [num_reals, ~] = size(damage.tenant_units{1}.qnt_damaged);
    num_reals = np.size(damage['tenant_units'][0]['qnt_damaged'],0)    
    # Find which components potentially affect function accross any tenant unit
    
    for s in range(len(damage['tenant_units'])):
        # affects_function = zeros(num_reals, len(damagecomp_ds_table));
        affects_function = np.zeros([num_reals, len(damage['comp_ds_table']['comp_id'])], dtype=bool)
        affects_function = np.logical_or(affects_function, np.logical_and(damage['fnc_filters']['affects_function'], np.array(damage['tenant_units'][s]['qnt_damaged']) > 0))

    
    # identify component damage that is resolved by temporary repairs
    tmp_repaired = tmp_repair_complete_day < np.inf # inf here means there is not temp repair
       
    ## Define ranks for each system 
    sys_affects_function = np.zeros([num_reals, num_sys]) # only prioritize the systems that potentially affect function
    sys_tmp_repaired = np.zeros([num_reals, num_sys]) # dont prioitize the systems that are completely resolved by temporary repairs
    
    for sys in range(num_sys):
        sys_filter = damage['comp_ds_table']['system'] == sys+1 #FZ# +1 done to account for python indexing starting from 0
        sys_affects_function[:,sys] = np.any(affects_function[:,sys_filter], axis = 1); # any damage that potentially affects function in this system
        sys_tmp_repaired[:,sys] = np.all(tmp_repaired[:,sys_filter], axis = 1) # all components must be resolved by temp repairs in this system

    prioritize_system = np.logical_and(sys_affects_function == 1, sys_tmp_repaired == 0)
    
    sys_priority_matrix = prioritize_system * (100 + np.array(systems['priority'])) + np.logical_not(prioritize_system) * (200 + np.array(systems['priority'])) # the added 200 is just to deprioritize non-function hindering damage

    
    # use rank matrix to get row indices of priorities
    sys_idx_priority_matrix = np.argsort(sys_priority_matrix, axis=1)
    
    return sys_idx_priority_matrix

def fn_set_repair_constraints(systems, conditionTag):
    '''Define a constraint matrix to be used by repair schedule
    
    Develops a matrix of various constriants between each system (i.e. what
    systems need to be repaired before others) for each realization
    
    Parameters
    ----------
    systems: DataFrame
     data table containing information about each system's attributes
    
    conditionTag: logical array (num_reals x 1)
     Is the building red tagged for each realization
    
    Returns
    -------
    sys_constraint_matrix: array [num reals x num_sys]
     array of system ids which define which systems (column index) are delayed by the
     system ids (array values)
    
    Notes
    -----
    Shortcoming: as implemented, each system can only be constrained by one
                  other system
    Example:
    [0 0 1 0 0 0 0 6 0]
    Interiors (column 3) are blocked by struture (value of 1 in the 3rd column)
    HVAC (column 8) is blocked by plumbing (value of 6 in the 8th column)'''
    
    #Initial Setup
    num_sys = len(systems)
    num_reals = len(conditionTag)
    sys_constraint_matrix = np.zeros([num_reals, num_sys])
    
    # Interior Constraints
    # Interiors are delayed by structural repairs
    interiors_idx = np.where(np.array(systems['name']) == 'interior')[0] #FZ# [0] is done to convert tuple to np array
    structure_idx = np.where(np.array(systems['name']) == 'structural')[0]
 
    sys_constraint_matrix[:,interiors_idx] = structure_idx+1 #FZ# +1 is done to replace with the system id which starts with 1, but python indexing starts at 0. 
    
    # Red Tag Constraints
    # All systems blocked by structural when red tagged
    for rt in np.where(conditionTag)[0]:
        for st in np.where(np.array(systems['name']) != 'structural')[0]:
            sys_constraint_matrix[rt, st] = structure_idx+1

    return sys_constraint_matrix


def fn_allocate_workers_systems(sys_repair_days, sys_crew_size, 
                                max_workers_per_building, 
                                sys_idx_priority_matrix, 
                                sys_constraint_matrix, 
                                condition_tag, 
                                sys_impeding_factors):


    '''Stagger repair to each system and allocate workers based on the repair
    constraints, priorities, and repair times of each system
    
    Parameters
    ----------
    system_repair_days: [num reals x num systems]
     Number of days from the start of repair of each to the completion of
     the system (assuming all sequences start on day zero)
    
    sys_crew_size: array [num reals x num systems]
     required crew size for each system
     
    max_workers_per_building: int
     Maximum number of workers that can work in the building at the same time 
     
    sys_idx_priority_matrix: matrix [num reals x systems]
     worker allocation order of system id's prioritized for each realiztion
     
    sys_constraint_matrix: array [num reals x num_sys]
     array of system ids which define which systems (column index) are delayed by the
     system ids (array values)
     
    condition_tag: logical array [num reals x 1]
     true/false if the building is red tagged
     
    sys_impeding_factors: array [num_reals x num_sys]
     maximum impedance time (days) for each system. Pass in empty array when
     calculating repair times (i.e. not including impeding factors).
    
    Returns
    -------
    repair_complete_day_per_system: matrix [num reals x num systems]
     Number of days from the start of each sequence to the completion of the
     sequence considering the allocation of workers to each sequence (ie
     some sequences start before others)
     
    worker_data['total_workers']: array [num reals x varies]
     total number of workers in the building at each time step of the worker
     allocation algorthim. The number of columns varies with the number of
     increments of the worker allocation algorithm.
     
    worker_data['day_vector']: array [num reals x varies]
     Day of each time step of the worker allocation algorthim. The number of 
     columns varies with the number of increments of the worker allocation algorithm.
    
    Notes
    -----'''
    
    import sys
    
    def fitler_matrix_by_rows( values, filter_by):
    # Use a identiry matrix to filter values from another matrix by rows
    
        # Parameters
        # ----------
        # values: matrix [n x m]
        #   values to filter by row
        # filter: matrix [n x m]
        #   array indexes to grab from each row of values
        #
        # Returns
        # -------
        # filtered_values: matrix [n x m]
        #   values filtered by rows
        
        # Method
        x2t = np.transpose(values)
        idx1 = np.transpose(filter_by)
        y4 = np.zeros(np.shape(idx1))
        for r in range(np.size(values,0)):
            y4[:, r] = x2t[idx1[:, r], r]
        filtered_values = np.transpose(y4)
        
        return filtered_values

    
    ## Initial Setup
    # Initialize Variables
    num_reals, num_sys = np.shape(sys_repair_days)
    priority_system_complete_day = np.zeros([num_reals,num_sys])
    day_vector = np.zeros([num_reals,0])
    total_workers = np.zeros([num_reals,0])
    
    # Re-order system variables based on priority
    priority_sys_workers_matrix = fitler_matrix_by_rows(sys_crew_size, sys_idx_priority_matrix)
    priority_sys_constraint_matrix = fitler_matrix_by_rows(sys_constraint_matrix, sys_idx_priority_matrix)
    priority_sys_repair_days = fitler_matrix_by_rows(sys_repair_days, sys_idx_priority_matrix)
    if sys_impeding_factors.size == 0:
        priority_sys_impeding_factors = np.zeros([num_reals, num_sys])
    else:
        priority_sys_impeding_factors = fitler_matrix_by_rows(sys_impeding_factors, sys_idx_priority_matrix)

    
    # Round up days to the nearest day
    # Provides an implicit change of trade delay, as well as help to reduce the
    # number of delta increments in the following while loop
    priority_sys_repair_days = np.ceil(priority_sys_repair_days)
    # priority_sys_impeding_factors = np.ceil(priority_sys_impeding_factors) #FZ# Already rounded. Check requirement
    
    ## Assign workers to each system based on repair constraints
    iter = 0
    current_day = np.zeros(num_reals)
    priority_sys_waiting_days = priority_sys_impeding_factors
    while sum(sum(priority_sys_repair_days)) > 0.01:
        iter = iter + 1; 
        if iter > 1000: # keep the while loop pandemic contained
            sys.exit('error (PBEE_Recovery:RepairSchedule, Could not converge worker allocations for among systems')

        
        # zero out assigned workers matrix
        assigned_workers = np.zeros([num_reals,num_sys])
        
        # limit available workers to the max that can be on any one given story
        # this ensures next system cannot start until completely unblocked on
        # every story. Need to update for taller buildings which could start
        # next sequence on lower story once previous sequence was far enough
        # along
        # available_workers = min(max(max_workers_per_story),max_workers_per_building)*ones(num_reals, 1);  % currently assumes all stories have the same crew size limitation (uniform sq ft for each story)
        available_workers = max_workers_per_building * np.ones(num_reals)
        
        # Define what systems are waiting to begin repairs
        sys_blocked = np.zeros([num_reals,num_sys]).astype(bool)
        sys_incomplete = priority_sys_repair_days > 0
        # constraining_systems = unique(priority_sys_constraint_matrix(priority_sys_constraint_matrix ~=0));
        for s in range(num_sys): # Loop over each system that may constrain something
            constrained_systems = priority_sys_constraint_matrix == s+1 # These systems are constrained by looped system #FZ# s+1 is done to correlate with +1 done in deriving constraint matrix
            constraining_sys_filt = sys_idx_priority_matrix == s; # location in matrix of this system
            is_constraining_sys_incomplete = np.amax(sys_incomplete * constraining_sys_filt, axis=1) # Vec of relizations for looped system
            sys_blocked = sys_blocked | np.transpose(np.transpose(constrained_systems) * is_constraining_sys_incomplete) # System is constrained if blocked by an incomplete system. #FZ# transpose done to align arrays for the operation
        
        # Need to wait for impeding factors or other repairs to finish
        is_waiting = np.transpose(current_day < np.transpose(priority_sys_impeding_factors)) | sys_blocked # assuming impeding factors are the only constraints. #FZ# transpose done to align arrays for the operation
        
        # Define where needs repair
        # System needs repair if there are still repairs days left and it is
        # not waiting to be unblocked
        needs_repair = (priority_sys_repair_days>0) & np.logical_not(is_waiting)
    
        # Defined Required Workers
        required_workers = needs_repair * priority_sys_workers_matrix
        
        # Assign Workers to each system
        for s in range(num_sys):
            # Assign Workers to this systems
            enough_workers = required_workers[:,s] <= available_workers
            assigned_workers[enough_workers,s] = np.minimum(required_workers[enough_workers,s], available_workers[enough_workers])
    
            # Define Available Workers
            # when in series limit available workers to the workers in this
            # system, assumes when red tagged, first systems is always
            # structural
            in_series = np.logical_and(condition_tag, s == 0)
            available_workers[np.logical_and(in_series, assigned_workers[:,s] > 0)] = 0 #FZ# Python index 0 is structural system
            # when not in series, calc the remaining workers
            available_workers[np.logical_not(in_series)] = available_workers[np.logical_not(in_series)] - assigned_workers[np.logical_not(in_series),s]

        
        # Calculate the time associated with this increment of the while loop
        in_progress = assigned_workers > 0 # sequences where work is being done
        total_repair_days = np.empty(np.shape(in_progress)) # pre-allocate with inf's becuase we take a min later
        total_repair_days[:] = np.inf
        total_repair_days[in_progress] = priority_sys_repair_days[in_progress]
        total_waiting_days = priority_sys_waiting_days
        
        #FZ##### the problem is here. Check
        total_waiting_days[total_waiting_days == 0] = np.inf # Convert zeros to inf such that zeros are not included in the min in the next step
        
        total_time = np.minimum(total_repair_days,total_waiting_days) # combime repair time and waiting time
        delta_days = np.amin(total_time,axis=1) # time increment is whatever in-progress story that finishes first
        delta_days[np.isinf(delta_days)] = 0 # Replace infs from real that has no repair with zero
        
        #FZ# Additional code added to correct the issue with 0 being replaced with infinity in priority_sys_waiting_days and priority_sys_impeding_factors
        priority_sys_waiting_days[priority_sys_waiting_days == np.inf] = 0
        # priority_sys_impeding_factors[priority_sys_impeding_factors == np.inf] = 0    
        
        # Reduce waiting time
        priority_sys_waiting_days = np.maximum(np.transpose(np.transpose(priority_sys_waiting_days) - delta_days), 0) #FZ# transpose done to align arrays for the operation
        
        # Reduce time needed for repairs
        delta_days_in_progress = np.transpose(delta_days * np.transpose(in_progress)) # change in repair time for all sequences being worked on #FZ# transpose done to align arrays for the operation
        priority_sys_repair_days[in_progress] = np.maximum(priority_sys_repair_days[in_progress] - delta_days_in_progress[in_progress], 0)
        
        # Define Start and Stop of Repair for each sequence
        priority_system_complete_day = priority_system_complete_day + np.transpose(delta_days * np.transpose(needs_repair | is_waiting)) #FZ# transpose done to align arrays for the operation
        
        # Define Cummulative day of repair
        day_vector = np.column_stack((day_vector, current_day))
        current_day = current_day + delta_days
        
        # Save worker data data over time
        # total_workers = [total_workers, np.sum(assigned_workers,axis=1), np.sum(assigned_workers,axis=1)] #FZ# why assigned workers stored twice - Review
        total_workers = np.column_stack((total_workers, np.sum(assigned_workers,axis=1), np.sum(assigned_workers,axis=1)))
        day_vector = np.column_stack((day_vector, current_day))

        
    # Untangle system_complete_day back into system table order
    
    sys_idx_untangle_matrix = np.argsort(sys_idx_priority_matrix, axis=1)
    
    repair_complete_day_per_system = fitler_matrix_by_rows(priority_system_complete_day, sys_idx_untangle_matrix)
    
    # Save worker data matrices
    worker_data ={'total_workers' : total_workers, 'day_vector' : day_vector}

    return repair_complete_day_per_system, worker_data 
    

def fn_restructure_repair_schedule( damage, system_schedule,
    repair_complete_day_per_system, systems, tmp_repair_complete_day):
    
    '''Redistribute repair schedule data from the system and story level to the component level for use 
    in the functionality assessment (ie, put repair schedule data into the
    damage object)
    
    Parameters
    ----------
    damage: dictionary
     contains per damage state damage and loss data for each component in the building
     
    system_schedule: dictionary
     repair time data for each system in isolation
     
    repair_complete_day_per_system: matrix [num reals x num systems]
     Number of days from the start of each sequence to the completion of the
     sequence considering the allocation of workers to each sequence (ie
     some sequences start before others)
     
    systems: DataFrame
     data table containing information about each system's attributes
     
    tmp_repair_complete_day: array [num_reals x num_comp]
     contains the day (after the earthquake) the temporary repair time is 
     resolved per damage state damage and realization
    
    Returns
    -------
    damage: dictionary
     contains per damage state damage and loss data for each component in
     the building, including repair schedule data.
    
    Notes
    -----'''
    
    ## Initialize Parameters
    num_sys = len(systems);
    num_units = len(damage['tenant_units'])
    

    ## Redistribute repair schedule data
    for tu in range(num_units):
        damage['tenant_units'][tu]['recovery'] = {
            'repair_start_day': np.empty([len(tmp_repair_complete_day), len(damage['tenant_units'][tu]['num_comps'])]),
            'repair_complete_day': np.empty([len(tmp_repair_complete_day), len(damage['tenant_units'][tu]['num_comps'])]),        
            'repair_complete_day_w_tmp': np.empty([len(tmp_repair_complete_day), len(damage['tenant_units'][tu]['num_comps'])]),
            'start_day_w_tmp': np.empty([len(tmp_repair_complete_day), len(damage['tenant_units'][tu]['num_comps'])]),
            'tmp_day_controls': np.empty([len(tmp_repair_complete_day), len(damage['tenant_units'][tu]['num_comps'])]),
            'repair_start_day_w_tmp': np.empty([len(tmp_repair_complete_day), len(damage['tenant_units'][tu]['num_comps'])])}
            
    for sys in range(num_sys):
        # Calculate system repair times on each story
        system_duration = np.amax(system_schedule['per_system'][sys]['repair_complete_day'],axis=1) # total repair time spent in this system over all stories
        start_day = repair_complete_day_per_system[:,sys] - system_duration
        story_start_day = np.transpose(start_day+ np.transpose(system_schedule['per_system'][sys]['repair_start_day'])) #FZ# transpose done to align arrays for the operation
        story_complete_day = np.transpose(start_day + np.transpose(system_schedule['per_system'][sys]['repair_complete_day'])) #FZ# transpose done to align arrays for the operation
    
        # Re-distribute to each tenant unit
        sys_filt = damage['comp_ds_table']['system'] == systems['id'][sys] 
        
        for tu in range(num_units):
            is_damaged = np.array(damage['tenant_units'][tu]['qnt_damaged'])[:,sys_filt] > 0
            is_damaged = (is_damaged*1).astype(float)
            is_damaged[is_damaged == 0] = np.nan
    
            # Re-distribute repair days to component damage states
            damage['tenant_units'][tu]['recovery']['repair_start_day'][:,sys_filt] = np.transpose(np.transpose(is_damaged) * story_start_day[:,tu]) #FZ# transpose done to align arrays for the operation
            damage['tenant_units'][tu]['recovery']['repair_complete_day'][:,sys_filt] = np.transpose(np.transpose(is_damaged) * story_complete_day[:,tu]) #FZ# transpose done to align arrays for the operation

        
    # Post process for temp repairs
    for tu in range(num_units):
        # Calculate the day repairs are completed considering temporary repairs
        repair_complete_day_no_NaN = np.fmax(damage['tenant_units'][tu]['recovery']['repair_complete_day'] ,0)
        damage['tenant_units'][tu]['recovery']['repair_complete_day_w_tmp'] = np.minimum(repair_complete_day_no_NaN, tmp_repair_complete_day)
    
        # Calculate the day repairs start considering temporary repairs
        damage['tenant_units'][tu]['recovery']['start_day_w_tmp'] = damage['tenant_units'][tu]['recovery']['repair_start_day']
        damage['tenant_units'][tu]['recovery']['tmp_day_controls'] = damage['tenant_units'][tu]['recovery']['repair_complete_day_w_tmp'] < repair_complete_day_no_NaN
        damage['tenant_units'][tu]['recovery']['repair_start_day_w_tmp'][damage['tenant_units'][tu]['recovery']['tmp_day_controls']] = 0
    
        # Change zeros in complete day back to NaN (ie no damage)
        damage['tenant_units'][tu]['recovery']['repair_complete_day_w_tmp'][damage['tenant_units'][tu]['recovery']['repair_complete_day_w_tmp'] == 0] = np.nan

    return damage


def fn_format_gantt_chart_data( damage, systems ):
    '''Reformat data from the damage structure into data that is used for the
    gantt charts
    
    Parameters
    ----------
    damage: dictionary
     contains per damage state damage and loss data for each component in the building
    systems: DataFrame
     data table containing information about each system's attributes
    
    Returns
    -------
    repair_schedule: dictionary
     Contians reformated repair schedule data for gantt chart plots for
     both repair time and downtime calculations. Data is reformanted to
     show breakdowns by component, by story, by system, by story within each
     system, and by system within each story.
    
    Notes
    -----
    Since this all has to do with plotting gantt charts, a form of this
    (whether the damage structure or a higher level repair schedule
    structure) should be output and this reformatting logic moved outside the
    functional recovery assessment and into the data visuallation logic'''
    
    ## Initial Setup
    num_stories = len(damage['tenant_units'])
    num_reals = np.size(damage['tenant_units'][0]['recovery']['repair_start_day'],0)
    comps = np.unique(damage['comp_ds_table']['comp_id'])
    
    ## Reformate repair schedule data into various breakdowns
    # Per component
    repair_schedule = {'repair_start_day' : {}, 'repair_complete_day' : {}, 'component_names':[]}
    repair_schedule['repair_start_day']['per_component'] = np.empty([num_reals, len(comps)])
    repair_schedule['repair_start_day']['per_component'][:] = np.nan
    repair_schedule['repair_complete_day']['per_component'] = np.zeros([num_reals,len(comps)])
    for c in range(len(comps)):
        comps_filt = damage['comp_ds_table']['comp_id'] == comps[c]
        for s in range(num_stories):
            repair_schedule['repair_start_day']['per_component'][:,c] = np.nanmin(np.column_stack((repair_schedule['repair_start_day']['per_component'][:,c], damage['tenant_units'][s]['recovery']['repair_start_day'][:,comps_filt])), axis=1)
            repair_schedule['repair_complete_day']['per_component'][:,c] = np.nanmax(np.column_stack((repair_schedule['repair_complete_day']['per_component'][:,c], damage['tenant_units'][s]['recovery']['repair_complete_day'][:,comps_filt])), axis=1)

        repair_schedule['component_names'].append(str(comps[c]))

    
    # Per Story
    repair_schedule['repair_start_day']['per_story'] = np.empty([num_reals, num_stories])
    repair_schedule['repair_start_day']['per_story'][:] = np.nan
    repair_schedule['repair_complete_day']['per_story'] = np.zeros([num_reals,num_stories])
    for s in range(num_stories):
        repair_schedule['repair_start_day']['per_story'][:,s] = np.nanmin(np.column_stack((repair_schedule['repair_start_day']['per_story'][:,s], damage['tenant_units'][s]['recovery']['repair_start_day'])), axis=1)
        repair_schedule['repair_complete_day']['per_story'][:,s] = np.nanmax(np.column_stack((repair_schedule['repair_complete_day']['per_story'][:,s], damage['tenant_units'][s]['recovery']['repair_complete_day'])), axis=1)
    
    
    # Per Repair System
    repair_schedule['repair_start_day']['per_system'] = np.empty([num_reals, len(systems)])
    repair_schedule['repair_start_day']['per_system'][:] = np.nan
    repair_schedule['repair_complete_day']['per_system'] = np.zeros([num_reals,len(systems)])
    for sys in range(len(systems)):
        sys_filt = damage['comp_ds_table']['system'] == systems['id'][sys] # identifies which ds idices are in this seqeunce  
        for s in range(num_stories):
            repair_schedule['repair_start_day']['per_system'][:,sys] = np.nanmin(np.column_stack((repair_schedule['repair_start_day']['per_system'][:,sys], damage['tenant_units'][s]['recovery']['repair_start_day'][:,sys_filt])), axis=1)
            repair_schedule['repair_complete_day']['per_system'][:,sys] = np.nanmax(np.column_stack((repair_schedule['repair_complete_day']['per_system'][:,sys], damage['tenant_units'][s]['recovery']['repair_complete_day'][:,sys_filt])), axis=1)


    repair_schedule['system_names'] = np.array(systems['name'])
    
    # Per system per story
    num_sys_stories = num_stories * len(systems)
    repair_schedule['repair_start_day']['per_system_story'] = np.empty([num_reals,num_sys_stories])
    repair_schedule['repair_start_day']['per_system_story'][:] = np.nan
    repair_schedule['repair_complete_day']['per_system_story'] = np.zeros([num_reals,num_sys_stories])
    id = -1; #FZ# -1 done to account for python indexing starting from 0
    for s in range(num_stories):
        for sys in range(len(systems)):
            id += 1
            sys_filt = damage['comp_ds_table']['system'] == systems['id'][sys] # identifies which ds idices are in this seqeunce  
            repair_schedule['repair_start_day']['per_system_story'][:,id] = np.nanmin(np.column_stack((repair_schedule['repair_start_day']['per_system_story'][:,id], damage['tenant_units'][s]['recovery']['repair_start_day'][:,sys_filt])), axis=1)
            repair_schedule['repair_complete_day']['per_system_story'][:,id] = np.nanmax(np.column_stack((repair_schedule['repair_complete_day']['per_system_story'][:,id], damage['tenant_units'][s]['recovery']['repair_complete_day'][:,sys_filt])), axis=1)

    
    # Per story per system
    num_sys_stories = num_stories * len(systems)
    repair_schedule['repair_start_day']['per_story_system'] = np.empty([num_reals,num_sys_stories])
    repair_schedule['repair_start_day']['per_story_system'][:] = np.nan
    repair_schedule['repair_complete_day']['per_story_system'] = np.zeros([num_reals,num_sys_stories])
    
    id = -1; #FZ# -1 done to account for python indexing starting from 0
    for sys in range(len(systems)):
        for s in range(num_stories):
            id += 1
            sys_filt = damage['comp_ds_table']['system'] == systems['id'][sys] # identifies which ds idices are in this seqeunce 
            repair_schedule['repair_start_day']['per_story_system'][:,id] = np.nanmin(np.column_stack((repair_schedule['repair_start_day']['per_story_system'][:,id], damage['tenant_units'][s]['recovery']['repair_start_day'][:,sys_filt])), axis=1)
            repair_schedule['repair_complete_day']['per_story_system'][:,id] = np.nanmax(np.column_stack((repair_schedule['repair_complete_day']['per_story_system'][:,id], damage['tenant_units'][s]['recovery']['repair_complete_day'][:,sys_filt])), axis=1)

    return repair_schedule



    

    
    
    