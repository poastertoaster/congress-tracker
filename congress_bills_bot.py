import tweepy
import requests
import time
import textwrap
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

headers = {"x-api-key": "ProPublica API Key"}

#Set the fonts
titlefont = ImageFont.truetype('FRADM.TTF', 16)
sponsorfont = ImageFont.truetype('FRADM.TTF', 24)

#Set Twitter information
auth = tweepy.OAuthHandler('Consumer Key', 'Consumer Secret')
auth.set_access_token('Access Token', 'Access Secret')
api = tweepy.API(auth)

def getColor(party):
	if party == 'R':
		return (186, 16, 23)
	elif party == 'D':
		return (0, 68, 95)
	else:
		return (100, 100, 100)

def createImage(billInfo):
	#Create the Image
	createdImage = Image.new('RGB', (640, 360), color=getColor(billInfo['sponsor_party']))

	#Create the Bill Title
	titleLines = textwrap.wrap(billInfo['short_title'], 55)
	titleLineHeight = 10
	for line in titleLines:
		billName = ImageDraw.Draw(createdImage)
		bNw, bNh = billName.textsize(line, font=sponsorfont)
		billName.text((((640-bNw)/2), titleLineHeight), line, font=sponsorfont, fill='white')
		titleLineHeight += bNh

	#Create the Sponsor Name
	sponsor = billInfo['sponsor_title']+' '+billInfo['sponsor_name']
	sponsorName = ImageDraw.Draw(createdImage)
	sNw, sNh = sponsorName.textsize(sponsor, font=sponsorfont)
	sponsorName.text((10, ((360-sNh)*0.75)), sponsor, font=sponsorfont, fill='white')

	#Create the Sponsor's Image
	congressperson = requests.get('https://raw.githubusercontent.com/unitedstates/images/gh-pages/congress/225x275/'+billInfo['sponsor_id']+'.jpg')
	if congressperson.status_code == 200:
		imageData = Image.open(BytesIO(congressperson.content))
		resize = (imageData.size[0]/2, imageData.size[1]/2)
		imageData.thumbnail(resize, resample=Image.NEAREST)
		createdImage.paste(imageData, box=(630-imageData.size[0], int((360-imageData.size[1])*0.75)))
		outline = ImageDraw.Draw(createdImage)
		outline.rectangle([630-imageData.size[0], int((360-imageData.size[1])*0.75), 630, int(((360-imageData.size[1])*0.75)+imageData.size[1])], outline='white')

	#Create the Sponsor States' Flag

	#Create the Committee
	committee = ImageDraw.Draw(createdImage)
	committeeName = billInfo['committees'].replace("&#39;","'")
	lNw, lNh = committee.textsize(committeeName, font=titlefont)
	committee.text((((630-lNw)/2), 350-lNh), committeeName, font=titlefont, fill='white')

	#Create the line and stars
	star = Image.open('star.png')
	createdImage.paste(star, box=(int(320-(star.size[0]/2)), 320-lNh), mask=star)
	if billInfo['committees'] != '':
		line = ImageDraw.Draw(createdImage)
		line.line([((630-lNw)/2), 345-lNh, ((630-lNw)/2)+lNw, 345-lNh], fill='white', width=3)
		createdImage.paste(star, box=(int((630-lNw)/2), 320-lNh), mask=star)
		createdImage.paste(star, box=(int((630-lNw)/2)+lNw-star.size[0], 320-lNh), mask=star)
	else:
		createdImage.paste(star, box=(int(370-(star.size[0]/2)), 320-lNh), mask=star)
		createdImage.paste(star, box=(int(270-(star.size[0]/2)), 320-lNh), mask=star)

	createdImage.save('image.png')

def run_bot():
	lastHouseBill = getLastBill('house')
	houseBills = requests.get('https://api.propublica.org/congress/v1/116/house/bills/introduced.json', headers=headers).json()['results'][0]
	print('Checking the House for new legislation ...')
	process_bills(houseBills, lastHouseBill)
	lastSenateBill = getLastBill('senate')
	print('Checking the Senate for new legislation ...')
	senateBills = requests.get('https://api.propublica.org/congress/v1/116/senate/bills/introduced.json', headers=headers).json()['results'][0]
	process_bills(senateBills, lastSenateBill)

def getLastBill(chamber):
	file = open("last_seen_bill_"+chamber+'.txt', "r")
	last_bill = str(file.read().strip())
	file.close()
	return last_bill

def storeLastBill(chamber, last_id):
	chamber = chamber.lower()
	file = open("last_seen_bill_"+chamber+'.txt', "w")
	file.write(str(last_id))
	file.close()

def process_bills(bill_list, last_id):
	for index, bill in enumerate(bill_list['bills']):
		if index == 0:
			storeLastBill(bill_list['chamber'], bill['bill_id'])
		if bill['bill_id'] == last_id:
			return
		else:
			print(bill['short_title'])
			sponsor = requests.get(bill['sponsor_uri'], headers=headers).json()['results'][0]

			if bill['primary_subject'] == "":
				subject = ""
			else:
				subject = " #"+bill['primary_subject'].replace(" ", "").replace(",", "")

			if bill['bill_type'] == 'hres' or bill['bill_type'] == 'sres':
				billType = 'resolution'
			elif bill['bill_type'] == 'hconres':
				billType = 'concurrent resolution'
			elif bill['bill_type'] == 'hr' or bill['bill_type'] == 's':
				billType = 'bill'

			if sponsor['twitter_account'] == None:
				account = bill['sponsor_title']+' '+bill['sponsor_name']
			else:
				account = '.@'+sponsor['twitter_account']

			statusUpdate = account+' ('+bill['sponsor_party']+'-'+bill['sponsor_state']+') has introduced a '+billType+' before the '+bill_list['chamber']+'.'+subject+' '+bill['congressdotgov_url']
			createImage(bill)
			uploadedImage = api.media_upload('image.png')
			api.update_status(status=statusUpdate, media_ids=[uploadedImage.media_id])
			time.sleep(60)

while True:
	run_bot()
	time.sleep(3600)