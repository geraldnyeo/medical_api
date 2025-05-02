const express = require('express');

const app = express();
const port = 3000;

app.get("/", (req, res) => {
    res.send("Medical Notes Analytics Backend");
})

app.get("/patient", (req, res) => {
    const id = req.query.id;

    const data = {
        patientID: id,
        name: "Amy Tan",
        age: 20,
        gender: "Female",
        ethnicity: "Chinese",
        serviceType: "Regular",
        rank: "CFC",
        pes: "E9",
        vocation: "Supply Assistant",
        reason: "ORD FFI (Dental)",
        rawText: "Routine dental check completed without X-rays. No active dental pathology, caries, or signs of acute infection detected.",
        data: {
            tokens: [
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
                ".",
            ],
            labels: [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1],
        },
    }

    res.setHeader("Content-Type", "application/json");
    res.send(data);
})

app.listen(port, () => {
    console.log(`Server running on port ${port}.`);
})

module.exports = app;