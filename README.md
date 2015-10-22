# munki-rebrand

Scripts used by University of Oxford IT Services to rebrand [Munki](https://github.com/munki) for their *Orchard* branded Mac management solution.

This repo can give you some idea of how we rebrand munki at University of Oxford to bring it under our *Orchard* brand, add preflight and postflight scrips for managedsoftwareupdate, and a postflight for the installer package. Most of the scripts will need rework to be of use to others, as will the .icns file and artwork - please do not use our *Orchard* brand. 

We originally used the [munki_rebrand.py script](https://gist.github.com/bochoven/c1c656e0c2e1b1078dfd) by [Arjen van Bochoven](https://github.com/bochoven) to inject the pre/posflight scripts for munki into the munkitools mpkg itself, but now package these separately and push them out with munkitools so they are more easily updated separately from the installer. The pre and postflight scripts here are just examples of what can be done - for us we ensure that recon (jamf jss inventory collection) is only done after an install/remove by Munki.
