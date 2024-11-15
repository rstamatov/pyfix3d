# Overview
This software allows manual correction of segmentation labels in 2D and 3D images. It was developed specifically for correcting segmentation labels of chromosomes in cell nuclei but can be applied to other areas outside Molecular Biology. Manual correction is a necessary post-processing step of many automatic segmentation algorithms, which fail to segment objects perfectly, and require merging, splitting, and manual delineating. The software can also be used for generating ground truth segmentation masks for training supervised machine learning models. 

# Installation 
## System requirements

•	Windows: tested on Python 2.7, 3.6, and 3.7 but may work on other versions
•	Linux: tested on Python 3.4 - 3.11 version, but may work on earlier ones
•	Mac OS: tested on Python 3.10 but should work on any Python 3 version
To download python libraries, we recommend using PIP.
Specific installation for different operating systems is outlined below. Please ensure that no errors are reported at the installation step. If there are errors you are unable to fix, please let us know. Installation of all required libraries takes around two minutes on a typical desktop computer.
Windows
Pyfix3d was developed on Windows and extensively tested, so we recommend using it on Windows if possible. 
1.	Make sure you have Visual C++ Development Tools version 14.0 or higher.

2.	Install the required external libraries in a terminal:
python -m pip install numpy scipy matplotlib vtk tifffile networkx openpyxl
Note that “python” may have to be replaced by “python3”, “py”, “python36”, etc. depending on the alias used by the installation. 
3.	Then start the application from the terminal:
python path/to/project/Pyfix3d/pyfix3d.py
specifying the correct path. Alternatively, first navigate to the Pyfix3d project and open the terminal from that location, then type:
python pyfix3d.py

Linux
The program has been tested on Ubuntu 17.10 and Ubuntu 22.04. Follow the same steps as above.
Mac
The program has been tested on Mac OS Catalina with python 3.10. Follow the same steps as for Windows.

# Example workflow
Below is a description of a set of steps demonstrating Pyfix3d functionality. To follow these steps, please use the provided example database.
Database description
The folder sample_data contains 13 .tif files. Each .tif file is a 3D stack of a cell nucleus of size (64, 256, 256), i.e. 64 Z planes of size 256x256 pixels. These are different time points in a time lapse experiment, 8 seconds apart. The images represent chromosomes which are segmented and tracked over time. Each chromosome is a 3D object denoted with an integer. For example, all pixels of value 31 constitute one chromosome, and all pixels of value 40 constitute another. The visualizer will assign different colors to different numbers, and the chromosomes will appear as differently colored objects.

# Usage
## Initial settings
To start the program, after installing the required dependencies as explained above, navigate to Pyfix3d folder, start a terminal, and type:
python pyfix3d.py
The following window will appear (Fig. S1):

 ![startup menu](https://github.com/user-attachments/assets/3b1f2031-ec07-4279-968c-a9e1880cea9e)

Fig. S1 | Initialization menu. The user is prompted to specify the location of segmentation images to be displayed or corrected; optionally, a folder with oversegmentations can be specified as well, to aid in segmentation as a hidden layer (see below); a folder with raw images can be chosen for overlaying the segmentation. Start, end, interval positions and pixel size are also optional.

This is the initialization menu and it will appear in addition to the terminal, which runs backend operations. We recommend minimizing the terminal window and making sure it stays open.
Inside the initialization menu, “segmentation” is the only required argument. Using the Browse button, please navigate to the folder sample_data. Leaving the other fields blank will load all images from the selected folder, and will assign 1 (arbitrary unit) to the pixel size in x and y, and 2 to the pixel size in z. These pixel sizes should be set in case of anisotropic data – where the physical distance between Z planes is different from the pixel size in XY. This is the case with the current data. 
Start and end will enable loading a subset of the available images, at specific intervals. 
Let’s use the following settings:

start  0     
end 5  
interval  1                  

Pixel size:    x   0.045 
Pixel size  y   0.045  
Pixel size z   0.18
These are the pixel sizes in microns of the actual experiment.
After pressing OK, the images will start loading. Upon completion, the following outlook should appear in the viewer (Fig. S2):

 ![main view](https://github.com/user-attachments/assets/0f43c6c7-7e9e-45e5-b1cb-838385502ead)

Fig. S2 | The main view of Pyfix2D. Each segmentation label is given a random color.

This is the main view of Pyfix3D. The following mouse operations are available:
•	Left + Drag: rotation
•	Left click + Shift + Drag: Translation
•	Scroll: zoom in and out
•	Double left click on an object: center the view on this object.

Different outlooks are available. To toggle between dark and light background, use the “B” key (Fig. S3a). Mesh representation is enabled with the “W” key and disabled with “C” (Fig. S3b). Black and white color mapping can be chosen from the View submenu (Fig. S3c). The last option is especially useful for highlighting a particular object or a group of objects – see later how to change the color of a particular label.

 
Fig. S3 | Different views are available. (a) Dark background, enabled with the “B” key. (b) Mesh representation, enabled with the “O” key. (c) Black and white color mapping, enabled from the View submenu.

In addition to the main view window, you will see a menu pop up (Fig. S4a). The sliding bar, as well as the left and right arrowheads change the image in the loaded sequence (e.g. time). Four buttons are visible below the sliding bar. The button with the scissors is the action command – used for correction and curve manipulation (see later). The three remaining buttons are the mutually exclusive working modes. The default mode (hand icon) is used for visualization, rotation/zooming, chromosome selection, and crude corrections. The magic wand button enables fine corrections, and the curve fitting button allows semi-automatic spline fitting to the segmentation labels. All these procedures are explained below.

 ![submenus](https://github.com/user-attachments/assets/84228cab-fc3d-46ce-bcd5-6f913797965e)

Fig. S4 | Main menu and submenus. (a) The main menu has a sliding bar and buttons for changing the image in the sequence (as in a time series) and four buttons: the action button used mainly for executing a correction operation; the default mode which allows viewing and crude-level corrections; the magic wand mode, which enables precise corrections, and the curve fitting mode, allowing manual spline fitting. (b) The file submenu lists operations related to loading and saving; (c) the view submenu contains commands related to the viewer interface; (d) Manipulation commands are listed in the Edit submenu.

The File, Show, and Edit submenus list corresponding commands (Fig. S4b-d). Notice that most commands have a keyboard shortcut. 

## Label selection and marking
In the default mode (hand icon), Ctrl + Left click selects a label and highlights it in yellow. Several labels can be selected. To de-select all selected labels, use right click only (no Ctrl).
Several operations can be performed with selected labels:
•	Gray all others – by using the “G” key or Show  Gray/Show others. This option leaves the selected labels colored, while dimming out all the rest. (Fig. S5) Use the same command to revert.

•	Mark – by using the “M” key. This marks a label as processed and hides it. This is especially useful when many labels are crowded in a compact 3D structure, and hiding the ones not needed will facilitate access to the ones within. To show all labels, including the ones hidden, use the “A” key. Pressing “M” without any selection hides all marked labels. “U” shows all hidden. To unmark a marked label, use “N”.
Note that marked labels are saved in a text file called hidden_objects.txt inside the program folder. This way the marked objects can be loaded later, after restarting the program. Several such groups of marked objects can be created. To do this, use File  Create/load group – and select an existing object file to load or choose a location and name for a new group. 
In the simplest case, when just one group of marked labels is enough, and you’re relying on the default hidden_objects.txt file, don’t forget to delete it if starting a new task.
Searching for a specific label is also possible by using Show  Find…, or with Ctrl + “F.” You can list several numbers separated by a comma. The specified label(s) will remain colored while the rest will be dimmed. This view is reversed by “g” or “Show/Gray others”.
•	Changing the color – the “o” key opens a pop-up asking for a new color for the selected label in hexadecimal format (Fig. S6a-c). For example, dd0000 is the color code for a shade of red (Fig. S6d). Such color codes can be found online. This option is especially useful when nearby labels accidentally ended up with similar colors. Alternatively, one can use Ctrl + O without selection to randomize the colors of all labels.

•	Correction, merging and spline fitting – explained later. The explanations for those refer to marking of a label, as outlined in this section.

 ![gray_others](https://github.com/user-attachments/assets/09777201-61c6-4da8-a811-25dbd501a7af)

Fig. S4 | An example of the “gray others” option


![recolor](https://github.com/user-attachments/assets/58b0ad9e-c727-4dbd-b8fa-68fa310f06eb)

 
Fig. S6 | Changing the color of a selected label. (a) A decision is made to recolor the white label to red. (b) The label is selected with the mouse. (c) The “o” key brings up the color selection window, requiring a hexadecimal value for RGB. (d) The result after execution.


## Correction
Correction refers to changing the identity (integer value) of a group of pixels, making them part of a different segmentation label. This is not simply changing their visualization color, the actual value of those pixels is modified. In the general case, correction is necessary because two nearby labels are touching each other and part of one needs to be recolored to the other (Fig. S7a). Thus, correction generally involves two actors: the label which will be modified (here referred to as the source), and the label whose color we desire (referred to as the destination). In other words, we will recolor part of the source using the color of the destination. Having these definitions in mind, there are several types of corrections:
•	Magic wand correction. First, select the destination label and press “D” (or Edit  Set destination). Then set the source label with “S” (or Edit  Set source). Now go to the magic wand mode. Using the mouse with the Ctrl key pressed, outline the region that needs to be corrected (Fig. S7b). Note that only pixels part of the source can be selected. This operation selects all pixels of the source label within the 2D drawn shape, and along the ray of view in depth (Fig. S7c). Therefore, make sure no part of the label is hidden behind itself, unless you want to select it as well. Now pressing the action button (scissors icon), or Ctrl + Right click, performs the correction (Fig. S7d). Don’t forget to clear the destination with “D” and the source with “S”, without any selection. 
The source and destination can also be set from within the magic wand mode. However, clicking selection is disabled there, so you can outline a small region of the desired labels with the mouse.
The last correction can be undone with Ctrl + Z.
•	Merging – after setting the source and destination as above, use Edit  Merge on all frames – to recolor the whole source label to the destination, effectively merging them on all loaded images. Merging can be performed without setting source and destination. Just select two or more labels with Ctrl + Left click, and they can all be merged using the last selected label as the destination. The merging operation is undoable. 

•	Correction with oversegmentations – to use this option, you must have loaded a matching set of oversegmentation images at the initialization, as a second, hidden layer. If so, then clicking on a label in the default mode will not highlight the whole label but rather the underlying (hidden) chunk of the oversegmentation image. After setting the source and destination as above, you can now color whole chunks instead of manually drawing a region. This can be faster or  more convenient in certain situations. Again, destination and source may ne be used, and instead selecting two or more chunks can be used to correct all of them using the last selected chunk as the destination. 

The last such operation is reversible with Ctrl + Z.

•	Splitting – to split a label in parts, label it as destination. Then select a subset of its pixels, either by drawing with the magic wand or by clicking on an oversegmentation chunk. “Edit  Create new label” will create a new, unique ID for the selected region. 

 ![corrections](https://github.com/user-attachments/assets/8e730439-2b9d-42f1-9efa-2439d1bc4b9e)

Fig. S7 | Correction. (a) Top right corner – the magic wand mode is selected. Center – part of the purple label must be changed to be part of the green. (b) Ctrl + Left + Drag allows manual delineating of a region of interest. (c) Upon completion of the drawn shape, all pixels inside the shape, and along the view direction in 3D are highlighted. (c) The result after executing the command with the action button (or Ctrl + right).

## Curve fitting
Since Pyfix3D was originally developed for mitotic chromosomes, which are elongated tubular structures, it was essential to implement the option to fit curves semi-automatically. This is similar to skeletonization but most skeletonization algorithms are implemented automatically and don’t allow user interaction in case of errors, such as missing the structure endpoints or failing to capture loops. On the other hand, Fiji has the option to place landmarks manually in the 3D viewer but they are situated on the surface of the structure and not the center; besides, fitting a curve through these points requires further programming.
To use the curve fitting option in Pyfix3D, set it as destination (Fig. S8a), and choose the curve fitting button. Now place individual points along the structure using the mouse cursor and Ctrl + Left click. Right click (without Ctrl) clears the current points, so you can start over. A yellow sphere will appear at the location of each click (Fig. S8b). Notice that points are automatically located in the center of the structure. As was the case with the correction operation, avoid the case when part of the label is behind another part of the same label – in this case you must rotate the view, otherwise the point may not be placed correctly. 
After finishing with the selection points, you can use the action button (scissors icon) or Ctrl + Right click to fit a spline curve along the selected points (Fig. S8c). Only one curve can be fitted to a label. To delete the current curve, use Edit  Delete active spline.
To save the curves, use File  Save splines and choose a folder. To load splines, use File  Load splines, but make sure no other files have been manually added to the splines folder because this will interfere with the loading. 
Again, in the context of chromosomes, it was useful to have the option of denoting the location of the centromere. After the curve has been fit, you can choose a point on the curve, and press the action button (or Ctrl + Right click). This will place a sphere on the curve and divide it in two, splitting a chromosome into two arms.
File  Save measurements generates an excel file with two tabs – for the lengths of each spline  and for the ratio of the two arms in case a splitting point is created. Note that the length depends on the pixel sizes chosen upon initialization. If you load a set of splines and choose different pixel sizes, saving the measurements again will re-calculate the values using the new pixel sizes.
Note that saving the measurements and saving the splines themselves are distinct operation.

![curve fitting](https://github.com/user-attachments/assets/82e4e6d5-732a-4669-b21f-f2fdf66721fc)


 
Fig. S8 | Curve fitting. (a) The chromosome in cyan is chosen as destination to enable curve fitting on it. (b) Selecting the curve fitting button converts the destination label to mesh representation. Each mouse click places a point, centering it in depth. (c) The action button (or Ctrl + right click) fits a spline curve through the points.

To select specific labels and hide the rest, we can use the “Find object” button. Pressing “Find object” invokes a pop-up window (left image below), where we can type the number of the labels of interest. Let’s type in the following sequence, separated by comas: 31,41,80,100,101. Clicking OK grays out all other labels, as shown on the right:

## Saving
Use the “Save all” button to save the changes. We recommend doing this often, as a safeguard against sudden crash of your machine or the program itself. It may be wise to save the results to a new folder, otherwise the existing images will be overwritten. 

## Reporting errors
Please report any unusual behavior to us. If an exception is not caught and the program crashes, there should be some information in the terminal. Please report this to help us fix the issues.

