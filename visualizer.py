"""
    Implements VTK functionality for visualizing and modifying segmentation labels in 3D.
    Author: Rumen Stamatov
    05/03/2024
"""
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from tifffile import imread, imwrite
import glob
import numpy as np
import tkinter as tk
import os
from scipy.spatial import cKDTree
import networkx as nx
from visualizer_gui import *
from custom_interaction import *
from line_fit_interaction import *
from random import choices, choice, uniform
import time
import re
from tkinter import messagebox

if vtk.vtkMultiThreader.GetGlobalDefaultNumberOfThreads() > 4:
    vtk.vtkMultiThreader.SetGlobalMaximumNumberOfThreads(4)

class Visualizer_3D:
    def __init__(self, folder, overseg_folder, raw_folder, start, end, interval, spacing_x = 1.0, spacing_y = 1.0, spacing_z = 1.0):
        """
        Initializes the 3D visualizer with image data and oversegmentation data from the provided folder paths.
        Configures spacing between voxels along each axis and prepares initial rendering setup.
        :param folder: Path to folder containing the original TIF images.
        :param overseg_folder: Path to folder containing over-segmentation files.
        :param spacing_x: Spacing between voxels in x-axis.
        :param spacing_y: Spacing between voxels in y-axis.
        :param spacing_z: Spacing between voxels in z-axis.
        """
        self.log("visualizer.py: init")
            
        self.t = 0
        self.oversegmentations = []
        self.raw = []
        self.selected_labels = []

        self.imageDataObjects = []
        self.modified = {}

        self.grayed_out = False
        self.backup = None

        # for undo
        self.undo_copy = None
        self.last_correction_t = 0
        self.undo_labels = []

        
        self.last_clicked_point = [0, 0, 0]
        self.selected_voxels = [] # for magic wand corrections

        # Use vtkCellPicker for picking on volumetric data
        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.00001)

        self.labels_per_image = {}

        self.marchingCubes = {}
        self.surfaceMappers = {}
        self.surfaceActors = {}
        self.highlightActors = []

        self.visible = {}
        for label in range(1, 256):
            self.visible[label] = True

        self.magic_wand = False
        self.destination_color = 0
        self.source_color = 0

        self.draw_line_mode = False

        # Create a list of file paths for the TIF images
        image_files = glob.glob(folder)  
        overseg_files = glob.glob(overseg_folder)
        raw_files = glob.glob(raw_folder)

        if len(overseg_files) == 0:
            overseg_files = image_files

        self.start_t = 0
        self.end_t = len(image_files)

        self.init_colors_and_opacity()
        self.init_rendering()
        self.init_image_data(image_files, overseg_files, raw_files, start, end, interval, spacing_x, spacing_y, spacing_z)
        self.add_raw_data()

        self.set_current_image(self.t)

        # Set the defined interaction style to the render window interactor
        self.magic_wand_style = CustomInteractorStyle(self)
        self.interactorStyle = self.magic_wand_style
        self.renderWindowInteractor.SetInteractorStyle(self.interactorStyle)

        self.LineFit = LineFitInteraction(self)
        
        self.renderWindowInteractor.AddObserver("LeftButtonPressEvent", self.onMouseClick)
        self.renderWindowInteractor.AddObserver("RightButtonPressEvent", self.onMouseClick)
        self.renderWindowInteractor.AddObserver("KeyPressEvent", self.onKeyPress)
        self.renderWindowInteractor.AddObserver("ExitEvent", self.OnClose)

        self.add_text_for_time()
        self.hidden_objects_file = "hidden_objects.txt"

        self.adjust_camera()
        self.renderWindowInteractor.Initialize()

        self.gui = VisualizerGui(self)
        self.gui.run_loop()

        self.renderWindowInteractor.Start()

    ########################################################################################################
        
    def log(self, message):
        if not os.path.exists("log.txt"):
            f = open("log.txt", "w+")
            f.close()
        with open("log.txt", "a") as f:
            f.write(message + "\n")
            
    ########################################################################################################

    def OnClose(self, window, event):

        self.log("visualizer.py: OnClose")
        if messagebox.askyesno("Confirm Exit", "Are you sure you want to close the application?"):
            self.renderWindow.Finalize()  # Properly release the VTK render window resources
            self.renderWindowInteractor.TerminateApp()
            quit()
        else:
            self.gui.window.destroy()
            self.renderWindowInteractor.Initialize()
            
            self.gui = VisualizerGui(self)
            self.gui.slider_value.set(self.t)
            self.gui.run_loop()

            self.renderWindowInteractor.Start()

    ########################################################################################################

    def add_raw_data(self):
        self.log("visualizer.py: add_raw_data")
        if len(self.raw) == 0:
            return

        # Create a volume mapper
        self.rawVolumeMapper = vtk.vtkFixedPointVolumeRayCastMapper()
        
        # Create a color transfer function
        colorTransferFunction = vtk.vtkColorTransferFunction()
        colorTransferFunction.AddRGBPoint(0, 0.0, 0.0, 0.0)
        colorTransferFunction.AddRGBPoint(80, 0.0, 0.0, 0.0)
        colorTransferFunction.AddRGBPoint(255, 1.0, 1.0, 1.0) # Assuming the scalar range is 0-255

        # Create opacity transfer function
        opacityTransferFunction = vtk.vtkPiecewiseFunction()
        opacityTransferFunction.AddPoint(0, 0.0)  # Assume 0 is fully transparent
        opacityTransferFunction.AddPoint(80, 0.0)  # Assume 30 is fully transparent
        opacityTransferFunction.AddPoint(255, 1.0)  # And values towards 255 are fully opaque

        # Create volume property
        volumeProperty = vtk.vtkVolumeProperty()
        volumeProperty.SetColor(colorTransferFunction)
        volumeProperty.SetScalarOpacity(opacityTransferFunction)
        volumeProperty.ShadeOff()  # Turn off shading to see the raw images better
        volumeProperty.SetInterpolationTypeToLinear()

        # Create volume
        self.rawVolume = vtk.vtkVolume()
        self.rawVolume.SetMapper(self.rawVolumeMapper)
        self.rawVolume.SetProperty(volumeProperty)

        # Add the volume to the renderer
        self.renderer.AddViewProp(self.rawVolume)           
        

    ########################################################################################################

    def adjust_camera(self):
        self.log("visualizer.py: adjust_camera")
        # This function will automatically adjust the camera based on the bounds of the objects in the scene
        self.renderer.ResetCamera()

        # adjust the camera to ensure all objects are within view
        camera = self.renderer.GetActiveCamera()
        camera.Dolly(0.5) # zoom out a little
        self.renderer.ResetCameraClippingRange()

    ########################################################################################################

    def init_destination_and_source_color(self):
        self.log("visualizer.py: init_destination_and_source_color")

        width, height = self.renderWindowInteractor.GetRenderWindow().GetSize()
        
        self.destinationActor = vtk.vtkTextActor()
        self.destinationActor.SetInput("")
        self.destinationActor.GetTextProperty().SetFontSize(24)
        self.destinationActor.GetTextProperty().SetColor(1.0, 1.0, 1.0)  # Set text color to white
        
        self.destinationActor.SetPosition(150, 20)

        self.sourceActor = vtk.vtkTextActor()
        self.sourceActor.SetInput("")
        self.sourceActor.GetTextProperty().SetFontSize(24)
        self.sourceActor.GetTextProperty().SetColor(1.0, 1.0, 1.0)  # Set text color to white
        self.sourceActor.SetPosition(350, 20)

        self.magicWandActor = vtk.vtkTextActor()
        self.magicWandActor.SetInput("")
        self.magicWandActor.GetTextProperty().SetFontSize(24)
        self.magicWandActor.GetTextProperty().SetColor(1.0, 0.0, 0.0)  
        self.magicWandActor.SetPosition(20, 50)

        self.selectedLabelsActor = vtk.vtkTextActor()
        self.selectedLabelsActor.SetInput("")
        self.selectedLabelsActor.GetTextProperty().SetFontSize(24)
        self.selectedLabelsActor.GetTextProperty().SetColor(1.0, 0.0, 0.0)  
        self.selectedLabelsActor.SetPosition(20, 80)

        # Add the text actors to the renderer
        self.renderer.AddActor(self.destinationActor)
        self.renderer.AddActor(self.sourceActor)
        self.renderer.AddActor(self.magicWandActor)
        self.renderer.AddActor(self.selectedLabelsActor)

        self.renderer.Render()

    ########################################################################################################

    def longest_digit_substring(self, s):
        self.log("visualizer.py: longest_digit_substring")
        # Find all substrings of s that consist only of digits
        digit_substrings = re.findall('\d+', s)
        
        # Find the longest substring from digit_substrings
        longest = max(digit_substrings, key=len, default='')
        
        return longest

    ########################################################################################################

    def init_image_data(self, image_files, overseg_files, raw_files, start, end, interval, spacing_x, spacing_y, spacing_z):
        """
        Initializes image data from file names, setting up the spacing and transposing the image data for 
        visualization purposes. Loads over-segmentation files and prepares them for interaction.
        :param image_files: List of TIF image file paths.
        :param overseg_files: List of over-segmentation file paths.
        :param spacing_x: Spacing between voxels in x-axis.
        :param spacing_y: Spacing between voxels in y-axis.
        :param spacing_z: Spacing between voxels in z-axis.
        """
        self.log("visualizer.py: linit_image_data")
        
        # Variables representing the spacing between voxels along each axis
        self.spacing_x = spacing_x
        self.spacing_y = spacing_y
        self.spacing_z = spacing_z

        self.filenames = []
        image_files.sort()
        overseg_files.sort()


        loaded = 0
        # Load each image and add to imageDataObjects list
        for t, image_file in enumerate(image_files):

            if t % interval != 0:
                continue
            print(image_file)

            last_forward = image_file.rfind('/')
            last_backward = image_file.rfind('\\')  # Note the escape character for backslash
            last_slash_index = max(last_forward, last_backward)
            substring_img = image_file[last_slash_index:]

            #number = int(self.longest_digit_substring(substring))
            
            if (t < start and start >= 0) or (t > end and end > 0):
                continue

            if (start < 0 and t < len(image_files)+start) or (end <= 0 and t > len(image_files)+end):
                continue
            
            self.filenames.append(image_file)
            real_img = imread(image_file)

            current_labels = list(np.unique(real_img))
            current_labels.remove(0)

            # Make sure no labels >= 255
            for label in current_labels:
                if label >= 255:
                    new_label = self.find_available_label()
                    real_img[real_img == label] = new_label
                    
            current_labels = list(np.unique(real_img))
            current_labels.remove(0) 

                
            self.labels_per_image[loaded] = current_labels

            scalars_transposed = real_img.transpose(2, 1, 0)
            scalars_fortran_order = np.asfortranarray(scalars_transposed)
            vtk_scalars = numpy_to_vtk(num_array = scalars_fortran_order.ravel(), deep = True, array_type=vtk.VTK_FLOAT)

            self.imageData = vtk.vtkImageData()
            self.imageData.SetDimensions(real_img.shape)
            self.imageData.GetPointData().SetScalars(vtk_scalars)
            self.imageData.SetSpacing(self.spacing_z, self.spacing_y, self.spacing_x)  # Customize spacing if needed

            self.imageDataObjects.append(self.imageData)

            # Ensure the names of the overseg files match the segmentationn files

            matching_overseg = None
            for item in overseg_files:
            
                if substring_img in item:
                    matching_overseg = item
                    break
            
            
            if matching_overseg is not None:

                overseg = imread(matching_overseg)
            else:
                overseg = np.copy(real_img)
                
            overseg = self.split_overseg_labels_spanning_several_real(real_img, overseg)
            self.oversegmentations.append(overseg)

            self.init_surfaces(current_labels, loaded)
            self.init_surface_mappers()

            if len(raw_files) > 0:
                raw_img = imread(raw_files[loaded])
                scalars_transposed = raw_img.transpose(2, 1, 0)
                scalars_fortran_order = np.asfortranarray(scalars_transposed)
                vtk_scalars = numpy_to_vtk(num_array = scalars_fortran_order.ravel(), deep = True, array_type=vtk.VTK_FLOAT)

                self.imageData = vtk.vtkImageData()
                self.imageData.SetDimensions(raw_img.shape)
                self.imageData.GetPointData().SetScalars(vtk_scalars)
                self.imageData.SetSpacing(self.spacing_z, self.spacing_y, self.spacing_x)  # Customize spacing if needed

                self.raw.append(self.imageData)

            loaded += 1

        self.end_t = loaded

        """
        if len(self.imageDataObjects) > 0:
            self.volumeMapper.SetInputData(self.imageDataObjects[0])  # Set initial input data to ensure there's content to render at the start
        else:
            print("Error: No image data objects loaded. Check image loading process.")
            
        """
    ########################################################################################################

    def init_colors_and_opacity(self):
        """
        Initializes the color and opacity transfer functions for the volume visualization. This sets up how the scalar
        values in the data are mapped to colors and opacities in the rendered volume.
        """
        self.log("visualizer.py: init_colors_and_opacity")
        
        # Assuming the scalar range is from 0 to 255, adjust if it's different
        max_label = 255

        # Create a color transfer function
        self.colorTransferFunction = vtk.vtkColorTransferFunction()
        self.opacityTransferFunction = vtk.vtkPiecewiseFunction()

        # Set minimum scalar to black
        self.colorTransferFunction.AddRGBPoint(0, 0.0, 0.0, 0.0)

        self.opacityTransferFunction.AddPoint(0, 0.0)  # Fully transparent at the minimum scalar

        for obj in range(1, max_label):
            color = list(np.random.choice(np.arange(0, 1, 0.1), size = 3))
            self.colorTransferFunction.AddRGBPoint(obj, color[0], color[1], color[2])
            self.opacityTransferFunction.AddPoint(obj, 1.0)
        self.colorTransferFunction.AddRGBPoint(max_label, 1.0, 1.0, 0.0)  # Yellow for value 255
        self.opacityTransferFunction.AddPoint(max_label, 1.0)  # Fully opaque for value 255

        # Save the original opacity function to revert back to after graying out certain objects
        self.opacityTransferFunctionCopy = self.copy_opacity(self.opacityTransferFunction)

    ########################################################################################################

    def add_text_for_time(self):

        self.log("visualizer.py: add_text_for_time")
        
        # Create a vtkTextActor to display the time
        self.textActor = vtk.vtkTextActor()
        self.textActor.SetInput("Time: " + str(self.t) + "/" + str(len(self.imageDataObjects) - 1))
        self.textActor.GetTextProperty().SetFontSize(24)
        self.textActor.GetTextProperty().SetColor(0.0, 0.0, 0.0)  # Set text color to white
        self.textActor.SetPosition(20, 20)  # Specify the position of the text on the screen

        # Add the text actor to the renderer
        self.renderer.AddActor(self.textActor)

    ########################################################################################################

    def init_rendering(self):
        """
        Initializes the rendering window, renderer, render window interactor, and sets up the interaction style.
        Adds mouse and key press event observers for interactive visualization.
        """

        self.log("visualizer.py: init_rendering")
        
        self.renderWindow = vtk.vtkRenderWindow()
        self.renderer = vtk.vtkRenderer()

        self.renderer.SetBackground(1.0, 1.0, 1.0)
        
        self.renderWindow.AddRenderer(self.renderer)

        self.renderWindowInteractor = vtk.vtkRenderWindowInteractor()
        self.renderWindowInteractor.SetRenderWindow(self.renderWindow)

        self.renderWindowInteractor.Initialize()

        self.renderWindow.AddRenderer(self.renderer)

        self.init_destination_and_source_color()

        # Enable depth peeling in the renderer
        self.renderer.SetUseDepthPeeling(1)
        

    ########################################################################################################

    def copy_opacity(self, original_function):

        self.log("visualizer.py: copy_opacity")
        
        # Create a new instance of the PiecewiseFunction
        new_function = vtk.vtkPiecewiseFunction()
       
        # Get the number of points in the original function
        num_points = original_function.GetSize()
       
        # Temporary array to hold point data
        data = [0.0] * 4 # Initialize with size 4 to hold x, y, midpoint, sharpness values
       
        # Iterate over each point and add it to the new function
        for i in range(num_points):
            # Retrieve the data for the i-th point
            original_function.GetNodeValue(i, data)
           
            # Extract the relevant data
            x, y, midpoint, sharpness = data
           
            # Add the point to the new function with the same midpoint and sharpness
            new_function.AddPoint(x, y, midpoint, sharpness)
       
        return new_function

    ########################################################################################################

    def create_highlight_actors(self, label):

        self.log("visualizer.py: create_highlight_actors")

        # Getting the overlay mask based on the oversegmentation label
        overlay_mask = np.copy(self.oversegmentations[self.t])
        overlay_mask[overlay_mask != label] = 0

        # Converting numpy array (1D) to VTK array
        scalars_transposed = overlay_mask.transpose(2, 1, 0)
        scalars_fortran_order = np.asfortranarray(scalars_transposed)
        vtk_scalars = numpy_to_vtk(num_array=scalars_fortran_order.ravel(), deep = True, array_type=vtk.VTK_FLOAT)

        mask_image = vtk.vtkImageData()
        mask_image.SetDimensions(overlay_mask.shape)
        mask_image.GetPointData().SetScalars(vtk_scalars)
        mask_image.SetSpacing(self.spacing_z, self.spacing_y, self.spacing_x)

        # Step 3: Apply marching cubes to this mask to create geometry
        marchingCubes = vtk.vtkMarchingCubes()
        marchingCubes.SetInputData(mask_image)
        marchingCubes.SetValue(0, 0.5)  # surface at mid-value
        marchingCubes.Update()
        

        # Step 4: Create mapper and actor for this geometry
        mapper = vtk.vtkPolyDataMapper()
        mapper.ScalarVisibilityOff()
        mapper.SetInputConnection(marchingCubes.GetOutputPort())


        actor = vtk.vtkActor()
                
        actor.GetProperty().SetColor(1, 1, 0)  # Highlight color 
        actor.GetProperty().SetOpacity(1)
        actor.GetProperty().SetRepresentationToSurface()
        actor.SetMapper(mapper)
        actor.GetProperty().SetInterpolationToPhong()

        actor.GetProperty().SetAmbient(1)  # Increase the ambient light component
        actor.GetProperty().SetDiffuse(0.2)
        actor.GetProperty().SetSpecular(0.0)  # Increase the specular highlight (shininess)
        actor.GetProperty().SetSpecularPower(20)

        # Step 5: Add actor to renderer and keep track for easy removal
        self.renderer.AddActor(actor)
        self.highlightActors.append(actor)

    ########################################################################################################

    def remove_highlight_actors(self):
        self.log("visualizer.py: remove_highlight_actors")
        for actor in self.highlightActors:
            self.renderer.RemoveActor(actor)
        self.highlightActors.clear()

    ########################################################################################################

    # Mouse event callback function
    def onMouseClick(self, obj, event):
        """
        Callback function for mouse click events. Enables interaction with the volume via left and right mouse clicks,
        such as selecting regions and applying modifications. Centers the scene on a point upon double left click,
        unless the background is clicked.
        :param obj: The render window interactor instance.
        :param event: The event that triggered the callback.
        """
        # Handle mouse click events for interactive selection and editing
        """
        if self.gui is None:
            self.gui = VisualizerGui(self)
            self.gui.run_loop()
        """
        self.log("visualizer.py: OnMouseClick")

        worldPos = None
        
        ctrl_pressed = obj.GetControlKey()
        clickPos = obj.GetEventPosition()
        
        # Perform the pick operation. If nothing is picked, picker.Pick returns 0
        if self.picker.Pick(clickPos[0], clickPos[1], 0, self.renderer):
            # Get the picked position in world coordinates
            worldPos = self.picker.GetPickPosition()
            
            # Determine whether it's a double-click event
            if obj.GetRepeatCount():
                # If it's a double click and an object is picked, center on the picked point
                self.center_on_point(worldPos)
                return

        if obj.GetRepeatCount():
            return  # Do nothing if it's a double-click but on the background
        
        # Check which button was pressed for regular mouse interactions
        if ctrl_pressed and event == "LeftButtonPressEvent" and self.draw_line_mode == False:
            
            imageCoordinates = [0, 0, 0]

            if worldPos is not None:
                self.imageData.TransformPhysicalPointToContinuousIndex(worldPos, imageCoordinates)
                self.find_clicked_object(imageCoordinates)
            
        elif ctrl_pressed and event == "RightButtonPressEvent":

            self.make_correction()
            
        elif event == "RightButtonPressEvent":
            self.clear_selection()

        self.renderer.GetRenderWindow().Render()

    #########################################################################################################

    def make_correction(self):

        self.log("visualizer.py: make_corrections")

        if self.backup is None:
            self.backup = vtk.vtkImageData()
            self.backup.DeepCopy(self.imageDataObjects[self.t])
            
        self.undo_copy = vtk.vtkImageData()
        self.undo_copy.DeepCopy(self.backup)
        self.last_correction_t = self.t
        
        if self.magic_wand:
            self.correction_magic_wand()
        elif self.draw_line_mode:
            self.LineFit.indicate_centromere()
        else:
            self.correction()

        # After having done a correction, ensure the oversegmentation chunks don't span several real labels
        real_img = self.get_numpy_array(self.t)
        self.oversegmentations[self.t] = self.split_overseg_labels_spanning_several_real(real_img, self.oversegmentations[self.t])

        
        
    #########################################################################################################

    def undo(self):

        self.log("visualizer.py: undo")

        if self.t != self.last_correction_t or self.undo_copy is None:
            return
            
        self.imageDataObjects[self.t].DeepCopy(self.undo_copy)
        self.imageDataObjects[self.t].Modified()
        self.init_surfaces(self.undo_labels, self.t)
        self.set_current_image(self.t)
        #self.init_surface_mappers()
        self.renderer.GetRenderWindow().Render()

        self.undo_copy = None

    def update_time(self, direction):
        if direction == "forward" and self.t >= len(self.imageDataObjects) - 1:
            return
        if direction == "backward" and self.t <= 0:
            return
        
        self.clear_selection()
        self.selected_labels = []

        if direction == "forward":
            self.t += 1
        else:
            self.t -= 1
        self.set_current_image(self.t)
        self.textActor.SetInput("Time: " + str(self.t) + "/" + str(len(self.imageDataObjects) - 1))


        if self.draw_line_mode:
            self.LineFit.hide_curves()
            self.LineFit.load_existing_models()

        if self.gui is not None:
            self.gui.slider_value.set(self.t)

    #########################################################################################################
               
    def onKeyPress(self, obj, event):
        """
        Callback function for key press events. Allows navigation through the volume with the left and right arrow keys,
        and application of changes with other keys.
        :param obj: The render window interactor instance.
        :param event: The event that triggered the callback.
        """

        self.log("visualizer.py: OnKeyPress")
        
        # Handle key press events for navigation and modification

        key = obj.GetKeySym()  # Get the key symbol for the key that was pressed
        ctrl_pressed = obj.GetControlKey()
        
        if key == 'Left':
            self.update_time("backward")
            
        elif key == 'Right':
            self.update_time("forward")

        #elif key == 'Down':
            #self.save_current_view_as_jpeg("snap.jpeg")
            #self.save_movie()
        #    self.split_overseg_label()

        elif key == 'Up':
            if self.gui is None:
                self.gui = VisualizerGui(self)
                self.gui.run_loop()

        elif ctrl_pressed and (key == "S" or key == "s"):
            self.save_image_data_objects()

        elif (ctrl_pressed == False) and (key == "S" or key == "s"):
            self.update_source_color()

        elif key == 'v' or key == 'V':
            self.switch_source_destination()

        elif ctrl_pressed and (key == "f" or key == "F"):
            
            self.open_input_popup()

        elif key == "H" or key == "h":
            self.show_unmarked()

        elif key == "a" or key == "A":
            self.show_all_labels()
            
        elif key == "m" or key == "M":
            self.mark_labels(self.selected_labels)
            self.show_unmarked()

        elif key == "n" or key == "N":
            self.unmark_labels(self.selected_labels)
            self.show_marked()

        elif key == "u" or key == "U":
            self.show_marked()

        elif key == "d" or key == "D":
            self.update_destination_color()

        elif key == "g" or key == "G":
            if self.grayed_out:
                self.show_grayed()
            else:
                self.gray_all_others()

        elif key == "b" or key == "B":
            self.toggle_background_color()

        elif key == "w" or key == "W":
            self.toggle_shading()

        elif key == "o" or key == "O":
            if ctrl_pressed:
                self.randomize_all_colors()
            else:
                self.open_color_popup()
                #self.randomize_color_of_selected()

        elif key == "l" or key == "L":
            if self.draw_line_mode:
                self.gui.change_mode("default")
            else:
                self.gui.change_mode("draw line")
            

        elif key == "i" or key == "I":
            self.clear_selection()
            
            if self.magic_wand:
                self.gui.change_mode("default")
            else:
                self.gui.change_mode("magic wand")

        elif ctrl_pressed and (key == "z" or key == "Z"):
            self.undo()

        self.textActor.SetInput("Time: " + str(self.t) + "/" + str(len(self.imageDataObjects) - 1))
        self.renderer.GetRenderWindow().Render()

    ##############################################################################################################

    def enter_spline_mode(self):

        """
        if self.destination_color == 0:
            print ("Please set a destination color first.")
            return
        """

        self.log("visualizer.py: enter_spline_mode")
        
        self.interactorStyle.clear_selection()
        self.draw_line_mode = True

        self.selected_labels = [self.destination_color]
        self.gray_all_others()
            
        self.interactorStyle = self.LineFit
        self.LineFit.load_existing_models()
        
        for label in range(1, 256):
            self.surfaceActors[label].GetProperty().SetRepresentationToWireframe()
                    
        self.renderWindowInteractor.SetInteractorStyle(self.interactorStyle)

        self.renderer.GetRenderWindow().Render()

    #############################################################################################################

    def enter_default_mode(self):

        self.log("visualizer.py: enter_default_mode")

        self.interactorStyle.clear_selection()
        self.show_grayed()

        if self.magic_wand == True:
            self.remove_highlight_actors()
            self.magic_wand = False
            self.set_default_cursor()
            self.magicWandActor.SetInput("")
            self.renderer.GetRenderWindow().Render()

        if self.draw_line_mode == True:
            
            self.draw_line_mode = False
            #self.interactorStyle = CustomInteractorStyle(self)
            #self.renderWindowInteractor.SetInteractorStyle(self.interactorStyle)

            for label in range(1, 256):
                self.surfaceActors[label].GetProperty().SetRepresentationToSurface()

        self.renderer.GetRenderWindow().Render()

    #############################################################################################################

    def enter_magic_wand_mode(self):

        self.log("visualizer.py: enter_magic_wand_mode")
        self.interactorStyle.clear_selection()
            
        self.draw_line_mode = False
        self.interactorStyle = self.magic_wand_style
        self.renderWindowInteractor.SetInteractorStyle(self.interactorStyle)

        for label in range(1, 256):
            self.surfaceActors[label].GetProperty().SetRepresentationToSurface()

        self.magic_wand = True
        self.set_magic_wand_cursor()
        self.magicWandActor.SetInput("magic wand ON")
        self.show_grayed()
        self.renderer.GetRenderWindow().Render()

    #############################################################################################################

    def update_destination_color(self):

        self.log("visualizer.py: update_destination_color")

        if len(self.selected_labels) == 0:
            self.destination_color = 0
            self.destinationActor.GetTextProperty().SetColor(1.0, 1.0, 1.0)
            self.destinationActor.SetInput("")
            self.gui.draw_line_btn.config(relief = "raised", state = "disabled")
            return

        self.destination_color = self.selected_labels[-1]
        newColor = self.colorTransferFunction.GetColor(self.destination_color)
        self.destinationActor.GetTextProperty().SetColor(newColor)
        self.destinationActor.SetInput("destination set")

        self.gui.draw_line_btn.config(relief = "raised", state = "normal")

        self.renderer.GetRenderWindow().Render()

    #############################################################################################################

    def update_source_color(self):

        self.log("visualizer.py: update_source_color")

        if len(self.selected_labels) == 0:
            self.source_color = 0
            self.sourceActor.GetTextProperty().SetColor(1.0, 1.0, 1.0)
            self.sourceActor.SetInput("")
            return

        self.source_color = self.selected_labels[-1]
        newColor = self.colorTransferFunction.GetColor(self.source_color)
        self.sourceActor.GetTextProperty().SetColor(newColor)
        self.sourceActor.SetInput("source set")

        self.renderer.GetRenderWindow().Render()

    #############################################################################################################

    def switch_source_destination(self):

        self.log("visualizer.py: switch_source_destination")
        
        if self.source_color == 0 or self.destination_color == 0:
            return
        
        self.source_color , self.destination_color = self.destination_color , self.source_color

        newDestinationColor = self.colorTransferFunction.GetColor(self.destination_color)
        self.destinationActor.GetTextProperty().SetColor(newDestinationColor)
        self.destinationActor.SetInput("destination set")

        newSourceColor = self.colorTransferFunction.GetColor(self.source_color)
        self.sourceActor.GetTextProperty().SetColor(newSourceColor)
        self.sourceActor.SetInput("source set")

        self.renderer.GetRenderWindow().Render()
        
    #############################################################################################################

    def gray_all_others(self):

        self.log("visualizer.py: gray_all_others")

        selected = self.selected_labels
        self.clear_selection()
        
        self.grayed_out = True
        
        for obj in range(1, 255):
            if obj not in selected:
                self.surfaceActors[obj].GetProperty().SetOpacity(0.03)
                
        self.selected_labels = []

        self.renderer.GetRenderWindow().Render()

    #############################################################################################################

    def shades_of_gray(self):

        self.log("visualizer.py: shades_of_gray")
        
        for label in range(1, 255):            
            color = 3 * list(np.random.choice(np.arange(0, 1, 0.1), size = 1))
            self.colorTransferFunction.AddRGBPoint(label, color[0], color[1], color[2])
            self.surfaceActors[label].GetProperty().SetColor(color)
                
        self.selected_labels = []

        self.renderer.GetRenderWindow().Render()
        

    #############################################################################################################

    def randomize_color_of_selected(self):

        self.log("visualizer.py: randomize_color_of_selected")

        selected = self.selected_labels
        self.clear_selection()

        for label in selected:            
            color = list(np.random.choice(np.arange(0, 1, 0.1), size = 3))
            self.colorTransferFunction.AddRGBPoint(label, color[0], color[1], color[2])
            self.surfaceActors[label].GetProperty().SetColor(color)
                
        self.selected_labels = []

        self.renderer.GetRenderWindow().Render()

    #############################################################################################################

    def randomize_all_colors(self):

        self.log("visualizer.py: randomize_all_colors")

        self.clear_selection()

        for label in range(1, 255):            
            color = list(np.random.choice(np.arange(0, 1, 0.1), size = 3))
            self.colorTransferFunction.AddRGBPoint(label, color[0], color[1], color[2])
            self.surfaceActors[label].GetProperty().SetColor(color)
                
        self.selected_labels = []

        self.renderer.GetRenderWindow().Render()

    #############################################################################################################

    def show_grayed(self):

        self.log("visualizer.py: show_grayed")
        self.clear_selection()
        self.grayed_out = False
        for obj in range(1, 255):
            self.surfaceActors[obj].GetProperty().SetOpacity(1.0)

        self.renderer.GetRenderWindow().Render()

    #############################################################################################################

    def toggle_background_color(self):

        self.log("visualizer.py: toggle_background_color")
        current_color = self.renderer.GetBackground()

        if current_color == (1, 1, 1):
            self.renderer.SetBackground(0, 0, 0)
            self.textActor.GetTextProperty().SetColor(1, 1, 1)
        elif current_color == (0, 0, 0):
            self.renderer.SetBackground(1, 1, 1)
            self.textActor.GetTextProperty().SetColor(0, 0, 0)

    #############################################################################################################

    def init_surfaces(self, unique_labels, t):

        self.log("visualizer.py: init_surfaces")

        if t not in self.marchingCubes.keys():
            self.marchingCubes[t] = {}

        thresholdFilter = vtk.vtkImageThreshold()
        thresholdFilter.SetInputData(self.imageDataObjects[t])
      
        for label in unique_labels:
            # Threshold the volume data to create a binary mask for the current label
            
            thresholdFilter.ThresholdBetween(label, label)
            thresholdFilter.SetInValue(1)
            thresholdFilter.SetOutValue(0)
            thresholdFilter.Update()

            # Apply Marching Cubes on the binary mask to generate vtkPolyData
            marchingCubes = vtk.vtkFlyingEdges3D() #vtk.vtkMarchingCubes()
            marchingCubes.SetInputData(thresholdFilter.GetOutput())
            marchingCubes.SetValue(0, 0.5)  # Generate surface for the thresholded value
            marchingCubes.Update()
            """
            # Now apply Quadric Decimation on the resulting vtkPolyData
            decimator = vtk.vtkQuadricDecimation()
            decimator.SetInputData(marchingCubes.GetOutput())
            decimator.SetTargetReduction(0.2)  # Target 20% reduction
            decimator.Update()
            """
            # Store the decimated output instead of the original marching cubes output
            self.marchingCubes[t][label] = marchingCubes.GetOutput()#decimator.GetOutput()

            #memory_usage_kb = decimator.GetOutput().GetActualMemorySize()
            #print(f"Memory usage: {memory_usage_kb} KB")
        

    #############################################################################################################

    def init_surface_mappers(self):

        self.log("visualizer.py: init_surface_mappers")

        for label in range(1, 256):
            self.surfaceMappers[label] = vtk.vtkPolyDataMapper()
            self.surfaceMappers[label].ScalarVisibilityOff()

            self.surfaceActors[label] = vtk.vtkActor()
            self.surfaceActors[label].GetProperty().SetRepresentationToSurface()
            
            # Retrieve and apply the color for this label
            color = self.colorTransferFunction.GetColor(label)
            self.surfaceActors[label].GetProperty().SetColor(color)  # Set the color
            self.surfaceActors[label].GetProperty().SetOpacity(1.0)
            self.surfaceActors[label].GetProperty().SetRepresentationToSurface()
            self.surfaceActors[label].SetMapper(self.surfaceMappers[label])
            self.surfaceActors[label].GetProperty().SetInterpolationToPhong()

            self.surfaceActors[label].GetProperty().SetAmbient(0.9)  # Increase the ambient light component
            self.surfaceActors[label].GetProperty().SetDiffuse(0.2)
            self.surfaceActors[label].GetProperty().SetSpecular(0.1)  # Increase the specular highlight (shininess)
            self.surfaceActors[label].GetProperty().SetSpecularPower(2)

            # Add the actor to the renderer
            self.renderer.AddActor(self.surfaceActors[label])

            #print ("Memory of mappers: ", sys.getsizeof(self.surfaceMappers[label]))
            #print ("Memory of actors: ", sys.getsizeof(self.surfaceActors[label]))
        
    #############################################################################################################

    def set_current_image(self, image_index):

        self.log("visualizer.py: set_current_image")

        # Method to set the current image index and update the display
        currentImageData = self.imageDataObjects[self.t]
        
        # Extract all unique scalar values (labels) in the volume, excluding the background (assumed to be 0)
        scalars = vtk_to_numpy(currentImageData.GetPointData().GetScalars())
        unique_labels = np.unique(scalars)
        unique_labels = unique_labels[unique_labels != 0]  # Exclude the background

        for label in range(1, 256):
            if label in unique_labels and label in self.marchingCubes[self.t].keys():

                self.surfaceMappers[label].SetInputData(self.marchingCubes[self.t][label])

                if self.visible[label]:
                    self.surfaceActors[label].VisibilityOn()
                    self.surfaceActors[label].SetPickable(1)
                    self.surfaceActors[label].Modified()
            else:
                self.surfaceActors[label].VisibilityOff()

        # Add the raw data if exists
        if len(self.raw) > self.t:
            self.rawVolumeMapper.SetInputData(self.raw[self.t])

        self.imageDataObjects[self.t].Modified()
        self.renderer.GetRenderWindow().Render()

    #############################################################################################################

    def find_clicked_object(self, point):
        """
        Finds the object label corresponding to a clicked point in the visualization.
        :param point: The (x, y, z) coordinates of the clicked point.
        :return: None
        """
        self.log("visualizer.py: find_clicked_object")
        
        self.last_clicked_point = point
        # Determine which object was clicked based on point coordinates
        
        if len(self.selected_labels) == 0:
            self.backup = vtk.vtkImageData()
            self.backup.DeepCopy(self.imageDataObjects[self.t])

        array = self.oversegmentations[self.t]

        z, y, x = map(int, point)
        found = 0
        closest_point_position = None

        # Check if the clicked point is non-zero. If so, return immediately
        if array[z, y, x] != 0 and array[z, y, x] not in self.modified:
            found = array[z, y, x]
            closest_point_position = [z, y, x]
        else:
            # Construct a list of positions and values for all non-zero points excluding the ones marked modified
            non_zero_positions = np.argwhere(array != 0)
            valid_indices = [i for i, pos in enumerate(non_zero_positions) if array[tuple(pos)] not in self.modified]
            valid_positions = non_zero_positions[valid_indices]
            
            # Proceed only if there are valid positions to search within
            if len(valid_positions) > 0:
                # Build a KDTree from non-zero positions
                tree = cKDTree(valid_positions)
                
                # Query the single closest point to the clicked position
                distance, index = tree.query([z, y, x])
                
                closest_point_position = valid_positions[index]
                found = array[tuple(closest_point_position)]
                #print(f"Closest non-zero pixel found at (Z, Y, X): {closest_point_position[0]}, {closest_point_position[1]}, {closest_point_position[2]}")
                #print(f"Pixel value: {found}")
            else:
                #print("No non-zero pixel found within search radius.")
                closest_point_position = None

        if self.magic_wand:
            return closest_point_position

        if found == 0:
            return
        
        # Identify and modify the selected object in the visualization as needed
        selected = np.transpose(np.where(array == found))

        vtk_array = self.imageDataObjects[self.t].GetPointData().GetScalars()

        # Only update if the chunk is currently visible
        clicked_on_visible_chunk = False
        
        for p in selected:
            i, j, k = p
            id = self.imageDataObjects[self.t].ComputePointId((i, j, k))
            real_id = vtk_array.GetTuple1(id)
            # Only update if the object was not previously modified
            if real_id > 0 and real_id != 255 and self.visible[real_id]:
                self.modified[found] = real_id
                vtk_array.SetTuple1(id, 255)
                clicked_on_visible_chunk = True

                if real_id not in self.selected_labels:
                    self.selected_labels.append(real_id)

        if not clicked_on_visible_chunk:
            return
        
        self.create_highlight_actors(found)

        self.imageDataObjects[self.t].Modified()

        self.selectedLabelsActor.SetInput("selected: " + ", ".join([str(int(x)) for x in self.selected_labels]))

        self.renderer.GetRenderWindow().Render()
        

    ####################################################################################################

    def open_input_popup(self):
        """
        Opens a Tkinter pop-up window for capturing user input. 
        Intended to be called when Ctrl+F is pressed.
        """

        self.log("visualizer.py: open_input_popup")

        if self.grayed_out:
            self.show_grayed()

        # Function to handle the input ID and highlight object
        def handle_input(event = None):
            user_input = input_var.get()
            try:
                self.show_all_labels()
                object_ids = user_input.split(",")
                self.selected_labels = [float(x) for x in list(object_ids)]
                
                self.gray_all_others()

            except ValueError:
                print("Invalid input. Please enter a numeric ID.")
            input_window.destroy()  # Close the window after input is handled

        # Initialize a new Tkinter window
        input_window = tk.Tk()
        input_window.title("Enter Object ID")

        # Text label
        tk.Label(input_window, text="Object ID:").pack()

        # Entry widget for capturing user input
        input_var = tk.StringVar(input_window)
        input_entry = tk.Entry(input_window, textvariable = input_var)
        
        input_entry.pack()

        # Bind the Return key (Enter key) to the handle_input function
        input_entry.bind("<Return>", handle_input)

        # Button to submit input
        submit_button = tk.Button(input_window, text="Submit", command=handle_input)
        submit_button.pack()

        input_window.mainloop()

    ####################################################################################################

    def save_image_data_objects(self):
        """
        Saves the current state of all image data objects to TIF files, allowing users to select a save directory.
        Now it extracts the original filenames and saves them in the new folder.
        """

        self.log("visualizer.py: save_image_data_objects")

        self.show_all_labels()
        self.clear_selection()
        
        # Initiate a Tkinter root window but keep it hidden
        root = tk.Tk()
        root.withdraw()

        # Open a dialog to choose the save directory
        folder_selected = tk.filedialog.askdirectory()

        # Check if a folder was selected
        if not folder_selected:
            print("No folder selected.")
            return

        # Iterate through imageDataObjects and save each as a TIF file
        for idx, imageData in enumerate(self.imageDataObjects):
            # Extract numpy array from vtkImageData
            array = vtk_to_numpy(imageData.GetPointData().GetScalars())
            time.sleep(0.3)
            dims = imageData.GetDimensions()
            array = array.reshape(dims, order='F')  # Reshape according to the dimensions of the vtkImageData

            # Extract the original filename from the full path
            original_filename = os.path.basename(self.filenames[idx])
            # Create the new file path
            file_path = os.path.join(folder_selected, original_filename)

            # Save the numpy array as a TIF file
            imwrite(file_path, array)

            print(f"Saved: {file_path}")

        print("All images have been saved.")

##################################################################################################################

    def correction_magic_wand(self):

        self.log("visualizer.py: correction_magic_wand")
        
        if not self.selected_voxels:
            print ("no selected voxels")
            return

        if self.draw_line_mode:
            return

        if self.destination_color > 0:
            destination = self.destination_color
        else:
            destination = self.selected_labels[-1]

        sources = self.selected_voxels

        self.clear_selection()
        
        vtk_array = self.imageDataObjects[self.t].GetPointData().GetScalars()

        modified_labels = [destination]
        for p in sources:
            real_id = vtk_array.GetTuple1(p)
            modified_labels.append(real_id)
            vtk_array.SetTuple1(p, destination)

        modified_labels = np.unique(modified_labels)
        self.undo_labels = modified_labels
            
        self.init_surfaces(modified_labels, self.t)
        self.set_current_image(self.t)

        self.selected_voxels = []

        self.renderer.GetRenderWindow().Render()

##################################################################################################################

    def merge(self):

        self.log("visualizer.py: merge")

        if self.draw_line_mode:
            return

        # Infer the source and destination colors

        if self.destination_color > 0 and self.source_color > 0:
            destination = self.destination_color
            sources = [self.source_color]
            
        elif self.destination_color > 0 and self.source_color == 0:
            destination = self.destination_color
            
            if len(self.selected_labels) > 1:
                sources = self.selected_labels
            else:
                return

        elif self.destination_color == 0 and self.source_color == 0:
            if len(self.selected_labels) > 1:
                destination = self.selected_labels[-1]
                sources = self.selected_labels[:-1]
            else:
                return

        elif self.destination_color == 0 and self.source_color > 0:
            if len(self.selected_labels) > 0:
                destination = self.selected_labels[-1]
                sources = [self.source_color] + self.selected_labels[:-1]
            else:
                return

        else:
            return
            
        self.recolor(sources, destination)

    ##########################################################################################################################
    def find_available_label(self):
        # Find the maximum label
        available_labels = list(range(1, 255))

        for t in self.labels_per_image.keys():
            for label in self.labels_per_image[t]:
                if label in available_labels:
                    available_labels.remove(label)

        if len (available_labels) > 0:
            return available_labels[0]
        else:
            return 0

    ##########################################################################################################################
    def make_new(self):

        self.log("visualizer.py: make_new")
        
        new_label = self.find_available_label()
        
        if new_label == 0:
            print ("Can't create a new label, too many")
            return
            
        print ("Created label " + str(new_label))

        for t in self.labels_per_image.keys():
            self.labels_per_image[t].append(new_label)

        # temporarily change the destination color to the new label and then revert it
        previous_destination = self.destination_color
        self.destination_color = new_label

        if self.magic_wand:
            self.correction_magic_wand()
        else:
            self.correction()

        self.destination_color = previous_destination

        # After having done a correction, ensure the oversegmentation chunks don't span several real labels
        real_img = self.get_numpy_array(self.t)
        self.oversegmentations[self.t] = self.split_overseg_labels_spanning_several_real(real_img, self.oversegmentations[self.t])

    ##########################################################################################################################

    def get_numpy_array(self, t):
        """ Covert the VTK array for time point t back to numpy representation """

        self.log("visualizer.py: get_numpy_array")

        image_data_object = self.imageDataObjects[t]
        # Extract the VTK array and convert it back to a NumPy array
        vtk_scalars = image_data_object.GetPointData().GetScalars()
        scalars_array = vtk_to_numpy(vtk_scalars)
        
        # Transform the array back into the shape it had before being raveled and ensure correct array order
        dims = image_data_object.GetDimensions()
        reshaped_array = scalars_array.reshape(dims[2], dims[1], dims[0]).transpose(2, 1, 0)
        reshaped_array = np.ascontiguousarray(reshaped_array)  # Ensure contiguous array for manipulation

        return reshaped_array

    ##########################################################################################################################        
        
    def recolor(self, sources, destination):
        """ Helper function for merge(). """

        self.log("visualizer.py: recolor")

        self.clear_selection()

        # Perform the merging operation

        for t in range(len(self.imageDataObjects)):

            reshaped_array = self.get_numpy_array(t)
            
            # Find indices where color needs to be changed (considering the reshaped array structure)
            for source in sources:
                reshaped_array[reshaped_array == source] = destination

            # Convert the reshaped array back to Fortran order and ravel it for VTK
            scalars_fortran_order = np.asfortranarray(reshaped_array.transpose(2, 1, 0))
            new_vtk_scalars = numpy_to_vtk(num_array=scalars_fortran_order.ravel(), deep = True, array_type=vtk.VTK_FLOAT)
            
            # Update the vtkImageData object
            self.imageDataObjects[t].GetPointData().SetScalars(new_vtk_scalars)

            self.init_surfaces(sources + [destination], t)
            
        self.set_current_image(self.t)
        self.renderer.GetRenderWindow().Render()

#######################################################################################################
        
    def correction(self):
        """
        Applies corrections to the currently modified objects at timepoint t, merging or separating labels as needed.
        """
        # Apply modifications to the selected region or object

        self.log("visualizer.py: correction")

        if self.draw_line_mode:
            return
        
        if not self.modified:
            return
        
        vtk_array = self.imageDataObjects[self.t].GetPointData().GetScalars()

        if self.destination_color > 0:
            destination = self.destination_color
            self.selected_labels.append(destination)

        else:
            # Clear the destination chunk
            overseg_index, destination = self.modified.popitem()
            selected = np.transpose(np.where(self.oversegmentations[self.t] == overseg_index))
            modified_labels = [destination]
         
            for p in selected:
                i, j, k = p
                id = self.imageDataObjects[self.t].ComputePointId((i, j, k))
                real_id = vtk_array.GetTuple1(id)
                modified_labels.append(real_id)
                vtk_array.SetTuple1(id, destination)

            modified_labels = np.unique(modified_labels)

        # Recolor the source chunks
        for overseg_index in self.modified.keys():
            selected = np.transpose(np.where(self.oversegmentations[self.t] == overseg_index))

            for p in selected:
                i, j, k = p
                id = self.imageDataObjects[self.t].ComputePointId((i, j, k))
                vtk_array.SetTuple1(id, destination)

        self.imageDataObjects[self.t].Modified()
        #self.volumeMapper.Modified()

        print ("Selected labels = ", self.selected_labels)
        self.undo_labels = self.selected_labels
        self.init_surfaces(self.selected_labels, self.t)
        self.set_current_image(self.t)

        self.modified = {}
        self.selected_labels = []
        self.backup = None
        self.clear_selection()
        self.renderer.GetRenderWindow().Render()

    #######################################################################################################

    def clear_selection(self):
        
        """
        Clears the current selection of modified objects, reverting them back to their original state.
        """
        # Clear current modifications and revert to original state

        self.log("visualizer.py: clear_selection")

        if self.backup is not None:
            self.imageDataObjects[self.t].DeepCopy(self.backup)
            self.imageDataObjects[self.t].Modified()
            #self.volumeMapper.Modified()
            self.backup = None

        if self.magic_wand:
            self.init_surfaces(self.selected_labels + [255], self.t)
        else:
            self.remove_highlight_actors()

        self.selected_labels = []
        self.modified = {}
        self.selected_voxels = []

        self.set_current_image(self.t)
        self.selectedLabelsActor.SetInput("")
        
        self.renderer.GetRenderWindow().Render()

    def set_magic_wand_cursor(self):
        self.log("visualizer.py: set_magic_wand_cursor")
        self.renderWindow.SetCurrentCursor(vtk.VTK_CURSOR_CROSSHAIR)

    #######################################################################################################

    def set_default_cursor(self):
        self.log("visualizer.py: set_default_cursor")
        self.renderWindow.SetCurrentCursor(vtk.VTK_CURSOR_ARROW)

    #######################################################################################################

    def get_labels_from_file(self):

        self.log("visualizer.py: get_labels_from_file")

        if not os.path.exists(self.hidden_objects_file):
            f = open(self.hidden_objects_file, "w+")
            f.close()

        labels_from_file = []
        with open(self.hidden_objects_file, "r") as f:
            for line in f:
                try:
                    labels_from_file.append(float(line[:-1]))
                except:
                    pass

        return labels_from_file

    ###################################################################################################

    def new_group(self):

        self.log("visualizer.py: new_group")
        
        # Initiate a Tkinter root window but keep it hidden
        root = tk.Tk()
        root.withdraw()

        # Open a dialog to choose the save directory
        file_selected = tk.filedialog.asksaveasfilename()

        # Check if a folder was selected
        if not file_selected:
            print("No filename selected.")
            return

        self.hidden_objects_file = file_selected

    ################################################################################################### 

    def mark_labels(self, labels_to_mark):

        self.log("visualizer.py: mark_labels")

        if 0 in labels_to_mark:
            labels_to_mark.remove(0)
            
        if not os.path.exists(self.hidden_objects_file):
            np.savetxt(self.hidden_objects_file, np.array(labels_to_mark))

        labels_from_file = self.get_labels_from_file()
            
        labels_from_file += labels_to_mark
        labels_from_file = list(np.unique(labels_from_file))
        
        np.savetxt(self.hidden_objects_file, np.array(labels_from_file))

    ###################################################################################################

    def unmark_labels(self, labels_to_unmark):

        self.log("visualizer.py: unmark_labels")
        
        if not os.path.exists(self.hidden_objects_file):
            return # nothing marked, so nothing to unmark

        labels_from_file = self.get_labels_from_file()
        labels_from_file = [x for x in labels_from_file if x not in labels_to_unmark]
            
        np.savetxt(self.hidden_objects_file, np.array(labels_from_file))
        
    ###################################################################################################

    def show_unmarked(self):
        """
        Hides specified labels in the visualization by setting their opacity to 0.
        :param labels_to_hide: List of labels to be hidden in the visualization.
        """
        # Hide selected labels from the volume rendering

        self.log("visualizer.py: show_unmarked")

        self.clear_selection()

        self.show_all_labels()

        marked = self.get_labels_from_file()

        for label in marked:
            if label in self.surfaceActors.keys() and label != 255:
                self.surfaceActors[label].SetVisibility(0)
                self.surfaceActors[label].SetPickable(0)
                self.visible[label] = False

        self.renderer.GetRenderWindow().Render()

        ###################################################################################################

    def show_marked(self):
        """
        Hides specified labels in the visualization by setting their opacity to 0.
        :param labels_to_hide: List of labels to be hidden in the visualization.
        """
        # Hide selected labels from the volume rendering
        self.log("visualizer.py: show_marked")

        self.clear_selection()

        self.show_all_labels()

        marked = self.get_labels_from_file()

        for label in self.surfaceActors.keys():
            if label not in marked and label != 255:
                self.surfaceActors[label].SetVisibility(0)
                self.surfaceActors[label].SetPickable(0)
                self.visible[label] = False

        self.renderer.GetRenderWindow().Render()

    ###################################################################################################
    
    def show_all_labels(self):
        """
        Restores all previously hidden labels to full opacity, making them visible again in the visualization.
        """
        self.log("visualizer.py: show_all_labels")
        
        # Show all labels that were previously hidden
        for label in self.surfaceActors.keys():
            self.surfaceActors[label].SetVisibility(1)
            self.surfaceActors[label].SetPickable(1)

        for label in range(1, 256):
            self.visible[label] = True

        self.set_current_image(self.t)

    ###################################################################################################

    def center_on_point(self, point):
        """
        Centers the scene on the provided 3D point in world coordinates.
        
        :param point: A tuple or list of (x, y, z) coordinates in world space to center on.
        """

        self.log("visualizer.py: center_on_point")
        
        if not hasattr(self, 'renderer') or not self.renderer:
            print("Renderer is not initialized.")
            return
        
        camera = self.renderer.GetActiveCamera()
        if not camera:
            print("Active camera not found.")
            return

        # Compute the offset to center the camera
        camera_pos = camera.GetPosition()
        focal_point = camera.GetFocalPoint()
        offset = [point[i] - focal_point[i] for i in range(len(point))]
        
        # Update camera position and focal point to center on the new location
        new_camera_pos = [camera_pos[i] + offset[i] for i in range(len(point))]
        new_focal_point = [focal_point[i] + offset[i] for i in range(len(point))]
        
        camera.SetPosition(new_camera_pos)
        camera.SetFocalPoint(new_focal_point)
        
        self.renderer.ResetCameraClippingRange()  # Readjust clipping range based on the current scene
        self.renderer.GetRenderWindow().Render()

    def toggle_shading(self):
        self.log("visualizer.py: toggle_shading")
        pass
        #self.init_surface_mappers()
        #self.volume.GetProperty().SetShade(not self.volume.GetProperty().GetShade())
        #self.display_all_surfaces_with_marching_cubes()

    ###################################################################################################

    def split_overseg_label(self):

        self.log("visualizer.py: split_overseg_label")

        N_random_points = 100

        img = self.oversegmentations[self.t]
        result = np.copy(img)
        
        # Find all labels
        all_labels = list(np.unique(img))
        all_labels.remove(0)
        max_label = np.max(all_labels)

        selected = list(self.modified.keys())
        self.clear_selection()

        for obj in selected:

            # find the set of points within this label
            z, y, x = np.where(img == obj);
            all_points = np.vstack([z, y, x]).T
            size = len(all_points)

            # Take a sample of points
            index = choices(list(range(len(x))), k = N_random_points)
            sample_points = np.vstack([z[index], y[index], x[index]]).T
            points_np = np.array(sample_points)

            # construct a graph
            graph = nx.Graph()

            for i, point in enumerate(points_np):
                graph.add_node(i)

            tree = cKDTree(points_np)
            for i, point in enumerate(points_np):
                for j in tree.query_ball_point(point, 4):
                    if i != j:  # avoid self-loops
                        distance = np.linalg.norm(points_np[i] - points_np[j])
                        graph.add_edge(i, j, weight = distance)
            

            # find the endpoints - choose a random point, find the most distant
            # and then the most distant from that one, in turn

            chosen = choices(list(graph.nodes), k = 1)[0]
            path_lengths = nx.single_source_dijkstra_path_length(graph, chosen, weight = 'weight')
            start, max_distance = max(path_lengths.items(), key = lambda x: x[1])
            path_lengths = nx.single_source_dijkstra_path_length(graph, start, weight = 'weight')
            end, max_distance = max(path_lengths.items(), key = lambda x: x[1])

            start = np.array(sample_points[start])
            end = np.array(sample_points[end])

            # Color each pixel according to the start or end node it's closer to
            max_label += 1
            new_color = max_label
            for p in all_points:
                z, y, x = p
                if np.linalg.norm(p - start) < np.linalg.norm(p - end):
                    result[z, y, x] = obj
                else:
                    result[z, y, x] = new_color

        self.oversegmentations[self.t] = result
        self.clear_selection()

        self.find_clicked_object(self.last_clicked_point)

    ###################################################################################################################

    def split_overseg_labels_spanning_several_real(self, img, overseg, label = None):
        

        self.log("visualizer.py: split_overseg_labels_spanning_several_real")
        unique_labels = np.unique(overseg)
        # Ensure we don't process the background (0 label)
        mask = overseg != 0
        max_label = unique_labels[-1]
        
        img_flattened = img[mask]
        overseg_flattened = overseg[mask]
        new_overseg = overseg.copy()

        to_split = unique_labels[1:]
        if label is not None:
            to_split = [label]

        for obj in to_split:
            mask_obj = overseg_flattened == obj
            img_segment = img_flattened[mask_obj]
            
            # Skipping background pixels if present
            img_segment = img_segment[img_segment > 0]
            
            if len(img_segment) > 0:
                unique_components = list(np.unique(img_segment))
                if 0 in unique_components:
                    unique_components.remove(0)
                
                if len(unique_components) == 1:
                    # Segment is homogeneous enough; skip splitting
                    continue
                else:
                    # If not homogeneous, proceed with individual adjustments
                    mode_label = unique_components[0]
                    max_label += 1
                    specific_mask = (overseg == obj) & (img == mode_label)
                    #new_overseg[specific_mask] = max_label + 1
                    # Ensure other objects in the segment get unique labels if they do not exceed the threshold
                    for real_obj in np.unique(img_segment):

                        if real_obj != mode_label:
                            max_label += 1
                            specific_mask = (overseg == obj) & (img == real_obj)
                            new_overseg[specific_mask] = max_label

        return new_overseg

################################################################################

    def translate_actor(self, direction, dx = 2, dy = 2, dz = 0):

        self.log("visualizer.py: translate_actor")

        print (self.destination_color)
        if self.destination_color == 0:
            return

        self.clear_selection()

        if direction == "minus_x":
            dx = -dx
            dy = 0
        elif direction == "minus_y":
            dy = -dy
            dx = 0
        elif direction == "plus_x":
            dy = 0
        elif direction == "plus_y":
            dx = 0

        actor = self.surfaceActors[self.destination_color]

        # Obtain the orientation vectors of the camera
        camera = self.renderer.GetActiveCamera()
        camPosition = camera.GetPosition()
        camFocalPoint = camera.GetFocalPoint()
        camViewUp = camera.GetViewUp()
        
        # Compute the direction of projection (view direction)
        viewDirection = [camFocalPoint[i] - camPosition[i] for i in range(3)]
        
        # Normalize the view direction
        vtk.vtkMath.Normalize(viewDirection)
        
        # Compute the right direction (cross product of view direction and view up)
        rightDirection = [0, 0, 0]
        vtk.vtkMath.Cross(viewDirection, camViewUp, rightDirection)
        vtk.vtkMath.Normalize(rightDirection)
        
        # Up direction may not be orthogonal to the view direction, adjust it
        adjustedUpDirection = [0, 0, 0]
        vtk.vtkMath.Cross(rightDirection, viewDirection, adjustedUpDirection)
        vtk.vtkMath.Normalize(adjustedUpDirection)
        
        # Compute world displacement
        worldDisplacement = [rightDirection[i] * dx + adjustedUpDirection[i] * dy for i in range(3)]
        
        # Apply the displacement, preserving the original Z position
        actorPosition = actor.GetPosition()
        newActorPosition = [actorPosition[i] + worldDisplacement[i] for i in range(3)]
            
        # Create a transform that represents the translation
        transform = vtk.vtkTransform()
        
        # Get the current position of the actor
        current_position = actor.GetPosition()
        
        # Apply the translation to the current position to get the new position
        new_position = [current_position[0] + dx, current_position[1] + dy, current_position[2] + dz]
        
        # Set the actor's position to the new position
        actor.SetPosition(newActorPosition)
        
    ####################################################################################################

    def open_color_popup(self):

        self.log("visualizer.py: open_color_popup")

        if len(self.selected_labels) == 0:
            return
        
        selected = self.selected_labels[0]
        self.clear_selection()
        
    
        actor = self.surfaceActors[selected]

        # Function to handle the input ID and highlight object
        def handle_input(event = None):
            user_input = input_var.get()

            hex_color = user_input.lstrip('#')  # Remove the '#' symbol if it's there
            lv = len(hex_color)
            rgb_color = tuple(int(hex_color[i:i + lv // 3], 16) / 255.0 for i in range(0, lv, lv // 3))
            self.colorTransferFunction.AddRGBPoint(selected, rgb_color[0], rgb_color[1], rgb_color[2])
            actor.GetProperty().SetColor(rgb_color)  # Set the actor's color
            self.renderer.GetRenderWindow().Render()
        
            input_window.destroy()  # Close the window after input is handled

        # Initialize a new Tkinter window
        input_window = tk.Tk()
        input_window.title("Enter new color in hexadecimal notation")

        # Text label
        tk.Label(input_window, text="Color:").pack()

        # Entry widget for capturing user input
        input_var = tk.StringVar(input_window)
        input_entry = tk.Entry(input_window, textvariable = input_var)
        
        input_entry.pack()

        # Bind the Return key (Enter key) to the handle_input function
        input_entry.bind("<Return>", handle_input)

        # Button to submit input
        submit_button = tk.Button(input_window, text="Submit", command=handle_input)
        submit_button.pack()

        input_window.mainloop()


    ########################################################################################################

    def save_current_view_as_jpeg(self, file_path):
        """
        Saves the current view from the render window to a JPEG file.
        
        :param file_path: Path to save the JPEG file.
        """

        self.log("visualizer.py: save_current_view_as_jpeg")
        
        # Create a vtkWindowToImageFilter and set your render window
        window_to_image_filter = vtk.vtkWindowToImageFilter()
        window_to_image_filter.SetInput(self.renderWindow)
        window_to_image_filter.SetScale(1)  # Adjust the scale to change the image quality/size
        window_to_image_filter.SetInputBufferTypeToRGB()  # Also supports RGBA
        window_to_image_filter.ReadFrontBufferOff()  # Read from the back buffer
        window_to_image_filter.Update()

        # Create a vtkJPEGWriter and set the output file path
        writer = vtk.vtkJPEGWriter()
        writer.SetFileName(file_path)
        writer.SetInputConnection(window_to_image_filter.GetOutputPort())
        writer.Write()

        print(f"View saved to {file_path}")


    def center_of_mass(self, img):

        self.log("visualizer.py: center_of_mass")

        positive_coords = np.where(img > 0)

        if np.shape(positive_coords)[1] == 0:
            return [0, 0, 0]
        
        mean_z = np.mean(positive_coords[0])
        mean_y = np.mean(positive_coords[1])
        mean_x = np.mean(positive_coords[2])
        
        return [int(mean_z), int(mean_y), int(mean_x)]

    ########################################################################################################


    def save_movie(self):
        """
        Saves the current view from the render window to a JPEG file.
        
        :param file_path: Path to save the JPEG file.
        """

        self.log("visualizer.py: save_movie")
        
        if not os.path.exists("movie"):
            os.mkdir("movie")

        for t in range(len(self.imageDataObjects)):

            print (t)
            self.t = t
          
            self.set_current_image(self.t)
            imageData = self.imageDataObjects[t]
            array = vtk_to_numpy(imageData.GetPointData().GetScalars())
            dims = imageData.GetDimensions()
            array = array.reshape(dims, order='F')
            
            self.center_on_point(self.center_of_mass(array))
            
            if self.draw_line_mode:
                self.LineFit.hide_curves()
                self.LineFit.load_existing_models()

            if self.gui is not None:
                self.gui.update_slider_position(self.t)

            self.textActor.SetInput("Time: " + str(self.t) + "/" + str(len(self.imageDataObjects) - 1))
            self.renderer.GetRenderWindow().Render()
                
            # Create a vtkWindowToImageFilter and set your render window
            window_to_image_filter = vtk.vtkWindowToImageFilter()
            window_to_image_filter.SetInput(self.renderWindow)
            window_to_image_filter.SetScale(1)  # Adjust the scale to change the image quality/size
            window_to_image_filter.SetInputBufferTypeToRGB()  # Also supports RGBA
            window_to_image_filter.ReadFrontBufferOff()  # Read from the back buffer
            window_to_image_filter.Update()

            # Create a vtkJPEGWriter and set the output file path
            writer = vtk.vtkJPEGWriter()
            writer.SetFileName("movie/t" + str(1000+t) + ".jpg")
            writer.SetInputConnection(window_to_image_filter.GetOutputPort())
            writer.Write()

            


# Example usage within the Visualizer_3D class
# visualizer_3d_instance.save_current_view_as_jpeg("/path/to/save/image.jpeg")
    


    """ TODO:
def vtk_error_handler(obj, event):
    print("A VTK error occurred:", obj.GetLastErrorString())
    # Handle the error, e.g., by signaling the rest of your application
    # to adjust its operation, log the error, alert the user, etc.

# Assuming `renderer` is your VTK renderer or relevant VTK object
renderer.AddObserver("ErrorEvent", vtk_error_handler)
"""
