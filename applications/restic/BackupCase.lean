import Lean
import applications.restic.Backup
open Lean ApplicationStudy.ResticBackup

private structure Row where
  parent : Bool
  force : Bool
  ignoreCtime : Bool
  ignoreInode : Bool
  sizeEqual : Bool
  mtimeEqual : Bool
  ctimeEqual : Bool
  inodeEqual : Bool
  blobsIndexed : Bool
  readable : Bool
  priorContent : Nat
  liveContent : Nat
  rootAvailable : Bool
  fatal : Bool
  dryRun : Bool
  skipUnchanged : Bool
  sameTree : Bool
  itemErrors : Bool
  deriving FromJson
private structure Input where
  schema : Nat
  cases : List Row
  deriving FromJson
private def bit (b : Bool) : String := if b then "1" else "0"
private def evaluate (r : Row) : Except String String := do
  if r.priorContent == 0 || r.liveContent == 0 || r.priorContent > 2 || r.liveContent > 2 then
    throw "Unsupported fixture content identity."
  let c : Capture := ⟨r.parent,r.force,r.ignoreCtime,r.ignoreInode,
    ⟨r.sizeEqual,r.mtimeEqual,r.ctimeEqual,r.inodeEqual⟩,r.blobsIndexed,r.readable,r.priorContent,r.liveContent⟩
  let p : Publication := ⟨r.rootAvailable,r.fatal,r.dryRun,r.skipUnchanged,r.sameTree,r.itemErrors⟩
  let e := match effect p with
    | .refused => "refused" | .planned => "planned" | .unchanged => "unchanged" | .published => "published"
  let content := if !r.rootAvailable then 0 else (captured c).getD 0
  pure (String.intercalate "/" [bit (reuse c), toString content, e, toString (exitCode p), bit (hasReportedId p)])
def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one backup-model input."; return 2
  let text ← IO.FS.readFile path
  match Json.parse text >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 then IO.eprintln "Unsupported backup research schema."; return 2
    match input.cases.mapM evaluate with
    | .error error => IO.eprintln error; return 2
    | .ok values => IO.println (toJson values).compress; return 0
