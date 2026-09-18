python3 -m venv .venv
source .venv/bin/activate

python --version        # confirm 3.14.7 (or 3.12 if you switch)
which python            # must show .../.venv/bin/python

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

brew install libmagic
