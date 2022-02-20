import pyximport
import pathlib
import importlib
import sys
import pickle
from dataclasses import dataclass

from Cython.Compiler import Options
from Cython.Build.Dependencies import create_dependency_tree
from Cython.Distutils.build_ext import build_ext

loaded_recorded_stats = {}
is_patched_importer_installed = False
are_recorded_stats_loaded = False




# Temporary directories are long because pyximport "doubles" the parent directory path.

def new_finalize_options(bld_ext):
    old_finalize_options = bld_ext.finalize_options
    def finalize_options(bld_ext):
        bld_ext.build_temp = str(pathlib.Path.home().joinpath("_pyxbld").joinpath("temp"))
        old_finalize_options(bld_ext)
    return finalize_options

def replace_cython_build_ext():
    build_ext.finalize_options = new_finalize_options(build_ext)

@dataclass
class RecordedStat:
    st_mtime: float
    st_size: int

    @staticmethod
    def from_filepath(filepath):
        path = pathlib.Path(filepath)
        stat = path.stat()
        return RecordedStat(stat.st_mtime, stat.st_size)

def load_recorded_stats():
    global loaded_recorded_stats, are_recorded_stats_loaded

    pyxbld_dir = pathlib.Path.home().joinpath("_pyxbld")
    pyxbld_dir.mkdir(exist_ok = True)
    recorded_stats_path = pyxbld_dir.joinpath("recorded_stats.pkl")

    if recorded_stats_path.exists():
        with open(recorded_stats_path, 'rb') as recorded_stats_file:
            loaded_recorded_stats = pickle.load(recorded_stats_file)
    else:
        with open(recorded_stats_path, 'wb') as recorded_stats_file:
            recorded_stats = {}
            pickle.dump(recorded_stats, recorded_stats_file)

    are_recorded_stats_loaded = True

def save_recorded_stats():
    global loaded_recorded_stats, are_recorded_stats_loaded

    pyxbld_dir = pathlib.Path.home().joinpath("_pyxbld")
    pyxbld_dir.mkdir(exist_ok = True)
    recorded_stats_path = pyxbld_dir.joinpath("recorded_stats.pkl")

    if not are_recorded_stats_loaded:
        load_recorded_stats()

    with open(recorded_stats_path, 'wb') as recorded_stats_file:
        pickle.dump(loaded_recorded_stats, recorded_stats_file)

def recorded_stat(filepath):
    global loaded_recorded_stats

    if filepath not in loaded_recorded_stats:
        path = pathlib.Path(filepath)
        path.touch()
        update_recorded_stat(filepath)

    return loaded_recorded_stats[str(filepath)]


def update_recorded_stat(filepath):
    global loaded_recorded_stats

    loaded_recorded_stats[str(filepath)] = RecordedStat.from_filepath(filepath)
    save_recorded_stats()

def check_and_touch_one(filepath):
    the_recorded_stat = recorded_stat(filepath)

    path = pathlib.Path(filepath)
    stat = path.stat()

    if stat.st_mtime != the_recorded_stat.st_mtime or stat.st_size != the_recorded_stat.st_size:
        path.touch()
        update_recorded_stat(filepath)

def check_and_touch_dependencies(path):
    dependency_tree = create_dependency_tree()
    dependencies = dependency_tree.all_dependencies(str(path))

    for dependency in dependencies:
        check_and_touch_one(dependency)

def get_path_from_spec(spec, ext):

        if not spec:
            return None

        if not spec.loader:
            return None

        if not spec.origin:
            return None

        path = pathlib.Path(spec.origin)

        if path.stem == "__init__":
            return None

        if path.suffix != ext:
            return None

        return path


def uninstall_unpatched_importers():
    for importer in sys.meta_path:
        if (
            isinstance(importer, pyximport.PyxImporter)
            and not isinstance(importer, PyxImporter)
            and not isinstance(importer, PyPxdImporter)
        ):
            sys.meta_path.remove(importer)


def package_parent(mod_path, fullname):
    mod_split = fullname.split(".")

    if len(mod_split) == 1:
        # This is a free module
        return mod_path.parent
    else:
        # This module is in a package
        modname = mod_split.pop()
        dir = mod_path.parent

        while len(mod_split) > 1:
            pkg_name = mod_split.pop()
            if pkg_name != dir.name:
                # It is not safe to go up a directory because names are mismatched
                return dir #
            dir = dir.parent

        return dir

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

        mod_path = get_path_from_spec(spec, ".py")

        if mod_path is not None:
            pxd_path = mod_path.parent.joinpath(mod_path.stem).with_suffix(".pxd")

            if pxd_path.exists():
                check_and_touch_dependencies(mod_path)
                self.pyxbuild_dir = package_parent(mod_path, fullname).joinpath("_pyxbld")
                return pyximport.PyImporter.find_module(self, fullname, package_path)
            else:
                return None
        else:
            return None


class PyxImporter(pyximport.PyxImporter):
    """
        Compiles .pyx files
    """
    def __init__(self, extension=pyximport.PYX_EXT, pyxbuild_dir=None, inplace=False, language_level=None):
        pyximport.PyxImporter.__init__(
            self,
            extension=extension,
            pyxbuild_dir=pyxbuild_dir,
            inplace=inplace,
            language_level=language_level
        )

    def find_module(self, fullname, package_path=None):

        loader = pyximport.PyxImporter.find_module(self, fullname, package_path)

        if loader is not None:
            mod_path = pathlib.Path(loader.path)
            check_and_touch_dependencies(mod_path)
            loader.pyxbuild_dir = package_parent(mod_path, fullname).joinpath("_pyxbld")

        return loader

def install(annotate = True):
    global is_patched_importer_installed

    if not is_patched_importer_installed:
        replace_cython_build_ext()

        load_recorded_stats()

        # Next line is needed to define 'pyxargs'
        pyximport.install(build_in_temp = False); uninstall_unpatched_importers()

        Options.annotate = annotate;

        py_pxd_importer = PyPxdImporter(language_level=3)
        pyx_importer = PyxImporter(language_level=3)

        # make sure we import Cython before we install the import hook
        import Cython.Compiler.Main, Cython.Compiler.Pipeline, Cython.Compiler.Optimize
        sys.meta_path.insert(0, py_pxd_importer)
        sys.meta_path.insert(0, pyx_importer)

        is_patched_importer_installed = True
