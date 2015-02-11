#!//anaconda/bin/python
import os, csv, re, datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

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
read_elevations('Elevations_2011.csv')
read_elevations('Elevations_2012.csv')
read_elevations('Elevations_2013.csv')
read_elevations('Elevations_2014.csv')
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
dfe1 = dfe

# 2011 through 2014, checking + savings: 457 entries, 13 columns

def assign_cats_el(s):
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
		if s['Amount'] > 0:
			what3 = 'Dues Monthly'
		else:
			what3 = 'Fees Other'
	elif ('PAYPAL' in s['El_Memo'].upper()) | \
		('PAYPAL' in s['El_Description'].upper()):
		how = 'EFT'
		who = 'Paypal'
		if s['Amount'] > 0:
			what3 = 'Dues Other'
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
		what3 = 'Dues Other'
	elif 'HOME BANKING' in s['El_Description'].upper():
		how =  'EFT'
		who = 'Self'
		what2 = 'Transfers'
	elif 'DIVIDEND' in s['El_Description'].upper():
		how =  'EFT'
		who = 'Elevations'
		what2 = 'Dividends'
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
			who = 'Zooko stale date checks'
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
		'how': how,
		'who' : who,
		'what1' : what1, 
		'what2' : what2,
		'what3' : what3})

# dfe = dfe1
dfe_cats = dfe.apply(assign_cats_el, axis=1)
dfe = dfe.join(dfe_cats)

dfe2 = dfe


################################################################
# Split what3 = 'Rent and Utilities' 
################################################################
# ? try? df.append(s, ignore_index=True)

#dfe[dfe['what3'] == 'Rent and Utilities'][sumvars].groupby(dfe['El_Description']).sum()
#dfe[dfe['what3'] == 'Rent and Utilities'][sumvars].groupby(dfe['Date']).sum()

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

dfe3 = dfe


################################################################
# Split what2 = 'Dues and Donations'... 127 entries of this, 70 splittable
# first need to reconcile totals, then if matches, substitute detail
#dfe_dd['Date'] = pd.to_datetime(dfe_dd['Date'], format='%m/%d/%Y')
################################################################
# preprocessing: add fields needed for Paypal merging
dfe['Attendees'] = 0
dfe['Workshop_Disc'] = 0	
dfe['Dues_Rate'] = 0
dfe['Mbrs'] = 0	
dfe['Mbrs_Reg'] = 0	
dfe['Mbrs_SS'] = 0	
dfe['Mbrs_Fam'] = 0	
dfe['Mbrs_UNK'] = 0	

dfe_dd = dfe[dfe['what2'] == 'Dues and Donations'] # 127
dfe_nodd = dfe[dfe['what2'] != 'Dues and Donations'] # 355
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
dfdd = df_revdtl[df_revdtl['Payhow'].isin(['cash','check'])]
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

# next, for dates that matched and 0 diff, substitute detail rev data
# get subset to substitute: get list of dates, then subset on it
dd_subs_datelist = list(dd_compare[(dd_compare['Diff'] == 0) & \
	(dd_compare['Elevations'] != 0) & \
	(dd_compare['Date'] > '12-31-2012') & \
	(dd_compare['Date'] < '01-01-2015')]['Date'])

dfe_nosubs = dfe_dd[~dfe_dd['Date'].isin(dd_subs_datelist)] # 59
dfe_subs1 = dfe_dd[dfe_dd['Date'].isin(dd_subs_datelist)] # 68
dfe_subs1['Amount'].sum() # 7642.81

# reduce so there is only one row per date, before merging to detail by date
dfekeep = ['Date', 'Account', 'Month', 'Year', 'Entries', 'what1']
dfe_subs2 = dfe_subs1[dfekeep].drop_duplicates() # 36
dfddkeep = ['yrmo', 'Date', 'Category', 'Amount', 'From', \
	'Payhow', 'For Date', 'Qty']

dfe_subs3 = pd.merge(dfe_subs2, dfdd[dfddkeep], on='Date', \
	suffixes = ('', '_y')) # 178

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
	Workshop_Disc = 0
	what2 = s['Category']
	what3 = 'na'
	
	if s['Category'] == 'Workshop':
		what2 = 'Workshops'
		Attendees = max(1,s['Qty'])
	elif s['Category'] == 'Donation':
		what2 = 'Donations'
	
	elif s['Category'] == 'Dues Monthly':
		what2 = 'Dues'
		what3 = 'Dues Monthly'
		Dues_Rate = s['Amount'] # enough??
		Mbrs = 1
		if (s['Amount'] == 12.5) | \
			(s['Amount'] == 25) | \
			(s['Amount'] == 40):
			Mbrs_SS = 1
		if (s['Amount'] == 37.5) | \
			(s['Amount'] == 75):
			Mbrs_Reg = 1
		if (s['Amount'] == 50) | \
			(s['Amount'] == 100):
			Mbrs_Fam = 1
		else:
			Mbrs_UNK = 1
		if (s['Amount'] == 12.5) | \
			(s['Amount'] == 37.5) | \
			(s['Amount'] == 50):
			Workshop_Disc = 1
			Mbrs = Mbrs * .5
			Mbrs_Reg = Mbrs_Reg * .5
			Mbrs_SS = Mbrs_SS * .5
			Mbrs_Fam = Mbrs_Fam * .5
			Mbrs_UNK = Mbrs_UNK * .5
	
	if s['For Month temp'] == 0: 
		For_Month = int(s['Date'].strftime('%Y%m'))
	else: 
		For_Month = s['For Month temp']
	
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
		'Workshop_Disc' : Workshop_Disc})


dfe_subs3b = dfe_subs3.apply(assign_dddtl, axis=1)
dfe_subs4 = dfe_subs3.join(dfe_subs3b)

#dfe_subs4['Amount'].sum() # 7642.81



# dfe['Amount'].sum() # 4989.64
dfe = pd.concat([dfe_nodd, dfe_nosubs, dfe_subs4])
# dfe['Amount'].sum() # 4989.64

dfe4 = dfe


################################################################
# Next: 
################################################################
# include square payment detail
# dues month in subs4 should be from the 'For Date' field!?!?
# remove all other columns? dfe_dd.columns

dfekeep = ['Date', 'Year', 'Month', 'For Month', \
	'Account', 'SourceFile', 'Transaction ID', \
	'how', 'who', 'what1', 'what2', 'what3', 
	'Amount', 'Balance', 'Entries', \
	'Attendees', 'Workshop_Disc', 'Dues_Rate', \
	'Mbrs', 'Mbrs_Reg', 'Mbrs_SS', 'Mbrs_Fam', 'Mbrs_UNK', \
	'El_Description', 'El_Memo', 'El_Check Number']
dfe = dfe[dfekeep]


dfe.to_csv('dfe.csv')

################################################################
# Summaries (note, by Name may not print them all...)
################################################################
sumvars = ['Amount','Entries']
dfe[sumvars].groupby(dfe['Account']).sum()
dfe[sumvars].groupby(dfe['Month']).sum()
dfe[sumvars].groupby(dfe['El_Description']).sum()

dfe[sumvars].groupby(dfe['how']).sum()
dfe[sumvars].groupby(dfe['who']).sum()
dfe[sumvars].groupby(dfe['what1']).sum()
dfe[sumvars].groupby(dfe['what2']).sum()
dfe[sumvars].groupby(dfe['what3']).sum()

# end of year balances... fails because do not always have 12/31 entries
dfe[dfe['Date'] == '12/05/2012'][sumvars].groupby(dfe['Account']).sum()

################################################################
# Use for troubleshooting
################################################################

dfex = dfe[dfe['who'] == 'UNKNOWN']
dfex[['Date','El_Description','Amount']]
dfex[['Date','El_Memo','Amount']]

# check rent and utilities
dfex = dfe[dfe['what2'] == 'Rent']
dfex[sumvars].groupby(dfex['Month']).sum()
dfex = dfe[dfe['what2'] == 'Utilities']
dfex[sumvars].groupby(dfex['Month']).sum()



################################################################
# To do
################################################################
# Elevations:
# Square all going to dues right now, but some are not dues, also need mbrs
# there was at least one Square payment that was a donation not dues
# make it give 12/31 views - note will not always have a 12/31 entry...

# Everything:
# upload RFID info from system and from spreadsheet (for Old RFID info)
# joel and liz and others (rob, jennifer) - itemize reimbursements as dues
# workshop discounts, and other dues credits, how to do better
# build recon with spreadsheet

# Need process (a form really) for recording itemization of deposits:
# date
# what: dues, donations, workshop fees
# from who
# what2, if dues: what month(s) for dues (dues rate, # months, which months?, discount applied?)
# what2, if donation: detail e.g. beverage money or donation
# what2, if workshop: when, who was teacher, quantity (how many fees being paid)
# special for 501c3


# do NOT know what this is - ask other admins?:
326  10/07/2014                     Withdrawal     0.00  -100.00



################################################################
# CONSIDER FOR CHANGES: 
# Zooko stale date checks treatment (12/05/2012)
# could split Debit -1253 into 3 fee, 1250 Rent (201202-201204): who = 'Rent'
# reimbursing members: how to handle? see drafts 202, 203, 204, 206, 232... who = the underlying who, or the member? (and, not always a member, eg Christa)
################################################################


################################################################
# NOTES - treatment of special situations above
################################################################
