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
    a = {
        **locals()
    }
    print(a)

    if medicalCentre != None:
        try:
            clinical_notes = db["clinical_records"].find({
                **locals()
            })
            clinical_notes = [{k: v for k, v in entry.items() if k != "_id"} for entry in clinical_notes]
        except Exception as e:
            raise HTTPException(status_code=500, detail="Unable to fetch data from database.")
    else:
        raise HTTPException(status_code=404, detail="No criteria selected.")

    return clinical_notes


@app.get("/testing", status_code=status.HTTP_200_OK)
def test_ner():
    annotate_ner("Name: Kai Ming Tan\nAge: 60\nGender: Male\nEthnicity: Chinese\nReason: Report Sick\nHOPCt:\nThe patient reports acute onset of left ankle pain and functional limitation following a torsional injury sustained during a shipboard drill 24 hours prior. He describes localized pain exacerbated by weight-bearing activities, particularly dorsiflexion and external rotation of the ankle. Symptoms include progressive edema and difficulty ambulating without assistance. Denies prior history of ankle trauma or instability. Reports intermittent paraesthesia over the dorsum of the foot but no frank numbness or vascular compromise.\n\nO/e:\n- Inspection: Moderate edema and ecchymosis over the anterolateral aspect of the left ankle, consistent with traumatic soft tissue injury. Antalgic gait observed.\n- Palpation: Tenderness localized to the distal tibiofibular syndesmosis, with no crepitus or bony irregularities. Negative posterior malleolar tenderness.\n- Range of Motion: Pain-limited dorsiflexion (reduced to 5° vs. 15° on contralateral side) and plantarflexion (30° vs. 40°). Passive external rotation elicits sharp pain at the syndesmosis.\n- Special Tests: Negative anterior drawer test (no talar shift), negative squeeze test (no syndesmotic widening), and stable Mortise joint on stress examination.\n- Neurovascular: Distal pulses palpable, capillary refill <2 seconds, no motor deficits.\n\nImpression:\nAcute Grade II Sprain of the Distal Tibiofibular Ligament (Syndesmotic Injury), Left Ankle\n- Mechanism consistent with forced external rotation and dorsiflexion.\n- Clinical stability preserved, indicating partial ligamentous tear without diastasis.\n\nPlan:\n1. Acute Management:\n- RICE Protocol: Rest, ice application (15–20 minutes q4h), compression bandage, and elevation to mitigate edema.\n- Pharmacotherapy: Oral NSAIDs (Celecoxib 200 mg BD for 5 days) for analgesia and anti-inflammatory effect.\n- Immobilization: Ankle brace with lateral stabilization to limit syndesmotic stress during ambulation.\n\n2. Medical Leave:\n- Medical Certificate (MC): 7 days to facilitate reduced weight-bearing and tissue healing.\n- Light Duty (LD): 14 days post-MC, restricting prolonged standing, ladder climbing, and heavy lifting.\n\n3. Investigations:\n- X-ray left ankle (AP/lateral/mortise views) ordered to exclude occult malleolar fracture or syndesmotic diastasis.\n\n4. Rehabilitation:\n- Referral to physiotherapy for progressive proprioceptive training, peroneal strengthening, and gait normalization after acute phase.\n\nFollow-up:\n- Re-evaluate in 7 days for reassessment of edema, pain severity, and functional capacity.\n- If persistent instability or pain >4/10 VAS, consider MRI to assess ligament integrity and orthopedic consultation.\n- Advise strict adherence to brace use during duty and gradual return to activity guided by physiotherapy.\n- Educate on signs of compartment syndrome (e.g., escalating pain, pallor) requiring urgent review.\n\n---\nNote: PES status remains unchanged. Prognosis favorable with compliance to rehabilitation.")

    return "completed"
    

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)