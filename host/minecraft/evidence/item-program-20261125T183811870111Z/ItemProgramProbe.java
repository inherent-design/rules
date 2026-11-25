package study.minecraft;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import design.inherent.skyweavecompat.client.model.ResourceDefinitions;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Predicate;
import java.util.function.ToDoubleFunction;
import java.util.function.ToIntFunction;

/** Original generic compiler/consumer calls with explicit authored Values and context adapters. */
public final class ItemProgramProbe {
    private static final Gson GSON = new Gson();

    private static final class Values implements ResourceDefinitions.Values<JsonObject> {
        final List<String> events;
        Values(List<String> events) { this.events = events; }

        @Override public ResourceDefinitions.Selector<JsonObject> select(String id, JsonObject definition) {
            events.add("compile:select:" + id);
            if (!id.equals("study:pick")) throw new IllegalArgumentException("Unselected fixture selector");
            return new ResourceDefinitions.Selector<>() {
                @Override public Object decode(JsonElement value) {
                    if (!value.isJsonPrimitive() || !value.getAsJsonPrimitive().isString())
                        throw new IllegalArgumentException("Unselected fixture case value");
                    events.add("decode:" + value.getAsString());
                    return value.getAsString();
                }
                @Override public Object current(JsonObject context) {
                    events.add("evaluate:select");
                    return context.get("pick").getAsString();
                }
            };
        }

        @Override public Predicate<JsonObject> condition(String id, JsonObject definition) {
            events.add("compile:condition:" + id);
            if (!id.equals("study:condition")) throw new IllegalArgumentException("Unselected fixture condition");
            return context -> { events.add("evaluate:condition"); return context.get("condition").getAsBoolean(); };
        }

        @Override public ToDoubleFunction<JsonObject> range(String id, JsonObject definition) {
            events.add("compile:range:" + id);
            if (!id.equals("study:number")) throw new IllegalArgumentException("Unselected fixture number");
            return context -> { events.add("evaluate:range"); return Double.parseDouble(context.get("number").getAsString()); };
        }

        @Override public ToIntFunction<JsonObject> tint(String id, JsonObject definition) {
            events.add("compile:tint:" + id);
            if (!id.equals("study:color")) throw new IllegalArgumentException("Unselected fixture tint");
            return context -> { events.add("evaluate:tint"); return context.get("color").getAsInt(); };
        }
    }

    private static JsonObject run(JsonObject spec) {
        JsonObject row = new JsonObject();
        row.addProperty("id", spec.get("id").getAsString());
        JsonObject input = spec.getAsJsonObject("input");
        String before = GSON.toJson(input);
        List<String> events = new ArrayList<>();
        try {
            ResourceDefinitions.Root<JsonObject> root = ResourceDefinitions.compile(input, new Values(events));
            row.addProperty("compile", "returned");
            row.add("dependencies", GSON.toJsonTree(root.dependencies().stream().sorted().toList()));
            row.addProperty("handAnimation", root.handAnimation());
            row.addProperty("oversizedInGui", root.oversizedInGui());
            row.addProperty("swapScaleBits", Integer.toUnsignedString(Float.floatToRawIntBits(root.swapScale())));
            JsonArray results = new JsonArray();
            for (JsonElement entry : spec.getAsJsonArray("contexts")) {
                JsonObject context = entry.getAsJsonObject();
                JsonObject result = new JsonObject();
                result.addProperty("contextId", context.get("id").getAsString());
                JsonArray layers = new JsonArray();
                for (ResourceDefinitions.Layer<JsonObject> layer : root.layers(context)) {
                    JsonObject value = new JsonObject();
                    value.addProperty("model", layer.model());
                    JsonArray tints = new JsonArray();
                    for (ToIntFunction<JsonObject> tint : layer.tints()) tints.add(tint.applyAsInt(context));
                    value.add("tints", tints); layers.add(value);
                }
                result.add("layers", layers); results.add(result);
            }
            row.add("results", results);
            row.addProperty("status", "returned");
        } catch (Throwable failure) {
            row.addProperty("status", "threw");
            row.addProperty("errorClass", failure.getClass().getSimpleName());
            row.addProperty("message", failure.getMessage());
        }
        row.addProperty("inputSerializationUnchanged", before.equals(GSON.toJson(input)));
        row.add("events", GSON.toJsonTree(events));
        return row;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Supply request and output");
        JsonObject request = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        if (request.get("schema").getAsInt() != 1) throw new IllegalArgumentException("Unselected research schema");
        JsonArray results = new JsonArray();
        for (JsonElement value : request.getAsJsonArray("cases")) results.add(run(value.getAsJsonObject()));
        JsonObject output = new JsonObject(); output.addProperty("schema", 1); output.add("cases", results);
        Files.writeString(Path.of(args[1]), GSON.toJson(output) + "\n");
        System.out.println("Recorded original generic resource compiler/layer calls with authored Values/context; no game or loader.");
    }
}
