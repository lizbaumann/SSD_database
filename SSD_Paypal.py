#!//anaconda/bin/python
import os, csv, re, datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

pathPaypal = '/Users/lizbaumann/Liz/SSD/_Paypal/'

################################################################
# Read in and process Paypal data
################################################################
def read_paypal(csvfile):
	dfpname = pd.read_csv(pathPaypal + csvfile, thousands=',')
	dfpname['SourceFile'] = csvfile
	global dfp
	dfp = dfp.append(dfpname, ignore_index=True)

dfp = pd.DataFrame()

#read_paypal('Paypal_sample.csv')
read_paypal('Paypal_20150214_new.csv')
read_paypal('Paypal_20150214_old.csv')
read_paypal('Paypal_2014_new.csv')
read_paypal('Paypal_2014_old.csv')
read_paypal('Paypal_2013.csv')
read_paypal('Paypal_2012.csv')

# 2012 through 2014: 1462 entries, 42 columns

# Preprocessing
dfp.columns = map(str.strip, dfp.columns)
dfp = dfp[~dfp['Type'].isin(['Update to eCheck Sent', \
	'Update to eCheck Received', 'Payment Review', 
	'Cancelled Fee', 'PayPal card confirmation refund'])]

dfp[['Item Title']] = dfp[['Item Title']].astype(str)
dfp[['Option 1 Name']] = dfp[['Option 1 Name']].astype(str)
dfp[['Option 1 Value']] = dfp[['Option 1 Value']].astype(str)
dfp[['Gross']] = dfp[['Gross']].astype(float)
dfp[['Fee']] = dfp[['Fee']].astype(float)
dfp['Gross'] = dfp['Gross'].apply(lambda x: float(np.round(int(x*100)))/100)
dfp['Fee'] = dfp['Fee'].apply(lambda x: float(np.round(int(x*100)))/100)
dfp['Date'] = pd.to_datetime(dfp['Date'], format='%m/%d/%Y')
dfp['Month'] = dfp['Date'].apply(lambda dt: int(dt.strftime('%Y%m')))
dfp['Amount'] = dfp['Gross']
dfp['Entries'] = 1
dfp['Account'] = 'Paypal'
dfp['how'] = 'EFT'
dfp['who'] = dfp['Name']

dfp1 = dfp.copy()


def assign_cats_pp(s):
	'''Assign descriptors for every transaction:
	how (ATM, Check, EFT)
	who (Paypal, Square, member, vendor, etc.)
	what1 (revenue, expense, other) 
	what2 (dues, donations, dividends, workshops, other revenue,
		501c3 Fund, transfers, 
		rent and utilities, taxes insurance and fees, 
		special expense, other expense)
	what3 (dues type: monthly, recurring, refund, other; 
		expense type: rent, utilities, internet, trash, 
		taxes, licenses, fees monthly, fees other, 
		fees paypal monthly, fees paypal transactions,
		(special expense detail),  
		consumables, equipment, promotional, other expense;
		transfers)'''
	
	what1 = 'UNKNOWN'
	what2 = 'UNKNOWN'
	what3 = 'na'
	
	if (s['Month'] == 201501) & (s['Name'] == 'Ryan Bennett'):
		what3 = 'Dues Monthly'
	elif s['Type'] == 'Web Accept Payment Received':
		if 'per person' in s['Item Title']:
			what3 = 'Workshops'
		elif 'Monthly Dues' in s['Item Title']:
			what3 = 'Dues Monthly'
	elif (s['Type'] == 'Recurring Payment Received') | \
		(s['Type'] == 'Subscription Payment Received') | \
		(s['Type'] == 'Payment Received'):
		what3 = 'Dues Recurring'
	elif (s['Type'] == 'Donation Received') | \
		(s['Type'] == 'Mobile Payment Received'):
		what3 = 'Donations'
	elif s['Type'] == 'Refund':
		# usually for workshop discount but just a couple exceptions
		if (s['Name'] == 'Jarad Christianson') & \
			(s['Month'] == 201310) & (s['Gross'] == -25):
			# general refund of full dues
			what3 = 'Dues Recurring'
		elif (s['Name'] == 'Robert Bryan') & \
			(s['Month'] == 201404) & (s['Gross'] == -53.48):
			# reimbursing equipment purchase
			what3 = 'Equipment'
		elif ((s['Name'] == 'Jennifer Farmer') & \
			(s['Month'] == 201411) & (s['Gross'] == -24)):
			# reimbursing consumables purchase
			what3 = 'Consumables'
		else:
			what3 = 'Dues Recurring' # should offset dues payment
	elif s['Name'] == 'Bank Account':
		what3 = 'Transfers'
	elif s['Name'] == 'PayPal Monthly Billing' :
		what3 = 'Fees Paypal Monthly'
	
	# assign rollup categories... used by both PP and El, maybe move?
	if what3 in ['Workshops', 'Donations', 'Dividends', 'Transfers']:
		what2 = what3
	elif 'Dues' in what3:
		what2 = 'Dues'
	elif what3 in ['Rent and Utilities', \
		'Rent', 'Utilities', 'Internet', 'Trash']:
		what2 = 'Rent and Utilities'
	elif what3 in ['Insurance', 'Taxes', 'SOS Registration', \
		'Fees Paypal Monthly', 'Fees Paypal Transactions', \
		'Fees Monthly', 'Fees Other']:
		what2 = 'Insurance, Taxes and Fees'
	elif what3 in ['Consumables', 'Equipment', 'Promotional', 'Other']:
		what2 = 'Other Expenses'
	
	if what2 == 'Transfers':
		what1 = 'Other'
	elif what2 in ['Dues and Donations', \
		'Dues', 'Donations', 'Dividends', 'Workshops']:
		what1 = 'Revenue'
	else:
		what1 = 'Expenses'
	
	return pd.Series({
		'what1' : what1, 
		'what2' : what2,
		'what3' : what3})


# dfp = dfp1.copy()
dfp_cats = dfp.apply(assign_cats_pp, axis=1)
dfp = dfp.join(dfp_cats)


dfp2 = dfp.copy()

# gross collected and fees are in different columns, separate them
dfp_gross = dfp.copy()
dfp_fees = dfp.copy()
dfp_fees['Amount'] = dfp_fees['Fee']
dfp_fees['Gross'] = 0
dfp_fees['Net'] = 0
dfp_fees['what3'] = 'Fees Paypal Transactions' 
dfp_fees['what2'] = 'Insurance, Taxes and Fees' 
dfp_fees['what1'] = 'Expenses' 
dfp_fees['who'] = 'Paypal'

dfp_gross['Fee'] = 0
# this is resetting dfp_fees to 0 also, even with deep=False


dfp = pd.DataFrame()
dfp = dfp_gross.append(dfp_fees, ignore_index=True)

dfp3 = dfp.copy()

def assign_members_pp(s):
	''' Derive members, dues rate, workshop discount,
	workshop attendees. Prerequisite: what2 is assigned '''
	mbrs = 0.0
	duesrate = float(0)
	mbrs_reg = 0.0
	mbrs_ss = 0.0
	mbrs_fam = 0.0
	mbrs_unk = 0.0
	duesdisc = 0
	attendees = 0
	
	if 'Dues' in s['what2']:
		if (s['Month'] == 201501) & (s['Name'] == 'Ryan Bennett'):
			mbrs = 4.0
		elif '3 Months' in s['Option 1 Value']:
			mbrs = 3.0
		elif ('2 Months' in s['Option 1 Value']) | (s['Gross'] == 130):
			mbrs = 2.0
		elif ('1 Half-Month' in s['Option 1 Value']) | \
			('after the 15th' in s['Option 1 Value']) | \
			('Prorated' in s['Option 1 Value']):
			mbrs = 0.5
		else: 
			mbrs = 1.0
	
		# dues discount for workshop: either charged half or refunded
		if (s['Gross'] == 12.5) | \
			(s['Gross'] == 32.5) | \
			((s['Gross'] == 50.0) & (mbrs == 1)):
			duesdisc = 1
			duesrate = s['Gross'] * 2.0 / mbrs
		elif 'Refund' in s['Type']:
			# usually for workshop discount but just a couple exceptions
			if (s['Name'] == 'Jarad Christianson') & \
				(s['Month'] == 201310) & \
				(s['Gross'] == -25):
				# general refund of full dues
				mbrs = -1
				mbrs_ss = -1
				duesdisc = 0
				duesrate = -25.0
			else:
				# so not to overstate when added to other one
				duesdisc = 1
				mbrs = 0
				duesrate = s['Gross'] * (-2) 
		elif (s['Gross'] == 55) & (s['Month'] < 201301):
			# used to give $10 off, in 2012
			duesdisc = 1
			duesrate = 65.0
		else:
			duesrate = s['Gross'] * 1.0 / mbrs
		
		# Adjust duesrate for various reimbursements... maybe revise
		# how this is done later when incorporating 'cash' file
		if (s['Name'] == 'JOEL BARTLETT') & (duesrate < 50):
			duesrate = 65.0
		elif (s['Name'] == 'Elizabeth Baumann') & (s['Month'] == 201303):
			duesrate = 65.0
		elif (s['who'] == 'Daniel Zukowski') & ():
			duesrate = 65
		elif (s['who'] == 'Jeffrey Ammons') & ():
			duesrate = 65
		elif (s['who'] != 'Richard Buchman'):
			# 25 each for his son and him - how to handle?
			duesrate = s['Gross'] * 1.0 / mbrs
		elif (duesrate == 40.0):
			duesrate = 25.0 # a few people have paid 40, count as SS
		elif (duesrate >= 75.0) & (duesrate < 77):
			duesrate = 75.0
		elif (duesrate >= 60.0) and (duesrate <= 65.0):
			# Feb prorated in 201202 becomes 62.08
			duesrate = 65.0
		
		if mbrs_reg + mbrs_ss + mbrs_fam + mbrs_unk == 0: 
			if (duesrate == 65.0) | \
				(duesrate == 75.0) | \
				('Regular' in s['Option 1 Value']):
				mbrs_reg = mbrs
			elif (duesrate == 25.0) | ('Student' in s['Option 1 Value']):
				mbrs_ss = mbrs
			elif (duesrate == 100.0) | ('Family' in s['Option 1 Value']):
				mbrs_fam = mbrs
			else: 
				mbrs_unk = mbrs
	
	if s['what2'] == 'Workshops':
		if ('$30.00 per person' in s['Item Title']) & \
			('3D' in s['Item Title']):
			attendees = 2
		else: 
			attendees = 1
	
	return pd.Series({'Mbrs' : mbrs, 
		'Mbrs_Reg' : mbrs_reg,
		'Mbrs_SS' : mbrs_ss,
		'Mbrs_Fam' : mbrs_fam,
		'Mbrs_UNK' : mbrs_unk,
		'Dues_Rate' : duesrate,
		'Attendees' : attendees,
		'Dues_Disc' : duesdisc})


dfp_mbrs = dfp.apply(assign_members_pp, axis=1)
dfp = dfp.join(dfp_mbrs)

dfp4 = dfp.copy()

################################################################
# Split payments for 2 or 3 months into pieces (creating new rows)
# Also deal with family memberships
################################################################
dfp['For Month'] = dfp['Month']
dfp_m1 = dfp[dfp['Mbrs'] <= 1.0]
dfp_m2 = dfp[dfp['Mbrs'] == 2.0]
dfp_m3 = dfp[dfp['Mbrs'] == 3.0]
dfp_m4 = dfp[dfp['Mbrs'] == 4.0] # 1/27/15 Ryan Bennett

dfp_m2a = dfp_m2.copy()
dfp_m2b = dfp_m2.copy()
dfp_m3a = dfp_m3.copy()
dfp_m3b = dfp_m3.copy()
dfp_m3c = dfp_m3.copy()
dfp_m4a = dfp_m4.copy()
dfp_m4b = dfp_m4.copy()
dfp_m4c = dfp_m4.copy()
dfp_m4d = dfp_m4.copy()

numerics = ['Gross', 'Fee', 'Net', 'Amount', 'Mbrs', \
	'Mbrs_Reg', 'Mbrs_SS', 'Mbrs_Fam', 'Mbrs_UNK']

for field in numerics:
	dfp_m2a[field] = dfp_m2[field] / 2
	dfp_m2b[field] = dfp_m2[field] / 2
	dfp_m3a[field] = dfp_m3[field] / 3
	dfp_m3b[field] = dfp_m3[field] / 3
	dfp_m3c[field] = dfp_m3[field] / 3
	dfp_m4a[field] = dfp_m4[field] / 4
	dfp_m4b[field] = dfp_m4[field] / 4
	dfp_m4c[field] = dfp_m4[field] / 4
	dfp_m4d[field] = dfp_m4[field] / 4

# increment For Month for 2nd of 2 month and 2nd, 3rd of 3 month
def increment_month(s):
	nextdate = s + pd.DateOffset(months=1)
	nextmonth = int(nextdate.strftime('%Y%m'))
	return nextmonth

dfp_m2b['For Month'] = dfp_m2a['For Month'].map(increment_month)
dfp_m3b['For Month'] = dfp_m3a['For Month'].map(increment_month)
dfp_m3c['For Month'] = dfp_m3b['For Month'].map(increment_month)

dfp_m4a['For Month'] = 201408
dfp_m4b['For Month'] = dfp_m4a['For Month'].map(increment_month)
dfp_m4c['For Month'] = dfp_m4b['For Month'].map(increment_month)
dfp_m4d['For Month'] = dfp_m4c['For Month'].map(increment_month)

dfp = pd.DataFrame()
dfp = dfp.append(dfp_m1, ignore_index=True)
dfp = dfp.append(dfp_m2a, ignore_index=True)
dfp = dfp.append(dfp_m2b, ignore_index=True)
dfp = dfp.append(dfp_m3a, ignore_index=True)
dfp = dfp.append(dfp_m3b, ignore_index=True)
dfp = dfp.append(dfp_m3c, ignore_index=True)
dfp = dfp.append(dfp_m4a, ignore_index=True)
dfp = dfp.append(dfp_m4b, ignore_index=True)
dfp = dfp.append(dfp_m4c, ignore_index=True)
dfp = dfp.append(dfp_m4d, ignore_index=True)

if (dfp['Name'] == 'Dylan Kishner-Lopez') & \
	(dfp['Month'] == 201501) & \ 	
	(dfp['Trans'] == '81E50031HF428491Y'):
	dfp['For Month'] = 201502

# Family memberships:
# Seb and Kerry, 65 = 40 + 25
# Ryan Bennett, John Bennett, Nova Art LLC scienceart.com, Dylan Kishner-Lopez, 100 = 50 + 50 
# Nicholas d howard and Sara Snider, 100 = 50 + 50 
# Richard Buchman and Jordan Buchman, billed 50 = 25 + 25, but not 'family'
Daniel Zukowski                 2013-10-12, refunded workshop
Jeffrey Ammons                  2013-06-29, refunded workshop
Nova Art LLC scienceart.com
Note people paying dues after the 15th or so put in next For Month?
Ryan B payments always complicated...

dfp5 = dfp.copy()


################################################################
# Get primary fields (to be merged with Paypal data) and a csv copy
################################################################
dfp['For Year'] = dfp['For Month'].apply(lambda ym: int(ym/100))
dfp.rename(columns={'Time' : 'PP_Time', \
	'Type' : 'PP_Type', \
	'Status' : 'PP_Status', \
	'Item Title' : 'PP_Item Title', \
	'Option 1 Value' : 'PP_Option 1', \
	'Option 2 Value' : 'PP_Option 2', \
	'From Email Address' : 'PP_From Email'
	}, inplace=True)

dfpkeep = ['Date', 'Month', 'For Year', 'For Month', \
	'Account', 'SourceFile', 'Transaction ID', \
	'how', 'who', 'what1', 'what2', 'what3', \
	'Amount', 'Balance', 'Entries', \
	'Attendees', 'Dues_Disc', 'Dues_Rate', \
	'Mbrs', 'Mbrs_Reg', 'Mbrs_SS', 'Mbrs_Fam', 'Mbrs_UNK', \
	'PP_Time', 'PP_Type', 'PP_Status', 'PP_Item Title', \
	'PP_Option 1', 'PP_Option 2', 'PP_From Email']
dfp = dfp[dfpkeep]

dfp.to_csv(pathPaypal + 'dfp.csv')

################################################################
# Summaries (note, by Name may not print them all...)
################################################################
sumvars_pp = ['Amount', 'Entries', 'Mbrs', 'Dues_Disc', 'Attendees']
sumvars2_pp = ['Gross','Fee','Net','Amount','Entries']
mbrvars_pp = ['Mbrs','Mbrs_Reg','Mbrs_SS','Mbrs_Fam','Mbrs_UNK']

dfp[sumvars_pp].groupby(dfp['what1']).sum()
dfp[sumvars_pp].groupby(dfp['what2']).sum()
dfp[sumvars_pp].groupby(dfp['what3']).sum()

dfpdues = dfp[dfp['what2'] == 'Dues']

dfpdues[sumvars_pp].groupby(dfpdues['Dues_Rate']).sum()
dfpdues[mbrvars_pp].groupby(dfpdues['Dues_Rate']).sum()
dfpdues[mbrvars_pp].groupby(dfpdues['Mbrs']).sum()

dfp[sumvars_pp].groupby(dfp['For Month']).sum()
dfp[mbrvars_pp].groupby(dfp['For Month']).sum()


################################################################
# Use for troubleshooting
################################################################
# check refunds, all for half off dues?
x = dfpdues[dfpdues['Mbrs_UNK'] != 0]
x = dfp[(dfp['Name'] == 'Robert Bryan') & (dfp['For Month'] == 201404)]
x = dfp[(dfp['Name'] == 'Jarad Christianson')]

dfpfam = dfp[dfp['Mbrs_Fam'] > 0]
dfpfam[sumvars_pp].groupby(dfpfam['who']).sum()
x = dfpfam[(dfpfam['who'] == 'Nova Art LLC scienceart.com')]
x[['who','Date','Amount','what2','Dues_Rate','Dues_Disc', 'Mbrs','Mbrs_Reg','Mbrs_SS','Mbrs_UNK']].sort('Date')
Daniel Zukowski                 2013-10-12, refunded workshop
Jeffrey Ammons                  2013-06-29, refunded workshop
Nova Art LLC scienceart.com     2014-01-07


>>> dfpfam[sumvars_pp].groupby(dfpfam['who']).sum()
                             Amount  Entries  Mbrs  Dues_Disc  Attendees
who                                                                     
Daniel Zukowski                  50        1     1          1          0
Dylan Kishner-Lopez             200        2     2          0          0
Jeffrey Ammons                   50        1     1          1          0
John Bennett                    200        2     2          0          0
Nicholas d howard               700        7     7          0          0
Nova Art LLC scienceart.com     100        1     1          0          0
Richard Buchman                 600       12    12         12          0
Ryan Bennett                    700        7     7          0          0



dfpdues = dfp[dfp['what2'] == 'Dues']
x = dfpdues[(dfpdues['Mbrs'] == 3.0)]

x = dfpdues[(dfpdues['who'] == 'Wayne Radinsky') & (dfpdues['Month'] >= 201409)]
x = dfpdues[dfpdues['Dues_Rate'] == 0]

x = dfpdues[(dfpdues['who'] == 'Ryan Bennett') & (dfpdues['Month'] >= 201407)]
x[['who','Date','Amount','what2','Dues_Rate','Dues_Disc', 'Mbrs','Mbrs_Reg','Mbrs_SS','Mbrs_UNK']].sort('Date')

# choose one of these, then run the summaries on it
dfp2 = dfp[dfp['Mbrs_UNK'] > 0]
dfp2 = dfp[dfp['what2'] == 'UNKNOWN']
dfp2 = dfp[dfp['what2'] == 'Fee Other']
dfp2 = dfp[dfp['Type'] == 'Cancelled Fee']

dfp2[['Name','For Month','Gross','Dues_Rate','Dues_Disc']]
dfp2[['Type','Gross','Dues_Rate']]
dfp2[['Option 1 Value','Gross','Dues_Rate']]
dfp2[['Item Title','Gross','Dues_Rate']]

# checking the month parsing
# dfp4[['Amount','Mbrs']].sum()
# dfp5[['Amount','Mbrs']].sum()
# Amount     462.94, Mbrs      1197.00

# dfp4.shape # (2836, 62)
# dfp5.shape # (2860, 62)
# dfp_m2.shape # (14, 62)
# dfp_m3.shape # (5, 62)

# dfp_m2a['Date']
# dfp_m2b['Date']
# dfp_m3a['Date']
# dfp_m3b['Date']
# dfp_m3c['Date']

################################################################
# How to handle this properly?
# Paid $15 for workshop, reduced dues instead:
################################################################
Daniel Zukowski                 2013-10-12, refunded workshop
Jeffrey Ammons                  2013-06-29, refunded workshop



################################################################
# NOTES - treatment of special situations above
# workshops: paying for 2 people at $15 each shows as 1 at $30... may be more like this, but only fixed this one
# Oddball dues rates, accounted for above:
# we used to tack on paypal fees (76.50), count as 75
# someone paid $0.01 for workshop and so dues 64.99, count as 65 
# some paid 40 for membership, count any < 50 as student membership
# workshop discount has been half off or $10 off in 2012 etc
# Feb prorated dues 31.03 at one point, count as 65 dues rate, 1/2 mbr
# MAY CHANGE LATER: partial dues due to reimbursement... Joel and Liz
# Type == 'Update to eCheck Received', 'Update to eCheck Sent: 
# these happen for 2 reasons: 
# 1. dues payers, sometimes money not debited immediately, there are 2 transactions for same amount, 2nd one has this code
# 2. monthly fees, if money needed to come from Elevations, there are 3 transactions +19.99 and -19.99 together, and this is last one +19.99
# While the balance gets debited/credited with the last 'update' one, it seems to make more sense to exclude it from this process - to include would duplicate; to otherwise reflect it would be a lot of extra work for little gain.
# Type == Mobile Payment Received: 2 @ 2012-08, Christian Macy... donation?
# Type == Cancelled Fee: goes with refunds - but just use fee column
# Type == PayPal card confirmation refund: 1 @ 2012-06 1.95... fees? just remove, not sure if it is with something else
# Type == Payment Received: 130 from Bill P 2014-01, 65 Chris C 2013-12... these were late payments for recurring dues 
# Type == Payment Review: donald dangelo, 8 @ 2013-04-2013-07... these reverse each other and the real payment is earlier, so delete them
# 2 and 3 month lump payments have been parsed to be monthly
################################################################
