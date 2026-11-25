// Avoids the real root's initialization/configuration/renderer side effects.
package net.mehvahdjukaar.polytone;
import org.apache.logging.log4j.Logger;
public final class Polytone {
    public static int warnings=0;
    public static final Logger LOGGER=(message,first,second)->warnings++;
}
