import common.Host
open Host

def main : IO Unit := do
  for a in [false,true] do
    for b in [false,true] do
      for (name, n) in [("file", file a b), ("work", work a b)] do
        IO.println s!"{name} {a} {b} {n}"
      for c in [false,true] do
        for (name,n) in [("streams", streams a b c), ("receipt", receipt a b c),
            ("apply_review", applyReview a b c), ("reuse", reuse a b c), ("effect", effect a b c)] do
          IO.println s!"{name} {a} {b} {c} {n}"
        for d in [false,true] do
          IO.println s!"product {a} {b} {c} {d} {product a b c d}"
