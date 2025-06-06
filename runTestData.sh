# Run test data
# Renames the files in the test-data folder using NameIt and tests id they are renamed according the nameIt standard as expexted 

echo ""
echo "checking if test-data files are there"
echo "" 

FILE1=test-data/ecis-2025.pdf
FILE2=test-data/s13174-019-0105-z.pdf
FILE3=test-data/s13174-019-0105-z.pdf
FILE4='test-data/AI Magazine - 2023 - Khan.pdf'
FILE5=test-data/s13174-015-0028-2.pdf
FILE6=test-data/s13174-019-0105-z.pdf
FILE7=test-data/test.txt

test -f "$FILE1"             && echo "$FILE1 exists." || { echo  "$FILE1 do not exist. "; echo  "ABORTING TESTS" ; exit ;  }
test -f "$FILE2"             && echo "$FILE2 exists." || { echo  "$FILE2 do not exist. "; echo  "ABORTING TESTS" ; exit ;  }
test -f "$FILE3"             && echo "$FILE3 exists." || { echo  "$FILE3 do not exist. "; echo  "ABORTING TESTS" ; exit ;  }
test -f "$FILE4"             && echo "$FILE4 exists." || { echo  "$FILE4 do not exist. "; echo  "ABORTING TESTS" ; exit ;  }
test -f "$FILE5"             && echo "$FILE5 exists." || { echo  "$FILE5 do not exist. "; echo  "ABORTING TESTS" ; exit ;  }
test -f "$FILE6"             && echo "$FILE6 exists." || { echo  "$FILE6 do not exist. "; echo  "ABORTING TESTS" ; exit ;  }
test -f "$FILE7"             && echo "$FILE7 exists." || { echo  "$FILE7 do not exist. "; echo  "ABORTING TESTS" ; exit ;  }


sleep 1

echo ""
echo ":) test-data files exist "
echo ""

sleep 1

echo ""
echo "renaming now the files"
echo ""

echo renaming $FILE1; 
./NameIt $FILE1
echo

echo renaming $FILE1; 
./NameIt $FILE2
echo

echo renaming $FILE1; 
./NameIt $FILE3
echo

echo renaming $FILE1; 
./NameIt $FILE4
echo

echo renaming $FILE1; 
./NameIt $FILE5
echo

echo renaming $FILE1; 
./NameIt $FILE6
echo

echo renaming $FILE1; 
./NameIt $FILE7
echo

sleep 1

echo "checking if the filename is now the  expected one"

