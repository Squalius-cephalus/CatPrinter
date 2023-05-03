import time
from tkinter import *
import tkinter as tk
from PIL import ImageTk, Image, ImageOps
from tkinter import filedialog
# TODO: rename print2 to something better.
import print2
import tempfile
import yaml


with open("config.yaml", "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
printer_width = config["printer_width"]

root = Tk()
root.geometry("800x600")
root.title("Cat Printer")
root.resizable(width=False, height=False)

# Create a global variable to store the panel object
panel = None
img = None
# TODO: Make better "blank" image!
temp_path = "Untitled.png"

default_img = Image.new(
    'RGB', (printer_width, printer_width), color='gray')
img = ImageTk.PhotoImage(default_img)


def save_settings(device_name, contrast, feed_lines, printer_width):

    # Yes, this is not good way to do this.
    config["bluetooth_name"] = device_name
    config["contrast"] = contrast-1
    config["feed_lines"] = int(feed_lines)
    config["printer_width"] = int(printer_width)
    with open("config.yaml", "w") as new_file:
        yaml.dump(config, new_file)


def open_settingswindow():
    settings_window = tk.Toplevel()

    tk.Label(settings_window, text="Device name").grid(row=0)
    tk.Label(settings_window, text="Contrast").grid(row=1)
    tk.Label(settings_window, text="Feed lines").grid(row=2)
    tk.Label(settings_window, text="Printer width").grid(row=3)

    device_name = tk.Entry(settings_window)
    device_name.insert(0, config["bluetooth_name"])

    contrast = Scale(settings_window, from_=1, to=3, orient=HORIZONTAL)
    contrast.set(config["contrast"]+1)
    # contrast = tk.Entry(settings_window)
    # contrast.insert(0, config["contrast"])
    feed_lines = tk.Entry(settings_window)
    feed_lines.insert(0, config["feed_lines"])
    printer_width = tk.Entry(settings_window)
    printer_width.insert(0, config["printer_width"])

    save_button = tk.Button(
        settings_window, text="Save", command=lambda: save_settings(device_name.get(), contrast.get(), feed_lines.get(), printer_width.get()))
    exit_button = tk.Button(settings_window, text="Exit",
                            command=settings_window.destroy)

    device_name.grid(row=0, column=1)
    contrast.grid(row=1, column=1)
    feed_lines.grid(row=2, column=1)
    printer_width.grid(row=3, column=1)

    save_button.grid(row=4, column=0)
    exit_button.grid(row=4, column=1)


def openfn():
    filename = filedialog.askopenfilename(title='open')
    return filename


def save_temp_image(image):
    # Create a temporary file to save the image
    with tempfile.NamedTemporaryFile(suffix='.PNG', delete=False) as temp:
        # Save the image to the temporary file
        image.save(temp.name)
        # Print the path of the temporary file
        print('Temporary image saved to:', temp.name)
        return temp.name


def open_img():
    global panel  # Access the global panel object
    global img
    global temp_path

    # TODO: Too small images with alpha channel does weird things. Scale images to bigger than printers width.

    x = openfn()
    img = Image.open(x)
    img = print2.render_image(img, False)
    mywidth = printer_width

    wpercent = (mywidth/float(img.size[1]))
    hsize = int((float(img.size[0])*float(wpercent)))
    img = img.resize((hsize, mywidth), Image.ANTIALIAS)
    print(img)
    img = ImageTk.PhotoImage(img)

    if panel:  # If the panel object exists, destroy it
        panel.destroy()
    panel = Label(root, image=img)
    panel.image = img
    panel.pack()

    temp_path = save_temp_image(ImageTk.getimage(img))
    print(type(temp_path))


def PreparePrint():
    global temp_path

    data = print2.tulostus(temp_path)
    set_status(f"Connecting to printer...")
    ConnectingToPrinter(data)


def ConnectingToPrinter(print_data):
    print_failed = False
    for i in range(1, 4):
        try:
            print2.connecting(print_data)
            set_status(f"Printing done!")
            break
        except:
            set_status(f"Printer not found, trying again...{i}")
            time.sleep(1)  # import time

        print_failed = True

    # TODO: Fix this, sometimes this does not fail but still sets "print_failed" true

    if print_failed:
        set_status(f"WARNING! Printer not found!")


btn = Button(root, text='Open image', command=open_img)
btn.pack()
settingsbutton = tk.Button(root, text="Open settings",
                           command=open_settingswindow)
settingsbutton.pack()


def update_status_label(text):
    status_label.config(text=text)


def set_status(status):
    status_label.config(text=status)
    status_label.update()


status_label = tk.Label(root, text="Ready", bd=1,
                        relief=tk.SUNKEN, anchor=tk.W)
status_label.pack(side=tk.BOTTOM, fill=tk.X)


panel = Label(root, image=img)
panel.image = img
panel.pack()
btn2 = Button(root, text='Print image', command=PreparePrint)
btn2.pack(side='bottom')


root.mainloop()
