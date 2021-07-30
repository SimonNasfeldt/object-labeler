import glob
import os
import shutil
import json

from pathlib import Path
from PIL import Image, ImageTk
from functools import partial

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter.constants import ANCHOR

class App(tk.Frame):
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)

        parent.update()

        canvas_width = parent.winfo_width()
        canvas_height = parent.winfo_height()
        sidebar_width = 200
        
        self.id = None
        self.class_selected = None
        self.x0 = 0
        self.y0 = 0
        self.x1 = 0
        self.y1 = 0

        # Import options
        options_file = Path(__file__).with_name('options.json')

        with options_file.open('r') as file:
            options = json.load(file)

            print("options:", options)

            self.images_path = options["images_path"]
            self.labels_path = options["labels_path"]
            self.yolo_directory = options["yolo_directory"]
            self.yolo_weightfile = options["yolo_weightfile"]
            self.yolo_output = options["yolo_output"]

            self.class_names = options["class_names"]

        # Class
        self.class_colors = ["red", "blue", "green", "yellow", "orange", "cyan", "magenta", "white"]
        self.class_id = {}
        self.class_text = {}
        
        # Canvas
        self.grip_canvas = ttk.Sizegrip(parent)
        self.grip_canvas.grid(row=0, column=0, sticky="nw")

        self.canvas = tk.Canvas(self.grip_canvas, width=canvas_width, height=canvas_height, bg="white")
        self.canvas.grid(row=0, column=0, sticky='nsew')

        # Image
        self.image_index = 0
        self.image_list = self.image_load_all(self.images_path, self.labels_path)

        self.image = self.canvas.create_image(0, 0, anchor="nw")
        
        if len(self.images_path) > 0:
            self.image_set(self.image_list[self.image_index])

        # Guides
        self.line_h = self.canvas.create_line(0, 0, 10000, 0)
        self.line_v = self.canvas.create_line(0, 0, 0, 10000)

        # Scrollbar
        xscrollbar = tk.Scrollbar(parent, orient=tk.HORIZONTAL)
        xscrollbar.grid(row=1, column=0, sticky="ew")

        yscrollbar = tk.Scrollbar(parent, orient=tk.VERTICAL)
        yscrollbar.grid(row=0, column=1, sticky="ns")

        xscrollbar.config(command=self.canvas.xview)
        yscrollbar.config(command=self.canvas.yview)

        self.canvas.config(scrollregion=self.canvas.bbox(self.image))

        # Sidebar
        self.sidebar = tk.Frame(parent, width=sidebar_width)
        self.sidebar.grid(row=0, column=2, sticky='nsew')

        # Class Display
        self.string = tk.StringVar()
        self.label = tk.Label(self.sidebar, textvariable=self.string)
        self.label.grid(row=0, column=0)

        # Class Listbox
        self.listbox = tk.Listbox(self.sidebar)
        self.listbox.grid(row=1, column=0)

        for name in self.class_names:
            self.listbox.insert(tk.END, name)
        
        self.listbox.bind('<<ListboxSelect>>', self.class_choose)

        # Select Class Button
        tk.Button(self.sidebar, text="<-", command=self.image_previous).grid(row=2, column=0, sticky="w")
        tk.Button(self.sidebar, text="->", command=self.image_next).grid(row=2, column=0, sticky="e")

        # Load images
        #tk.Button(self.sidebar, text="Load images", command=self.image_load_all).grid(row=3, column=0)
        
        # Autolabel Button
        tk.Button(self.sidebar, text="Predict labels (All)", command=self.yolo_label, bg="yellow").grid(row=4, column=0)

        # Path Checks
        self.path_checklist = []

        self.path_checklist.append({"name": "images path", "path": self.images_path})
        self.path_checklist.append({"name": "labels path", "path": self.labels_path})
        self.path_checklist.append({"name": "yolo detect.py", "path": self.yolo_directory, "ext": "*.py"})
        self.path_checklist.append({"name": "yolo weights .pt", "path": self.yolo_weightfile, "ext": "*.pt"})
        self.path_checklist.append({"name": "yolo output", "path": self.yolo_output})

        for i, check in enumerate(self.path_checklist):
            cmd = partial(self.choose_dir, check)
            check["button"] = tk.Button(self.sidebar, text=check["name"], command=self.check_dirs)
            check["button"].grid(row=5+i, column=0)
        
        self.check_dirs()

        # Mouse Binds
        self.canvas.bind("<Button-1>", self.rectangle_start)
        self.canvas.bind("<B1-Motion>", self.rectangle_move)
        self.canvas.bind("<Motion>", self.mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.rectangle_stop)

        # Keyboard Binds
        self.canvas.bind_all("<Left>", self.image_previous)
        self.canvas.bind_all("<Right>", self.image_next)

        # Resize
        self.grip_canvas.bind("<Configure>", self.resize)

    def resize(self, event):
        self.canvas.configure(width=event.width, height=event.height)

    def check_dirs(self):
        for check in self.path_checklist:
            if os.path.exists(check["path"]):
                check["button"].config(fg="green")
                check["check"] = True
            else:
                check["button"].config(fg="red")
                check["check"] = False
        
        if all(check["check"] for check in self.path_checklist):
            return True
        else:
            return False
    
    def choose_dir(self, check):
        if "ext" in check:
            path = filedialog.askopenfilename(initialdir = "/",
                title = "Select File",
                filetypes=(("File", check["ext"]), ("Any", "*.*")))
        else:
            path = filedialog.askdirectory(initialdir = "/",title = "Select Folder")
        
        if path:
            check["path"] = path

    def yolo_label(self):
        if self.check_dirs():
            # Remove previous predictions
            if os.path.exists(self.yolo_output):
                shutil.rmtree(self.yolo_output)
                print(f"Removed previously predicted labels from {self.yolo_output}")

            # predict labels
            os.system(f"python {self.yolo_directory} \
                --save-txt \
                --nosave \
                --weights {self.yolo_weightfile} \
                --img 640 \
                --conf 0.25 \
                --name {self.yolo_output} \
                --source {self.images_path}")
            
            # Move predicted labels to label folder
            print("moving predictions to label folder...")

            file_list = os.listdir(f"{self.yolo_output}/labels/")

            for file in file_list:
                print(f"{self.yolo_output}/labels/{file}\n", "\____", f"{self.labels_path}/{file}")
                shutil.move(f"{self.yolo_output}/labels/{file}", f"{self.labels_path}/{file}")
            
            # Reload labels for current image
            self.rectangle_delete_all()
            self.rectangle_load(self.image_list[self.image_index]["label_path"])

            print(f"Done, {len(file_list)} images labeled")
    
    def mouse_move(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        self.canvas.coords(self.line_h, 0, y, 10000, y)
        self.canvas.coords(self.line_v, x, 0, x, 10000)

    def rectangle_create(self, x0, y0, x1, y1, class_id):
        id = self.canvas.create_rectangle(x0, y0, x1, y1)

        color = self.class_colors[class_id] if class_id < len(self.class_colors) else "gray"

        self.canvas.itemconfig(id, fill=color)
        self.canvas.itemconfig(id, outline="black")
        self.canvas.itemconfig(id, stipple="gray50")
        self.canvas.itemconfig(id, tag="label")

        self.class_id[id] = class_id
        self.class_text[id] = self.canvas.create_text(x0, y0, anchor="nw", text=self.class_names[class_id])

        self.canvas.tag_bind(id, "<Button-3>", self.rectangle_clicked)
        self.canvas.tag_bind(self.class_text[id], "<Button-3>", self.rectangle_clicked_text)

        return id
    
    def rectangle_delete(self, id):
        self.canvas.delete(self.class_text[id])
        self.canvas.delete(id)

        del self.class_id[id]
        del self.class_text[id]
    
    def rectangle_delete_all(self):
        rectangle_list = self.canvas.find_withtag("label")

        for rectangle in rectangle_list:
            self.rectangle_delete(rectangle)

    def rectangle_start(self, event):
        if self.class_selected is not None:
            self.x0 = self.canvas.canvasx(event.x)
            self.y0 = self.canvas.canvasy(event.y)

            self.id = self.rectangle_create(self.x0, self.y0, self.x0, self.y0, self.class_selected)

    def rectangle_move(self, event):
        if self.id is not None:
            self.x1 = self.canvas.canvasx(event.x)
            self.y1 = self.canvas.canvasy(event.y)

            # Change coordinates of the label
            self.canvas.coords(self.id, self.x0, self.y0, self.x1, self.y1)
            
            # Replace class-name text to upper left corner
            _, text_y = self.canvas.coords(self.class_text[self.id])

            if self.x1 < self.x0:
                self.canvas.coords(self.class_text[self.id], self.x1, text_y)
            
            text_x, _ = self.canvas.coords(self.class_text[self.id])

            if self.y1 < self.y0:
                self.canvas.coords(self.class_text[self.id], text_x, self.y1)
    
    def rectangle_stop(self, event):
        self.id = None
    
    def rectangle_clicked(self, event):
        id = event.widget.find_withtag("current")[0]

        self.rectangle_delete(id)
    
    def rectangle_clicked_text(self, event):
        id = event.widget.find_withtag("current")[0]
        id_rectangle = list(self.class_text.keys())[list(self.class_text.values()).index(id)]

        self.rectangle_delete(id_rectangle)
    
    def rectangle_save(self, filename):
        try:
            W = self.canvas.bbox(self.image)[2] - self.canvas.bbox(self.image)[0]
            H = self.canvas.bbox(self.image)[3] - self.canvas.bbox(self.image)[1]

            rectangle_list = self.canvas.find_withtag("label")
            
            with open(filename, 'w') as f:
                for rectangle in rectangle_list:
                    class_id = self.class_id[rectangle]
                    x0 = self.canvas.coords(rectangle)[0]/W
                    y0 = self.canvas.coords(rectangle)[1]/H
                    x1 = self.canvas.coords(rectangle)[2]/W
                    y1 = self.canvas.coords(rectangle)[3]/H

                    x = x0 + (x1 - x0)/2
                    y = y0 + (y1 - y0)/2
                    w = x1 - x0
                    h = y1 - y0

                    f.write(f"{class_id} {x} {y} {w} {h}\n")
            
            print("Saved labels:", filename)
        except:
            print("Failed to save labels:")
    
    def rectangle_load(self, filename):
        W = self.canvas.bbox(self.image)[2] - self.canvas.bbox(self.image)[0]
        H = self.canvas.bbox(self.image)[3] - self.canvas.bbox(self.image)[1]

        if os.path.exists(filename):
            with open(filename) as file:
                for line in file:
                    values = line.split()

                    class_id = int(values[0])

                    x = float(values[1])
                    y = float(values[2])
                    w = float(values[3])
                    h = float(values[4])

                    x0 = (x - w/2)*W
                    y0 = (y - h/2)*H
                    x1 = (x + w/2)*W
                    y1 = (y + h/2)*H

                    self.rectangle_create(x0, y0, x1, y1, class_id)
    
    def class_choose(self, event):
        try:
            id = event.widget.curselection()[0]

            self.class_selected = id
            name = self.class_names[id]

            self.string.set(f"Class: {name}")
        except:
            print("No class selected")
    
    def image_load_all(self, images_folder, labels_folder):
        ext_list = ["png", "jpg"]
        image_list = []

        for ext in ext_list:
            for file in glob.glob(f"{images_folder}/*.{ext}"):
                image_path = f"{images_folder}/{os.path.basename(file)}"
                label_path = f"{labels_folder}/{os.path.splitext(os.path.basename(file))[0]}.txt"

                #print(image_path, label_path)

                image_list.append({"image_path": image_path, "label_path": label_path})
        
        return image_list

    def image_set(self, image):
        try:
            self.photoimage = ImageTk.PhotoImage(file=image["image_path"])

            self.canvas.itemconfig(self.image, image=self.photoimage)
            self.canvas.config(scrollregion=self.canvas.bbox(self.image))

            self.rectangle_load(image["label_path"])
        except:
            self.canvas.itemconfig(self.image, image="")
        
            print("Failed to load image:", image["image_path"])
    
    def image_previous(self, *event):
        self.rectangle_save(self.image_list[self.image_index]["label_path"])

        if self.image_index > 0:
            self.image_index -= 1

            self.rectangle_delete_all()
            self.image_set(self.image_list[self.image_index])
    
    def image_next(self, *event):
        self.rectangle_save(self.image_list[self.image_index]["label_path"])

        if self.image_index < len(self.image_list) - 1:
            self.image_index += 1

            self.rectangle_delete_all()
            self.image_set(self.image_list[self.image_index])

if __name__ == "__main__":
    root = tk.Tk()
    root.title('Labeler')
    root.geometry("800x600")
    root.resizable(True, True)
    root.rowconfigure(0, weight=1)
    root.columnconfigure(0, weight=1)

    app = App(root)

    app.mainloop()