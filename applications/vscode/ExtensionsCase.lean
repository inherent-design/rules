import Lean
import applications.vscode.Extensions
open Lean ApplicationStudy.VscodeExtensions

private structure HostRow where
  label : String
  surface : String
  localKinds : List String
  remoteKinds : List String
  «local» : Bool
  remote : Bool
  remoteHost : Bool
  worker : Bool
  development : String
  deriving FromJson

private structure ManagementRow where
  label : String
  operation : String
  registered : Nat
  requested : Nat
  compatible : Bool
  deriving FromJson

private structure Input where
  schema : Nat
  profile : String
  hosts : List HostRow
  management : List ManagementRow
  deriving FromJson

private def kinds (xs : List String) : Except String (List Kind) := do
  if xs.isEmpty || xs.length > 3 || xs.eraseDups.length != xs.length then
    throw "Supply one to three distinct effective kinds."
  xs.mapM fun k => match k with
    | "ui" => pure .ui | "workspace" => pure .workspace | "web" => pure .web
    | _ => throw "Unknown extension kind."

private def host (r : HostRow) : Except String Json := do
  let surface ← match r.surface with
    | "desktop" => pure Surface.desktop | "browser" => pure .browser
    | _ => throw "Unknown application surface."
  if !r.«local» && !r.remote then throw "The source caller requires a scanned extension."
  if surface == .desktop && r.remote && !r.remoteHost then throw "Remote scan lacks its host premise."
  if surface == .browser && !r.worker then throw "Browser picker has no worker availability parameter."
  let (ld,rd) ← match r.development with
    | "none" => pure (false,false) | "local" => pure (true,false)
    | "remote" => pure (false,true) | "both" => pure (true,true)
    | _ => throw "Unknown development placement."
  if (ld && !r.«local») || (rd && !r.remote) then throw "Development placement lacks its scanned extension."
  let request : HostRequest := ⟨surface,← kinds r.localKinds,← kinds r.remoteKinds,
    r.«local»,r.remote,r.remoteHost,r.worker,ld,rd⟩
  return Json.mkObj [("label",toJson r.label),("host",toJson (select request)),
    ("preference",toJson (preference request)),("kinds",toJson (if r.«local» then r.localKinds else r.remoteKinds))]

private def management (r : ManagementRow) : Except String Json := do
  if r.registered > 2 then throw "Unknown registered fixture version."
  let operation ← match r.operation with
    | "query" => pure Operation.query | "install" => pure .install | "uninstall" => pure .uninstall
    | _ => throw "Unknown management operation."
  if operation == .install then
    if r.requested < 1 || r.requested > 3 || r.compatible != (r.requested != 3) then
      throw "VSIX version and engine premise disagree."
  else if r.requested != 0 || !r.compatible then throw "Unexpected operand for this fixture operation."
  let result := manage ⟨operation,r.registered,r.requested,r.compatible⟩
  return Json.mkObj [("label",toJson r.label),("action",toJson result.action),
    ("exit",toJson result.exit),("registered",toJson result.registered)]

def main (args : List String) : IO UInt32 := do
  let [path] := args | IO.eprintln "Supply one extension-study JSON input."; return 2
  match Json.parse (← IO.FS.readFile path) >>= fromJson? (α := Input) with
  | .error error => IO.eprintln error; return 2
  | .ok input =>
    if input.schema != 1 || input.profile != "vscode-1.148-local-vsix-and-source-hosts" then
      IO.eprintln "Unsupported extension study profile."; return 2
    if input.hosts.isEmpty || input.hosts.length > 40 || input.management.isEmpty || input.management.length > 20 then
      IO.eprintln "Input exceeds the bounded study or omits a band."; return 2
    match (do pure (← input.hosts.mapM host,← input.management.mapM management) : Except String (List Json × List Json)) with
    | .error error => IO.eprintln error; return 2
    | .ok (hosts,management) =>
      IO.println (Json.mkObj [("hosts",toJson hosts),("management",toJson management)]).compress
      return 0
