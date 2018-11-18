from PIL import Image
from io import BytesIO
import base64
from threading import Thread
import multiprocessing
from colorama import init, Fore, Style

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,
                                                **self._kwargs)
    def join(self, *args):
        Thread.join(self, *args)
        return self._return

def usage():
	print('Usage: main.py <command> [<options>...] [<inputs>]')
	print('')
	print('<commands>')
	print('-l : download LINE stickers and generate JSON')
	print('-d : generate JSON from a directory')
	print('')
	print('<options>')
	print('-t | --threads <number of threads>')
	print('-o | --output  <output JSON filename> (will be ignored if more than one inputs)')
	print('-f | --detination_folder  <output directory>')
	print('-p | --preview (a preview will be automatically generated.)')
	print('')
	print('<inputs>')
	print('LINE Stickers ID / directory depending on your command')

def resize(img,boxSize,img_format):
	if not (boxSize in img.size):
		#only when both dimensions of image are below the boxSize, resize is required.
		if img.size[0] < img.size[1]:
			newSize = (int(img.size[0]/img.size[1]*boxSize), boxSize)
		else:
			newSize = (boxSize, int(img.size[1]/img.size[0]*boxSize))
		img = img.resize(newSize, Image.ANTIALIAS)

	buffer = BytesIO()
	#create an empty image with a size of boxSize * boxSize
	new_im = Image.new('RGBA', (boxSize, boxSize), (255, 0, 0, 0))
	new_im.paste(img, ((boxSize-img.size[0])//2,(boxSize-img.size[1])//2))

	#encode and store the image in buffer
	if img_format=="webp":
		new_im.save(buffer,format="webp",lossless=True,quality=100)
	elif img_format=="png":
		new_im.save(buffer,format="png",optimize=True)
	else:
		new_im.save(buffer,format=img_format)
	return str(base64.b64encode(buffer.getvalue()), "utf-8")

def prev(filename_metadata):
	from PIL import Image, ImageDraw, ImageFont
	import sys, os

	fonts = [os.path.dirname(sys.argv[0])+"/fonts/NotoSansCJKtc-Light.otf",os.path.dirname(sys.argv[0])+"/fonts/NotoSansCJKtc-Black.otf"]

	imgs = []
	metadata=filename_metadata[1]
	for sticker in metadata["stickers"]:
		img = Image.open(BytesIO(base64.b64decode(sticker["image_data"])),mode="r")
		imgs.append(img)
	
	new_im = Image.new('RGBA', (720, 1280), (255, 255, 255, 255))
	x=0
	for img in imgs:
		img = img.resize((133,133), Image.ANTIALIAS).convert("RGBA")
		new_im.paste(img, (10+140*(x%5),300+(x//5)*140), img)
		x+=1

	img = Image.open(BytesIO(base64.b64decode(metadata["tray_image"])),mode="r").convert("RGBA")
	new_im.paste(img, (15,180),img)
	
	d = ImageDraw.Draw(new_im)
	fnt = ImageFont.truetype(fonts[0], 24)
	d.text((15,140), os.path.basename(filename_metadata[0]), font=fnt, fill=(0,0,0,255))
	fnt = ImageFont.truetype(fonts[1], 40)
	d.text((120,180), metadata["name"], font=fnt, fill=(0,0,0,255))
	fnt = ImageFont.truetype(fonts[0], 28)
	d.text((120,225), "created by " + metadata["publisher"], font=fnt, fill=(48,48,48,255))
	
	#fnt = ImageFont.truetype('NotoSans-Regular.ttf', 36)
	#d.text((20,360), "identifier: " + metadata["identifier"], font=fnt, fill=(0,0,0,255))
	
	new_im.save(filename_metadata[0]+".png",format="png",optimize=True)
	from colorama import init, Fore, Style
	init()
	print("Preview file {}{}.png{} generated".format(Fore.GREEN,filename_metadata[0],Style.RESET_ALL))

def conv(path):
	img = Image.open(path)
	tempstick = {
		"image_data": resize(img,512,"WEBP")
	}
	return tempstick

def download(id):
	import urllib.request
	import zipfile
	import json
	import os
	import re
	print('Downloading:',Fore.CYAN+id+Fore.RESET )
	urllib.request.urlretrieve("http://dl.stickershop.line.naver.jp/products/0/0/1/" + id + "/iphone/stickers@2x.zip", './'+id+'.zip')  
	print('Downloaded: ',Fore.CYAN+id+Fore.RESET )
	with zipfile.ZipFile(id+".zip","r") as zip_ref:
		zip_ref.extractall(id)
	os.remove(id+".zip")

	with open(id+'/productInfo.meta', encoding='utf-8') as data_file:
		data = json.loads(data_file.read())
	metadata = {
		"identifier": id+'_'+re.sub(r"[^A-Za-z]+", '', data["title"]["en"]),
		"name": data["title"]["zh-Hant"] if "zh-Hant" in data["title"] else data["title"]["en"],
		"publisher": data["author"]["zh-Hant"] if "zh-Hant" in data["author"] else data["author"]["en"]
	}
	stickers_list = ["{}/{}@2x.png".format(id,sticker['id']) for sticker in data["stickers"]]
	tray_path = "{}/tab_on@2x.png".format(id)
	print(Style.BRIGHT+id+Style.RESET_ALL +'-'+ Style.BRIGHT+metadata["name"]+Style.RESET_ALL,'by', Style.BRIGHT+metadata["publisher"]+Fore.RESET+Style.RESET_ALL)
	dest_name = "{}-{}".format(id, metadata['name'])
	obj={
		"metadata": metadata,
		"stickers_list": stickers_list,
		"tray_path": tray_path,
		"filename": dest_name
	}
	import shutil
	shutil.rmtree(id)
	return obj

def folder(directory):
	if not directory.exists():
		print("directory {} not found".format(directory))
		sys.exit()
	config= directory / 'config.txt'
	if config.exists():
		with io.open(directory / 'config.txt', 'r', encoding="utf-8") as file:
			config=file.readline().split('\t')
		metadata = {
			"identifier": config[2],
			"name": config[0],
			"publisher": config[1]
		}
	else:
		metadata = {
			"identifier": re.sub(r"[^A-Za-z]+", '', directory.name),
			"name": directory.name,
			"publisher": directory.name
		}
	print(directory)
	stickers_list=[]
	for ext in ("webp","png","jpeg"):
		stickers_list.extend(directory.glob("[!tray]*.{}".format(ext)))
	tray=list(directory.glob("tray*"))
	if len(tray) < 1:
		tray_path = stickers_list[0]
	else:
		tray_path = tray[0]
	
	print(Style.BRIGHT+metadata["name"]+Style.RESET_ALL,'by', Style.BRIGHT+metadata["publisher"]+Fore.RESET+Style.RESET_ALL)
	obj={
		"metadata": metadata,
		"stickers_list": stickers_list,
		"tray_path": tray_path,
		"filename": directory.name
	}
	return obj

def generateJSON(obj):
	import time
	import json
	import os
	from multiprocessing import Pool

	metadata=obj["metadata"]
	stickers_list=obj["stickers_list"]
	tray_path=obj["tray_path"]
	dest_name=obj["filename"]
	thread_num=4
	start = time.time()
	print("{} stickers have been found".format(len(stickers_list)))
	if len(stickers_list)<3:
		print("Warning: at least 3 stickers are required to work properly with WhatsApp")
	conv_start = time.time()

	stickers=[]
	with Pool(thread_num) as pconv:
		stickers=pconv.map(conv,stickers_list)
	metadata["tray_image"] = resize(Image.open(tray_path),96,"PNG")
	conv_time = time.time() - conv_start
	text="{} stickers and tray image have been converted in {:.3f} s".format(len(stickers_list),conv_time)
	print (text)
	s = len(stickers)<=30
	i = 1
	original_iden = metadata["identifier"]
	jsons=[]
	while len(stickers) > 0:
		destination = "{}.json".format(dest_name) if s else "{} Part{}.json".format(dest_name,i)
		metadata["identifier"] = original_iden if s else original_iden +'_part'+str(i)
		metadata["stickers"] = stickers[:30]
		with open(destination, 'w', encoding='utf-8') as outfile:
			json.dump(metadata, outfile, ensure_ascii=False)
		print(Fore.GREEN+destination+Style.RESET_ALL,"( {:7.2f} KiB) has been generated".format(os.stat(destination).st_size/1024))
		del stickers[:30]
		jsons.append((destination, metadata.copy()))
		i+=1
	
	total_time = time.time() - start
	print(i-1,'json(s) have been generated in',"{:.3f}".format(total_time),"s")
	return jsons

def main(argv):
	thread_num = multiprocessing.cpu_count()//2
	mode = out = dest_folder = ""
	preview = False
	try:
		opts, args = getopt.getopt(argv,"hldpo:t:f:",["help","preview","output=","threads=","destination_folder="])
	except getopt.GetoptError:
		usage()
		sys.exit()
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			usage()
			sys.exit()
		elif opt in ("-l"):
			mode="l"
		elif opt in ("-d"):
			mode="d"
		elif opt in ("-p", "--p"):
			preview=True
		elif opt in ("-o", "--output"):
			out = arg
		elif opt in ("-f", "--destination_folder"):
			dest_folder = arg
		elif opt in ("-t", "--threads"):
			thread_num = int(arg)
	if mode=="":
		if preview:
			mode="p"
			preview=False
		else:
			usage()
			exit(0)
	print("WhatsApp Stickers JSON Generator by Chester")
	print("verions 1.2.0")
	import glob
	matches=[]

	if mode=="p":
		for arg in args:
			matches.extend(glob.glob(arg))
		datas=[]
		for arg in matches:
			with open(arg, encoding='utf-8') as data_file:
				datas.append([arg,json.loads(data_file.read())])
		with Pool(thread_num) as p2:
			p2.map(prev,datas)

	if mode in ["l","d"]:
		objs = []
		if mode=="l":
			with Pool(thread_num) as p2:
				objs=p2.map(download,args)
		if mode=="d":
			for arg in args:
				matches.extend(glob.glob(arg))
			for arg in matches:
				objs.append(folder(Path(arg)))
		if len(objs)==1 and out!="":
			objs[0]["filename"]=out
		jsons=[]
		#with Pool(thread_num) as p:
			#jsonss=p.map(generateJSON, objs)
		for obj in objs:
			if dest_folder != "":
				obj["filename"]=dest_folder +os.path.basename(obj["filename"])
			jsons.extend(generateJSON(obj))
		if preview:
			with Pool(thread_num) as pprev:
				pprev.map(prev,jsons)
			#for jso in jsons:
				#prev(jso)

if __name__ == '__main__':
	import time
	import io
	import json
	import os
	from pathlib import Path
	import PIL
	import re
	import sys
	import multiprocessing
	from multiprocessing import Pool
	import getopt
	import sys
	import multiprocessing
	multiprocessing.freeze_support()

	from colorama import init, Fore, Style
	init()
	main(sys.argv[1:])