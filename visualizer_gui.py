import tkinter as tk
from tkinter import filedialog, ttk

class PathChoice:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Choose working directories")

        # Container frame for directory paths
        path_frame = tk.Frame(self.root, padx=10, pady=10)
        path_frame.grid(row=0, column=0, sticky="ew")

        # Good segmentation
        tk.Label(path_frame, text="segmentation").grid(row=0, column=0, sticky="w")
        self.good_segmentation_entry = tk.Entry(path_frame)
        self.good_segmentation_entry.grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(path_frame, text="Browse", command=lambda: self.browse("good segmentation")).grid(row=0, column=2, padx=5)

        # Oversegmentation
        tk.Label(path_frame, text="oversegmentation (optional)").grid(row=1, column=0, sticky="w")
        self.oversegmentation_entry = tk.Entry(path_frame)
        self.oversegmentation_entry.grid(row=1, column=1, sticky="ew", padx=5)
        tk.Button(path_frame, text="Browse", command=lambda: self.browse("oversegmentation")).grid(row=1, column=2, padx=5)

        # Raw
        tk.Label(path_frame, text="raw (optional)").grid(row=2, column=0, sticky="w")
        self.raw_entry = tk.Entry(path_frame)
        self.raw_entry.grid(row=2, column=1, sticky="ew", padx=5)
        tk.Button(path_frame, text="Browse", command=lambda: self.browse("raw")).grid(row=2, column=2, padx=5)

        # Configurations frame
        config_frame = tk.Frame(self.root, padx=10, pady=10)
        config_frame.grid(row=1, column=0, sticky="ew")

        # New column for start, end, and interval
        time_settings_column = tk.Frame(config_frame)
        time_settings_column.grid(row=0, column=0, sticky="nsew")

        tk.Label(time_settings_column, text="start").grid(row=0, column=0, sticky="w")
        self.start_entry = tk.Entry(time_settings_column)
        self.start_entry.grid(row=1, column=0, padx=5, pady=2)

        tk.Label(time_settings_column, text="end").grid(row=2, column=0, sticky="w")
        self.end_entry = tk.Entry(time_settings_column)
        self.end_entry.grid(row=3, column=0, padx=5, pady=2)

        tk.Label(time_settings_column, text="interval").grid(row=4, column=0, sticky="w")
        self.interval_entry = tk.Entry(time_settings_column, textvariable=tk.StringVar(value="1"))
        self.interval_entry.grid(row=5, column=0, padx=5, pady=2)

        # New column for pixel sizes
        pixel_size_column = tk.Frame(config_frame)
        pixel_size_column.grid(row=0, column=1, sticky="nsew", padx=20)  # Pad to separate columns

        tk.Label(pixel_size_column, text="pixel size X").grid(row=0, column=0, sticky="w")
        self.pixel_x_entry = tk.Entry(pixel_size_column, textvariable=tk.StringVar(value="1"))
        self.pixel_x_entry.grid(row=1, column=0, padx=5, pady=2)

        tk.Label(pixel_size_column, text="pixel size Y").grid(row=2, column=0, sticky="w")
        self.pixel_y_entry = tk.Entry(pixel_size_column, textvariable=tk.StringVar(value="1"))
        self.pixel_y_entry.grid(row=3, column=0, padx=5, pady=2)

        tk.Label(pixel_size_column, text="pixel size Z").grid(row=4, column=0, sticky="w")
        self.pixel_z_entry = tk.Entry(pixel_size_column, textvariable=tk.StringVar(value="2"))
        self.pixel_z_entry.grid(row=5, column=0, padx=5, pady=2)

        # Action buttons
        button_frame = tk.Frame(self.root, padx=10, pady=20)
        button_frame.grid(row=2, column=0, sticky="ew")
        tk.Button(button_frame, text="OK", command=self.ok).grid(row=0, column=0, padx=10)
        tk.Button(button_frame, text="Cancel", command=self.cancel).grid(row=0, column=1, padx=10)
        
        # Frame weighting for dynamic resizing
        path_frame.grid_columnconfigure(1, weight=1)
        config_frame.grid_columnconfigure([0, 1], weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Resize the window to fit the content
        self.root.resizable(True, False)

    def browse(self, key):
        dirname = filedialog.askdirectory()  # Use askdirectory for folders instead of askopenfilename
        if key == "good segmentation":
            self.good_segmentation_entry.delete(0, tk.END)  # Clear any previous input
            self.good_segmentation_entry.insert(0, dirname)
        elif key == "oversegmentation":
            self.oversegmentation_entry.delete(0, tk.END)  # Clear any previous input
            self.oversegmentation_entry.insert(0, dirname)
        elif key == "raw":
            self.raw_entry.delete(0, tk.END)  # Clear any previous input
            self.raw_entry.insert(0, dirname)

    def ok(self):

        start = self.start_entry.get()
        end = self.end_entry.get()
        interval = self.interval_entry.get()
        size_x = self.pixel_x_entry.get()
        size_y = self.pixel_y_entry.get()
        size_z = self.pixel_z_entry.get()

        try:
            start = int(start)
        except:
            start = 0

        try:
            end = int(end)
        except:
            end = -1

        try:
            interval = int(interval)
        except:
            interval = 1

        try:
            size_x = float(size_x)
        except:
            size_x = 1

        try:
            size_y = float(size_y)
        except:
            size_y = 1

        try:
            size_z = float(size_z)
        except:
            size_z = 2
        
        self.values = (
            self.good_segmentation_entry.get(),
            self.oversegmentation_entry.get(),
            self.raw_entry.get(),
            start,
            end,
            interval,
            size_x,
            size_y,
            size_z
            
        )
        self.root.quit()

    def cancel(self):
        self.values = ()
        self.root.quit()

    def prompt(self):
        self.root.mainloop()
        self.root.destroy()
        return self.values


#############################################################################################################################

import tkinter as tk
from tkinter import ttk

class VisualizerGui:
    def __init__(self, visualizer_3d):
        self.visualizer_3d = visualizer_3d

        # Create Tkinter window
        self.window = tk.Tk()
        self.window.title('Visualizer 3D Controls')

        window_width = 400  # Set the width to 800 pixels (or whatever width you prefer)
        window_height = 100  # Example height, adjust as needed
        self.window.geometry(f'{window_width}x{window_height}')

        # Configure grid columns to expand
        total_columns = 20
        for i in range(total_columns):  # Setup each column to expand
            self.window.grid_columnconfigure(i, weight=1)

        # Define buttons and their actions
        commands = {
            'Save': self.save,
            'Correction': self.visualizer_3d.make_correction,
            'Show unmarked': self.show_unmarked,
            'Show hidden': self.show_all_labels,
            'Gray/show others': self.toggle_gray_others,
            'Set source': self.set_source_color,
            'Set destination': self.set_destination_color,
            #'Make new': self.make_new,
            #'Randomize colors': self.randomize_colors,
            'Exit': self.on_close,
            # Specify additional buttons and their callbacks as needed
        }

        # Create a menu bar
        self.menu_bar = tk.Menu(self.window)
        self.window.config(menu = self.menu_bar)

        # "File" menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff = 0)
        self.menu_bar.add_cascade(label = "File", menu = self.file_menu)
        self.file_menu.add_command(label = "Save                          Ctrl+S", command = self.save)
        self.file_menu.add_command(label = "Save splines", command = self.save_current_splines)
        self.file_menu.add_command(label = "Load splines", command = self.load_splines)
        self.file_menu.add_command(label = "Save spline measurements", command = self.save_splines)
        self.file_menu.add_command(label = "Create/load group", command = self.visualizer_3d.new_group)
        self.file_menu.add_separator()  # Adds a separator line in the menu
        self.file_menu.add_command(label = "Exit", command = self.on_close)

        # "Show" submenu
        self.show_menu = tk.Menu(self.menu_bar, tearoff = 0)
        self.menu_bar.add_cascade(label = "Show", menu = self.show_menu)
        self.show_menu.add_command(label = "Show unmarked (M)", command = self.show_unmarked)
        self.show_menu.add_command(label = "Show marked (U)", command = self.visualizer_3d.show_marked)
        self.show_menu.add_command(label = "Show hidden (A)", command = self.show_all_labels)
        self.show_menu.add_command(label = "Gray/show others (G)", command = self.toggle_gray_others)
        self.show_menu.add_command(label = "Find... (Ctrl+F)", command = self.visualizer_3d.open_input_popup)
        self.show_menu.add_command(label = "Change color of selected (O)", command = self.visualizer_3d.randomize_color_of_selected)
        self.show_menu.add_command(label = "Randomize all colors (Ctrl+O)", command = self.visualizer_3d.randomize_all_colors)
        self.show_menu.add_command(label = "Black and white", command = self.visualizer_3d.shades_of_gray)

        # "Edit" submenu
        self.edit_menu = tk.Menu(self.menu_bar, tearoff = 0)
        self.menu_bar.add_cascade(label = "Edit", menu = self.edit_menu)
        self.edit_menu.add_command(label = "Set source (S)", command = self.set_source_color)
        self.edit_menu.add_command(label = "Set destination (D)", command = self.set_destination_color)
        self.edit_menu.add_command(label = "Switch source and destination (V)", command = self.visualizer_3d.switch_source_destination)
        self.edit_menu.add_command(label = "Correction (Ctrl+Right click)", command = self.visualizer_3d.make_correction)
        self.edit_menu.add_command(label = "Merge on all frames", command = self.visualizer_3d.merge)
        self.edit_menu.add_command(label = "Create new label", command = self.visualizer_3d.make_new)
        self.edit_menu.add_command(label = "Delete active spline", command = self.delete_spline)
        self.edit_menu.add_command(label = "Undo (Ctrl+Z)", command = self.visualizer_3d.undo)

        # Slider configuration
        self.slider_value = tk.DoubleVar()
        self.slider = ttk.Scale(self.window, from_ = self.visualizer_3d.start_t, to = self.visualizer_3d.end_t,
                                orient = 'horizontal', variable = self.slider_value,
                                command = self.on_slider_update)
        self.slider.grid(row = 3, column = 1, columnspan = total_columns-1, sticky = 'ew')
        
        # Next and Previous buttons
        tk.Button(self.window, text='<', command=self.prev).grid(row = 3, column = 0, sticky = 'w')
        tk.Button(self.window, text='>', command=self.next).grid(row = 3, column = total_columns, sticky = 'ew')

        # Define button labels with charactes
        default_mode_label = '✋' # Arrow symbol for default mode
        magic_wand_label = '✨'  # Star symbol for magic wand
        draw_line_label = ' ⟅ '  # Wavy dash for drawing/curve fitting
        correction_label = "✂"


        # Buttons
        self.default_mode_btn = tk.Button(self.window, text = default_mode_label, font=("Arial", 14), command = lambda: self.change_mode('default'))
        self.magic_wand_btn = tk.Button(self.window, text = magic_wand_label, font=("Arial", 14), command = lambda: self.change_mode('magic wand'))
        self.draw_line_btn = tk.Button(self.window, text = draw_line_label, font=("Arial", 14), command = lambda: self.change_mode('draw line'))
        self.correction_btn = tk.Button(self.window, text = correction_label, font=("Arial", 14), command = self.visualizer_3d.make_correction)

        self.correction_btn.grid(row = 4, column = 0, padx = 0, pady = 5, columnspan = 1, sticky = "w")
        self.default_mode_btn.grid(row = 4, column = 1, padx = 0, pady = 5, columnspan = 1, sticky = "w")
        self.magic_wand_btn.grid(row = 4, column = 2, padx = 0, pady = 5, columnspan = 1, sticky = "w")
        self.draw_line_btn.grid(row = 4, column = 3, padx = 0, pady = 5, columnspan = 1, sticky = "w")

        self.default_mode_btn.config(relief = "raised", state = "normal")
        self.magic_wand_btn.config(relief = "raised", state = "normal")
        self.draw_line_btn.config(relief = "raised", state = "disabled")

        # Initialize the mode
        self.change_mode('default')

        # Create a label for hover text, initially not shown
        self.hover_info = tk.Label(self.window, text="", font = ("Arial", 10))
        self.hover_info.grid(row = 5, column = 0, columnspan = 4)
        
        # Modify the button creation code to bind mouse enter and leave events
        button_descriptions = {
            self.default_mode_btn: 'Default mode',
            self.magic_wand_btn: 'Magic wand',
            self.draw_line_btn: 'Curve fitting',
            self.correction_btn: 'Make correction'
        }
        
        for button, description in button_descriptions.items():
            button.bind("<Enter>", lambda e, d = description: self.show_hover_text(d))
            button.bind("<Leave>", self.hide_hover_text)

        # Bind the custom close method
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    ################################################################################################################################################

    def show_hover_text(self, description):
        # Display the description in the hover info label
        self.hover_info.config(text=description)

    def hide_hover_text(self, event = None):
        # Hide the hover info label
        self.hover_info.config(text = "")

    def save_splines(self):
        self.visualizer_3d.LineFit.save_spline_measurements()

    ################################################################################################################################################

    def change_mode(self, mode):
        # Deactivate all buttons by setting them to a 'disabled' appearance
        self.default_mode_btn.config(relief = "raised", state = "normal")
        self.magic_wand_btn.config(relief = "raised", state = "normal")
        self.draw_line_btn.config(relief = "raised", state = "normal")

        if self.visualizer_3d.destination_color != 0:
            self.draw_line_btn.config(relief = "raised", state = "normal")

        # Activate the selected mode button
        if mode == 'default':
            self.default_mode_btn.config(relief = "sunken", state = "disabled")
            self.visualizer_3d.enter_default_mode()
            
        elif mode == 'magic wand':
            self.magic_wand_btn.config(relief = "sunken", state = "disabled")
            self.visualizer_3d.enter_magic_wand_mode()
            
        elif mode == 'draw line': # and self.visualizer_3d.destination_color != 0:
            self.draw_line_btn.config(relief = "sunken", state = "disabled")
            self.visualizer_3d.enter_default_mode()
            self.visualizer_3d.enter_spline_mode()

    ################################################################################################################################################

    def show_all_labels(self):
        self.visualizer_3d.show_all_labels()

    ################################################################################################################################################

    def show_unmarked(self):
        self.visualizer_3d.show_unmarked()

    ################################################################################################################################################

    def run_loop(self):
        self.window.mainloop()

    ################################################################################################################################################

    def toggle_gray_others(self):
        if self.visualizer_3d.grayed_out:
            self.visualizer_3d.show_grayed()
        else:
            self.visualizer_3d.gray_all_others()

    ################################################################################################################################################

    def save(self):
        self.visualizer_3d.save_image_data_objects()

    ################################################################################################################################################

    def update_slider_position(self, new_value):
        self.slider_value.set(new_value)

    ################################################################################################################################################

    def set_destination_color(self):
        self.visualizer_3d.update_destination_color()

    ################################################################################################################################################

    def set_source_color(self):
        self.visualizer_3d.update_source_color()

    ################################################################################################################################################
        
    def on_slider_update(self, value):

        rounded_value = int(round(float(value)))
        
        if rounded_value < 0 or rounded_value > self.visualizer_3d.end_t - 1:
            return
        
        self.visualizer_3d.t = rounded_value
        self.visualizer_3d.clear_selection()
        self.visualizer_3d.selected_labels = []

        self.slider_value.set(rounded_value)
        
        self.visualizer_3d.set_current_image(self.visualizer_3d.t)
        self.visualizer_3d.textActor.SetInput("Time: " + str(self.visualizer_3d.t) + "/" + str(len(self.visualizer_3d.imageDataObjects) - 1))

        if self.visualizer_3d.draw_line_mode:
            self.visualizer_3d.LineFit.hide_curves()
            self.visualizer_3d.LineFit.load_existing_models()
            
        self.visualizer_3d.renderer.GetRenderWindow().Render()

    ################################################################################################################################################
        
    def next(self):
        self.on_slider_update(self.visualizer_3d.t + 1)

    ################################################################################################################################################
        
    def prev(self):
        self.on_slider_update(self.visualizer_3d.t - 1)

    ################################################################################################################################################

    def on_close(self):
        # Perform any cleanup tasks here
        print("Closing the application...")
        # Optionally handle other shutdown processes here
        
        # Finally, destroy the window
        self.window.destroy()
        quit()

    ################################################################################################################################################

    def save_current_splines(self):
        self.change_mode("draw line")
        self.visualizer_3d.LineFit.save_current_splines()

    ################################################################################################################################################

    def load_splines(self):
        self.change_mode("draw line")
        self.visualizer_3d.LineFit.load_from_file()

    ################################################################################################################################################

    def delete_spline(self):
        self.visualizer_3d.LineFit.delete_active_spline()
        

