package study.minecraft;

import com.google.gson.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

/** Original font-option filter APIs; no provider loading, glyph or renderer calls. */
public final class FontFilterProbe {
    private FontFilterProbe() { }
    private static Object uniform, japanese;
    private static Constructor<?> ctor;
    private static Method apply, merge;
    private static Map<Object,Boolean> map(int code) {
        Map<Object,Boolean> result=new HashMap<>();int a=code%3,b=code/3;
        if(a!=0)result.put(uniform,a==2);if(b!=0)result.put(japanese,b==2);return result;
    }
    private static Set<Object> options(int bits) {
        Set<Object> result=new HashSet<>();if((bits&1)!=0)result.add(uniform);if((bits&2)!=0)result.add(japanese);return result;
    }
    private static JsonObject row(String kind,int left,int right,int bits,Object filter) throws Exception {
        JsonObject row=new JsonObject();row.addProperty("kind",kind);row.addProperty("left",left);row.addProperty("right",right);row.addProperty("mask",bits);
        row.addProperty("result",(Boolean)apply.invoke(filter,options(bits)));return row;
    }
    public static void main(String[] args) throws Exception {
        JsonObject bindings=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject ob=bindings.getAsJsonObject("option"),fb=bindings.getAsJsonObject("filter");
        Class<?> option=Class.forName(ob.get("class").getAsString()),filter=Class.forName(fb.get("class").getAsString());
        if(option.getEnumConstants().length!=2)throw new IllegalStateException("Unselected option universe");
        Field u=option.getDeclaredField(ob.getAsJsonObject("fields").get("UNIFORM").getAsString());u.setAccessible(true);uniform=u.get(null);
        Field j=option.getDeclaredField(ob.getAsJsonObject("fields").get("JAPANESE_VARIANTS").getAsString());j.setAccessible(true);japanese=j.get(null);
        ctor=filter.getDeclaredConstructor(Map.class);ctor.setAccessible(true);
        apply=filter.getDeclaredMethod(fb.getAsJsonObject("methods").get("apply").getAsString(),Set.class);apply.setAccessible(true);
        merge=filter.getDeclaredMethod(fb.getAsJsonObject("methods").get("merge").getAsString(),filter);merge.setAccessible(true);
        JsonArray rows=new JsonArray(),controls=new JsonArray();
        for(int left=0;left<9;left++) {
            Object self=ctor.newInstance(map(left));
            for(int mask=0;mask<4;mask++)rows.add(row("direct",left,0,mask,self));
            for(int right=0;right<9;right++) {
                Object combined=merge.invoke(self,ctor.newInstance(map(right)));
                for(int mask=0;mask<4;mask++)rows.add(row("merged",left,right,mask,combined));
            }
        }
        Map<Object,Boolean> source=map(2);Object borrowed=ctor.newInstance(source),snapshot=merge.invoke(borrowed,ctor.newInstance(map(0)));
        controls.add(row("before-borrowed",2,0,1,borrowed));controls.add(row("before-snapshot",2,0,1,snapshot));
        source.put(uniform,false);
        controls.add(row("after-borrowed",1,0,1,borrowed));controls.add(row("after-snapshot",2,0,1,snapshot));
        JsonObject output=new JsonObject();output.addProperty("schema",1);output.addProperty("observerErrors",0);output.addProperty("options",2);
        output.add("rows",rows);output.add("controls",controls);
        Files.writeString(Path.of(args[1]),new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create().toJson(output)+"\n");
        System.out.println("Observed "+rows.size()+" original filter applications and "+controls.size()+" map-custody applications;no glyph/provider load");
    }
}
