# The NameIt standard for naming journal articles in a pdf file

## Overview 

According to the NameIt standard, research journal articles in pdf file should be named by 

**Author(s) (year). Title. Publication. Publisher.** 

## Authors 

* Author names can be expressed using the Unicode character set and UTF-8 encoding (e.g., Apolinário, Widèn). In other words, NameIt accepts accents (e.g., Å á ê ò) and other often problematic characters. 

* Authors are just refered by their surname to save filename space.
* 
  - José A. Teixeira -> named just Teixeira. 
  - Teixeira, J. -> named just Teixeira.
  - Teixeira, A. J. -> names just Teixeira. 

* If an article have more than two authors, the filename will start with the first author surname followed by et al. to save filename space.

## Year 

* Is included in the filename between brakets '(' ')'.

* Limited to 4 numerical caracters (e.g., 1993, 1439).

* NameIt raises an error if a article is published in a year over current year. 

## Title 

* Needs to be often cut due to the restriction of the size of the filename to 255 characters.

* Problematic characters that have a special meaning for operating systems (e.g., / \ " ' * ; - ? [ ] & ) need to be encoded in Unicode using UTF8. 

## Publication 

* Usually they are not so long as titles, but some publishers often abreviate them (Advances in Behavioral Biology 	becomes Adv. Behav. Biol.).  The NameIt standard **avoids journal name abreviations** as different
  organizations abreviate them in different ways. 

## Publisher 

* There are not some many them as the big publishing houses have been buying the small family owned publishing houses over the years.

* They are often redundant and NameIT should pick the shorter version to save filename space

- Springer International Publishing -> will named just Springer.
- Sage UK -> will be name just Sage.
- Association for Information Systems (AIS) -> will be named just AIS.
- Association for Computing Machinery (ACM) -> will be named just ACM.
- Institute of Electrical and Electronics Engineers -> will be named just IEEE.
- Cambridge, MIT Press  -> will be just MIT Press. 

Note: That due to the restriction of the size of the filename to 255 characters, Name it will try to cut on the "title" instead of author, year or publication. 

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

Some filesystems restrict the length of filename. We **restrict the size of the filename to 255 characters** as they will work with most modern filesystems and operating systems. 

Certain characters have special meaning for operating systems. Avoid using these characters when you are settign the title of a research article. You can encode them using escape caracters, but you lose space from the filename for everytime the article title contains one of those caracters. 

These characters include the following:

 `/ \ " ' * ; - ? [ ] ( ) ~ ! $ { } &lt > # @ & | space tab newline`

Note that the NameIt standart is case sensitive. Uppercase and lowercase are both welcome. 

###  Unicode, UTF8, and Python

We adopt [unicode](https://home.unicode.org/) and [UTF8](https://en.wikipedia.org/wiki/UTF-8) as standards for encoding file names so you can move them between different filesystems and operating systems. 

The actual renaming of the filenames is handled by the [python os - Miscellaneous operating system interfaces](https://docs.python.org/3/library/os.html) library. 









