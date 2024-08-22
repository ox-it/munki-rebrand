#!/usr/bin/env python3
# encoding: utf-8
"""
munki_rebrand.py

Script to rebrand and customise Munki's Managed Software Center

Copyright (C) University of Oxford 2016-21
    Ben Goodstein <ben.goodstein at it.ox.ac.uk>

Based on an original script by Arjen van Bochoven

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import subprocess
import os
import stat
import shutil
from tempfile import mkdtemp
from xml.etree import ElementTree as ET
import plistlib
import argparse
import sys
import atexit
import glob
import fnmatch
import io
import json

VERSION = "5.6"

APPNAME = "Managed Software Center"

APPNAME_LOCALIZED = {
    "Base": "Managed Software Center",
    "da": "Managed Software Center",
    "de": "Geführte Softwareaktualisierung",
    "en": "Managed Software Center",
    "en-AU": "Managed Software Centre",
    "en-GB": "Managed Software Centre",
    "en-CA": "Managed Software Centre",
    "en_AU": "Managed Software Centre",
    "en_GB": "Managed Software Centre",
    "en_CA": "Managed Software Centre",
    "es": "Centro de aplicaciones",
    "fi": "Managed Software Center",
    "fr": "Centre de gestion des logiciels",
    "it": "Centro Gestione Applicazioni",
    "ja": "Managed Software Center",
    "nb": "Managed Software Center",
    "nl": "Managed Software Center",
    "ru": "Центр Управления ПО",
    "sv": "Managed Software Center",
}

MSC_APP = {
    "path": "Applications/Managed Software Center.app",
    "icon": ["Managed Software Center.icns", "AppIcon.icns"],
}
MS_APP = {
    "path": os.path.join(MSC_APP["path"], "Contents/Helpers", "MunkiStatus.app"),
    "icon": ["MunkiStatus.icns", "AppIcon.icns"],
}
MN_APP = {
    "path": os.path.join(MSC_APP["path"], "Contents/Helpers", "munki-notifier.app"),
    "icon": ["AppIcon.icns"],
}
APPS = [MSC_APP, MS_APP, MN_APP]

MUNKI_PATH = "usr/local/munki"
PY_FWK = os.path.join(MUNKI_PATH, "Python.Framework")
PY_CUR = os.path.join(PY_FWK, "Versions/Current")

ICON_SIZES = [
    ("16", "16x16"),
    ("32", "16x16@2x"),
    ("32", "32x32"),
    ("64", "32x32@2x"),
    ("128", "128x128"),
    ("256", "128x128@2x"),
    ("256", "256x256"),
    ("512", "256x256@2x"),
    ("512", "512x512"),
    ("1024", "512x512@2x"),
]

PKGBUILD = "/usr/bin/pkgbuild"
PKGUTIL = "/usr/sbin/pkgutil"
PRODUCTBUILD = "/usr/bin/productbuild"
PRODUCTSIGN = "/usr/bin/productsign"
CODESIGN = "/usr/bin/codesign"
FILE = "/usr/bin/file"
PLUTIL = "/usr/bin/plutil"
SIPS = "/usr/bin/sips"
ICONUTIL = "/usr/bin/iconutil"
CURL = "/usr/bin/curl"
ACTOOL = [
    "/usr/bin/actool",
    "/Applications/Xcode.app/Contents/Developer/usr/bin/actool",
]

MUNKIURL = "https://api.github.com/repos/munki/munki/releases/latest"

global verbose
verbose = False
tmp_dir = mkdtemp()


@atexit.register
def cleanup():
    print("Cleaning up...")
    try:
        shutil.rmtree(tmp_dir)
    # In case subprocess cleans up before we do
    except OSError:
        pass
    print("Done.")


def run_cmd(cmd, ret=None):
    """Runs a command passed in as a list. Can also be provided with a regex
    to search for in the output, returning the result"""
    proc = subprocess.run(cmd, capture_output=True)
    if verbose and proc.stdout != b"" and not ret:
        print(proc.stdout.rstrip().decode())
    if proc.returncode != 0:
        print(proc.stderr.rstrip().decode())
        sys.exit(1)
    if ret:
        return proc.stdout.rstrip().decode()


def get_latest_munki_url():
    cmd = [CURL, MUNKIURL]
    j = run_cmd(cmd, ret=True)
    api_result = json.loads(j)
    return api_result["assets"][0]["browser_download_url"]


def download_pkg(url, output):
    print(f"Downloading munkitools from {url}...")
    cmd = [CURL, "--location", "--output", output, url]
    run_cmd(cmd)


def flatten_pkg(directory, pkg):
    """Flattens a pkg folder"""
    cmd = [PKGUTIL, "--flatten-full", directory, pkg]
    run_cmd(cmd)


def expand_pkg(pkg, directory):
    """Expands a flat pkg to a folder"""
    cmd = [PKGUTIL, "--expand-full", pkg, directory]
    run_cmd(cmd)


def plist_to_xml(plist):
    """Converts plist file to xml1 format"""
    cmd = [PLUTIL, "-convert", "xml1", plist]
    run_cmd(cmd)


def plist_to_binary(plist):
    """Converts plist file to binary1 format"""
    cmd = [PLUTIL, "-convert", "binary1", plist]
    run_cmd(cmd)


def guess_encoding(f):
    cmd = [FILE, "--brief", "--mime-encoding", f]
    enc = run_cmd(cmd, ret=True)
    if "ascii" in enc:
        return "utf-8"
    return enc

def is_binary(f):
    if guess_encoding(f) == "binary":
        return True
    else:
        return False

def replace_strings(strings_file, code, appname):
    """Replaces localized app name in a .strings file with desired app name"""
    localized = APPNAME_LOCALIZED[code]
    if verbose:
        print(f"Replacing '{localized}' in {strings_file} with '{appname}'...")
    backup_file = f"{strings_file}.bak"
    enc = guess_encoding(strings_file)

    # Could do this in place but im oldskool so
    with io.open(backup_file, "w", encoding=enc) as fw, io.open(
        strings_file, "r", encoding=enc
    ) as fr:
        for line in fr:
            # We want to only replace on the right hand side of any =
            # and we don't want to do it to a comment
            if "=" in line and not line.startswith("/*"):
                left, right = line.split("=")
                right = right.replace(localized, appname)
                line = "=".join([left, right])
            fw.write(line)
    os.remove(strings_file)
    os.rename(backup_file, strings_file)


def icon_test(png):
    # Check if icon is png
    with open(png, "rb") as f:
        pngbin = f.read()
    if pngbin[:8] == b'\x89PNG\r\n\x1a\n' and pngbin[12:16] == b'IHDR':
        return True
    return False


def convert_to_icns(png, output_dir, actool=""):
    """Takes a png file and attempts to convert it to an icns set"""
    icon_dir = os.path.join(output_dir, "icons")
    os.mkdir(icon_dir)
    xcassets = os.path.join(icon_dir, "Assets.xcassets")
    os.mkdir(xcassets)
    iconset = os.path.join(xcassets, "AppIcon.appiconset")
    os.mkdir(iconset)
    contents = {}
    contents["images"] = []
    for hw, suffix in ICON_SIZES:
        scale = "1x"
        if suffix.endswith("2x"):
            scale = "2x"
        cmd = [
            SIPS,
            "-z",
            hw,
            hw,
            png,
            "--out",
            os.path.join(iconset, f"AppIcon_{suffix}.png"),
        ]
        run_cmd(cmd)
        if suffix.endswith("2x"):
            hw = str(int(hw) / 2)
        image = dict(
            size=f"{hw}x{hw}",
            idiom="mac",
            filename=f"AppIcon_{suffix}.png",
            scale=scale,
        )
        contents["images"].append(image)
    icnspath = os.path.join(icon_dir, "AppIcon.icns")

    # Munki 3.6+ has an Assets.car which is compiled from the Assets.xcassets
    # to provide the AppIcon
    if actool:
        # Use context of the location of munki_rebrand.py to find the Assets.xcassets
        # directory.
        rebrand_dir = os.path.dirname(os.path.abspath(__file__))
        xc_assets_dir = os.path.join(rebrand_dir, "Assets.xcassets/")
        if not os.path.isdir(xc_assets_dir):
            print(
                f"The Assets.xcassets folder could not be found in {rebrand_dir}. "
                "Make sure it's in place, and then try again."
            )
            sys.exit(1)
        shutil.copytree(xc_assets_dir, xcassets, dirs_exist_ok=True)
        with io.open(os.path.join(iconset, "Contents.json"), "w") as f:
            contentstring = json.dumps(contents)
            f.write(contentstring)
        cmd = [
            actool,
            "--compile",
            icon_dir,
            "--app-icon",
            "AppIcon",
            "--minimum-deployment-target",
            "10.11",
            "--output-partial-info-plist",
            os.path.join(icon_dir, "Info.plist"),
            "--platform",
            "macosx",
            "--errors",
            "--warnings",
            xcassets,
        ]
        run_cmd(cmd)
    else:
        # Old behaviour for < 3.6
        cmd = [ICONUTIL, "-c", "icns", iconset, "-o", icnspath]
        run_cmd(cmd)

    carpath = os.path.join(icon_dir, "Assets.car")
    if not os.path.isfile(carpath):
        carpath = None
    if not os.path.isfile(icnspath):
        icnspath = None

    return icnspath, carpath


def sign_package(signing_id, pkg):
    """Signs a pkg with a signing id"""
    cmd = [PRODUCTSIGN, "--sign", signing_id, pkg, f"{pkg}-signed"]
    print("Signing pkg...")
    run_cmd(cmd)
    print(f"Moving {pkg}-signed to {pkg}...")
    os.rename(f"{pkg}-signed", pkg)


def sign_binary(
    signing_id,
    binary,
    verbose=False,
    deep=False,
    options=[],
    entitlements="",
    force=False):
    """Signs a binary with a signing id, with optional arguments for command line
    args"""
    cmd = [CODESIGN, "--sign", signing_id]
    if force:
        cmd.append("--force")
    if deep:
        cmd.append("--deep")
    if verbose:
        cmd.append("--verbose")
    if entitlements:
        cmd.append("--entitlements")
        cmd.append(entitlements)
    if options:
        cmd.append("--options")
        cmd.append(",".join([option for option in options]))
    cmd.append(binary)
    run_cmd(cmd)


def is_signable_bin(path):
    '''Checks if a path is a file and is executable'''
    if os.path.isfile(path) and (os.stat(path).st_mode & stat.S_IXUSR > 0):
        return True
    return False


def is_signable_lib(path):
    '''Checks if a path is a file and ends with .so or .dylib'''
    if os.path.isfile(path) and (path.endswith(".so") or path.endswith(".dylib")):
        return True
    return False


def main():
    p = argparse.ArgumentParser(
        description="Rebrands Munki's Managed Software "
        "Center - gives the app a new name in Finder, "
        "and can also modify its icon. N.B. You will "
        "need Xcode and its command-line tools "
        "installed to run this script successfully."
    )

    p.add_argument(
        "-a",
        "--appname",
        action="store",
        help="Your desired app name for Managed Software Center.",
    )
    p.add_argument(
        "-k", "--pkg", action="store", help="Prebuilt munkitools pkg to rebrand."
    ),
    p.add_argument(
        "-i",
        "--icon-file",
        action="store",
        default=None,
        help="""Optional icon file to replace Managed Software Center's. Should be a
         1024x1024 .png with alpha channel""",
    )
    p.add_argument(
        "--identifier",
        action="store",
        default="com.googlecode.munki",
        help="Optionally change the prefix of the package identifier"
    )
    p.add_argument(
        "-o",
        "--output-file",
        action="store",
        default=None,
        help="Optional base name for the customized pkg outputted by this tool",
    )
    p.add_argument(
        "-p",
        "--postinstall",
        action="store",
        default=None,
        help="Optional postinstall script to include in the output pkg",
    )
    p.add_argument(
        "-r",
        "--resource-addition",
        action="store",
        default=None,
        help="Optional add additional file to scripts directory for use by postinstall script"  
    )
    p.add_argument(
        "-s",
        "--sign-package",
        action="store",
        default=None,
        help="Optional sign the munki distribution package with a "
        "Developer ID Installer certificate from keychain. Provide "
        "the certificate's Common Name. e.g.: "
        "'Developer ID Installer: Munki (U8PN57A5N2)'",
    ),
    p.add_argument(
        "-S",
        "--sign-binaries",
        action="store",
        default=None,
        help="Optionally sign the munki app binaries with a "
        "Developer ID Application certificate from keychain. "
        "Provide the certificate's Common Name. e.g.: "
        "'Developer ID Application  Munki (U8PN57A5N2)'",
    ),
    p.add_argument("-v", "--verbose", action="store_true", help="Be more verbose"),
    p.add_argument(
        "-x", "--version", action="store_true", help="Print version and exit"
    )
    args = p.parse_args()
    if not args.version and not args.appname:
        p.error("-a or --appname is required")

    if args.version:
        print(VERSION)
        sys.exit(0)

    if os.geteuid() != 0:
        print(
            "You must run this script as root in order to build your new "
            "munki installer pkg!"
        )
        sys.exit(1)

    global verbose
    verbose = args.verbose
    outfilename = args.output_file or "munkitools"

    # Look for actool
    actool = next((x for x in ACTOOL if os.path.isfile(x)), None)
    if not actool:
        print(
            "WARNING: actool not found. Icon file will not be replaced in "
            "Munki 3.6 and higher. See README for more info."
        )

    if args.icon_file and os.path.isfile(args.icon_file):
        if icon_test(args.icon_file):
            # Attempt to convert png to icns
            print("Converting .png file to .icns...")
            icns, car = convert_to_icns(args.icon_file, tmp_dir, actool=actool)
        else:
            print("ERROR: icon file must be a 1024x1024 .png")
            sys.exit(1)

    output = os.path.join(tmp_dir, "munkitools.pkg")

    if not args.pkg:
        download_pkg(get_latest_munki_url(), output)
        args.pkg = output

    if args.pkg and args.pkg.startswith("http"):
        download_pkg(args.pkg, output)
        args.pkg = output

    if args.pkg and os.path.isfile(args.pkg):
        pkg_id_prefix = args.identifier
        root_dir = os.path.join(tmp_dir, "root")
        expand_pkg(args.pkg, root_dir)

        # Grab just the first match of this glob to get the app pkg regardless
        # of version number
        app_pkg = glob.glob(os.path.join(root_dir, "munkitools_app[-.]*"))[0]
        core_pkg = glob.glob(os.path.join(root_dir, "munkitools_core[-.]*"))[0]
        python_pkg = glob.glob(os.path.join(root_dir, "munkitools_python[-.]*"))[0]

        # Get our munkitools version from existing Distribution file
        # (will be same as munki core)
        distfile = os.path.join(root_dir, "Distribution")
        tree = ET.parse(distfile)
        r = tree.getroot()
        # Grab the first pkg-ref element (the one with the version)
        pkgref = r.findall(f"pkg-ref[@id='{pkg_id_prefix}.app']")[0]
        app_version = pkgref.attrib["version"]
        product = r.findall(f"product[@id='{pkg_id_prefix}']")[0]
        munki_version = product.attrib["version"]

        app_scripts = os.path.join(app_pkg, "Scripts")
        app_payload = os.path.join(app_pkg, "Payload")
        core_payload = os.path.join(core_pkg, "Payload")
        python_payload = os.path.join(python_pkg, "Payload")

        if args.postinstall and os.path.isfile(args.postinstall):
            dest = os.path.join(app_scripts, "postinstall")
            print(f"Copying postinstall script {args.postinstall} to {dest}...")
            shutil.copyfile(args.postinstall, dest)
            print(f"Making {dest} executable...")
            os.chmod(dest, 0o755)

        if args.resource_addition and os.path.isfile(args.resource_addition):
            destination = app_scripts
            source = args.resource_addition
            print(f"Adding additional resource {source} to {destination}...")
            try:
                shutil.copy(source, destination)
            except shutil.SameFileError:
                print("Source and destination represents the same file.")
            # If there is any permission issue
            except PermissionError:
                print("Permission denied.")
            # For other errors
            except:
                print("Error occurred while copying file.")


        # Find the lproj directories in the apps' Resources dirs
        print(f"Replacing app name with {args.appname}...")
        for app in APPS:
            app_dir = os.path.join(app_payload, app["path"])
            resources_dir = os.path.join(app_dir, "Contents/Resources")
            # Get a list of all the lproj dirs in each app's Resources dir
            lproj_dirs = glob.glob(os.path.join(resources_dir, "*.lproj"))
            for lproj_dir in lproj_dirs:
                # Determine lang code
                code = os.path.basename(lproj_dir).split(".")[0]
                # Don't try to change anything we don't know about
                if code in list(APPNAME_LOCALIZED.keys()):
                    for root, dirs, files in os.walk(lproj_dir):
                        for file_ in files:
                            lfile = os.path.join(root, file_)
                            if fnmatch.fnmatch(lfile, "*.strings"):
                                replace_strings(lfile, code, args.appname)
            if args.icon_file:
                if icns:
                    for icon in app["icon"]:
                        if os.path.isfile(
                            os.path.join(
                                app_payload,
                                os.path.join(app["path"], "Contents/Resources", icon),
                            )
                        ):
                            found_icon = icon
                            break
                    icon_path = os.path.join(
                        app["path"], "Contents/Resources", found_icon
                    )
                    dest = os.path.join(app_payload, icon_path)
                    print(f"Replacing icons in {dest} with {args.icon_file}...")
                    shutil.copyfile(args.icon_file, dest)
                if car:
                    car_path = os.path.join(
                        app["path"], "Contents/Resources", "Assets.car"
                    )
                    dest = os.path.join(app_payload, car_path)
                    if os.path.isfile(dest):
                        shutil.copyfile(car, dest)
                        print(f"Replacing icons in {dest} with {car}...")

        # Set root:admin throughout payload
        for root, dirs, files in os.walk(root_dir):
            for dir_ in dirs:
                os.chown(os.path.join(root, dir_), 0, 80)
            for file_ in files:
                os.chown(os.path.join(root, file_), 0, 80)

        if args.sign_binaries:
            # Generate entitlements file for later
            entitlements = {
                "com.apple.security.cs.allow-unsigned-executable-memory": True
            }
            ent_file = os.path.join(tmp_dir, "entitlements.plist")
            with open(ent_file, "wb") as f:
                plistlib.dump(entitlements, f)

            # Add the MSC app pkg binaries
            binaries = [
                os.path.join(
                    app_payload,
                    MSC_APP["path"],
                    "Contents/PlugIns/MSCDockTilePlugin.docktileplugin",
                ),
                os.path.join(
                    app_payload,
                    MSC_APP["path"],
                    "Contents/Helpers/munki-notifier.app",
                ),
                os.path.join(app_payload, MS_APP["path"]),
                os.path.join(app_payload, MSC_APP["path"]),
            ]
            # In munki 5.3 and higher, managedsoftwareupdate is a signable binary
            # wrapper to allow for changes to PPPC in Ventura. We don't want to sign it if 
            # it's just the python script in earlier versions.
            msu = os.path.join(
                    core_payload,
                    MUNKI_PATH,
                    "managedsoftwareupdate",
                )
            if is_binary(msu):
                binaries.append(msu)

            # Add the executable libs and bins in python pkg
            pylib = os.path.join(python_payload, PY_CUR, "lib")
            pybin = os.path.join(python_payload, PY_CUR, "bin")
            for pydir in pylib, pybin:
                binaries.extend(
                    [
                        os.path.join(pydir, f)
                        for f in os.listdir(pydir)
                        if is_signable_bin(os.path.join(pydir, f))
                    ]
                )
                for root, dirs, files in os.walk(pydir):
                    for file_ in files:
                        if is_signable_lib(os.path.join(root, file_)):
                            binaries.append(os.path.join(root, file_))

            # Add binaries which need entitlements
            entitled_binaries = [
                os.path.join(python_payload, PY_CUR, "Resources/Python.app"),
                os.path.join(pybin, "python3"),
            ]

            # Sign all the binaries. The order is important. Which is why this is a bit
            # gross
            print("Signing binaries (this may take a while)...")
            for binary in binaries:
                if verbose:
                    print(f"Signing {binary}...")
                sign_binary(
                    args.sign_binaries,
                    binary,
                    deep=True,
                    force=True,
                    options=["runtime"],
                )
            for binary in entitled_binaries:
                if verbose:
                    print(f"Signing {binary} with entitlements from {ent_file}...")
                sign_binary(
                    args.sign_binaries,
                    binary,
                    deep=True,
                    force=True,
                    options=["runtime"],
                    entitlements=ent_file,
                )
            # Finally sign python framework
            py_fwkpath = os.path.join(python_payload, PY_FWK)
            if verbose:
                print(f"Signing {py_fwkpath}...")
            sign_binary(args.sign_binaries, py_fwkpath, deep=True, force=True)

        final_pkg = os.path.join(os.getcwd(), f"{outfilename}-{munki_version}.pkg")
        print(f"Building output pkg at {final_pkg}...")
        flatten_pkg(root_dir, final_pkg)
        if args.sign_package:
            sign_package(args.sign_package, final_pkg)

    else:
        print(f"Could not find munkitools pkg {args.pkg}.")


if __name__ == "__main__":
    main()
