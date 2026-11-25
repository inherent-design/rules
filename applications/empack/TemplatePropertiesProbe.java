import java.io.ByteArrayInputStream;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HexFormat;
import java.util.Properties;

/** Read retained encoder outputs; no launch, networking, or system property writes. */
public class TemplatePropertiesProbe {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) throw new IllegalArgumentException("Supply one retained TSV path");
        System.out.println("runtime\t" + System.getProperty("java.runtime.version"));
        for (String line : Files.readAllLines(Path.of(args[0]), StandardCharsets.UTF_8)) {
            String[] fields = line.split("\t", -1);
            if (!fields[1].equals("value")) continue;
            String encoded = new String(HexFormat.of().parseHex(fields[3]), StandardCharsets.US_ASCII);
            byte[] file = ("value=" + encoded + "\n").getBytes(StandardCharsets.US_ASCII);
            for (String route : new String[]{"stream", "reader"}) {
                Properties result = new Properties();
                if (route.equals("stream")) result.load(new ByteArrayInputStream(file));
                else result.load(new StringReader(new String(file, StandardCharsets.US_ASCII)));
                System.out.println(fields[0] + "\t" + route + "\t" + result.size() + "\t" +
                    HexFormat.of().formatHex(result.getProperty("value").getBytes(StandardCharsets.UTF_8)));
            }
        }
    }
}
