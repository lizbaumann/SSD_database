#!//anaconda/bin/python
import os, csv, re, datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

pathPaypal = '/Users/lizbaumann/Liz/SSD/_Paypal/'

################################################################
# Read in and process Paypal data
################################################################
dfp = pd.DataFrame()

def read_paypal(csvfile):
	dfpname = pd.read_csv(pathPaypal + csvfile, thousands=',')
	dfpname['SourceFile'] = csvfile
	global dfp
	dfp = dfp.append(dfpname, ignore_index=True)

#read_paypal('Paypal_sample.csv')
read_paypal('Paypal_2012.csv')
read_paypal('Paypal_2013.csv')
read_paypal('Paypal_2014_old.csv')
read_paypal('Paypal_2014_new.csv')

# 2012 through 2014: 1462 entries, 42 columns

# Preprocessing
dfp.columns = map(str.strip, dfp.columns)
def getmonth(dt):
	return int(datetime.datetime.strptime(dt, '%m/%d/%Y').strftime('%Y%m'))

dfp['Month'] = dfp['Date'].apply(getmonth)
dfp['Entries'] = 1
dfp[['Item Title']] = dfp[['Item Title']].astype(str)
dfp[['Option 1 Name']] = dfp[['Option 1 Name']].astype(str)
dfp[['Option 1 Value']] = dfp[['Option 1 Value']].astype(str)
dfp = dfp[dfp['Type'] != 'Update to eCheck Sent']
dfp = dfp[dfp['Type'] != 'Update to eCheck Received']
dfp = dfp[dfp['Type'] != 'Payment Review']
dfp = dfp[dfp['Type'] != 'Cancelled Fee']
dfp = dfp[dfp['Type'] != 'PayPal card confirmation refund']
dfp[['Fee']] = dfp[['Fee']].astype(float)
dfp1 = dfp



# Assign paytype (dues vs workshops etc), member count fields
def assign_paytype(s):
	paytype = 'UNKNOWN'
	if s['Type'] == 'Web Accept Payment Received':
		if 'per person' in s['Item Title']:
			paytype = 'Workshop'
		elif 'Monthly Dues' in s['Item Title']:
			paytype = 'Dues Monthly'
	elif (s['Type'] == 'Recurring Payment Received') | \
		(s['Type'] == 'Subscription Payment Received') | \
		(s['Type'] == 'Payment Received'):
		paytype = 'Dues Recurring'
	elif (s['Type'] == 'Donation Received') | \
		(s['Type'] == 'Mobile Payment Received'):
		paytype = 'Donation'
	elif s['Type'] == 'Refund':
		paytype = 'Refund'
	elif s['Name'] == 'Bank Account':
		paytype = 'Transfer'
	elif s['Name'] == 'PayPal Monthly Billing' :
		paytype = 'Fee Monthly'
	return paytype


def assign_members(s):
	''' Derive members, dues rate, workshop discount,
	workshop attendees. Prerequisite: Paytype is assigned '''
	mbrs = 0.0
	duesrate = 0.0
	mbrs_reg = 0.0
	mbrs_ss = 0.0
	mbrs_fam = 0.0
	mbrs_unk = 0.0
	workshopdisc = 0
	attendees = 0
	
	if 'Dues' in s['Paytype']:
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
	
		if (s['Gross'] == 12.5) | (s['Gross'] == 32.5) | \
			((s['Gross'] == 50) & (mbrs == 1)):
			# workshops handled by either charging half or by refund
			workshopdisc = 1
			duesrate = s['Gross'] * 2 / mbrs
		elif s['Gross'] == 55:
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
		
		if (duesrate == 65) | (duesrate == 75) | \
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
	
	if s['Paytype'] == 'Workshop':
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
		'Workshop_Disc' : workshopdisc})



dfp['Paytype'] = dfp.apply(assign_paytype, axis=1)
dfp_mbrs = dfp.apply(assign_members, axis=1)
dfp = dfp.join(dfp_mbrs)


################################################################
# Summaries (note, by Name may not print them all...)
################################################################
sumvars = ['Gross','Fee','Dues_Rate','Entries','Mbrs','Attendees']
sumvars2 = ['Gross','Fee','Net','Entries']
mbrvars = ['Mbrs','Mbrs_Reg','Mbrs_SS','Mbrs_Fam','Mbrs_UNK','Workshop_Disc']

dfp[sumvars].groupby(dfp['Paytype']).sum()
dfp[mbrvars].groupby(dfp['Paytype']).sum()
dfp[sumvars].groupby(dfp['Dues_Rate']).sum()
dfp[mbrvars].groupby(dfp['Dues_Rate']).sum()

dfp2 = dfp[dfp['Paytype'] != 'Transfer']
dfp2[sumvars].groupby(dfp2['Month']).sum()
dfp2[mbrvars].groupby(dfp2['Month']).sum()

################################################################
# Use for troubleshooting
################################################################

# choose one of these, then run the summaries on it
dfp2 = dfp[dfp['Mbrs_UNK'] > 0]
dfp2 = dfp[dfp['Paytype'] == 'UNKNOWN']
dfp2 = dfp[dfp['Paytype'] == 'Fee Other']
dfp2 = dfp[dfp['Type'] == 'Cancelled Fee']

dfp2[['Name','Month','Gross','Dues_Rate','Workshop_Disc']]
dfp2[['Type','Gross','Dues_Rate']]
dfp2[['Option 1 Value','Gross','Dues_Rate']]
dfp2[['Item Title','Gross','Dues_Rate']]


################################################################
# CONSIDER FOR CHANGES: 
# review Joel and Liz adjustments, do by month
# monthly dues: if paying > 1 month: create multiple records from 1 record?
# also need the 'for' month, not the payment month?
# modeling question: 'Mbrs_Reg','Mbrs_SS','Mbrs_Fam' fields or rows?

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
