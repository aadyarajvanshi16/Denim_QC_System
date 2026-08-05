// ============================================
// LIVE QUALITY CAMERA
// ============================================

let stream = null;
let inspectionInterval = null;

// ============================================
// UPLOAD REFERENCE IMAGE
// ============================================

function uploadReference() {

    const input = document.getElementById("reference_input");

    const file = input.files[0];

    if (!file) {
        alert("Please select a reference image.");
        return;
    }

    // Show preview immediately
    document.getElementById("reference_preview").src =
        URL.createObjectURL(file);

    const formData = new FormData();

    formData.append("reference", file);

    fetch("/upload_live_reference", {
        method: "POST",
        body: formData
    })
    .then(response => {

        if (!response.ok) {
            throw new Error("Upload failed");
        }

        return response.json();

    })
    .then(data => {

        console.log(data);

        alert("Reference image uploaded successfully!");

    })
    .catch(error => {

        console.error(error);

        alert("Upload failed!");

    });

}

// ============================================
// START CAMERA
// ============================================

async function startCamera() {

    const video = document.getElementById("video");

    try {

        stream = await navigator.mediaDevices.getUserMedia({
            video: true
        });

        video.srcObject = stream;

    }

    catch (err) {

        alert("Unable to access camera!");

        console.log(err);

    }

}

// ============================================
// START PHONE CAMERA (RTSP via MediaMTX)
// ============================================

async function startPhoneCamera() {

    const video = document.getElementById("video");

    try {

        const connection = new RTCPeerConnection();

        connection.ontrack = function(event) {
            video.srcObject = event.streams[0];
        };

        connection.addTransceiver('video', { direction: 'recvonly' });

        const offer = await connection.createOffer();
        await connection.setLocalDescription(offer);

        const response = await fetch("http://localhost:8889/live/denim_cam/whep", {
            method: "POST",
            headers: { "Content-Type": "application/sdp" },
            body: connection.localDescription.sdp
        });

        const answerSdp = await response.text();

        await connection.setRemoteDescription({
            type: "answer",
            sdp: answerSdp
        });

    }

    catch (err) {

        alert("Unable to connect to phone camera!");

        console.log(err);

    }

}

// ============================================
// START LIVE INSPECTION
// ============================================

function startInspection() {

    alert("Inspection Started!");

    if (inspectionInterval != null) {
        clearInterval(inspectionInterval);
    }

    inspectionInterval = setInterval(
        sendFrame,
        300
    );

}

// ============================================
// SEND FRAME TO FLASK
// ============================================

function sendFrame() {

    const video = document.getElementById("video");

    const canvas = document.getElementById("canvas");

    const ctx = canvas.getContext("2d");

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    ctx.drawImage(
        video,
        0,
        0
    );

    canvas.toBlob(function(blob){

        const formData = new FormData();

        formData.append(
            "frame",
            blob,
            "live.jpg"
        );

        fetch("/live_analyze", {

            method: "POST",

            body: formData

        })

        .then(response => response.json())

        .then(data => {

            console.log("LIVE RESPONSE:", data);

    console.log("Similarity:", data.similarity);
    console.log("Delta E:", data.delta_e);
    console.log("LAB:", data.l, data.a, data.b);
    console.log("Status:", data.status);
    console.log("Confidence:", data.confidence);

            // ==========================
            // UPDATE LIVE RESULTS
            // ==========================

            document.getElementById("similarity").innerHTML =
                data.similarity;

            document.getElementById("deltae").innerHTML =
                data.delta_e;

            document.getElementById("lvalue").innerHTML =
                data.l;

            document.getElementById("avalue").innerHTML =
                data.a;

            document.getElementById("bvalue").innerHTML =
                data.b;

            const status = document.getElementById("status");

            status.innerHTML = data.status;

            if(data.status === "PASS"){

                status.style.background = "#16a34a";
                status.style.color = "white";

            }
            else{

                status.style.background = "#dc2626";
                status.style.color = "white";

            }

            // NEW
            if(document.getElementById("confidence")){
                document.getElementById("confidence").innerHTML =
                    data.confidence;
            }

        })

        .catch(error => {

            console.log("Live Inspection Error:", error);

        });

    }, "image/jpeg");

}

// ============================================
// STOP INSPECTION
// ============================================

function stopInspection() {

    if (inspectionInterval != null) {

        clearInterval(inspectionInterval);

        inspectionInterval = null;

    }

    if (stream) {

        stream.getTracks().forEach(track => track.stop());

        document.getElementById("video").srcObject = null;

        stream = null;

    }

}

// ============================================
// CONNECT RTSP CAMERA
// ============================================

function connectRTSP() {

    const url =
        document.getElementById("rtsp_url").value;

    const formData =
        new FormData();

    formData.append(

        "rtsp",

        url

    );

    fetch(

        "/set_rtsp",

        {

            method: "POST",

            body: formData

        }

    )

    .then(response => response.json())

    .then(data => {

        alert("RTSP Camera Connected!");

        console.log(data);

    })

    .catch(error => {

        console.log(error);

    });

}

// ============================================
// SELECT ROI
// ============================================

function selectROI() {

    alert("Calling Flask...");

    fetch("/select_live_roi", {
        method: "POST"
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
    })
    .catch(error => {
        console.log(error);
        alert(error);
    });

}