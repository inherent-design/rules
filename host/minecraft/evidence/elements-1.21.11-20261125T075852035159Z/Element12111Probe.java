// Owner-run original 1.21.11 Gson element/face deserializers, without game startup.
package study.minecraft;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.google.gson.JsonParseException;
import com.google.gson.JsonParser;
import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.joml.Matrix4fc;
import org.joml.Vector3fc;

public final class Element12111Probe {
    private final JsonObject bindings;
    private Element12111Probe(JsonObject bindings) { this.bindings = bindings; }
    private Class<?> type(String role) throws ReflectiveOperationException {
        return Class.forName(bindings.getAsJsonObject(role).get("class").getAsString());
    }
    private Object construct(String role) throws ReflectiveOperationException {
        Constructor<?> c = type(role).getDeclaredConstructor(); c.setAccessible(true); return c.newInstance();
    }
    private Object get(String role, String field, Object value) throws ReflectiveOperationException {
        String name = bindings.getAsJsonObject(role).getAsJsonObject("getters").get(field).getAsString();
        Method m = value.getClass().getDeclaredMethod(name); m.setAccessible(true); return m.invoke(value);
    }
    private static JsonArray vector(Vector3fc v) {
        JsonArray a = new JsonArray(); a.add(v.x()); a.add(v.y()); a.add(v.z()); return a;
    }
    private JsonObject rotation(Object value) throws ReflectiveOperationException {
        JsonObject r = new JsonObject();
        if (value == null) { r.addProperty("kind", "absent"); return r; }
        Object angles = get("rotation", "value", value);
        r.add("origin", vector((Vector3fc)get("rotation", "origin", value)));
        r.addProperty("rescale", (Boolean)get("rotation", "rescale", value));
        if (angles.getClass().equals(type("euler"))) {
            r.addProperty("kind", "euler"); JsonArray a = new JsonArray();
            for (String f : new String[]{"x", "y", "z"}) a.add((Float)get("euler", f, angles));
            r.add("angles", a);
        } else if (angles.getClass().equals(type("scalar"))) {
            r.addProperty("kind", "scalar"); r.addProperty("axis", ((Enum<?>)get("scalar", "axis", angles)).name());
            r.addProperty("angle", (Float)get("scalar", "angle", angles));
        } else throw new IllegalStateException("Unselected rotation result class");
        Matrix4fc m = (Matrix4fc)get("rotation", "transform", value); JsonArray a = new JsonArray();
        for (float f : new float[]{m.m00(),m.m01(),m.m02(),m.m03(),m.m10(),m.m11(),m.m12(),m.m13(),m.m20(),m.m21(),m.m22(),m.m23(),m.m30(),m.m31(),m.m32(),m.m33()}) a.add(f);
        r.add("jomlComponents_m00_m01_m02_m03_m10_through_m33", a); return r;
    }
    private JsonElement face(Object value) throws ReflectiveOperationException {
        if (value == null) return JsonNull.INSTANCE;
        JsonObject r = new JsonObject(); Object cull = get("face", "cullForDirection", value);
        r.addProperty("cull", cull == null ? null : ((Enum<?>)cull).name());
        r.addProperty("tint", (Integer)get("face", "tintIndex", value));
        r.addProperty("texture", (String)get("face", "texture", value));
        r.addProperty("quadrant", ((Enum<?>)get("face", "rotation", value)).name());
        Object uv = get("face", "uvs", value);
        if (uv == null) r.add("uv", JsonNull.INSTANCE);
        else {
            JsonArray a = new JsonArray(); for (String f : new String[]{"minU","minV","maxU","maxV"}) a.add((Float)get("uvs", f, uv));
            r.add("uv", a);
        }
        return r;
    }
    private JsonObject element(Object value) throws ReflectiveOperationException {
        JsonObject r = new JsonObject();
        r.add("from", vector((Vector3fc)get("element", "from", value))); r.add("to", vector((Vector3fc)get("element", "to", value)));
        r.addProperty("shade", (Boolean)get("element", "shade", value)); r.addProperty("light", (Integer)get("element", "lightEmission", value));
        r.add("rotation", rotation(get("element", "rotation", value))); JsonObject faces = new JsonObject();
        Object map = get("element", "faces", value);
        if (!(map instanceof Map<?,?> entries)) throw new IllegalStateException("Unselected face container");
        for (Map.Entry<?,?> entry : entries.entrySet()) faces.add(((Enum<?>)entry.getKey()).name(), face(entry.getValue()));
        r.add("faces", faces); return r;
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("Supply frozen bindings, requests and output paths");
        Element12111Probe probe = new Element12111Probe(JsonParser.parseString(Files.readString(Path.of(args[0]), StandardCharsets.UTF_8)).getAsJsonObject());
        Gson gson = new GsonBuilder().registerTypeAdapter(probe.type("element"), probe.construct("elementDeserializer"))
            .registerTypeAdapter(probe.type("face"), probe.construct("faceDeserializer")).create();
        JsonObject requests = JsonParser.parseString(Files.readString(Path.of(args[1]), StandardCharsets.UTF_8)).getAsJsonObject();
        JsonArray rows = new JsonArray(); int errors = 0;
        for (JsonElement input : requests.getAsJsonArray("cases")) {
            JsonObject request = input.getAsJsonObject(), row = new JsonObject(); row.add("case", request.get("id")); row.add("input", request.get("input").deepCopy());
            try { Object result = gson.fromJson(request.get("input"), probe.type("element")); row.addProperty("accepted", true); row.add("value", probe.element(result)); }
            catch (JsonParseException failure) { row.addProperty("accepted", false); row.addProperty("exception", failure.getClass().getName()); row.addProperty("message", failure.getMessage()); }
            catch (ReflectiveOperationException | LinkageError | RuntimeException failure) { errors++; row.addProperty("observerError", true); row.addProperty("exception", failure.getClass().getName()); row.addProperty("message", failure.getMessage()); }
            rows.add(row);
        }
        JsonObject result = new JsonObject(); result.addProperty("schema", 1); result.addProperty("observerErrors", errors); result.add("cases", rows);
        Files.writeString(Path.of(args[2]), result.toString()+"\n", StandardCharsets.UTF_8); System.out.println("cases="+rows.size()+" observerErrors="+errors);
        if (errors != 0) System.exit(3);
    }
}
