# -*- coding: utf-8 -*-
"""
Created on Mon Apr 13 06:24:03 2020

@authors: Pablo Fernandez and Roger Gonzalez

CIM/UK to OpenDSS converter


"""
   
from lxml import etree
# import pandas as pd
from timeit import default_timer as timer
import re
import logging
 
# Create and configure logger
logging.basicConfig(filename="CIMReport.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
 
# Creating an object
logger = logging.getLogger()
 
# Setting the threshold of logger to DEBUG
logger.setLevel(logging.DEBUG)


#Conversion dictionaries
getPhases = {'ABC': '.1.2.3', 'A': '.1', 'B': '.2','C': '.3', 'AB': '.1.2', 'AC': '.1.3', 'BC': '.2.3', 'AN': '.1.0', 'BN': '.2.0','CN': '.3.0'}
noPhases = {'ABC': '3', 'A': '1', 'B': '1','C': '1', 'AB': '2', 'AC': '2', 'BC': '2', 'AN': '1', 'BN': '1','CN': '1'}
conections = {'D':'delta','Yn':'wye','Y':'wye'}

#Cleaning string to avoid OpenDSS troubles
def cleanString(string):
    return re.sub('\W+','-', string).replace(" ", "")

def nonZerovalue(string):
    if float(string) == 0.0:
        v = '0.1'        
    else:
        v = string
    return v



start = timer()

"""
############################################################
############################################################
############################################################
############################################################
############################################################
############################################################
"""

#Loading .xml

# filename = "cgmes_306004_abham_sgp_2021_10_18_11.08.38.xml"

filename = "cgmes_306004_abham_sgp_2022_02_05_12.46.35.xml"

tree = etree.parse(filename)


# root = tree_gl.getroot()

# PP_nodes = []

# for child in root:
   
    
#     if 'PositionPoint' in child.tag:
#         #Saving ACline segments nodes:           
#         PP_nodes.append(child)

#%%
name = filename.split('_')[2]

#Getting tree of xml file
root = tree.getroot()

#Defining namespaces
namespace = root.nsmap
cim = '{'+namespace['cim']+'}'
rdf = '{'+namespace['rdf']+'}'
md = '{'+namespace['md']+'}'

#Classifying nodes. BaseVoltage and Connectivity nodes have only 1 attribute useful so they are saved directly as dictionaries
AClines_nodes = []
PowerTransformers = []
Switches = []
BaseVoltage = {}
Terminal_nodes = {}
Terminal_CondEquip = {}
CN_names= {}
# CN_containers= {}
Energy_consumer = {}
Equivalent_injection = {}

u = set()

childTags=[]

#Splitting xml by useful child tags
for child in root:
    childTags.append(child.tag)
    
    if 'ACLineSegment' in child.tag:
        #Saving ACline segments nodes:           
        AClines_nodes.append(child)
        
    if 'Breaker' in child.tag or 'Disconnector' in child.tag or 'LoadBreakSwitch' in child.tag or 'Switch' in child.tag or 'SeriesCompensator' in child.tag or 'GroundDisconnector' in child.tag:
        #Saving all switches nodes:           
        Switches.append(child)
    
    if 'BaseVoltage' in child.tag:
        #Getting base voltages            
        BaseVoltage['#'+child.attrib.get(rdf+'ID')]={} 
        BaseVoltage['#'+child.attrib.get(rdf+'ID')]=child.findtext(cim+'BaseVoltage.nominalVoltage', default = 'None')
    
    if 'Terminal' in child.tag:        
        Terminal_nodes[child.attrib.get(rdf+'ID')] = child
        Terminal_CE_name = child.find(cim+'Terminal.ConductingEquipment').attrib.get(rdf+'resource')
        if Terminal_CE_name in Terminal_CondEquip:
            Terminal_CondEquip[Terminal_CE_name+'b'] = {}
            Terminal_CondEquip[Terminal_CE_name+'b']['child'] = child 
        else:
            Terminal_CondEquip[Terminal_CE_name] = {}
            Terminal_CondEquip[Terminal_CE_name]['child'] = child        
        
    if 'ConnectivityNode' in child.tag:  
        CN_names['#'+child.attrib.get(rdf+'ID')] = {}
        CN_names['#'+child.attrib.get(rdf+'ID')] = child.attrib.get(rdf+'ID')
        #CN_names['#'+child.attrib.get(rdf+'ID')] = child.findtext(cim+'IdentifiedObject.name', default = 'None')
        # CN_containers[child.attrib.get(rdf+'ID')] = {}
        # CN_containers[child.find(cim+'ConnectivityNode.ConnectivityNodeContainer').attrib.get(rdf+'resource')] = child.findtext(cim+'IdentifiedObject.name', default = 'None')
        
    if 'EnergyConsumer' in child.tag:  
        Energy_consumer['#'+child.attrib.get(rdf+'ID')] = {}
        Energy_consumer['#'+child.attrib.get(rdf+'ID')] = child.findtext(cim+'IdentifiedObject.name', default = 'None')
        
    if 'EquivalentInjection' in child.tag:  
        Equivalent_injection['#'+child.attrib.get(rdf+'ID')] = {}
        Equivalent_injection['#'+child.attrib.get(rdf+'ID')] = child.findtext(cim+'IdentifiedObject.name', default = 'None')
    
    if 'PowerTransformerEnd' in child.tag:
            #Saving PowerTransformer segments nodes:           
            PowerTransformers.append(child)
    
      
#%%
"""
############################################################
             MASTER FILE
############################################################
""" 

master = [
'clear',
'new circuit.'+name,
'set defaultbasefrequency = 50',
'!Edit Vsource.Source BasekV=132 pu = 1.00 angle = 0 frequency = 50 phases = 3',
'redirect '+ name+ '_vsources.dss',
'redirect '+ name+ '_linecodes.dss',
'redirect '+ name+ '_lines.dss',
'redirect '+ name+ '_lines_f.dss',
'redirect '+ name+ '_lines_switches.dss',
'redirect '+ name+ '_transformers.dss',
'redirect Loadshapes.dss',
'redirect '+ name+ '_loads.dss'
]

with open(name + '_master.dss', 'w') as filehandle:
    for l in master:
        filehandle.write('%s\n' % l)  

"""
############################################################
             AC LINES
############################################################
"""      

lg = {}
AClines = {}
ACline_terminalsCN = {}
ACline_CNACL = {}
for ACline in AClines_nodes:
    #creating dict with each line info
    AClines[ACline.attrib.get(rdf+'ID')] = {}
    
    #Saving name and description
    AClines[ACline.attrib.get(rdf+'ID')]['IdentifiedObject.name'] = ACline.findtext(cim+'IdentifiedObject.name', default = 'None')
    AClines[ACline.attrib.get(rdf+'ID')]['IdentifiedObject.description'] = ACline.findtext(cim+'IdentifiedObject.description', default = 'None')
    
    #Saving voltage
    voltage=ACline.find(cim+'ConductingEquipment.BaseVoltage').attrib.get(rdf+'resource')
    AClines[ACline.attrib.get(rdf+'ID')]['ConductingEquipment.BaseVoltage'] = voltage
    
    #Saving X
    x=ACline.findtext(cim+'ACLineSegment.x', default = 'None')
    AClines[ACline.attrib.get(rdf+'ID')]['ACLineSegment.x'] = x
    
    #Saving Bch
    bch=ACline.findtext(cim+'ACLineSegment.bch', default = 'None')
    AClines[ACline.attrib.get(rdf+'ID')]['ACLineSegment.bch'] = bch
    
    #Saving R
    r=ACline.findtext(cim+'ACLineSegment.r', default = 'None')
    AClines[ACline.attrib.get(rdf+'ID')]['ACLineSegment.r'] = r
    
    #Saving Lenght
    AClines[ACline.attrib.get(rdf+'ID')]['Conductor.length'] = ACline.findtext(cim+'Conductor.length', default = 'None')
    
    #Creating Line Geometry from R, X, Bch and Voltage    
    AClines[ACline.attrib.get(rdf+'ID')]['Conductor.LineGeometry'] = '3P_'+r[0]+'_'+x[0]+'_'+bch[0]+'_'+BaseVoltage[voltage].split('.')[0]
    lg['3P_'+''+r[0]+'_'+x[0]+'_'+bch[0]+'_'+BaseVoltage[voltage]]={'type':'New linecode.'+'3P_'+''+r[0]+'_'+x[0]+'_'+bch[0]+'_'+
                                                                    BaseVoltage[voltage].split('.')[0]+' nphases=3 R1='+format(float(nonZerovalue(r)),
                                                                    '.10f')+' X1='+format(float(nonZerovalue(x)), '.10f')+' C1='+format(float(nonZerovalue(bch)), '.10f')} # to know unique LG
    
    #Adding terminals to each line segment
    terminal = Terminal_CondEquip['#'+ACline.attrib.get(rdf+'ID')]['child']
    terminal_b = Terminal_CondEquip['#'+ACline.attrib.get(rdf+'ID')+'b']['child']  
    for term in (terminal, terminal_b):
        
        t='T'+term.find(cim+'ACDCTerminal.sequenceNumber').text # to get T1 or T2 name
        
        #Creating dict for each terminal of line
        AClines[ACline.attrib.get(rdf+'ID')][t] = {}
        
        #Adding elements to dict name, phases and CN
        AClines[ACline.attrib.get(rdf+'ID')][t]['IdentifiedObject.name'] = term.findtext(cim+'IdentifiedObject.name', default = 'None')             
        AClines[ACline.attrib.get(rdf+'ID')][t]['Terminal.phases'] = term.find(cim+'Terminal.phases').attrib.get(rdf+'resource').split(".")[-1]
        AClines[ACline.attrib.get(rdf+'ID')][t]['Terminal.ConnectivityNode'] = term.find(cim+'Terminal.ConnectivityNode').attrib.get(rdf+'resource')
    
        #Saving terminals of AC line segments to be used in ficticious lines
        ACline_terminalsCN[term.find(cim+'IdentifiedObject.name').text]=term.find(cim+'Terminal.ConnectivityNode').attrib.get(rdf+'resource')
        ACline_CNACL[term.find(cim+'Terminal.ConnectivityNode').attrib.get(rdf+'resource')]=ACline.attrib.get(rdf+'ID')
        
#%  OpenDSS format              
lines=[]
for i in AClines:
    
    #if '_INM' in i:
        try:
            lines.append('new line.'+cleanString(AClines[i]['IdentifiedObject.name']) +
                         ' bus1='+ cleanString(CN_names[AClines[i]['T1']['Terminal.ConnectivityNode']])+
                         getPhases[AClines[i]['T1']['Terminal.phases']] +' bus2='+
                         cleanString(CN_names[AClines[i]['T2']['Terminal.ConnectivityNode']]) +
                         getPhases[AClines[i]['T2']['Terminal.phases']] + ' linecode=' + AClines[i]['Conductor.LineGeometry'] +
                         ' length=' + AClines[i]['Conductor.length'] + ' units=m !linekV='+BaseVoltage[AClines[i]['ConductingEquipment.BaseVoltage']]) 
        except Exception as e:
            logger.debug('Error during creation of ACline for OpenDSS ' + str(e))

with open(name + '_lines.dss', 'w') as filehandle:
    for l in lines:
        filehandle.write('%s\n' % l)  
        
with open(name + '_linecodes.dss', 'w') as filehandle:
    for l in lg:        
        filehandle.write('%s\n' % lg[l].get('type')) 
        
#%%        
###########################################################################################
###########################################################################################
#Switches matching with ACline terminals

AClines_switches = {}
AClines_switches_wo_line = []
counter = 0
for sw in Switches:
    AClines_switches[sw.attrib.get(rdf+'ID')] = {}
    
    #Saving name and normalOpen
    AClines_switches[sw.attrib.get(rdf+'ID')]['IdentifiedObject.name'] = sw.findtext(cim+'IdentifiedObject.name', default = 'None')
    
    try:
        AClines_switches[sw.attrib.get(rdf+'ID')]['Switch.normalOpen'] = sw.findtext(cim+'Switch.normalOpen', default = 'None')
    except:
        AClines_switches[sw.attrib.get(rdf+'ID')]['Switch.normalOpen'] = 'False'
    
    #Adding terminals to each switch
    terminal = Terminal_CondEquip['#'+sw.attrib.get(rdf+'ID')]['child']
    terminal_b = Terminal_CondEquip['#'+sw.attrib.get(rdf+'ID')+'b']['child']  
    for term in (terminal, terminal_b):
        
        t='T'+term.find(cim+'ACDCTerminal.sequenceNumber').text # to get T1 or T2 name
        
        #Creating dict for each terminal of line
        AClines_switches[sw.attrib.get(rdf+'ID')][t] = {}
        
        #Adding elements to dict name, phases and CN
        AClines_switches[sw.attrib.get(rdf+'ID')][t]['IdentifiedObject.name'] = term.findtext(cim+'IdentifiedObject.name', default = 'None')  
        AClines_switches[sw.attrib.get(rdf+'ID')][t]['Terminal.ConnectivityNode'] = term.find(cim+'Terminal.ConnectivityNode').attrib.get(rdf+'resource')
        
        #Some terminals do not have phase element
        try:
            AClines_switches[sw.attrib.get(rdf+'ID')][t]['Terminal.phases'] = term.find(cim+'Terminal.phases').attrib.get(rdf+'resource').split(".")[-1]
        except:
            AClines_switches[sw.attrib.get(rdf+'ID')][t]['Terminal.phases'] = 'ABC'
            # pass

    #Relating switch to adjacent line    
    if AClines_switches[sw.attrib.get(rdf+'ID')]['T1']['Terminal.ConnectivityNode'] in list(ACline_terminalsCN.values()):
        AClines_switches[sw.attrib.get(rdf+'ID')]['ConductingEquipment.BaseVoltage'] = AClines[ACline_CNACL[AClines_switches[sw.attrib.get(rdf+'ID')]['T1']['Terminal.ConnectivityNode']]]['ConductingEquipment.BaseVoltage']    
        AClines_switches[sw.attrib.get(rdf+'ID')]['Conductor.LineGeometry'] = AClines[ACline_CNACL[AClines_switches[sw.attrib.get(rdf+'ID')]['T1']['Terminal.ConnectivityNode']]]['Conductor.LineGeometry']
    elif AClines_switches[sw.attrib.get(rdf+'ID')]['T2']['Terminal.ConnectivityNode'] in list(ACline_terminalsCN.values()):
        AClines_switches[sw.attrib.get(rdf+'ID')]['ConductingEquipment.BaseVoltage'] = AClines[ACline_CNACL[AClines_switches[sw.attrib.get(rdf+'ID')]['T2']['Terminal.ConnectivityNode']]]['ConductingEquipment.BaseVoltage']      
        AClines_switches[sw.attrib.get(rdf+'ID')]['Conductor.LineGeometry'] = AClines[ACline_CNACL[AClines_switches[sw.attrib.get(rdf+'ID')]['T2']['Terminal.ConnectivityNode']]]['Conductor.LineGeometry']
    else:
        AClines_switches_wo_line.append(sw.attrib.get(rdf+'ID'))
    
    AClines_switches[sw.attrib.get(rdf+'ID')]['Conductor.length'] = '1' # default lenght 1m
    
linesf = []
linesf.extend(['','!Ficticious lines for switches',''])

for i in AClines_switches: 
    try:
                
        if AClines_switches[i]['Switch.normalOpen'] == 'false':
            linesf.append('new line.'+cleanString(AClines_switches[i]['IdentifiedObject.name']) +
                          ' bus1='+ cleanString(CN_names[AClines_switches[i]['T1']['Terminal.ConnectivityNode']])+ 
                          getPhases[AClines_switches[i]['T1']['Terminal.phases']] +' bus2='+
                          cleanString(CN_names[AClines_switches[i]['T2']['Terminal.ConnectivityNode']]) +
                          getPhases[AClines_switches[i]['T2']['Terminal.phases']] + ' linecode=' +
                          AClines_switches[i]['Conductor.LineGeometry'] + ' length=' +
                          AClines_switches[i]['Conductor.length'] + ' units=m !linekV='+BaseVoltage[AClines_switches[i]['ConductingEquipment.BaseVoltage']]) 
        else:
            linesf.append('!new line.'+cleanString(AClines_switches[i]['IdentifiedObject.name']) +
                          ' bus1='+ cleanString(CN_names[AClines_switches[i]['T1']['Terminal.ConnectivityNode']])+
                          getPhases[AClines_switches[i]['T1']['Terminal.phases']] +' bus2='+
                          cleanString(CN_names[AClines_switches[i]['T2']['Terminal.ConnectivityNode']]) +
                          getPhases[AClines_switches[i]['T2']['Terminal.phases']] + ' linecode=' +
                          AClines_switches[i]['Conductor.LineGeometry'] + ' length=' +
                          AClines_switches[i]['Conductor.length'] + ' units=m !linekV='+BaseVoltage[AClines_switches[i]['ConductingEquipment.BaseVoltage']]) 
    
    
    except Exception:
        pass

    
with open(name + '_lines_f.dss', 'w') as filehandle:
    for l in linesf:
        filehandle.write('%s\n' % l)                

#%%        
###########################################################################################
###########################################################################################
#Switches do not matching with ACline terminals

lines_switches = []
LS=[]
for i in AClines_switches_wo_line: 
    try:                
        if AClines_switches[i]['Switch.normalOpen'] == 'false':
            lines_switches.append('new line.'+cleanString(AClines_switches[i]['IdentifiedObject.name']) +
                                  ' bus1='+ cleanString(CN_names[AClines_switches[i]['T1']['Terminal.ConnectivityNode']])+
                                  getPhases[AClines_switches[i]['T1']['Terminal.phases']] +' bus2='+
                                  cleanString(CN_names[AClines_switches[i]['T2']['Terminal.ConnectivityNode']]) +
                                  getPhases[AClines_switches[i]['T2']['Terminal.phases']] + ' linecode=3P_0_0_0_33' + ' length=1'  + ' units=m ') 
        else:
            lines_switches.append('!new line.'+cleanString(AClines_switches[i]['IdentifiedObject.name']) +
                                  ' bus1='+ cleanString(CN_names[AClines_switches[i]['T1']['Terminal.ConnectivityNode']])+
                                  getPhases[AClines_switches[i]['T1']['Terminal.phases']] +' bus2='+
                                  cleanString(CN_names[AClines_switches[i]['T2']['Terminal.ConnectivityNode']]) +
                                  getPhases[AClines_switches[i]['T2']['Terminal.phases']] + ' linecode=P_0_0_0_33' + ' length=1'  + ' units=m ') 
    
    
    except Exception as e:
        LS.append(i)
        logger.debug('Error during creation of Switch ACline for OpenDSS ' + str(e))  

with open(name + '_lines_switches.dss', 'w') as filehandle:
    for l in lines_switches:
        filehandle.write('%s\n' % l) 
#%%
"""
############################################################
             LOADS
############################################################
"""
Loads = {}

for i in Energy_consumer.keys():
    Loads[i] = {}
    
    #Saving name and description
    Loads[i]['IdentifiedObject.name'] = Energy_consumer[i]
    
    term = Terminal_CondEquip[i]['child']
    
    t='T'+term.find(cim+'ACDCTerminal.sequenceNumber').text # to get T1 or T2 name
        
    #Creating dict for each terminal of line
    Loads[i][t] = {}
    
    Loads[i][t]['IdentifiedObject.name'] = term.findtext(cim+'IdentifiedObject.name', default = 'None')             
    Loads[i][t]['Terminal.phases'] = term.find(cim+'Terminal.phases').attrib.get(rdf+'resource').split(".")[-1]
    Loads[i][t]['Terminal.ConnectivityNode'] = term.find(cim+'Terminal.ConnectivityNode').attrib.get(rdf+'resource')
    

#%  OpenDSS format              
loads=[]
for i in Loads:    
    loads.append('new load.'+cleanString(Loads[i]['IdentifiedObject.name']) +
                 ' bus1='+ cleanString(CN_names[Loads[i]['T1']['Terminal.ConnectivityNode']])+
                 getPhases[Loads[i]['T1']['Terminal.phases']] +' model=1 conn=wye kW=.3 kvar=.1 status=variable phases='+
                 noPhases[Loads[i]['T1']['Terminal.phases']] +' daily=load_profile') 

with open(name + '_loads.dss', 'w') as filehandle:
    for l in loads:
        filehandle.write('%s\n' % l)   


#%%

"""
############################################################
             TRANSFORMERS
############################################################
"""

def to_perc(val,base):
    return round(float(val)*100/base,3)

Transformers = {}
t = []
for Tx in PowerTransformers:
    # creating dict with each line info
    # Transformers[Tx.attrib.get(rdf+'ID')] = {}
    tx_id = Tx.attrib.get(rdf+'ID')
    tx_name = Tx.findtext(cim+'IdentifiedObject.name', default = 'None')
    try:
        # Transformers[Tx.attrib.get(rdf+'ID')]['IdentifiedObject.name'] = tx_name
        # Transformers[Tx.attrib.get(rdf+'ID')]['PowerTransformerEnd.ratedU'] = Tx.findtext(cim+'PowerTransformerEnd.ratedU', default = 'None')
        
        side=''
        if 'ALIAS-' in tx_name:
            tx_name, side = tx_name.rsplit('-',1)
        elif 'PRIM' in tx_name:
            tx_name, side = tx_name.split(' ')
            tx_name = tx_name.replace('=PRIM','')
            tx_num, side = side.replace('TX=','').split('_')
            tx_name = '_'.join([tx_name, tx_num])
        elif 'DIST' in tx_name:
            tx_name, side = tx_name.split(' ',1)
            tx_name = tx_name.replace('=DIST','')
            try:
                tx_num, side = side.replace('TX=','').split('_')
                tx_name = '_'.join([tx_name, tx_num])
            except:
                tx_num, side = side.replace('TX ','').split('_')
                tx_name = '_'.join([tx_name, tx_num])
        else: # 'TAP'
            continue # discarted
        
#%%        
        if tx_name not in Transformers:
            Transformers[tx_name] = {}
        ratedU = Tx.findtext(cim+'PowerTransformerEnd.ratedU', default = 'None')
        ratedS = 1e3*float(Tx.findtext(cim+'PowerTransformerEnd.ratedS', default = 'None'))
        r = Tx.findtext(cim+'PowerTransformerEnd.r', default = 'None')
        x = Tx.findtext(cim+'PowerTransformerEnd.x', default = 'None')
        
        r = to_perc(r,ratedS)
        x = to_perc(x,ratedS)
        
        conn = Tx.find(cim+'PowerTransformerEnd.connectionKind').attrib.get(rdf+'resource')
        
        #baseVoltage = BaseVoltage[Tx.find(cim+'TransformerEnd.BaseVoltage').attrib.get(rdf+'resource')]
        term = Tx.find(cim+'TransformerEnd.Terminal').attrib.get(rdf+'resource')
        #terminal object
        terminal = Terminal_nodes[term[1:]]
        terminal_name = terminal.findtext(cim+'IdentifiedObject.name', default = 'None')
        phases = terminal.find(cim+'Terminal.phases').attrib.get(rdf+'resource').split('.')[-1]
        conductingEquipment = terminal.find(cim+'Terminal.ConductingEquipment').attrib.get(rdf+'resource')
        connectivityNode = terminal.find(cim+'Terminal.ConnectivityNode').attrib.get(rdf+'resource')
        
        seqNumber = terminal.findtext(cim+'ACDCTerminal.sequenceNumber', default='None')
        side = seqNumber
        t.append((tx_name,side))
        # print(tx_name, f'PowerTransformerEnd.ID_{side}')
        
        Transformers[tx_name][f'PowerTransformerEnd.ID_{side}'] = tx_id
        Transformers[tx_name][f'PowerTransformerEnd.ratedU_{side}'] = ratedU
        #Transformers[tx_name]['PowerTransformerEnd.baseVoltage'] = baseVoltage
        Transformers[tx_name][f'PowerTransformerEnd.r_{side}'] = nonZerovalue(r)
        Transformers[tx_name][f'PowerTransformerEnd.x_{side}'] = nonZerovalue(x)
        Transformers[tx_name]['PowerTransformerEnd.ratedS'] = ratedS
        Transformers[tx_name][f'PowerTransformerEnd.connectionKind_{side}'] = conn.split('.')[-1]
        Transformers[tx_name]['PowerTransformerEnd.phases'] = phases
        Transformers[tx_name]['Terminal.ConductingEquipmentID'] = conductingEquipment
        Transformers[tx_name][f'Terminal.name_{side}'] = terminal_name
        Transformers[tx_name][f'Terminal.sequenceNumber_{side}'] = seqNumber
        Transformers[tx_name][f'Terminal.ConnectivityNode_{side}'] = connectivityNode
        Transformers[tx_name][f'Terminal.ConnectivityNode_Name_{side}'] = CN_names[connectivityNode]
        u.add(Tx.findtext(cim+'PowerTransformerEnd.ratedU', default = 'None'))
    except KeyError:
        print(tx_id, tx_name)

#340041=PRIM TX=T1_2
#ALIAS-425031-e_1
tx_lines = []
tx_dss = []
# OpenDSS line creation
for tx, params in sorted(Transformers.items()):
    try:
        tx_lines.append(f'new line.tx_{tx}'+\
                      f' bus1={cleanString(params["Terminal.ConnectivityNode_Name_1"])}'+ \
                    getPhases[params['PowerTransformerEnd.phases']] +\
                      f' bus2={cleanString(params["Terminal.ConnectivityNode_Name_2"])}'+ \
                    getPhases[params['PowerTransformerEnd.phases']] +\
                      ' geometry=fakeLine' +\
                      ' length=1'+\
                      f' units=m !linekV={params["PowerTransformerEnd.ratedU_1"]} ')
    except Exception as e:
        print(e)
        logger.debug('Error during creation of ACline for OpenDSS ' + str(e))

    try:
        # select the non-zero x parameter
        xhl = max([float(params["PowerTransformerEnd.x_1"]), float(params["PowerTransformerEnd.x_2"])])
        rs = f"[{params['PowerTransformerEnd.x_1']}, {params['PowerTransformerEnd.x_2']}]"
        kV = f'[{params["PowerTransformerEnd.ratedU_1"]} {params["PowerTransformerEnd.ratedU_2"]}]'
        kVA = f"[{params['PowerTransformerEnd.ratedS']}, {params['PowerTransformerEnd.ratedS']}]"
        
        conn_1 =  f"{conections[params['PowerTransformerEnd.connectionKind_1']]}"
        conn_2 =  f"{conections[params['PowerTransformerEnd.connectionKind_2']]}"
        
        tx_dss.append(' '.join([f'new transformer.{tx} phases={noPhases[params["PowerTransformerEnd.phases"]]}',
                                f'windings=2 Xhl={xhl} %Rs={rs}', 
                                ''.join([f'buses=[{cleanString(params["Terminal.ConnectivityNode_Name_1"])}',
                                getPhases[params['PowerTransformerEnd.phases']]]),
                                ''.join([f'{cleanString(params["Terminal.ConnectivityNode_Name_2"])}',
                                getPhases[params['PowerTransformerEnd.phases']] + "]"]),
                                f'kVs={kV} kVAs={kVA} conns=[{conn_1} {conn_2}] Taps=[1 1]']
                               )
                      )
    except Exception as e:
        logger.debug('Error during creation of Transformer for OpenDSS ' + str(e))
#%%
with open(name + '_tx_fake_lines.dss', 'w') as filehandle:
    for l in tx_lines:
        filehandle.write('%s\n' % l)   
with open(name + '_transformers.dss', 'w') as filehandle:
    for l in tx_dss:
        filehandle.write('%s\n' % l) 

#%%
"""
############################################################
             ENERGY INJECTIONS
############################################################
"""
DG = {}

for i in Equivalent_injection.keys():
    DG[i] = {}
    
    #Saving name
    DG[i]['IdentifiedObject.name'] = Equivalent_injection[i]
    
    term = Terminal_CondEquip[i]['child']
    
    t='T'+term.find(cim+'ACDCTerminal.sequenceNumber').text # to get T1 or T2 name
        
    #Creating dict for each terminal of line
    DG[i][t] = {}
    
    DG[i][t]['IdentifiedObject.name'] = term.findtext(cim+'IdentifiedObject.name', default = 'None')   
    
    DG[i][t]['Terminal.ConnectivityNode'] = term.find(cim+'Terminal.ConnectivityNode').attrib.get(rdf+'resource')
    
    try:
        DG[i][t]['Terminal.phases'] = term.find(cim+'Terminal.phases').attrib.get(rdf+'resource').split(".")[-1]    
    except:
        DG[i][t]['Terminal.phases'] = 'ABC'
    
    

#%  OpenDSS format              
dg=[]
for i in DG:    
    dg.append('New Vsource.'+cleanString(DG[i]['IdentifiedObject.name']) +' BasekV=132 pu = 1.00 angle = 0 frequency = 50 phases = 3 bus1 = '+ cleanString(CN_names[DG[i]['T1']['Terminal.ConnectivityNode']])+ getPhases[DG[i]['T1']['Terminal.phases']]) 

with open(name + '_vsources.dss', 'w') as filehandle:
    for l in dg:
        filehandle.write('%s\n' % l) 
        
end = timer()
print(end - start) 
