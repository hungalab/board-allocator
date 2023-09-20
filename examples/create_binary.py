import os
import sys

# import PyInstaller.__main__ as pyi_cli
from PyInstaller.building import makespec, build_main


def create_spec(target_script:str, import_path_list: list):
    pathex = import_path_list
    filenames = [target_script]
    spec_file_path = makespec.main(filenames, onefile=True, pathex=pathex)
    print(f"Create spec file as {spec_file_path}")
    return spec_file_path


def create_binary(spec_file_path: str):
    distpath = os.path.join(os.getcwd(), "dist")
    workpath = os.path.join(os.getcwd(), "build")
    build_main.main(None, spec_file_path, distpath=distpath, workpath=workpath, clean_build=False)


if __name__ == "__main__":
    import_list = sys.path
    import_list.append("../")
    target = "run_allocator.py"
    spec_file_path = create_spec(target, import_list)
    create_binary(spec_file_path)
    print("[INFO] Finish creating binary")
