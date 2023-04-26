from tkinter import *
from PIL import ImageTk, Image
from tkinter import filedialog
import os
import print2
import tempfile


root = Tk()
root.geometry("550x300+300+150")
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


def test():
    print(img)


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


btn = Button(root, text='open image', command=open_img)
btn.pack()


def tulosta():
    global temp_path
    print2.tulostus(temp_path)


panel = Label(root, image=img)
panel.image = img
panel.pack()
btn2 = Button(root, text='print', command=tulosta)
btn2.pack(side='bottom')

root.mainloop()
