import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pymongo import MongoClient

from medical_annotation import annotate_llm, annotate_ner, summarize_llm

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
    patientID: str | None = None, 
    name: str | None = None, 
    hist: int = 1):
    """
    Retrieves patient details and all associated clinical notes
    """
    if patientID != None:
        try:
            patient_data = db["patient_data"].find_one({
                "patientID": patientID
            })
            patient_data = {k: v for k, v in patient_data.items() if k != "_id"}
        except Exception as e:
            raise HTTPException(status_code=404, detail="Patient ID not found.")
    elif name != None:
        try:
            patient_data = db["patient_data"].find_one({
                "name": name
            })
            patientID = patient_data["patientID"]
            patient_data = {k: v for k, v in patient_data.items() if k != "_id"}
        except Exception as e:
            raise HTTPException(status_code=404, detail="Patient name not found.")
    else:
        raise HTTPException(status_code=404, detail="No name or ID provided.")
    
    if hist != 0:
        try:
            patient_notes = db["clinical_records"].find({
                "patientID": patientID
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

class Patient(BaseModel):
    patientID: str
    name: str
    age: int
    gender: str
    ethnicity: str
    serviceType: str
    rank: str
    pes: str
    vocation: str

@app.post("/patient", status_code=status.HTTP_201_CREATED)
def create_new_patient(patient: Patient):
    patient_dict = patient.dict(by_alias=True)    
    patientID = patient_dict["patientID"]

    try:
        d = db["patient_data"].find_one({ 
            "patientID": patientID
        })
        if d != None:
            raise HTTPException(status_code=422, detail="Patient ID already exists.")
    except:
        raise HTTPException(status_code=500, detail="Unable to fetch data from database.")

    try:    
        db["patient_data"].insert_one(patient_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create patient record.")
    
    return "Patient record uploaded"

@app.put("/patient/{patientID}", status_code=status.HTTP_200_OK)
def update_patient_record(patientID: str, patient: Patient):
    update_data = patient.dict(exclude_unset=True, by_alias=True)

    try:
        db["patient_data"].update_one(
            { "patientID": patientID },
            { "$set": update_data }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update patient record.")
    
    if "patientID" in update_data.keys():
        if update_data["patientID"] != patientID:
            try:
                db["clinical_records"].update_many(
                    { "patientID": patientID },
                    { "$set": { "patientID": update_data["patientID"] } }
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail="Failed to update clinical records.")

    return "Patient record updated"


class Record(BaseModel):
    patientID: str
    date: str
    medicalCentre: str
    reason: str
    text: str
    parentID: int | None = None

@app.post("/upload", status_code=status.HTTP_201_CREATED)
def upload_clinical_record(record: Record):
    record_dict = record.model_dump(by_alias=True)

    # get parent ID
    parentID = record_dict.pop("parentID")
    if parentID != None:
        record_dict["parentID"] = parentID

    # get record ID
    try:
        latest_id = db["clinical_records"].find().sort({"recordID": -1}).limit(1)[0]
        recordID = latest_id["recordID"] + 1
        
        record_dict["recordID"] = recordID
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to fetch data from database.")
        
    record_dict["rawText"] = record_dict.pop("text")

    # annotate data
    try:      
        annotation_modes = {
            "ORD FFI (Dental)": "ffi_dental",
            "ORD FFI (Medical)": "ffi_medical",
            "PES Review (Upgrade)": "pes_upgrade",
            "PES Review (Downgrade)": "pes_downgrade",
            "Report Sick": "sick"
        }
        
        if record_dict["reason"] in annotation_modes.keys():
            annotation_mode = annotation_modes[record_dict["reason"]]
        else:
            annotation_mode = "append"

        # tokens, labels = annotate_llm(record_dict["rawText"],
        #                               mode = annotation_mode)

        tokens, labels = annotate_ner(mode = annotation_mode, 
                                      text = record_dict["rawText"],
                                      splitting_mode = "regex") 
        
        for t, l in zip(tokens, labels): print(f"{t:20} {l}")
               
        record_dict["data"] = {
            "tokens": tokens,
            "labels": labels
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to generate labels.")
    
    # summarize text
    try:
        category, summary = summarize_llm(text = record_dict["rawText"], 
                                          splitting_mode = "regex")
        record_dict["category"] = category
        record_dict["summary"] = summary
    except Exception as e:
        raise HTTPException(status_code=500, detail="Unable to generate summary.")
    
    try:
        db["clinical_records"].insert_one(record_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create clinical record.")

    return "Clinical record uploaded"

@app.delete("/record/{recordID}", status_code=status.HTTP_200_OK)
def delete_clinical_record(recordID: int):
    try:
        db["clinical_records"].delete_one({
            "recordID": recordID
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete clinical record.")
    
    return "Clinical record deleted"


@app.get("/findRecord", status_code=status.HTTP_200_OK)
def find_clinical_record(
    medicalCentre: str | None = None,
    category: str | None = None):
    """
    Finds all clinical records corresponding to a certain filter
    """
    filters = {k: v for k, v in locals().items() if v != None}

    if len(filters.keys()) != 0:
        try:
            clinical_notes = db["clinical_records"].find({
                **filters
            })
            clinical_notes = [{k: v for k, v in entry.items() if k != "_id"} for entry in clinical_notes]
        except Exception as e:
            raise HTTPException(status_code=500, detail="Unable to fetch data from database.")
    else:
        raise HTTPException(status_code=404, detail="No criteria selected.")

    return clinical_notes
    

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)