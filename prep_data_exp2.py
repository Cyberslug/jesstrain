#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Filename : prep_data_exp2.py
# @Version : 2.1
# @Date : 2019-10-13-14-52
# @Project: jesstrain
# @AUTHOR
# : jessir
'''
Removes some hardcoding of differences across experiments
'''

import numpy as np
import pandas as pd
import os
#import sys
from glob import glob
from analysis_tools import bearingError, positionError

code_directory = ('C:\\Users\\jesir\\PycharmProjects\jesstrain')
os.chdir(code_directory)

# Set the directory
# Get code path - currently inside jesstrain
##code_directory = os.path.dirname(sys.argv[0])  #Note this won't work when typed into console
##os.chdir(code_directory)
# Change directory to data folder
os.chdir('..')
os.chdir('data')
data_directory = os.getcwd()

# Get list of team folders and team numbers
team_folder_list = glob('Team*')

df_condlist = pd.read_csv('condlist.csv')
df_sst = pd.read_csv('Sonar_start_time.csv')  # Get sonar start times

# Set up variables used for all analysis
sessions = [1,2]
exclude_RT_outliers = True #set to 1 to exclude solutions that are made too quickly from last solution
exclude_sonar_outliers = True # set to 1 to exclude any solutions that set the range beyond what sonar can detect
exclude_bearing_outliers = True # set to 1 to exclude any solutions with bearing errors outside bearerrmax
endtime = 3700  # total number of seconds to look at
timepoint_secs = 20  # number of seconds per time point
timepoint_number = int(endtime / timepoint_secs)
ypm = 33.756  # Yards per minute travelling at 1 knot = 33.756
points_range = .33  # Solution must be within this proportion of range in order # to score a point
zig_degrees = 30  # How many degrees change in course to qualify for a zig
sonar_range = 30000  # Max range for detection (as told to participants)
bearing_error_max = 20  # bearing errors outside of this considered outliers
minRT = 10  # minimum allowable time since last solution
# Weights from highest 3 to lowest 1 CLASSIFICATION BELOW
classification_weights_dict = {'Warship': 3, 'Fishing': 2, 'Merchant': 1}
range_weights_dict = {5000: 3, 10000: 2, 15000: 1}
course_weights_dict = {'Closing': 3, 'Opening': 1}
zig_weights_dict = {'Zigging': 3, 'Notzigging': 1}

firstcompleted = 0

# Save any flagged issues in this file in the main directory
flagfile = open('flagfile.txt', 'w')

for team_folder in team_folder_list:

    team = int(team_folder.strip('Team '))
    os.chdir(data_directory + '\\' + team_folder)
    session_folder_list = glob('cruse-*')

    for session in sessions:

        session_folder = session_folder_list[session-1]  # minus 1 to match indexing
        os.chdir(data_directory + '\\' + team_folder + '\\' + session_folder)

        condlist_criteria = (df_condlist['Team'] == team)
        integration_condition = df_condlist[condlist_criteria][('Session' + str(session) + '_Intcond')].iloc[0]
        scenario_num = str(df_condlist[condlist_criteria][('Session' + str(session) + '_Scenario')].iloc[0])
        condition_label = integration_condition + '_' + scenario_num

        print(team_folder)
        print('Session ' + str(session))
        print(session_folder)

        flagfile.write(team_folder + '\n')
        flagfile.write('Session ' + str(session) + '\n')
        flagfile.write(session_folder + '\n')

        # Clear flags
        rangeFlag = 0
        bearerrFlag = 0
        rtFlag = 0
        multisolFlag = 0
        
        # Import necessary files into dataframes
        df_sl = pd.read_csv('solution_legs.csv')  # All solutions entered. Includes initial solution set by sonar
        df_ts = pd.read_csv('target_solution.csv')  # Ground truth for every vessel every 20s
        df_nav = pd.read_csv('navdata.csv')  # Ownship nagivation data. Updated every 1s
        df_cn = pd.read_csv('contacts.csv')  # Contact timing info
        df_eh = pd.read_csv('entity_history.csv')  # Included sonar tracker data
        df_st = pd.read_csv('sonar_tracks.csv')  # Sonar TID and SCID initiation
        df_ann = pd.read_csv('annotations.csv')  # TPC and Sonar annotations
        df_atw = pd.read_csv('atwit.csv')  # atwit scores
        df_atw = df_atw[df_atw.aw_console != 'COMMAND'].copy()  # remove rows from console "command"
        df_atw['aw_workload'] = df_atw['aw_workload'].replace(999, np.NaN)  # replace 999 with NA

        # Get console/operator names used in this experiment from data
        consoles = pd.unique(df_atw['aw_console'])
        consoles.sort()

        # DON'T REALLY NEED THIS ANYMORE Get vessel names used in this experiment from data
        #classifications = pd.unique(df_eh['eh_classification'])
        #classifications.sort()

        ### DATA CLEANING AND PREP
        df_sl = df_sl[df_sl.sl_console != 'TPC'].copy() # remove any new visual contacts initiated by TPC 
        ts_all_cons = pd.unique(df_ts['ts_id']) 
        ts_all_n = ts_all_cons.size   #total number of contacts listed in TS, including those not yet detected
        sl_all_cons = pd.unique(df_sl['sl_sid']) 
        if ts_all_n > sl_all_cons.size:
            flagfile.write('*** FLAG *** Not all contacts detected\n')
        elif ts_all_n < sl_all_cons.size:
            flagfile.write('*** FLAG *** More solution numbers than contacts\n')
            
        
# 1. Convert solution legs from metres/m per second to yards and knots to match other files
        df_sl.loc[:,'sl_range'] = df_sl.loc[:,'sl_range']*1.09361
        df_sl.loc[:,'sl_speed'] = df_sl.loc[:,'sl_speed']*1.94384
        
# 2. Calculate x/y for solution
        
        # Get ownship x/y from Navdata for the time each SL was lodged. UPDATED to fix error with two SLs on same timepoint
        for sl, row in df_sl.iterrows(): 
            navcrit = (df_nav.loc[:,'nd_time']==round(df_sl.loc[sl,'sl_time']))
            df_sl.loc[sl,'sl_ownship_x'] = df_nav.loc[navcrit]['nd_x'].iloc[0]
            df_sl.loc[sl,'sl_ownship_y'] = df_nav.loc[navcrit]['nd_y'].iloc[0]
        
        # Calculate x/y of each solution using bearing and range 
        df_sl.loc[:,'sl_x'] = df_sl['sl_range'] * np.sin(np.deg2rad((df_sl['sl_bearing']))) + df_sl['sl_ownship_x']
        df_sl.loc[:,'sl_y'] = df_sl['sl_range'] * np.cos(np.deg2rad((df_sl['sl_bearing']))) + df_sl['sl_ownship_y']
        
# 3. Match sl_id to ts_id. Use contacs file to do this - this corresponds to the sonar initial solutions and seems to match with SL ID
        
        # Get the most recent timepoint prior to when the solution was lodged. Use this to match up ground truth poition
        df_sl['sl_prior_time'] = np.floor(df_sl['sl_time']/20)*20
        df_sl['sl_post_time'] = np.ceil(df_sl['sl_time']/20)*20
        df_sl['sl_ts_id'] = 0
        
# 4. For each SL contact, find the closest TS current visible
        for sl_id in sl_all_cons: 
            slcrit = (df_sl['sl_sid']==sl_id)
            slc_bearing = df_sl.loc[slcrit]['sl_bearing'].iloc[0] # Take the bearing of the initial (sonar) solution
            slc_time = df_sl.loc[slcrit]['sl_time'].iloc[0] # Take the time of the initial (sonar) solution
            ts_time = df_sl.loc[slcrit]['sl_prior_time'].iloc[0] # Take the time of the initial (sonar) solution
            
            # Use only the TSs that are currently available to sonar from df_sst file
            sonar_ts_ids = df_sst.loc[(df_sst['Time'])<=slc_time]['Con']
            
            # Find vessel on closest bearing at this time
            matchcrit = (df_ts['ts_time']==ts_time) & (df_ts['ts_id'].isin(sonar_ts_ids))
            ts_bears = df_ts.loc[matchcrit].copy()
            # Uses bearingError function from analysis_tools
            ts_bears['bear_diffs'] = [bearingError(bearing, slc_bearing) for bearing in ts_bears['ts_bearing']]  
            ts_id = df_ts.loc[ts_bears['bear_diffs'].idxmin(),'ts_id']
            
            # Flag anything weird going on here
            if ts_bears['bear_diffs'].min() > 1:
                flagfile.write('*** FLAG *** SCID assigned to a contact with bearing error greater than 1: TS' + str(ts_id) + ' SL' + str(sl_id) + ' Bearing error' + str(ts_bears['bear_diffs'].min()) + '\n')
            if sum(ts_bears['bear_diffs'].nsmallest(2)<1) > 1: #i.e. if more than 2 TS are within 1 degree
                ts_id2 = ts_bears.sort_values(by=['bear_diffs'])['ts_id'].iloc[1]
                flagfile.write('*** FLAG *** Two possible contacts within 1 degree of SCID: SL' + str(sl_id) + ' TS' + str(ts_id) + ' and TS' + str(ts_id2) + '\n')
                print('*** FLAG *** Two possible contacts within 1 degree of SCID\n')
            
            # Update SL with TS ID
            df_sl.loc[slcrit,'sl_ts_id'] = ts_id
            
# 5. Check to see whether there are multiple SCIDs attached to a single contact and combine into single sierra num
        for ts_id in ts_all_cons:
            tscrit = (df_sl['sl_ts_id']==ts_id)
            if df_sl[tscrit].shape[0] > 0:
                if pd.unique(df_sl[tscrit]['sl_sid']).shape[0] > 1: #If multiple SLs assigned to same SD
                    flagfile.write('*** FLAG *** More than one SL assigned to TS %d \n' % ts_id) 
                    print(('*** FLAG *** More than one SL assigned to TS %d' % ts_id))
                    flagfile.write(str(pd.unique(df_sl[tscrit]['sl_sid'])) + '\n')
                    print(str(pd.unique(df_sl[tscrit]['sl_sid'])))
                    multisolFlag += 1
                # Set all SLs to the same value in this variable
                df_sl.loc[tscrit,'sl_first_sid'] = pd.unique(df_sl[tscrit]['sl_sid']).min()
            
# 6. Get timings for TID detect time, SCID detect time
            stcrit = (df_st['st_entity_id']== ts_id) #Get TID detect time from sonar tracks file
            slcrit = (df_sl['sl_ts_id'] == ts_id)
            # TiD detect time
            if df_st.loc[stcrit].shape[0] > 0: # If any TIDs have been assigned ANY CASES IN WHICH THIS WOULDN'T BE TRUE
                df_sl.loc[tscrit,'sl_TID_detect_time'] = df_st.loc[stcrit]['st_init_time'].iloc[0] #Choose the time of the first TID
                df_sl.loc[tscrit,'sl_SCID_detect_time'] = df_sl.loc[slcrit]['sl_time'].iloc[0] # time first solution initiated by sonar in SL

        
# 7. Calculate position error relative to most recent timepoint
        for sl, row in df_sl.iterrows():
            tsrowcrit = (df_ts.loc[:,'ts_time']==df_sl.loc[sl,'sl_prior_time']) & (df_ts.loc[:,'ts_id']==df_sl.loc[sl,'sl_ts_id'])
            df_sl.loc[sl,'sl_ts_x'] = df_ts[tsrowcrit]['ts_x'].iloc[0]
            df_sl.loc[sl,'sl_ts_y'] = df_ts[tsrowcrit]['ts_y'].iloc[0]
            df_sl.loc[sl,'sl_ts_bearing'] = df_ts[tsrowcrit]['ts_bearing'].iloc[0]
            df_sl.loc[sl,'sl_ts_range'] = df_ts[tsrowcrit]['ts_range'].iloc[0]
            df_sl.loc[sl,'sl_ts_course'] = df_ts[tsrowcrit]['ts_course'].iloc[0]
            df_sl.loc[sl,'sl_ts_speed'] = df_ts[tsrowcrit]['ts_speed'].iloc[0]

# 8. Calculate the contact that is the closest to the solution at time of solution and check whether it matches the correct solution
            tstimecrit = (df_ts.loc[:,'ts_time']==df_sl.loc[sl,'sl_prior_time'])
            ts_times = df_ts.loc[tstimecrit].copy()
            # Uses bearingError function from analysis_tools
            ts_times['pe'] = [positionError(x1,df_sl.loc[sl,'sl_x'],y1,df_sl.loc[sl,'sl_y']) for x1,y1 in zip(ts_times['ts_x'],ts_times['ts_y'])]
            df_sl.loc[sl,'sl_ts_closest'] = df_ts.loc[ts_times['pe'].idxmin(),'ts_id']
            df_sl.loc[sl,'sl_closest_acc'] = int(df_sl.loc[sl,'sl_ts_closest'] == df_sl.loc[sl,'sl_ts_id'])
            
# 9. Assign classifications & weights
            
            # Classification
            # $%$%$%$% MAYBE DONE OUTSIDE THE LOOP???
            sstcrit = (df_sst['Con']==df_sl.loc[sl,'sl_ts_id'])
            df_sl.loc[sl,'sl_ts_classification'] = df_sst.loc[sstcrit]['Class'].iloc[0]
            # Get the broad classification category (Merchant, Fishing, Warship) to match to weighting dictionary
            classification_category = df_sl.loc[sl,'sl_ts_classification'].split(' ', 1)[0]
            df_sl.loc[sl,'sl_class_weight'] = classification_weights_dict.get(classification_category, "none")
                
            # Range
            rangebin = np.ceil(df_sl.loc[sl,'sl_ts_range'] / next(iter(range_weights_dict))) * next(iter(range_weights_dict)) # Divides by the smallest range, rounds to the ceiling, then multiplies by the smallest range
            df_sl.loc[sl,'sl_range_weight'] = range_weights_dict.get(rangebin, 1) # Alternative is 1 = range larger than used here
            
            # Course (Closing = positive timeCPA, opening = negative timeCPA)
            if df_ts[tsrowcrit]['ts_timecpa'].iloc[0] > 0:
                df_sl.loc[sl,'sl_course_weight'] = course_weights_dict.get('Closing', "none")
            else: 
                df_sl.loc[sl,'sl_course_weight'] = course_weights_dict.get('Opening', "none")
            # Zig: Get later from the solutionleg_over_time data

# 10. Calculate error

        df_sl['sl_PE'] = positionError(df_sl.loc[:,'sl_ts_x'], df_sl.loc[:,'sl_x'], df_sl.loc[:,'sl_ts_y'], df_sl.loc[:,'sl_y'])
        df_sl['sl_PE_over_range'] = df_sl['sl_PE']/df_sl['sl_ts_range']
        df_sl['sl_bearingError'] = [bearingError(ts_bearing, sl_bearing) for ts_bearing, sl_bearing in zip(df_sl['sl_ts_bearing'],df_sl['sl_bearing'])]
        df_sl['sl_rangeError'] = abs(df_sl['sl_ts_range'] - df_sl['sl_range']) # NOTE RANGE AND SPEED ARE ASBOLUTE HERE
        df_sl['sl_courseError'] = [bearingError(ts_course, sl_course) for ts_course, sl_course in zip(df_sl['sl_ts_course'],df_sl['sl_course'])]
        df_sl['sl_speedError'] = abs(df_sl['sl_ts_speed'] - df_sl['sl_speed'])   

# 11. Add in RT
        
        # Response time from initial detection
        df_sl['sl_RT'] = df_sl['sl_time'] - df_sl['sl_SCID_detect_time']
        
        # TMA RT: Time since the last solution (by each TMA)
        TMA_count = sum('TMA' in console for console in consoles)  # Count how many TMAs
        for tma in range(1,TMA_count+1):
            tmaname = 'TMA' + str(tma)
            tmacrit= (df_sl['sl_console']==tmaname)
            tmatime = df_sl.loc[tmacrit]['sl_time']
            tmaRTs = [x-y for x, y in zip(tmatime[1:], tmatime)]
            tmaRTs.insert(0,df_sl.loc[tmacrit]['sl_RT'].iloc[0]) # Add in the first RT  
            df_sl.loc[tmacrit,'sl_tmaRT'] = tmaRTs
        # Time since this contact was last updated    
        for ts_id in ts_all_cons:
            tstmacrit = (df_sl['sl_ts_id']==ts_id) & df_sl['sl_console'].str.contains("TMA")
            updatetime = df_sl.loc[tstmacrit]['sl_time']
            if len(updatetime) > 1:
                tsRTs = [x-y for x, y in zip(updatetime[1:], updatetime)]
                tsRTs.insert(0,np.nan) # Add in the first RT              
                df_sl.loc[tstmacrit,'sl_updateRT'] = tsRTs
            df_sl.loc[tstmacrit,'sl_contact_SLcount'] = range(1,len(updatetime)+1)
  
           
# 12. Save sonar data
        
        # Get sonar detection detection speed
        df_soncols = ['son_time','son_ts_id']
        df_son = pd.DataFrame(np.nan,index = [], columns = df_soncols)
        for ts_id in ts_all_cons:
            if df_sl.loc[(df_sl.loc[:,'sl_ts_id']==ts_id)].shape[0] == 0:
                print('*** FLAG *** Contact not detected: TS ' + str(ts_id) + '\n')
                flagfile.write('*** FLAG *** Contact not detected: TS ' + str(ts_id) + '\n')
            else:                
                sl_id = df_sl.loc[(df_sl.loc[:,'sl_ts_id']==ts_id),'sl_first_sid'].iloc[0]
                slsoncrit = df_sl['sl_console'].str.contains("SONAR") & (df_sl['sl_ts_id']==ts_id)
                stcrit = (df_st['st_parent_scid']== sl_id)
                if df_sl[slsoncrit].shape[0] > 0:
                    df_son.loc[ts_id,'son_time'] = df_sl[slsoncrit]['sl_time'].iloc[0]
                    df_son.loc[ts_id,'son_ts_id'] = ts_id
                    df_son.loc[ts_id,'son_onset_time'] = df_sst.loc[(df_sst.loc[:,'Con']==ts_id),'Time'].iloc[0]
                    df_son.loc[ts_id,'son_SCID_detect_time'] = df_sl[slsoncrit]['sl_SCID_detect_time'].iloc[0]
                    df_son.loc[ts_id,'son_SCID_RT'] = df_son.loc[ts_id,'son_SCID_detect_time'] - df_son.loc[ts_id,'son_onset_time'] 
                    if df_st[stcrit].shape[0] > 0:
                        df_son.loc[ts_id,'son_TID_detect_time'] = df_sl[slsoncrit]['sl_TID_detect_time'].iloc[0]
                        df_son.loc[ts_id,'son_TID_RT'] = df_son.loc[ts_id,'son_TID_detect_time'] - df_son.loc[ts_id,'son_onset_time'] 
                        df_son.loc[ts_id,'son_console'] = df_st[stcrit]['st_owner'].iloc[0]            
                    if df_son.loc[ts_id,'son_TID_RT'] < 0:
                            print('*** FLAG *** Sonar detect time faster than 0')
                            flagfile.write('*** FLAG *** Sonar detect time faster than 0\n')
            
           
    
# 13. Save original data then remove remove outliers                       
                         
        # Save all data include sonar solutions and outliers
        df_son.to_csv('son_%s.csv' % condition_label)
        df_sl.to_csv('sl_all_%s.csv' % condition_label)
        
        df_sl['sl_team']= team
        df_sl['sl_session'] = session
        df_sl['sl_integ'] = integration_condition
        df_sl['sl_scen'] = scenario_num       
        
        # 11.  Combine data across teams
        if firstcompleted == 0:
            df_sl_all_allscenarios = df_sl.copy()
        else:
            df_sl_all_allscenarios = df_sl_all_allscenarios.append(df_sl)
        
        # Now remove sonar solutions from SL to leave only solutions set by TMA
        if 'sl_console' in df_sl.columns: # early versions did not include sonar solutions
            df_sl = df_sl[df_sl['sl_console'].str.contains("TMA")].copy()
            
        
        # Bearig error outliers
        bearcrit = (df_sl['sl_bearingError'] <= bearing_error_max)
        if df_sl['sl_bearingError'].max() > bearing_error_max:
            outbears = list(df_sl.loc[~bearcrit]['sl_bearingError'])
            flagfile.write('*** FLAG *** Bearing error outside max: ' + str(outbears) + '\n')
            bearerrFlag += len(outbears)
        if exclude_bearing_outliers:
            df_sl = df_sl.loc[bearcrit].copy()
        
        # Remove RT outliers
        RTcrit = (df_sl['sl_tmaRT'] >= minRT) 
        if df_sl['sl_tmaRT'].min() < minRT:
            outRTs = list(df_sl.loc[~RTcrit]['sl_tmaRT'])
            flagfile.write('*** FLAG *** Faster solution RT: ' + str(outRTs) + '\n')
            rtFlag += len(outRTs)
        if exclude_RT_outliers:
            df_sl = df_sl.loc[RTcrit].copy()
            
        # Save final solution data
        df_sl = df_sl.reset_index(drop=True)
        df_sl.to_csv('sl_sonaroutliers_%s.csv' % condition_label) 
            
        # Sonar outliers
        rangecrit = (df_sl['sl_range'] <= sonar_range)
        if df_sl['sl_range'].max() > sonar_range: #If at least one outside range
            outranges = list(df_sl.loc[~rangecrit]['sl_range'])
            print('*** FLAG *** Solutions outside sonar range: ' + str(outranges) + '\n')
            flagfile.write('*** FLAG *** Solutions outside sonar range: ' + str(outranges) + '\n')
            rangeFlag += len(outranges)
        if exclude_sonar_outliers:
            df_sl = df_sl.loc[rangecrit].copy()           

# Save final solution data
        df_sl = df_sl.reset_index(drop=True)
        df_sl.to_csv('sl_%s.csv' % condition_label) 
        
        # 11.  Combine data across teams
        if firstcompleted == 0:
            df_sl_allscenarios = df_sl.copy()
            firstcompleted = 1
        else:
            df_sl_allscenarios = df_sl_allscenarios.append(df_sl)
        
os.chdir(data_directory)        
#df_sl_allscenarios.to_csv('SL_allscenarios.csv') 
#df_sl_all_allscenarios.to_csv('SL_all_allscenarios.csv') 
       
flagfile.close()      

print('Finished code')

        
