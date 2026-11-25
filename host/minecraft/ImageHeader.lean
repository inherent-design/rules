import host.java.Word64

namespace Host.Minecraft.ImageHeader

structure Input where
  generation : Nat -- 0: first three clients; 1:1.21.11; 2:26.3
  limit : Nat
  magic : Bool
  length13 : Bool
  ihdr : Bool
  widthBits : Nat
  heightBits : Nat
  depth : Nat
  color : Nat
  position : Nat := 0
  littleEndian : Bool := true
  readOnly : Bool := false
  deriving BEq, DecidableEq, Repr

/-- Error category: 0 normal return, 1 IOException, 2 absolute-read IndexOutOfBounds. -/
def error (i : Input) : Nat :=
  if (i.generation == 1 && i.limit < 16) || (i.generation == 2 && i.limit < 33) then 1
  else if i.limit < 8 then 2
  else if !i.magic then 1
  else if i.limit < 12 then 2
  else if !i.length13 then 1
  else if i.limit < 16 then 2
  else if !i.ihdr then 1
  else if i.generation != 2 then 0
  else if ![1, 2, 4, 8, 16].contains i.depth then 1
  else if ![0, 2, 3, 4, 6].contains i.color then 1
  else if i.depth == 16 && !Host.Java.Word64.intRoundtrip (Host.Java.Word64.estimate i.widthBits i.heightBits) then 1
  else 0

structure Outcome where
  error : Nat
  littleEndian : Bool
  position : Nat
  limit : Nat
  remaining : Nat
  readOnly : Bool
  bytesUnchanged : Bool
  deriving BEq, DecidableEq, Repr

def run (i : Input) : Outcome :=
  let failure := error i
  ⟨failure, failure == 0 && i.littleEndian, i.position, i.limit, i.limit - i.position, i.readOnly, true⟩

def baseline : Input := ⟨2, 33, true, true, true, 2, 3, 8, 6, 0, true, false⟩

theorem successful_header_restores_order (i : Input) (success : error i = 0) :
    (run i).littleEndian = i.littleEndian := by simp [run, success]
theorem failure_leaves_big_endian (i : Input) (failed : error i ≠ 0) :
    (run i).littleEndian = false := by simp [run, failed]
theorem absolute_reads_preserve_position (i : Input) : (run i).position = i.position := rfl
theorem absolute_reads_preserve_limit (i : Input) : (run i).limit = i.limit := rfl
theorem no_byte_writes (i : Input) : (run i).bytesUnchanged = true := rfl
theorem read_only_is_not_order_immutable :
    (run { baseline with magic := false, readOnly := true }).littleEndian = false := by decide
theorem old_short_prefix_unchecked : error { baseline with generation := 0, limit := 15 } = 2 := by decide
theorem intermediate_short_prefix_checked : error { baseline with generation := 1, limit := 15 } = 1 := by decide
theorem intermediate_accepts_sixteen : error { baseline with generation := 1, limit := 16 } = 0 := by decide
theorem latest_requires_thirty_three : error { baseline with limit := 32 } = 1 := by decide
theorem remaining_is_not_header_length : error { baseline with position := 32 } = 0 := by decide
theorem independently_allowed_fields_do_not_validate_pairing : error { baseline with depth := 1 } = 0 := by decide
theorem depth8_does_not_check_positive_dimension : error { baseline with widthBits := 0 } = 0 := by decide
theorem depth16_can_reject_int_overflow :
    error { baseline with depth := 16, widthBits := 16384, heightBits := 16384 } = 1 := by decide
theorem depth16_accepts_negative_wrap :
    error { baseline with depth := 16, widthBits := 1073741825, heightBits := 2147483646 } = 0 := by decide
theorem depth16_accepts_positive_wrap :
    error { baseline with depth := 16, widthBits := 1073763824, heightBits := 2147439649 } = 0 := by decide

end Host.Minecraft.ImageHeader
