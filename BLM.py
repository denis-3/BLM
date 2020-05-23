# Required Initialization
import requests
import RPi.GPIO as GPIO
import time
import paramiko
import os
import papirus
import picamera
import sys
from PIL import Image
from threading import Thread
import zbarlight
GPIO.setmode(GPIO.BCM)

# Define variables, GPIO ports, and perform other tasks
GPIO.setup(21, GPIO.IN, GPIO.PUD_UP) # Coin Acceptor
GPIO.setup(20, GPIO.IN, GPIO.PUD_UP) # Button
oldTime = 0
newTime = 0
timeDiff = 0
totalCoinPulses = 0
isPulsing = True
totalCoinValue = 0
timeDiff = 0
perSymbol = "%"
totalCoinPulses = 0
isPulsing = True
continueThread = True
buttonPressed = True
totalCoinValue = 0
error = False
qrcontent = "" # This variable stores the information of the QR code, which will be changed later
timestamp = str(time.time()) # This variable will be changed later
#
camera = picamera.PiCamera()
camera.led = False
#
text = papirus.PapirusText()
screen = papirus.Papirus()
#
ssh = paramiko.SSHClient()
channel = paramiko.channel.Channel
#
streamPicNum = -1
#
response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json")
btcPrice = response.json()["bpi"]["USD"]["rate"]
btcPriceFloat = response.json()["bpi"]["USD"]["rate_float"]
threshold = len(btcPrice)-2
btcPrice = "$" + btcPrice[:threshold]
oldBtcPrice = btcPrice
satoshi = btcPriceFloat / 100000000
#
imgCounters = [1, 2, 3, 4, 5]
#
def takePictureBursts():
        global imgCounter
        global continueThread
        camera.shutter_speed = 16667
        camera.start_preview()
        time.sleep(1.5)
        while continueThread == True:
                camera.capture_sequence([
                        '/home/pi/blmfiles/temppics/image%s.jpg'%(imgCounters[0]),
                        '/home/pi/blmfiles/temppics/image%s.jpg'%(imgCounters[1]),
                        '/home/pi/blmfiles/temppics/image%s.jpg'%(imgCounters[2]),
                        '/home/pi/blmfiles/temppics/image%s.jpg'%(imgCounters[3]),
                        '/home/pi/blmfiles/temppics/image%s.jpg'%(imgCounters[4])
                ])
                print("done capture of 5 images")
                for i in range(5):
                        if continueThread == True:
                                Thread(target=analyzePicture, args=['image%s'%(imgCounters[i])]).start()
                for i in range(5):
                        imgCounters[i] += 5
        camera.stop_preview()
#
def analyzePicture(img):
        global qrcontent
        global continueThread
        tempCode = None
        if continueThread == True:
                with open('/home/pi/blmfiles/temppics/%s.jpg'%(img), 'rb') as pic_file:
                        pic = Image.open(pic_file)
                        pic.load()
                tempCode = str(zbarlight.scan_codes(['qrcode'], pic))
                if tempCode == "None":
                        print('done anaylzing %s. No QR CODE FOUND'%(img))
                        os.system('sudo rm /home/pi/blmfiles/temppics/%s.jpg'%(img))
                else:
                        qrcontent = tempCode[3:-2]
                        print("~~~Done! QR code found in %s: %s~~~"%(img, qrcontent))
                        continueThread = False
# Pre-loop code
os.system('papirus-write \'Welcome to BLM\nPress the button to begin\nOne Cent: %s sat(s)\nBTC Price: %s + 10%s\' --fsize 15'%(str(round(0.01/satoshi,0))[:-2],btcPrice,perSymbol))

# Idle Screen
while buttonPressed == True:
        buttonPressed = GPIO.input(20)
        if error == True:
                buttonPressed = True
                response = requests.get("https://api.coindesk.com/v1/bpi/currentprice.json")
        if response.status_code != 200 and error == False:
                error = True
                os.system('papirus-write \'Sorry, but we cannot retrieve data about the Bitcoin price. This is most likely a temporary error, so stick around!\' --fsize 15')
        elif response.status_code == 200 and error == True:
                error = False
        if oldBtcPrice != btcPrice and error == False:
                oldBtcPrice = btcPrice
                btcPriceFloat = response.json()["bpi"]["USD"]["rate_float"]
                satoshi = btcPriceFloat / 100000000
                os.system('papirus-write \'Welcome to BLM\nPress the button to begin\nOne Cent: %s sat\nBTC Price: %s + 10%s\' --fsize 15'%(str(round(0.01/satoshi,0))[:-2],btcPrice,perSymbol))
                error = False
        elif error == False:
                error = False
                btcPrice = response.json()["bpi"]["USD"]["rate"]
                threshold = len(btcPrice)-2
                btcPrice = "$" + btcPrice[:threshold]
buttonPressed = True
os.system('papirus-write \'Please insert coin(s)\' --fsize 15')
#nNote: around %s cent(s) will be deducted from your conversion because of transaction fees\' --fsize 15'%(str(round(satoshi*1000/0.01,0))[:-2]))
btcPriceFloat = btcPriceFloat * 1.1
satoshi = btcPriceFloat / 100000000
# Detect coins
while buttonPressed == True:
        buttonPressed = GPIO.input(20)
        isPulsing = GPIO.input(21)
        oldTime = time.time()
        timeDiff = 0
        while timeDiff < 0.3:
                isPulsing = GPIO.input(21)
                newTime = time.time()
                timeDiff = newTime - oldTime
                if isPulsing == False:
                        totalCoinPulses = totalCoinPulses + 1
                        while isPulsing == False:
                                isPulsing = GPIO.input(21)
                        oldTime = time.time()
        if totalCoinPulses >= 1 and error == False:
                if totalCoinPulses == 2:
                        totalCoinValue = totalCoinValue + 0.01
                elif totalCoinPulses == 3:
                        totalCoinValue = totalCoinValue + 0.05
                elif totalCoinPulses == 4:
                        totalCoinValue = totalCoinValue + 0.10
                elif totalCoinPulses == 5:
                        totalCoinValue = totalCoinValue + 0.25
                elif totalCoinPulses == 6:
                        totalCoinValue = totalCoinValue + 1
                if totalCoinPulses > 1:
                        text.write('Inserted: $%s \n Satoshi(s): %s\n\nPress the button when you are finished'%(str(totalCoinValue), round((totalCoinValue/satoshi),5)), size=15)
                totalCoinPulses = 0
totalCoinValue = 0.41
text.write("Please put your QR code within sight of the camera.",size=15)
# Scan QR Code
Thread(target=takePictureBursts).start()
time.sleep(0.5)
while continueThread == True:
        time.sleep(0.1)
os.system("sudo rm -r blmfiles/temppics/ && mkdir blmfiles/temppics/")
print("the QR code that was scanned was: %s"%(qrcontent))
# Save transaction data to a txt file and message a message with Telegram bot
satoshi = str(round((totalCoinValue/satoshi),0))[:-2]

timestamp = time.strftime('%Y-%m-%d@%H:%M:%S', time.localtime(time.time()))
teleTimestamp = time.strftime('%Y\\-%m\\-%d@%H:%M:%S', time.localtime(time.time()))
os.system("touch /home/pi/blmfiles/transactiondata/%s.txt"%(timestamp))
os.system("echo 'Timestamp: %s\nAmount (sats): %s\nFiat: $%s\nPrice of BTC: %s' >> /home/pi/blmfiles/transactiondata/%s.txt"%(timestamp,str(satoshi),str(totalCoinValue),btcPrice,timestamp))
bot_token = "" # Replace this with your Telegram Bot API token
chat_id = "" # Replace this with the identifier of the person to who you want to send the message to
response = requests.get("https://api.telegram.org/bot" + bot_token + "/sendMessage?chat_id=" + chat_id + "&parse_mode=MarkdownV2&text=*Timestamp*: %s\n*Amount \\(sats\\)*: %s\n*Fiat*: $%s\n*Price of BTC*: $%s"%(teleTimestamp, satoshi,"\\.".join(str(round(totalCoinValue,2)).split('.')),'\\.'.join(str('{:,}'.format(round(btcPriceFloat,2))).split('.'))))
print("telebot message code: "+str(response.status_code))
text.write("Sending $%s to %s..."%(str(totalCoinValue),qrcontent),size=15)

# Transfer Satoshi(s)
ssh.load_system_host_keys()
node_ip_address = '' # Replace this with the I.P. address of your Bitcoin Node
node_password = '' # Replace this with the password for your Mode
ssh.connect(node_ip_address, 22, 'admin', node_password)
stdin, stdout, stderr = ssh.exec_command("lncli payinvoice --pay_req=%s --amt=%s --fee_limit=1000 --force"%(qrcontent, str(satoshi)))
time.sleep(10.5)
ssh.close()

# Grand Finale
#text.write("Done! Your Satoshi(s) should arrive soon (if they havn't already). Enjoy your day!",size=15)
text.write('Transaction completed. Astra Nova rules!', size=15)

time.sleep(3)

#Debugging data
print('~~~~~DEBUGGING DATA~~~~')
print("command: lncli payinvoice --pay_req=%s --amt=%s --fee_limit=1000 --force"%(qrcontent, satoshi))
print('stdout: ' + str(stdout.readlines()))
print('qrcontent: ' + str(qrcontent))
print('Satoshi(s) sent: ' + satoshi)

GPIO.cleanup()
