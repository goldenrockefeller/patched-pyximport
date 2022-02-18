import pyximport
import pathlib
import importlib
import sys


class PyPxdImporter(pyximport.PyImporter):
    """
        Compiles .py files only if there is an accompanying .pxd file
    """
    def __init__(self, pyxbuild_dir=None, inplace=False, language_level=None):
        pyximport.PyImporter.__init__(
            self,
            pyxbuild_dir=pyxbuild_dir,
            inplace=inplace,
            language_level=language_level
        )
        self.checked_names = set()

    def find_module(self, fullname, package_path=None):

        if fullname in self.checked_names:
            return None
        else:
            self.checked_names.add(fullname)
            spec = importlib.util.find_spec(fullname)

        if not spec:
            return None

        if not spec.loader:
            return None

        if not spec.origin:
            return None

        py_path = pathlib.Path(spec.origin)

        if py_path.stem == "__init__":
            return None

        if py_path.suffix == ".py":
            pxd_path = py_path.parent.joinpath(py_path.stem).with_suffix(".pxd")
        else:
            return None

        if pxd_path.exists():
            return pyximport.PyImporter.find_module(self, fullname, package_path)
        else:
            return None

def install(location, annotate = True, inplace = False):
    build_path = pathlib.Path(location).parent.joinpath("_pyxbld")
    py_importer, pyx_importer = (
        pyximport.install(
            build_dir=build_path,
            build_in_temp=False,
            language_level=3,
            inplace = inplace
        )
    )


    if pyx_importer is not None:
        from Cython.Compiler import Options
        Options.annotate = annotate;

        py_pxd_importer = (
            PyPxdImporter(
                pyxbuild_dir=build_path,
                inplace=inplace,
                language_level=3
            )
        )
        # make sure we import Cython before we install the import hook
        import Cython.Compiler.Main, Cython.Compiler.Pipeline, Cython.Compiler.Optimize
        sys.meta_path.insert(0, py_pxd_importer)

        sys.meta_path.remove(pyx_importer)
        sys.meta_path.insert(0, pyx_importer)
