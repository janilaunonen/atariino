#
# pytholiino - a program to serve sectors from .ATR files to Atariino.
#   usage: pytholiino <serial port> <.ATR file for D1> [<.ATR file for D2> ... <.ATR file for D15>]
# no support for formatting a new disk from Atari yet
# 0. read command line arguments, check that the listed files exists
# 0.1. check that serial port is a special file (in unix)
# 0.2. check that .ATR files .ATR extension and seem valid .ATR images.
# 0.3. enumerate .ATR files - this is how many disk drives we support.
# 1. open serial port, read line and assert it reads "Atariino".
# 2. read line, which is the Atariino's versin number (for curiosity)
# -- not necessary if we support 15 disks. There are associated .ATR images or they are considered to have empty disks in.( 2.1. write to Atariino, how many drives we support 1-15 (none, if printer?))
# -- not necessary (above) (2.2. read line and assert it reads "OK")
# 2.3 we might need to tell Atariino, if we have write protected .ATRs.
# 3. enter event loop:
# 3.1. read command frame (4 bytes, DEVID, CMDID, AUX1, AUX2) (Atarino has validated checksum)
# 3.2. check whether DEVID is a drive we support (should be!)
# 3.3. check CMDID is STATUS, GET_SECTOR or PUT_SECTOR
# 3.4. check in case of G_S and P_S the sector number is < 720
# 3.5. read and write...
# 3.6 goto 3.

import os
import sys
import serial

USAGE = 'pytholiino <serial port> <.ATR for D1> [<.ATR for D2> [... <.ATR for D15>>]]'
SERIALDEV = '/dev/ttyACM0'
SERIALSPEED = 115200
SERIALBITS = 8
#ATRIMAGE = 'Koronis Rift.ATR'
#ATRIMAGE = 'Mercenary - Escape from Targ _ Novagen Software.atr'
#ATRIMAGE = 'Theatre Europe _ PSS.atr'
#ATRIMAGE = 'xlpmax.atr'
ATRIMAGE = '../images/A-Rogue.atr'
COMMAND_FRAME_LEN = 4	# device id, command id, aux1, aux2
ATR_HEADER_LEN = 16
SECTOR_LEN = 128
PRINTER_LINE_LEN = 40

HEX = 16

DEVID_D1		= int('0x31', HEX)
DEVID_P1		= int('0x40', HEX)

DISK_GET_STATUS 	= int('0x53', HEX)
DISK_GET_SECTOR 	= int('0x52', HEX)
DISK_PUT_SECTOR		= int('0x50', HEX)

PRINTER_PRINT_LINE 	= int('0x57', HEX)
PRINTER_GET_STATUS 	= int('0x53', HEX)

# Atariino - Pytholiino custom debug command ids not part of SIO specification
# The command frame will contain DEVID_P1 and one of following CMDIDs and
# AUX1 will contain the length of debug text or binary blob in bytes.
# Data frame will contain the debug text or binary blob without chksum.
# Text length will include terminating 0. To reduce memory consumption in
# ATMega, one cmd frame can be followd by several data frames as long as
# the total amount of data equals the AUX1 field.
PRINTER_DEBUG_TXT	= int('0xEE', HEX) # data frame will contain ASCII
PRINTER_DEBUG_BIN       = int('0xFF', HEX) # data frame will contain binary

ACK			= int('0x41', HEX)
NAK			= int('0x4E', HEX)
COMPLETE		= int('0x43', HEX)
ERR			= int('0x45', HEX)

config = dict(serialdev=SERIALDEV)	# default
#disk_drives = ['d1', '

#def is_atr_file(arg):
	# check extension
	# check it exists
	# check it can be opened

def is_serialdev_file(arg):
	return os.file.isatty(arg)

def create_config():
	i = 0
	for arg in sys.args:
		if is_atr_file(arg):
			config[i]=arg
		elif is_serialdev_file(arg):
			config['serialdev']=arg
		elif not i == 0:
			print 'Not .atr or serial device file:' + arg

def read_commandline_args():
	if len(sys.argv) > 2:
		return create_config()
		# should check for /dev/ttyACM0... bugger it for now!
		# return number_of_diskdrives(sys.argv)
	else:
		print USAGE
		return False

def init_connection():
	return serial.Serial(SERIALDEV, SERIALSPEED, SERIALBITS)

#
# Disk operations
#
def get_sector_offset_from_aux(command_frame):
	aux1 = ord(command_frame[2])
        aux2 = ord(command_frame[3])
        sector_number = (256 * aux2) + aux1 - 1 # make sector start from 0
	print 'aux1 = ' + str(aux1) + ' aux2 = ' + str(aux2) + ' sector = ' + str(sector_number)
        sector_offset = ATR_HEADER_LEN + (128 * sector_number)
	return sector_offset

def disk_get_status(command_frame):
	print 'disk_get_status()'

def get_sector(port, imagefile, command_frame):
	print 'get_sector'
	sector_offset = get_sector_offset_from_aux(command_frame)
	imagefile.seek(sector_offset)
	sector_data = imagefile.read(SECTOR_LEN)
	port.write(sector_data)

def put_sector(port, imagefile, command_frame):
	print 'put_sector'
	sector_offset = get_sector_offset_from_aux(command_frame)
	imagefile.seek(sector_offset)
	sector_data = port.read(SECTOR_LEN)
	imagefile.write(sector_data)
	imagefile.flush() # probably overkill

# print command dispatcher
def handle_disk(port, imagefile, command_frame):
	cmdid = ord(command_frame[1])
	if cmdid == DISK_GET_STATUS:
		disk_get_status(command_frame)
	elif cmdid == DISK_GET_SECTOR:
		get_sector(port, imagefile, command_frame)
	elif cmdid == DISK_PUT_SECTOR:
		put_sector(port, imagefile, command_frame)

#
# Print operations (both Atari printer P: and Atariino debug)
#
def printer_get_status(command_frame):
	print '>>printer_get_status'

def print_line(port, command_frame):
	aux2 = ord(command_frame[3])	# print mode, expect 0x4E -> 40 bytes frame (+ chksum)
	line_data = port.read(PRINTER_LINE_LEN)
	print '*print_line>>' + line_data + '<<'

def print_debug_txt(port, command_frame):
	aux1 = ord(command_frame[2])	# lenght of txt in bytes including terminating 0
	debug_txt = port.read(aux1)
	print '*print_debug_txt>>' + debug_txt + '<<'

def print_debug_bin(port, command_frame):
	aux1 = ord(command_frame[2])
	debug_bin = port.read(aux1)
	print '*print_debug_bin>>' + ":".join("{:02x}".format(ord(c)) for c in debug_bin) + '<<'

# print command dispatcher
def handle_printer(port, command_frame):
	cmdid = ord(command_frame[1])
	if cmdid == PRINTER_PRINT_LINE:
		print_line(port, command_frame)
	elif cmdid == PRINTER_GET_STATUS:
		printer_get_status(command_frame)
	elif cmdid == PRINTER_DEBUG_TXT:
		print_debug_txt(port, command_frame)
	elif cmdid == PRINTER_DEBUG_BIN:
		print_debug_bin(port, command_frame)
	# handle status, write and write with verify

# TODO: need to have connection reinitialization - close, reopen?
# at least error detection, when connection is lost
def eventloop(port, imagefile):
	try:
		while True:
			command_frame = port.read(COMMAND_FRAME_LEN)
			devid = ord(command_frame[0])
			if devid == DEVID_D1:
				handle_disk(port, imagefile, command_frame)
			elif devid == DEVID_P1:
				handle_printer(port, command_frame)
			else:
				print '>>Unknown device (devid)' + hex(devid)
				print '>>Whole command frame: ' + command_frame
	except serial.SerialException:
		print 'Lost connection to Atariino'

def make_connection():

	#TODO: reiterate init_connection() and enter eventloop()
	port = init_connection()
	d1_file = open(ATRIMAGE, 'rb+')
	#file(sys.argv[1])

	print port.readline()
	print port.readline()
	# port.readline() == 'Atariino'
	# port.readline() == 'OK'

	print 'Connected to Atariino, waiting in eventloop'

	eventloop(port, d1_file)

def main():
	#if read_commandline_args():
	make_connection()

if __name__ == '__main__':
	main()

