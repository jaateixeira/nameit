# NameIt # 

NameIt is a software tool that renames research articles in pdf files in a standardised way. 

Based on the pdf metadata and on the content of the document first page, it renames the file  with author, year, title, publication, and publisher. 

# In-and-out

## INPUT: 
* One or several pdf files (e.g., journal articles) 

## OUTPUT: 
* The same pdf files are renamed in a standardised way - author, year, title, publication (e.g., journal name), and publisher. 

Example: "4242343.pdf" as downloaded from the publisher woud become "Teixeira, J., Robles, G., & González-Barahona, J. M. (2015). Lessons learned from applying social network analysis on an industrial Free/Libre/Open Source Software ecosystem. Journal of Internet Services and Applications. Springer.pdf" as renamed by the NameIt tool. 

# Mission # 

* MISSION 1 - Enable researchers across the world to store and find research articles in their computers, servers or shared folders in a easier and faster way.
* MISSION 2 - Advance the standardisation on how research articles in pdf format are named. 

# Benefits of using NameIT

* Research articles are easier to find.
* Research articles are stored in a standardized way.

# TARGET USERS:  # 

* Human users - Researchers or research teams that want to store and exchange files with a standard naming convention. 
* Software users -  Software tools supporting the management of citations, bibliometrics, references, and literature reviews have now a tool and a standard way to "file name" research articles in PDF format.

# Requirements # 

* Python 3
* Habanero (nameIt will try install it if you don't have it)
* PyMuPDF (nameIt will try install it if you don't have it)

We suport the ext3, ext4, xfs, zfs, NTFS, APFS, HFS+ and xFAT filesystems. Support for FAT32 pending. 
Should work in most modern computers running Linux, macOS and Windows. Problems could arise with the use of old  USB flash drives  and SDcard disks in old Linux Kernels. 

# Dependencies 

## Habanero ##
 $ pip (or pip3) install habanero

## PyMuPDF ##

$ pip (or pip3) install PyMuPDF


# How to use it 

* Install the Habanero and PyMuPDF dependencies 

* Invoke the Python script and pass the file to be renamed as a document.

* A GUI version for less tech users is forthcoming  <funding needed - funding being appied - new contributors welcome>.

# How it works 

First, the tool tries to find pdf's metadata to rename the file. If no metadata is found, it will try to find the author, year, title, publication, and publisher from the article 1st page. 


# License #

MIT license. Please acknowledge derivative works. 

# Aknowledgements 

* First created by Jose Teixeira <jose.teixeira@abo.fi>
* First contribuitions by Sukrit 
* Support from the Academy of Finland via the DiWIL project  <see https://web.abo.fi/projekt/diwil/> 
* Support from the open-science initiatives of Åbo Akademi 
