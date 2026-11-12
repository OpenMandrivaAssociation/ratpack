Name:		ratpack
Version:	1.9.0
Release:	1
Summary:	Ratpack base, exec, and core libraries
Group:		Development/Java
License:	Apache-2.0
URL:		https://ratpack.io/
# Tag v1.9.0, commit d62e05d331577684670e793d9273bb3ddb4c7f6e.
# Only ratpack-base, ratpack-exec, and ratpack-core are built. The JRuby
# resolver starts RatpackServer from the core jar.
Source0:	ratpack-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	mvn(com.google.guava:guava)
BuildRequires:	mvn(org.slf4j:slf4j-api)
BuildRequires:	mvn(org.reactivestreams:reactive-streams)
BuildRequires:	mvn(org.jctools:jctools-core)
BuildRequires:	mvn(io.netty:netty-buffer)
BuildRequires:	mvn(io.netty:netty-codec)
BuildRequires:	mvn(io.netty:netty-codec-dns)
BuildRequires:	mvn(io.netty:netty-codec-http)
BuildRequires:	mvn(io.netty:netty-codec-socks)
BuildRequires:	mvn(io.netty:netty-common)
BuildRequires:	mvn(io.netty:netty-handler)
BuildRequires:	mvn(io.netty:netty-handler-proxy)
BuildRequires:	mvn(io.netty:netty-resolver)
BuildRequires:	mvn(io.netty:netty-resolver-dns)
BuildRequires:	mvn(io.netty:netty-transport)
BuildRequires:	mvn(io.netty:netty-transport-native-unix-common)
BuildRequires:	mvn(com.fasterxml.jackson.core:jackson-annotations)
BuildRequires:	mvn(com.fasterxml.jackson.core:jackson-core)
BuildRequires:	mvn(com.fasterxml.jackson.core:jackson-databind)
BuildRequires:	mvn(com.fasterxml.jackson.dataformat:jackson-dataformat-yaml)
BuildRequires:	mvn(com.fasterxml.jackson.datatype:jackson-datatype-guava)
BuildRequires:	mvn(com.fasterxml.jackson.datatype:jackson-datatype-jdk8)
BuildRequires:	mvn(com.fasterxml.jackson.datatype:jackson-datatype-jsr310)
BuildRequires:	mvn(com.github.ben-manes.caffeine:caffeine)
BuildRequires:	mvn(org.javassist:javassist)
BuildRequires:	mvn(com.sun.activation:javax.activation)
BuildRequires:	mvn(org.yaml:snakeyaml)

%description
io.ratpack %{version} base, exec, and core. Core starts an embedded server
and builds its config ObjectMapper with GuavaModule.

%prep
%autosetup -n ratpack-%{version} -p1
set -eo pipefail
python3 - << 'PY'
import os
bad = []
for dirpath, dirs, files in os.walk("."):
    for d in dirs:
        if d.endswith(".jar"):
            bad.append(os.path.join(dirpath, d))
    for fn in files:
        path = os.path.join(dirpath, fn)
        if fn.endswith((".jar", ".class", ".so", ".node", ".wasm", ".dll", ".a", ".o")):
            bad.append(path)
            continue
        try:
            with open(path, "rb") as fh:
                mag = fh.read(4)
        except OSError:
            continue
        if mag in (b"\x7fELF", b"\xca\xfe\xba\xbe"):
            bad.append(path)
if bad:
    print("\n".join(bad))
    raise SystemExit(1)
PY
test -s ratpack-base/src/main/java/ratpack/api/Nullable.java
test -s ratpack-exec/src/main/java/ratpack/exec/Promise.java
test -s ratpack-core/src/main/java/ratpack/server/RatpackServer.java
test -s ratpack-core/src/main/java/ratpack/config/internal/DefaultConfigDataBuilder.java

%build
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
test -s %{_javadir}/netty-buffer.jar
netty_cp=%{_javadir}/netty-buffer.jar
for j in netty-codec netty-codec-dns netty-codec-http netty-codec-socks netty-common netty-handler netty-handler-proxy netty-resolver netty-resolver-dns netty-transport netty-transport-native-unix-common; do
	test -s "%{_javadir}/${j}.jar"
	netty_cp="$netty_cp:%{_javadir}/${j}.jar"
done
base_cp=%{_javadir}/guava.jar:%{_javadir}/slf4j-api.jar
exec_cp="$base_cp:%{_javadir}/reactive-streams.jar:$netty_cp:ratpack-base-classes"
core_cp="$exec_cp:ratpack-exec-classes:%{_javadir}/caffeine.jar:%{_javadir}/javassist.jar:%{_javadir}/javax.activation.jar:%{_javadir}/jackson-annotations.jar:%{_javadir}/jackson-core.jar:%{_javadir}/jackson-databind.jar:%{_javadir}/jackson-dataformat-yaml.jar:%{_javadir}/jackson-datatype-guava.jar:%{_javadir}/jackson-datatype-jdk8.jar:%{_javadir}/jackson-datatype-jsr310.jar:%{_javadir}/snakeyaml.jar"

compile_one() {
	mod=$1
	nsrc=$2
	ncls=$3
	cp=$4
	find "$mod/src/main/java" -name '*.java' > "$mod.srcs"
	test "$(wc -l < "$mod.srcs")" -eq "$nsrc"
	mkdir -p "$mod-classes"
	javac --release 8 -encoding UTF-8 -Xlint:-options -cp "$cp" -d "$mod-classes" @"$mod.srcs"
	test "$(find "$mod-classes" -name '*.class' | wc -l)" -eq "$ncls"
}
compile_one ratpack-base 16 15 "$base_cp"
compile_one ratpack-exec 124 235 "$exec_cp"
compile_one ratpack-core 325 422 "$core_cp"
/bin/cp -a ratpack-core/src/main/resources/. ratpack-core-classes/
# Groovy ExtensionModule is not a Java service. jar --describe-module rejects it.
# ratpack-groovy is not part of this package.
/bin/rm -rf ratpack-core-classes/META-INF/services

jar_one() {
	mod=$1
	module=$2
	printf '%%s\n' 'Manifest-Version: 1.0' "Automatic-Module-Name: $module" "Implementation-Version: %{version}" > "$mod.mf"
	jar cfm "$mod.jar" "$mod.mf" -C "$mod-classes" .
	jar i "$mod.jar"
	if jar tf "$mod.jar" | grep -E '\.(java|jar|so|node|wasm)$'; then
		exit 1
	fi
	desc=$(jar --describe-module --file "$mod.jar")
	printf '%%s\n' "$desc"
	printf '%%s\n' "$desc" | grep -F -qx "$module automatic"
	if printf '%%s\n' "$desc" | grep -F -q Unable; then
		exit 1
	fi
}
jar_one ratpack-base ratpack.base
jar_one ratpack-exec ratpack.exec
jar_one ratpack-core ratpack.core
javap -v -classpath ratpack-base-classes ratpack.api.Nullable | grep -F -q 'major version: 52'
javap -v -classpath ratpack-exec-classes ratpack.exec.Promise | grep -F -q 'major version: 52'
javap -v -classpath ratpack-core-classes ratpack.server.RatpackServer | grep -F -q 'major version: 52'

cat > ratpack-base.pom << 'END'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>io.ratpack</groupId>
  <artifactId>ratpack-base</artifactId>
  <version>%{version}</version>
  <name>ratpack-base</name>
  <description>Ratpack base utilities.</description>
  <url>https://ratpack.io/</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>com.google.guava</groupId>
      <artifactId>guava</artifactId>
      <version>33.6.0-jre</version>
    </dependency>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.17</version>
    </dependency>
  </dependencies>
</project>
END

cat > ratpack-exec.pom << 'END'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>io.ratpack</groupId>
  <artifactId>ratpack-exec</artifactId>
  <version>%{version}</version>
  <name>ratpack-exec</name>
  <description>Ratpack execution model.</description>
  <url>https://ratpack.io/</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>io.ratpack</groupId>
      <artifactId>ratpack-base</artifactId>
      <version>%{version}</version>
    </dependency>
    <dependency>
      <groupId>org.reactivestreams</groupId>
      <artifactId>reactive-streams</artifactId>
      <version>1.0.2</version>
    </dependency>
    <dependency>
      <groupId>com.google.guava</groupId>
      <artifactId>guava</artifactId>
      <version>33.6.0-jre</version>
    </dependency>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.17</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-common</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-buffer</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-transport</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
  </dependencies>
</project>
END

cat > ratpack-core.pom << 'END'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>io.ratpack</groupId>
  <artifactId>ratpack-core</artifactId>
  <version>%{version}</version>
  <name>ratpack-core</name>
  <description>Ratpack core server.</description>
  <url>https://ratpack.io/</url>
  <licenses>
    <license>
      <name>Apache-2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>io.ratpack</groupId>
      <artifactId>ratpack-base</artifactId>
      <version>%{version}</version>
    </dependency>
    <dependency>
      <groupId>io.ratpack</groupId>
      <artifactId>ratpack-exec</artifactId>
      <version>%{version}</version>
    </dependency>
    <dependency>
      <groupId>org.reactivestreams</groupId>
      <artifactId>reactive-streams</artifactId>
      <version>1.0.2</version>
    </dependency>
    <dependency>
      <groupId>com.google.guava</groupId>
      <artifactId>guava</artifactId>
      <version>33.6.0-jre</version>
    </dependency>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.17</version>
    </dependency>
    <dependency>
      <groupId>com.github.ben-manes.caffeine</groupId>
      <artifactId>caffeine</artifactId>
      <version>3.0.5</version>
    </dependency>
    <dependency>
      <groupId>org.javassist</groupId>
      <artifactId>javassist</artifactId>
      <version>3.33.0-GA</version>
    </dependency>
    <dependency>
      <groupId>com.sun.activation</groupId>
      <artifactId>javax.activation</artifactId>
      <version>1.2.0</version>
    </dependency>
    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-databind</artifactId>
      <version>2.23.0</version>
    </dependency>
    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-core</artifactId>
      <version>2.23.0</version>
    </dependency>
    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-annotations</artifactId>
      <version>2.23</version>
    </dependency>
    <dependency>
      <groupId>com.fasterxml.jackson.dataformat</groupId>
      <artifactId>jackson-dataformat-yaml</artifactId>
      <version>2.23.0</version>
    </dependency>
    <dependency>
      <groupId>com.fasterxml.jackson.datatype</groupId>
      <artifactId>jackson-datatype-guava</artifactId>
      <version>2.23.0</version>
    </dependency>
    <dependency>
      <groupId>com.fasterxml.jackson.datatype</groupId>
      <artifactId>jackson-datatype-jdk8</artifactId>
      <version>2.22.3</version>
    </dependency>
    <dependency>
      <groupId>com.fasterxml.jackson.datatype</groupId>
      <artifactId>jackson-datatype-jsr310</artifactId>
      <version>2.22.3</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-common</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-buffer</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-transport</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-transport-native-unix-common</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-resolver</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-resolver-dns</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-codec</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-codec-http</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-codec-socks</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-codec-dns</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-handler</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
    <dependency>
      <groupId>io.netty</groupId>
      <artifactId>netty-handler-proxy</artifactId>
      <version>4.1.139.Final</version>
    </dependency>
  </dependencies>
</project>
END

%install
set -eo pipefail
sysjar install --buildroot %{buildroot} \
	--artifact ratpack-base.pom:ratpack-base.jar \
	--file-name ratpack-base \
	--filelist .mfiles-base
sysjar install --buildroot %{buildroot} \
	--artifact ratpack-exec.pom:ratpack-exec.jar \
	--file-name ratpack-exec \
	--filelist .mfiles-exec
sysjar install --buildroot %{buildroot} \
	--artifact ratpack-core.pom:ratpack-core.jar \
	--file-name ratpack-core \
	--filelist .mfiles-core
awk '!seen[$0]++' .mfiles-base .mfiles-exec .mfiles-core > .mfiles
for art in ratpack-base ratpack-exec ratpack-core; do
	idx="%{buildroot}/usr/share/sysjar/index/io.ratpack/${art}.sysjar"
	test -s "$idx"
	grep -F -q '"version": "%{version}"' "$idx"
	grep -F -q "\"artifactId\": \"$art\"" "$idx"
	test -s "%{buildroot}%{_javadir}/${art}.jar"
done

%check
set -eo pipefail
export JAVA_HOME=%{_jvmdir}/java-openjdk
export PATH="$JAVA_HOME/bin:/usr/bin:/bin"
BASE=%{buildroot}%{_javadir}/ratpack-base.jar
EXEC=%{buildroot}%{_javadir}/ratpack-exec.jar
CORE=%{buildroot}%{_javadir}/ratpack-core.jar
test -s "$BASE"
test -s "$EXEC"
test -s "$CORE"
test -s %{_javadir}/netty-buffer.jar
netty_cp=%{_javadir}/netty-buffer.jar
for j in netty-codec netty-codec-dns netty-codec-http netty-codec-socks netty-common netty-handler netty-handler-proxy netty-resolver netty-resolver-dns netty-transport netty-transport-native-unix-common; do
	test -s "%{_javadir}/${j}.jar"
	netty_cp="$netty_cp:%{_javadir}/${j}.jar"
done
mkdir -p check
cat > check/RatpackCheck.java << 'END'
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.collect.ImmutableList;
import ratpack.config.ConfigData;
import ratpack.config.ConfigDataBuilder;
import ratpack.server.RatpackServer;
import ratpack.server.ServerConfig;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class RatpackCheck {
    public static void main(String[] args) throws Exception {
        ConfigDataBuilder builder = ConfigData.builder();
        ObjectMapper mapper = builder.getObjectMapper();
        String json = mapper.writeValueAsString(ImmutableList.of("ok"));
        if (!"[\"ok\"]".equals(json)) {
            throw new RuntimeException(json);
        }
        RatpackServer server = RatpackServer.of(spec -> spec
            .serverConfig(ServerConfig.embedded())
            .handlers(chain -> chain.get(ctx -> ctx.getResponse().send("ratpack_ok"))));
        server.start();
        try {
            int port = server.getBindPort();
            if (port <= 0) {
                throw new RuntimeException("port " + port);
            }
            HttpURLConnection conn = (HttpURLConnection) new URL("http://127.0.0.1:" + port + "/").openConnection();
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(5000);
            int code = conn.getResponseCode();
            InputStream in = conn.getInputStream();
            byte[] buf = new byte[64];
            int n = in.read(buf);
            if (n < 0) {
                throw new RuntimeException("empty");
            }
            String text = new String(buf, 0, n, StandardCharsets.UTF_8);
            if (code != 200 || !"ratpack_ok".equals(text)) {
                throw new RuntimeException(code + " " + text);
            }
            System.out.println("ratpack_ok GET " + text + " " + json);
        } finally {
            server.stop();
        }
    }
}
END
CP="$BASE:$EXEC:$CORE:%{_javadir}/reactive-streams.jar:%{_javadir}/jackson-datatype-guava.jar:%{_javadir}/jackson-datatype-jdk8.jar:%{_javadir}/jackson-datatype-jsr310.jar:%{_javadir}/guava.jar:%{_javadir}/slf4j-api.jar:%{_javadir}/caffeine.jar:%{_javadir}/javassist.jar:%{_javadir}/javax.activation.jar:%{_javadir}/jackson-annotations.jar:%{_javadir}/jackson-core.jar:%{_javadir}/jackson-databind.jar:%{_javadir}/jackson-dataformat-yaml.jar:%{_javadir}/snakeyaml.jar:%{_javadir}/jctools-core.jar:$netty_cp"
javac --release 8 -encoding UTF-8 -Xlint:-options -cp "$CP" -d check check/RatpackCheck.java
java -cp "check:$CP" RatpackCheck > check/out.txt
cat check/out.txt
grep -F -qx 'ratpack_ok GET ratpack_ok ["ok"]' check/out.txt

%files -f .mfiles
%license LICENSE.txt
%doc README.md
