This application is a centralized, responsive search and data management portal. It embeds a main data archive via an iframe and provides an interface that allows users to trigger an asynchronous back-end Python pipeline script to update the underlying data repository on demand. This application works on a Blogspot blog, https://globalwarming-arclein.blogspot.com/. As Blogger is mainly a publishing platform, not a real app backend. Blogger holds the posts; our app handles search, tags, categories, and UI. 

This directory contains the code that was used to copy Blogger blog posts to a database, 

This code copies the blog posts at  to an SQLite database, insights.db.
 
The update-pipeline.py script will update the databse, adding only new articles from the blog. If the database is empty it should try to copy all the posts from the blog.

To run the Python code on Linux (should be very similar on Mac),

Copy the project folder and files to your computer

#chown -R [user name]:[user name] code
#(on the current AWS server, the username is : ubuntu)
chown -R ubuntu:www-data code

cd flask_app

#if you need to use a virtual environment, run these two lines
python3 -m venv venv
source venv/bin/activate

At the time of this writing, this application is up and running at https://globalwarming-arclein.duckdns.org/ or access the blog https://globalwarming-arclein.blogspot.com/ and using the 'Search' interface. You can also view the insights.db file directly. I use a program called DB Browser for SQLite, it is free, open source, cross platform.
