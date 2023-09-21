# Clean the test-dats
echo Running "git clean -f test-data"

git clean -f test-data

sleep 1

echo git restore test-data/
git restore test-data/


