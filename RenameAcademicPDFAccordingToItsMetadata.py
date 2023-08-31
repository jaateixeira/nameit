#!/usr/bin/python
from __future__ import with_statement

# Rename files according to its metadata
# Created and maintained by Jose Teixeira <jose.teixeira@abo.fi>
# Ideas for future development include:
## the use of journal abreviations
## extract the doi from publication (see http://stackoverflow.com/questions/27910/finding-a-doi-in-a-document-or-page)
## integrate layour aware techniques https://code.google.com/archive/p/lapdftext/

# For applying in all files use
# find . -name "*.pdf" -exec  RenameAcademicPDFAccordingToItsMetadata.py {} \;

import sys
import os
import datetime
import subprocess
import re
import string

from pdfrw import PdfReader
# See https://github.com/pmaupin/pdfrw/
from PyPDF2 import PdfFileReader
# See https://pythonhosted.org/PyPDF2/

import unicodedata

validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)

def removeDisallowedFilenameChars(filename):
    cleanedFilename = unicodedata.normalize('NFKD', unicode(filename)).encode('ASCII', 'ignore')
    return ''.join(c for c in cleanedFilename if c in validFilenameChars)


print 'Number of arguments:', len(sys.argv), 'arguments.'
print 'Argument List:', str(sys.argv)

if len(sys.argv) != 2:
    print "Wrong number of arguments --- Abort"
    exit()

filename = sys.argv[1]
    
if not os.path.exists(filename):
    print  filename+" does not exist--- Abort"
    exit()


try:
    pdfrw_info= PdfReader(filename).Info
    print filename+" its as readable pdf file"
except:
    print  "Unable to read pdf with pdfrw "+filename+" --- WARNING"
    pdfrw_info = None
    #exit()


if pdfrw_info != None: 

    # Info from pdfrw
    print "\n\tInformation retrieved by pdfrw:"
    print "\t",pdfrw_info


# info from pypdf2

try:
    ipdf = PdfFileReader(open(filename, 'rb'))
except:
    print  "Unable to read pdf with pypdf2 "+filename+" --- Warning"
    ipdf = None 
    #exit()


pypdf2_info=ipdf.getDocumentInfo()
pypdf2_xmp=ipdf.getXmpMetadata()

print "\n\tInformation retrieved by pypdf2:"
print "\t", pypdf2_info
print "\n\tXMP Information retrieved by pypdf2:"
print "\t",pypdf2_xmp


# Save now the author, year, title, publisher information if possible


# Attempt author first
author = 'Unknown author'

if pdfrw_info != None: 
    for key, value in pdfrw_info.items():
        if 'auth' in  key.lower():
            author = value

for key, value in pypdf2_info.items():
    if  'auth' in  key.lower():
        author = value

if pypdf2_xmp != None: 
    authors = pypdf2_xmp.dc_creator

    if len(authors) == 1 :
        author = authors[0]
    if len(authors) == 2 :
        author = authors[0] + " and " + authors[1]
    if len(authors) > 2 :
        author = authors[0] + " et al."

    
# Attempt now the year
year = 'Unknown year'

if pdfrw_info != None: 
    for key, value in pdfrw_info.items():
        if 'date' in key.lower():
            date_str = value


for key, value in pypdf2_info.items():
    if 'date' in key.lower():
        date_str = value 

print "\n\t pdfrw or pypdf2 date_str=", date_str
        
# For now we are able to get the date if signed in the fortat \dyyyy


def getYearFromDateStr(date_str):

    def valid_year(year):
        if year and year.isdigit():
            if int(year) >=1900 and int(year) <=2020:
                return True
        return False

    "Finds the first valid year yyyy patter in the string date_str"
    for i in range(0,len (date_str)):
        tmp = date_str[i:i+4]
        if valid_year(tmp):
            return tmp

    return "Unable to process year information" 


print "\n\t year retrived from date string =", getYearFromDateStr(date_str)

year = getYearFromDateStr(date_str)
        
if pypdf2_xmp != None:

    if pypdf2_xmp.xmp_metadataDate != None:
        year = str(pypdf2_xmp.xmp_metadataDate.year)
    
    if pypdf2_xmp.xmp_modifyDate != None:
        year = str(pypdf2_xmp.xmp_modifyDate.year) 
    
    if pypdf2_xmp.xmp_createDate != None:
        year = str(pypdf2_xmp.xmp_createDate.year)


# Attempt now the tile

title= "Unknown title"

if pdfrw_info != None: 
    for key, value in pdfrw_info.items():
        if 'title' in  key.lower():
            title = value

for key, value in pypdf2_info.items():
    if  'title' in  key.lower():
        title = value

if pypdf2_xmp != None :
    if pypdf2_xmp.dc_title != None and pypdf2_xmp.dc_title != {}:
        title = ""
        for key, value in pypdf2_xmp.dc_title.items():
            title = title + value

    print "\n\t title retrieved by pypdf2_xmp.dc_title=",title 
        
# attempt now the publication name
publication = "Unkown publication"


if pdfrw_info != None: 
    for key, value in pdfrw_info.items():
        if 'source' in  key.lower():
            publication = value

        if 'doi' in  key.lower():
            publication = value

        if 'subject' in  key.lower():
            publication = value

        if 'publication' in  key.lower():
            publication = value

        
for key, value in pypdf2_info.items():
    if 'source' in  key.lower():
        publication = value

    if 'doi' in  key.lower():
        publication = value

    if 'subject' in  key.lower():
        publication = value
        break 

    if 'publication' in  key.lower():
        break 
        publication = value

    
if pypdf2_xmp != None :
    if pypdf2_xmp.dc_source != None and pypdf2_xmp.dc_source != {}:
        publication = pypdf2_xmp.dc_source
    print "\n\t publication retrieved by pypdf2_xmp.dc_title=",publication



# attempt now the publisher / creator  name
publisher  = "Unkown publisher"




if pdfrw_info != None: 
    for key, value in pdfrw_info.items():
        if 'publisher' in  key.lower():
            publisher = value

        if 'creator' in  key.lower():
            publisher = value


        
for key, value in pypdf2_info.items():
    if 'publisher' in  key.lower():
        publisher = value

    if 'creator' in  key.lower():
        publisher = value



print ""
print " \tRetrieved METADATA *********************" 
print '\tauthor='+author
print '\tyear='+year
print '\ttitle='+title
print '\tpublication='+publication
print '\tpublisher='+publisher
print "\t*******************************************\n\n" 


# Trying now to get publication from the file itself

"find a pattern in a give file" 
def findPatternInFile(file,pattern):
    cmd = '/usr/bin/strings "'+ filename +'"  | /bin/grep publication'
    print "invoking", cmd

    try:
        res_cmd = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print e

        if e.output.startswith('error: {'):
            error = json.loads(e.output[7:]) # Skip "error: "
            print error['code']
            print error['message']
    
        return False 
    except:
        print "Unexpected error:", sys.exc_info()[0]
        return False 

        
    print "\t\t DEBUG LEVEL 2 - strings + grep returned ", res_cmd

        
    # looking for <prism:publicationName>The Journal of Academic Librarianship</prism:publicationName>
    m = re.findall(pattern, res_cmd)

    print "\t\t DEBUG LEVEL 2 - First found patter m[0]=", m[0]

    if m != None:
        return  m[0]
    else:
        print "error can find publication name"
        return False 

    
    
if publication  == "Unkown publication":
    print "Trying now to get publication from the file itself"

    foundPublicationName = findPatternInFile(filename,'<prism:publicationName>(.*)</prism:publicationName>')

    print "\t \t DEBUG LEVEL 1 - foundPublicationName in file =", foundPublicationName 
    
    if foundPublicationName != False:
        publication =  foundPublicationName
    

        print " \tRetrieved from file  *********************" 
        print '\tpublication='+publication
        print " \t******************************************" 

# Tries also to get title using docear (see http://www.docear.org/software/add-ons/docears-pdf-inspector/)
# calls java -jar docears-pdf-inspector/docears-pdf-inspector.jar  -title 

def getDocearTitle(filename):
    print "\n\t DEBUG 1 Attempting to get title from docear"

    cmd = '/usr/bin/java  -jar /home/apolinex/ownCloud/FLOSS-dev/renamePdfByMetaData/renameacademicpdfaccordingtoitsmetadata/docears-pdf-inspector/docears-pdf-inspector.jar  -title "'+ filename + '"'
    print "invoking", cmd

    try:
        res_cmd = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print e

        if e.output.startswith('error: {'):
            error = json.loads(e.output[7:]) # Skip "error: "
            print error['code']
            print error['message']
    
        return False 
    except:
        print "Unexpected error:", sys.exc_info()[0]
        return False 

    print "\n\t DEBUG 1 docear return title:", res_cmd 

    if res_cmd != None:
        return res_cmd
    else:
        return False 
   

# If the title is uknown try to get it from Docer
# Elsevier gets journal names bigger than title 
if (title=="Unknown title"  or title == '' or title ==' ' ) and publisher != 'Elsevier':
    docearTitle = getDocearTitle(filename)
    if docearTitle != False :
        title = docearTitle


# Now time to set the file name



def  get_filename_prefix_str(filepath):
    print "\n\t\t DEBUG LEVEL 2 finding filename prefix for filepath =[",filepath,"]"

    # Deals with files that were alreadt renamed by this software 
    filename_prefix_index= filepath.find("(only able to retrieve")
    if filename_prefix_index > 1:
        print "Warning: it was already renamed"
        return  filepath[:filename_prefix_index] 

    filename_prefix_index= filepath.find("(unable to retrieve any meta-data)")
    if filename_prefix_index > 1:
        print "Warning: it was already renamed"
        return  filepath[:filename_prefix_index] 

    # Otherwise returm the string until the first .pdf
    filename_prefix_index= filepath.find(".pdf")
    
    if filename_prefix_index > 1:
        print "\n\t\t DEBUG LEVEL 2 filename prefix = ", filepath[:filename_prefix_index] 
        return  filepath[:filename_prefix_index] 
    
    else:
        print "Extension error: is it name .pdf?"
        sys.exit()

    

## Nothing is known 
if author=='Unknown author' and year=='Unknown'  and title=='Unknown title' and publication=='Unkown publication' and publisher=='Unkown publisher':
    newname = get_filename_prefix_str(filename)  + "(unable to retrieve any meta-data).pdf"
    print "\t\n--Unable--"

## Only one field is known 
elif author=='Unknown author' and year!='Unknown'  and title=='Unknown title' and publication=='Unkown publication' and publisher=='Unkown publisher':
    newname = get_filename_prefix_str(filename)  + "(only able to retrieve year from  meta-data).pdf"
    print "\t\n--Able to get year only--"

elif author!='Unknown author' and year=='Unknown'  and title=='Unknown title' and publication=='Unkown publication' and publisher=='Unkown publisher':
    newname = get_filename_prefix_str(filename) + "(only able to retrieve author from  meta-data).pdf"
    print "\t\n--Able to get author only--"

elif author=='Unknown author' and year=='Unknown'  and title!='Unknown title' and publication=='Unkown publication' and publisher=='Unkown publisher':
    newname = get_filename_prefix_str(filename)  + "(only able to retrieve title from meta-data).pdf"
    print "\t\n--Able to get title only--"
    

elif author=='Unknown author' and year=='Unknown'  and title=='Unknown title' and publication!='Unkown publication' and publisher=='Unkown publisher':
    newname = get_filename_prefix_str(filename)  + "(only able to retrieve publication from meta-data).pdf"
    print "\t\n--Able to get publication only--"

elif author=='Unknown author' and year=='Unknown'  and title=='Unknown title' and publication=='Unkown publication' and publisher!='Unkown publisher':
    newname = get_filename_prefix_str(filename)  + "(only able to retrieve publisher from meta-data).pdf"
    print "\t\n--Able to get publisher only--"


## If at least author and year is known but not the title -> use the filename as differenciator 

elif author!='Unknown author' and year!='Unknown' and title=='Unknown title':
    str_prefix_tmp =  get_filename_prefix_str(filename)

    "use the 15 chars of the origital file name as the differenciator"
    str_prefix_tmp = str_prefix_tmp[:15]
    
    newname = author + " " + year + " " + "(unknown title) ["+  str_prefix_tmp +"]" + " @" + publication + ". " + publisher + ".pdf"
    print "\t\n--Able to get at least author and year--"



## If at least title is known

elif title!='Unknown title' :
    newname = os.path.dirname(filename) + "/" +  author + " (" + year + ") " + title  + " @" + publication + ". " + publisher + ".pdf"
    print "\t\n--Able to get at least get the author  year--"


## Able to get all information

elif author!='Unknown author' and year!='Unknown'  and title!='Unknown title' and publication!='Unkown publication' and publisher!='Unkown publisher':

    newname = os.path.dirname(filename)  + "/"  + author + " (" + year + ") " + title  + " @" + publication + ". " + publisher + ".pdf"
    print "\t\n--Able to get all necessary metadata--"

else:
    print "ERROR, unable to get necessart information to perform an remanme"
    sys.exit(-1)

# Validate the new file name


print "\n\t DEBUG LEVEL 1 - oldFileName ["+ filename+"]"
print "\n\t DEBUG LEVEL 1 - newName before validation["+ newname+"]"

newFileNameBase= newname[len(os.path.dirname(filename)):]

# Remove the / that apears often in doi 
print "\n\t DEBUG LEVEL 1 - newFileNameBase (newName before validation) before removing /: ["+newFileNameBase+"]"

newFileNameBase = newFileNameBase.replace('/',' ')
print "\n\t DEBUG LEVEL 1 - newFileNameBase (newName before validation)  after removing /: ["+newFileNameBase+"]"

newFileNameBase= removeDisallowedFilenameChars(newFileNameBase)
print "\n\t DEBUG LEVEL 1 - newFileNameBase  after removing disallowed charts            : [" +newFileNameBase+"]"

newFileNameBase=newFileNameBase.lstrip(' ')
newFileNameBase=newFileNameBase.lstrip('\t')
newFileNameBase=newFileNameBase.lstrip('\n')

print "\n\t DEBUG LEVEL 1 - newFileNameBase  after removing ' ', '\n', '\t'              : [" +newFileNameBase+"]"




# As mac and windows maximum characters name length is 260
# It's better  to get the first 128 char on the left, the last 128 char on the right  and  add '...' in the midle
# Not implemented yet

if len(newFileNameBase) > 200:
    print "\n WARNING - newFileNameBase name longer that 200 char"
    pre = newFileNameBase[:100]
    suf = newFileNameBase[-95:]
    print "pre=", pre 
    print "suf=", suf
    newFileNameBase =  pre + "..." +  suf

print "\n\t DEBUG LEVEL 1 - newFileNameBase  after resize                                :["+newFileNameBase+"]"


newname= os.path.join(os.path.dirname(filename),newFileNameBase)
print "\n\t DEBUG LEVEL 1 - final new file name =", newname

os.rename(filename,newname)        
print "\n\tRES: ",filename," renamed to ", newname
    
## Title and something else 
    
print 'END' 


