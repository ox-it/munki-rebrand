#!/usr/bin/python
# -*- coding: utf-8 -*-

# Arjen van Bochoven Oct 2014
# Script to rebrand/customize Managed Software Center
#
# Customised for University of Oxford by
# Ben Goodstein Mar 2015
#
# Prerequisites: You need Xcode (5/6) installed
# For Xcode 6 you need to add the 10.8 SDK
# See: https://github.com/munki/munki/wiki/Building%20Munki2%20Pkgs
#
# Put this script in an *empty* directory
# and make it executable
#
# Set appNameWanted to your preferred name
# Add an optional AppIcon.icons file
# Add an optional postinstall_script
#
# Then run ./munki_rebrand.py
#
# ! Caveat: this is a very rudimentary script that is likely
# to break in future MSC releases. Use at your own risk

import fileinput
import subprocess
import re
from os import listdir, stat, chmod
from os.path import isfile, join
from shutil import copyfile

# Desired new app name
appNameWanted = 'Orchard Software Centre'

# Optional icon file to replace the MSC icon
srcIcon = 'AppIcon.icns'

# Optional postinstall script to be executed upon install
postinstall_script = 'postinstall_script'

# Git release tag (leave empty for latest build)
tag = 'v2.2.4'

### Probably don't need to edit below this line

# App name requiring replacement
appNameOriginal = 'Managed Software Center'

# Localized forms of app name
appNameLocalized = {    'da'       : 'Managed Software Center',
                                'de'       : 'Geführte Softwareaktualisierung',
                                'en'       : 'Managed Software Center',
                                'en_AU'  : 'Managed Software Centre',
                                'en_GB'  : 'Managed Software Centre',
                                'en_CA'  : 'Managed Software Centre',
                                'es'       : 'Centro de aplicaciones',
                                'fi'       : 'Managed Software Center',
                                'fr'       : 'Centre de gestion des logiciels',
                                'it'       : 'Centro Gestione Applicazioni',
                                'ja'       : 'Managed Software Center,
                                'nb'       : 'Managed Software Center',
                                'nl'       : 'Managed Software Center',
                                'ru'       : 'Центр Управления ПО',
                                'sv'       : 'Managed Software Center'
                            }

# Git repo
git_repo = "https://github.com/munki/munki"

# Make Munki pkg script
make_munki = 'munki/code/tools/make_munki_mpkg.sh'

# First cleanup previous runs
print 'Cleaning up previous runs'
proc = subprocess.Popen(['sudo','/bin/rm','-rf', 'munki'])
proc.communicate()

# Checkout git repo
print 'Cloning git repo'
proc = subprocess.Popen(['git','clone', git_repo])
proc.communicate()

if tag:
      print 'Checkout tag %s' % tag
      proc = subprocess.Popen(['git','-C', 'munki', 'checkout', 'tags/%s' % tag])
      proc.communicate()

# Replace in required files

print 'Replacing %s with %s' % (appNameOriginal, appNameWanted)

replaceList = ['InfoPlist.strings', 'Localizable.strings', 'MainMenu.strings']

appDirs = ['munki/code/apps/Managed Software Center/Managed Software Center','munki/code/apps/MunkiStatus/MunkiStatus']

def searchReplace(search, replace, fileToSearch):
      if isfile(fileToSearch):
            try:
                for line in fileinput.input(fileToSearch, inplace=True):
                      print(re.sub(search, replace, line)),
            except Exception, e:
                print "Error replacing in %s" % fileToSearch

for appDir in appDirs:
      
      if isfile(join(appDir, 'en.lproj/MainMenu.xib')):
            searchReplace(appNameOriginal, appNameWanted, join(appDir, 'en.lproj/MainMenu.xib'))
      if isfile(join(appDir, 'MSCMainWindowController.py')):
            searchReplace(appNameOriginal, appNameWanted, join(appDir, 'MSCMainWindowController.py'))
      
      for f in listdir(appDir):
            for countryCode, localizedName in appNameLocalized.iteritems():
                if f.endswith('%s.lproj' % countryCode):
                      for i in replaceList:
                            fileToSearch = join(appDir, f, i)
                            if isfile(fileToSearch):
                                # Replaces all instances of original app name
                                searchReplace(appNameOriginal, appNameWanted, fileToSearch)
                                # Matches based on localized app name
                                searchReplace(localizedName, appNameWanted, fileToSearch)

# Copy icons
if isfile(srcIcon):
      print("Replace icons with %s" % srcIcon)
      destIcon = "munki/code/apps/Managed Software Center/Managed Software Center/Managed Software Center.icns"
      copyfile(srcIcon, destIcon)
      destIcon = "munki/code/apps/MunkiStatus/MunkiStatus/MunkiStatus.icns"
      copyfile(srcIcon, destIcon)

      print("Add postinstall script: %s" % postinstall_script)
      postinstall_dest = "munki/code/pkgtemplate/Scripts_app/postinstall"
      copyfile(postinstall_script, postinstall_dest)
      # Set execute bit
      st = stat(postinstall_dest)
      chmod(postinstall_dest, (st.st_mode | 0111))


print("Building Munki")
proc = subprocess.Popen(['./munki/code/tools/make_munki_mpkg.sh','-r','munki'])
proc.communicate()
