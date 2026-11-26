package study.minecraft;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.lang.invoke.MethodHandle;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.MethodType;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Locale;

/** Original CPU image methods on one zero-initialized 2x2 image; no decoder or GPU. */
public final class NativeImageProbe {
    private NativeImageProbe() { }

    private static String word(int value) {
        return String.format(Locale.ROOT, "%08x", value);
    }

    public static void main(String[] args) throws Throwable {
        Path output = Path.of(args[1]);
        JsonObject request = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject bindings = request.getAsJsonObject("bindings");
        Class<?> imageClass = Class.forName(bindings.get("imageClass").getAsString(), false,
            NativeImageProbe.class.getClassLoader());
        Class<?> formatClass = Class.forName(bindings.get("formatClass").getAsString(), false,
            NativeImageProbe.class.getClassLoader());
        MethodHandles.Lookup lookup = MethodHandles.publicLookup();
        // Exact descriptors avoid enumerating unrelated font, decoder, and GPU signatures.
        MethodHandle constructor = lookup.findConstructor(imageClass,
            MethodType.methodType(void.class, int.class, int.class, boolean.class));
        MethodHandle width = lookup.findVirtual(imageClass, bindings.get("width").getAsString(), MethodType.methodType(int.class));
        MethodHandle height = lookup.findVirtual(imageClass, bindings.get("height").getAsString(), MethodType.methodType(int.class));
        MethodHandle format = lookup.findVirtual(imageClass, bindings.get("format").getAsString(), MethodType.methodType(formatClass));
        MethodHandle get = lookup.findVirtual(imageClass, bindings.get("get").getAsString(),
            MethodType.methodType(int.class, int.class, int.class));
        MethodHandle set = lookup.findVirtual(imageClass, bindings.get("set").getAsString(),
            MethodType.methodType(void.class, int.class, int.class, int.class));
        MethodHandle close = lookup.findVirtual(imageClass, "close", MethodType.methodType(void.class));
        JsonObject result = new JsonObject();
        result.addProperty("schema", 1);
        result.addProperty("os", System.getProperty("os.name"));
        result.addProperty("osVersion", System.getProperty("os.version"));
        result.addProperty("architecture", System.getProperty("os.arch"));
        result.addProperty("javaVersion", System.getProperty("java.version"));
        result.addProperty("imageClass", imageClass.getName());
        result.addProperty("imageClassLocation", imageClass.getProtectionDomain().getCodeSource().getLocation().toString());
        result.addProperty("originalSigners", imageClass.getSigners() == null ? 0 : imageClass.getSigners().length);
        result.addProperty("allocatorProperty", System.getProperty("org.lwjgl.system.allocator"));
        result.addProperty("libraryPathProperty", System.getProperty("org.lwjgl.librarypath"));
        JsonArray events = new JsonArray();
        result.add("events", events);
        Object image = null;
        boolean closeReturned = false;
        try {
            for (var element : request.getAsJsonArray("steps")) {
                JsonObject spec = element.getAsJsonObject();
                JsonObject row = new JsonObject();
                row.addProperty("id", spec.get("id").getAsString());
                String operation = spec.get("operation").getAsString();
                try {
                    switch (operation) {
                        case "construct" -> {
                            if (image != null) throw new IllegalArgumentException("Only one image in this fixture.");
                            image = constructor.invoke(2, 2, true);
                        }
                        case "get" -> row.addProperty("word", word((int) get.invoke(image,
                            spec.get("x").getAsInt(), spec.get("y").getAsInt())));
                        case "set" -> set.invoke(image, spec.get("x").getAsInt(), spec.get("y").getAsInt(),
                            (int) Long.parseUnsignedLong(spec.get("word").getAsString(), 16));
                        case "close" -> { close.invoke(image); closeReturned = true; }
                        case "metadata" -> { /* Measured below independently of pixel access. */ }
                        default -> throw new IllegalArgumentException("Unknown fixture operation.");
                    }
                    row.addProperty("status", "returned");
                } catch (Throwable error) {
                    row.addProperty("status", "threw");
                    row.addProperty("errorClass", error.getClass().getName());
                    row.addProperty("message", error.getMessage());
                }
                if (image != null) {
                    JsonObject metadata = new JsonObject();
                    metadata.addProperty("width", (int) width.invoke(image));
                    metadata.addProperty("height", (int) height.invoke(image));
                    metadata.addProperty("format", ((Enum<?>) format.invoke(image)).name());
                    row.add("metadata", metadata);
                    // No pixel observation after a returned close. This is a fixture gate,
                    // not an observation of the native address or physical reclamation.
                    if (!closeReturned) {
                        JsonArray pixels = new JsonArray();
                        for (int y = 0; y < 2; y++) for (int x = 0; x < 2; x++)
                            pixels.add(word((int) get.invoke(image, x, y)));
                        row.add("pixels", pixels);
                    }
                }
                events.add(row);
                Files.writeString(output, new GsonBuilder().setPrettyPrinting().create().toJson(result) + "\n");
                if (operation.equals("construct") && image == null)
                    throw new IllegalStateException("Cannot continue without the tiny fixture image.");
            }
        } finally {
            if (image != null) {
                close.invoke(image);
                result.addProperty("finallyCloseReturned", true);
            }
            Files.writeString(output, new GsonBuilder().setPrettyPrinting().create().toJson(result) + "\n");
        }
    }
}
