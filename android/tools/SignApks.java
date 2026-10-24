import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Properties;

/** Locally sign CI intermediates; private properties never leave this machine. */
class SignApks {
    public static void main(String[] args) throws Exception {
        if (args.length != 4) {
            throw new IllegalArgumentException(
                "Usage: SignApks.java <signing.properties> <SDK> <unsigned APK root> <output APK root>");
        }
        Path propertiesFile = Path.of(args[0]).toRealPath();
        Properties properties = new Properties();
        try (var input = Files.newInputStream(propertiesFile)) {
            properties.load(input);
        }
        Path store = Path.of(required(properties, "storeFile"));
        if (!store.isAbsolute()) store = propertiesFile.getParent().resolve(store);
        store = store.toRealPath();
        Path signer = Path.of(args[1], "build-tools", "35.0.0", "lib", "apksigner.jar").toRealPath();
        String executable = System.getProperty("os.name").startsWith("Windows") ? "java.exe" : "java";
        String java = Path.of(System.getProperty("java.home"), "bin", executable).toString();
        for (String flavor : List.of("free", "freeAds", "supporter", "pro")) {
            Path input = Path.of(args[2], flavor, "release", "app-" + flavor + "-release-unsigned.apk")
                .toRealPath();
            Path output = Path.of(args[3], flavor, "release", "app-" + flavor + "-release.apk");
            if (Files.exists(output)) throw new IOException("Refusing to replace signed APK: " + output);
            Files.createDirectories(output.getParent());
            ProcessBuilder process = new ProcessBuilder(java, "-jar", signer.toString(), "sign",
                "--ks", store.toString(), "--ks-key-alias", required(properties, "keyAlias"),
                "--ks-pass", "env:QUASAR_STORE_PASS", "--key-pass", "env:QUASAR_KEY_PASS",
                "--out", output.toString(), input.toString());
            process.environment().put("QUASAR_STORE_PASS", required(properties, "storePassword"));
            process.environment().put("QUASAR_KEY_PASS", required(properties, "keyPassword"));
            if (process.inheritIO().start().waitFor() != 0) {
                throw new IOException("APK signing failed for " + flavor);
            }
            System.out.println("Signed " + output);
        }
    }

    private static String required(Properties properties, String key) {
        String value = properties.getProperty(key);
        if (value == null || value.isEmpty()) {
            throw new IllegalArgumentException("Missing signing property: " + key);
        }
        return value;
    }
}
