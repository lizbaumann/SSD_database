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
read_paypal('Paypal_2012.csv')
read_paypal('Paypal_2013.csv')
read_paypal('Paypal_2014_old.csv')
read_paypal('Paypal_2014_new.csv')

# 2012 through 2014: 1462 entries, 42 columns

# Preprocessing
dfp.columns = map(str.strip, dfp.columns)
dfp = dfp[~dfp['Type'].isin(['Update to eCheck Sent', \
	'Update to eCheck Received', 'Payment Review', 
	'Cancelled Fee', 'PayPal card confirmation refund'])]

dfp['Entries'] = 1
dfp['Account'] = 'Paypal'
dfp[['Item Title']] = dfp[['Item Title']].astype(str)
dfp[['Option 1 Name']] = dfp[['Option 1 Name']].astype(str)
dfp[['Option 1 Value']] = dfp[['Option 1 Value']].astype(str)
dfp[['Fee']] = dfp[['Fee']].astype(float)
dfp['Date'] = pd.to_datetime(dfp['Date'], format='%m/%d/%Y')
dfp['Month'] = dfp['Date'].apply(lambda dt: int(dt.strftime('%Y%m')))
dfp['Year'] = dfp['Date'].apply(lambda dt: int(dt.strftime('%Y')))
dfp['For Month'] = dfp['Month']
dfp['how'] = 'EFT'

dfp1 = dfp


################################################################
################################################################
# NEED TO DEAL WITH: 
# Refunds, eg: gross -24, fee 0.7, net -23.3
# Amount = Gross or fee, eg: gross 25, fee -1.03, net 23.97
#how to transpose? run through twice then reassign certain fields and concat?
#revenue  dues 25
#expenses  fees -1.03
################################################################
################################################################




def assign_cats_pp(s):
	'''Assign descriptors for every transaction:
	how (ATM, Check, EFT)
	who (Paypal, Square, member, vendor, etc.)
	what1 (revenue, expense, other) 
	what2 (dues, donations, dividends, workshops, 501c3 Fund, other revenue,
		rent and utilities, taxes insurance and fees, 
		special expense, other expense, 
		transfers)
	what3 (dues type: monthly, recurring, other; 
		expense type: rent, utilities, internet, trash, 
		taxes, licenses, fees monthly, fees other,
		(special expense detail),  
		consumables, equipment, promotional, other expense)'''
	
	what1 = 'UNKNOWN'
	what2 = 'UNKNOWN'
	what3 = 'na'
	
	if s['Type'] == 'Web Accept Payment Received':
		if 'per person' in s['Item Title']:
			what2 = 'Workshops'
		elif 'Monthly Dues' in s['Item Title']:
			what3 = 'Dues Monthly'
	elif (s['Type'] == 'Recurring Payment Received') | \
		(s['Type'] == 'Subscription Payment Received') | \
		(s['Type'] == 'Payment Received'):
		what3 = 'Dues Recurring'
	elif (s['Type'] == 'Donation Received') | \
		(s['Type'] == 'Mobile Payment Received'):
		what2 = 'Donations'
	elif s['Type'] == 'Refund':
		what2 = 'Refunds'
	elif s['Name'] == 'Bank Account':
		what2 = 'Transfers'
	elif s['Name'] == 'PayPal Monthly Billing' :
		what3 = 'Fees Monthly'
	
	# assign rollup categories
	if what3 in ['Dues Monthly', 'Dues Recurring', 'Dues Other']:
		what2 = 'Dues'
	elif what3 in ['Rent and Utilities', \
		'Rent', 'Utilities', 'Internet', 'Trash']:
		what2 = 'Rent and Utilities'
	elif what3 in ['Insurance', 'Taxes', 'SOS Registration', \
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
		'what1' : what2, 
		'what2' : what2,
		'what3' : what3})


dfp_cats = dfp.apply(assign_cats_pp, axis=1)
dfp = dfp.join(dfp_cats)

dfp2 = dfp

def assign_members(s):
	''' Derive members, dues rate, workshop discount,
	workshop attendees. Prerequisite: what2 is assigned '''
	mbrs = 0.0
	duesrate = 0.0
	mbrs_reg = 0.0
	mbrs_ss = 0.0
	mbrs_fam = 0.0
	mbrs_unk = 0.0
	workshopdisc = 0
	attendees = 0
	
	if 'Dues' in s['what2']:
		if '3 Months' in s['Option 1 Value']:
			mbrs = 3.0
		elif ('2 Months' in s['Option 1 Value']) | (s['Gross'] == 130):
			mbrs = 2.0
		elif ('1 Half-Month' in s['Option 1 Value']) | \
			('after the 15th' in s['Option 1 Value']) | \
			('Prorated' in s['Option 1 Value']):
			mbrs = 0.5
		else: 
			mbrs = 1.0
	
		if (s['Gross'] == 12.5) | \
			(s['Gross'] == 32.5) | \
			((s['Gross'] == 50) & (mbrs == 1)):
			# workshops handled by either charging half or by refund
			workshopdisc = 1
			duesrate = s['Gross'] * 2 / mbrs
		elif (s['Gross'] == 55) & (s['Month'] < 201301):
			# used to give $10 off, in 2012
			workshopdisc = 1
			duesrate = 65
		else:
			duesrate = s['Gross'] / mbrs
		
		# Adjust duesrate for various reimbursements... maybe revise
		# how this is done later when incorporating 'cash' file
		if (s['Name'] == 'JOEL BARTLETT') & (duesrate < 50):
			duesrate = 65
		elif (s['Name'] == 'Elizabeth Baumann') & (s['Month'] == 201303):
			duesrate = 65
		elif duesrate == 76.5:
			duesrate = 75
		elif duesrate == 64.99:
			duesrate = 65
		elif duesrate == 62.06:
			# Feb prorated becomes this
			duesrate = 65
		
		if (duesrate == 65) | \
			(duesrate == 75) | \
			('Regular' in s['Option 1 Value']):
			mbrs_reg = mbrs
		elif (duesrate == 25) | ('Student' in s['Option 1 Value']):
			mbrs_ss = mbrs
		elif (duesrate == 100) | ('Family' in s['Option 1 Value']):
			mbrs_fam = mbrs
		elif (duesrate == 40) & (s['Type'] == 'Recurring Payment Received'):
			mbrs_ss = mbrs # so, $40 dues payments treated as student/senior
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
		'Dues_Disc' : workshopdisc})


dfp_mbrs = dfp.apply(assign_members, axis=1)
dfp = dfp.join(dfp_mbrs)

dfp3 = dfp

################################################################
# Get primary fields (to be merged with Paypal data) and a csv copy
################################################################
dfp.rename(columns={'Gross' : 'Amount', \
	'Name' : 'who', \
	'Time' : 'PP_Time', \
	'Type' : 'PP_Type', \
	'Status' : 'PP_Status', \
	'Item Title' : 'PP_Item Title', \
	'Option 1 Value' : 'PP_Option 1', \
	'Option 2 Value' : 'PP_Option 2', \
	'From Email Address' : 'PP_From Email'
	}, inplace=True)

dfpkeep = ['Date', 'Year', 'Month', 'For Month', \
	'Account', 'SourceFile', 'Transaction ID', \
	'what2', 'how', 'who', 'what', 'what2', 
	'Amount', 'Balance', 'Entries', \
	'Attendees', 'Dues_Disc', 'Dues_Rate', \
	'Mbrs', 'Mbrs_Reg', 'Mbrs_SS', 'Mbrs_Fam', 'Mbrs_UNK', \
	'PP_Time', 'PP_Type', 'PP_Status', 'PP_Item Title', \
	'PP_Option 1', 'PP_Option 2', 'PP_From Email']
dfp = dfp[dfpkeep]

dfp.to_csv('dfp.csv')

################################################################
# Summaries (note, by Name may not print them all...)
################################################################
sumvars = ['Gross','Fee','Dues_Rate','Entries','Mbrs','Attendees']
sumvars2 = ['Gross','Fee','Net','Entries']
mbrvars = ['Mbrs','Mbrs_Reg','Mbrs_SS','Mbrs_Fam','Mbrs_UNK','Dues_Disc']

dfp[sumvars].groupby(dfp['what2']).sum()
dfp[mbrvars].groupby(dfp['what2']).sum()
dfp[sumvars].groupby(dfp['Dues_Rate']).sum()
dfp[mbrvars].groupby(dfp['Dues_Rate']).sum()

dfp2 = dfp[dfp['what2'] != 'Transfer']
dfp2[sumvars].groupby(dfp2['Month']).sum()
dfp2[mbrvars].groupby(dfp2['Month']).sum()


################################################################
# Use for troubleshooting
################################################################

# choose one of these, then run the summaries on it
dfp2 = dfp[dfp['Mbrs_UNK'] > 0]
dfp2 = dfp[dfp['what2'] == 'UNKNOWN']
dfp2 = dfp[dfp['what2'] == 'Fee Other']
dfp2 = dfp[dfp['Type'] == 'Cancelled Fee']

dfp2[['Name','Month','Gross','Dues_Rate','Dues_Disc']]
dfp2[['Type','Gross','Dues_Rate']]
dfp2[['Option 1 Value','Gross','Dues_Rate']]
dfp2[['Item Title','Gross','Dues_Rate']]


################################################################
# CONSIDER FOR CHANGES: 
# review Joel and Liz adjustments, do by month
# monthly dues: if paying > 1 month: create multiple records from 1 record?
# also need the 'for' month, not the payment month?
# have mbr_type instead of tiers in columns?

# PROBLEMS:
# where is mill money (2012?)
# collect less or not at all on Paypal because of paying expense credit... how much to care about this past stuff? want good duesrate... but maybe better to add elevations and 'cash' payment file in first, then calc duesrate? for past... for go forward, establish a better process? (always do with refunds, for instance)
# split up family to 2 people?
# consider / need to properly adjust/account for Seb+Kerry family membership
# workshop discount is incomplete: refunds will not show as workshop discount yet... need to tie refund to original, maybe sum up, and put the discount indicator with the orig payment? could tie by refund.reference == orig.transaction. Related question: how do I really want to account for workshop discount?

################################################################


################################################################
# NOTES - treatment of special situations above
# workshops: paying for 2 people at $15 each shows as 1 at $30... may be more like this, but only fixed this one
# Oddball dues rates, accounted for above:
# we used to tack on paypal fees (76.50), count as 75
# someone paid $0.01 for workshop and so dues 64.99, count as 65 
# Andy paid 40 for membership, count any < 50 as student membership
# workshop discount has been half off or $10 off
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
################################################################
