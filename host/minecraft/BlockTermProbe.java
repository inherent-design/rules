package study.minecraft;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;

/** Literal atom records only; no Terms codec, property domain, state, or game. */
public final class BlockTermProbe {
    private BlockTermProbe() { }

    private static JsonObject term(Object value, Method text, Method negated) throws Exception {
        JsonObject out = new JsonObject();
        out.addProperty("value", (String) text.invoke(value));
        out.addProperty("negated", (boolean) negated.invoke(value));
        out.addProperty("encoded", value.toString());
        return out;
    }

    public static void main(String[] args) throws Exception {
        JsonObject request = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject bindings = request.getAsJsonObject("bindings");
        Class<?> original = Class.forName(bindings.get("className").getAsString());
        Method parse = original.getMethod(bindings.get("parse").getAsString(), String.class);
        Method text = original.getMethod(bindings.get("value").getAsString());
        Method negated = original.getMethod(bindings.get("negated").getAsString());
        Constructor<?> construct = original.getConstructor(String.class, boolean.class);
        JsonArray rows = new JsonArray();
        for (JsonElement element : request.getAsJsonArray("cases")) {
            JsonObject spec = element.getAsJsonObject();
            String input = spec.get("value").getAsString();
            if (input.length() > 32) throw new IllegalArgumentException("Outside short literal atom profile.");
            JsonObject row = new JsonObject();
            row.addProperty("id", spec.get("id").getAsString());
            row.addProperty("inputUtf16Length", input.length());
            try {
                Object value = spec.get("operation").getAsString().equals("parse")
                    ? parse.invoke(null, input) : construct.newInstance(input, spec.get("negated").getAsBoolean());
                row.addProperty("status", "returned");
                row.add("term", term(value, text, negated));
                try {
                    Object parsed = parse.invoke(null, value.toString());
                    row.addProperty("reparseStatus", "returned");
                    row.add("reparsed", term(parsed, text, negated));
                    row.addProperty("equalAfterReparse", value.equals(parsed));
                } catch (InvocationTargetException failure) {
                    row.addProperty("reparseStatus", "threw");
                    row.addProperty("reparseErrorClass", failure.getCause().getClass().getName());
                }
            } catch (InvocationTargetException failure) {
                row.addProperty("status", "threw");
                row.addProperty("errorClass", failure.getCause().getClass().getName());
                row.addProperty("message", failure.getCause().getMessage());
            }
            rows.add(row);
        }
        JsonObject output = new JsonObject();
        output.addProperty("schema", 1);
        output.addProperty("os", System.getProperty("os.name"));
        output.addProperty("osVersion", System.getProperty("os.version"));
        output.addProperty("architecture", System.getProperty("os.arch"));
        output.addProperty("javaVersion", System.getProperty("java.version"));
        output.addProperty("originalClass", original.getName());
        output.addProperty("originalSigners", original.getSigners() == null ? 0 : original.getSigners().length);
        output.add("cases", rows);
        Files.writeString(Path.of(args[1]), new GsonBuilder().setPrettyPrinting().create().toJson(output) + "\n");
    }
}
