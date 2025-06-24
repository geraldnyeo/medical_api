<!-- About the Project -->
# Medical Notes Analytics API

Backend API for [Medical Notes Analytics](https://github.com/iwtf-04/medical_notes_analytics). Features include:
* Document annotation
* Fetching / storing data from MongoDB database

### Table of Contents


## About the Project


### Built With
[FastAPI](https://fastapi.tiangolo.com/)
[MongoDB](https://www.mongodb.com/https://www.mongodb.com/)
[LangChain](https://www.langchain.com/)
[SparkNLP](https://sparknlp.org/)


### Summary of Analysis Methods


## Getting Started
This project uses a few external services, which you have to set up before you can use the project.

### Prerequisites
- Linux-like terminal environment (e.g., WSL2 on Windows, which this project was developed on)
- Python 3.12 (for WSL2 users, ensure that your wsl terminal is capable of using the python command)

#### Windows Prerequisite Setup
1 | [Install WSL2](https://learn.microsoft.com/en-us/windows/wsl/install)
2 | Setup Python for WSL2
 - Navigate to your WSL2 terminal
 - Install python3, pip and venv
 ```
 sudo apt-get update
 sudo apt install python3
 sudo apt install python3-pip
 sudo apt install python3-venv
 ```

### Deepseek API Key
In order to use this project, you need a Deepseek API key. Please refer to this website to get one: [Deepseek API Docs](https://api-docs.deepseek.com/)

### MongoDB Cluster
In order to use this project, you will need to set up a MongoDB cluster. Wehn prompted, save your username and password. You will need this later.

#### Creating your database
1. Create one database, name it anything you want. Remember this name for later.
2. Create two collections: "patient_data" and "clinical_records". There is no need to add any data for now.

#### Connecting to Your Cluster
1. Find the "connect" button on the front page of your cluster. 
2. You will be prompted to select a connection method. Select "Drivers".
3. Choose the "Python" driver, use the latest version.
4. The driver installation will be installed later with your environment setup, so don't worry about it.
5. Save the connection string. Replace the database username and password with your username and password. This is your connection URI.

### Environment Variables
Create a .env file in the /src directory of this project. Add the following environment variables:
DATABASE_NAME="YOUR_DATABASE_NAME"
MONGODB_URI="YOUR_MONGODB_CONNECTION_URI"
DEEPSEEK_API_KEY="YOUR_DEEPSEEK_API_KEY"

### Using NER Models
In order to use the NER models, you will have to download them yourself from the NER model training project, as they are too large to be stored on github. Please refer to the README on that project for instructions.

Save all the models to /src/models. Modify the file paths under the "annotate_ner" in medical_annotation.py to match. You should have the following models:
 - One ner_pipe model - the preprocessing / embeddings model
 - Fifteen ner models - the entity extraction models, one for each combination of label type "SYM/DIA/TRT" and category "ffi_dental/ffi_medical/pes_downgrade/pes_upgrade/sick".

#### Using LLM Models
Currently, the project is set up for using NER models for entity extraction. If you wish to use LLM models instead, you will have to modify the code yourself. Find the "upload_clinical_record" function in main.py, and comment / uncomment the relevant code. It has been clearly marked for you.

### Running Locally
The following instructions are for WSL2 terminal. Ensure you are in the root directory of the project.

1 | Create a python venv (if not done before)
```
python3 -m venv env
```
- This will create an "env" folder in the root directory.
2 | Activate venv
```
source env/bin/activate
```
- Your terminal should now show a "(env)" at the start of the line.
3 | Install pip dependencies (if not done before)
```
python3 -m pip install -r requirements.txt
```
4 | Navigate to src folder
```
cd src
```
5 | Run
```
python3 main.py
```

You can test if the project is running successfully by using the following curl commands from the /src directory:

**Test if server is live**
```
curl 0.0.0.0:8000/
```
- You should return the following response: {"message":"Medical Notes Analysis Backend"}

**Test if annotation is working**
```
curl 0.0.0.0:8000/upload -X POST -H "Content-Type: application/json" -d @test_add_patient.json
```
- You must run this first, to create a patient.

```
curl 0.0.0.0:8000/upload -X POST -H "Content-Type: application/json" -d @test_upload.json
```

### Running with Docker
The following instructions are for WSL2 terminal.

1. Install [Docker Desktop](https://docs.docker.com/desktop/)
2. Please refer to these [installation instructions](https://docs.docker.com/desktop/features/wsl/) for using Docker Desktop with WSL2.


### Notes on Python Packages
These versions should already be contained within the requirements.txt file. It is important that you use these version numbers, NOT the latest or default versions, for the program to run properly.
* spark-nlp version: 6.0.2
* pyspark version: 3.5.1
* py4j version: 0.10.9.7 (should be automatically installed when you install pyspark 3.5.1)
