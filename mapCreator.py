# -*- coding: utf-8 -*-
"""
Map creation script

"""
import subprocess
import sys
import os
from configparser import ConfigParser
import math
from PIL import Image
# import urllib.request, urllib.parse, urllib.error
from subprocess import STDOUT, check_output
from time import sleep

from multiprocessing.pool import ThreadPool as Pool
# from multiprocessing import Pool

pool_size = 16  # your "parallelness"

MAX_DOWNLOAD_TIME = 120 # seconds
DOWNLOAD_MAX_RETRY_COUNT = 5
DOWNLOAD_SLEEP_TIME = 0.0

# {0} - zoom, {1} - x, {2} - y
server_url = "http://localhost:8080/tile/{0}/{1}/{2}.png"

# tile positions, see https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon..2Flat._to_tile_numbers_2
def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def get_tile(fName, url, idx, tiles_len):
    print('[%i/%i] %s' % (idx + 1, tiles_len, fName), end=' ')
    if not os.path.exists(fName):
        print(f'Requesting {url}...')
        cmd = ['curl', '-o', fName, url]
        for _ in range(DOWNLOAD_MAX_RETRY_COUNT):
            try:
                ret = check_output(cmd, stderr=STDOUT, timeout=MAX_DOWNLOAD_TIME)
                if not ret:
                    print('Error downloading tile:', ret)
                    sys.exit(1)
                
                break
            except subprocess.TimeoutExpired:
                print('Timeout downloading tile:', url)
                print("Retrying...")

        print('OK!')

        sleep(DOWNLOAD_SLEEP_TIME) # be nice to the server
    else:
        print('Cached!')

def get_file_name(tilestore_path, tile):
    fname = '_'.join([str(f) for f in tile]) + '.png'
    return os.path.join(tilestore_path, fname)

def print_usage():
    print('Usage: mapCreator.py <name> <n> <e> <s> <w> <zoom>')

def main():
    if len(sys.argv) < 7:
        print_usage()
        sys.exit(2)

    print(sys.argv)
    name = sys.argv[1]
    bounds_n = float(sys.argv[2])
    bounds_e = float(sys.argv[3])
    bounds_s = float(sys.argv[4])
    bounds_w = float(sys.argv[5])
    zoom = int(sys.argv[6])

    source =  server_url
    dest_path = os.getcwd() + '/maps'
    tilestore_path = os.getcwd() + '/tiles'

    if not os.path.exists(dest_path):
        os.mkdir(dest_path)

    dest_path = os.path.join(dest_path, "%s_zoom%i.jpeg" % (name, zoom))
    tilestore_path = tilestore_path

    # parse bounding box
    bbox_str = '<bbox n="%f" e="%f" s="%f" w="%f"/>' % (bounds_n, bounds_e, bounds_s, bounds_w)
    txt = bbox_str
    c = [float(v) for v in txt.split('"')[1::2]]
    bbox = dict(list(zip(['n', 'e', 's', 'w'], c)))

    if not os.path.exists(tilestore_path):
        os.makedirs(tilestore_path)

    top_left = deg2num(bbox['n'], bbox['w'], zoom)
    bottom_right = deg2num(bbox['s'], bbox['e'], zoom)


    # create tile list 
    tiles = []

    for x in range(top_left[0], bottom_right[0]):
        for y in range(top_left[1], bottom_right[1]):
            tiles.append((zoom,x,y))
            
    print('Nr tiles: ', len(tiles))


    # download tiles and make map


    height = (bottom_right[1] - top_left[1]) * 256
    width = (bottom_right[0] - top_left[0]) * 256

    print('Map size: %i x %i' % (width, height))

    pool = Pool(pool_size)
    for idx, tile in enumerate(tiles):     
        zoom,x,y = tile
        fName = get_file_name(tilestore_path, tile)

        pool.apply_async(get_tile, (fName, source.format(*tile), idx, len(tiles)))    
        

    pool.close()
    pool.join()

    img = Image.new("RGB", (width, height))
    for tile in tiles:
        zoom,x,y = tile
        fName = get_file_name(tilestore_path, tile)

        # paste
        tmp = Image.open(fName)
        img.paste(tmp, (256 * (x - top_left[0]), 256 * (y - top_left[1])))

        
    print('Saving to ', dest_path)
    img.save(dest_path, "JPEG")

if __name__ == '__main__':
    main()