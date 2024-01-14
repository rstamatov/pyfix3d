#!/bin/sh
pip install tifffile pysimplegui pynput==1.6.0 pptk --find-links .

python_site_packages=$(python-m site --user-site 2>&1)/pptk/libs/
cd $python_site_packages
mv  libz.so.1  libz.so.1.old
sudo ln -s /lib/x86_64-linux-gnu/libz.so.1
export QT_DEBUG_PLUGINS=1
sudo apt-get libxcb-xinerama0