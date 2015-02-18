#!//anaconda/bin/python
import os, csv, re, datetime
import pandas as pd
import numpy as np
#import matplotlib.pyplot as plt

pathElevations = '/Users/lizbaumann/Liz/SSD/_Elevations/'
pathFinances = '/Users/lizbaumann/Liz/SSD/_Finances/'

# debits always negative, credits always positive

################################################################
# Read in and process Elevations data
################################################################
def read_elevations(csvfile, acct = 'Checking'):
	dfename = pd.read_csv(pathElevations + csvfile, skiprows=3)
	dfename['SourceFile'] = csvfile
	dfename['Account'] = acct
	global dfe
	dfe = dfe.append(dfename, ignore_index=True)

dfe = pd.DataFrame()
read_elevations('Elevations_20150214.csv')
read_elevations('Elevations_2014.csv')
read_elevations('Elevations_2013.csv')
read_elevations('Elevations_2012.csv')
read_elevations('Elevations_2011.csv')
read_elevations('Elevations_Savings_20141231.csv', 'Savings')

# Preprocessing
dfe.columns = map(str.strip, dfe.columns)
dfe.rename(columns={ \
	'Transaction Number' : 'Transaction ID', \
	'Description' : 'El_Description', \
	'Memo' : 'El_Memo', \
	'Check Number' : 'El_Check Number'
	}, inplace=True)

dfe[['El_Description']] = dfe[['El_Description']].astype(str)
dfe[['El_Memo']] = dfe[['El_Memo']].astype(str)
dfe[['Amount Debit']] = dfe[['Amount Debit']].astype(float)
dfe['Amount Debit'].fillna(0, inplace=True)
dfe[['Amount Credit']] = dfe[['Amount Credit']].astype(float)
dfe['Amount Credit'].fillna(0, inplace=True)
dfe['Amount'] = dfe['Amount Debit'] + dfe['Amount Credit']
dfe['Date'] = pd.to_datetime(dfe['Date'], format='%m/%d/%Y')
dfe['Month'] = dfe['Date'].apply(lambda dt: int(dt.strftime('%Y%m')))
dfe['Year'] = dfe['Date'].apply(lambda dt: int(dt.strftime('%Y')))
dfe['For Month'] = dfe['Month']
dfe['Entries'] = 1
#dfe_pre2013 = dfe[dfe['Date'] < '01-01-2013']
#dfe = dfe[dfe['Date'] >= '01-01-2013']

dfe1 = dfe.copy()

# 2011 through 2014, checking + savings: 457 entries, 13 columns

def assign_cats_el(s):
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
	
	how = 'UNKNOWN'
	who = 'UNKNOWN'
	what1 = 'UNKNOWN'
	what2 = 'UNKNOWN'
	what3 = 'na'
	
	########## Assign simple how = EFT, ATM, Check ##########
	if ('WITHDRAWAL BILL PAYMENT' in s['El_Description'].upper()) | \
		('WITHDRAWAL WESTERN' in s['El_Description'].upper()) | \
		('WITHDRAWAL KREIZEL' in s['El_Description'].upper()) | \
		(' FEE' in s['El_Description'].upper()):
		how =  'EFT'
	elif 'ATM' in s['El_Description'].upper():
		how = 'ATM'
	elif ('BY CHECK' in s['El_Description'].upper()) | \
		(('DRAFT' in s['El_Description'].upper()) & (s['Amount'] < 0)):
		how = 'check'
		
	########## Dues, Donations, Dividends, some Fees ##########
	if ('SQUARE' in s['El_Memo'].upper()) | \
		('SQC' in s['El_Memo'].upper()) | \
		('SQUARE' in s['El_Description'].upper()):
		how = 'EFT'
		who = 'Square'
		what2 = 'Dues and Donations'
	elif ('PAYPAL' in s['El_Memo'].upper()) | \
		('PAYPAL' in s['El_Description'].upper()):
		how = 'EFT'
		who = 'Paypal'
		if s['Amount'] > 0:
			what3 = 'Transfers'
		else:
			what3 = 'Fees Monthly'
	elif ('PP' in s['El_Memo'].upper()) & \
		(s['El_Description'] == 'Withdrawal'):
		how = 'EFT'
		who = 'Paypal'
		what3 = 'Fees Other'
	elif 'DEPOSIT ADJUSTMENT' in s['El_Description'].upper():
		how = 'ATM' # eg deposit said 75 but check was for 70
		who = 'Geoffrey Terrell'
		what3 = 'Dues Monthly'
	elif 'HOME BANKING' in s['El_Description'].upper():
		how =  'EFT'
		who = 'Self'
		what3 = 'Transfers'
	elif 'DIVIDEND' in s['El_Description'].upper():
		how =  'EFT'
		who = 'Elevations'
		what3 = 'Dividends'
	elif 'DEPOSIT' in s['El_Description'].upper():
		what2 = 'Dues and Donations'
	
	########## Fees ##########
	elif s['El_Description'] == 'Business Fee':
		how = 'EFT'
		who = 'Elevations'
		what3 = 'Fees Monthly'
	elif (s['El_Description'] == 'Courtesy Pay Fee') | \
		('ITEM FEE STALE DATE' in s['El_Memo'].upper()):
		# Courtesy pay fee for? not sure why
		how =  'EFT'
		who = 'Elevations'
		what3 = 'Fees Other'
	
	########## Rent and Utilities ##########
	elif (s['El_Description'] == 'Withdrawal by Check') & \
		(s['Month'] >= 201202) & (s['Month'] <= 201204):
		who = 'Westland'
		what3 = 'Rent'
	elif ('Draft' in s['El_Description']) & (s['Month'] <= 201303) & \
		(s['Amount'] == -1250):
		who = 'Westland'
		what3 = 'Rent'
	elif (s['El_Description'] == 'Draft 000127') | \
		(s['El_Description'] == 'Draft 000157') | \
		(s['El_Description'] == 'Draft 000158') | \
		(s['El_Description'] == 'Draft 000159') | \
		(s['El_Description'] == 'Draft 000177') | \
		(s['El_Description'] == 'Draft 000179'):
		who = 'Westland'
		what3 = 'Utilities'
	elif (s['El_Description'] == 'Draft 000151') | \
		(s['El_Description'] == 'Draft 000180') | \
		(s['El_Description'] == 'Draft 000181') | \
		(s['El_Description'] == 'Draft 000182') | \
		(s['El_Description'] == 'Draft 000183'):
		who = 'Westland'
		what3 = 'Rent and Utilities'
	
	elif (s['El_Description'] == 'Draft 000184') | \
		((s['Date'] == '04/03/2014') & (s['Amount'] == -61.46)):
		who = 'Kreizel'
		what3 = 'Rent'
	elif (s['El_Description'] == 'Draft 000227') | \
		(('KREIZEL' in s['El_Description'].upper()) & (s['Month'] == 201406)):
		who = 'Kreizel'
		what3 = 'Utilities'
	elif (s['El_Description'] == 'Draft 000226') | \
		(s['El_Description'] == 'Draft 000228') | \
		(s['El_Description'] == 'Draft 000229') | \
		(s['El_Description'] == 'Draft 000231') | \
		('KREIZEL' in s['El_Description'].upper()) | \
		('KREIZEL' in s['El_Memo'].upper()):
		who = 'Kreizel'
		what3 = 'Rent and Utilities'
	
	########## Internet, Trash ##########
	elif ('LIVE WIRE' in s['El_Memo'].upper()) | \
		('LIVE WIRE' in s['El_Description'].upper()) | \
		(s['El_Description'] == 'Draft 000101'):
		who = 'Live Wire'
		what3 = 'Internet'
	elif 'WESTERN DISPOSAL' in s['El_Description'].upper():
		who = 'Western Disposal'
		what3 = 'Trash'
	
	########## Special Items ##########
	elif s['El_Description'] == 'Draft 000152':
		who = 'Mill'
		what2 = 'Special Expense'
		what3 = 'Mill'
	elif s['El_Description'] == 'Draft 000202':
		who = 'John English'
		what2 = 'Special Expense'
		what3 = 'Reimburse Kreizel Deposit'	
	
	########## Misc Expenses ##########
	# what2 categories: Consumables, Equipment, Insurance, 
	# Promotional, Taxes, Fees, Other
	elif s['El_Description'] == 'Draft 000206':
		# 4/4/14 Jim Turpin for shelf materials, paid by Liz
		who = 'Reimburse Member'
		what3 = 'Equipment'	
	elif s['El_Description'] == 'Draft 000233':
		# 4/8/14 Loveland Mini Maker Faire exhibit dues, paid by Joel
		who = 'Making Progress'
		what3 = 'Promotional'	
	elif (s['El_Description'] == 'Draft 000207') | \
		(s['El_Description'] == 'Draft 000205'):
		who = 'Taxworks'
		what3 = 'Taxes'
	elif (s['El_Description'] == 'Draft 000230') | \
		(s['El_Description'] == 'Draft 000234') | \
		(s['El_Description'] == 'Draft 000203'):
		# note Draft 203 insurance reimbursed Dan Z for 2012
		who = 'Agostini'
		what3 = 'Insurance'	
	elif (s['El_Description'] == 'Draft 000232'):
		who = 'Reimburse Member'
		what3 = 'Promotional'
	elif (s['El_Description'] == 'Draft 000204'):
		who = 'Reimburse Member'
		what3 = 'Equipment'
	elif 'Withdrawal' in s['El_Description']:
		if 'ITEM STALE DATE' in s['El_Memo'].upper():
			who = 'Zooko'
			what3 = 'Dues Other'
		elif 'SOS REGISTRATION' in s['El_Memo'].upper():
			who = 'CO Sec of State'
			what3 = 'SOS Registration'
		
		consumables = ['FDX', 'Home Depot', 'ID Enhancements', \
			'King Soopers', 'Office Max', 'Safeway', 'Target', \
			'Walmart', 'USPS']
		equipment = ['Aleph Objects', 'McGuckin', 'SparkFun']
		promotional = ['Meetup', 'StickerGiant', 'Vistaprint'] 
		otherexp = ['Blackjack Pizza', 'Moes Broadway Bagel', \
			'Nolo', 'Rebay']
		for company in consumables:
			if company.upper() in s['El_Memo'].upper():
				who = company
				what3 = 'Consumables'
		for company in equipment:
			if company.upper() in s['El_Memo'].upper():
				who = company
				what3 = 'Equipment'
		for company in promotional:
			if company.upper() in s['El_Memo'].upper():
				who = company
				what3 = 'Promotional'
		for company in otherexp:
			if company.upper() in s['El_Memo'].upper():
				who = company
				what3 = 'Other'
	
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
		'how': how,
		'who' : who,
		'what1' : what1, 
		'what2' : what2,
		'what3' : what3})

# dfe = dfe1
dfe_cats = dfe.apply(assign_cats_el, axis=1)
dfe = dfe.join(dfe_cats)

dfe2 = dfe.copy()

################################################################
# Split what3 = 'Rent and Utilities' 
################################################################
# ? try? df.append(s, ignore_index=True)

#dfe2[dfe2['what3'] == 'Rent and Utilities'][['Amount','Entries']].groupby(dfe2['El_Description']).sum()
#dfe2[dfe2['what3'] == 'Rent and Utilities'][['Amount','Entries']].groupby(dfe2['Date']).sum()

def split_rentutil(s):
	if s['Month'] < 201304:
		rent = -1250
		utilities = s['Amount'] - rent
	elif s['Month'] < 201308:
		utilities = -150
		rent = s['Amount'] - utilities
	elif s['Amount'] > -200:
		utilities = 0
		rent = s['Amount']
	else:
		utilities = -200
		rent = s['Amount'] - utilities
	return pd.Series({'Rent': rent, 'Utilities': utilities})

dfe_not_ru = dfe[dfe['what3'] != 'Rent and Utilities']

dfe_rent = dfe[dfe['what3'] == 'Rent and Utilities']
dfe_rent['what3'] = 'Rent'
dfe_rent['Amount'] = dfe_rent.apply(split_rentutil, axis=1)['Rent']

dfe_util = dfe[dfe['what3'] == 'Rent and Utilities']
dfe_util['what3'] = 'Utilities'
dfe_util['Amount'] = dfe_util.apply(split_rentutil, axis=1)['Utilities']

dfe = pd.concat([dfe_not_ru, dfe_rent, dfe_util])

#dfe_rent[['Date','what3','who','Amount']].sort('Date')
#dfe_util[['Date','what3','who','Amount']].sort('Date')

dfe3 = dfe.copy()


################################################################
# Split what2 = 'Dues and Donations'... 
# first need to reconcile totals, then if matches, substitute detail
################################################################
#dfe[dfe['what2'] == 'Dues and Donations'] # who=Square and UNKNOWN
# preprocessing: add fields needed for Paypal merging
dfe['Attendees'] = 0
dfe['Dues_Disc'] = 0	
dfe['Dues_Rate'] = 0
dfe['Mbrs'] = 0	
dfe['Mbrs_Reg'] = 0	
dfe['Mbrs_SS'] = 0	
dfe['Mbrs_Fam'] = 0	
dfe['Mbrs_UNK'] = 0	

dfe_dd = dfe[dfe['what2'] == 'Dues and Donations'] # shape: 143
dfe_nodd = dfe[dfe['what2'] != 'Dues and Donations'] # shape: 339
dfe_dd_bydt = dfe_dd['Amount'].groupby(dfe_dd['Date']).sum()

# Read in and process Revenue Detail from spreadsheet
# this will have cash/check dues and donations
df_revdtl = pd.read_csv(pathFinances + 'RevenueDetail.csv',skiprows=8)
df_revdtl['Amount'] = df_revdtl['Amount'].str.replace(r'$', '')
df_revdtl['Amount'] = df_revdtl['Amount'].str.replace(r',', '').astype(float)
df_revdtl['Date'] = pd.to_datetime(df_revdtl['Date'], format='%m/%d/%Y')
df_revdtl['For Date'] = pd.to_datetime(df_revdtl['For Date'], format='%m/%d/%Y')

# get only Elevations data
df501c3box = df_revdtl[df_revdtl['Payhow'] == '501c3box']
dfdd = df_revdtl[df_revdtl['Payhow'].isin(['cash','check','square'])]
dfdd = dfdd[dfdd['Category'] != 'Flotations']

# summarize by month, merge to Elevations data and reconcile
dfdd_bydt = dfdd['Amount'].groupby(dfdd['Date']).sum()
dd_compare = pd.merge(
	dfdd_bydt.reset_index(), 
	dfe_dd_bydt.reset_index(), 
	how='outer', on='Date', sort = 'TRUE')

dd_compare.columns = ['Date','Spreadsheet','Elevations']
dd_compare.fillna(0, inplace=True)
dd_compare['Diff'] = dd_compare['Spreadsheet'] - dd_compare['Elevations']

# check for differences, do not have detail before 2013, and 3 dates in 2013
#dd_compare[(dd_compare['Diff'] != 0) & (dd_compare['Elevations'] != 0) & (dd_compare['Date'] > '12-31-2012') & (dd_compare['Date'] < '01-01-2015')]

# next, for dates that matched and 0 diff, substitute detail rev data
# get subset to substitute: get list of dates, then subset on it
dd_subs_datelist = list(dd_compare[(dd_compare['Diff'] == 0) & \
	(dd_compare['Elevations'] != 0) & \
	(dd_compare['Date'] > '12-31-2012') & \
	(dd_compare['Date'] < '01-01-2015')]['Date'])

dfe_nosubs = dfe_dd[~dfe_dd['Date'].isin(dd_subs_datelist)] # shape 67
dfe_subs1 = dfe_dd[dfe_dd['Date'].isin(dd_subs_datelist)] # shape 76
dfe_subs1['Amount'].sum() # 7907.35

# reduce so there is only one row per date, before merging to detail by date
dfekeep = ['Date', 'Account', 'Month', 'Year', 'Entries', 'what1']
dfe_subs2 = dfe_subs1[dfekeep].drop_duplicates() # shape 43
dfddkeep = ['yrmo', 'Date', 'Category', 'Amount', 'From', \
	'Payhow', 'For Date', 'Qty']

dfe_subs3 = pd.merge(dfe_subs2, dfdd[dfddkeep], on='Date', \
	suffixes = ('', '_y')) # shape 187
#dfe_nosubs.shape, dfe_subs1.shape, dfe_subs2.shape, dfe_subs3.shape


# assign straightforward columns
dfe_subs3['SourceFile'] = 'Rev Detail'
dfe_subs3['how'] = dfe_subs3['Payhow']
dfe_subs3['who'] = dfe_subs3['From']
dfe_subs3['For Month temp'] = [int(d.strftime('%Y%m')) if not pd.isnull(d) \
	else 0 for d in dfe_subs3['For Date']]

# assign less straightforward or derived columns
def assign_dddtl(s):
	''' Assign dues / donations detail fields. Note set it up
	so that payments for multiple months are in separate rows.'''
	Attendees = 0
	Dues_Rate = 0
	Mbrs = 0
	Mbrs_Reg = 0
	Mbrs_SS = 0
	Mbrs_Fam = 0
	Mbrs_UNK = 0
	Dues_Disc = 0
	what2 = s['Category']
	what3 = 'na'
	
	if s['For Month temp'] == 0: 
		For_Month = int(s['Date'].strftime('%Y%m'))
	else: 
		For_Month = s['For Month temp']
	
	if s['Category'] == 'Workshop':
		what2 = 'Workshops'
		Attendees = max(1,s['Qty'])
	elif s['Category'] == 'Donation':
		what2 = 'Donations'
	
	elif s['Category'] == 'Dues Monthly':
		what2 = 'Dues'
		what3 = 'Dues Monthly'
		Mbrs = 1
		if (s['For Month temp'] == 201412) & (s['who'] == 'John West'):
			Mbrs_SS = 0.5 # 12/1/14 dues split over 2 months
			Mbrs = 0.5
			Dues_Rate = 25.0
		elif ((s['Amount'] >= 11) & (s['Amount'] <= 13)) | \
			((s['Amount'] >= 23) & (s['Amount'] <= 25)) | \
			(s['Amount'] == 30) | (s['Amount'] == 40):
			Mbrs_SS = 1
			Dues_Rate = 25.0
		elif ((s['Amount'] >= 35) & (s['Amount'] <= 38)) | \
			((s['Amount'] >= 62) & (s['Amount'] <= 65)) | \
			((s['Amount'] >= 71) & (s['Amount'] <= 75)):
			Mbrs_Reg = 1
			if (s['Amount'] >= 62) & (s['Amount'] <= 65):
				Dues_Rate = 65.0
			else:
				Dues_Rate = 75.0
		elif ((s['Amount'] >= 48) & (s['Amount'] <= 50)) | \
			((s['Amount'] >= 95) & (s['Amount'] <= 100)):
			Mbrs_Fam = 1
			Dues_Rate = 100.0
		else:
			Mbrs_UNK = 1
		if (Mbrs == 1) & \
			(((s['Amount'] >= 11) & (s['Amount'] <= 13)) | \
			((s['Amount'] >= 31) & (s['Amount'] <= 33)) | \
			((s['Amount'] >= 35) & (s['Amount'] <= 38)) | \
			((s['Amount'] >= 46) & (s['Amount'] <= 50))):
			Dues_Disc = 1
	
	return pd.Series({
		'what2' : what2,
		'what3' : what3,
		'For Month' : For_Month,
		'Attendees' : Attendees, 
		'Dues_Rate': Dues_Rate,
		'Mbrs' : Mbrs,
		'Mbrs_Reg' : Mbrs_Reg,
		'Mbrs_SS' : Mbrs_SS,
		'Mbrs_Fam' : Mbrs_Fam,
		'Mbrs_UNK' : Mbrs_UNK,
		'Dues_Disc' : Dues_Disc})


dfe_subs3b = dfe_subs3.apply(assign_dddtl, axis=1)
dfe_subs4 = dfe_subs3.join(dfe_subs3b)

dfe_subs4['Amount'].sum() # 7907.35



dfe['Amount'].sum() # 4989.64
dfe = pd.concat([dfe_nodd, dfe_nosubs, dfe_subs4])
dfe['Amount'].sum() # 4989.64

dfe4 = dfe.copy()


################################################################
# Get primary fields (to be merged with Paypal data) and a csv copy
################################################################
dfe['For Year'] = dfe['For Month'].apply(lambda ym: int(ym/100))
dfekeep = ['Date', 'Month', 'For Year', 'For Month', \
	'Account', 'SourceFile', 'Transaction ID', \
	'how', 'who', 'what1', 'what2', 'what3', 
	'Amount', 'Balance', 'Entries', \
	'Attendees', 'Dues_Disc', 'Dues_Rate', \
	'Mbrs', 'Mbrs_Reg', 'Mbrs_SS', 'Mbrs_Fam', 'Mbrs_UNK', \
	'El_Description', 'El_Memo', 'El_Check Number']
dfe = dfe[dfekeep]

dfe.to_csv(pathElevations + 'dfe.csv')

################################################################
# Summaries (note, by Name may not print them all...)
################################################################
sumvars = ['Amount', 'Entries', 'Attendees', 'Mbrs', 'Dues_Disc']
mbrvars = ['Mbrs', 'Mbrs_Reg', 'Mbrs_SS', 'Mbrs_Fam', 'Mbrs_UNK']

dfecur = dfe[(dfe['Date'] >= '01-01-2013') & (dfe['Date'] < '02-15-2015')]
dfecur_dues = dfecur[dfecur['what2'] == 'Dues']

dfecur[sumvars].groupby(dfecur['Account']).sum()
dfecur[mbrvars].groupby(dfecur['Account']).sum()
dfecur[sumvars].groupby(dfecur['Month']).sum()
dfecur[sumvars].groupby(dfecur['For Month']).sum()


dfecur[sumvars].groupby(dfecur['how']).sum()
dfecur[sumvars].groupby(dfecur['what1']).sum()
dfecur[sumvars].groupby(dfecur['what2']).sum()
dfecur[sumvars].groupby(dfecur['what3']).sum()

dfecur_dues[sumvars].groupby(dfecur_dues['Dues_Rate']).sum()
dfecur_dues[mbrvars].groupby(dfecur_dues['Dues_Rate']).sum()
dfecur_dues[sumvars].groupby(dfecur_dues['Mbrs']).sum()
dfecur_dues[mbrvars].groupby(dfecur_dues['Mbrs']).sum()

dfecur_dues[sumvars].groupby(dfecur_dues['For Month']).sum()
dfecur_dues[mbrvars].groupby(dfecur_dues['For Month']).sum()

dfecur_exp = dfecur[dfecur['what1'] == 'Expenses']
dfecur_exp[sumvars].groupby(dfecur_exp['who']).sum()


################################################################
# Use for troubleshooting
################################################################
dfecur[dfecur['what2'] == 'Dues and Donations']
dfecur[dfecur['Mbrs_UNK'] != 0]

x = dfecur_dues[dfecur_dues['Mbrs_UNK'] != 0]
x = dfe[(dfe['Name'] == '') & (dfe['For Month'] == 201404)]

x = dfecur_dues[dfecur_dues['Dues_Rate'] == 0]

x[['Name','Date','Gross','Dues_Rate','Mbrs','Type', 'Option 1 Value']].sort('Date')
x[['Name','Date','Gross','Amount','what2','Dues_Rate','Dues_Disc','Type','Mbrs','Mbrs_Reg','Mbrs_SS','Mbrs_UNK']].sort('Date')
x[['Name','Date','Gross','Type', 'Option 1 Value']].sort('Date')


################################################################
# To do
################################################################
# Elevations:
# make it give 12/31 balances - note will not always have a 12/31 entry...
#dfecur[dfecur['Date'] == '12/05/2012'][sumvars].groupby(dfecur['Account']).sum()
# Dues and Donations, still unknown: 2/1/13 $139 of 259 and 3/22/13 $680 of 995, total 1254


################################################################
# CONSIDER FOR CHANGES: 
# What is proper way to handle these things: Zooko stale checks 12/5/12, John E Reimburse Kreizel Deposit, Dan Z reimburse insurance, reimbursing members in general, see drafts 202, 203, 204, 206, 232... who = the underlying who, or the member? (and, not always a member, eg Christa)
# could split Debit -1253 into 3 fee, 1250 Rent (201202-201204): who = 'Rent'
# do NOT know what this is - ask other admins?:
#326  10/07/2014                     Withdrawal     0.00  -100.00
################################################################


################################################################
# NOTES - treatment of special situations above
################################################################
