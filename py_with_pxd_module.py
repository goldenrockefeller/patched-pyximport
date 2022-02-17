import cython

if cython.compiled:
    is_compiled = True
else:
    is_compiled = False