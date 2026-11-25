package study.minecraft;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;

/** Tiny heap-buffer calls only: no PNG decoding, native allocation, or game bootstrap. */
public final class ImageHeaderProbe {
    private ImageHeaderProbe() { }

    private static JsonObject state(ByteBuffer buffer, byte[] bytes) throws Exception {
        JsonObject result = new JsonObject();
        result.addProperty("order", buffer.order().toString());
        result.addProperty("position", buffer.position());
        result.addProperty("limit", buffer.limit());
        result.addProperty("capacity", buffer.capacity());
        result.addProperty("remaining", buffer.remaining());
        result.addProperty("readOnly", buffer.isReadOnly());
        result.addProperty("bytesSha256", HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)));
        return result;
    }

    public static void main(String[] args) throws Exception {
        JsonObject request = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject result = new JsonObject();
        result.addProperty("schema", 1);
        result.addProperty("os", System.getProperty("os.name"));
        result.addProperty("osVersion", System.getProperty("os.version"));
        result.addProperty("architecture", System.getProperty("os.arch"));
        result.addProperty("javaVersion", System.getProperty("java.version"));
        JsonArray rows = new JsonArray();
        if (request.has("className")) {
            Class<?> original = Class.forName(request.get("className").getAsString());
            Method validate = original.getDeclaredMethod(request.get("methodName").getAsString(), ByteBuffer.class);
            result.addProperty("originalClass", original.getName());
            result.addProperty("originalSigners", original.getSigners() == null ? 0 : original.getSigners().length);
            for (JsonElement element : request.getAsJsonArray("cases")) {
                JsonObject spec = element.getAsJsonObject();
                byte[] bytes = HexFormat.of().parseHex(spec.get("hex").getAsString());
                if (bytes.length > 33) throw new IllegalArgumentException("Outside tiny-buffer study.");
                ByteBuffer buffer = ByteBuffer.wrap(bytes);
                if (spec.get("readOnly").getAsBoolean()) buffer = buffer.asReadOnlyBuffer();
                buffer.limit(spec.get("limit").getAsInt()).position(spec.get("position").getAsInt());
                buffer.order(spec.get("order").getAsString().equals("LITTLE_ENDIAN") ? ByteOrder.LITTLE_ENDIAN : ByteOrder.BIG_ENDIAN);
                JsonObject row = new JsonObject();
                row.addProperty("id", spec.get("id").getAsString());
                row.add("before", state(buffer, bytes));
                try {
                    validate.invoke(null, buffer);
                    row.addProperty("status", "returned");
                } catch (InvocationTargetException error) {
                    Throwable cause = error.getCause();
                    row.addProperty("status", "threw");
                    row.addProperty("errorClass", cause.getClass().getName());
                    row.addProperty("message", cause.getMessage());
                }
                row.add("after", state(buffer, bytes));
                rows.add(row);
            }
        }
        result.add("cases", rows);
        JsonArray arithmetic = new JsonArray();
        for (JsonElement element : request.getAsJsonArray("arithmetic")) {
            JsonObject spec = element.getAsJsonObject();
            int width = spec.get("width").getAsInt();
            int height = spec.get("height").getAsInt();
            long estimate = 4L * (long) width * (long) height * 2L;
            JsonObject row = new JsonObject();
            row.addProperty("id", spec.get("id").getAsString());
            // Decimal strings preserve signed 64-bit values across JSON consumers.
            row.addProperty("wrappedLong", Long.toString(estimate));
            row.addProperty("narrowedInt", Integer.toString((int) estimate));
            row.addProperty("roundtrip", estimate == (long) (int) estimate);
            try {
                long exact = Math.multiplyExact(Math.multiplyExact(Math.multiplyExact(4L, (long) width), (long) height), 2L);
                row.addProperty("checked", Long.toString(exact));
            } catch (ArithmeticException error) {
                row.addProperty("checkedError", error.getClass().getName());
            }
            arithmetic.add(row);
        }
        result.add("arithmetic", arithmetic);
        Files.writeString(Path.of(args[1]), new GsonBuilder().setPrettyPrinting().create().toJson(result) + "\n");
    }
}
