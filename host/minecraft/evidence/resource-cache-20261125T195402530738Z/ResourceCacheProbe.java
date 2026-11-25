package design.inherent.skyweavecompat.client.model;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Authored calls to original host-free cache methods; no game classes or copied implementation. */
public final class ResourceCacheProbe {
    private ResourceCacheProbe() {}

    public static void main(String[] argv) throws Exception {
        JsonObject input = JsonParser.parseString(Files.readString(Path.of(argv[0]))).getAsJsonObject();
        JsonArray cases = new JsonArray();
        for (JsonElement item : input.getAsJsonArray("cases")) {
            JsonObject spec = item.getAsJsonObject();
            JsonObject result = new JsonObject();
            result.addProperty("id", spec.get("id").getAsString());
            List<String> events = new ArrayList<>();
            ResourceValueCache cache;
            try {
                cache = new ResourceValueCache(spec.get("capacity").getAsInt());
                result.addProperty("construction", "returned");
            } catch (Exception failure) {
                result.addProperty("construction", "threw");
                result.addProperty("errorClass", failure.getClass().getSimpleName());
                result.addProperty("message", failure.getMessage());
                cases.add(result);
                continue;
            }
            Map<String, Object> objects = new HashMap<>();
            objects.put("a", new String("same-value"));
            objects.put("b", new String("same-value"));
            objects.put("c", new String("other-value"));
            result.addProperty("aEqualsB", objects.get("a").equals(objects.get("b")));
            result.addProperty("aIdenticalB", objects.get("a") == objects.get("b"));
            JsonArray steps = new JsonArray();
            for (JsonElement entry : spec.getAsJsonArray("actions")) {
                JsonObject action = entry.getAsJsonObject();
                JsonObject step = new JsonObject();
                String operation = action.get("op").getAsString();
                step.addProperty("op", operation);
                try {
                    switch (operation) {
                        case "project" -> {
                            String token = action.get("token").getAsString();
                            Object component = token.equals("null") ? null : objects.get(token);
                            ResourceValueCache.Kind kind = ResourceValueCache.Kind.valueOf(action.get("kind").getAsString());
                            String marker = action.get("marker").getAsString();
                            Object value = cache.project(kind, component, ignored -> {
                                events.add("project:" + marker);
                                if (action.get("throw").getAsBoolean()) throw new IllegalStateException("authored projection:" + marker);
                                return action.get("value").isJsonNull() ? null : action.get("value").getAsString();
                            });
                            step.addProperty("value", value == ResourceValueCache.ABSENT ? "absent" : "string:" + value);
                        }
                        case "onClear" -> {
                            String marker = action.get("marker").getAsString();
                            int[] remaining = {action.get("failures").getAsInt()};
                            cache.onClear(() -> {
                                events.add("clear:" + marker);
                                if (remaining[0] > 0) {
                                    remaining[0]--;
                                    throw new IllegalStateException("authored clear:" + marker);
                                }
                            });
                        }
                        case "clear" -> cache.clear();
                        default -> throw new IllegalArgumentException("Unselected fixture operation");
                    }
                    step.addProperty("status", "returned");
                } catch (Exception failure) {
                    step.addProperty("status", "threw");
                    step.addProperty("errorClass", failure.getClass().getSimpleName());
                    step.addProperty("message", failure.getMessage());
                }
                step.addProperty("size", cache.size());
                step.add("events", new Gson().toJsonTree(events));
                steps.add(step);
            }
            result.add("steps", steps);
            cases.add(result);
        }
        JsonObject output = new JsonObject();
        output.addProperty("schema", 1);
        output.add("cases", cases);
        Files.writeString(Path.of(argv[1]), new GsonBuilder().serializeNulls().create().toJson(output) + "\n");
    }
}
