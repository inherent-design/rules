// Static original-client inspection using Java25's stable Class-File API.
// Never defines,initializes,links or invokes a class from the inspected JAR.
package study.host;

import java.io.PrintWriter;
import java.lang.classfile.ClassFile;
import java.lang.classfile.instruction.InvokeInstruction;
import java.lang.classfile.instruction.InvokeDynamicInstruction;
import java.lang.reflect.AccessFlag;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.zip.ZipFile;

public final class HostApiScan {
    private static String q(String s) {
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }
    private static String family(String owner) {
        if (owner.startsWith("java/lang/foreign/")) return "foreign-memory";
        if (owner.startsWith("java/nio/file/") || owner.startsWith("java/io/")) return "filesystem-stream";
        if (owner.startsWith("java/net/")) return "network";
        if (owner.startsWith("io/netty/")) return "network-netty";
        if (owner.startsWith("java/util/concurrent/") || owner.equals("java/lang/Thread") || owner.startsWith("java/lang/Thread$") || owner.startsWith("java/lang/ScopedValue")) return "work-scope";
        if (owner.equals("java/lang/Runtime") || owner.equals("java/lang/System") || owner.startsWith("java/lang/Process")) return "process-runtime";
        if (owner.startsWith("java/awt/") || owner.startsWith("javax/swing/")) return "desktop";
        if (owner.startsWith("java/security/") || owner.startsWith("javax/crypto/")) return "security-crypto";
        if (owner.startsWith("java/lang/reflect/") || owner.startsWith("java/lang/invoke/") || owner.equals("java/lang/Class") || owner.startsWith("java/lang/ClassLoader")) return "reflection-loading";
        if (owner.contains("/Unsafe")) return "unsafe";
        if (owner.startsWith("com/sun/jna/") || owner.startsWith("oshi/")) return "native-platform";
        if (owner.startsWith("org/lwjgl/")) return "lwjgl";
        if (owner.startsWith("com/mojang/renderpearl/")) return "renderpearl";
        return "";
    }
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Supply one owned read-only client JAR");
        int classes=0,methods=0,dynamic=0,selected=0;
        var parser=ClassFile.of();
        var digest=MessageDigest.getInstance("SHA-256");
        var out=new PrintWriter(System.out,false,StandardCharsets.UTF_8);
        try (var jar=new ZipFile(Path.of(args[0]).toFile())) {
            for (var entry:jar.stream().filter(e -> e.getName().endsWith(".class")).sorted(java.util.Comparator.comparing(java.util.zip.ZipEntry::getName)).toList()) {
                byte[] bytes;
                try (var in=jar.getInputStream(entry)) { bytes=in.readAllBytes(); }
                var model=parser.parse(bytes);classes++;
                String owner=model.thisClass().asInternalName();
                out.println("{\"kind\":\"class\",\"entry\":"+q(entry.getName())+",\"name\":"+q(owner)+",\"sha256\":"+q(HexFormat.of().formatHex(digest.digest(bytes)))+",\"major\":"+model.majorVersion()+",\"minor\":"+model.minorVersion()+"}");
                for (var method:model.methods()) {
                    methods++;
                    String prefix="\"caller\":"+q(owner)+",\"method\":"+q(method.methodName().stringValue())+",\"descriptor\":"+q(method.methodType().stringValue());
                    if (method.flags().has(AccessFlag.NATIVE)) out.println("{\"kind\":\"native-declaration\","+prefix+"}");
                    if (method.code().isEmpty()) continue;
                    int ordinal=0;
                    for (var element:method.code().get()) {
                        if (element instanceof InvokeDynamicInstruction) dynamic++;
                        if (element instanceof InvokeInstruction call) {
                            String callee=call.owner().asInternalName(),group=family(callee);
                            if (!group.isEmpty()) {
                                selected++;
                                out.println("{\"kind\":\"invoke\","+prefix+",\"elementOrdinal\":"+ordinal+",\"family\":"+q(group)+",\"opcode\":"+q(call.opcode().name())+",\"owner\":"+q(callee)+",\"name\":"+q(call.name().stringValue())+",\"type\":"+q(call.type().stringValue())+"}");
                            }
                        }
                        ordinal++;
                    }
                }
            }
        }
        out.println("{\"kind\":\"summary\",\"classes\":"+classes+",\"methods\":"+methods+",\"selectedInvokeInstructions\":"+selected+",\"dynamicInvokeInstructions\":"+dynamic+"}");
        out.flush();
        if (out.checkError()) throw new IllegalStateException("Static scan output failed");
    }
}
