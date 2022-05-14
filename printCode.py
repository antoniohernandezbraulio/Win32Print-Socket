import asyncio
import json
from json import dumps
import logging
import websockets
import gc
from subprocess import call
from barcode import Gs1_128
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw,ImageFont
import random
import win32print
import win32ui
from PIL import Image, ImageWin
import sys
import os
from io import BytesIO
from barcode.writer import ImageWriter

logging.basicConfig()
STATE = {"value": 0}
USERS = set()
index = 0

##Impresora
options = {
    'font_size': 12,
    'dpi': 400,
    'module_height': 4,
    'text_distance': 1,
    }

portWs = 8001
ipWs = "127.0.0.1"

with open("config.json","r") as j:
    mydata = json.load(j)
    portWs = mydata["port"]
    ipWs = mydata["ip"]

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def add_margin(pil_img, top, right, bottom, left, color):
    width, height = pil_img.size
    new_width = width + right + left
    new_height = height + top + bottom
    result = Image.new(pil_img.mode, (new_width, new_height), color)
    result.paste(pil_img, (left, top))
    return result

def print_code(file_name):
    HORZRES = 100
    VERTRES = 50
    LOGPIXELSX = 88
    LOGPIXELSY = 90

    PHYSICALWIDTH = 110
    PHYSICALHEIGHT = 100

    PHYSICALOFFSETX = 100
    PHYSICALOFFSETY =100

    printer_name = win32print.GetDefaultPrinter ()

    hDC = win32ui.CreateDC()
    hDC.CreatePrinterDC(printer_name)
    printable_area = hDC.GetDeviceCaps(HORZRES), hDC.GetDeviceCaps (VERTRES)
    printer_size = hDC.GetDeviceCaps (PHYSICALWIDTH), hDC.GetDeviceCaps (PHYSICALHEIGHT)
    printer_margins = hDC.GetDeviceCaps (PHYSICALOFFSETX), hDC.GetDeviceCaps (PHYSICALOFFSETY)

    bmp = Image.open (file_name)
    # if bmp.size[0] > bmp.size[1]:
    #     bmp = bmp.rotate (90)

    ratios = [1.0 * printable_area[0] / bmp.size[0], 1.0 * printable_area[1] / bmp.size[1]]
    scale = min (ratios)

    hDC.StartDoc (file_name)
    hDC.StartPage ()

    dib = ImageWin.Dib (bmp)
    scaled_width, scaled_height = [int (scale * i) for i in bmp.size]
    x1 = int ((printer_size[0] - scaled_width) / 2)
    y1 = int ((printer_size[1] - scaled_height) / 2)
    x2 = x1 + scaled_width
    y2 = y1 + scaled_height

    print(x1, y1, x2, y2)
    dib.draw(hDC.GetHandleOutput(), (1, 10, 700, 300))

    hDC.EndPage()
    hDC.EndDoc()
    hDC.DeleteDC()
    os.remove(file_name)

class create_code_bar:
    def __init__(self,codebar,internalCode,productName):
        nameRandom = str(random.randint(1, 99999999999))
        with open(nameRandom+'.jpg', 'wb') as f:
            Gs1_128(str(codebar), writer=ImageWriter()).write(f,options)

        img = Image.open(nameRandom+'.jpg')
        img = add_margin(img, 24, 5, 5, 5, "#fff")
        I1 = ImageDraw.Draw(img)

        font = ImageFont.truetype("Montserrat.otf", 18)
        I1.text((35,2),productName+'\n', fill="black",font = font)
        I1.text((35,125),internalCode+'\n', fill="black",font= font)
        img.save(nameRandom+".jpg")
        # img.show()
        print_code(nameRandom+".jpg")
###########
def state_event():
    return json.dumps({"type": "state", **STATE})
def users_event():
    return json.dumps({"type": "users", "count": len(USERS)})

async def notify_state():
    if USERS:
        message = state_event()
        await asyncio.wait([user.send(message) for user in USERS])
async def notify_users():
    if USERS:
        message = users_event()
        gc.collect()
        await asyncio.wait([user.send(message) for user in USERS])

async def register(websocket):
    USERS.add(websocket)
    gc.collect()
    await notify_users()
async def unregister(websocket):
    USERS.remove(websocket)
    gc.collect()
    await notify_users()
    

async def accionWebSocket(websocket):
    await register(websocket)
    try:
        await websocket.send(state_event())
        async for message in websocket:
            data = json.loads(message)
            print("-------------------")
            print(data)
            print("-------------------")
            for dataInfo in data:
                create_code_bar(str(dataInfo['barCode']),str(dataInfo['internalCode']),str(dataInfo['name']))

            await notify_state()
            gc.collect()
    finally:
        await unregister(websocket)

try:
    start_server = websockets.serve(accionWebSocket, ipWs, portWs)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
except IOError as e:
    print("Error => ",e)
