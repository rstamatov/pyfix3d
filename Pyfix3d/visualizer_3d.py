from tifffile import imread, imsave
import numpy as np
#import matplotlib.colors
import time
#from skimage.morphology import erosion

import pptk

import threading
from pynput import mouse
from visualizer_gui import *

#from visualizer_gui import *
from mouse_business import *

# with Python 3.7: downloaded from https://github.com/mhammond/pywin32/releases
#from win32.win32gui import FindWindow, GetWindowRect

import os
import sys
#import matplotlib.pyplot as plt
#from scipy.ndimage import zoom

class Visualizer_3D:
    def __init__(self):
        self.v = pptk.viewer([], [], debug = True)
        self.temp_viewer = None

    def erode_image(self, image):
        return np.subtract(image, erosion(image))

    def delete_temp_files(self):
        if os.path.exists("hidden_objects.txt"):
            os.remove("hidden_objects.txt")
        if os.path.exists("error_log.txt"):
            os.remove("error_log.txt")

    ###########################################################################################################################################

    def add_data(self):

        file_path, oversegmented_path, self.start_t, self.end_t, self.interval, self.z_aspect_ratio = PathChoice().prompt()

        if oversegmented_path == "":
            oversegmented_path = file_path
        if file_path == "":
            file_path = oversegmented_path
            
        start_t, end_t, image_filenames, image_timepoints = self.extract_info_from_filename(file_path)
        start_t_overseg, end_t_overseg, overseg_filenames, overseg_timepoints = self.extract_info_from_filename(oversegmented_path)

        if self.start_t == -1:
            self.start_t = start_t
        if self.end_t == -1:
            self.end_t = end_t

        # his global list contains all points which are part of the segmentation (not background)
        self.all_points = [] # initialize by adding the origin

        # The real color labels of the points - the indices must match those of all_points
        self.real_colors = [] # initialize with a meaningless entry

        # The color labels of the oversegmentations. The indices must match those of the two lists above
        self.overseg_colors = []
        #self.raw_values  = [0]

        # pptk doesn't seem to have the capability to use 4D (3D+t) dimensions.
        # As a workaround, let's display all timepoint stacks but at different spatial locations.
        # This is the number to be added to the Y coordinate, to "create" the next time point
        self.next_t_in_space = 1000
        self.start_indices_at_specific_times = {}

        # Map the color labels in the segmentations to a list of indices of this label
        self.map_overseg_to_indices = {}
        self.map_realseg_to_indices = {}

        self.dimension = None

        # Load the raw files
        """
        self.raws = []
        if raw_path != "":
            start_t_raw, end_t_raw, raw_filenames, raw_timepoints = self.extract_info_from_filename(raw_path)
            for i in range (0, len(raw_filenames)):
                if raw_timepoints[i] > self.start_t and raw_timepoints[i] < self.end_t:
                    self.raws.append(raw_filenames[i])
        """
        

        # Load the data from files
        for i in range (0, len(image_filenames)):
          
            if image_timepoints[i] % self.interval != 0:
                continue

            if self.start_t % self.interval != 0:
                self.start_t = image_timepoints[i]
                
            tif = image_filenames[i]
            print (tif)


            current_t = image_timepoints[i]
            if current_t < self.start_t or current_t  > self.end_t:
                continue

            self.start_indices_at_specific_times[current_t] = len(self.all_points)

            self.map_overseg_to_indices[current_t - self.start_t] = {}
            
            stack = imread(tif)
            overseg_stack = imread(overseg_filenames[i])
                        
            points = np.array(np.where(stack)).T

            for p in points:
                z, y, x = p
                self.real_colors.append(stack[z, y, x])
                
                self.overseg_colors.append(overseg_stack[z, y, x])
                self.all_points.append([z * self.z_aspect_ratio, y, x + (current_t - self.start_t) * self.next_t_in_space])

                if overseg_stack[z, y, x] not in self.map_overseg_to_indices[current_t - self.start_t].keys():
                    self.map_overseg_to_indices[current_t - self.start_t][overseg_stack[z, y, x]] = []
                    
                self.map_overseg_to_indices[current_t - self.start_t][overseg_stack[z, y, x]].append(len(self.all_points)-1)

                if stack[z, y, x] not in self.map_realseg_to_indices:
                    self.map_realseg_to_indices[stack[z, y, x]] = []
                self.map_realseg_to_indices[stack[z, y, x]].append(len(self.all_points)-1)

            if self.dimension == None:
                self.dimension = np.shape(stack)
                
        self.selected_points = []
        self.selected_point_ids = []
        self.selected_times = []
        self.hidden_points = [[0, 0, 0]] * len(self.all_points)

        # Remap the colors to avoid gaps and create a consistent colormap    
        self.all_colors = self.remap_colors(np.array(self.real_colors))

        # Initialize the pptk viewer. debug must be True to avoid a known bug in thread hanging
        self.v.load(self.all_points, self.all_colors, debug = True)
        self.v.set(point_size = 1)

        # This should be the center of the object. TODO - calculate it automatically based on the image dimensions
        #self.v.set(lookat = (25, 166, 140))
        self.t = self.start_t # t is the current timepoint

        # Create the colormap
        self.num_colors = len(np.unique(self.all_colors))
        np.random.seed(0)
        self.colormap = np.random.rand (self.num_colors, 4)
        self.colormap[:, 3] = 1.0 # transparency

        self.colormap_copy = np.copy(self.colormap)
        self.v.set(color_map = self.colormap)
        #self.v.color_map('hsv')

        # The distance of the camera to the object
        self.v.set(r = 200)

        self.rat = mouse.Controller()

        self.raw_v = None
        self.source_idx = None
        self.correction_idx = None
        self.source_color = None

        self.measure_mode = -1
        self.create_chunk = False

        self.v.set(floor_color = [0, 0, 0, 0])
        self.v.set(bg_color = [0, 0, 0, 1])
        self.v.set(show_grid = False)
        self.v.set(show_info = False)
        self.v.set(show_axis = False)

        self.image_filenames = image_filenames
        self.changed_frames = []
               
    ###########################################################################################################################################
    
    def extract_info_from_filename(self, filename):

        # get .tif files only
        tifs = [x for x in os.listdir(filename) if ".tif" in x]
        
        # extract the initial and final timepoints from the names
        timepoints = []
        for tif in tifs:
            timepoints.append(int("".join([s for s in tif.split()[0] if s.isdigit()])))
            
        start_t = np.min(timepoints)
        end_t = np.max(timepoints)

        full_paths = [filename + "/" + x for x in tifs]

        return start_t, end_t, full_paths, timepoints

    ###########################################################################################################################################

    def remap_colors(self, colors):
        """ make a copy of the color labels which is a continuous sequence without gaps.
            Currently, some colors may not be used, which results in unpredictable interpolation
            in the color map. After this remapping, the color map will be consistent. """
        
        unique_labels = list(np.unique(colors))
        remapped = []

        self.real_to_remapped = {}
        
        for i, c in enumerate(colors):
            new_c = unique_labels.index(c)
            remapped.append(new_c)

            if c not in self.real_to_remapped:
                self.real_to_remapped[c] = new_c
                
        return remapped

    ###########################################################################################################################################

    def show_raw(self):

        self.v.load(self.all_points, self.raw_values)
        self.v.color_map("gray")

    ###################################################################################################################

    def reload_view(self, current_lookat):
        
        # set back to the current position
        current_r = self.v.get("r")
        current_phi = self.v.get("phi")
        current_theta = self.v.get("theta")
        
        self.v.clear()
        self.v.load(self.all_points, self.all_colors)
        self.v.set(color_map = self.colormap)
        
        self.v.set(r = current_r)
        self.v.set(theta = current_theta)
        self.v.set(phi = current_phi)

        self.v.set(selected = [])

        self.check_update_camera(current_lookat)
        self.update_camera()

    ###################################################################################################################
        
    def correction(self):

        
        if self.source_color == None:
            return self.correction_standard()
        
        if self.correction_idx == None:
            return

        if len(self.v.get("selected")) == 0:
            return

        current_lookat = self.v.get("lookat")
        
        destination = self.correction_idx

        destination_color = self.real_colors[destination]
        destination_color_remapped = self.all_colors[destination]

        # remove the currently selected, as they are going to be recolored
        self.map_realseg_to_indices[self.source_color] = \
                    list(set(self.map_realseg_to_indices[self.source_color]) - set(self.v.get("selected")))
        
        # add those indices to the new color
        self.map_realseg_to_indices[destination_color] += list(self.v.get("selected"))

        for point_index in self.v.get("selected"):
            
            self.real_colors[point_index] = destination_color
            self.all_colors[point_index] = destination_color_remapped

            source_overseg_color = self.overseg_colors[point_index]
            destination_overseg_color = self.overseg_colors[self.correction_idx]
            
            self.map_overseg_to_indices[self.t-self.start_t][source_overseg_color] = \
                    list(set(self.map_realseg_to_indices[source_overseg_color]) - set(self.v.get("selected")))

            self.map_overseg_to_indices[self.t-self.start_t][destination_overseg_color] += list(self.v.get("selected"))
        
        self.reload_view(current_lookat)

###############################################################################################
        
    def correction_standard(self):

        # no points selected, nothing to do
        if len(self.selected_point_ids) == 0:
            return

        current_lookat = self.v.get("lookat")
        
        # if a correction color is set, use it
        if self.correction_idx != None:
            sources = self.selected_point_ids
            destination = self.correction_idx

        # if not, assume the correction is the last selected color
        else:
            if len(self.selected_point_ids) < 2:
                return
        
            sources = self.selected_point_ids[:-1]
            destination = self.selected_point_ids[-1]

        for s, source in enumerate(sources):

            destination_color = self.real_colors[destination]
            destination_color_remapped = self.all_colors[destination]
            source_overseg_color = self.overseg_colors[source]

            for overseg_index in self.map_overseg_to_indices[self.selected_times[s]-self.start_t][source_overseg_color]:
                self.real_colors[overseg_index] = destination_color
                self.all_colors[overseg_index] = destination_color_remapped

        self.reload_view(current_lookat)

    ###################################################################################################################
        
    def correct_all(self):

        # no points selected, nothing to do
        if len(self.selected_point_ids) == 0:
            return

        current_lookat = self.v.get("lookat")

        # if a correction color is set, use it
        if self.correction_idx != None:
            sources = self.selected_point_ids
            destination = self.correction_idx

        # if not, assume the correction is the last selected color
        else:
            if len(self.selected_point_ids) < 2:
                return
        
            sources = self.selected_point_ids[:-1]
            destination = self.selected_point_ids[-1]

        destination_color = self.real_colors[destination]
        destination_color_remapped = self.all_colors[destination]

        
        for s, source in enumerate(sources):
            
            source_color = self.real_colors[source]

            for ind, c in enumerate(self.real_colors):


                if c == source_color:
            
                    self.real_colors[ind] = destination_color
                    self.all_colors[ind] = destination_color_remapped
                    self.map_realseg_to_indices[destination_color] += self.map_realseg_to_indices[source_color]
                    self.map_realseg_to_indices[source_color] = []
        
        self.reload_view(current_lookat)

        ###################################################################################################################
        
    def recolor_as_new_object_standard(self):
        """ Recolor the selected overseg junk as a new object"""

        # Find the selected object
        if len(self.selected_point_ids) < 1:
            return

        current_lookat = self.v.get("lookat")

        # Extend the colormap
        self.num_colors += 1
        self.colormap = np.random.rand (self.num_colors, 4)
        self.colormap[:, 3] = 0.9 # transparency
        self.colormap[:self.num_colors-1, :] = self.colormap_copy[:self.num_colors-1, :]
        self.colormap_copy = np.copy(self.colormap)
        
        sources = self.selected_point_ids

        # Find the maximum of the objects, to avoid repetition
        max_object_id = np.max(self.real_colors)
        print (max_object_id)

        # Recolor these chunks
        for s, source in enumerate(sources):

            destination_color = max_object_id + 1 + s

            source_overseg_color = self.overseg_colors[source]
            self.map_realseg_to_indices[destination_color] = source

            for overseg_index in self.map_overseg_to_indices[self.selected_times[s]-self.start_t][source_overseg_color]:
                self.real_colors[overseg_index] = destination_color
                self.all_colors[overseg_index] = self.num_colors-1

        self.real_to_remapped[destination_color] = destination_color
        
        self.reload_view(current_lookat)

    ###################################################################################################################
        
    def recolor_as_new_object(self):
        """ Recolor the selected overseg junk as a new object"""

        if self.source_color == None:
            return self.recolor_as_new_object_standard()

        # Else, we are using a source color and need to recolor the selected pixels
        current_lookat = self.v.get("lookat")

        # Find the maximum of the objects, to avoid repetition
        max_object_id = np.max(self.real_colors)
        destination_color = int(max_object_id + 1)
        destination_color_remapped = int(max_object_id + 1)
        destination_overseg_color = 1 + int(np.max(self.overseg_colors))
        self.real_to_remapped[destination_color] = destination_color

        # remove the currently selected, as they are going to be recolored
        self.map_realseg_to_indices[self.source_color] = \
                    list(set(self.map_realseg_to_indices[self.source_color]) - set(self.v.get("selected")))
        
        # add those indices to the new color
        self.map_realseg_to_indices[destination_color] = list(self.v.get("selected"))

        for point_index in self.v.get("selected"):
            
            self.real_colors[point_index] = destination_color
            self.all_colors[point_index] = destination_color_remapped

            source_overseg_color = self.overseg_colors[point_index]
            #destination_overseg_color = self.overseg_colors[point_index]
            
            self.map_overseg_to_indices[self.t-self.start_t][source_overseg_color] = \
                    list(set(self.map_realseg_to_indices[source_overseg_color]) - set(self.v.get("selected")))

            self.map_overseg_to_indices[self.t-self.start_t][destination_overseg_color] = list(self.v.get("selected"))
            self.overseg_colors[point_index] = destination_overseg_color
        
        self.reload_view(current_lookat)


    ###################################################################################################################

    def color_all_selected_the_same_standard(self):
        
        if len(self.selected_point_ids) < 1:
            return

        # Keep the original colors before graying out
        self.colormap_copy = np.copy(self.colormap)


        selected_colors = np.unique(np.array(self.all_colors)[self.selected_point_ids])
        random_color = np.random.rand (4)
        random_color[3] = 0.9 # transparency
        
        for c in selected_colors:
            self.colormap[c, :] = random_color

        self.v.set(color_map = self.colormap)
        self.v.set(selected = [])

        ###################################################################################################################

    def set_source_color(self):

        if self.source_idx != None:
            self.source_idx = None
            self.source_color = None
            return 'slate gray'
        
        if len(self.selected_point_ids) == 0:
            return        
        self.source_idx = self.selected_point_ids[0]
        self.source_color = self.real_colors[self.source_idx]

        color_dec = self.colormap[self.all_colors[self.source_idx], :]
        a, b, c = color_dec[:3]
        a = hex(int(a * 255))[2:]
        b = hex(int(b * 255))[2:]
        c = hex(int(c * 255))[2:]
        
        if len(a) < 2:
            a = "0" + a
        if len(b) < 2:
            b = "0" + b
        if len(c) < 2:
            c = "0" + c
        
        hex_color = "#" + a + b + c
        
        return hex_color

    ###################################################################################################################

    def set_correction_color(self):

        if self.correction_idx != None:
            self.correction_idx = None
            return 'slate gray'
        
        if len(self.selected_point_ids) == 0:
            return        
        self.correction_idx = self.selected_point_ids[0]

        color_dec = self.colormap[self.all_colors[self.correction_idx], :]
        a, b, c = color_dec[:3]
        a = hex(int(a * 255))[2:]
        b = hex(int(b * 255))[2:]
        c = hex(int(c * 255))[2:]
        
        if len(a) < 2:
            a = "0" + a
        if len(b) < 2:
            b = "0" + b
        if len(c) < 2:
            c = "0" + c
        
        hex_color = "#" + a + b + c
        
        return hex_color
        
    ###################################################################################################################

    def save_current(self, save_folder):
        
        # Construct image stacks from the points
        stack = np.zeros(self.dimension)

        for i, p in enumerate(self.all_points):            
            z, y, x = p

            if x // self.next_t_in_space == self.t-self.start_t:
                stack[int(z/self.z_aspect_ratio), y, x % self.next_t_in_space] = self.real_colors[i]

        imsave(save_folder + "t" + str(self.t) + "_corrected.tif", stack)

    ###################################################################################################################

    def save_all(self, save_folder):

        self.show_grayed()
        self.show_hidden()
        
        original_t = self.t
        for t in self.changed_frames:
            print (t)
            self.t = t
            self.save_current(save_folder)
        self.t = original_t

        self.changed_frames = []
            
    ###################################################################################################################

    def make_selection(self):
           
        selected_indices = []
        for index in self.selected_points:

            selected_color = self.all_colors[index]
            selected_indices += [i for i, x in enumerate(self.all_colors) if x == selected_color]
        
        self.v.set(selected = selected_indices)

    ###################################################################################################################
        
    def terminate(self):
        self.v.clear()
        self.v.close()

    ###################################################################################################################

    def check_update_camera(self, current_lookat):

        z, y, x = current_lookat
        displayed_t = z // self.next_t_in_space
        if True: #displayed_t != (self.t-self.start_t):        
            self.v.set(lookat = (z, y, x % self.next_t_in_space + (self.t-self.start_t) * self.next_t_in_space))
       
    ###################################################################################################################

    def update_time_view(self):

        try:
            [z, y, x] = self.v.get("lookat")
            self.v.set(lookat = (z, y, x % self.next_t_in_space + (self.t-self.start_t) * self.next_t_in_space))
        except:
            print ("error occurred in update_time_view")

    ###################################################################################################################
            
    def update_camera(self):

        #self.check_update_camera()
        return

    ###################################################################################################################
        
    def hide_selected(self):

        if len(self.selected_point_ids) == 0:
            return

        current_lookat = self.v.get("lookat")

        # selected_point_ids contain the indices of oversegmented objects
        # find the indices of the truly segmented objects

        selected_colors = np.unique(np.array(self.all_colors)[self.selected_points])
        indices_to_hide = []
        for c in selected_colors:
            indices_to_hide += list(np.where(self.all_colors == c)[0])

        for selected_p in indices_to_hide:

            if self.all_points[selected_p] != [0, 0, 0]:
                self.hidden_points[selected_p] = self.all_points[selected_p]
                self.all_points[selected_p] = [0, 0, 0]

        self.reload_view(current_lookat)
        self.v.set(selected = [])


    ###################################################################################################################

    def hide_all_others(self):

        if len(self.selected_point_ids) == 0:
            return

        current_lookat = self.v.get("lookat")
        
        # selected_point_ids contain the indices of oversegmented objects
        # find the indices of the truly segmented objects

        selected_colors = list(np.unique(np.array(self.real_colors)[self.selected_points]))
        
        all_colors = list(np.unique(np.array(self.real_colors)))

        if 0 in all_colors:
            all_colors.remove(0)
        selected_colors = [x for x in all_colors if x not in selected_colors]

        self.show_hidden(reload = False)
        
        indices_to_hide = []
        for c in selected_colors:
            indices_to_hide += self.map_realseg_to_indices[c]

        for selected_p in indices_to_hide:

            if self.all_points[selected_p] != [0, 0, 0]:
                self.hidden_points[selected_p] = self.all_points[selected_p]
                self.all_points[selected_p] = [0, 0, 0]

        self.reload_view(current_lookat)
        self.v.set(selected = [])

    ###################################################################################################################

    def dim_all_others(self):

        if len(self.selected_point_ids) == 0:
            return

        self.colormap[:, 3] = 0.05
        selected_colors = np.unique(np.array(self.all_colors)[self.selected_points])
        
        for c in selected_colors:
            self.colormap[c, 3] = 1

        self.v.set(color_map = self.colormap)
        self.v.set(selected = [])

    ###################################################################################################################

    def gray_all_others(self):

        if len(self.selected_point_ids) == 0:
            return

        self.show_grayed()

        # Keep the original colors before graying out
        self.colormap_copy = np.copy(self.colormap)

        # set all to gray
        self.colormap = np.full(np.shape(self.colormap), 0.5)
        self.colormap[:, 3] = 0.1
        selected_colors = np.unique(np.array(self.all_colors)[self.selected_point_ids])
        
        for c in selected_colors:
            self.colormap[c, :] = self.colormap_copy[c, :]

        self.v.set(color_map = self.colormap)
        self.v.set(selected = [])

    ###################################################################################################################

    def show_grayed(self):
        self.colormap = np.copy(self.colormap_copy)
        self.v.set(color_map = self.colormap)

    ###################################################################################################################

    def randomize_colors(self):
        self.colormap = np.random.rand (self.num_colors, 4)
        self.colormap[:, 3] = 0.9 # transparency
        self.v.set(color_map = self.colormap)
        
    ###################################################################################################################
        
    def show_hidden(self, reload = True):

        current_lookat = self.v.get("lookat")
        
        self.colormap[:, 3] = 0.9 # in case something was dimmed
        self.v.set(color_map = self.colormap)

        if np.sum(self.hidden_points) == 0:
            return
        
        for i, p in enumerate(self.hidden_points):

            if p != [0, 0, 0]:

                self.all_points[i] = self.hidden_points[i]
                self.hidden_points[i] = [0, 0, 0]

        if reload:
            self.reload_view(current_lookat)

    ###################################################################################################################

    def load_selected_objects(self, selected_objects_file):
        """ Load the object IDs from the provided file. """

        if not os.path.exists(selected_objects_file):
            return []

        return list(np.loadtxt(selected_objects_file, ndmin = 1))

    ###################################################################################################################

    def hide_objects_from_file(self, selected_objects_file):

        current_lookat = self.v.get("lookat")
        selected_colors = self.load_selected_objects(selected_objects_file)

        self.show_hidden(reload = False)
        
        indices_to_hide = []
        for c in selected_colors:
            
            indices_to_hide += self.map_realseg_to_indices[c]

        for selected_p in indices_to_hide:

            if self.all_points[selected_p] != [0, 0, 0]:
                self.hidden_points[selected_p] = self.all_points[selected_p]
                self.all_points[selected_p] = [0, 0, 0]

        self.reload_view(current_lookat)
        self.v.set(selected = [])

    ###################################################################################################################

    def show_only_objects_from_file(self, selected_objects_file):

        current_lookat = self.v.get("lookat")
        
        selected_colors = self.load_selected_objects(selected_objects_file)
        all_colors = list(np.unique(np.array(self.real_colors)))
        if 0 in all_colors:
            all_colors.remove(0)
        selected_colors = [x for x in all_colors if x not in selected_colors]

        self.show_hidden(reload = False)
        
        indices_to_hide = []
        for c in selected_colors:
            indices_to_hide += self.map_realseg_to_indices[c]

        for selected_p in indices_to_hide:

            if self.all_points[selected_p] != [0, 0, 0]:
                self.hidden_points[selected_p] = self.all_points[selected_p]
                self.all_points[selected_p] = [0, 0, 0]

        self.reload_view(current_lookat)
        self.v.set(selected = [])

    ###################################################################################################################

    def add_raw_view(self, raw_v):
        self.raw_v = raw_v

    ###################################################################################################################

    def get_rotation(self):
        return self.v.get("phi")[0], self.v.get("theta")[0]

    ###################################################################################################################

    def add_objects_to_file(self, selected_objects_file):
        
        if not os.path.exists(selected_objects_file):
            f = open(selected_objects_file, "w+")
            f.close()

        if len(self.selected_point_ids) == 0:
            return

        # selected_point_ids contain the indices of oversegmented objects
        # find the indices of the truly segmented objects

        selected_colors = list(np.unique(np.array(self.real_colors)[self.selected_points]))

        with open(selected_objects_file, "a") as f:
            for obj in selected_colors:
                f.write(str(obj) + "\n")
        
        self.hide_objects_from_file(selected_objects_file)
        self.v.set(selected = [])

    ###################################################################################################################

    def remove_objects_from_file(self, selected_objects_file):
        
        if not os.path.exists(selected_objects_file):
            return

        if len(self.selected_point_ids) == 0:
            return

        # selected_point_ids contain the indices of oversegmented objects
        # find the indices of the truly segmented objects

        selected_colors = list(np.unique(np.array(self.real_colors)[self.selected_points]))
        objects_in_file = list(np.loadtxt(selected_objects_file))

        
        for obj in selected_colors:
            if obj in objects_in_file:
                objects_in_file.remove(obj)
                
        np.savetxt(selected_objects_file, objects_in_file)

        self.show_only_objects_from_file(selected_objects_file)
        self.v.set(selected = [])

    ###################################################################################################################

    def highlight_selected(self, selected_colors):

        if len(selected_colors) == 0:
            return
        
        # convert to integers colors
        selected_colors = [int(x) for x in selected_colors]

        # Keep the original colors before graying out
        self.colormap_copy = np.copy(self.colormap)

        # set all to gray
        self.colormap = np.full(np.shape(self.colormap), 0.5)
        self.colormap[:, 3] = 0.02
        
        for c in selected_colors:
            if c in self.real_to_remapped.keys():
                real_c = self.real_to_remapped[c]
                self.colormap[real_c, :] = self.colormap_copy[real_c, :]

        self.v.set(color_map = self.colormap)
        self.v.set(selected = [])

    ###################################################################################################################

    def invert_good_and_bad(self, selected_objects_file):
        selected = np.loadtxt(selected_objects_file)
        all_objects = list(np.unique(self.real_colors))
        remaining = np.array([x for x in all_objects if x not in selected])
        np.savetxt(selected_objects_file, remaining)

    ###################################################################################################################

    def measure_arm(self):
        
        if self.measure_mode != 1:
            return

        selected = self.v.get("selected")

        if len(selected) == 0:
            return

        # print the real ID of the selected objects
        real_ids = np.array(self.real_colors)[selected[0]]
        print (real_ids)        
        print (len(selected))
      
    ###################################################################################################################

    def create_new_chunk(self):

        # Find the selected points
        selected = self.v.get("selected")

        print (selected)
        if len(selected) < 1:
            return

        max_chunk_id = np.max(list(self.map_overseg_to_indices[self.t - self.start_t].keys()))
        self.map_overseg_to_indices[self.t - self.start_t][max_chunk_id + 1] = selected
        
        for s in selected:
            self.overseg_colors[s] = max_chunk_id + 1

    ###################################################################################################################

    def high_res_image(self):
        
        # upsample the current image
        current_img = imread(self.image_filenames[self.t - self.start_t])
        current_img = zoom(current_img, (6, 6, 6), order = 0)

        # make hollow to save space
        eroded_img = erosion(current_img)
        current_img[eroded_img > 0] = 0

        # load into pptk
        points = np.array(np.where(current_img)).T

        all_points = []
        colors = []
        for p in points:
            z, y, x = p
            colors.append(current_img[z, y, x])
            all_points.append([z * self.z_aspect_ratio, y, x + (self.t - self.start_t) * self.next_t_in_space])

        unique_labels = list(np.unique(self.real_colors))

        remapped = [self.real_to_remapped[c] for c in colors]
            
        self.temp_viewer = pptk.viewer(all_points, remapped, debug = True)
        self.temp_viewer.set(point_size = 0.5)

        current_lookat = self.v.get("lookat")
        z, y, x = current_lookat
        x -= (self.t - self.start_t) * self.next_t_in_space
        self.temp_viewer.set(lookat = [6 * z, 6 * y, 6 * x + (self.t - self.start_t) * self.next_t_in_space])
        self.temp_viewer.set(r = 6 * self.v.get("r"))

        self.temp_viewer.set(color_map = self.colormap)
        
        
        self.temp_viewer.set(theta = self.v.get("theta"))
        self.temp_viewer.set(phi = self.v.get("phi"))
        self.temp_viewer.set(bg_color = [0, 0, 0, 1])
        self.temp_viewer.set(floor_color = [0, 0, 0, 0])
        self.temp_viewer.set(show_grid = False)
        self.temp_viewer.set(show_info = False)
        self.temp_viewer.set(show_axis = False)
                
        self.temp_viewer.capture("snap.png")
        

    ###################################################################################################################

    def update_selection_from_mouse(self):


        if self.source_idx == None:
            return self.update_selection_from_mouse_standard()

        # Get all selected points by PPTK
        selected_pptk = self.v.get("selected")

        # If none, our job here is done
        if len(selected_pptk) == 0:
            return

        if self.t not in self.changed_frames:
            self.changed_frames.append(self.t)

        # Find the object whose color is selected as source_color and get all indices
        object_indices = self.map_realseg_to_indices[self.source_color]

        # Get the intersection with the pptk selection
        new_selected = np.intersect1d(selected_pptk, object_indices)

        # Remove out of time indices
        if self.t + self.interval in self.start_indices_at_specific_times.keys():
            future_point_indices = list(range(self.start_indices_at_specific_times[self.t + self.interval], len(self.all_points)))
            new_selected = list(set(new_selected) - set(future_point_indices))

        if self.t in self.start_indices_at_specific_times.keys():
            past_point_indices = list(range(0, max(0, self.start_indices_at_specific_times[self.t])))
            new_selected = list(set(new_selected) - set(past_point_indices))
        
        # Update the PPTK selection
        self.v.set(selected = new_selected)

        #self.unselect_out_of_time_points()
        
    ###################################################################################################################    
        
        
    def update_selection_from_mouse_standard(self):

        if self.create_chunk:
            return

        #global self.selected_points, self.selected_point_ids
        if len(self.v.get("selected")) == 0:
            self.selected_points = []
            self.selected_point_ids = []
            self.selected_times = []
            return True
        
        source = [x for x in list(self.v.get("selected")) if x not in self.selected_points]

        if len(source) == 0:
            return True

        if self.t not in self.changed_frames:
            self.changed_frames.append(self.t)

        self.selected_point_ids.append(source[0])
        self.selected_times.append(self.t)
        source_overseg_color = self.overseg_colors[source[0]]

        new_selected_indices = []
        for overseg_index in self.map_overseg_to_indices[self.t-self.start_t][source_overseg_color]:
            new_selected_indices.append(overseg_index)

        current_selected = list(self.v.get("selected"))  
        self.v.set(selected = current_selected + new_selected_indices)
        self.selected_points = self.v.get("selected")

        # print the real ID of the selected objects
        real_ids = np.unique(np.array(self.real_colors)[self.selected_point_ids])
        print (real_ids)

        
    
