#!/usr/bin/env python3
import asyncio
import argparse
import time
import yaml

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

import PIL.Image


with open("config.yaml", "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)


bluetooth_name = config["bluetooth_name"]
print_contrast = config["contrast"]
printer_width = config["printer_width"]
img_print_speed = [0x23]
blank_speed = [0x19]
feed_lines = config["feed_lines"]
header_lines = 0
scale_feed = False
packet_length = 60
throttle = 0.01
address = None
device = None
debug = config["debug"]

PrinterCharacteristic = "0000AE01-0000-1000-8000-00805F9B34FB"
NotifyCharacteristic = "0000AE02-0000-1000-8000-00805F9B34FB"

# CRC8 table extracted from APK, pretty standard though
crc8_table = (
    0x00, 0x07, 0x0e, 0x09, 0x1c, 0x1b, 0x12, 0x15, 0x38, 0x3f, 0x36, 0x31,
    0x24, 0x23, 0x2a, 0x2d, 0x70, 0x77, 0x7e, 0x79, 0x6c, 0x6b, 0x62, 0x65,
    0x48, 0x4f, 0x46, 0x41, 0x54, 0x53, 0x5a, 0x5d, 0xe0, 0xe7, 0xee, 0xe9,
    0xfc, 0xfb, 0xf2, 0xf5, 0xd8, 0xdf, 0xd6, 0xd1, 0xc4, 0xc3, 0xca, 0xcd,
    0x90, 0x97, 0x9e, 0x99, 0x8c, 0x8b, 0x82, 0x85, 0xa8, 0xaf, 0xa6, 0xa1,
    0xb4, 0xb3, 0xba, 0xbd, 0xc7, 0xc0, 0xc9, 0xce, 0xdb, 0xdc, 0xd5, 0xd2,
    0xff, 0xf8, 0xf1, 0xf6, 0xe3, 0xe4, 0xed, 0xea, 0xb7, 0xb0, 0xb9, 0xbe,
    0xab, 0xac, 0xa5, 0xa2, 0x8f, 0x88, 0x81, 0x86, 0x93, 0x94, 0x9d, 0x9a,
    0x27, 0x20, 0x29, 0x2e, 0x3b, 0x3c, 0x35, 0x32, 0x1f, 0x18, 0x11, 0x16,
    0x03, 0x04, 0x0d, 0x0a, 0x57, 0x50, 0x59, 0x5e, 0x4b, 0x4c, 0x45, 0x42,
    0x6f, 0x68, 0x61, 0x66, 0x73, 0x74, 0x7d, 0x7a, 0x89, 0x8e, 0x87, 0x80,
    0x95, 0x92, 0x9b, 0x9c, 0xb1, 0xb6, 0xbf, 0xb8, 0xad, 0xaa, 0xa3, 0xa4,
    0xf9, 0xfe, 0xf7, 0xf0, 0xe5, 0xe2, 0xeb, 0xec, 0xc1, 0xc6, 0xcf, 0xc8,
    0xdd, 0xda, 0xd3, 0xd4, 0x69, 0x6e, 0x67, 0x60, 0x75, 0x72, 0x7b, 0x7c,
    0x51, 0x56, 0x5f, 0x58, 0x4d, 0x4a, 0x43, 0x44, 0x19, 0x1e, 0x17, 0x10,
    0x05, 0x02, 0x0b, 0x0c, 0x21, 0x26, 0x2f, 0x28, 0x3d, 0x3a, 0x33, 0x34,
    0x4e, 0x49, 0x40, 0x47, 0x52, 0x55, 0x5c, 0x5b, 0x76, 0x71, 0x78, 0x7f,
    0x6a, 0x6d, 0x64, 0x63, 0x3e, 0x39, 0x30, 0x37, 0x22, 0x25, 0x2c, 0x2b,
    0x06, 0x01, 0x08, 0x0f, 0x1a, 0x1d, 0x14, 0x13, 0xae, 0xa9, 0xa0, 0xa7,
    0xb2, 0xb5, 0xbc, 0xbb, 0x96, 0x91, 0x98, 0x9f, 0x8a, 0x8d, 0x84, 0x83,
    0xde, 0xd9, 0xd0, 0xd7, 0xc2, 0xc5, 0xcc, 0xcb, 0xe6, 0xe1, 0xe8, 0xef,
    0xfa, 0xfd, 0xf4, 0xf3
)


def crc8(data):
    crc = 0
    for byte in data:
        crc = crc8_table[(crc ^ byte) & 0xFF]
    return crc & 0xFF


# General message format:
# Magic number: 2 bytes 0x51, 0x78
# Command: 1 byte
# 0x00
# Data length: 1 byte
# 0x00
# Data: Data Length bytes
# CRC8 of Data: 1 byte
# 0xFF
def format_message(command, data):
    data = [0x51, 0x78] + [command] + [0x00] + \
        [len(data)] + [0x00] + data + [crc8(data)] + [0xFF]
    return data


def printer_short(i):
    return [i & 0xFF, (i >> 8) & 0xFF]


# Commands
RetractPaper = 0xA0  # Data: Number of steps to go back
FeedPaper = 0xA1  # Data: Number of steps to go forward
DrawBitmap = 0xA2  # Data: Line to draw. 0 bit -> don't draw pixel, 1 bit -> draw pixel
GetDevState = 0xA3  # Data: 0
# Data: Eleven bytes, all constants. One set used before printing, one after.
ControlLattice = 0xA6
GetDevInfo = 0xA8  # Data: 0
# Data: one byte, set to a device-specific "Speed" value before printing
OtherFeedPaper = 0xBD
#                              and to 0x19 before feeding blank paper
DrawingMode = 0xBE  # Data: 1 for Text, 0 for Images
SetEnergy = 0xAF  # Data: 1 - 0xFFFF
SetQuality = 0xA4  # Data: 0x31 - 0x35. APK always sets 0x33 for GB01

PrintLattice = [0xAA, 0x55, 0x17, 0x38,
                0x44, 0x5F, 0x5F, 0x5F, 0x44, 0x38, 0x2C]
FinishLattice = [0xAA, 0x55, 0x17, 0x00,
                 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x17]
XOff = (0x51, 0x78, 0xAE, 0x01, 0x01, 0x00, 0x10, 0x70, 0xFF)
XOn = (0x51, 0x78, 0xAE, 0x01, 0x01, 0x00, 0x00, 0x00, 0xFF)

energy = {
    0: printer_short(8000),
    1: printer_short(12000),
    2: printer_short(17500)
}


def detect_printer(detected, advertisement_data):
    global device
    if address:
        cut_addr = detected.address.replace(":", "")[-(len(address)):].upper()
        if cut_addr != address:
            return
    if detected.name == bluetooth_name:
        device = detected


def notification_handler(sender, data):
    global debug
    if debug:
        print("{0}: [ {1} ]".format(sender, " ".join(
            "{:02X}".format(x) for x in data)))
    if tuple(data) == XOff:
        print("Error: Printer data overrun!")
        return
    if data[2] == GetDevState:
        if data[6] & 0b1000:
            print("Warning: Low battery! Print quality might be affected…")
        # print("printer status byte: {:08b}".format(data[6]))
        # xxxxxxx1 no_paper ("No paper.")
        # xxxxxx10 paper_positions_open ("Warehouse.")
        # xxxxx100 too_hot ("Too hot, please let me take a break.")
        # xxxx1000 no_power_please_charge ("I have no electricity, please charge")
        # I don't know if multiple status bits can be on at once, but if they are, then iPrint won't detect them.
        # In any case, I think the low battery flag is the only one the GB01 uses.
        # It also turns out this flag might not turn on, even when the battery's so low the printer shuts itself off…
        return


async def connect_and_send(data):
    scanner = BleakScanner()
    scanner.register_detection_callback(detect_printer)
    await scanner.start()
    for x in range(50):
        await asyncio.sleep(0.1)
        if device:
            break
    await scanner.stop()

    if not device:
        raise BleakError(f"The printer was not found.")
    async with BleakClient(device) as client:
        # Set up callback to handle messages from the printer
        await client.start_notify(NotifyCharacteristic, notification_handler)

        while data:
            # Cut the command stream up into pieces small enough for the printer to handle
            await client.write_gatt_char(PrinterCharacteristic, bytearray(data[:packet_length]))
            data = data[packet_length:]
            if throttle is not None:
                await asyncio.sleep(throttle)


def request_status():
    return format_message(GetDevState, [0x00])


def blank_paper(lines):
    # Feed extra paper for image to be visible
    blank_commands = format_message(OtherFeedPaper, blank_speed)
    count = lines
    while count:
        feed = min(count, 0xFF)
        blank_commands = blank_commands + \
            format_message(FeedPaper, printer_short(feed))
        count = count - feed
    return blank_commands


def render_image(img, printing):
    global header_lines
    global feed_lines
    global print_contrast

    cmdqueue = []
    # Set quality to standard
    cmdqueue += format_message(SetQuality, [0x33])
    # start and/or set up the lattice, whatever that is
    cmdqueue += format_message(ControlLattice, PrintLattice)
    # Set energy used
    cmdqueue += format_message(SetEnergy, energy[print_contrast])
    # Set mode to image mode
    cmdqueue += format_message(DrawingMode, [0])
    # not entirely sure what this does
    cmdqueue += format_message(OtherFeedPaper, img_print_speed)

    if img.width > printer_width:
        # image is wider than printer resolution; scale it down proportionately
        scale = printer_width / img.width
        if scale_feed:
            header_lines = int(header_lines * scale)
            feed_lines = int(feed_lines * scale)
        img = img.resize((printer_width, int(img.height * scale)))
    if img.width < (printer_width // 2):
        # scale up to largest whole multiple
        scale = printer_width // img.width
        if scale_feed:
            header_lines = int(header_lines * scale)
            feed_lines = int(feed_lines * scale)
        img = img.resize((img.width * scale, img.height *
                         scale), resample=PIL.Image.NEAREST)
    # convert image to black-and-white 1bpp color format
    img = img.convert("RGB")
    img = img.convert("1")
    if img.width < printer_width:
        # image is narrower than printer resolution
        # pad it out with white pixels
        pad_amount = (printer_width - img.width) // 2
        padded_image = PIL.Image.new("1", (printer_width, img.height), 1)
        padded_image.paste(img, box=(pad_amount, 0))
        img = padded_image

    if header_lines:
        cmdqueue += blank_paper(header_lines)

    for y in range(0, img.height):
        bmp = []
        bit = 0
        # pack image data into 8 pixels per byte
        for x in range(0, img.width):
            if bit % 8 == 0:
                bmp += [0x00]
            bmp[int(bit / 8)] >>= 1
            if not img.getpixel((x, y)):
                bmp[int(bit / 8)] |= 0x80
            else:
                bmp[int(bit / 8)] |= 0

            bit += 1

        cmdqueue += format_message(DrawBitmap, bmp)

    # finish the lattice, whatever that means
    cmdqueue += format_message(ControlLattice, FinishLattice)

    if printing:
        return cmdqueue
    else:
        return img


def tulostus(filename):

    print_data = request_status()
    image = PIL.Image.open(filename)

    try:
        # Removes alpha-channel and replaces it with white
        canvas = PIL.Image.new('RGBA', image.size, (255, 255, 255, 255))
        canvas.paste(image, mask=image)
        print_data = print_data + render_image(canvas, True)
    except:  # If image does not have alpha channel, PIL throws an error
        print_data = print_data + render_image(image, True)
    print_data = print_data + blank_paper(feed_lines)

    return print_data

    # loop = asyncio.get_event_loop()

    # i = 1
    # print_failed = False

    # while i < 4:
    #     try:
    #         loop.run_until_complete(connect_and_send(print_data))
    #         i = 4
    #         print_failed = False
    #         return "printti done :)"
    #     except:
    #         time.sleep(1)  # import time
    #         print(f"Warning: Printer not found, trying again... {i}")
    #         i += 1
    #         print_failed = True

    # if print_failed == True:
    #     return "Emt, joku juttu meni rikki"


def connecting(print_data):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(connect_and_send(print_data))
