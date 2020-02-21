# Secure Windows VM Desktop

[ WORK IN PROGRESS ]

## Introduction

This article describes a method of providing a secure Windows 10 desktop environment to be used by a member of a collaborative team.

In order to provide a secure and shielded working environment, we want to establish following objectives:
1. Access is allowed for members only
2. Invited members do not need a password, instead the authenticate against their existing Identity Provider.
3. Once authenticated, members are requested to setup 1 or more access tokens. Each token must be extra secured with u pincode. Access tokens are used as a unique shortliving application specific password to logon and unlock a Windows RDP desktop.
4. The RDP session must use a secure channel and no further ports on the Windows VM should be accessible.
5. If members are removed from the team, the access to the service should no longer be possible.
6. ...


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

 
[scz]:https://sbs.pilot.scz.lab.surf.nl
[docker]:[https://www.docker.com/]
[privacyidea]:https://www.privacyidea.org/
[zerotier]:https://zerotier.com/
[guacamole]:https://guacamole.apache.org/
[samba]:https://www.samba.org/
[windows]:https://www.microsoft.com/

# ZeroTier preparation.
We need a private net prepared. If you do not yet have an account with Zerotier, create one.
In Zerotier, create a network, you can choose between different private network IP ranges, for example: 192.168.100/24

You will be given a unique Network ID, take note of the that ID, for example **1a2b3cd4e5**

# Docker stack.
The docker stack is straight forward.

One of the services is the zerotier service. This is standard image.
Instead of lauching all services, we start by launching the Zerotier service exclusively first.

```
$ docker-compose up -d zerotier
```

This will launch the zerotier service and creates a running container.
Now we can join to the private network, by following command

```
docker exec zerotier-one zerotier-cli join <network-id>
```
(*) substitute <network-id> with the value of the network ID that you have taken note of during Zerotier Preparation in previous paragraph

According to the given example, this will look like:
```
docker exec zerotier-one zerotier-cli join 1a2b3cd4e5
```

You have not requested to join tho this Zerotier Network, but that request must be granted before actual connection takes place. For granting this connection, go back to the Zerotier website and look into the details of your network. You should see a new entry. Just check the box of that entry and this makes this a trusted connection in your private network.

Going back to your docker host, you can now verify that the connection with zeroier was succesful:
```
route -n
```

```
$ route -n
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         ***.***.***.*   0.0.0.0         UG    0      0        0 ens2
192.168.100.0   0.0.0.0         255.255.255.0   U     0      0        0 ztabc
***.***.***.0   0.0.0.0         255.255.252.0   U     0      0        0 ens2
172.17.0.0      0.0.0.0         255.255.0.0     U     0      0        0 docker0
```

Here you zee that the interface for your Zerotier network is named **ztabc**

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

### Network configuration

As a Administrar of this VM connect to this machine run following steps

- Install Zerotier (download Windows MSI from Zerotier website)
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

### Further configuration of Windows

Next, we need some additional adjustments on this VM:

< TO BE SPECIFIED IN MORE DETAIL >

- Change IPV4 properties, DNS -> SAMBA host
- Disconnect IPV6 (for now)
- JOIN domain
- Allow Remote Desktop for "Everyuser"
- Firewall windows inkomend 3389 (Add Remote Desktop APP)
- Switch off NLA (Remote Desktop Settings)
- install VC_REDIST
- Install SCZ Credential Provider
- Restart VM

# PrivacyIdea Administrator actions

One off the started services is the PrivacyIdea Administrator portal.

< TO BE SPECIFIED IN MORE DETAIL >

- Change Administrator Password
- Setup LDAP link to SCZ user LDAP
- some more configuration steps
- ...

# Guacamole Administrator actions

One off the started services is the Guacamole Administrator portal.

< TO BE SPECIFIED IN MORE DETAIL >

- Change Administrator Password
- Configuration: Specify link to Guac Daemon
- Create connection link to Windows VM 
  
