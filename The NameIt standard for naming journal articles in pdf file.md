# The NameIt standard for naming journal articles in a pdf file

## Overview 

According to the NameIt standard, research journal articles in pdf file should be named by 

**Author(s) (year). Title. Publication, Publisher.** 




## Related standards 

### APA

The NameIT standard lended from the [Publication Manual of the American Psychological Association, Seventh Edition](https://apastyle.apa.org/products/publication-manual-7th-edition). However the filename does not include the issue, volume or DOI. Instead it includes the publisher. 

According to [APA 7th style](https://apastyle.apa.org/style-grammar-guidelines/references/examples/journal-article-references), the work of Grady et al. (2019) should be in a listed in a references list as 

>Grady, J. S., Her, M., Moreno, G., Perez, C., & Yelinek, J. (2019). Emotions in storybooks: A comparison of storybooks that represent ethnic and racial groups in the United States. *Psychology of Popular Media Culture, 8*(3), 207–217. https://doi.org/10.1037/ppm0000185

According to the NameIt standard such article in pdf format should be file-named as 

`"Grady et al. (2019). Emotions in storybooks: A comparison of storybooks that represent ethnic and racial groups in the United States. Psychology of Popular Media Culture, American Psychological Association.pdf"

Note that by not listing all authors we save filename space and we avoid DOIs and URLs as they are problemantic for filenames (e.g., the caracter '/'  can be understood as a folder path in many filesystems). 

### Operating System Filesystems 

We suport the **ext3, ext4, xfs, zfs, NTFS, APFS, HFS+ and xFAT** filesystems and therefore we constrained by them. 

Some filesystems restrict the length of filename 

###  Unicode and Python

We adopt [unicode](https://home.unicode.org/) as a standard for encoding file names so you can move them between different filesystems and operating systems. 

The actual renaming of the filenames is handled by the python os Miscellaneous operating system interfaces[https://docs.python.org/3/library/os.html] library. 












