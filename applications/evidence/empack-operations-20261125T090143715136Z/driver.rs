// Owned fixture calls unchanged runtime/resource modules. No Engine, publisher,
// process adapter, user project, cache, or durable operations store is opened.
use serde_json::{json,Value};
use std::sync::{Arc,atomic::{AtomicBool,Ordering}};
use std::time::Duration;
use tokio::sync::oneshot;
use super::runtime::*;
use super::resources::*;

fn req()->ResourceRequest{ResourceRequest{jobs:1,memory_bytes:8,scratch_bytes:4,open_files:1}}
fn retained()->ResourceRequest{ResourceRequest{jobs:0,..req()}}
fn resources(g:&ResourceGovernor)->Value{let s=g.status();json!([s.reserved.jobs,s.reserved.memory_bytes,s.reserved.scratch_bytes,s.reserved.open_files])}
fn error(e:&RuntimeError)->String{format!("{e:?}")}
fn result(o:&OperationOutcome<u64>)->Value{match o{OperationOutcome::Completed(n)=>json!({"kind":"completed","value":n}),OperationOutcome::Failed(e)=>json!({"kind":"failed","error":error(e)})}}
fn state(h:&OperationHandle<u64>,g:&ResourceGovernor)->Value{let s=h.status();json!({"phase":format!("{:?}",s.phase),"terminal":s.terminal.as_ref().map(|o|result(o)),"reserved":resources(g),"progress":h.progress().map(|p|format!("{p:?}"))})}
fn emit(case:&str,point:&str,observed:Value){println!("{}",json!({"schema":1,"case":case,"point":point,"observed":observed}));}
async fn wait_phase(h:&OperationHandle<u64>,phase:OperationPhase){let mut receiver=h.subscribe();tokio::time::timeout(Duration::from_secs(3),receiver.wait_for(|s|s.phase==phase)).await.unwrap().unwrap();}

pub async fn run(path:std::path::PathBuf){
    // Retention and late subscriptions use a real retained Arc, not an event log.
    {
        let g=ResourceGovernor::new(req());let rt=OperationRuntime::new(g.clone(),1);
        let mut h=rt.start(|_|async{Ok(42)}).unwrap();let id=h.id();let o=h.wait().await;
        emit("retention","completed",state(&h,&g));drop(h);
        let mut observer=rt.observe(id).unwrap();let seen=observer.wait().await;
        let full=matches!(rt.start(|_|async{Ok(0)}),Err(RuntimeError::RegistryFull));
        emit("retention","late-observer",json!({"sameArc":Arc::ptr_eq(&o,&seen),"result":result(&seen),"registryFull":full}));
        let released=rt.release_completed(id);let after=observer.wait().await;
        emit("retention","release",json!({"released":released,"registryPresent":rt.observe(id).is_some(),"observerResult":result(&after),"sameArc":Arc::ptr_eq(&o,&after)}));
        rt.shutdown().await;emit("retention","closed",json!({"newStartClosed":matches!(rt.start(|_|async{Ok(0)}),Err(RuntimeError::Closed)),"reserved":resources(&g)}));
    }
    // An actual blocking file owner outlives both a work receiver and caller.
    {
        let g=ResourceGovernor::new(req());let rt=OperationRuntime::new(g.clone(),1);
        let (release,gate)=std::sync::mpsc::channel();let(started,ready)=oneshot::channel();let p=path.clone();
        let h=rt.start(move|scope|async move{
            drop(scope.spawn_blocking(req(),ResourceRequest::default(),move|cancel|{
                use std::io::{Read,Seek,Write};let mut f=std::fs::OpenOptions::new().create_new(true).write(true).read(true).open(p).unwrap();
                f.write_all(b"data").unwrap();f.sync_all().unwrap();let _=started.send(cancel);
                gate.recv_timeout(Duration::from_secs(8)).unwrap();f.rewind().unwrap();let mut b=Vec::new();f.read_to_end(&mut b).unwrap();assert_eq!(&b,b"data");
            })?);
            scope.cancellation().cancelled().await;Err(RuntimeError::Cancelled)
        }).unwrap();let id=h.id();let cancel=tokio::time::timeout(Duration::from_secs(3),ready).await.unwrap().unwrap();
        let mut observer=rt.observe(id).unwrap();drop(rt.observe(id));
        emit("drop-custody","observer-drop",json!({"cancelled":cancel.is_cancelled(),"state":state(&observer,&g),"fileBytes":std::fs::read(&path).unwrap()}));
        drop(h);wait_phase(&observer,OperationPhase::Retiring).await;
        emit("drop-custody","caller-drop-retiring",json!({"cancelled":cancel.is_cancelled(),"state":state(&observer,&g),"releaseAccepted":rt.release_completed(id),"registryFull":matches!(rt.start(|_|async{Ok(0)}),Err(RuntimeError::RegistryFull)),"capacityBusy":matches!(g.try_admit(req()),Err(AdmissionError::Busy{..}))}));
        release.send(()).unwrap();let o=observer.wait().await;
        emit("drop-custody","retired",json!({"result":result(&o),"state":state(&observer,&g),"fileBytes":std::fs::read(&path).unwrap()}));assert!(rt.release_completed(id));rt.shutdown().await;
    }
    // Supersession affects ordinary results; admitted receipt collection checks
    // owning operation/scope, not the normal attempt/cancellation acceptance gate.
    {
        let g=ResourceGovernor::new(ResourceRequest{memory_bytes:24,scratch_bytes:12,open_files:3,..req()});let view=g.clone();let rt=OperationRuntime::new(g.clone(),1);
        let mut h=rt.start(move|mut scope|async move{
            let a=scope.spawn(req(),retained(),|_|async{7u64})?.wait().await?;
            emit("acceptance","retained",json!({"reserved":resources(&view)}));scope.next_attempt()?;
            let stale=scope.accept(a).err().unwrap();emit("acceptance","superseded",json!({"error":error(&stale),"reserved":resources(&view)}));
            let normal=scope.spawn(req(),retained(),|_|async{8u64})?.wait().await?;
            let receipt=scope.spawn(req(),retained(),|_|async{42u64})?.wait().await?;
            scope.next_attempt()?;scope.cancellation().cancel();let stale=scope.accept(normal).err().unwrap();
            let retained=scope.accept_publication(receipt)?;
            emit("acceptance","cancelled-receipt",json!({"ordinaryError":error(&stale),"receiptValue":*retained,"reserved":resources(&view)}));Ok(*retained)
        }).unwrap();let o=h.wait().await;emit("acceptance","terminal",json!({"result":result(&o),"reserved":resources(&g)}));rt.shutdown().await;
    }
    // Progress uses a separate last-observation cell. Test status notification
    // coalescing and late callback delivery without making progress authority.
    {
        let g=ResourceGovernor::new(req());let rt=OperationRuntime::new(g.clone(),1);let(tx,rx)=oneshot::channel();let(go,gate)=oneshot::channel();
        let mut h=rt.start(move|scope|async move{scope.report_progress(WorkProgress::ReadingLocalContent);scope.report_progress(WorkProgress::SavingCachedContent);tx.send(scope.progress_reporter()).ok().unwrap();gate.await.unwrap();Ok(5)}).unwrap();
        let sink=rx.await.unwrap();emit("progress","coalesced",state(&h,&g));go.send(()).unwrap();let o=h.wait().await;
        let mut subscription=h.subscribe();subscription.borrow_and_update();sink(WorkProgress::PublishingChanges);
        emit("progress","late-terminal",json!({"state":state(&h,&g),"sameArc":Arc::ptr_eq(&o,&h.status().terminal.as_ref().unwrap()),"statusChanged":subscription.has_changed().unwrap()}));
        let released=rt.release_completed(h.id());sink(WorkProgress::RevalidatingInputs);
        emit("progress","after-release",json!({"released":released,"registryPresent":rt.observe(h.id()).is_some(),"state":state(&h,&g)}));rt.shutdown().await;
    }
    // Three actual supervisor combinations. Worker faults remain separately
    // observed before the driver's chosen terminal return.
    for mode in ["driver-ok","driver-cancelled","driver-panicked"]{
        let g=ResourceGovernor::new(req());let rt=OperationRuntime::new(g.clone(),1);let flag=Arc::new(AtomicBool::new(false));let observed=flag.clone();
        let mut h=rt.start(move|scope|async move{
            let work=scope.spawn(req(),ResourceRequest::default(),move|_|async move{observed.store(true,Ordering::SeqCst);panic!("rules-owned worker fault");})?;
            let fault=work.wait().await.err().unwrap();emit("failure-priority",mode,json!({"workerError":error(&fault)}));
            match mode{"driver-ok"=>Ok(9),"driver-cancelled"=>Err(RuntimeError::Cancelled),_=>panic!("rules-owned driver fault")}
        }).unwrap();let o=h.wait().await;emit("failure-priority",&format!("{mode}-terminal"),json!({"result":result(&o),"workerRan":flag.load(Ordering::SeqCst),"reserved":resources(&g)}));rt.shutdown().await;
    }
    // Retiring a preparation's child token does not cancel the parent token.
    {
        let g=ResourceGovernor::new(req());let rt=OperationRuntime::new(g.clone(),1);let mut h=rt.start(|scope|async move{
            let parent=scope.cancellation();drop(scope.spawn(req(),ResourceRequest::default(),|cancel|async move{cancel.cancelled().await})?);scope.retire().await?;
            emit("retire","child-only",json!({"parentCancelled":parent.is_cancelled()}));Ok(6)
        }).unwrap();let o=h.wait().await;emit("retire","terminal",json!({"result":result(&o),"reserved":resources(&g)}));rt.shutdown().await;
    }
    // Two concurrent shutdown callers both wait on an explicitly held worker.
    {
        let g=ResourceGovernor::new(req());let rt=Arc::new(OperationRuntime::new(g.clone(),1));let(ready,started)=oneshot::channel();let(go,gate)=oneshot::channel();
        let mut h=rt.start(move|scope|async move{
            drop(scope.spawn(req(),ResourceRequest::default(),move|cancel|async move{let _=ready.send(cancel.clone());gate.await.unwrap();})?);
            scope.cancellation().cancelled().await;Ok(10)
        }).unwrap();let cancel=started.await.unwrap();let a=rt.clone();let b=rt.clone();let sa=tokio::spawn(async move{a.shutdown().await});let sb=tokio::spawn(async move{b.shutdown().await});
        tokio::time::timeout(Duration::from_secs(3),cancel.cancelled()).await.unwrap();wait_phase(&h,OperationPhase::Retiring).await;
        emit("shutdown","pending",json!({"firstFinished":sa.is_finished(),"secondFinished":sb.is_finished(),"newStartClosed":matches!(rt.start(|_|async{Ok(0)}),Err(RuntimeError::Closed)),"state":state(&h,&g)}));
        go.send(()).unwrap();sa.await.unwrap();sb.await.unwrap();let o=h.wait().await;emit("shutdown","retired",json!({"result":result(&o),"reserved":resources(&g)}));
    }
}
