package study.minecraft;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/** Authored observer of one original static method; no item/world/bake fixture. */
public final class Range1214Probe {
    private Range1214Probe() { }

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("bindings requests output");
        JsonObject bindings = JsonParser.parseString(Files.readString(Path.of(args[0]), StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject request = JsonParser.parseString(Files.readString(Path.of(args[1]), StandardCharsets.UTF_8)).getAsJsonObject();
        Class<?> original = Class.forName(bindings.get("class").getAsString());
        Method search = original.getDeclaredMethod(bindings.get("method").getAsString(), float[].class, float.class);
        search.setAccessible(true);
        JsonArray rows = new JsonArray();
        int observerErrors = 0;
        for (JsonElement element : request.getAsJsonArray("cases")) {
            JsonObject input = element.getAsJsonObject();
            JsonObject row = new JsonObject();
            row.addProperty("case", input.get("id").getAsString());
            row.add("input", input.deepCopy());
            JsonArray supplied = input.getAsJsonArray("thresholds");
            float[] thresholds = new float[supplied.size()];
            for (int i = 0; i < thresholds.length; i++) thresholds[i] = supplied.get(i).getAsFloat();
            float query = input.get("query").getAsFloat();
            JsonArray before = new JsonArray();
            for (float value : thresholds) before.add(value);
            row.add("nativeThresholdsBefore", before);
            row.addProperty("nativeQuery", query);
            try {
                int index = ((Integer)search.invoke(null, thresholds, query)).intValue();
                row.addProperty("index", index);
            } catch (InvocationTargetException error) {
                observerErrors++;
                Throwable cause = error.getCause();
                row.addProperty("observerError", cause.getClass().getName());
                row.addProperty("message", cause.getMessage());
            }
            JsonArray after = new JsonArray();
            for (float value : thresholds) after.add(value);
            row.add("nativeThresholdsAfter", after);
            rows.add(row);
        }
        JsonObject result = new JsonObject();
        result.addProperty("schema", 1);
        result.addProperty("observerErrors", observerErrors);
        result.add("cases", rows);
        Gson gson = new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();
        Files.writeString(Path.of(args[2]), gson.toJson(result) + "\n", StandardCharsets.UTF_8);
        System.out.println("Observed " + rows.size() + " original range-search calls; observerErrors=" + observerErrors);
        if (observerErrors != 0) System.exit(2);
    }
}
