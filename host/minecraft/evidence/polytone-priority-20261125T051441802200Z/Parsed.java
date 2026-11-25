// Data-only adapter. Original Polytone Parsed codec/static initialization excluded.
package net.mehvahdjukaar.polytone.common;
public final class Parsed<T> {
    public final int priority;
    public final boolean enabled;
    public final T marker;
    public Parsed(boolean enabled,int priority,T marker) {
        this.enabled=enabled;this.priority=priority;this.marker=marker;
    }
    public boolean isEnabled() { return enabled; }
}
