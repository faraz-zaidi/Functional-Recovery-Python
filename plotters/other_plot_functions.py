# -*- coding: utf-8 -*-
"""
Created on Thu Dec  1 16:15:28 2022

@author: fzai683
"""

def plt_heatmap_breakdowns(recovery, plot_dir):
    '''Plot the time and percent of realizations that each system and/or 
    component is impeding function as a heatmap
    
    Parameters
    ----------
    recovery: dictionary
     dictionary containing recovery breakdown data from the functional
     recovery assessment
     
    plot_dir: str
     Save directory for plots. Plots will save directly to this location as
     png files.
    
    Returns
    -------'''
    
    import seaborn as sb
    import matplotlib.pyplot as plt
    import os
    import numpy as np
    
    ## Initial Setup
    if os.path.exists(plot_dir) == False:
        os.mkdir(plot_dir)
    plot_dir=plot_dir +'/'
    
    perform_targ_labs = ['Immediately', '>3 Days', '>7 Days', '>2 Weeks', '>1 Month', '>6 Months', '>1 Year']
    var = ['component_breakdowns', 'system_breakdowns']
    labs = ['comp_names', 'system_names']
    plt_ht = [10, 8]
    
    ## Plot Heatmaps
    fnc_states = list(recovery.keys())
    for fs in range(len(fnc_states)):
        for v in range(len(var)):
            y_labs = recovery[fnc_states[fs]]['breakdowns'][labs[v]]
            data = np.array(recovery[fnc_states[fs]]['breakdowns'][var[v]])
            
            plt.rcParams["font.family"] = "Times New Roman"
            plt.figure(figsize=(plt_ht))
            h = sb.heatmap(data, cmap='Blues', linewidths = 0.5, linecolor = 'black', annot = np.round(data,2), xticklabels = perform_targ_labs, yticklabels = y_labs, clip_on = False)
            fnc_lab = fnc_states[fs][0].upper() + fnc_states[fs][1:len(fnc_states[fs])]+' Recovery'
            title = 'Fraction of Realizations Affecting Building ' + fnc_lab
            h.set(xlabel  = 'Recovery Time After Earthquake')
            # h.set(ylabel = labs[v])
            h.set_title(title, x=0.5, y=1.05)
            plt.xticks(rotation=45)
            plt.subplots_adjust(bottom=0.15)
            
            plt.savefig(plot_dir + var[v] +' '+fnc_states[fs] + '.png', dpi=300)

    return

def plt_histograms( recovery, plot_dir ):
    
    '''Plot all realizations of building level recovery as a histogram
    
    Parameters
    ----------
    recovery: dictionary
      dictionary containing building-level recovery data from the 
      functional recovery assessment
     
    plot_dir: str
      Save directory for plots. Plots will save directly to this location as
      png files.
    
    Returns
    -------'''
    
    import seaborn as sb
    import matplotlib.pyplot as plt
    import os
    
    ## Initial Setup
    if os.path.exists(plot_dir) == False:
        os.mkdir(plot_dir)
    plot_dir=plot_dir +'/'
    
    ## Plot Histograms
    fnc_states = list(recovery.keys())
    for fs in range(len(fnc_states)):
        plt.rcParams["font.family"] = "Times New Roman"
        plt.figure(figsize=(6,4))
        sb.histplot(data = recovery[fnc_states[fs]]['building_level']['recovery_day'])
        fnc_lab = fnc_states[fs][0].upper() + fnc_states[fs][1:len(fnc_states[fs])]+' Recovery'        
        plt.xlabel(fnc_lab + ' Time (days)')
        plt.ylabel('Number of Realizatons')
        plt.savefig(plot_dir + fnc_states[fs] + '.png', dpi=300)
        
    return

def plt_recovery_trajectory( recovery, full_repair_time, plot_dir):
    '''Plot mean recovery trajectories
    
    Parameters
    ----------
    recovery: dictionary
      dictionary containing recovery trajectory data from the functional
      recovery assessment
     
    full_repair_time: array [num reals x 1] 
      simulated realization of full repair time 
    
    plot_dir: str
      Save directory for plots. Plots will save directly to this location as
      png files.
    
    Returns
    -------'''
     
    
    import matplotlib.pyplot as plt
    import os
    import numpy as np
    
    ## Initial Setup
    if os.path.exists(plot_dir) == False:
        os.mkdir(plot_dir)
    plot_dir=plot_dir +'/'
    
    # Calculate mean recovery times
    reoc = np.mean(np.array(recovery['reoccupancy']['recovery_trajectory']['recovery_day']), axis=0)
    func = np.mean(np.array(recovery['functional']['recovery_trajectory']['recovery_day']), axis=0)
    full = np.mean(full_repair_time)
    level_of_repair = recovery['functional']['recovery_trajectory']['percent_recovered']
    
    ## Plot Recovery Trajectory
    plt.rcParams["font.family"] = "Times New Roman"
    plt.figure(figsize=(6,4)) 
    plt.plot(reoc, level_of_repair,'r-', linewidth = 1.5, label = 'Re-Occupancy') 
    plt.plot(func, level_of_repair,'b-', linewidth = 1.5, label= 'Functional') 
    plt.plot([full, full], [0, 1],'k-', linewidth = 1.5, label= 'Fully Repaired') 
    plt.xlim([0,np.ceil((full+1)/10)*10])
    plt.xlabel('Days After Earthquake')
    plt.ylabel('Fraction of Floor Area')
    plt.legend(loc='upper left')
    plt.grid()
    
    plt.savefig(plot_dir + 'recovery_trajectory.png', dpi=300)

    return

def plt_gantt_chart(p_idx, recovery, full_repair_time, workers, schedule, impede, plot_dir, plot_name):
    '''Plot gantt chart for a single realization of the functional recovery
    assessment
    
    Parameters
    ----------
    p_idx: int
      realization index of interest
     
    recovery: dictionary
      dictionary containing recovery trajectory data from the functional
      recovery assessment
    
    full_repair_time: array [num reals x 1] 
      simulated realization of full repair time 
    
    workers: dictionary
      data structure containing work allocation data from the functional
      recovery assessment
    
    schedule: dictionary
      dictionary containing repair schedule data from the functional
      recovery assessment
    
    impede: dictionary
      data structure containing impedance time data from the functional
      recovery assessment
    
    plot_dir: str
      Save directory for plots. Plots will save directly to this location as
      png files.
     
    plot_name: str
      name of file to save plot as (does not include the file type extension)
    
    Returns
      -------'''

    import matplotlib.pyplot as plt
    import os
    import numpy as np
    
    ## Initial Setup
    if os.path.exists(plot_dir) == False:
        os.mkdir(plot_dir)
    plot_dir=plot_dir +'/'
    
    imps = list(impede.keys())
    sys = list(impede['contractor_mob'].keys())
    
    ## Format Gantt Chart Data
    recovery_trajectory = {
        'reoc' : np.array(recovery['reoccupancy']['recovery_trajectory']['recovery_day'])[p_idx,:],
        'func' : np.array(recovery['functional']['recovery_trajectory']['recovery_day'])[p_idx,:],
        'level_of_repair' : np.array(recovery['reoccupancy']['recovery_trajectory']['percent_recovered']),
        'ful_rep' : np.ones(len(recovery['reoccupancy']['recovery_trajectory']['percent_recovered'])) * np.ceil(full_repair_time[p_idx])
        }
    
    # Collect Worker Data
    worker_data = {
        'total_workers' : np.array(workers['total_workers'])[p_idx,:],
        'day_vector' : np.array(workers['day_vector'])[p_idx,:]
        }
    
    # Collect Impedance Times
    sys_imp_times = []
    labs = []
    for s in range(len(sys)):
        for i in range(len(imps)):
            if 'complete_day' in impede[imps[i]].keys():
                duration = impede[imps[i]]['complete_day'][p_idx] - impede[imps[i]]['start_day'][p_idx]
                if duration > 0:
                    sys_imp_times.append([impede[imps[i]]['start_day'][p_idx], duration])
                    labs.append(imps[i][0].upper() + imps[i][1:len(imps[i])].replace('_',' '))

                
            elif sys[s] in impede[imps[i]].keys():
                duration = impede[imps[i]][sys[s]]['complete_day'][p_idx] - impede[imps[i]][sys[s]]['start_day'][p_idx]
                if duration > 0:
                    sys_imp_times.append([impede[imps[i]][sys[s]]['start_day'][p_idx], duration])
                    labs.append(sys[s][0].upper() + sys[s][1:len(sys[s])] + ' ' + imps[i].replace('_',' '))
 
        
    labs_imp = np.array(labs)
    # y_imp = np.flip(np.array(sys_imp_times), axis=0)
    y_imp = np.array(sys_imp_times)
    # Find and delete repeatative entries
    rep_lab=np.ones(len(labs_imp)).astype(bool)
    for i in np.unique(labs_imp):
        num=0
        for j in range(len(labs)):
            if i == labs[j]:
                num=num+1
                if num >1:
                    rep_lab[j] = False
                    
    labs_imp = labs_imp[rep_lab]
    y_imp = y_imp[rep_lab,:]
    
    labs_imp = np.flip(labs_imp)
    y_imp = np.flip(y_imp, axis=0)

    
    # Collect Repair Times 
    sys_repair_times = []
    labs = []
    for s in range(len(sys)): # WARNING: This assumes the system order in the output of repair schedule is the same order has the impedance breakdowns
        duration = schedule['repair_complete_day']['per_system'][p_idx][s] - schedule['repair_start_day']['per_system'][p_idx][s]
        if duration > 0:
            sys_repair_times.append([schedule['repair_start_day']['per_system'][p_idx][s], duration])
            labs.append(sys[s][0].upper() + sys[s][1:len(sys[s])] + ' Repairs')

    labs.reverse()    
    labs_rep = labs
    y_rep = np.flip(np.array(sys_repair_times), axis=0)
    ## Plot Gantt
    # x_limit = max(np.ceil(max(recovery_trajectory['ful_rep'])/10)*10, 1)
    
    plt.rcParams["font.family"] = "Times New Roman"
    # Impedance Time
    fig, (G1, G2, G3, G4) = plt.subplots(4, 1, sharex=True, figsize = (10,12), gridspec_kw={'height_ratios': [2, 1, 1, 1]})
    G1.barh(labs_imp, y_imp[:,0], color = 'white')    
    G1.barh(labs_imp, y_imp[:,1], left = y_imp[:,0], color='lightgrey')
    G1.set_title('Impedance Time')
    G1.grid(which = 'major', axis = 'x', alpha=0.5)
    # G1.set_xlabel('Days After Earthquake')
    
    # Repair Time
    G2.barh(labs_rep, y_rep[:,0], color = 'white')
    G2.barh(labs_rep, y_rep[:,1], left = y_rep[:,0], color='grey')
    G2.set_title('Repair Time') 
    G2.grid(which = 'major', axis = 'x', alpha=0.5)    
    
    
    # Workers
    G3.plot(worker_data['day_vector'], worker_data['total_workers'])
    G3.set_ylabel('Number of workers')
    G3.set_title('Number of workers')
    G3.grid(which = 'major', axis = 'x', alpha=0.5) 
    
    # Plot Recovery Trajectory
    G4.plot(recovery_trajectory['reoc'], recovery_trajectory['level_of_repair'],'r-', linewidth = 1.5, label = 'Re-Occupancy')
    G4.plot(recovery_trajectory['func'], recovery_trajectory['level_of_repair'],'b-', linewidth = 1.5, label = 'Functional')
    G4.plot(recovery_trajectory['ful_rep'], recovery_trajectory['level_of_repair'],'k-', linewidth = 1.5, label = 'Fully Repaired')
    G4.set_ylim([0,1])
    G4.set_xlabel('Days After Earthquake')
    G4.set_ylabel('Fraction of Floor Area')
    G4.set_title('Building Recovery State')
    G4.grid(which = 'major', axis = 'x', alpha=0.5)
    G4.legend()
    fig.subplots_adjust(left=0.20)
    fig.savefig(plot_dir + plot_name + '.png', dpi=300)
    
    return

    # % Set and Save plot
    # set(gcf,'position',[10,10,800,600])
    # saveas(gcf,[plot_dir filesep plot_name],'png')
    # close
    
    # end
    
    # function [] = fn_format_subplot(ax,x_limit,y_lab,x_lab,tle)
    #     ax.XGrid = 'on';
    #     ax.XMinorGrid = 'on';
    #     xlim([0,x_limit])
    #     box on
    #     set(gca,'fontname','times')
    #     set(gca,'fontsize',9)
    #     if ~isempty(y_lab)
    #         ylabel(y_lab)
    #     end
    #     if ~isempty(x_lab)
    #         xlabel(x_lab)
    #     else
    #         set(gca,'XTickLabel',[])
    #     end
    #     title(tle)
    # end