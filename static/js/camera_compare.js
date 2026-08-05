let currentType = "";

const video = document.getElementById("video");
const captureBtn = document.getElementById("captureBtn");
const canvas = document.getElementById("canvas");

function startCamera(type){

    currentType = type;

    navigator.mediaDevices.getUserMedia({
        video:true
    })

    .then(function(stream){

        video.srcObject = stream;

        video.style.display="block";

        captureBtn.style.display="inline-block";

    })

    .catch(function(error){

        alert("Unable to access camera.");

        console.log(error);

    });

}

captureBtn.onclick=function(){

    const ctx=canvas.getContext("2d");

    canvas.width=video.videoWidth;

    canvas.height=video.videoHeight;

    ctx.drawImage(video,0,0);

    canvas.toBlob(function(blob){

        const file=new File(
            [blob],
            currentType+".jpg",
            {
                type:"image/jpeg"
            }
        );

        const dt=new DataTransfer();

        dt.items.add(file);

        if(currentType==="reference"){

            document.getElementById("reference_input").files=dt.files;

        }

        if(currentType==="test"){

            document.getElementById("test_input").files=dt.files;

        }

        if(video.srcObject){

            video.srcObject.getTracks().forEach(track=>track.stop());

        }

        video.srcObject=null;

        video.style.display="none";

        captureBtn.style.display="none";

        alert(currentType+" image captured.");

    },"image/jpeg");

};