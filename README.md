# patched-pyximport
Simple pyximport patch for Cython projects. This will extend pyximport, making it more usable for effortlessly compilling Cython code automatically.

You can just copy the `patch_pyximport.py` file into your projects and start using it. This repository serves as an example of how to use it. Just run the `__main__.py`  file

Currently (Feb 2022) Cython's pyximport can be finicky to use. This work extends pyximport to:
- Locally place all compiled extensions to avoid naming collisions between two modules from different, unrelated projects that have the same name. 
With pyximport, it doesn't matter that the other module is not being touched/imported, if that module was compiled at any time in history, then the previously generated extension can override the compilation of the current module with a similar name. This can lead to unexpected and hard-to-debug execution error in your projects. With this simple patch, issues with naming collisions are less likely, (but still possible).
- Allow for only the compilation of .py files that has an accompanying .pxd file. This allows you to use pyximport with Cython's new Pure Python Mode, so you can swtich on/off Cython compilation for the .py file. The user can tell pyximport to compile a particular file by adding an accompanying .pxd file. By requiring that there must be an accompanying .pxd file, this patch avoids compiling every single .py files that is imported, and only focus on compiling the files that the user want to compile. 
- Turn on Cython annotations by default. Annotations are great for development and can help guide users on how to use Cython to optimize their Python code.
- Set language level to 3 by default. Since Python 3 is now the dominant python version.


Note that, in most situations, this will not install import hooks if Cython's pyximport installs its hooks first. Additionally, Cython's pyximport will not install its hooks if this patched pyximport installs its hooks first.
