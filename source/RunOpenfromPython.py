# -*- coding: utf-8 -*-
"""
Created on Mon Jun 29 13:14:58 2020

@author: pfernandez
"""

import os
import comtypes.client as cc
# import csv
import matplotlib.pyplot as plt
import numpy as np
import time
import matplotlib.dates as mdates

start = time.time()

n = 96 # 
sz= str(60*24/n) # stepsize

#Parameters to change
circuit = 'abham'
firstLine ='ALIAS-360070-C_BorderNode'
# firstLine ='ALIAS-1506694-U'

voltagebases = str([0.120, 0.208, 0.240, 0.416, 0.480, 13.8, 33, 132, 230, 400])

#%% DSS file path
filespath = os.path.dirname(os.path.abspath(__file__))
DSS_file_name = f'{circuit}_master.dss'

###############################################################################
#%%
# #############################################################################
# ######################%% Initialize COM cowithn OpenDSS ###########
# #############################################################################
DSSobj = cc.CreateObject("OpenDSSEngine.DSS")
DSSstart = DSSobj.Start(0)
DSStext = DSSobj.Text
DSScircuit = DSSobj.ActiveCircuit
DSSTransformers = DSScircuit.Transformers

###############################################################################
####################%% Initialize OpenDSS ######################
###############################################################################

DSStext.Command = 'Clear' 
DSS_file_name = f'{circuit}_Master.dss'   
# RP.write_on_dss(DSStext, loadshapes, loads_edit) 
DSStext.Command = f'Compile "{os.path.join(filespath , DSS_file_name)}"'
#
#DSStext.Command = 'redirect '+ os.path.join(DSS_filespath , 'Monitors_final.dss') 
DSStext.Command = 'Set mode = daily'  
DSStext.Command = 'Set number= 1' 
DSStext.Command = 'Set stepsize='+sz+'m'  
DSStext.Command = 'Set time=(0,0)' 
DSStext.Command = 'Set VoltageBases = '+voltagebases
DSStext.Command = 'CalcVoltageBases'
# DSStext.Command = 'New Monitor.HVMV_PQ_vs_Time Vsource.' + firstLine + ' terminal = 2 Mode=1 ppolar=0'  

#%% 


Potencias=[]
# Losses
lossesWList = list() 

# current simulation powers
temp_powersP = []
temp_powersQ = []

index = list(DSScircuit.AllNodeNames)

voltages=[]

for i in range(n): 

    DSScircuit.Solution.Solve() 
    
    #Extracting first line powers
    DSScircuit.setActiveElement('Vsource.' + firstLine)
    temp_powers = DSScircuit.ActiveElement.Powers  
    temp_powersP.append(-1*(temp_powers[2] + temp_powers[4] + temp_powers[0]))
    temp_powersQ.append(-1*(temp_powers[3] + temp_powers[5] + temp_powers[1]))
    
    lossesWList.append(DSScircuit.Losses[0] / 1000)
    
    #Buses names   
    if i == 0:
        names= list(DSScircuit.AllNodeNames)
    else: pass

    #Extracting all voltages in each time instant
    voltages.append(list(DSScircuit.AllBusVmagPU))


# ############################################################
# ############################################################

# ###### Hour format for x axis ##########
import datetime as dt
hours = mdates.drange(dt.datetime(2015, 1, 1), dt.datetime(2015, 1, 2), dt.timedelta(minutes=15))
fmtr = mdates.DateFormatter("%H:%M")


#%%
# # ##################################################
# # ###   Plots ###
# # ##################################################
   
# Voltage progile
fig1 = plt.figure(1)
ax = plt.gca()

for b in range(len(voltages[0])):    
    ax.plot(hours, list(zip(*voltages))[b])
        
ax.xaxis.set_major_formatter(fmtr)
ax.set_xlabel('Hour')
ax.set_ylabel('V')
#ax.set_ylim([0.9565, 0.9569])
# ax.set_ylim([0.9965, 1.00569])
ax.legend()
ax.set_title('Voltage profile - ' + circuit)

#%%
# Demand profile

fig2 = plt.figure(2)
ax = plt.gca()
ax.plot(hours, temp_powersP, label='P')
# ax.plot(hours, temp_powersQ, label='Q')
ax.xaxis.set_major_formatter(fmtr)
ax.set_xlabel('Hour')
ax.set_ylabel('kW')
ax.legend()
ax.set_title('Daily power flow - ' + circuit)

