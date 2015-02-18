#!//anaconda/bin/python
import os, csv, re, datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

pathElevations = '/Users/lizbaumann/Liz/SSD/_Elevations/'
pathFinances = '/Users/lizbaumann/Liz/SSD/_Finances/'
pathPaypal = '/Users/lizbaumann/Liz/SSD/_Paypal/'

################################################################
# Read in processed Paypal and Elevations data
################################################################
dfkeep = ['Date', 'Year', 'Month', 'For Month', \
	'Account', 'SourceFile', 'Transaction ID', \
	'how', 'who', 'what1', 'what2', 'what3', \
	'Amount', 'Balance', 'Entries', \
	'Attendees', 'Dues_Disc', 'Dues_Rate', \
	'Mbrs', 'Mbrs_Reg', 'Mbrs_SS', 'Mbrs_Fam', 'Mbrs_UNK']

df = pd.DataFrame()
df1 = pd.read_csv(pathPaypal + 'dfp.csv')[dfkeep]
df2 = pd.read_csv(pathElevations + 'dfe.csv')[dfkeep]
df = df.append(df1, ignore_index=True)
df = df.append(df2, ignore_index=True)


################################################################
# Summaries (note, by Name may not print them all...)
################################################################
sumvars_pp = ['Amount', 'Entries', 'Mbrs', 'Dues_Disc', 'Attendees']
sumvars2_pp = ['Gross','Fee','Net','Amount','Entries']
mbrvars_pp = ['Mbrs','Mbrs_Reg','Mbrs_SS','Mbrs_Fam','Mbrs_UNK']

df[sumvars_pp].groupby(df['what1']).sum()
df[sumvars_pp].groupby(df['what2']).sum()
df[sumvars_pp].groupby(df['what3']).sum()

dfdues = df[df['what2'] == 'Dues']

dfdues[sumvars_pp].groupby(dfdues['Dues_Rate']).sum()
dfdues[mbrvars_pp].groupby(dfdues['Dues_Rate']).sum()
dfdues[sumvars_pp].groupby(dfdues['Mbrs']).sum()
dfdues[mbrvars_pp].groupby(dfdues['Mbrs']).sum()

dfdues[sumvars_pp].groupby(dfdues['For Month']).sum()
dfdues[mbrvars_pp].groupby(dfdues['For Month']).sum()



################################################################
# Use for troubleshooting
################################################################
# check refunds, all for half off dues?
x = dfdues[dfdues['Mbrs_UNK'] != 0]
x = df[(df['Name'] == 'Robert Bryan') & (df['For Month'] == 201404)]
x = df[(df['Name'] == 'Jarad Christianson')]

dfdues = df[df['what2'] == 'Dues']

x = dfdues[(dfdues['Mbrs'] == 3.0)]

x = dfdues[(dfdues['Name'] == 'Elizabeth Baumann') & (dfdues['For Month'] == 201412)]
x = dfdues[(dfdues['Name'] == 'Wayne Radinsky') & (dfdues['For Month'] >= 201409)]
x = dfdues[dfdues['Dues_Rate'] == 0]

x[['Name','Date','Gross','Dues_Rate','Mbrs','Type', 'Option 1 Value']].sort('Date')
x[['Name','Date','Gross','Amount','what2','Dues_Rate','Dues_Disc','Type','Mbrs','Mbrs_Reg','Mbrs_SS','Mbrs_UNK']].sort('Date')
x[['Name','Date','Gross','Type', 'Option 1 Value']].sort('Date')

# choose one of these, then run the summaries on it
df2 = df[df['Mbrs_UNK'] > 0]
df2 = df[df['what2'] == 'UNKNOWN']
df2 = df[df['what2'] == 'Fee Other']
df2 = df[df['Type'] == 'Cancelled Fee']


################################################################
# NOTES - treatment of special situations above
################################################################
