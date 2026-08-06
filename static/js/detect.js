function startScan(){
  const file=document.getElementById("fileInput").files[0];
  if(!file){ alert("Select an image"); return; }

  document.getElementById("preview").src=URL.createObjectURL(file);
  document.getElementById("preview").hidden=false;

  document.getElementById("fname").innerText=file.name;
  document.getElementById("fsize").innerText=(file.size/1024).toFixed(2)+" KB";
  document.getElementById("ftime").innerText=new Date().toLocaleString();

  const confidence=Math.floor(Math.random()*35)+60;
  document.getElementById("bar").style.width=confidence+"%";
  document.getElementById("conf").innerText=confidence;

  const risk=document.getElementById("risk");
  risk.innerText=confidence>70?"HIGH RISK":"LOW RISK";
  risk.style.background=confidence>70?"#dc2626":"#16a34a";

  document.getElementById("result").hidden=false;
}