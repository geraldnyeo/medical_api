import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pymongo import MongoClient

from langchain_deepseek import ChatDeepSeek

from medical_annotation import annotate_llm

# Connect to MongoDB
MONGO_PASSWORD = "m8pWxZ4g5W7p7Edd"
DATABASE_NAME = "patient_records"
uri = f"mongodb+srv://geraldnyeo:{MONGO_PASSWORD}@medical-notes-analysis.nziqawg.mongodb.net/?retryWrites=true&w=majority&appName=Medical-Notes-Analysis"
client= MongoClient(uri)
db = client[DATABASE_NAME]

# FastAPI
app = FastAPI()

# CORS
origins = ["*"] # enable all
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PATHS
@app.get("/")
async def root():
    return {
        "message": "Medical Notes Analysis Backend"
    }

@app.get("/patient")
async def retrieve_patient_data(
    id: str | None = None, 
    name: str | None = None, 
    hist: int = 1):
    """
    Retrieves patient details and all associated clinical notes
    """
    if id != None:
        try:
            patient_data = db["patient_data"].find_one({
                "patientID": id
            })
            patient_data = {k: v for k, v in patient_data.items() if k != "_id"}
        except Exception as e:
            raise HTTPException(status_code=404, detail="Patient ID not found.")
    elif name != None:
        try:
            patient_data = db["patient_data"].find_one({
                "name": name
            })
            id = patient_data["patientID"]
            patient_data = {k: v for k, v in patient_data.items() if k != "_id"}
        except Exception as e:
            raise HTTPException(status_code=404, detail="Patient name not found.")
    else:
        raise HTTPException(status_code=404, detail="No name or ID provided.")
    
    if hist != 0:
        try:
            patient_notes = db["clinical_records"].find({
                "patientID": id
            })
            patient_notes = [{k: v for k, v in entry.items() if k != "_id" and k != "patientID"} for entry in patient_notes]

            patient_records = {
                **patient_data,
                "history": patient_notes
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail="Unable to fetch data from database.")
    else:
        patient_records = patient_data

    return patient_records

class Record(BaseModel):
    recordID: str
    patientID: str
    reason: str
    text: str

@app.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_clinical_record(record: Record):
    try:        
        record_dict = record.dict(by_alias=True)
        record_dict["rawText"] = record_dict.pop("text")

        annotation_modes = {
            "ORD FFI (Dental)": "ffi_dental",
            "ORD FFI (Medical)": "ffi_medical",
            "PES Review (Upgrade)": "pes_upgrade",
            "PES Review (Downgrade)": "pes_downgrade",
            "Report Sick": "sick"
        }
        # TODO: FIX THIS
        # if record_dict["reason"] in annotation_modes.keys():
        #     annotation_mode = annotation_modes[record_dict["reason"]]
        # else:
        #     annotation_mode = "append"
        annotation_mode = "append"

        tokens, labels = annotate_llm(record_dict["rawText"],
                                      mode = annotation_mode)
        record_dict["data"] = {
            "tokens": tokens,
            "labels": labels
        }

        db["clinical_records"].insert_one(record_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create clinical record.")

    return "Patient record uploaded"

class Patient(BaseModel):
    patientID: str
    name: str
    age: str
    gender: str
    ethnicity: str
    serviceType: str
    rank: str
    pes: str
    vocation: str

@app.post("/patient", status_code=status.HTTP_201_CREATED)
def create_new_patient(patient: Patient):
    patient_dict = patient.dict(by_alias=True)    
    id = patient_dict["patientID"]

    d = db["patient_data"].find_one({ 
        "patientID": id 
    })
    if d != None:
        raise HTTPException(status_code=500, detail="Failed to create patient record.")

    try:    
        db["patient_data"].insert_one(patient_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create patient record.")
    
    return "Clinical record uploaded"

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)