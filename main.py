import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/")
async def root():
    return {
        "message": "Medical Notes Analysis Backend"
    }

@app.get("/patient")
async def retrieve_patient_data(id: int):
    print(id)

    data = {
        "patientID": id,
        "name": "Amy Tan",
        "age": 20,
        "gender": "Female",
        "ethnicity": "Chinese",
        "serviceType": "Regular",
        "rank": "CFC",
        "pes": "E9",
        "vocation": "Supply Assistant",
        "reason": "ORD FFI (Dental)",
        "rawText": "Routine dental check completed without X-rays. No active dental pathology, caries, or signs of acute infection detected.",
        "data": {
            "tokens": [
                "Routine",
                "dental",
                "check",
                "completed",
                "without",
                "X-rays",
                ".",
                "No",
                "active",
                "dental",
                "pathology",
                ",",
                "caries",
                ",",
                "or",
                "signs",
                "of",
                "acute",
                "infection",
                "detected",
                "."
            ],
            "labels": [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1]
        }
    }

    return data

class Record(BaseModel):
    patientID: int
    reason: str
    text: str

@app.post("/upload")
def upload_clinical_record(record: Record):
    print(record)

class Patient(BaseModel):
    patientID: int
    name: str
    age: str
    gender: str
    ethnicity: str
    serviceType: str
    rank: str
    pes: str
    vocation: str

@app.post("/patient")
def create_new_patient(patient: Patient):
    print(patient)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)