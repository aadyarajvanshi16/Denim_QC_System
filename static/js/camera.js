const video = document.getElementById("video");
const captureBtn = document.getElementById("captureBtn");
const canvas = document.getElementById("canvas");

function startCamera() {
  navigator.mediaDevices
    .getUserMedia({ video: true })
    .then(function (stream) {
      video.srcObject = stream;
      video.style.display = "block";
      captureBtn.style.display = "inline-block";
    })
    .catch(function (error) {
      alert("Unable to access camera.");
      console.log(error);
    });
}

function captureImage() {
  const ctx = canvas.getContext("2d");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  ctx.drawImage(video, 0, 0);

  const preview = document.getElementById("preview");
  preview.src = canvas.toDataURL("image/jpeg");
  document.getElementById("previewContainer").style.display = "block";
  document.getElementById("cameraLoading").classList.remove("hidden");

  if (video.srcObject) {
    video.srcObject.getTracks().forEach((t) => t.stop());
  }

  canvas.toBlob(function (blob) {
    const formData = new FormData();
    formData.append("image", blob, "camera.jpg");

    fetchWithCsrf("/recipe_extraction/upload", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.text())
      .then((html) => {
        document.open();
        document.write(html);
        document.close();
      })
      .catch((error) => {
        console.log(error);
        document.getElementById("cameraLoading").classList.add("hidden");
        alert("Upload failed — please try again.");
      });
  }, "image/jpeg");
}
