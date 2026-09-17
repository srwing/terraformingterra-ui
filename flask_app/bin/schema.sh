#! /bin/bash
sqlite3 ~/flask_app/insights.db ".schema" | less #> schema.sql
