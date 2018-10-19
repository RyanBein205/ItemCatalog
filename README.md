# Installation of Dependancies
- This Program is designed for Python 2.7 you must goto the website @ https://www.python.org/download/releases/2.7/
Select the proper installer for your machine.

- To Install the Flask Application for Python required to run this application Open your Terminal and enter "pip install Flask". Installation Documentation can be found @ http://flask.pocoo.org/docs/1.0/installation/

- To Install the SQLAlchemy application for Python required then open your Terminal and enter "pip install SQLAlchemy".
Documentation can be found here https://docs.sqlalchemy.org/en/latest/intro.html

- After downloading the Files. Extract them to a known location. Run the File named **"db_setup"** to setup the database for the application's use. This will create a SQL database File named **"categorywithusers.db".** This file will hold your data from the Flask application.

## **Running the Program**

- Once the **"db_setup.py"** file has been executed and you succesfully have the database file located. Now is time to setup your Flask Application.
- Run the File named **"ItemCatalog.py"**. This file is the Flask Application that will handle your traffic and transactions.

## **Usage**

- The Application will Seperate data into Categories or Items within a Category.
- Each Category has a JSON Endpoint for WebScraping for those of you developers out there.
-The Templates Folder located within the Downloaded files provide the HTML endpoints for the Web Application.
- The Static Folder located within the Downloaded Files provide the Images and CSS for the Web Application with you may also adjust to pretty up your Application.

# **Contributions/Research**

- A Grand thanks to Udacity.com for the knowledge to implement a Flask based application for handling web traffic and Oauth Procedures.

- A Special thanks to the Markdown Guide from Udacity.com for the extra hand writing a detailed document for readers.