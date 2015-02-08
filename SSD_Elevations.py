#!//anaconda/bin/python
import os, csv, re, datetime, numpy
import pandas as pd

################################################################
# Read in and process Elevations data
################################################################
pathElevations = '/Users/lizbaumann/Liz/SSD/_Elevations/'

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
dfe.rename(columns={'Amount Credit':'Credit', 'Amount Debit':'Debit'}, inplace=True)
dfe[['Debit']] = dfe[['Debit']].astype(float)
dfe[['Credit']] = dfe[['Credit']].astype(float)
dfe['Debit'].fillna(0, inplace=True)
dfe['Credit'].fillna(0, inplace=True)
def getmonth(dt):
	return int(datetime.datetime.strptime(dt, '%m/%d/%Y').strftime('%Y%m'))

def getnet(series):
	return series['Debit'] + series['Credit']

dfe['Net'] = dfe.apply(getnet, axis=1)
dfe[['Net']] = dfe[['Net']].astype(float)
dfe['Net'].fillna(0, inplace=True)
dfe['Month'] = dfe['Date'].apply(getmonth)
dfe['Entries'] = 1
dfe[['Description']] = dfe[['Description']].astype(str)
dfe[['Memo']] = dfe[['Memo']].astype(str)
dfe1 = dfe

# 2011 through 2014, checking + savings: 457 entries, 13 columns


def assign_paytypes(s):
	'''Assign descriptors for every transaction:
	paytype (deposit, withdrawal), 
	how (ATM, Check, EFT),
	what (rent, utilities, dues and donations, expenses, etc.), 
	what2,
	who (Paypal, Square, etc.)'''
	
	paytype = 'UNKNOWN'
	how = 'UNKNOWN'
	what = 'UNKNOWN'
	what2 = 'na'
	who = 'UNKNOWN'
	
	########## Assign paytype = Deposit or Withdrawal ##########
	if 'DEPOSIT' in s['Description'].upper():
		paytype = 'Deposit'
	elif 'WITHDRAWAL' in s['Description'].upper():
		paytype = 'Withdrawal'
	elif s['Debit'] < 0:
		paytype = 'Withdrawal'
	elif s['Credit'] > 0:
		paytype = 'Deposit'
	
	########## Assign simple how = EFT, ATM, Check ##########
	if ('WITHDRAWAL BILL PAYMENT' in s['Description'].upper()) | \
		('WITHDRAWAL WESTERN' in s['Description'].upper()) | \
		('WITHDRAWAL KREIZEL' in s['Description'].upper()) | \
		(' FEE' in s['Description'].upper()):
		how =  'EFT'
	elif 'ATM' in s['Description'].upper():
		how = 'ATM'
	elif ('BY CHECK' in s['Description'].upper()) | \
		(('DRAFT' in s['Description'].upper()) & (s['Debit'] < 0)):
		how = 'Check'
	# else: how = 'Debit' # ??????????????
		
	########## Dues, Donations, Dividends, some Fees ##########
	if ('SQUARE' in s['Memo'].upper()) | \
		('SQC' in s['Memo'].upper()) | \
		('SQUARE' in s['Description'].upper()):
		how = 'EFT'
		who = 'Square'
		if paytype == 'Deposit':
			what = 'Dues'
		else:
			what = 'Fee Other'
	elif ('PAYPAL' in s['Memo'].upper()) | \
		('PAYPAL' in s['Description'].upper()):
		how = 'EFT'
		who = 'Paypal'
		if paytype == 'Deposit':
			what = 'Dues'
		else:
			what = 'Fee Monthly'
	elif ('PP' in s['Memo'].upper()) & \
		(s['Description'] == 'Withdrawal'):
		how = 'EFT'
		who = 'Paypal'
		what = 'Fee Other'
	elif 'DEPOSIT ADJUSTMENT' in s['Description'].upper():
		how = 'ATM' # eg deposit said 75 but check was for 70
		what = 'Dues'
		who = 'Dues Deposit Adjustment'
	elif 'HOME BANKING' in s['Description'].upper():
		how =  'EFT'
		what = 'Transfer'
		who = 'Self'
	elif 'DIVIDEND' in s['Description'].upper():
		how =  'EFT'
		what = 'Dividend'
		who = 'Elevations'
	elif 'DEPOSIT' in s['Description'].upper():
		who = 'Dues and Donations'
		what = 'Dues and Donations'
	
	########## Fees ##########
	elif s['Description'] == 'Business Fee':
		how = 'EFT'
		who = 'Elevations'
		what = 'Fee Monthly'
	elif (s['Description'] == 'Courtesy Pay Fee') | \
		('ITEM FEE STALE DATE' in s['Memo'].upper()):
		# Courtesy pay fee for? not sure why
		how =  'EFT'
		who = 'Elevations'
		what = 'Fee Other'
	
	########## Rent and Utilities ##########
	elif (s['Description'] == 'Withdrawal by Check') & \
		(s['Month'] >= 201202) & (s['Month'] <= 201204):
		who = 'Westland'
		what = 'Rent'
	elif ('Draft' in s['Description']) & (s['Month'] <= 201303) & \
		(s['Debit'] == -1250):
		who = 'Westland'
		what = 'Rent'
	elif (s['Description'] == 'Draft 000127') | \
		(s['Description'] == 'Draft 000157') | \
		(s['Description'] == 'Draft 000158') | \
		(s['Description'] == 'Draft 000159') | \
		(s['Description'] == 'Draft 000177') | \
		(s['Description'] == 'Draft 000179'):
		who = 'Westland'
		what = 'Utilities'
	elif (s['Description'] == 'Draft 000151') | \
		(s['Description'] == 'Draft 000180') | \
		(s['Description'] == 'Draft 000181') | \
		(s['Description'] == 'Draft 000182') | \
		(s['Description'] == 'Draft 000183'):
		who = 'Westland'
		what = 'Rent and Utilities'
	
	elif (s['Description'] == 'Draft 000184') | \
		((s['Date'] == '04/03/2014') & (s['Debit'] == -61.46)):
		who = 'Kreizel'
		what = 'Rent'
	elif (s['Description'] == 'Draft 000227') | \
		(('KREIZEL' in s['Description'].upper()) & (s['Month'] == 201406)):
		who = 'Kreizel'
		what = 'Utilities'
	elif (s['Description'] == 'Draft 000226') | \
		(s['Description'] == 'Draft 000228') | \
		(s['Description'] == 'Draft 000229') | \
		(s['Description'] == 'Draft 000231') | \
		('KREIZEL' in s['Description'].upper()) | \
		('KREIZEL' in s['Memo'].upper()):
		who = 'Kreizel'
		what = 'Rent and Utilities'
	
	########## Internet, Trash ##########
	elif ('LIVE WIRE' in s['Memo'].upper()) | \
		('LIVE WIRE' in s['Description'].upper()) | \
		(s['Description'] == 'Draft 000101'):
		who = 'Live Wire'
		what = 'Internet'
	elif 'WESTERN DISPOSAL' in s['Description'].upper():
		who = 'Western Disposal'
		what = 'Trash'
	
	########## Special Items ##########
	elif s['Description'] == 'Draft 000152':
		who = 'Mill'
		what = 'Mill'
	elif s['Description'] == 'Draft 000202':
		who = 'John English'
		what = 'Reimburse Kreizel Deposit'	
	
	########## Misc Expenses ##########
	# what2 categories: Consumables, Equipment, Insurance, 
	# Promotional, Taxes and Fees, Other
	elif s['Description'] == 'Draft 000206':
		# 4/4/14 Jim Turpin for shelf materials, paid by Liz
		who = 'Reimburse Member'
		what = 'Expenses'	
		what2 = 'Equipment'	
	elif s['Description'] == 'Draft 000233':
		# 4/8/14 Loveland Mini Maker Faire exhibit dues, paid by Joel
		who = 'Making Progress'
		what = 'Expenses'	
		what2 = 'Promotional'	
	elif (s['Description'] == 'Draft 000207') | \
		(s['Description'] == 'Draft 000205'):
		who = 'Taxworks'
		what = 'Taxes and Fees'	
	elif (s['Description'] == 'Draft 000230') | \
		(s['Description'] == 'Draft 000234') | \
		(s['Description'] == 'Draft 000203'):
		# note Draft 203 insurance reimbursed Dan Z for 2012
		who = 'Agostini'
		what = 'Insurance'	
	elif (s['Description'] == 'Draft 000232'):
		who = 'Reimburse Member'
		what = 'Expenses'	
		what2 = 'Promotional'
	elif (s['Description'] == 'Draft 000204'):
		who = 'Reimburse Member'
		what = 'Expenses'	
		what2 = 'Equipment'
	elif 'Withdrawal' in s['Description']:
		if 'ITEM STALE DATE' in s['Memo'].upper():
			who = 'Zooko stale date checks'
			what = 'Dues'
			what2 = 'Bank return stale check'
		elif 'SOS REGISTRATION' in s['Memo'].upper():
			who = 'CO Sec of State'
			what = 'Expenses'
			what2 = 'Taxes and Fees'
		
		consumables = ['FDX', 'Home Depot', 'ID Enhancements', \
			'King Soopers', 'Office Max', 'Safeway', 'Target', 'USPS']
		equipment = ['Aleph Objects', 'McGuckin', 'SparkFun']
		promotional = ['Meetup', 'StickerGiant', 'Vistaprint'] 
		otherexp = ['Blackjack Pizza', 'Moes Broadway Bagel', \
			'Nolo', 'Rebay']
		for company in consumables:
			if company.upper() in s['Memo'].upper():
				who = company
				what = 'Expenses'
				what2 = 'Consumables'
		for company in equipment:
			if company.upper() in s['Memo'].upper():
				who = company
				what = 'Expenses'
				what2 = 'Equipment'
		for company in promotional:
			if company.upper() in s['Memo'].upper():
				who = company
				what = 'Expenses'
				what2 = 'Promotional'
		for company in otherexp:
			if company.upper() in s['Memo'].upper():
				who = company
				what = 'Expenses'
				what2 = 'Other'
	
		
	return pd.Series({
		'Paytype' : paytype, 
		'how': how,
		'what' : what,
		'what2' : what2,
		'who' : who})

# dfe = dfe1
dfe_paytypes = dfe.apply(assign_paytypes, axis=1)
dfe = dfe.join(dfe_paytypes)

################################################################
# Split who = 'Rent and Utilities' 
################################################################

#dfe[dfe['what'] == 'Rent and Utilities'][sumvars].groupby(dfe['Description']).sum()
#dfe[dfe['what'] == 'Rent and Utilities'][sumvars].groupby(dfe['Date']).sum()

def split_rentutil(s):
	if s['Month'] < 201304:
		rent = -1250
		utilities = s['Debit'] - rent
	elif s['Month'] < 201308:
		utilities = -150
		rent = s['Debit'] - utilities
	else:
		utilities = -200
		rent = s['Debit'] - utilities
	return pd.Series({'Rent': rent, 'Utilities': utilities})

dfe2 = dfe

dfe_not_ru = dfe[dfe['what'] != 'Rent and Utilities']

dfe_rent = dfe[dfe['what'] == 'Rent and Utilities']
dfe_rent['what'] = 'Rent'
dfe_rent['Debit'] = dfe_rent.apply(split_rentutil, axis=1)['Rent']
dfe_rent['Net'] = dfe_rent['Debit']

dfe_util = dfe[dfe['what'] == 'Rent and Utilities']
dfe_util['what'] = 'Utilities'
dfe_util['Debit'] = dfe_util.apply(split_rentutil, axis=1)['Utilities']
dfe_util['Net'] = dfe_util['Debit']

dfe = pd.concat([dfe_not_ru, dfe_rent, dfe_util])

#dfe_rent[['Date','what','who','Debit','Credit']]
#dfe_util[['Date','what','who','Debit','Credit']]


################################################################
# Read in and process Revenue Detail from spreadsheet
# this will have cash/check dues and donations
################################################################
pathFinances = '/Users/lizbaumann/Liz/SSD/_Finances/'
df_revdtl = pd.read_csv(pathFinances + 'RevenueDetail.csv', skiprows=8)

df_revdtl['Amount'] = df_revdtl['Amount'].str.replace(r'$', '')
df_revdtl['Amount'] = df_revdtl['Amount'].str.replace(r',', '').astype(float)
df_revdtl.rename(columns={'yrmo':'Month'}, inplace=True)

# for checking
df_revdtl['Amount'].groupby(df_revdtl['Category']).sum()
df_revdtl['Amount'].groupby(df_revdtl['Payhow']).sum()

# get only bank data
df_dddtl = df_revdtl[df_revdtl['Payhow'].isin(['cash','check','501c3box'])]
df_dddtl = df_dddtl[df_dddtl['Category'].isin(['Dues','Donations'])]

dddtl_byyrmo = df_dddtl['Amount'].groupby(df_dddtl['Month']).sum()
# how to merge this series to the Elevations data and compare?
# Month and has no name
dddtl_byyrmo.index.names(['Month','Amount'])

pd.merge(duesdtl, donsdtl, on='Date')
duesdtl = duesdtl.join(clsdtl, on='Date')

################################################################
# Split who = 'Dues and Donations'... 108 entries of this
# first need to reconcile totals, then if matches, merge
################################################################
dfe_dd = dfe[dfe['who'] == 'Dues and Donations']
dfe_dd[['Date','Description','Credit','Debit']]
dfe_dd[['Date','Memo','Credit','Debit']]

dfe_dep_byyrmo = dfe_dep['Net'].groupby(dfe_dep['Month']).sum()
pd.concat([dddtl_byyrmo, dfe_dep_byyrmo])


dfe_dep[sumvars].groupby(dfe_dep['Month']).sum()

# Need process (a form really) for recording itemization of deposits:
# date
# what: dues, donations, workshop fees
# from who
# what2, if dues: what month(s) for dues (dues rate, # months, which months?, discount applied?)
# what2, if donation: detail e.g. beverage money or donation
# what2, if workshop: when, who was teacher, quantity (how many fees being paid)

################################################################
# Summaries (note, by Name may not print them all...)
################################################################
sumvars = ['Credit','Debit','Net','Entries']
dfe[sumvars].groupby(dfe['Account']).sum()
dfe[sumvars].groupby(dfe['Month']).sum()
dfe[sumvars].groupby(dfe['Description']).sum()

dfe[sumvars].groupby(dfe['Paytype']).sum()
dfe[sumvars].groupby(dfe['how']).sum()
dfe[sumvars].groupby(dfe['what']).sum()
dfe[sumvars].groupby(dfe['who']).sum()

# end of year balances... fails because do not always have 12/31 entries
dfe[dfe['Date'] == '12/05/2012'][sumvars].groupby(dfe['Account']).sum()

################################################################
# Use for troubleshooting
################################################################

dfex = dfe[dfe['who'] == 'UNKNOWN']
dfex[['Date','Description','Credit','Debit']]
dfex[['Date','Memo','Credit','Debit']]

# check rent and utilities
dfex = dfe[dfe['what'] == 'Rent']
dfex[sumvars].groupby(dfex['Month']).sum()
dfex = dfe[dfe['what'] == 'Utilities']
dfex[sumvars].groupby(dfex['Month']).sum()


# 248 how = UNKNOWN
# 51 what = UNKNOWN
# 51 who = UNKNOWN
# there was at least one Square payment that was a donation not dues


################################################################
# To do
################################################################
# Elevations:
# Deposits itemized: who = 'Dues and Donations'
# Square all going to dues right now, but some are not dues
# make it give 12/31 views - note will not always have a 12/31 entry...

# Everything:
# upload donations from spreadsheet?
# upload RFID info from system and from spreadsheet (for Old RFID info)
# joel and liz and others (rob, jennifer) - itemize reimbursements as dues
# workshop discounts, and other dues credits, how to do better
# build recon with spreadsheet

UNKNOWNs
           Date                    Description   Credit    Debit
# these may be regular bank or ATM deposits, probably for dues/donations
14   11/30/2011                        Deposit   100.00     0.00
15   11/29/2011                        Deposit   430.00     0.00
29   11/30/2012                        Deposit   115.00     0.00
83   07/17/2012                        Deposit   113.00     0.00
103  05/31/2012                        Deposit   195.00     0.00
107  05/10/2012                        Deposit    20.00     0.00
108  05/10/2012                        Deposit   500.00     0.00
110  05/09/2012                        Deposit   100.00     0.00
111  05/09/2012                        Deposit   300.00     0.00
129  03/02/2012                        Deposit     2.00     0.00
130  03/02/2012                        Deposit   100.00     0.00
131  03/01/2012                        Deposit   525.00     0.00
136  02/09/2012                        Deposit   223.00     0.00
139  02/01/2012                        Deposit   500.00     0.00
140  02/01/2012                        Deposit   100.00     0.00
141  02/01/2012                        Deposit   150.00     0.00
142  02/01/2012                        Deposit   161.00     0.00
257  04/30/2013                        Deposit   216.00     0.00
289  02/01/2013                        Deposit   159.00     0.00

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

# join, merge, concat
