import common.Lifecycle
open Lifecycle
def main : IO Unit := do
  for a in [false,true] do
    for b in [false,true] do
      for (key,n) in [("save_status",saveStatus a b),("retire",retire a b),("finalized",finalized a b)] do
        IO.println s!"{key} {a} {b} {n}"
      for c in [false,true] do
        for (key,n) in [("draft",draft a b c),("execute",execute a b c),("consume",consume a b c)] do
          IO.println s!"{key} {a} {b} {c} {n}"
        for d in [false,true] do
          for e in [false,true] do
            IO.println s!"collect {a} {b} {c} {d} {e} {collect a b c d e}"
