import pyximport
import pathlib
import importlib
import sys
import pickle
from dataclasses import dataclass
import os

from Cython.Compiler import Options
from Cython.Build.Dependencies import create_dependency_tree
from Cython.Distutils.build_ext import build_ext


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
class PathStat:
    st_mtime: float
    st_size: int

    @staticmethod
    def from_path(path):
        path = pathlib.Path(path)
        stat = path.stat()
        return PathStat(stat.st_mtime, stat.st_size)

class RecordedPathStatsManager:
    def __init__(self, stats_path):
        self.stats_path = stats_path
        self.stats = recorded_stats_from_path(stats_path)
        self.dependency_tree = create_dependency_tree()

    def save_stats(self):
        save_recorded_stats_to_path(self.stats, self.stats_path)

    def update_stats_for_path(self, path):
        self.stats[str(path)] = PathStat.from_path(path)
        self.save_stats()

    def check_and_touch_one(self, path):
        path = pathlib.Path(path)
        if self.stats.get(str(path)) != PathStat.from_path(path):
            path.touch()
            self.update_stats_for_path(path)

    def check_and_touch_dependencies(self, source_path):
        str_dependency_paths = self.dependency_tree.all_dependencies(str(source_path))

        for str_path in str_dependency_paths:
            self.check_and_touch_one(str_path)



def recorded_stats_from_path(path):

    recorded_stats = {}

    if path.exists():
        with open(path, 'rb') as recorded_stats_file:
            recorded_stats = pickle.load(recorded_stats_file)

    return recorded_stats

def save_recorded_stats_to_path(recorded_stats, path):
    with open(path, 'wb') as recorded_stats_file:
        pickle.dump(recorded_stats, recorded_stats_file)


#
# def module_is_up_to_date(source_path, dependency_paths, recorded_stats):
#     current_dependency_stats = [
#         PathStat.from_path(dependency_path)
#         for dependency_path
#         in dependency_paths
#     ]
#     recorded_dependency_stats = [
#         recorded_stats.get((str(source_path), str(dependency_path)))
#         for dependency_path
#         in dependency_paths
#     ]
#
#     return current_dependency_stats == recorded_dependency_stats


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


def uninstall_importers():
    for importer in sys.meta_path:
        if isinstance(importer, pyximport.PyxImporter):
            sys.meta_path.remove(importer)


def package_dir(source_path, fullname):
    mod_split = fullname.split(".")

    if len(mod_split) == 1:
        # This is a free module
        return source_path.parent
    else:
        # This module is in a package
        modname = mod_split.pop()
        dir = source_path.parent

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
    def __init__(self, recorded_stats_manager, pyxbuild_dir=None, inplace=False, language_level=None):
        pyximport.PyImporter.__init__(
            self,
            pyxbuild_dir=pyxbuild_dir,
            inplace=inplace,
            language_level=language_level
        )
        self.checked_names = set()
        self.recorded_stats_manager = recorded_stats_manager

    def find_module(self, fullname, package_path=None):

        if fullname in self.checked_names:
            return None
        else:
            self.checked_names.add(fullname)
            spec = importlib.util.find_spec(fullname)

        source_path = get_path_from_spec(spec, ".py")

        if source_path is not None:
            pxd_path = source_path.parent.joinpath(source_path.stem).with_suffix(".pxd")

            if pxd_path.exists():
                self.recorded_stats_manager.check_and_touch_dependencies(source_path)
                self.pyxbuild_dir = package_dir(source_path, fullname).joinpath("_pyxbld")
                return pyximport.PyImporter.find_module(self, fullname, package_path)
            else:
                return None
        else:
            return None


class PyxImporter(pyximport.PyxImporter):
    """
        Compiles .pyx files
    """
    def __init__(self, recorded_stats_manager, extension=pyximport.PYX_EXT, pyxbuild_dir=None, inplace=False, language_level=None):
        pyximport.PyxImporter.__init__(
            self,
            extension=extension,
            pyxbuild_dir=pyxbuild_dir,
            inplace=inplace,
            language_level=language_level
        )

        self.recorded_stats_manager = recorded_stats_manager

    def find_module(self, fullname, package_path=None):

        loader = pyximport.PyxImporter.find_module(self, fullname, package_path)

        if loader is not None:
            source_path = pathlib.Path(loader.path)
            self.recorded_stats_manager.check_and_touch_dependencies(source_path)
            loader.pyxbuild_dir = package_dir(source_path, fullname).joinpath("_pyxbld")

        return loader

def install(annotating = True):

    replace_cython_build_ext()

    recorded_stats_path = pathlib.Path.home().joinpath("_pyxbld").joinpath("recorded_stats.pkl")
    recorded_stats_manager = RecordedPathStatsManager(recorded_stats_path)

    # Next line is needed to define 'pyxargs'
    pyximport.install(build_in_temp = False)

    uninstall_importers()

    Options.annotate = annotating;

    py_pxd_importer = PyPxdImporter(recorded_stats_manager, language_level=3)
    pyx_importer = PyxImporter(recorded_stats_manager, language_level=3)

    # make sure we import Cython before we install the import hook
    import Cython.Compiler.Main, Cython.Compiler.Pipeline, Cython.Compiler.Optimize
    sys.meta_path.insert(0, py_pxd_importer)
    sys.meta_path.insert(0, pyx_importer)

