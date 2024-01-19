import PySimpleGUI as sg
import threading
import time
import os

class PathChoice:
    def __init__(self):
        self.layout = [[sg.Text("segmentation folder\t"), sg.Input(key = 'good segmentation', size = (50, 50)), sg.FolderBrowse()],
                      [sg.Text("oversegmentation (optional)\t"), sg.Input(key='oversegmentation', size = (50, 50)), sg.FilesBrowse()],
                      [sg.Text("start"), sg.Input(key = "start", size = (6, 6)),
                       sg.Text("end"), sg.Input(key = "end", size = (6, 6)),
                       sg.Text("interval"), sg.Input(key = "interval", size = (6, 6)),
                       sg.Text("      Pixel size:"),
                       sg.Text("x"), sg.Input(key = "x_pixel_size", size = (5, 5)),
                       sg.Text("y"), sg.Input(key = "y_pixel_size", size = (5, 5)),
                       sg.Text("z"), sg.Input(key = "z_pixel_size", size = (5, 5))],
                      [sg.Text("")],
                      [sg.OK(), sg.Cancel()]]

        self.window = sg.Window('Choose working directories').Layout(self.layout)

    def prompt(self):

        while True:
            event, values = self.window.Read()

            if event == "OK":

                if values['good segmentation'] == "":
                    sg.popup("Please select a folder of segmentation images")
                    continue

                elif not os.path.exists(values['good segmentation']):
                    sg.popup("The folder of segmentation images is not found. Please use the browse button.")
                    continue

                if values['oversegmentation'] != "" and os.path.exists(values['oversegmentation']) == False:
                    sg.popup("The folder of oversegmentation images is not found. Please correct or leave blank.")
                    continue
                
                self.window.close()
                
                if values['start'] == '':
                    values['start'] = -1
                    
                if values['end'] == '':
                    values['end'] = -1

                if values['interval'] == '':
                    values['interval'] = 1

                if values["x_pixel_size"] == "":
                    values["x_pixel_size"] = 1

                if values["z_pixel_size"] == "":
                    values["z_pixel_size"] = 1

                aspect_ratio = float(values["z_pixel_size"]) / float(values["x_pixel_size"])
                    
                return values['good segmentation'], values['oversegmentation'], int(values['start']), int(values['end']), int(values['interval']), aspect_ratio
            
            elif event == "Cancel":
                self.window.close()
                return "", ""


################################################################################################################################################################################

class SaveChoice:
    def __init__(self):
        self.layout = [[sg.Text("Save To..."), sg.Input(key='saveas'), sg.FolderBrowse()],
                       [sg.OK(), sg.Cancel()]]

        self.window = sg.Window('Choose working directories').Layout(self.layout)

    def prompt(self):

        while True:
            event, values = self.window.Read()

            if event == "OK":
                self.window.close()
                return values['saveas'] + "/"
            elif event == "Cancel":
                self.window.close()
                return "", ""
################################################################################################################################################################################
            
class ObjectChoice:
    def __init__(self):
        self.layout = [[sg.Text("Find..."), sg.Input(key='find')],
                       [sg.OK(), sg.Cancel()]]

        self.window = sg.Window('Find object ID = ').Layout(self.layout)

    def prompt(self):

        while True:
            event, values = self.window.Read()

            if event == "OK":
                self.window.close()
                return values['find']
            elif event == "Cancel":
                self.window.close()
                return "", ""


#################################################################################################################################################################################
    
class VisualizerGui:

    def __init__(self, visualizer_3d):

        self.visualizer_3d = visualizer_3d
        
        self.layout = [  [
             #sg.Button('Save'),
             sg.Button('Correction'),
             sg.Button('Correct all'),
             sg.Button('Make new'),
             sg.Button('Save all'),
             sg.Button('Snapshot'),
             sg.Button('Exit')
             ],
                         
             [
             sg.Button('Gray others'),
             sg.Button('Show grayed'),
             #sg.Button('Randomize colors'),
             sg.Button('Set/clear source'),
             sg.Button('Set/clear correction'),
             #sg.Button('Color all selected'),
             sg.Button("Find object")
             ],
                         
             [
             sg.Button('Mark'),
             sg.Button('Unmark'),
             #sg.Button('Switch good/bad'),
             sg.Button('Show marked'),
             sg.Button('Show unmarked'),
             sg.Button('Show hidden'),
             sg.Button('Save marked')
             ],

            [sg.Button('<'),
             sg.Slider(range=(self.visualizer_3d.start_t, self.visualizer_3d.end_t-1),
                       default_value = self.visualizer_3d.start_t,
                       size=(50, 10),
                       orientation="h",
                       resolution = self.visualizer_3d.interval,
                        enable_events=True, key="slider"),
             sg.Button('>'),]]

        self.window = sg.Window('Realtime Shell Command Output', self.layout, finalize = True)
        self.window['slider'].bind('<ButtonRelease>', '_released')

    def run_loop(self):

        while True:             # Event Loop

            #check_update_camera()
            #time.sleep(0.2)
            
            event, values = self.window.Read()

            if event == "slider":
                try:
                    self.visualizer_3d.t = int(values["slider"])
                    self.visualizer_3d.update_time_view()

                    #update_thread = threading.Thread(target = self.visualizer_3d.update_time_view, args=(), daemon=True)
                    #update_thread.start()
                    #update_thread.join()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in slider:\n")
                        f.write (str(e) + "\n")
                    
            elif event == 'slider_released':
                try:
                    self.visualizer_3d.update_camera()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in slider_released:\n")
                        f.write (str(e) + "\n")

            elif event == '>' and self.visualizer_3d.t < self.visualizer_3d.end_t-1:
                try:
                    current_position = self.visualizer_3d.v.get("lookat")
                    self.visualizer_3d.v.set(lookat = current_position + (0, 0, self.visualizer_3d.interval * self.visualizer_3d.next_t_in_space))
                    self.visualizer_3d.t += self.visualizer_3d.interval
                    self.visualizer_3d.update_camera()

                    self.window['slider'].update(value = self.visualizer_3d.t)

                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in next button (>):\n")
                        f.write (str(e) + "\n")
                
            elif event == '<' and self.visualizer_3d.t > self.visualizer_3d.start_t:

                try:
                    current_position = self.visualizer_3d.v.get("lookat")
                    self.visualizer_3d.v.set(lookat = current_position - (0, 0, self.visualizer_3d.interval * self.visualizer_3d.next_t_in_space))
                    self.visualizer_3d.t -= self.visualizer_3d.interval
                    self.visualizer_3d.update_camera()

                    self.window['slider'].update(value = self.visualizer_3d.t)

                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in previous button (<):\n")
                        f.write (str(e) + "\n")

            elif event == 'Correction':
                try:
                    self.visualizer_3d.correction()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in Correction:\n")
                        f.write (str(e) + "\n")

            elif event == 'Correct all':
                try:
                    self.visualizer_3d.correct_all()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in correct_all:\n")
                        f.write (str(e) + "\n")
                
            elif event == 'Hide selected':
                try:
                    self.visualizer_3d.hide_selected()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in hide_selected:\n")
                        f.write (str(e) + "\n")

            elif event == 'Hide all others':
                try:
                    self.visualizer_3d.hide_all_others()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in hide_all_others:\n")
                        f.write (str(e) + "\n")

            elif event == 'Gray others':
                try:
                    self.visualizer_3d.gray_all_others()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in gray_others:\n")
                        f.write (str(e) + "\n")

            elif event == 'Show grayed':
                try:
                    self.visualizer_3d.show_grayed()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in show_grayed:\n")
                        f.write (str(e) + "\n")

            elif event == 'Show unmarked':
                try:
                    self.visualizer_3d.hide_objects_from_file("hidden_objects.txt")
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in show_bad:\n")
                        f.write (str(e) + "\n")

            elif event == 'Mark':
                try:
                    self.visualizer_3d.add_objects_to_file("hidden_objects.txt")
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in mark_good:\n")
                        f.write (str(e) + "\n")

            elif event == 'Switch good/bad':
                try:
                    self.visualizer_3d.invert_good_and_bad("hidden_objects.txt")
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in switch good/bad:\n")
                        f.write (str(e) + "\n")

            elif event == 'Unmark':
                try:
                    self.visualizer_3d.remove_objects_from_file("hidden_objects.txt")
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in mark_bad:\n")
                        f.write (str(e) + "\n")

            elif event == 'Show marked':
                try:
                    self.visualizer_3d.show_only_objects_from_file("hidden_objects.txt")
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in show_good:\n")
                        f.write (str(e) + "\n")

            elif event == 'Dim all others':
                try:
                    self.visualizer_3d.dim_all_others()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in dim_all_others:\n")
                        f.write (str(e) + "\n")

            elif event == 'Show hidden':
                try:
                    self.visualizer_3d.show_hidden()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in show_hidden:\n")
                        f.write (str(e) + "\n")

            elif event == 'Set/clear source':
                try:
                    source_color = self.visualizer_3d.set_source_color()
                    self.window.find_element("Set/clear source").Update(button_color = ("white", source_color))
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in set/clear source:\n")
                        f.write (str(e) + "\n")

            elif event == 'Set/clear correction':
                try:
                    correction_color = self.visualizer_3d.set_correction_color()
                    self.window.find_element("Set/clear correction").Update(button_color = ("white", correction_color))
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in set/clear correction:\n")
                        f.write (str(e) + "\n")

            elif event == 'Randomize colors':
                try:
                    self.visualizer_3d.randomize_colors()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in randomize colors:\n")
                        f.write (str(e) + "\n")

            elif event == 'Save':
                try:
                    save_path = SaveChoice().prompt()
                    self.visualizer_3d.save_current(save_path)
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in Save:\n")
                        f.write (str(e) + "\n")

            elif event == 'Save all':
                try:
                    save_path = SaveChoice().prompt()
                    self.visualizer_3d.save_all(save_path)
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in Save all:\n")
                        f.write (str(e) + "\n")

            elif event == "Make new":
                if True: #try:
                    self.visualizer_3d.recolor_as_new_object()
                else: #except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in make_new:\n")
                        f.write (str(e) + "\n")

            elif event == "Find object":
                try:
                    selected = ObjectChoice().prompt()
                    self.visualizer_3d.show_grayed()
                    self.visualizer_3d.highlight_selected(selected.split(","))
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in find_object:\n")
                        f.write (str(e) + "\n")

            elif event == "Color all selected":
                try:
                    self.visualizer_3d.color_all_selected_the_same()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in color_all_selected:\n")
                        f.write (str(e) + "\n")

            elif event == "High res image":
                try:
                    self.visualizer_3d.high_res_image()
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in high_res_image:\n")
                        f.write (str(e) + "\n")

            elif event == "Snapshot":
                try:
                    if self.visualizer_3d.temp_viewer != None:  
                        self.visualizer_3d.temp_viewer.capture("snap.png")
                        time.sleep(1)
                        self.visualizer_3d.temp_viewer.close()
                        self.visualizer_3d.temp_viewer = None
                    else:
                        self.visualizer_3d.v.capture("snap.png")
                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in snapshot:\n")
                        f.write (str(e) + "\n")

            elif event == "New chunk":

                try:
                
                    if self.visualizer_3d.create_chunk:
                        
                        self.visualizer_3d.create_new_chunk()
                        self.visualizer_3d.create_chunk = False
                        self.visualizer_3d.show_hidden()
                    else:
                        self.visualizer_3d.hide_all_others()
                        self.visualizer_3d.create_chunk = True

                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in new_chunk:\n")
                        f.write (str(e) + "\n")
                

            elif event == "Measure":

                try:
                    if self.visualizer_3d.measure_mode == -1:
                        self.visualizer_3d.hide_all_others()
                    else:
                        self.visualizer_3d.show_hidden()
                    self.visualizer_3d.measure_mode = -self.visualizer_3d.measure_mode

                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in Measure:\n")
                        f.write (str(e) + "\n")
                
            elif event == 'Exit' or event == sg.WIN_CLOSED:
                try:
                    self.visualizer_3d.terminate()
                    break

                except Exception as e:
                    with open ("error_log.txt", "a+") as f:
                        f.write ("Error occurred in Exit:\n")
                        f.write (str(e) + "\n")

    
