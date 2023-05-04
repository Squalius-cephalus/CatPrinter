import time
from tkinter import *
import tkinter as tk
from PIL import ImageTk, Image, ImageOps
from tkinter import filedialog, messagebox

import printing
import tempfile
import yaml


with open("config.yaml", "r") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
printer_width = config["printer_width"]

root = Tk()
root.geometry("500x550")
root.title("Cat Printer")
root.resizable(width=False, height=False)

panel = None
img = None
temp_path = None

default_img = Image.new(
    'RGB', (printer_width, printer_width), color='gray')
img = ImageTk.PhotoImage(default_img)

icon_open = PhotoImage(file='assets/bxs-folder-open.png')
icon_settings = PhotoImage(file='assets/bx-cog.png')
icon_print = PhotoImage(file='assets/bx-printer.png')
icon_help = PhotoImage(file="assets/bx-question-mark.png")
icon_app = PhotoImage(file="assets/app_icon.png")
icon_save = PhotoImage(file="assets/bx-save.png")


helpimage = Image.open("assets/help.png")

# Muuta kuva tkinter-yhteensopivaksi
tk_helpimage = ImageTk.PhotoImage(helpimage)


def open_helpwindow():
    help_window = Toplevel()
    help_window.title("Help")
    help_window.resizable(width=False, height=False)
    label = Label(help_window, image=tk_helpimage)
    label.pack()


def save_settings(device_name, contrast, feed_lines, printer_width, header_lines):

    # Yes, this is not good way to do this.
    config["bluetooth_name"] = device_name
    config["contrast"] = contrast-1
    config["feed_lines"] = int(feed_lines)
    config["printer_width"] = int(printer_width)
    config["header_lines"] = int(header_lines)
    with open("config.yaml", "w") as new_file:
        yaml.dump(config, new_file)


def open_settingswindow():
    settings_window = tk.Toplevel()
    settings_window.geometry("300x200")
    settings_window.title("Settings")
    settings_window.resizable(width=False, height=False)

    tk.Label(settings_window, text="Device name").grid(row=0)
    tk.Label(settings_window, text="Contrast").grid(row=1)
    tk.Label(settings_window, text="Feed lines").grid(row=2)
    tk.Label(settings_window, text="Printer width").grid(row=4)
    tk.Label(settings_window, text="Header lines").grid(row=3)
    device_name = tk.Entry(settings_window)
    device_name.insert(0, config["bluetooth_name"])

    contrast = Scale(settings_window, from_=1, to=3, orient=HORIZONTAL)
    contrast.set(config["contrast"]+1)
    feed_lines = tk.Entry(settings_window)
    feed_lines.insert(0, config["feed_lines"])
    printer_width = tk.Entry(settings_window)
    printer_width.insert(0, config["printer_width"])
    header_lines = tk.Entry(settings_window)
    header_lines.insert(0, config["header_lines"])

    device_name.grid(row=0, column=1)
    contrast.grid(row=1, column=1)
    feed_lines.grid(row=2, column=1)
    printer_width.grid(row=4, column=1)
    header_lines.grid(row=3, column=1)

    buttonframe = Frame(settings_window)
    buttonframe.grid(row=5, column=1)
    save_button = tk.Button(
        buttonframe, text="Save", font=(
            'Helvetica 15'), image=icon_save, height=30, width=70, compound=LEFT, command=lambda: save_settings(device_name.get(), contrast.get(), feed_lines.get(), printer_width.get(), header_lines.get()))
    help_button = tk.Button(buttonframe, text="Help", font=(
        'Helvetica 15'), image=icon_help, height=30, width=70, compound=LEFT,
        command=open_helpwindow)

    exit_button = tk.Button(buttonframe, text="Close", font=(
        'Helvetica 15'), image=icon_settings, height=30, width=70, compound=LEFT,
        command=settings_window.destroy)

    save_button.pack(side='left', anchor='w', expand=True)
    help_button.pack(side='right', anchor='w', expand=True)


def open_file():
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

    openfile = open_file()
    img = Image.open(openfile)
    img = printing.render_image(img, False)
    temp_path = save_temp_image(img)
    # converts temp image to greyscale and scales it down to fit to the window
    wpercent = (printer_width/float(img.size[1]))
    hsize = int((float(img.size[0])*float(wpercent)))
    img = ImageOps.grayscale(img)
    img = img.convert("L")
    img = img.resize((hsize, printer_width))
    print(img)
    img = ImageTk.PhotoImage(img)

    if panel:  # If the panel object exists, destroy it
        panel.destroy()
    panel = Label(root, image=img)
    panel.image = img
    panel.pack()

    print(type(temp_path))


def prepare_print():
    global temp_path

    if temp_path == None:
        messagebox.showerror("Error!", "Please load an image", icon="error")
        return 0

    data = printing.send_print_data(temp_path)
    set_status(f"Connecting to printer...")
    connect_to_printer(data)


def connect_to_printer(print_data):
    print_failed = False
    for i in range(1, 4):
        try:
            printing.connecting(print_data)

            set_status(f"Printing done!")
            print_failed = False
            break
        except:
            print_failed = True
            set_status(f"Printer not found, trying again...{i}")
            time.sleep(1)  # import time

    if printing.lowbattery == True:
        messagebox.showerror(
            "Warning", "Low battery, please recharge.", icon="warning")

    if print_failed:
        set_status(f"Error! Printer not found!")


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
root.iconphoto(False, icon_app)

buttonframe = Frame(root)
buttonframe.pack(expand=True, fill=BOTH, side="bottom")

settingsbutton = tk.Button(buttonframe, text="Settings", font=(
    'Helvetica 15'), image=icon_settings, height=30, width=130, compound=LEFT,
    command=open_settingswindow)
settingsbutton.pack()


openimagebutton = Button(buttonframe, text="Open image", font=(
    'Helvetica 15'), image=icon_open, height=30, width=130, compound=LEFT, command=open_img)
openimagebutton.pack(side='right', anchor='w', expand=True)

printbutton = Button(buttonframe, text="Print image", font=(
    'Helvetica 15'), image=icon_print, height=30, width=130, compound=LEFT,  command=prepare_print)
printbutton.pack(side='left', anchor='e', expand=True)


root.mainloop()
