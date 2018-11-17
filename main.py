from PIL import Image
from io import BytesIO
import base64
	
def resize(img,boxSize,img_format):
	if not (512 in img.size):
		#only when both dimensions of image are below the boxSize, resize is required.
		if img.size[0] < img.size[1]:
			newSize = (int(img.size[0]/img.size[1]*boxSize), boxSize)
		else:
			newSize = (boxSize, int(img.size[0]/img.size[1]*boxSize))
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

def conv(path):
	img = Image.open(path)
	tempstick = {
		"image_data": resize(img,512,"WEBP")
	}
	return tempstick

def download(id):
	import urllib.request
	import zipfile
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
	return [metadata,stickers_list,tray_path,dest_name]

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
	return [metadata,stickers_list,tray_path,directory.name]
	
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
	print('')
	print('<inputs>')
	print('LINE Stickers ID / directory depending on your command')

def generateJSON(metadata,stickers_list,tray_path,dest_name,thread_num):
	start = time.time()
	print("{} stickers have been found".format(len(stickers_list)))
	if len(stickers_list)<3:
		print("Warning: at least 3 stickers are required to work properly with WhatsApp")
	conv_start = time.time()

	stickers=[]
	with Pool(thread_num) as p:
		stickers=p.map(conv, stickers_list)
	metadata["tray_image"] = resize(Image.open(tray_path),96,"PNG")
	conv_time = time.time() - conv_start
	print("{} stickers and tray image have been converted in {:.3f} s".format(len(stickers_list),conv_time))
	
	s = len(stickers)<=30
	i = 1
	original_iden = metadata["identifier"]
	
	while len(stickers) > 0:
		destination = "{}.json".format(dest_name) if s else "{} Part{}.json".format(dest_name,i)
		metadata["identifier"] = original_iden if s else original_iden +'_part'+str(i)
		metadata["stickers"] = stickers[:30]
		
		with open(destination, 'w', encoding='utf-8') as outfile:
			json.dump(metadata, outfile, ensure_ascii=False)
		print(Fore.GREEN+destination+Style.RESET_ALL,"( {:7.2f} KiB) has been generated".format(os.stat(destination).st_size/1024))
		del stickers[:30]
		i+=1
	
	total_time = time.time() - start
	print(i-1,'json(s) have been generated in',"{:.3f}".format(total_time),"s")
	
def main(argv):
	thread_num = multiprocessing.cpu_count()//2
	mode = out = dest_folder = ""
	try:
		opts, args = getopt.getopt(argv,"hldo:t:f:",["help","output=","threads=","destination_folder="])
	except getopt.GetoptError:
		usage()
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-h", "--help"):
			usage()
			sys.exit()
		elif opt in ("-l"):
			mode="l"
		elif opt in ("-d"):
			mode="d"
		elif opt in ("-o", "--output"):
			out = arg
		elif opt in ("-f", "--destination_folder"):
			dest_folder = arg
		elif opt in ("-t", "--threads"):
			thread_num = int(arg)
	if mode=="":
		usage()
		sys.exit(2)
	print("WhatsApp Stickers JSON Generator by Chester")
	print("verions 1.1.0")
	for arg in args:
		if mode=="l":
			metadata,stickers_list,tray_path,dest_name = download(arg)
		if mode=="d":
			metadata,stickers_list,tray_path,dest_name = folder(Path(arg))
		if len(args)==1 and out!="":
			dest_name=out
		generateJSON(metadata,stickers_list,tray_path,dest_folder+dest_name,thread_num)
		if mode=="l":
			import shutil
			shutil.rmtree(arg)

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