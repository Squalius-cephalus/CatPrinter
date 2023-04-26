import time
from tkinter import *
import tkinter as tk
from PIL import ImageTk, Image
from tkinter import filedialog
import print2
import tempfile


root = Tk()
root.geometry("800x600")
root.resizable(width=True, height=True)

# Create a global variable to store the panel object
panel = None
img = None
temp_path = "Untitled.png"

default_img = Image.new('RGB', (250, 250), color='gray')
img = ImageTk.PhotoImage(default_img)


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

    x = openfn()
    img = Image.open(x)
    img = print2.render_image(img, False)
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

    if print_failed:
        set_status(f"WARNING! Printer not found!")


btn = Button(root, text='Open image', command=open_img)
btn.pack()


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
