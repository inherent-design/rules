// Headless owner-run observer. Invokes original client code through official mappings.
// No launcher, game instance, renderer, account, or network operation is invoked here.
package study.minecraft;

import com.google.gson.*;
import com.mojang.serialization.Codec;
import com.mojang.serialization.DataResult;
import com.mojang.serialization.JsonOps;
import com.mojang.serialization.MapCodec;
import java.lang.reflect.*;
import java.io.Reader;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

public final class CodecProbe {
    private static JsonObject mappings;
    private static JsonObject mapping(String name) {
        JsonObject value = mappings.getAsJsonObject(name);
        if (value == null) throw new IllegalArgumentException("Unbound observer class: " + name);
        return value;
    }
    private static Class<?> type(String name) throws ClassNotFoundException {
        return Class.forName(mapping(name).get("name").getAsString());
    }
    private static String fieldName(String owner, String name) throws NoSuchFieldException {
        JsonElement found = mapping(owner).getAsJsonObject("fields").get(name);
        if (found == null) throw new NoSuchFieldException(owner + "." + name);
        return found.getAsString();
    }
    private static String methodName(String owner, String signature) throws NoSuchMethodException {
        JsonElement found = mapping(owner).getAsJsonObject("methods").get(signature);
        if (found == null) throw new NoSuchMethodException(owner + "." + signature);
        return found.getAsString();
    }
    private static Object field(String owner, String name, Object receiver) throws ReflectiveOperationException {
        Field field = type(owner).getDeclaredField(fieldName(owner, name));
        field.setAccessible(true);
        return field.get(receiver);
    }
    private static Object invoke(String owner, String signature, Object receiver,
                                 Class<?>[] parameters, Object... arguments) throws ReflectiveOperationException {
        Method method = type(owner).getDeclaredMethod(methodName(owner, signature), parameters);
        method.setAccessible(true);
        return method.invoke(receiver, arguments);
    }
    private static JsonElement scalar(Object value) {
        if (value == null) return JsonNull.INSTANCE;
        if (value instanceof Optional<?> optional) {
            JsonObject result = new JsonObject();
            result.addProperty("present", optional.isPresent());
            optional.ifPresent(item -> result.add("value", scalar(item)));
            return result;
        }
        if (value instanceof Boolean b) return new JsonPrimitive(b);
        if (value instanceof Number number) {
            if (!Double.isFinite(number.doubleValue())) return new JsonPrimitive(number.toString());
            return new JsonPrimitive(number);
        }
        if (value instanceof String text) return new JsonPrimitive(text);
        JsonObject result = new JsonObject();
        result.addProperty("nativeClass", value.getClass().getName());
        if (value instanceof Collection<?> collection) result.addProperty("size", collection.size());
        if (value instanceof Map<?, ?> map) {
            result.addProperty("size", map.size());
            JsonArray values = new JsonArray();
            for (Object item : map.values()) values.add(scalar(item));
            result.add("values", values);
        }
        return result;
    }
    private static Throwable cause(Throwable error) {
        while (error instanceof InvocationTargetException && error.getCause() != null) error = error.getCause();
        return error;
    }
    private static JsonObject observe(JsonObject input) {
        JsonObject result = new JsonObject();
        result.addProperty("id", input.get("id").getAsString());
        String owner = input.get("class").getAsString();
        String action = input.get("action").getAsString();
        String phase = "observer_lookup";
        try {
            JsonElement document = input.get("input");
            Object value;
            if (action.equals("codec")) {
                Object raw = field(owner, input.get("member").getAsString(), null);
                Codec<?> codec = raw instanceof MapCodec<?> map ? map.codec() : (Codec<?>) raw;
                phase = "native_decode";
                DataResult<?> decoded = codec.parse(JsonOps.INSTANCE, document);
                result.addProperty("accepted", decoded.result().isPresent());
                result.addProperty("partial", decoded.error().map(error -> error.partialValue().isPresent()).orElse(false));
                decoded.error().ifPresent(error -> result.addProperty("message", error.message()));
                value = decoded.result().orElse(null);
            } else if (action.equals("block_model")) {
                phase = "native_decode";
                value = input.has("reader") && input.get("reader").getAsBoolean()
                    ? invoke(owner, "fromStream(java.io.Reader)", null, new Class<?>[]{Reader.class}, new StringReader(document.toString()))
                    : invoke(owner, "fromString(java.lang.String)", null, new Class<?>[]{String.class}, document.toString());
                result.addProperty("accepted", true);
            } else if (action.equals("particle")) {
                phase = "native_decode";
                value = invoke(owner, "fromJson(com.google.gson.JsonObject)", null,
                    new Class<?>[]{JsonObject.class}, document.getAsJsonObject());
                result.addProperty("accepted", true);
            } else if (action.equals("metadata_serializer")) {
                String holder = input.get("holder").getAsString();
                Object serializer = field(holder, input.get("member").getAsString(), null);
                phase = "native_decode";
                value = invoke(owner, input.get("observationClass").getAsString() + " fromJson(com.google.gson.JsonObject)", serializer,
                    new Class<?>[]{JsonObject.class}, document.getAsJsonObject());
                result.addProperty("accepted", true);
            } else if (action.equals("sound")) {
                Constructor<?> constructor = type(input.get("serializer").getAsString()).getDeclaredConstructor();
                constructor.setAccessible(true);
                Object serializer = constructor.newInstance();
                phase = "native_decode";
                value = new GsonBuilder().registerTypeAdapter(type(owner), serializer).create().fromJson(document, type(owner));
                result.addProperty("accepted", true);
            } else throw new IllegalArgumentException("Unknown observer action: " + action);
            if (value != null && input.has("fields")) {
                phase = "observer_fields";
                JsonObject observed = new JsonObject();
                String observationOwner = input.has("observationClass")
                    ? input.get("observationClass").getAsString() : owner;
                for (JsonElement name : input.getAsJsonArray("fields")) {
                    String selected = name.getAsString();
                    observed.add(selected, scalar(field(observationOwner, selected, value)));
                }
                result.add("fields", observed);
            }
        } catch (Throwable original) {
            Throwable error = cause(original);
            boolean observerError = !phase.equals("native_decode")
                || error instanceof ReflectiveOperationException || error instanceof LinkageError;
            if (!result.has("accepted")) result.addProperty("accepted", false);
            result.addProperty("phase", phase);
            result.addProperty("observerError", observerError);
            result.addProperty("exception", error.getClass().getName());
            result.addProperty("message", String.valueOf(error.getMessage()));
        }
        return result;
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Supply frozen request and output paths.");
        JsonObject request = JsonParser.parseString(Files.readString(Path.of(args[0]), StandardCharsets.UTF_8)).getAsJsonObject();
        mappings = request.getAsJsonObject("mappings");
        for (JsonElement item : request.getAsJsonArray("initializers")) {
            JsonObject initializer = item.getAsJsonObject();
            invoke(initializer.get("class").getAsString(), initializer.get("method").getAsString(), null, new Class<?>[0]);
        }
        JsonArray results = new JsonArray();
        for (JsonElement input : request.getAsJsonArray("cases")) results.add(observe(input.getAsJsonObject()));
        Files.writeString(Path.of(args[1]), new GsonBuilder().setPrettyPrinting().create().toJson(results) + "\n", StandardCharsets.UTF_8);
    }
}
