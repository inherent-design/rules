self.onmessage=async ({data})=>{
  try {
    const root=await navigator.storage.getDirectory();
    const file=await root.getFileHandle(data.name,{create:true});
    const access=await file.createSyncAccessHandle();
    const bytes=new TextEncoder().encode(data.text);
    access.write(bytes,{at:0});
    access.truncate(bytes.length);
    access.flush();
    access.close();
    self.postMessage({retained:data.name});
  } catch(error) {
    self.postMessage({error:error.name,message:error.message});
  }
};
