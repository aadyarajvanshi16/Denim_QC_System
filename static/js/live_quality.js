let stream = null;
let inspectionInterval = null;
let pendingRoi = null; // {x,y,w,h} in natural image pixels, awaiting confirmation

// ============================================
// UPLOAD REFERENCE IMAGE
// ============================================
function uploadReference() {
  const input = document.getElementById("reference_input");
  const file = input.files[0];
  if (!file) return;

  const statusEl = document.getElementById("refUploadStatus");
  statusEl.textContent = "Uploading…";

  const formData = new FormData();
  formData.append("reference", file);

  fetchWithCsrf("/upload_live_reference", { method: "POST", body: formData })
    .then((response) => {
      if (!response.ok) throw new Error("Upload failed");
      return response.json();
    })
    .then((data) => {
      statusEl.textContent = "Reference uploaded.";
      const preview = document.getElementById("reference_preview");
      preview.src = URL.createObjectURL(file);
      document.getElementById("refRoiWrap").classList.remove("hidden");

      preview.onload = () => {
        initRoiSelector({
          frameId: "refFrame",
          imgId: "reference_preview",
          boxId: "refBox",
          statusId: "refStatus",
          xId: "__roi_x_placeholder",
          yId: "__roi_y_placeholder",
          wId: "__roi_w_placeholder",
          hId: "__roi_h_placeholder",
        });
      };
    })
    .catch((error) => {
      console.error(error);
      statusEl.textContent = "Upload failed — please try again.";
    });
}

// Because live_quality's ROI needs to be POSTed via fetch (not a form),
// we override the hidden-input approach with a lightweight listener
// that reads the visible roi-box element directly on confirm.
function confirmRoi() {
  const box = document.getElementById("refBox");
  const img = document.getElementById("reference_preview");
  if (box.classList.contains("hidden") || !box.style.width) {
    alert("Draw a region on the reference image first.");
    return;
  }

  const sx = img.naturalWidth / img.clientWidth;
  const sy = img.naturalHeight / img.clientHeight;

  const x = Math.round(parseFloat(box.style.left) * sx);
  const y = Math.round(parseFloat(box.style.top) * sy);
  const w = Math.round(parseFloat(box.style.width) * sx);
  const h = Math.round(parseFloat(box.style.height) * sy);

  if (w < 4 || h < 4) {
    alert("Selected region is too small.");
    return;
  }

  const formData = new FormData();
  formData.append("x", x);
  formData.append("y", y);
  formData.append("w", w);
  formData.append("h", h);

  fetchWithCsrf("/select_live_roi", { method: "POST", body: formData })
    .then((r) => r.json())
    .then((data) => {
      const badge = document.getElementById("roiConfirmStatus");
      if (data.error) {
        badge.textContent = data.error;
        badge.className = "badge badge-fail ms-2";
        return;
      }
      badge.textContent = "ROI Confirmed";
      badge.className = "badge badge-pass ms-2";
    })
    .catch((error) => console.error(error));
}

// ============================================
// CAMERA SOURCES
// ============================================
async function startCamera() {
  const video = document.getElementById("video");
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
  } catch (err) {
    alert("Unable to access camera!");
    console.log(err);
  }
}

async function startPhoneCamera() {
  const video = document.getElementById("video");
  try {
    const connection = new RTCPeerConnection();
    connection.ontrack = (event) => {
      video.srcObject = event.streams[0];
    };
    connection.addTransceiver("video", { direction: "recvonly" });

    const offer = await connection.createOffer();
    await connection.setLocalDescription(offer);

    const response = await fetch("http://localhost:8889/live/denim_cam/whep", {
      method: "POST",
      headers: { "Content-Type": "application/sdp" },
      body: connection.localDescription.sdp,
    });

    const answerSdp = await response.text();
    await connection.setRemoteDescription({ type: "answer", sdp: answerSdp });
  } catch (err) {
    alert("Unable to connect to phone camera!");
    console.log(err);
  }
}

function connectRTSP() {
  const url = document.getElementById("rtsp_url").value;
  const statusEl = document.getElementById("rtspStatus");
  statusEl.textContent = "Connecting…";

  const formData = new FormData();
  formData.append("rtsp", url);

  fetchWithCsrf("/set_rtsp", { method: "POST", body: formData })
    .then((r) => r.json())
    .then((data) => {
      statusEl.textContent = data.message || data.status || "Connected";
    })
    .catch((error) => {
      statusEl.textContent = "Connection failed.";
      console.log(error);
    });
}

// ============================================
// INSPECTION LOOP
// ============================================
function startInspection() {
  if (inspectionInterval != null) clearInterval(inspectionInterval);
  inspectionInterval = setInterval(sendFrame, 500);
}

function sendFrame() {
  const video = document.getElementById("video");
  if (!video.srcObject && !video.videoWidth) return;

  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  ctx.drawImage(video, 0, 0);

  canvas.toBlob(function (blob) {
    const formData = new FormData();
    formData.append("frame", blob, "live.jpg");

    fetchWithCsrf("/live_analyze", { method: "POST", body: formData })
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "Select ROI first" || data.status === "Upload a reference image first") {
          setStatus(data.status, "badge-warn");
          return;
        }
        if (data.status === "error") {
          setStatus(data.message || "Error", "badge-fail");
          return;
        }

        document.getElementById("similarity").innerHTML = data.similarity;
        document.getElementById("deltae").innerHTML = data.delta_e;
        document.getElementById("lvalue").innerHTML = data.l;
        document.getElementById("avalue").innerHTML = data.a;
        document.getElementById("bvalue").innerHTML = data.b;
        document.getElementById("confidence").innerHTML = data.confidence;

        setStatus(data.status, data.status === "PASS" ? "badge-pass" : "badge-fail");
      })
      .catch((error) => console.log("Live inspection error:", error));
  }, "image/jpeg");
}

function setStatus(text, cls) {
  const el = document.getElementById("status");
  el.textContent = text;
  el.className = "badge " + cls;
}

function stopInspection() {
  if (inspectionInterval != null) {
    clearInterval(inspectionInterval);
    inspectionInterval = null;
  }
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
    document.getElementById("video").srcObject = null;
    stream = null;
  }
}
