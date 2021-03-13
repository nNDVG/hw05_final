# Description
### Yatube Project
#### A social network with registration, where users can publish posts grouped by topic, with the ability to leave comments on posts, as well as subscribe to interesting authors. 
#### An API was also developed for this project based on the Django REST framework: https://github.com/nNDVG/api_final_yatube

# Run
## To install on a local computer, you must:
#### Download project files from the repository or clone it: https://github.com/nNDVG/hw05_final.git
#### Being in the project directory (in the same directory with the "manage.py" file):
* Create a virtual environment (depending on your operating system) and load all dependencies from the file with the command:
 - pip install -r requirements.txt 

* Create new migrations run the following commands (In the same directory):
 - python manage.py makemigrations
 - python manage.py migrate
* After all the above commands, you can run the app enter command:
 - python manage.py runserver 
  
# Tests
### Run the command in the project directory (with file the "pitest.ini" file:
 - pytest


# Author
 - https://github.com/nNDVG/
 - https://hub.docker.com/u/ndvg/

# Tech stack:
* Python
* Django
* Django REST

