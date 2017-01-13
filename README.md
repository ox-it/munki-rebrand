# munki_rebrand

munki_rebrand is a script to rebrand the Managed Software Center app from Greg Neagle's [Munki](https://github.com/munki/munki). It allows you to give the app a different name in Finder (in all localized languages if required), modify its icon, and add an optional postinstall script to the installer pkg.

## Usage

Please note: munki_rebrand must be run as root in order to successfully build the output pkg. You will need Xcode (7+) and its command-line tools installed.

At its simplest you can use ```sudo ./munki_rebrand.py --appname "Amazing Software Center"``` to rename Managed Software Center to Amazing Software Center in the Finder where the language is set to English (U.S.) and you install Munki with the outputted pkg file. Use the ```--localized``` option to also changed all localized versions of Managed Software Center to your desired app name.

The ```--icon-file``` option allows you to specify the path to an icon to replace the one in Managed Software Center. This can be an .icns file or a 1024x1024 .png file with alpha channel for transparency that will be converted on the fly. An example .png is included in the repo. The ```--postinstall``` option allows you to specify the path to an optional postinstall script that will be executed after munki installs. A postinstall script could be used, for instance, to set the client defaults outlined on the [Munki wiki](https://github.com/munki/munki/wiki/Preferences).

To download a specific tag of munki use the ```--munki-release``` option. If this is set to e.g. ```v2.8.2``` munki_rebrand will switch to this release for the building of your customized pkg. See the [Munki releases page](https://github.com/munki/munki/releases) for details of release tags. If this is not set, munki_rebrand will use the latest, bleeding-edge Munki code from Github. To specify the output filename of your custom pkg use ```--output-file```. For example, if you set this to ```"Amazing_Software_Center"``` your output file will be renamed from something like ```munkitools-2.8.2553.pkg``` to ```Amazing_Software_Center-2.8.2553.pkg```

To use a local copy of munki use the ```--local-code``` option and specify a path. This will skip the git clone entirely.

To use the new DEP package tool, use the ```--dep``` option.

For usage help please see ```sudo ./munki_rebrand.py --help```

## Notes
* The app will still appear as ```Managed Software Center.app``` in the filesystem e.g. when viewed in Terminal. This is by design, in case the app is called or searched for by name by any other process. The changed name will only appear in Finder, the Dock, and the app's menu bar.
* The pkg ids of ```com.google.munki.*``` are also left unchanged for similar reasons.
* Versions of munki older than 2.8.0 may require that you have the OS X 10.8 SDK added to XCode. See <https://github.com/munki/munki/wiki/Building-Munki2-Pkgs/b9976fabfb964a727da3e7e38ef3b5857554f284> if you're really intent on building an older version.

## To-do
* Enable the splitting of the distribution pkg into its component pkgs so that the user can decide which to upgrade (perhaps they do not want to upgrade the launchd package if not necessary and can therefore avoid a reboot).
* munkiimport the resulting pkg(s)?
