package study.minecraft;

import com.google.gson.*;
import design.inherent.skyweavecompat.Feature;
import design.inherent.skyweavecompat.FeatureSettings;
import design.inherent.skyweavecompat.FeatureSelection;
import design.inherent.skyweavecompat.client.model.MultiAxisModels;
import java.io.StringReader;
import java.nio.file.*;
import java.util.*;

/** Selected original Compat policy/helper APIs;metadata and JSON fixtures only. */
public final class ProviderProbe {
    private ProviderProbe() { }
    private static int observerErrors;
    private static final Gson gson=new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();
    private static void error(JsonObject row,Throwable error) {
        row.addProperty("status","threw");row.addProperty("errorClass",error.getClass().getSimpleName());
        row.addProperty("message",String.valueOf(error.getMessage()));
        if(error instanceof LinkageError||error instanceof ReflectiveOperationException)observerErrors++;
    }
    private static JsonObject metadata(JsonObject spec) {
        JsonObject row=new JsonObject();row.addProperty("id",spec.get("id").getAsString());
        if(spec.has("compatSelected")&&!spec.get("compatSelected").getAsBoolean()) {
            row.addProperty("status","not-invoked");return row;
        }
        try {
            var values=new EnumMap<Feature,Boolean>(Feature.class);
            for(Feature feature:Feature.values())values.put(feature,false);
            for(var entry:Map.of("model",Feature.MODEL_ROTATIONS,"items",Feature.ITEM_DEFINITIONS).entrySet()) {
                int value=spec.get(entry.getKey()).getAsInt();
                if(value==-1)values.remove(entry.getValue());else values.put(entry.getValue(),value==1);
            }
            Map<String,String> mods=new TreeMap<>();
            for(var entry:spec.getAsJsonObject("mods").entrySet())mods.put(entry.getKey(),entry.getValue().getAsString());
            var selection=FeatureSelection.select(new FeatureSettings(values),mods,spec.get("client").getAsBoolean());
            JsonObject result=new JsonObject();
            for(Feature feature:List.of(Feature.MODEL_ROTATIONS,Feature.ITEM_DEFINITIONS)) {
                JsonObject fact=new JsonObject();fact.addProperty("enabled",selection.enabled(feature));
                var reason=selection.reasons().get(feature);
                if(reason!=null){fact.addProperty("reason",reason.kind().name());fact.add("details",gson.toJsonTree(reason.details()));}
                result.add(feature.key,fact);
            }
            row.addProperty("status","returned");row.add("features",result);
            row.add("mixins",gson.toJsonTree(selection.mixins(spec.get("client").getAsBoolean())));
        }catch(Throwable failure){error(row,failure);}
        return row;
    }
    private static JsonObject configuration(JsonObject spec) {
        JsonObject row=new JsonObject();row.addProperty("id",spec.get("id").getAsString());
        try {
            var settings=FeatureSettings.read(new StringReader(spec.get("properties").getAsString()));
            row.addProperty("status","returned");row.addProperty("model",settings.enabled(Feature.MODEL_ROTATIONS));
            row.addProperty("items",settings.enabled(Feature.ITEM_DEFINITIONS));
        }catch(Throwable failure){error(row,failure);}
        return row;
    }
    private static JsonObject adaptation(JsonObject spec) {
        JsonObject row=new JsonObject();row.addProperty("id",spec.get("id").getAsString());
        JsonElement input=spec.get("input");String before=gson.toJson(input);
        try {
            JsonElement output=MultiAxisModels.adapt(input);row.addProperty("status","returned");
            row.addProperty("sameObject",output==input);row.add("output",output.deepCopy());
        }catch(Throwable failure){error(row,failure);}
        row.addProperty("inputBytesUnchanged",before.equals(gson.toJson(input)));return row;
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=2)throw new IllegalArgumentException("Supply request and output.");
        JsonObject request=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        if(request.get("schema").getAsInt()!=1)throw new IllegalArgumentException("Unselected provider research schema.");
        JsonObject output=new JsonObject();output.addProperty("schema",1);
        for(String family:List.of("metadata","configuration","adaptation")) {
            JsonArray results=new JsonArray();
            for(JsonElement item:request.getAsJsonArray(family)) {
                JsonObject spec=item.getAsJsonObject();
                results.add(switch(family){case "metadata"->metadata(spec);case "configuration"->configuration(spec);default->adaptation(spec);});
            }
            output.add(family,results);
        }
        JsonObject defaults=new JsonObject();
        for(Feature feature:List.of(Feature.MODEL_ROTATIONS,Feature.ITEM_DEFINITIONS))defaults.addProperty(feature.key,feature.defaultEnabled);
        output.add("featureDefaults",defaults);output.addProperty("observerErrors",observerErrors);
        Files.writeString(Path.of(args[1]),gson.toJson(output)+"\n");System.out.println("Recorded provider metadata/Reader/JSON helper cases;no loader or game launch.");
    }
}
