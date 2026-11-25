package study.host;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.IdentityHashMap;
import java.util.Set;

/** Authored classes only. No application/provider class is loaded by this fixture. */
public final class ClassInitProbe {
    private static final int[] effects = new int[6];
    private static final IdentityHashMap<Class<?>, Integer> identities = new IdentityHashMap<>();
    private static final String PREFIX = "study.host.ClassInitProbe$";
    private static CountingLoader loaderA;
    private static CountingLoader loaderB;
    private static int sequence;

    public static void mark(int kind) { effects[kind]++; }
    public static boolean fail() { return true; }

    public static final class Good { static { mark(0); } }
    public static final class Bad { static { mark(1); if (fail()) throw new IllegalStateException("owned initializer refusal"); } }
    public static final class HardBad { static { mark(2); if (fail()) throw new AssertionError("owned initializer error"); } }
    public static final class ArrayElement { static { mark(3); } }

    private static final class CountingLoader extends ClassLoader {
        private final Path classes;
        private final int marker;
        private final Set<String> owned = Set.of(PREFIX + "Good", PREFIX + "Bad", PREFIX + "HardBad", PREFIX + "ArrayElement", PREFIX + "Missing");
        CountingLoader(Path classes, int marker) { super(ClassInitProbe.class.getClassLoader()); this.classes = classes; this.marker = marker; }
        @Override protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
            if (!owned.contains(name)) return super.loadClass(name, resolve);
            synchronized (getClassLoadingLock(name)) {
                Class<?> result = findLoadedClass(name);
                if (result == null) result = findClass(name);
                if (resolve) resolveClass(result);
                return result;
            }
        }
        @Override protected Class<?> findClass(String name) throws ClassNotFoundException {
            mark(marker);
            if (!owned.contains(name) || name.equals(PREFIX + "Missing")) throw new ClassNotFoundException(name);
            try {
                byte[] bytes = Files.readAllBytes(classes.resolve(name.replace('.', '/') + ".class"));
                return defineClass(name, bytes, 0, bytes.length);
            } catch (java.io.IOException error) { throw new ClassNotFoundException(name, error); }
        }
    }

    @FunctionalInterface private interface Lookup { Class<?> get() throws Throwable; }
    private static String quote(String text) {
        return "\"" + text.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r") + "\"";
    }
    private static int loaderId(Class<?> type) {
        ClassLoader loader = type.getClassLoader();
        return loader == ClassInitProbe.class.getClassLoader() ? 0 : loader == loaderA ? 1 : loader == loaderB ? 2 : -1;
    }
    private static void observe(String id, String operation, String target, int requestedLoader, boolean initialize, boolean array, Lookup lookup) {
        int[] before = effects.clone();
        Class<?> type = null;
        Throwable failure = null;
        try { type = lookup.get(); } catch (Throwable error) { failure = error; }
        int[] after = effects.clone();
        int identity = type == null ? 0 : identities.computeIfAbsent(type, ignored -> identities.size() + 1);
        String error = failure == null ? "none" : failure.getClass().getName();
        String cause = failure == null || failure.getCause() == null ? "none" : failure.getCause().getClass().getName();
        String json = "{\"schema\":1,\"index\":" + sequence++ + ",\"case\":" + quote(id)
            + ",\"operation\":" + quote(operation) + ",\"target\":" + quote(target)
            + ",\"requestedLoader\":" + requestedLoader + ",\"initialize\":" + initialize + ",\"array\":" + array
            + ",\"before\":" + Arrays.toString(before) + ",\"after\":" + Arrays.toString(after)
            + ",\"returnedClass\":" + (type != null) + ",\"className\":" + quote(type == null ? "" : type.getName())
            + ",\"actualLoader\":" + (type == null ? -1 : loaderId(type)) + ",\"classIdentity\":" + identity
            + ",\"error\":" + quote(error) + ",\"cause\":" + quote(cause)
            + ",\"caughtByClassNotFound\":" + (failure instanceof ClassNotFoundException)
            + ",\"caughtByException\":" + (failure instanceof Exception) + "}";
        System.out.println(json);
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Supply owned class directory");
        Path classes = Path.of(args[0]).toRealPath();
        loaderA = new CountingLoader(classes, 4);
        loaderB = new CountingLoader(classes, 5);
        ClassLoader system = ClassInitProbe.class.getClassLoader();
        observe("good-literal", "literal", "Good", 0, false, false, () -> Good.class);
        observe("good-no-init", "explicit", "Good", 0, false, false, () -> Class.forName(PREFIX + "Good", false, system));
        observe("good-default", "default", "Good", 0, true, false, () -> Class.forName(PREFIX + "Good"));
        observe("good-repeat", "explicit", "Good", 0, true, false, () -> Class.forName(PREFIX + "Good", true, system));
        observe("bad-no-init", "explicit", "Bad", 0, false, false, () -> Class.forName(PREFIX + "Bad", false, system));
        observe("bad-default", "default", "Bad", 0, true, false, () -> Class.forName(PREFIX + "Bad"));
        observe("bad-retry", "explicit", "Bad", 0, true, false, () -> Class.forName(PREFIX + "Bad", true, system));
        observe("bad-metadata-after-failure", "explicit", "Bad", 0, false, false, () -> Class.forName(PREFIX + "Bad", false, system));
        observe("loader-a-no-init", "explicit", "Good", 1, false, false, () -> Class.forName(PREFIX + "Good", false, loaderA));
        observe("loader-a-init", "explicit", "Good", 1, true, false, () -> Class.forName(PREFIX + "Good", true, loaderA));
        observe("loader-b-init", "explicit", "Good", 2, true, false, () -> Class.forName(PREFIX + "Good", true, loaderB));
        observe("loader-a-missing", "explicit", "Missing", 1, false, false, () -> Class.forName(PREFIX + "Missing", false, loaderA));
        observe("array-literal", "literal", "ArrayElement", 0, false, true, () -> ArrayElement[].class);
        observe("array-default", "default", "ArrayElement", 0, true, true, () -> Class.forName("[L" + PREFIX + "ArrayElement;"));
        observe("array-element-init", "explicit", "ArrayElement", 0, true, false, () -> Class.forName(PREFIX + "ArrayElement", true, system));
        observe("error-default", "default", "HardBad", 0, true, false, () -> Class.forName(PREFIX + "HardBad"));
        observe("error-retry", "explicit", "HardBad", 0, true, false, () -> Class.forName(PREFIX + "HardBad", true, system));
        observe("error-metadata-after-failure", "explicit", "HardBad", 0, false, false, () -> Class.forName(PREFIX + "HardBad", false, system));
        observe("system-missing", "default", "Missing", 0, true, false, () -> Class.forName(PREFIX + "Missing"));
        for (String name : new String[]{"java/lang/Class.class", "java/lang/ClassLoader.class"}) {
            try (var input = ClassLoader.getSystemResourceAsStream(name)) {
                if (input == null) throw new IllegalStateException(name);
                String digest = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(input.readAllBytes()));
                System.out.println("{\"schema\":1,\"runtimeClass\":" + quote(name) + ",\"sha256\":" + quote(digest) + "}");
            }
        }
    }
}
