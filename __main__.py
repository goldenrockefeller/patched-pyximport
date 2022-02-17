import patched_pyximport

using_cython = False

# Comment out this next line to disable Cython compilation and use the original .py files
patched_pyximport.install(__file__); using_cython = True

import py_module
import py_with_pxd_module

if using_cython:
    import pyx_module
    modules = (pyx_module, py_module, py_with_pxd_module)
else:
    modules = ( py_module, py_with_pxd_module)

print("\n-------------------\n")

for module in modules:
    if module.is_compiled:
        print(f"Yes, {module.__name__} was compiled with Cython")
    else:
        print(f"No, {module.__name__} was not compiled with Cython")