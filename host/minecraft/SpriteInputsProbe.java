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
import java.util.stream.IntStream;

/** Constructed original sprites over tiny owned images; no decoder/ticker/GPU. */
public final class SpriteInputsProbe {
    private SpriteInputsProbe() { }

    private static Class<?> type(JsonObject b, String key) throws ClassNotFoundException {
        return Class.forName(b.get(key).getAsString(), false, SpriteInputsProbe.class.getClassLoader());
    }

    private static JsonArray frameIds(MethodHandle frames, Object sprite) throws Throwable {
        int[] ids;
        try (IntStream stream = (IntStream) frames.invoke(sprite)) { ids = stream.toArray(); }
        if (ids.length < 1 || ids.length > 2) throw new IllegalStateException("Unexpected frame count.");
        JsonArray result = new JsonArray();
        for (int id : ids) result.add(id);
        return result;
    }

    public static void main(String[] args) throws Throwable {
        JsonObject request = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        Path output = Path.of(args[1]);
        JsonObject b = request.getAsJsonObject("bindings");
        Class<?> imageClass = type(b, "imageClass"), spriteClass = type(b, "spriteClass"),
            sizeClass = type(b, "sizeClass"), metadataClass = type(b, "metadataClass"), nameClass = type(b, "nameClass");
        MethodHandles.Lookup lookup = MethodHandles.publicLookup();
        MethodHandle makeImage = lookup.findConstructor(imageClass, MethodType.methodType(void.class, int.class, int.class, boolean.class));
        MethodHandle set = lookup.findVirtual(imageClass, b.get("set").getAsString(), MethodType.methodType(void.class, int.class, int.class, int.class));
        MethodHandle get = lookup.findVirtual(imageClass, b.get("get").getAsString(), MethodType.methodType(int.class, int.class, int.class));
        MethodHandle closeImage = lookup.findVirtual(imageClass, "close", MethodType.methodType(void.class));
        MethodHandle makeSize = lookup.findConstructor(sizeClass, MethodType.methodType(void.class, int.class, int.class));
        MethodHandle empty = lookup.findStaticGetter(metadataClass, b.get("emptyMetadata").getAsString(), metadataClass);
        MethodHandle makeSprite = lookup.findConstructor(spriteClass, MethodType.methodType(void.class, nameClass, sizeClass, imageClass, metadataClass));
        MethodHandle width = lookup.findVirtual(spriteClass, b.get("width").getAsString(), MethodType.methodType(int.class));
        MethodHandle height = lookup.findVirtual(spriteClass, b.get("height").getAsString(), MethodType.methodType(int.class));
        MethodHandle frames = lookup.findVirtual(spriteClass, b.get("frames").getAsString(), MethodType.methodType(IntStream.class));
        MethodHandle transparent = lookup.findVirtual(spriteClass, b.get("transparent").getAsString(), MethodType.methodType(boolean.class, int.class, int.class, int.class));
        MethodHandle closeSprite = lookup.findVirtual(spriteClass, "close", MethodType.methodType(void.class));
        Object metadata = empty.invoke();
        JsonObject result = new JsonObject();
        result.addProperty("schema", 1);
        result.addProperty("javaVersion", System.getProperty("java.version"));
        result.addProperty("os", System.getProperty("os.name"));
        result.addProperty("osVersion", System.getProperty("os.version"));
        result.addProperty("architecture", System.getProperty("os.arch"));
        result.addProperty("spriteClass", spriteClass.getName());
        result.addProperty("originalSigners", spriteClass.getSigners() == null ? 0 : spriteClass.getSigners().length);
        result.addProperty("nameContext", "null adapter;no identifier construction");
        result.addProperty("metadataContext", "original ResourceMetadata.EMPTY;no metadata parsing");
        JsonArray cases = new JsonArray(); result.add("cases", cases);
        for (var element : request.getAsJsonArray("cases")) {
            JsonObject spec = element.getAsJsonObject();
            int w = spec.get("width").getAsInt(), h = spec.get("height").getAsInt();
            JsonArray masks = spec.getAsJsonArray("masks");
            int count = masks.size();
            if (w < 1 || w > 3 || h != 2 || count < 1 || count > 2 || w * h * count > 8)
                throw new IllegalArgumentException("Outside tiny sprite profile.");
            JsonObject row = new JsonObject(); row.addProperty("id", spec.get("id").getAsString());
            Object image = null, sprite = null;
            boolean explicitlyClosed = false;
            Throwable failed = null;
            try {
                image = makeImage.invoke(w, h * count, true);
                for (int frame = 0; frame < count; frame++) {
                    int mask = masks.get(frame).getAsInt();
                    if (mask < 0 || mask >= (1 << (w * h))) throw new IllegalArgumentException("Outside mask profile.");
                    for (int y = 0; y < h; y++) for (int x = 0; x < w; x++)
                        set.invoke(image, x, y + frame * h, (mask & (1 << (y * w + x))) != 0 ? -1 : 0);
                }
                sprite = makeSprite.invoke((Object) null, makeSize.invoke(w, h), image, metadata);
                row.addProperty("width", (int) width.invoke(sprite)); row.addProperty("height", (int) height.invoke(sprite));
                JsonArray ids = frameIds(frames, sprite); row.add("uniqueFrames", ids);
                JsonArray matrices = new JsonArray();
                for (var id : ids) {
                    JsonObject matrix = new JsonObject(); matrix.addProperty("frame", id.getAsInt());
                    JsonArray cells = new JsonArray();
                    for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) cells.add((boolean) transparent.invoke(sprite, id.getAsInt(), x, y));
                    matrix.add("transparent", cells); matrices.add(matrix);
                }
                row.add("matrices", matrices);
                if (spec.get("aliasLifecycle").getAsBoolean()) {
                    row.addProperty("beforeMutation", (boolean) transparent.invoke(sprite, 1, 0, 0));
                    set.invoke(image, 0, 0, -1);
                    row.addProperty("afterMutation", (boolean) transparent.invoke(sprite, 1, 0, 0));
                    closeSprite.invoke(sprite); explicitlyClosed = true;
                    try { get.invoke(image, 0, 0); row.addProperty("inputImageAfterSpriteClose", "returned"); }
                    catch (IllegalStateException error) { row.addProperty("inputImageAfterSpriteClose", error.getClass().getName()); }
                    try { transparent.invoke(sprite, 1, 0, 0); row.addProperty("spriteAfterClose", "returned"); }
                    catch (IllegalStateException error) { row.addProperty("spriteAfterClose", error.getClass().getName()); }
                    row.addProperty("widthAfterClose", (int) width.invoke(sprite)); row.addProperty("heightAfterClose", (int) height.invoke(sprite));
                    row.add("framesAfterClose", frameIds(frames, sprite));
                }
                row.addProperty("status", "returned");
            } catch (Throwable error) {
                failed = error;
                row.addProperty("status", "threw"); row.addProperty("errorClass", error.getClass().getName()); row.addProperty("message", error.getMessage());
            } finally {
                try {
                    if (sprite != null && !explicitlyClosed) { closeSprite.invoke(sprite); row.addProperty("spriteCleanupReturned", true); }
                    else if (explicitlyClosed) row.addProperty("spriteExplicitCloseReturned", true);
                } finally {
                    if (image != null) { closeImage.invoke(image); row.addProperty("imageFinalCloseReturned", true); }
                    cases.add(row); Files.writeString(output, new GsonBuilder().setPrettyPrinting().create().toJson(result) + "\n");
                }
            }
            if (failed != null) throw failed;
        }
    }
}
