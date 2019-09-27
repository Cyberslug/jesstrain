# -*- coding: utf-8 -*-
"""
Created on Fri Apr 13 2019

- OSPA-inspired method 1 for calculating position error
- Includes cardinality penalty: receive max PE for any contacts that have not yet been given a solution and any extra solutions on same ground truth
- Uses max threshold on PE: PE cannot exceed this, and this is the penality applied for contacts without solutions
- No penalty for extra contacts

@author: ironsj
"""
import numpy as np
import pandas as pd
import os
import analysis_tools

# Maximum PE threshold
ospa_c = 10000

# User parameters
teams = range(17,17+1) # Teams list
sessions = range(1,2+1) # Sessions per team
endtime = 3700  # total number of seconds to look at
firstcompleted = 0
jiteams = [1,2,6,9,10,15]

condcols = ['Team','Session','Integration', 'Configuration']  
maindir = ('\\\\homes-stl\\home1\\ironsj\\Documents\\CRUSE\\Experiment 1 Integration & Config study\\Data')
#maindir = ('\\\\homes-stl\\home1\\ironsj\\Documents\\CRUSE\\Experiment 1 Integration & Config study\\Data')
os.chdir(maindir)
df_condlist = pd.read_csv('condlist.csv')
df_sst = pd.read_csv('Sonar_start_time.csv') # Get sonar start times
  
# Set up variables used for all analysis
tpdur = 20 # number of seconds per time point
tpnum = int(endtime/tpdur)
ypm = 33.756 # Yards per minute travelling at 1 knot = 33.756
pointsrange = .5 # Solution must be within this proportion of range in order # to score a point
zigdegrees = 30 # How many degrees change in course to qualify for a zig
sonarrange = 30000 # Max range for detection (as told to participants)
bearerrmax = 20 # bearing errors outside of this considered outliers
minRT = 10 # minimum allowable time since last solution 
consoles = ['SONAR1','SONAR2','PERISCOPE','TMA1','TMA2','TPC']
# Weights from highest 3 to lowest 10 
classweightdict = {'Warship':3,'Fishing':2,'Merchant':1, 'Merchant B':1,'Merchant C':1} 
rangeweightdict = {5000:3,10000:2,15000:1}
courseweightdict = {'Closing':3,'Opening':1}
zigweightdict = {'Zigging':3,'Notzigging':1}
                    
for team in teams:
    for session in sessions:
        
        print('Team ' + str(team))
        print('Session ' + str(session))
        
        clcrit = (df_condlist['Team']==team) & (df_condlist['Session']==session)
        datafolder = df_condlist[clcrit]['Directory'].iloc[0]
        intcond = df_condlist[clcrit]['Integration'].iloc[0]
        configcond = df_condlist[clcrit]['Configuration'].iloc[0]
        scennum = str(df_condlist[clcrit]['Scenario'].iloc[0])
        condlabel = intcond + '_' + configcond + '_' + scennum
        datadir = (maindir + r'\Team ' + str(team) + '\\' + datafolder)
        os.chdir(datadir)
        
        # Import necessary files into dataframes
        df_sl_all = pd.read_csv('sl_all_%s.csv' % condlabel) # SL generated by 
### CHANGE for this version, keep in the range outliers (will hit the PE threshold)
        df_sl = pd.read_csv('sl_%s.csv' % condlabel) # All solutions entered. Includes initial solution set by sonar
        df_sl_out = pd.read_csv('sl_sonaroutliers_%s.csv' % condlabel) # All solutions entered. Includes initial solution set by sonar
        df_sol = pd.read_csv('solution.csv') # Indicates whether extra solutions were deleted
        df_ts = pd.read_csv('target_solution.csv') # Ground truth for every vessel every 20s
        df_nav = pd.read_csv('navdata.csv') # Ownship nagivation data. Updated every 1s
        df_cn = pd.read_csv('contacts.csv') # Contact timing info
        df_eh = pd.read_csv('entity_history.csv') # Included sonar tracker data
        df_st = pd.read_csv('sonar_tracks.csv') # Sonar TID and SCID initiation
        df_ann = pd.read_csv('annotations.csv') # TPC and Sonar annotations
        df_atw = pd.read_csv('atwit.csv') # atwit scores
        df_atw[df_atw.aw_console != 'COMMAND'] # remove rows from console "command" 
        df_atw['aw_workload'] = df_atw['aw_workload'].replace(999,np.NaN) # replace 999 with NA
        df_atw['aw_zulu'] = np.floor(df_atw['aw_zulu']/100)*100 # Do this to round any atwit times that are too slow
        
        
        ts_all_cons = pd.unique(df_ts['ts_id']) 
        ts_all_n = ts_all_cons.size   #total number of contacts listed in TS, including those not yet detected
        sl_all_cons = pd.unique(df_sl_all['sl_sid']) 
        outlierPE = 0 # Used to count how many PEs hit the ospa_c threshold
        nonoutlierPE = 0 

### 1. Get X/Y Coords over time
        
        df_tsslcols = ['tssl_ts_id','tssl_sl_id','tssl_time','tssl_ownship_x','tssl_ownship_y','tssl_detected','tssl_solution','tssl_solutionCount','tssl_sl_x','tssl_sl_y','tssl_ts_range','tssl_ts_x','tssl_ts_y','tssl_PE','tssl_class_weight','tssl_range_weight','tssl_course_weight','tssl_zig_weight']
        df_tssl = pd.DataFrame(np.nan,index = [0], columns = df_tsslcols)
        
        tssl = 0
        # for each ground truth contact
        for ts_id in ts_all_cons:
            tscrit = (df_sl_out['sl_ts_id']==ts_id)
            tscritall = (df_sl_all['sl_ts_id']==ts_id) # Solutions submitted by sonar and TMA
            sl_c = 0 # solution count for each contact
            zigweight = zigweightdict.get('Notzigging', "none")
            prevcourse = 0
            prevspeed = 0
            extrapenalty = 0 # whether or not there is an extra solution
            
            # if contacted detected by sonar 
            if df_sl_all[tscritall].shape[0] > 0:    
                detecttime_ts = df_sl_all[tscritall]['sl_time'].iloc[0] # get first time detected for all contacts, including those without SLs
                classweight = classweightdict.get(df_sl_all.loc[tscritall,'sl_ts_classification'].iloc[0], "none")
            else:
                detecttime_ts = 999999 # if not detected, set to arbitrarily long number
                
            for tp in range(0,tpnum+1):
                tp_time = tp*tpdur
                df_tssl.loc[tssl,'tssl_ts_id'] = ts_id 
                df_tssl.loc[tssl,'tssl_time'] = tp_time 
                
                # Get ownship data
                navcrit = (df_nav['nd_time']==tp_time)
                df_tssl.loc[tssl,'tssl_ownship_x'] = df_nav[navcrit]['nd_x'].iloc[0]
                df_tssl.loc[tssl,'tssl_ownship_y'] = df_nav[navcrit]['nd_y'].iloc[0]   
                
                tstpcrit = ((df_ts['ts_id']==ts_id) & (df_ts['ts_time']==tp_time))                 
                
# 2. Get ground truth data
                # Contact detected by sonar yet?
                if (tp_time >= detecttime_ts):
                    df_tssl.loc[tssl,'tssl_detected'] = 1
### CHANGE: Set default PE, update later if there's a solution
                    df_tssl.loc[tssl,'tssl_PE'] = ospa_c 
                    
                    # Get TS data    
                    df_tssl.loc[tssl,'tssl_ts_range'] = df_ts[tstpcrit]['ts_range'].iloc[0]
                    df_tssl.loc[tssl,'tssl_ts_x'] = df_ts[tstpcrit]['ts_x'].iloc[0]
                    df_tssl.loc[tssl,'tssl_ts_y'] = df_ts[tstpcrit]['ts_y'].iloc[0]   # Get x/y data etc            

# 3. Assign weights for each timepoint (within the get x/y loop)
                    # Classification
                    df_tssl.loc[tssl,'tssl_class_weight'] = classweight
                        
                    # Range
                    rangebin = np.ceil(df_ts[tstpcrit]['ts_range'].iloc[0]/next(iter(rangeweightdict)))*next(iter(rangeweightdict)) # Divides by the smallest range, rounds to the ceiling, then multiplies by the smallest range
                    df_tssl.loc[tssl,'tssl_range_weight'] = rangeweightdict.get(rangebin, 1) # Alternative is 1 = range larger than used here
                
                    # Course (Closing = positive timeCPA, opening = negative timeCPA)
                    if df_ts[tstpcrit]['ts_timecpa'].iloc[0] > 0:
                        df_tssl.loc[tssl,'tssl_course_weight'] = courseweightdict.get('Closing', "none")
                    else: 
                        df_tssl.loc[tssl,'tssl_course_weight'] = courseweightdict.get('Opening', "none")
                    
                    # Zig:
                    if (zigweight == 1) & (prevcourse > 0) & (prevspeed > 1):   # Only do it if the previous speed is greater than 1: sometimes contacts will be not moving on the outskirts, could be wrongly taken as a zig 
                        # Once changed, don't change again (once a zigging vessel, always a zigging vessel)
                        coursechange = bearingError(df_ts[tstpcrit]['ts_course'].iloc[0], prevcourse)
                        if coursechange > zigdegrees:
                            zigweight = zigweightdict.get('Zigging', "none")
                    df_tssl.loc[tssl,'tssl_zig_weight'] = zigweight
                    prevcourse = df_ts[tstpcrit]['ts_course'].iloc[0]        
                    prevspeed = df_ts[tstpcrit]['ts_speed'].iloc[0]
  
### CHANGE include product weight                          
                    # Summed & Product weight
                    df_tssl.loc[tssl,'tssl_sum_weight'] = df_tssl.loc[tssl,'tssl_class_weight'] + df_tssl.loc[tssl,'tssl_range_weight'] + df_tssl.loc[tssl,'tssl_course_weight'] + df_tssl.loc[tssl,'tssl_zig_weight']
                    df_tssl.loc[tssl,'tssl_product_weight'] = df_tssl.loc[tssl,'tssl_class_weight'] * df_tssl.loc[tssl,'tssl_range_weight'] * df_tssl.loc[tssl,'tssl_course_weight'] * df_tssl.loc[tssl,'tssl_zig_weight']
         
# 4. Get solution data                
                    # Solution lodged yet?    
                    if (df_sl_out[tscrit].shape[0] > 0): # If any solution
                        if (tp_time >= df_sl_out[tscrit]['sl_post_time'].iloc[0]): # If the first solution submitted
                            # Solution x/y    
                            if (sl_c < df_sl_out[tscrit].shape[0]): # if there are new solutions to come
                                if (df_sl_out[tscrit]['sl_post_time'].iloc[sl_c] == tp_time): # if new solution has just been submitted
                                    sl_id = df_sl_out[tscrit]['sl_sid'].iloc[sl_c]
                                    # Update x/y from solution start time
                                    sl_startx = df_sl_out[tscrit]['sl_x'].iloc[sl_c].copy()
                                    sl_starty = df_sl_out[tscrit]['sl_y'].iloc[sl_c].copy()
                                    sl_course = df_sl_out[tscrit]['sl_course'].iloc[sl_c].copy()
                                    sl_speed = df_sl_out[tscrit]['sl_speed'].iloc[sl_c].copy()
                                    sl_timediff = tp_time - df_sl_out[tscrit]['sl_time'].iloc[sl_c].copy()
                                    sl_newx = sl_startx + np.sin(np.deg2rad(sl_course)) * (ypm * (sl_timediff/60) * sl_speed);
                                    sl_newy = sl_starty + np.cos(np.deg2rad(sl_course)) * (ypm * (sl_timediff/60) * sl_speed);
                                    # Update for next solution
                                    sl_c = sl_c + 1
                                else:
                                    # Update from last timepoint
                                    sl_newx = sl_newx + np.sin(np.deg2rad(sl_course)) * (ypm * (tpdur/60) * sl_speed);
                                    sl_newy = sl_newy + np.cos(np.deg2rad(sl_course)) * (ypm * (tpdur/60) * sl_speed);
                            else:
                                # Update from last timepoint
                                sl_newx = sl_newx + np.sin(np.deg2rad(sl_course)) * (ypm * (tpdur/60) * sl_speed);
                                sl_newy = sl_newy + np.cos(np.deg2rad(sl_course)) * (ypm * (tpdur/60) * sl_speed);
                                
                            df_tssl.loc[tssl,'tssl_solution'] = 1
                            df_tssl.loc[tssl,'tssl_solutionCount'] = sl_c
                            df_tssl.loc[tssl,'tssl_sl_id'] = sl_id
                            df_tssl.loc[tssl,'tssl_sl_x'] = sl_newx
                            df_tssl.loc[tssl,'tssl_sl_y'] = sl_newy
                            df_tssl.loc[tssl,'tssl_PE'] = min(ospa_c, positionError(df_tssl.loc[tssl,'tssl_ts_x'], sl_newx, df_tssl.loc[tssl,'tssl_ts_y'], sl_newy))
                            if df_tssl.loc[tssl,'tssl_PE'] == ospa_c: # Count how frequently PE hits the threshold to decide if it's too small/large
                                outlierPE += 1
                            else:
                                nonoutlierPE += 1
                            
### CHANGE: use either position error or max threshold, whichever is smaller
# Calculate other versions of PE (if detected)
                    df_tssl.loc[tssl,'tssl_PEoverRange'] = df_tssl.loc[tssl,'tssl_PE'] / df_tssl.loc[tssl,'tssl_ts_range'] 
                    df_tssl.loc[tssl,'tssl_InversePEoverRange'] = 1 - df_tssl.loc[tssl,'tssl_PEoverRange'] # Subtract from 1 to make higher scores = better
                # row counter for TSSL
                tssl += 1
            
        
# 5. calculate weights as % of all current weights  
        for tp, row in df_tssl.iterrows():
            tp_time = df_tssl.loc[tp,'tssl_time']
            tsslcrit= (df_tssl['tssl_time']==tp_time) & (df_tssl['tssl_detected']==1)
            totalweighttp = df_tssl[tsslcrit]['tssl_sum_weight'].sum()
            totalproductweighttp = df_tssl[tsslcrit]['tssl_product_weight'].sum()
            df_tssl.loc[tp,'tssl_tpsumweight'] = totalweighttp
            df_tssl.loc[tp,'tssl_tpproductweight'] = totalproductweighttp
            
            if df_tssl.loc[tp,'tssl_detected'] == 1:
                df_tssl.loc[tp,'tssl_percent_weight'] = df_tssl.loc[tp,'tssl_sum_weight']/totalweighttp
                df_tssl.loc[tp,'tssl_percent_prodweight'] = df_tssl.loc[tp,'tssl_product_weight']/totalproductweighttp
                
                
        df_tssl.loc[:,'tssl_PE_percentweighted'] = df_tssl.loc[:,'tssl_PE'] * df_tssl.loc[:,'tssl_percent_weight'] 
        df_tssl.loc[:,'tssl_PEoverRange_percentweighted'] = df_tssl.loc[:,'tssl_PEoverRange'] * df_tssl.loc[:,'tssl_percent_weight'] 
        df_tssl.loc[:,'tssl_InversePEoverRange_percentweighted'] = df_tssl.loc[:,'tssl_InversePEoverRange'] * df_tssl.loc[:,'tssl_percent_weight'] 
        df_tssl.loc[:,'tssl_PE_percentprodweighted'] = df_tssl.loc[:,'tssl_PE'] * df_tssl.loc[:,'tssl_percent_prodweight'] 
        df_tssl.loc[:,'tssl_PEoverRange_percentprodweighted'] = df_tssl.loc[:,'tssl_PEoverRange'] * df_tssl.loc[:,'tssl_percent_prodweight'] 
        df_tssl.loc[:,'tssl_InversePEoverRange_percentprodweighted'] = df_tssl.loc[:,'tssl_InversePEoverRange'] * df_tssl.loc[:,'tssl_percent_prodweight'] 
        
        # Assign a point based on whether it's within range or not, and weight the point by the percent weight
        df_tssl.loc[:,'tssl_PEoverRange_points'] = df_tssl.loc[:,'tssl_PEoverRange'] < pointsrange # True or false for point or not
        df_tssl.loc[:,'tssl_PEoverRange_points_percentweighted'] = df_tssl.loc[:,'tssl_PEoverRange_points'] * df_tssl.loc[:,'tssl_percent_weight'] 
        df_tssl.loc[:,'tssl_PEoverRange_points_prodpercentweighted'] = df_tssl.loc[:,'tssl_PEoverRange_points'] * df_tssl.loc[:,'tssl_percent_prodweight'] 
        
# 6. Update zig weight in SL doc
        for sl, row in df_sl.iterrows():
            tsslcrit =  (df_tssl['tssl_time']==df_sl.loc[sl,'sl_prior_time']) & (df_tssl['tssl_ts_id']==df_sl.loc[sl,'sl_ts_id']) 
            df_sl.loc[sl,'sl_zig_weight'] = df_tssl[tsslcrit]['tssl_zig_weight'].iloc[0]
            # Sum weight
            df_sl.loc[sl,'sl_sum_weight'] = df_sl.loc[sl,'sl_class_weight'] + df_sl.loc[sl,'sl_range_weight'] + df_sl.loc[sl,'sl_course_weight'] + df_sl.loc[sl,'sl_zig_weight']
            
   
# 7. Combine across all contacts for each timepoints
        df_tssltpcols = ['tp_time','tp_detectedCount','tp_contactsWithSolutions','tp_solutionCount']
        df_tssltp = pd.DataFrame(np.nan,index = [0], columns = df_tssltpcols)
        
        for tp in range(0,tpnum+1):
            tp_time = tp*tpdur
            tsslcrit = (df_tssl['tssl_time']==tp_time)
            df_tssltp.loc[tp,'tp_time'] = tp_time
            df_tssltp.loc[tp,'tp_detectedCount'] = df_tssl[tsslcrit]['tssl_detected'].sum()
            df_tssltp.loc[tp,'tp_contactsWithSolutions'] = df_tssl[tsslcrit]['tssl_solution'].sum()
            df_tssltp.loc[tp,'tp_solutionCount'] = df_tssl[tsslcrit]['tssl_solutionCount'].sum()
### CHANGE: Calculate this for any detected contact, even if no solutions on them
            if df_tssltp.loc[tp,'tp_detectedCount'] > 0: # Only calculate this for rows with a solution
                df_tssltp.loc[tp,'tp_meanPE'] = df_tssl[tsslcrit]['tssl_PE'].mean()
                df_tssltp.loc[tp,'tp_meanPEoverRange'] = df_tssl[tsslcrit]['tssl_PEoverRange'].mean()
                #df_tssltp.loc[tp,'tp_totalweightedPE'] = np.nansum(df_tssl[tsslcrit]['tssl_PE']*df_tssl[tsslcrit]['tssl_sum_weight'])    
                df_tssltp.loc[tp,'tp_weightedPE'] = np.nansum(df_tssl[tsslcrit]['tssl_PE_percentweighted'])
                df_tssltp.loc[tp,'tp_prodweightedPE'] = np.nansum(df_tssl[tsslcrit]['tssl_PE_percentprodweighted'])
                df_tssltp.loc[tp,'tp_prodweightedPE_points'] = np.nansum(df_tssl[tsslcrit]['tssl_PEoverRange_points_prodpercentweighted'])
                df_tssltp.loc[tp,'tp_totalrangepoints'] = np.nansum((df_tssl[tsslcrit]['tssl_PE']/df_tssl[tsslcrit]['tssl_ts_range']) < pointsrange)
                df_tssltp.loc[tp,'tp_meanrangepoints'] = df_tssltp.loc[tp,'tp_totalrangepoints']/df_tssl[tsslcrit]['tssl_detected'].sum()               
        
        # Add ATWIT to TSSLtp
        # Get most recently completed atwit
            atw_start_time = np.floor(tp_time/300)*300
            atw_end_time =atw_start_time + 300
            if atw_start_time >= 300:
                for console in consoles:
                    atwcrit = (df_atw['aw_zulu']>=atw_start_time) & (df_atw['aw_zulu']<atw_end_time) & (df_atw['aw_console']==console)
                    colname = 'tp_atw_' + console
                    df_tssltp.loc[tp,colname] = df_atw.loc[atwcrit]['aw_workload'].iloc[0]
                df_tssltp.loc[tp,'tp_atw_all'] = (df_tssltp.loc[tp,'tp_atw_SONAR1'] + df_tssltp.loc[tp,'tp_atw_SONAR2'] + df_tssltp.loc[tp,'tp_atw_PERISCOPE'] + df_tssltp.loc[tp,'tp_atw_TMA1'] + df_tssltp.loc[tp,'tp_atw_TMA2'] + df_tssltp.loc[tp,'tp_atw_TPC'])/6
                if team in jiteams:
                    df_tssltp.loc[tp,'tp_atw_all_exclJI'] = (df_tssltp.loc[tp,'tp_atw_SONAR1'] + df_tssltp.loc[tp,'tp_atw_PERISCOPE'] + df_tssltp.loc[tp,'tp_atw_TMA1'] + df_tssltp.loc[tp,'tp_atw_TMA2'] + df_tssltp.loc[tp,'tp_atw_TPC'])/5
                else:
                    df_tssltp.loc[tp,'tp_atw_all_exclJI'] = df_tssltp.loc[tp,'tp_atw_all']
        #df_sl.to_csv('sl_%s.csv' % condlabel) 
        
 # 8. Save all data   
        
        df_sl.to_csv('sl_%s.csv' % condlabel) 
        df_tssl.to_csv('tssl_OI3_%s.csv' % condlabel) 
        df_tssltp.to_csv('tssltp_OI3_%s.csv' % condlabel)

print('Finished code')
