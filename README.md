# Secure Windows VM Desktop

[ WORK IN PROGRESS ]

## Introduction

This article describes a method of providing a secure Windows 10 desktop environment to be used by a member of a collaborative team.

For a better uderstanding below picture makes clear what the landscape looks like.

![Overview](doc/overview.svg)

The components used are various.
* Science Collaboration Zone (SCZ)
https://sbs.pilot.scz.lab.surf.nl
This components is offered by SURF and lets you create and maintain colllaborative teams. Team members may be invited and each person must authenticate with a Identity Provider that is associated with SCZ.

* PrivacyIdea
https://www.privacyidea.org/
* ZeroTier
https://zerotier.com/
* Guacamole
https://guacamole.apache.org/
* Samba
https://www.samba.org/
* MS Windows
https://www.microsoft.com/

# Installation instructions

Windows 10
- Change IPV4 properties, DNS -> SAMBA host
- Disconnect IPV6 (for now)
- JOIN domain
- Allow Remote Desktop for "Everyuser"
- Firewall windows inkomend 3389 (Add Remote Desktop APP)
- Switch off NLA (Remote Desktop Settings)
- install VC_REDIST
- Install SCZ Credential Provider
- Restart VM
