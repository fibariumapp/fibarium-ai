HELLO

venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip list
deactivate
pip freeze > requirements.txt