﻿# Overview
This software allows manual correction of segmentation labels in 2D and 3D images. It was developed specifically for correcting segmentation labels of chromosomes in cell nuclei but can be applied to other areas outside Molecular Biology. Manual correction is a necessary post-processing step of many automatic segmentation algorithms, which fail to segment objects perfectly, and require merging, splitting, and manual delineating. The software can also be used for generating ground truth segmentation masks for training supervised machine learning models. 
# Installation
## System requirements
- Python 3

Specific installation for different operating systems is outlined below.
## Windows
My3D Space was developed on Windows and extensively tested, so we recommend using it on Windows if possible. 

1. Make sure you have Visual C++ Development Tools version 14.0 or higher.

1. Install the required external libraries in a terminal:

**python -m pip install tifffile pysimplegui pynput==1.6.0 pptk --find-links .**

Note that “**python**” may have to be replaced **by “python3”, “py”, “python36”**, etc. depending on the alias used by the installation.

1. Then start the application from the terminal:

**python path/to/project/my\_3d\_space.py**

specifying the correct path. Alternatively, first navigate to the My3D Space project and open the terminal from that location, then type:

**python my\_3d\_space.py**
## Linux
1. Navigate to the project directory and install the required external libraries in a terminal:

**python -m pip install tifffile pysimplegui pynput==1.6.0 pptk --find-links .**

1. Follow the steps below to implement a workaround for a bug in the PPTK library:

**cd /home/ubuntu/.pyenv/versions/3.6.8/lib/python3.6/site-packages/pptk/libs/**

(replace the above location with the correct location of python site-packages)

**mv  libz.so.1  libz.so.1.old**

**sudo ln -s /lib/x86\_64-linux-gnu/libz.so.1**

**export QT\_DEBUG\_PLUGINS=1**

**sudo apt-get libxcb-xinerama0**

1. Then start the application from the terminal:

**python path/to/project/my\_3d\_space.py**

specifying the correct path. Alternatively, first navigate to the My3D Space project and open the terminal from that location, then type:

**python my\_3d\_space.py**

## Mac

# Example workflow
Below is a description of a set of steps demonstrating My3D Space functionality. To follow these steps, please use the provided example database.
## Database description
The folder sample\_data contains 13 .tif files. Each .tif file is a 3D stack of a cell nucleus of size (120, 724, 724), i.e. 120 Z planes of size 724x724 pixels. These are different time points in a time lapse experiment, 8 seconds apart. The images represent chromosomes which are segmented and tracked over time. Each chromosome is a 3D object denoted with an integer. For example, all pixels of value 31 constitute one chromosome, and all pixels of value 40 constitute another. The visualizer will assign different colors to different numbers, and the chromosomes will appear as differently colored objects.
## Usage
To start the program, after installing the required dependencies as explained above, navigate to My3D Space folder, start a terminal, and type:

**python my\_3d\_space.py**

The following three windows will appear:

![](Aspose.Words.7093e295-5dba-471f-89c4-c63110b026c3.001.jpeg)

The window on the top left is the initialization menu. The window on the right is the viewer, which is empty for now. The black window on the bottom left is a terminal, which runs backend operations. We recommend minimizing it and making sure it stays open.

Inside the menu (top left), “Segmentation folder” is the only required argument. Using the Browse button, please navigate to the folder sample\_data. Leaving the other fields blank will load all images from the selected folder, and will assign 1 (arbitrary unit) to the pixel size in x, y, and z. These pixel sizes should be set in case of anisotropic data – where the physical distance between Z planes is different from the pixel size in XY. This is the case with the current data. 

Start and end will enable loading a subset of the available images, at specific intervals. 

Let’s use the following settings:

start  1100     end  1105   interval  1                  Pixel size:    x   0.045  y   0.045  z   0.18

These are the pixel sizes in microns of the actual experiment.

After pressing OK, the images will start loading. Upon completion, the following outlook should appear in the viewer:

![](Aspose.Words.7093e295-5dba-471f-89c4-c63110b026c3.002.jpeg)

The sliding bar on the bottom changes the time point. 

The following operations are inherited from the PPTK library:

Left click + drag performs rotation. 

Scroll performs zooming in/out. 

Double left clicking on an object centers the view on that object.

Holding Shift + left click translates the view left/right or up/down.

