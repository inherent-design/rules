// Final Java 25 API. A lexically propagated review identity is only an input to authorization.
class ScopeProbe {
    static final ScopedValue<String> ACTOR = ScopedValue.newInstance();
    public static void main(String[] args) {
        var granted = new java.util.HashSet<String>();
        granted.add("reviewer");
        ScopedValue.where(ACTOR, "reviewer").run(() -> {
            for (boolean revoked : new boolean[]{false,true}) {
                if (revoked) granted.clear();
                var writes = new java.util.ArrayList<String>();
                if (granted.contains(ACTOR.get())) writes.add("pack");
                HostProbe.row("apply_review", "jdk-scope-" + (revoked ? "revoked" : "current"),
                    writes.size(), new String[]{"actor_allowed","target_matches","basis_current"},
                    !revoked, true, true);
            }
        });
        if (ACTOR.isBound()) throw new AssertionError("binding escaped lexical scope");
    }
}
