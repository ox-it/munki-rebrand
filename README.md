# munki-rebrand
Scripts used by University of Oxford (NSMS Group) to rebrand Munki for their Orchard mac management platform

This repo can give you some idea of how we rebrand munki at University of Oxford to bring it under our 'Orchard' mac management brand. Most of the scripts will need editing by hand to be of use to others (as will the icns file!).
N.B. - we originally used the munki_rebrand.py script to inject the pre/posflight scripts for munki into the munkitools mpkg itself, but now package these separately and push them out with munkitools so they are more easily updated separately from the installer.
