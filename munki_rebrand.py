#!/usr/bin/python
# encoding: utf-8
"""
munki_rebrand.py

Script to rebrand and customise Munki's Managed Software Center

Copyright (C) University of Oxford 2016-17
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
from subprocess import Popen, PIPE
import os
import shutil
from tempfile import mkdtemp
from xml.etree import ElementTree as ET
import plistlib
import argparse
import sys
import re
import atexit
import glob
import fnmatch
import io
import json

APPNAME = 'Managed Software Center'

APPNAME_LOCALIZED = {
    'da': u'Managed Software Center',
    'de': u'Geführte Softwareaktualisierung',
    'en': u'Managed Software Center',
    'en_AU': u'Managed Software Centre',
    'en_GB': u'Managed Software Centre',
    'en_CA': u'Managed Software Centre',
    'es': u'Centro de aplicaciones',
    'fi': u'Managed Software Center',
    'fr': u'Centre de gestion des logiciels',
    'it': u'Centro Gestione Applicazioni',
    'ja': u'Managed Software Center',
    'nb': u'Managed Software Center',
    'nl': u'Managed Software Center',
    'ru': u'Центр Управления ПО',
    'sv': u'Managed Software Center'
}

MSC_APP = {'path': 'Applications/Managed Software Center.app/Contents/Resources',
           'icon': 'Managed Software Center.icns'}
MS_APP = {'path': os.path.join(MSC_APP['path'], 'MunkiStatus.app/Contents/Resources'),
          'icon': 'MunkiStatus.icns'}

APPS = [ MSC_APP, MS_APP ]

ICON_SIZES = [('16', '16x16'), ('32', '16x16@2x'),
              ('32', '32x32'), ('64', '32x32@2x'),
              ('128', '128x128'), ('256', '128x128@2x'),
              ('256', '256x256'), ('512', '256x256@2x'),
              ('512', '512x512'), ('1024', '512x512@2x')]

PKGBUILD = '/usr/bin/pkgbuild'
PKGUTIL = '/usr/sbin/pkgutil'
PRODUCTBUILD = '/usr/bin/productbuild'
PRODUCTSIGN = '/usr/bin/productsign'
DITTO = '/usr/bin/ditto'
PLUTIL = '/usr/bin/plutil'
SIPS = '/usr/bin/sips'
ICONUTIL = '/usr/bin/iconutil'
CURL = '/usr/bin/curl'

MUNKIURL = 'https://api.github.com/repos/munki/munki/releases/latest'

global verbose
verbose = False
tmp_dir = mkdtemp()

@atexit.register
def cleanup():
    print "Cleaning up..."
    try:
        shutil.rmtree(tmp_dir)
    # In case subprocess cleans up before we do
    except OSError:
        pass
    print "Done."


def run_cmd(cmd, ret=None):
    '''Runs a command passed in as a list. Can also be provided with a regex
    to search for in the output, returning the result'''
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    output = out
    if verbose and out != '':
        print out.rstrip()
    if proc.returncode is not 0:
        print err
        sys.exit(1)
    if ret:
        return output


def get_latest_munki_url():
    cmd = [CURL, MUNKIURL]
    j = run_cmd(cmd, ret=True)
    api_result = json.loads(j)
    return api_result['assets'][0]['browser_download_url']

def download_pkg(url, output):
    print "Downloading munkitools from %s..." % url
    cmd = [CURL,
           '--location',
           '--output', output,
           url]
    run_cmd(cmd)


def flatten_pkg(directory, pkg):
    '''Flattens a pkg folder'''
    cmd = [PKGUTIL, '--flatten', directory, pkg]
    run_cmd(cmd)


def expand_pkg(pkg, directory):
    '''Expands a flat pkg to a folder'''
    cmd = [PKGUTIL, '--expand', pkg, directory]
    run_cmd(cmd)


def expand_payload(payload, directory):
    '''Expands a pkg payload to a directory'''
    cmd = [DITTO]
    # Ditto verbose is to stderr :(
    #if verbose:
    #    cmd.extend(['-v'])
    cmd.extend(['-x', payload, directory])
    run_cmd(cmd)


def analyze(pkgroot, plist):
    '''Analyzes a pkgroot to create a component plist'''
    cmd = [PKGBUILD, '--analyze', '--root', pkgroot, plist]
    run_cmd(cmd)


def make_unrelocatable(plist):
    '''Changes BundleIsRelocatable in component plist to false'''
    p = plistlib.readPlist(plist)
    p[0]['BundleIsRelocatable'] = False
    plistlib.writePlist(p, plist)


def pkgbuild(pkgroot, plist, identifier, script_dir, output_path):
    '''Uses a component plist to build a component pkg'''
    cmd = [PKGBUILD,
           '--root', pkgroot,
           '--component-plist', plist,
           '--identifier', identifier,
           '--scripts', script_dir,
           output_path]
    run_cmd(cmd)


def productbuild(distribution, pkg_path, output_path):
    '''Builds a product pkg from a product root and distribution file'''
    cmd = [PRODUCTBUILD,
           '--distribution', distribution,
           '--package-path', pkg_path,
           output_path]
    run_cmd(cmd)


def plist_to_xml(plist):
    '''Converts plist file to xml1 format'''
    cmd = [PLUTIL, '-convert', 'xml1', plist]
    run_cmd(cmd)


def plist_to_binary(plist):
    '''Converts plist file to binary1 format'''
    cmd = [PLUTIL, '-convert', 'binary1', plist]
    run_cmd(cmd)


def replace_strings(strings_file, code, appname):
    '''Replaces localized app name in a .strings file with desired app name'''
    localized = APPNAME_LOCALIZED[code]
    if verbose:
        print "Replacing \'%s\' in %s with \'%s\'..." % (localized,
                                                         strings_file,
                                                         appname)
    backup_file = '%s.bak' % strings_file
    with io.open(backup_file, 'w', encoding='utf-16') as fw, \
         io.open(strings_file, 'r', encoding='utf-16') as fr:
        for line in fr:
            # We want to only replace on the right hand side of any =
            # and we don't want to do it to a comment
            if '=' in line and not line.startswith('/*'):
                left, right = line.split('=')
                right = right.replace(localized, appname)
                line = '='.join([left, right])
            fw.write(line)
    os.remove(strings_file)
    os.rename(backup_file, strings_file)


def replace_nib(nib_file, code, appname):
    '''Replaces localized app name in a .nib file with desired app name'''
    localized = APPNAME_LOCALIZED[code]
    if verbose:
        print "Replacing \'%s\' in %s with \'%s\'..." % (localized,
                                                         nib_file,
                                                         appname)
    backup_file = '%s.bak' % nib_file
    plist_to_xml(nib_file)
    with io.open(backup_file, 'w', encoding='utf-8') as fw,  io.open(nib_file, 'r', encoding='utf-8') as fr:
        for line in fr:
            # Simpler than mucking about with plistlib
            line = line.replace(localized, appname)
            fw.write(line)
    os.remove(nib_file)
    os.rename(backup_file, nib_file)
    plist_to_binary(nib_file)


def convert_to_icns(png, output_dir):
    '''Takes a png file and attempts to convert it to an icns set'''
    iconset = os.path.join(output_dir, 'AppIcns.iconset')
    os.mkdir(iconset)
    for hw, suffix in ICON_SIZES:
        cmd = [SIPS, '-z', hw, hw, png,
               '--out', os.path.join(iconset, 'icon_%s.png' % suffix)]
        run_cmd(cmd)
    icns = os.path.join(output_dir, 'AppIcns.icns')
    cmd = [ICONUTIL, '-c', 'icns', iconset,
           '-o', icns]
    run_cmd(cmd)
    return icns


def sign_package(signing_id, pkg):
    '''Signs a pkg with a signing id'''
    cmd = [PRODUCTSIGN,
           '--sign', signing_id,
           pkg,
           '%s-signed' % pkg]
    run_cmd(cmd)
    print "Moving %s-signed to %s..." % (pkg, pkg)
    os.rename('%s-signed' % pkg, pkg)


def main():
    p = argparse.ArgumentParser(description="Rebrands Munki's Managed Software "
                                "Center - gives the app a new name in Finder, "
                                "and can also modify its icon. N.B. You will "
                                "need Xcode and its command-line tools "
                                "installed to run this script successfully.")

    p.add_argument('-a', '--appname', action='store',
                   required=True,
                   help="Your desired app name for Managed Software "
                   "Center."),
    p.add_argument('-k', '--pkg', action='store',
                   help="Prebuilt munkitools pkg to rebrand."),
    p.add_argument('-i', '--icon-file', action='store',
                   default=None,
                   help="Optional icon file to replace Managed Software "
                   "Center's. Can be a .icns file or a 1024x1024 .png with "
                   "alpha channel, in which case it will be converted to an "
                   ".icns")
    p.add_argument('-o', '--output-file', action='store',
                   default=None,
                   help="Optional base name for the customized pkg "
                   "outputted by this tool")
    p.add_argument('-p', '--postinstall', action='store',
                   default=None,
                   help="Optional postinstall script to include in the output "
                   "pkg")
    p.add_argument('-s', '--sign-package', action='store',
                   default=None,
                   help="Optional sign the munki distribution package with a "
                   "Developer ID Installer certificate from keychain. Provide "
                   "the certificate's Common Name. Ex: "
                   "'Developer ID Installer: Munki (U8PN57A5N2)'")
    p.add_argument('-v', '--verbose', action='store_true',
                   help="Be more verbose")
    args = p.parse_args()

    if os.geteuid() != 0:
        print "You must run this script as root in order to build your new " \
              "munki installer pkg!"
        sys.exit(1)

    verbose = args.verbose
    outfilename = args.output_file or "munkitools"

    if args.icon_file and os.path.isfile(args.icon_file):
        if fnmatch.fnmatch(args.icon_file, '*.png'):
            # Attempt to convert png to icns
            print "Converting .png file to .icns..."
            args.icon_file = convert_to_icns(args.icon_file,
                                             tmp_dir)
    output = os.path.join(tmp_dir, 'munkitools.pkg')


    if not args.pkg:
        download_pkg(get_latest_munki_url(), output)
        args.pkg = output

    if args.pkg and args.pkg.startswith('http'):
        download_pkg(args.pkg, output)
        args.pkg = output

    if args.pkg and os.path.isfile(args.pkg):
        root_dir = os.path.join(tmp_dir, 'root')

        # Temporary directory for the app pkg scripts to reside
        scripts_dir = os.path.join(tmp_dir, 'scripts')
        expand_pkg(args.pkg, root_dir)

        # Grab just the first match of this glob to get the app pkg regardless
        # of version number
        app_pkg = glob.glob(os.path.join(root_dir, 'munkitools_app-*'))[0]

        # Get our munkitools version from existing Distribution file
        # (will be same as munki core)
        distfile = os.path.join(root_dir, 'Distribution')
        tree = ET.parse(distfile)
        r = tree.getroot()
        # Grab the first pkg-ref element (the one with the version)
        pkgref = r.findall("pkg-ref[@id='com.googlecode.munki.core']")[0]
        munki_version = pkgref.attrib['version']

        # Unpack the app pkg payload
        payload_file = os.path.join(app_pkg, 'Payload')
        app_scripts = os.path.join(app_pkg, 'Scripts')
        app_payload = os.path.join(tmp_dir, 'payload')
        os.mkdir(app_payload)
        expand_payload(payload_file, app_payload)
        # Preserve scripts
        shutil.copytree(app_scripts, scripts_dir)
        # Copy postinstall to scripts directory
        if args.postinstall and os.path.isfile(args.postinstall):
            dest = os.path.join(scripts_dir, 'postinstall')
            print "Copying postinstall script %s to %s..." % (args.postinstall,
                                                              dest)
            shutil.copyfile(args.postinstall, dest)
            print "Making %s executable..." % dest
            os.chmod(dest, 0755)
        # Delete the old expanded pkg
        shutil.rmtree(app_pkg)

        # Find the lproj directories in the apps' Resources dirs
        for app in APPS:
            resources_dir = os.path.join(app_payload, app['path'])
            # Get a list of all the lproj dirs in each app's Resources dir
            lproj_dirs = glob.glob(os.path.join(resources_dir, '*.lproj'))
            for lproj_dir in lproj_dirs:
                # Determine lang code
                code = os.path.basename(lproj_dir).split('.')[0]
                # Don't try to change anything we don't know about
                if code in APPNAME_LOCALIZED.keys():
                    for root, dirs, files in os.walk(lproj_dir):
                        for file_ in files:
                            lfile = os.path.join(root, file_)
                            if fnmatch.fnmatch(lfile, '*.strings'):
                                replace_strings(lfile, code, args.appname)
                            if fnmatch.fnmatch(lfile, '*.nib'):
                                replace_nib(lfile, code, args.appname)
            if args.icon_file:
                icon_path = os.path.join(app['path'], app['icon'])
                dest = os.path.join(app_payload, icon_path)
                print "Replacing icons with %s in %s..." % (args.icon_file, dest)
                shutil.copyfile(args.icon_file, dest)

        # Make a new root for the distribution product
        newroot = os.path.join(tmp_dir, 'newroot')
        os.mkdir(newroot)

        # Set root:admin throughout payload
        for root, dirs, files in os.walk(app_payload):
            for dir_ in dirs:
                os.chown(os.path.join(root, dir_), 0, 80)
            for file_ in files:
                os.chown(os.path.join(root, file_), 0, 80)
        component_plist = os.path.join(tmp_dir, 'component.plist')
        analyze(app_payload, component_plist)
        make_unrelocatable(component_plist)
        # Create app pkg in the newroot
        output_pkg = os.path.join(newroot, os.path.basename(app_pkg))
        pkgbuild(app_payload,
                 component_plist,
                 'com.googlecode.munki.app',
                 scripts_dir,
                 output_pkg)
        # Flatten the other pkgs into newroot
        for pkg in glob.glob(os.path.join(root_dir, '*.pkg')):
            flatten_pkg(pkg, os.path.join(newroot, os.path.basename(pkg)))
        # Now build new distribution product using old dist file
        final_pkg = os.path.join(os.getcwd(),
                                 '%s-%s.pkg' % (outfilename, munki_version))
        print "Building output pkg at %s..." % final_pkg
        productbuild(distfile,
                     newroot,
                     final_pkg)

        if args.sign_package:
            sign_package(args.sign_package, final_pkg)

    else:
        print "Could not find munkitools pkg %s." % args.pkg

if __name__ == '__main__':
    main()
