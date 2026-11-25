package study.minecraft;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.PathMatcher;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.List;

/** Original detector/validator calls with authored factories; no pack is opened. */
public final class PackDetectorProbe {
    private static JsonArray factoryEvents;
    private static String factoryMode;

    private PackDetectorProbe() { }

    public static Object factory(String kind, Path path) throws IOException {
        JsonObject event = new JsonObject();
        event.addProperty("kind", kind);
        event.addProperty("path", path.toString());
        event.addProperty("absoluteNormalizedPath", path.toAbsolutePath().normalize().toString());
        factoryEvents.add(event);
        if (factoryMode.equals("throw")) throw new IOException("authored-factory-failure:" + kind);
        return factoryMode.equals("null") ? null : kind;
    }

    private static JsonObject attributes(Path path) {
        JsonObject result = new JsonObject();
        try {
            BasicFileAttributes attrs = Files.readAttributes(path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
            result.addProperty("kind", attrs.isSymbolicLink() ? "symlink" : attrs.isDirectory() ? "directory" : attrs.isRegularFile() ? "regular" : "other");
            result.addProperty("fileKey", String.valueOf(attrs.fileKey()));
            result.addProperty("size", attrs.size());
        } catch (IOException error) {
            result.addProperty("errorClass", error.getClass().getName());
        }
        return result;
    }

    public static void main(String[] args) throws Exception {
        JsonObject request = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject bindings = request.getAsJsonObject("bindings");
        Class<?> validatorClass = Class.forName(bindings.get("validatorClass").getAsString());
        Class<?> detectorClass = Class.forName(bindings.get("detectorClass").getAsString());
        Method detect = detectorClass.getDeclaredMethod(bindings.get("detectMethod").getAsString(), Path.class, List.class);
        URLClassLoader adapterLoader = new URLClassLoader(new URL[]{Path.of(request.get("adapterDirectory").getAsString()).toUri().toURL()}, PackDetectorProbe.class.getClassLoader());
        Class<?> adapterClass = Class.forName("AuthoredDetector", true, adapterLoader);
        JsonArray rows = new JsonArray();
        for (JsonElement element : request.getAsJsonArray("cases")) {
            JsonObject spec = element.getAsJsonObject();
            Path path = Path.of(spec.get("path").getAsString());
            boolean allowed = spec.get("allowLinks").getAsBoolean();
            JsonArray matcherEvents = new JsonArray();
            PathMatcher matcher = target -> {
                JsonObject event = new JsonObject();
                event.addProperty("target", target.toString());
                event.addProperty("allowed", allowed);
                matcherEvents.add(event);
                return allowed;
            };
            Object validator = validatorClass.getConstructor(PathMatcher.class).newInstance(matcher);
            Object detector = adapterClass.getConstructor(validatorClass).newInstance(validator);
            List<Object> issues = new ArrayList<>();
            factoryEvents = new JsonArray();
            factoryMode = spec.get("factoryMode").getAsString();
            JsonObject row = new JsonObject();
            row.addProperty("id", spec.get("id").getAsString());
            row.add("inputAttributes", attributes(path));
            try {
                Object result = detect.invoke(detector, path, issues);
                row.addProperty("status", "returned");
                row.addProperty("result", result == null ? "null" : result.toString());
            } catch (InvocationTargetException error) {
                Throwable cause = error.getCause();
                row.addProperty("status", "threw");
                row.addProperty("errorClass", cause.getClass().getName());
                row.addProperty("message", cause.getMessage());
            }
            row.addProperty("issues", issues.size());
            row.add("matcherEvents", matcherEvents);
            row.add("factoryEvents", factoryEvents);
            row.add("inputAttributesAfter", attributes(path));
            rows.add(row);
        }
        JsonObject output = new JsonObject();
        output.addProperty("schema", 1);
        output.addProperty("cwd", Path.of("").toAbsolutePath().toString());
        output.addProperty("os", System.getProperty("os.name"));
        output.addProperty("osVersion", System.getProperty("os.version"));
        output.addProperty("architecture", System.getProperty("os.arch"));
        output.addProperty("javaVersion", System.getProperty("java.version"));
        output.addProperty("originalDetectorSigners", detectorClass.getSigners() == null ? 0 : detectorClass.getSigners().length);
        output.addProperty("originalValidatorSigners", validatorClass.getSigners() == null ? 0 : validatorClass.getSigners().length);
        output.addProperty("adapterSigners", adapterClass.getSigners() == null ? 0 : adapterClass.getSigners().length);
        output.addProperty("adapterHasSeparateLoader", adapterClass.getClassLoader() != detectorClass.getClassLoader());
        output.addProperty("filesystemType", Files.getFileStore(Path.of(request.get("fixtureRoot").getAsString())).type());
        output.add("cases", rows);
        Files.writeString(Path.of(args[1]), new GsonBuilder().setPrettyPrinting().create().toJson(output) + "\n");
        adapterLoader.close();
    }
}
