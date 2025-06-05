# NameIt # 

NameIt is a software tool that renames research articles in pdf files in a standardised way. 

Based on the pdf metadata and on the content of the document first page, it renames the file  with author, year, title, publication, and publisher. 

# In-and-out

## INPUT: 
* One or several pdf files (e.g., journal articles) 

## OUTPUT: 
* The same pdf files are renamed in a standardised way - author, year, title, publication (e.g., journal name), and publisher. 

Example: "s13174-015-0028-2.pdf" as downloaded from the publisher would become "Teixeira et al. (2015). Lessons learned from applying social network analysis on an industrial Free/Libre/Open Source Software ecosystem. Journal of Internet Services and Applications. Springer.pdf" as renamed by the NameIt tool. 

# Mission # 

* MISSION 1 - Enable researchers across the world to store and find research articles in their computers, servers or shared folders in a easier and faster way.
* MISSION 2 - Advance the standardisation on how research articles in pdf format are named. 

# Benefits of using NameIT

* Research articles are easier to get.
* Research articles are stored in a standardized way.

## Advantages of retrieving a well named pdf file from a hard drive over the publisher's website

- Faster to find it 
- Faster to open it
- Faster to print it (consider sustainability and ecological issues before printing)
- Less duplication of digital resources (note that you are saving space on your hard disk and saving traffic on the web)
- No need to login
- No need to connect to VPN
- No need to resolve some DOI
- No adds
- No paywalls
- No overload with related or non-related information 
- You can get the pdf straight before even seeing the HTML web version
- No cookies tracking your behaviour online
- No hidden fingerprinting codes or watermarking schemes that identify the buyers for every copy of each PDF sold


## Advantages of adoptiong the NameIt standard for naming research articles in pdf. 

- Easier to understand what is on a file as its filename encodes information on author, year, title, publication (e.g., journal name), and publisher.
- Easier to link pdf files to entries on software tools suporting systematic literature reviews (see [https://aut.ac.nz.libguides.com/systematic_reviews/tools](https://aut.ac.nz.libguides.com/systematic_reviews/tools) for more information). 
- Easier to link pdf files to reference management systems (see [https://www.helsinki.fi/en/helsinki-university-library/using-collections/courses-and-workshops/reference-management-software](https://www.helsinki.fi/en/helsinki-university-library/using-collections/courses-and-workshops/reference-management-software) for more information).
- Better interopability between software tools that deal with research articles in pdf. 
- Predictability (i.e., you will not be surprised on how a pdf file is named after being downloaded from a publisher website or the website of colleague). 
- Easier exchangability of collection of research articles between researchers, research groups, libraries and publishers.

# TARGET USERS:  # 

* Human users - Researchers or research teams that want to store and exchange files with a standard naming convention. 
* Software users -  Software tools supporting the management of citations, bibliometrics, references, and literature reviews have now a tool and a standard way to "file name" research articles in PDF format.

# Requirements # 

* Python 3
* Habanero (NameIt will try install it if you don't have it)
* PyMuPDF (NameIt will try install it if you don't have it)

We suport the ext3, ext4, xfs, zfs, NTFS, APFS, HFS+ and xFAT filesystems. Support for FAT32 pending. 
Should work in most modern computers running Linux, macOS and Windows. Problems could arise with the use of old  USB flash drives  and SDcard disks in old Linux Kernels. 

# Dependencies 

NameIt tries to automatically install its dependencies. If it fails, you can try to install them using pip - the package installer for Python

## Habanero ##
`$ pip (or pip3) install habanero`

## PyMuPDF ##

`$ pip (or pip3) install PyMuPDF`


# How to use it 

* Install the Habanero and PyMuPDF dependencies 

* Invoke the Python script and pass the file to be renamed as an argument.
* You can also pass a folder as an argument and NameIt will attempt to rename all pdf files in that folder.

## Example: ## 


`$ NameIt 4242343.pdf`

`$ NameIt research-articles-collection`




# How it works 

By default, the tool first tries to find pdf's metadata to rename the file. If no metadata is found, it will look on the article first page for a DOI (Digital Object Identifier) and then tries 
to connect to Internet to retrieve the metadata associated to the DOI. 

If pdf's metadata is not found and the retrieval of metadata via the DOI fails, the tool will still try to find the author, year, title, publication, and publisher from the article 1st page. 
It looks for the size of the text fonts  to distinguishes between what is a title or what is the author information and so on, all by using the [LayoutLMv3](https://huggingface.co/docs/transformers/en/model_doc/layoutlmv3) pre-trained multimodal Transformer AI/ML model. 

From more that 100 journal articles downloaded directly from the publishers websites. We could rename 98 without issues.  Author names with no so common accents and articles titles with not so common characters can be problematic.


# Future features 
- A GUI version for less tech users is forthcoming  <funding needed - funding being appied - new contributors welcome>.
- Support for wildcards (e.g., NameIt folder1/*pdf Elon*.pdf) 

# License #

MIT license. Please acknowledge derivative works. 

# Acknowledgements 

* First created by Jose Teixeira <jose.teixeira@abo.fi>
* First contribuitions by Sukrit 
* Support from the Academy of Finland via the DiWIL project  <see https://web.abo.fi/projekt/diwil/> 
* Support from the open-science initiatives of Åbo Akademi 
