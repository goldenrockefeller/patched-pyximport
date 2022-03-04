# patched-pyximport
Simple pyximport patch for Cython projects. This will extend pyximport, making it more usable for effortlessly compilling Cython code automatically.

You can just copy the `patch_pyximport.py` file into your projects and start using it. This repository serves as an example of how to use it. Just run the `__main__.py`  file

Currently (Feb 2022) Cython's pyximport can be finicky to use. This work extends pyximport to:
- Avoid naming collisions two modules (A and B) from different, unrelated projects that have the same name. This patch locally place all compiled extensions to avoid naming collisions between unrelated modules. With Cython's pyximport, it doesn't matter that module A is not being touched/imported, if module A was compiled at any time in history, then the previously generated extension for module A can override the compilation of module B with a similar name. This means that module A can be imported instead of module B. This can lead to unexpected and hard-to-debug execution error in your projects. With this simple patch, issues with naming collisions are less likely, (but still possible).
- Force recompilation if the module's modification time or size changes. By default, Cython only compiles modules if the module's modication time is after that modifcation of the generated .c file. But consider the situation where you want to replace the module's file with an older version of the file that you save elsewhere. Then the modification time could actually go backwards (atleast on Windows, this is the behavior I observe). This would mean that Cython will not recompile the module and gives no warning, leading to unexpected behavior. This patch will create and maintain a record of the module's file stats, and if these stats changes, then this patch will "touch" the file to force recompilation. This also works with any of the module's dependencies.
- Allow for only the compilation of .py files that has an accompanying .pxd file. This allows you to use pyximport with Cython's new Pure Python Mode, so you can swtich on/off Cython compilation for the .py file. The user can tell pyximport to compile a particular file by adding an accompanying .pxd file. By requiring that there must be an accompanying .pxd file, this patch avoids compiling every single .py files that is imported, and only focus on compiling the files that the user want to compile. 
- Turn on Cython annotations by default. Annotations are great for development and can help guide users on how to use Cython to optimize their Python code.
- Set language level to 3 by default. Since Python 3 is now the dominant python version.


Note that, in most situations, this patch will uninstall Cython's pyximport import hooks so that it can install its own. Additionally, Cython's pyximport will not install its hooks if this patched pyximport installs its hooks first.

Note that this patch will not force Cython recompilation if only the C files are changed.
