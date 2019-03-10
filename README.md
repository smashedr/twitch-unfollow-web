# Twitch Unfollow Alerts

[![build status](https://git.cssnr.com/shane/twitch-unfollow-web/badges/master/build.svg)](https://git.cssnr.com/shane/twitch-unfollow-web/commits/master) [![coverage report](https://git.cssnr.com/shane/twitch-unfollow-web/badges/master/coverage.svg)](https://git.cssnr.com/shane/twitch-unfollow-web/commits/master)

This tool alerts you on Discord of unfollows on Twitch.

### Frameworks

- Django (2.1.2) https://www.djangoproject.com/
- Celery (4.2.0) http://www.celeryproject.org/
- Bootstrap (4.1.3) http://getbootstrap.com/
- Font Awesome (5.4.2) http://fontawesome.io/

# Development

### Deployment

To deploy this project on the development server:

```
git clone https://git.cssnr.com/shane/twitch-unfollow-web.git
cd django-twitch
pyvenv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp settings.ini.example settings.ini
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata site-fixtures.json
python manage.py loaddata social-fixtures.json
python manage.py runserver 0.0.0.0:8000
```

*Note: Make sure to update the `settings.ini` with the necessary details...*

### Copying This Project

To clone a clean copy of this project int your repository:

```
git clone https://git.cssnr.com/shane/twitch-unfollow-web.git
cd django-twitch
rm -rf .git
git init
git remote add origin https://github.com/your-org/your-repo.git
git push -u origin master
```

*Note: make sure to replace `your-org/your-repo.git` with your actual repository location...*
