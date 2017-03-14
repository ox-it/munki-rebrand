#!/usr/bin/python
# encoding: utf-8
'''
munki_rebrand.py

Script to rebrand and customise Munki's Managed Software Center

Copyright (C) University of Oxford 2016
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
'''

from subprocess import Popen, PIPE
from os import listdir, stat, chmod, geteuid, mkdir, rename, getcwd
from os.path import join, isfile, isdir
from distutils.dir_util import copy_tree
from shutil import copyfile, rmtree
from tempfile import mkdtemp
import fileinput
import argparse
import sys
import re
import atexit

MUNKI_GITHUB = 'https://github.com/munki/munki'

MUNKI_MAKESCRIPT = 'code/tools/make_munki_mpkg.sh'

MUNKI_MAKESCRIPT_DEP = 'code/tools/make_munki_mpkg_DEP.sh'

APPNAME_ORIG = 'Managed Software Center'

APPNAME_ORIG_LOCALIZED = {
    'da': 'Managed Software Center',
    'de': 'Geführte Softwareaktualisierung',
    'en': 'Managed Software Center',
    'en_AU': 'Managed Software Centre',
    'en_GB': 'Managed Software Centre',
    'en_CA': 'Managed Software Centre',
    'es': 'Centro de aplicaciones',
    'fi': 'Managed Software Center',
    'fr': 'Centre de gestion des logiciels',
    'it': 'Centro Gestione Applicazioni',
    'ja': 'Managed Software Center',
    'nb': 'Managed Software Center',
    'nl': 'Managed Software Center',
    'ru': 'Центр Управления ПО',
    'sv': 'Managed Software Center'
}

APP_DIRS = {
    'MSC_DIR': 'code/apps/Managed Software Center/Managed Software Center',
    'MN_DIR': 'code/apps/munki-notifier/munki-notifier',
    'MS_DIR': 'code/apps/MunkiStatus/MunkiStatus'
}

APP_FILES = [
    '%s/en.lproj/MainMenu.xib' % APP_DIRS['MSC_DIR'],
    '%s/MSCMainWindowController.py' % APP_DIRS['MSC_DIR'],
    '%s/en.lproj/MainMenu.xib' % APP_DIRS['MN_DIR'],
    '%s/en.lproj/MainMenu.xib' % APP_DIRS['MS_DIR']
]

LOCALIZED_FILES = [
    'InfoPlist.strings',
    'Localizable.strings',
    'MainMenu.strings'
]

ICON_SIZES = [('16', '16x16'), ('32', '16x16@2x'),
              ('32', '32x32'), ('64', '32x32@2x'),
              ('128', '128x128'), ('256', '128x128@2x'),
              ('256', '256x256'), ('512', '256x256@2x'),
              ('512', '512x512'), ('1024', '512x512@2x')]

tmp_dir = mkdtemp()


@atexit.register
def cleanup():
    print "Cleaning up..."
    try:
        rmtree(tmp_dir)
    # In case subprocess cleans up before we do
    except OSError:
        pass
    print "Done."


def run_cmd(cmd, retgrep=None, verbose=False):
    ''' Runs a command passed in as a list. Can also be provided with a regex
    to search for in the output, returning the result'''
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    output = out
    if verbose:
        print out
    if proc.returncode is not 0:
        print err
        sys.exit(1)
    if retgrep:
        ret = re.search(retgrep, output)
        return ret


def find_replace(find, replace, files, verbose=False):
    ''' Finds instances of `find` string and replaces with `replace` string
    in `files`'''
    if verbose:
        print "Replacing %s with %s in %s" % (find, replace, files)
    for line in fileinput.input(files, inplace=True):
        print line.replace(find, replace)


def convert_to_icns(png, verbose=False):
    '''Takes a png file and attempts to convert it to an icns set'''
    iconset = join(tmp_dir, 'AppIcns.iconset')
    mkdir(iconset)
    for hw, suffix in ICON_SIZES:
        cmd = ['sips', '-z', hw, hw, png,
               '--out', join(iconset, 'icon_%s.png' % suffix)]
        run_cmd(cmd, verbose=verbose)
    icns = join(tmp_dir, 'AppIcns.icns')
    cmd = ['iconutil', '-c', 'icns', iconset,
           '-o', icns]
    run_cmd(cmd, verbose=verbose)
    return icns


def main():
    if geteuid() != 0:
        print "You must run this script as root in order to build your new " \
              "munki installer pkg!"
        sys.exit(1)

    p = argparse.ArgumentParser(description="Rebrands Munki's Managed Software "
                                "Center - gives the app a new name in Finder, "
                                "and can also modify its icon. N.B. You will "
                                "need Xcode and its command-line tools "
                                "installed to run this script successfully.")

    p.add_argument('-a', '--appname', action='store',
                   required=True,
                   help="Your desired app name for Managed Software "
                   "Center.")
    p.add_argument('-c', '--local-code', action='store',
                   default=None,
                   help="Use a local copy of a munki code repo rather than "
                   "cloning from GitHub. Provide the complete path e.g. "
                   "/Users/Shared/my_munki_fork/")
    p.add_argument('-d', '--dep', action='store_true',
                   default=None,
                   help="Build munki for DEP and other situations in which you "
                   "do not wish to force a reboot after munki is installed")
    p.add_argument('-i', '--icon-file', action='store',
                   default=None,
                   help="Optional icon file to replace Managed Software "
                   "Center's. Can be a .icns file or a 1024x1024 .png with "
                   "alpha channel, in which case it will be converted to an "
                   ".icns")
    p.add_argument('-l', '--localized', action='store_true',
                   help="Change localized versions of Managed Software Center "
                   "to your desired app name. You probably want this if you "
                   "envisage users using any other language than en_US")
    p.add_argument('-o', '--output-file', action='store',
                   default=None,
                   help="Optional base name for the customized pkg "
                   "outputted by this tool")
    p.add_argument('-p', '--postinstall', action='store',
                   default=None,
                   help="Optional postinstall script to include in the output "
                   "pkg")
    p.add_argument('-r', '--munki-release', action='store',
                   default=None,
                   help="Optional tag to download a specific release of munki "
                   "e.g. 'v2.8.2'. Leave blank for latest Github code")
    p.add_argument('-s', '--sign-package', action='store',
                   default=None,
                   help="Optional sign the munki distribution package with a "
                   "Developer ID Installer certificate from keychain. Provide "
                   "the certificate's Common Name. Ex: "
                   "'Developer ID Installer: Munki (U8PN57A5N2)'")
    p.add_argument('-v', '--verbose', action='store_true',
                   help="Be more verbose")
    args = p.parse_args()

    # Some pre-checks
    precheck_errors = []
    if args.icon_file and not isfile(args.icon_file):
        precheck_errors.append(
            'Icon file %s does not exist' % args.icon_file)
    if args.postinstall and not isfile(args.postinstall):
        precheck_errors.append(
            'postinstall script %s does not exist.' % args.postinstall)
    if args.local_code and not isdir(args.local_code):
        precheck_errors.append(
            'local code directory %s does not exist.' % args.local_code)
    if args.local_code and args.munki_release:
        precheck_errors.append(
            'cannot set both --local-code and --munki-release')
    if precheck_errors:
        for error in precheck_errors:
            print error
            sys.exit(1)

    if not args.local_code:
        # Clone git repo
        print "Cloning git repo..."
        cmd = ['git', 'clone', MUNKI_GITHUB, tmp_dir]
        run_cmd(cmd, verbose=args.verbose)

        # Checkout MUNKI_RELEASE if set
        if args.munki_release:
            print 'Checking out tag %s' % args.munki_release
            cmd = ['git', '-C', tmp_dir, 'checkout',
                   'tags/%s' % args.munki_release]
            run_cmd(cmd, verbose=args.verbose)
        else:
            print "Using latest Github code..."
    else:
        print "Copying local munki code to temp directory..."
        copy_tree(args.local_code, tmp_dir)

    # Patch non-localized names
    print "Replacing %s with %s in apps..." % (APPNAME_ORIG,
                                               args.appname)
    app_files = [join(tmp_dir, app_file) for app_file in APP_FILES]
    find_replace(APPNAME_ORIG, args.appname, app_files, verbose=args.verbose)

    # Patch localized names
    if args.localized:
        print "Replacing localized app names with %s..." % args.appname
        for app_dir in APP_DIRS.values():
            ls = [name for name in listdir(join(tmp_dir, app_dir)) if isdir(
                join(tmp_dir, app_dir, name))]
            for lproj_dir in ls:
                for code, local_name in APPNAME_ORIG_LOCALIZED.iteritems():
                    if lproj_dir.endswith('%s.lproj' % code):
                        for lfile in LOCALIZED_FILES:
                            lfile = join(tmp_dir, app_dir, lproj_dir, lfile)
                            if isfile(lfile):
                                find_replace(APPNAME_ORIG,
                                             args.appname,
                                             lfile,
                                             verbose=args.verbose)
                                find_replace(local_name,
                                             args.appname,
                                             lfile,
                                             verbose=args.verbose)

    if args.icon_file:
        # Copy icon files to correct destinations
        if args.icon_file.endswith('.png'):
            # Attempt to convert png to icns
            print "Converting .png file to .icns..."
            args.icon_file = convert_to_icns(
                args.icon_file, verbose=args.verbose)
        print "Replacing icons with %s..." % args.icon_file
        for dest in [join(tmp_dir,
                          '%s/Managed Software Center.icns'
                          % APP_DIRS['MSC_DIR']),
                     join(tmp_dir,
                          '%s/MunkiStatus.icns'
                          % APP_DIRS['MS_DIR'])]:
            copyfile(args.icon_file, dest)

    if args.postinstall:
        # Copy postinstall to correct destination
        print "Adding postinstall script: %s..." % args.postinstall
        dest = join(tmp_dir, 'code/pkgtemplate/Scripts_app/postinstall')
        copyfile(args.postinstall, dest)
        st = stat(dest)
        chmod(dest, (st.st_mode | 0111))

    # Run the munki build script on the customized files
    print "Building customized Munki..."
    if args.dep:
        print "Using DEP makescript..."
        makescript = MUNKI_MAKESCRIPT_DEP
    else:
        makescript = MUNKI_MAKESCRIPT

    # Run the makescript with -s if optionally passed
    if not args.sign_package:
        cmd = [join(tmp_dir, makescript),
               '-r', tmp_dir,
               '-o', tmp_dir]
    else:
        cmd = [join(tmp_dir, makescript),
               '-r', tmp_dir,
               '-s', args.sign_package,
               '-o', tmp_dir]
    group = run_cmd(
        cmd,
        retgrep='Distribution.*(?P<munki_pkg>munkitools.*pkg).',
        verbose=args.verbose)
    munki_pkg = group.groupdict()['munki_pkg']

    if args.output_file:
        # Rename the pkg to whatever is in args.outfile
        print "Renaming customized pkg..."
        out_pkg = re.sub('munkitools', args.output_file, munki_pkg)
        rename(join(tmp_dir, munki_pkg), join(tmp_dir, out_pkg))
        munki_pkg = out_pkg

    out_dir = getcwd()
    copyfile(join(tmp_dir, munki_pkg), join(out_dir, munki_pkg))
    print "Customized package built at %s." % join(out_dir, munki_pkg)

    sys.exit(0)

if __name__ == '__main__':
    main()
