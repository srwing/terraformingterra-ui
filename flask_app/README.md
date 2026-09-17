install required Python libraries.

pip install -r requirements.txt

Note : On some servers you may receive a pip error, "not enough space" error. To fix this error, by forcing pip to use a folder on your main partition, you need to redirect the temporary unpacking directory and bypass the cache directory by running : mkdir -p /pip_tmp pip install --no-cache-dir --cache-dir=/pip_tmp -r requirements.txt

To make this database availiable from the Blogspot website, a HTML certificate and a publicly availiable DNS address are required. To achieve this a certificate was created with Certbot (certbot.eff.org) and the DNS hosted with Duck DNS (duckdns.org) - these are free services.

As a lot of servers block access to secure HTTP (https), the Nginx (nginx.org) project was used to expose the project and database to the internet

The confirguration(s) for duckdns, certbot, and nginx are described in the file, duckdns_certbot_nginx_setup.txt.

There are a couple services that when setup will automatically keep the program running if the server is restarted. Instructions for seting these services up is in the amacon folder.

The blogspot_interface.html contains the code that is currently running on the blog in an HTML/JavaScript widget.

As this application is a work in progress, there are a couple scripts that need to be run after the database has initially been generated : category-pipeline.py create_FTS.py - * important * do not run this code if the database already contains tables with the fts string in the name. generate_embeddings.py create_indexs.py

This application is currently up and running at https://globalwarming-arclein.duckdns.org/ . You can also view the insights.db file directly. I use a program called DB Browser for SQLite, it is free, open source, cross platform.
