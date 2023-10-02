# munki_rebrand

munki_rebrand is a script to rebrand the Managed Software Center app from Greg Neagle's [Munki](https://github.com/munki/munki). It allows you to give the app a different name in Finder (in all localized languages if required), modify its icon, and add an optional postinstall script to the installer pkg.

This is version 4 of munki_rebrand. If you wish to use it to rebrand munki 3.6 or higher, you will need to have Xcode installed and have opened it and installed the extra components. The ability to provide your own .icns file has been removed and the icon will be generated from a 1024x1024px .png only.

It will either:

 - Download the latest release of munkitools from github, unpack it, rebrand it and repack it
 - Use or download a version of the munkitools pkg you specify with the -k or --pkg option. Therefore if you need a custom built pkg you can do this prior to running munki_rebrand, or you can download the automatic builds from https://munkibuilds.org


## Pre-requisites
 * Apple Mac running OS X/macOS 10.15+ 
 * Xcode 12+ (opened once, components installed)
 * Python3

## Usage

Please note: munki_rebrand must be run as root in order to successfully build the output pkg.

At its simplest you can use ```sudo ./munki_rebrand.py --appname "Amazing Software Center"``` to download the latest munkitools pkg from Github, and rename Managed Software Center to Amazing Software Center in the Finder in all localized versions of "Managed Software Center".

If you specify ```--pkg``` you can use either a pathname on disk to a prebuilt munkitools pkg or use an http/s URL to download one, which munki_rebrand will then attempt to rebrand.

The ```--icon-file``` option allows you to specify the path to an icon to replace the one in Managed Software Center. This must be a 1024x1024 .png file with alpha channel for transparency that will be converted on the fly. An example .png is included in the repo. The ```--postinstall``` option allows you to specify the path to an optional postinstall script that will be executed after munki installs. A postinstall script could be used, for instance, to set the client defaults outlined on the [Munki wiki](https://github.com/munki/munki/wiki/Preferences). In addition to the postinstall, you can include the ```--resource-addition``` option to include an additional file in the Scripts directory. A good example for this would be to include another package containing middleware. Please note, you may not be able to use ```--sign-binaries``` with this option unless the package being added is also previously notarized. 

To specify the output filename of your custom pkg use ```--output-file```. For example, if you set this to ```"Amazing_Software_Center"``` your output file will be renamed from something like ```munkitools-2.8.2553.pkg``` to ```Amazing_Software_Center-2.8.2553.pkg```

The ```--sign-package``` option allows you to have a rebranded munki package that is also natively signed. To use this option, your Developer Installer Certificate must be installed into the keychain. When using this option, you must specify the entire ```Common Name``` of the certificate. Example: ```"Developer ID Installer: Munki (U8PN57A5N2)"```

The ```--sign-binaries``` option allows you to recursively sign the app binaries for the rebranded Managed Software Center, allowing for notarization of the pkg. To use this option, your Developer Application Certificate must be installed into the keychain. When using this option, you must specify the entire ```Common Name``` of the certificate. Example: ```"Developer ID Applications: Munki (U8PN57A5N2)"```

For usage help please see ```sudo ./munki_rebrand.py --help```

## Troubleshooting/Notes
* If you receive the message 
```
xcode-select: error: tool 'actool' requires Xcode, but active developer directory '/Library/Developer/CommandLineTools' is a command line tools instance
```
then try the following:
```
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```
You can run ```sudo xcode-select -s /Library/Developer/CommandLineTools``` to revert this afterwards if you so wish.
* The `Assets.xcassets folder` must be located in the same folder that `munki_rebrand.py` is run from
* The app will still appear as ```Managed Software Center.app``` in the filesystem e.g. when viewed in Terminal. This is by design, in case the app is called or searched for by name by any other process. The changed name will only appear in Finder, the Dock, and the app's menu bar.
* The pkg ids of ```com.google.munki.*``` are also left unchanged for similar reasons.

## To-do
* Enable the splitting of the distribution pkg into its component pkgs so that the user can decide which to upgrade (perhaps they do not want to upgrade the launchd package if not necessary and can therefore avoid a reboot).
* munkiimport the resulting pkg(s)?
