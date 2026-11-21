import java.io.IOException;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

public class Kiosk {
    record Session(String id, String version, Set<String> zones) {
        Session {
            zones = Collections.unmodifiableSet(new LinkedHashSet<>(zones));
        }

        static Session load(Path registry, String id) throws IOException {
            Set<String> zones = new LinkedHashSet<>();
            String version = null;
            for (String[] row : read(registry, "session\tversion\tzone")) {
                if (!id.equals(row[0])) continue;
                if (version != null && !version.equals(row[1]))
                    throw new IllegalArgumentException("ambiguous_version");
                version = row[1];
                if (!zones.add(row[2])) throw new IllegalArgumentException("duplicate_zone");
            }
            if (zones.isEmpty()) throw new IllegalArgumentException("unknown_session");
            return new Session(id, version, zones);
        }
    }

    record Touch(String session, String version, String time, String zone) {}
    record Rejection(int row, String reason) {}

    static class SessionSummary {
        private final Session session;
        private final Map<String, Integer> counts = new LinkedHashMap<>();
        private final Map<String, BigInteger> last = new HashMap<>();
        private final List<Rejection> rejected = new ArrayList<>();
        private BigInteger previous = BigInteger.valueOf(-1);
        private int number;

        SessionSummary(Session session) {
            this.session = session;
            for (String zone : session.zones()) counts.put(zone, 0);
        }

        void accept(Touch touch) {
            if (!session.id().equals(touch.session()) || !session.version().equals(touch.version()))
                throw new IllegalArgumentException("binding");
            number++;
            BigInteger at;
            try {
                at = new BigInteger(touch.time().trim());
            } catch (NumberFormatException ex) {
                rejected.add(new Rejection(number, "time"));
                return;
            }
            if (at.signum() < 0 || at.compareTo(previous) < 0) {
                rejected.add(new Rejection(number, "time"));
                return;
            }
            previous = at;
            String zone = touch.zone();
            if (!counts.containsKey(zone)) {
                rejected.add(new Rejection(number, "unknown"));
            } else if (last.containsKey(zone) &&
                    at.subtract(last.get(zone)).compareTo(BigInteger.valueOf(250)) < 0) {
                rejected.add(new Rejection(number, "repeat"));
            } else {
                last.put(zone, at);
                counts.merge(zone, 1, Integer::sum);
            }
        }

        void print() {
            System.out.println(session.id() + "/" + session.version() + " " + counts);
            System.out.println(rejected);
        }
    }

    static List<String[]> read(Path file, String header) throws IOException {
        List<String> lines = Files.readAllLines(file);
        if (lines.isEmpty() || !header.equals(lines.get(0)))
            throw new IllegalArgumentException("header");
        int width = header.split("\t").length;
        List<String[]> rows = new ArrayList<>();
        for (String line : lines.subList(1, lines.size())) {
            String[] row = line.split("\t", -1);
            if (row.length != width) throw new IllegalArgumentException("columns");
            rows.add(row);
        }
        return rows;
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 3) throw new IllegalArgumentException("registry.tsv events.tsv session");
        SessionSummary summary = new SessionSummary(Session.load(Path.of(args[0]), args[2]));
        for (String[] row : read(Path.of(args[1]), "session\tversion\ttime_ms\tzone"))
            summary.accept(new Touch(row[0], row[1], row[2], row[3]));
        summary.print();
    }
}
