# Secure Windows VM Desktop

## Synopsis

This document demonstrates the combination of tools working together in order to facilitate the user with a secure Windows desktop with no client side requirements other than a HTML5 capable browser.

## Introduction

This article describes a method of providing a secure Windows 10 desktop environment to be used by a member of a collaborative team.

In order to provide a secure and shielded working environment, we want to establish following objectives:
1. Access is allowed for members only
2. Invited members do not need a password, instead the authenticate against their existing Identity Provider.
3. Once authenticated, members are requested to setup 1 or more access tokens. Each token must be extra secured with u pincode. Access tokens are used as a unique shortliving application specific password to logon and unlock a Windows RDP desktop.
4. The RDP session must use a secure channel and no further ports on the Windows VM should be accessible.
5. If members are removed from the team, the access to the service should no longer be possible.


For a better uderstanding below picture makes clear what the landscape looks like.

![Overview](doc/overview.svg)

The components used are various:
* [Science Collaboration Zone][scz]
This component is offered by SURF and lets you create and maintain colllaborative teams. Team members may be invited and each person must authenticate with a Identity Provider that is associated with SCZ.
This components is not further explained in this document, more information can be found at https://wiki.surfnet.nl/display/SCZ

* [Docker][docker]
The complete stack of components are specified in a single **docker-compose** spefication file.

* [PrivacyIdea][privacyidea]
We use PrivacyIdea as for register user tokens. Privacy is linked to the SCZ LDAP as a authoritive source of members that are allowed to create and maintain tokens.

* [ZeroTier][zerotier]
We use ZeroTier to establish a private VPN between the components that need to be interconnected. For example the Windows VM's might be created at AWS Cloud of Microsot Azure for example, where our SAMBA component might be hosted of a different Cloud Provider platform. By use of Zerotier we are able to establish VPN secure connections between those components as if they where hosted in a single datacentre on a shared bridge.

* [Apache Guacamole][guacamole]
Apache Guacamole is used to render a RDP session on a standard internet browser, meaning the Windows VM user does not need install extra software on his/her desktop to make a connection to the Windows VM. The RDP session is automatically secured via Secure Sockets Layer (SSL). 

* [Samba Active Directory / Domain Controller][samba]
The Samba compones is used as a Active Directory surrogate. The Windows VM will be joined to this domain and because of the domain join, windows delegates the user/password checking to the domain controller. So the users will not need a prepared account on the Windows VM.

* [Micorosoft Windows 10][windows]
In this setup we make use of a Windows 10 64-Bit VM hosted somewhere.
We do need to install a custom Credential Provider on this VM because the authentication flow is not standard:
  1. User is asked to enter his SCZ userid attribute as username (in current setup: email)
  2. User is asked to enter (one of his token values) as a password value, a token value is the combination of a self chose PIN together with the OTP value of the selected token (Google Authenticator TOTP value, or YUBIKEY OTP for example)
  3. the Credential Provider makes contact an validating API. The validating API does following:
     * Check validity of token value for this user principal against PrivacyIdea
     * When valid, generate a long secure password
     * create/update account in Active Directory, store the generated password. (when not yet existing, create a windows acceptable unique username as well.)
      * When all succeeds, return userid/password to credential provider, otherwise return Fail.
  4. Back in Windows credential provider, serialize the returned credentials and hand over to Windows kernel for regular kerberos validation against Active Directory. This will succeed, since the Active Directory is containing same credentials.

 
## Prerequisites
Please be noted that deploying the software stack as described in this repository, requires some prerequisites:
* FQDN (Fully Qualified Domain name)
You need a **Domain** name as well as a DNS A record that resolves to the machine at which you want to deploy this software stack. You should have administrator privileges on that machine.
In this docoument, we will use **example.com** as the DOMAIN name
* You need an account on a cloud provider platform at which you can request for a fresh Windows 10 VM image to be launched.
* You need an (free) account at zerotier.com (or sign up for one)
* You need some knwoledge of **docker** and **docker-compose**

## Acknowledgements
Credits for the work of others that is used in this software stack;
* [Apache GuacaMole][guacamole]
* [Lets Encrypt][letsencrypt]
* [Microsoft Sample Code][microsoft]
* [privacyIdea][privacyidea]
* [WiX Toolset][WiX]
* [Zerotier][zerotier]

[scz]:https://sbs.pilot.scz.lab.surf.nl
[docker]:[https://www.docker.com/]
[privacyidea]:https://www.privacyidea.org/
[zerotier]:https://zerotier.com/
[guacamole]:https://guacamole.apache.org/
[samba]:https://www.samba.org/
[windows]:https://www.microsoft.com/
[microsoft]:https://github.com/microsoft/Windows-classic-samples
[WiX]:https://wixtoolset.org
[letsencrypt]:https://letsencrypt.org/

# ZeroTier Preparation
We need a private net prepared. If you do not yet have an account with Zerotier, create one.
In Zerotier, create a network, you can choose between different private network IP ranges, for example: 192.168.100/24

You will be given a unique Network ID, take note of the that ID, for example **1a2b3cd4e5**

# Docker

De **docker-compose.yml** file defines several services, some are based on standard images, others are based on custom **Dockerfile** specifications.

**Note:**

This docker-compose will not run if your docker host is OSX. This is because https://docs.docker.com/docker-for-mac/networking/


## Prepare your secrets
First thing you need before docker can be launched, is to provide your own secrets that will be used during docker execution.
Create your own **.env** file containing following constants.

```
DOMAIN=<the top level domain, for example: EXAMPLE.COM>

PID_DATABASE_ROOT=<secret>
PID_DATABASE_NAME=pi
PID_DATABASE_USER=pi
PID_DATABASE_PASS=<secret>

SAMBA_ADMIN_PASSWORD=<secret>
SAMBA_ROOT_PASSWORD=<secret>
SAMBA_KERBEROS_PASSWORD=<secret>

PID_ADMIN_PASSWORD=<secret>
PID_SECRET=<secret>
PID_PEPPER=<secret>

GUACAMOLE_API_USER=api
GUACAMOLE_API_PASS=<secret>

GUACAMOLE_DB_NAME=db_guacamole
GUACAMOLE_DB_USER=guacamole_user
GUACAMOLE_DB_PASS=<secret>

ZEROTIER_IP_ADDRESS=<put in value as explained in README>
ZEROTIER_NETWORK_ID=<put in value as explained in README>
```
For all **\<secret\>** values, put in your own secret value, unique values might be generated for example using:

```
python  -c 'import uuid; print uuid.uuid4()'
```

## Docker build...

The docker stack is straight forward.

You can now build all images by:
```
docker-compose build
```

This will take quite a while...

## One time initialization...

One of the services is the zerotier service.
Instead of lauching all services, we start by launching the Zerotier service exclusively first.

```
$ docker-compose up -d zerotier
```

This will launch the zerotier service and creates a running container.
Now we can join to the private network, by following command

```
docker exec zerotier-one zerotier-cli join <network-id>
```
Note: substitute <network-id> with the value of the network ID that you have taken note of during Zerotier Preparation in previous paragraph
According to the given example, this will look like:
```
docker exec zerotier-one zerotier-cli join 1a2b3cd4e5
```
You have not requested to join tho this Zerotier Network, but that request must be granted before actual connection takes place. For granting this connection, go back to the Zerotier website and look into the details of your network. You should see a new entry. Just check the box of that entry and this makes this a trusted connection in your private network.
Going back to your docker host, you can now verify that the connection with zeroier was succesful:
```
route -n
```
Example response:
```
$ route -n
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         ***.***.***.*   0.0.0.0         UG    0      0        0 ens2
192.168.100.0   0.0.0.0         255.255.255.0   U     0      0        0 ztabc
***.***.***.0   0.0.0.0         255.255.252.0   U     0      0        0 ens2
172.17.0.0      0.0.0.0         255.255.0.0     U     0      0        0 docker0
```

Here you see that the interface for your Zerotier network is named **ztabc**

You can now find the IP address you hav been given, by

```
$ ifconfig ztabc
```

output will look like:

```
ztabc Link encap:Ethernet  HWaddr xx:xx:xx:xx:xx:xx
          inet addr:192.168.100.173  Bcast:192.168.100.255  Mask:255.255.255.0
          inet6 addr: xxxx:xxxx:xxxx:xxxx:xxx::1/40 Scope:Global
          inet6 addr: xxxx::xxxx:xxxx:xxxx:xxxx/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:2800  Metric:1
          RX packets:113685 errors:0 dropped:0 overruns:0 frame:0
          TX packets:69824 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:104472770 (104.4 MB)  TX bytes:4891234 (4.8 MB)
```

So, the IP address is **192.168.100.173**

You need to update the **.env** file with this IP Address

```
ZEROTIER_IP_ADDRESS=192.168.100.173
ZEROTIER_NETWORK_ID=1a2b3cd4e5
```

Now you can launch all services with:

```
docker-compose up -d
```

# Windows 10 VM instructions.

Select a Cloud Provider platform of your choice and launch a Windows 10 VM.

## Install required MSI packages

We need some additional components to be installed on this Windows VM:

* Zerotier
Install from https://download.zerotier.com/dist/ZeroTier%20One.msi

* Microsoft Visual Studio Redistributable
Downlod from https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads
Make sure you the version you select matches your Windows VM version and is suitable for Visual Studiu 2019

* SCZ Credential Provider
This package is included in this repository:
[SCZ Credential Provider](msi/SCZ_CredentialProvider_Setup.msi)

### Install SCZ Credential Provider

Start the MSI, the following screen will be presented

![SCZ install Credential Provider](doc/windows-install-SCZ_credential-provider.png)

Read and accept the license agreement, and click **Next**

![SCZ SCZ license](doc/windows-SCZ-license.png)

Select Core compoents to be installed plus the default provider to be this Credential Provider, and click **Next**

![SCZ SCZ Components](doc/windows-SCZ-components.png)

Now enter the address of the **FQDN** (Fully Qualified Domain Name) at which your server host is reachable. This is the service host at which the Docker-compose was executed. This docker-compose includes de API service that this SCZ Credential Provider depends on.

When done, click **Next**

![SCZ SCZ API Address](api/../doc/windows-SCZ-API-address.png)

Optionally you can adjust some other settings, then click **Next**

![SCZ SCZ API Address](api/../doc/windows-SCZ-optional-settings.png)

Now press **Install**

![SCZ SCZ Install](api/../doc/windows-SCZ-install.png)

You must approve this application to make changes to your VM...

![SCZ SCZ Install Approve](api/../doc/windows-SCZ-install-approve.png)

After installation, you will be instructed to restart your VM.
When that is completed, continue with some additional configuration described in more detail below.

### Network configuration

As a Administrator of this VM connect to this machine run following steps

- Start Zerotier application and join network (example: 1a2b3cd4e5)

- On Zerotier portal, grant connection of this new machine to your private network

Your machine has now access to the private network. You can check that you can reach the docker host, by opening a Command Prompt window, and type:

```
ping 192.168.100.173
```

This shoud work !

Also, take not of the Zerotier IP address that has been given to this Windows VM, please type:

```
ipconfig
```

Will show something like this
```
C:\Users\Administrator>ipconfig

Windows IP Configuration


Ethernet adapter Ethernet:

   Connection-specific DNS Suffix  . : xx.local
   IPv4 Address. . . . . . . . . . . : xx.xx.xx.xx
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : xx.xx.xx.1

Ethernet adapter ZeroTier One [1a2b3cd4e5]:

   Connection-specific DNS Suffix  . :
   IPv4 Address. . . . . . . . . . . : 192.168.100.148
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 255.255.255.254
```

We need the IP Addres of this Windows VM for configuring Guacamole later on.

### Change Network Adapter properties

As administrator, right-click on Explorer windowns at **Network**

![Windows Netwprk Properties](doc/windows-network-properties.png)


#### DNS -> SAMBA host

#### Disconnect IPV6 (for now)

Select line with Internet Protocol 6 (TCP/IPv6) and disable the checkbox in front of it.

![Windows Network Disable IPv6](doc/windows-network-disable-ipv6.png)

#### Adjust Preferred DNS

Select line with Internet Protocol 4 (TCP/IPv4) and click on properties.

![Windows Network Properties IPv4](doc/windows-network-properties-ipv4.png)

Set preferred DNS to the IP Address that was cocncluded during ZeroTier host installation, in this document **192.168.100.173**

![Windows Network Properties IPv4 DNS](doc/windows-network-properties-ipv4-dns.png)

### Join Domain

As administrator, start explorer, right click **This Machine** and select **properties**

![Windows Machine Properties](doc/windows-machine-properties.png)

On the next screen, select **Change Settings**

![Windows Machine Name Settings](doc/windows-machine-name-settings.png)

this will show the **System Properties** dialog, now choose **Change...**

![Windows Machine Name Network ID](doc/windows-machine-name-change.png)

Suppose you have selected **example.com** as your **DOMAIN** constant in your configuration settings, then fill in **ad.example.com** in the Domain field:

![Windows Domain Credentials](doc/windows-machine-domain-join.png)

and hit **OK**

You will be asked to enter the domain Administrator credentials. Please use **Administrator** as username and the password you have chosen earlier as your **SAMBA_ADMIN_PASSWORD**.

![Windows Domain Credentials](doc/windows-machine-domain-credentials.png)

This will take some time, but finally it will respond like:

![Windows Domain Welcome](doc/windows-machine-welcome-domain.png)

### RDP Settings

As administrator, start "select users" and open this setting.

![Windows RDP users](doc/windows-machine-rdp-users.png)

On next screen:
* unselect **Allow Remote Assistance connections to this computer**
* unselect **Only allow ... with Network Level Authentication ...**
* Clink **Select Users...**

![Windows RDP Settings](doc/windows-machine-rdp-settings.png)

On the next screen, make sure that **AD\Domain Users** are listed.

![Windows RDP Allowed Users](doc/windows-machine-rdp-allowed-users.png)

If not, click **Add...** and type in **AD\Domain Users** and hit OK.

![Windows RDP Domain Users](doc/windows-machine-rdp-allow-domain-users.png)

You will be asked to enter doman administrator credentials, user **Administrator** and the **SAMBA_ADMIN_PASSWORD** fropm your configuration secret passwords.

![Windows RDP Settings](doc/windows-machine-domain-authenticate.png)

### Adjust Firewall to allow Remote Desktop connections

As administrator, start "firewall"

![Windows Firewall](doc/windows-firewall.png)

Ckick on left menu option **Allow an app or feature...**

![Windows Firewall Adjust](doc/windows-firewall-adjust.png)

Scroll down to **Remote Desktop** and mark the option in front of this line as well as the marks in the 3 network columns (Domain, Private and Public)

![Windows Firewall Allow RDP](doc/windows-firewall-allow-rdp.png)

### Switch Off Network Level Authentication (NLA)

As administrator, start "Remote Desktop Settings"

![Windows NLA](doc/windows-NLA.png)

Switch On **Enable Remote Desktop**

![Windows NLA Settings](doc/windows-NLA-settings.png)

Click on Advanced Settings...

![Windows NLA Advanced Settings](doc/windows-NLA-advanced-settings.png)

Disable **Require computers to use Network Level Authentication to connect**

## Restart VM

Now that we have so many adjustments to our VM, let's give Windows some quality time for itself to ruminate these changes, Restart the machine !

# PrivacyIdea Administrator actions

One off the started services is the PrivacyIdea Administrator portal.

As a minimal, PrivacyIdae needs to be configured to specify what is the source the user-store. In this example we configure the user store to be a LDAP reference.

![User](doc/privacyIdea-user.png)

Choose **new ldapresolver** will let you confugure the required LDAP settings

![ldap](doc/privacyIdea-ldap.png)

Now that we have LDAP setup, we create a default **realm** so that users are resolved using the LDAP Resolver.

![realm](doc/privacyIdea-realm.png)

Next, we can continue with configuring tokens to allowed to be used by our users, for example TOTP (as used by Google Authenticator)

![User](doc/privacyIdea-tokens-TOTP.png)

# Guacamole Administrator actions

When the **docker** services have succesfully started, one off the started services is the Guacamole Administrator portal.

You can reach this portal with you webbrowser at:

```
https://<YOUR DOMAIN>/admin/
```

Log in with initial credentials:
```
guacadmin/guacadmin
```

on this portal go to menu (top right) and select settings.
* on the **Preferences** tab, adjust your administrator password immediately

When changed, select **Connections** tab and create *New*

Enter following details:
* [ Connection ]
  * Name: **Windows 10**
  * Location: **ROOT**
  * Protocol: **RDP**
* [ Guacamole Proxy Paramaters (GUACD) ]
  * Hostname: **guacd**
  * Port: **4822**
  * Encryption: **None (unencrypted)**
  **Note**: *Do not worry about this unencrypted settings, this is internal traffic taking place between docker containers and not visible outside the docker host. All traffic via public Internet is encrypted via SSL.*
* [ Parameters / Network ]
  * Hostname: **192.168.100.148**
   **Note**: *this is the IP address of the Windows VM as concluded during Windows Zerotier Configuration*
  *  Port: **3389**
*  [ Parameters / Authentication ]
   *  Domain: **AD**
   *  Security Mode: **TLS encryption**
   *  Disable Authentication: **True**
   *  Ignore server certificate: **True**
* [ Parameters / Display ]
  * Color Depth: **True Color (32-bit)**
  
Save these details.
  
# SCZ Preparations...

Last but not least we need to have an SCZ Colloboration membership.

\<TO BE CONTINUED\>

# Proof of working !

## Invite a member
\<TO BE CONTINUED\>

## have this member accept membership
\<TO BE CONTINUED\>

## have this member setup his personal token(s)
\<TO BE CONTINUED\>

## have this member logon to the Window VM Desktop !
\<TO BE CONTINUED\>
