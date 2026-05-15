/*
 * Toy ProductionApp — minimal signup feature for the polyglot pilot.
 *
 * Composition root: constructs the in-memory registry and audit log, exposes
 * `signup` (driving operation) and `captureUniverse` (state inspection at
 * port-exposed slots). Real-feature shape: in-process domain + driven ports
 * (here both in-memory).
 *
 * Universe slots exposed:
 *   - "registry.users" : List<Map<String,Object>> with {"email": String}
 *   - "audit.events"   : List<Map<String,Object>> with {"type": String, "email": String}
 *
 * Internal field names are NOT part of the universe — refactoring internals
 * stays GREEN.
 */
package pilot;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class ProductionApp {

    /** Thrown when a signup is attempted with an email already in the registry. */
    public static final class DuplicateSignupException extends RuntimeException {
        private static final long serialVersionUID = 1L;
        public final String email;

        public DuplicateSignupException(String email) {
            super("Duplicate signup rejected: " + email);
            this.email = email;
        }
    }

    // Driven-port state (in-memory).
    private final List<Map<String, Object>> users = new ArrayList<>();
    private final List<Map<String, Object>> events = new ArrayList<>();

    public ProductionApp() {
        // Toy feature — nothing to wire.
    }

    /**
     * Driving port — signup a user by email. Rejects duplicates by throwing
     * {@link DuplicateSignupException}. On success: appends to registry AND
     * appends a single {@code UserSignedUp} audit event.
     */
    public Map<String, Object> signup(String rawEmail) {
        if (rawEmail == null) {
            throw new IllegalArgumentException("signup: email must be non-null");
        }
        String email = rawEmail.trim().toLowerCase();
        if (email.isEmpty()) {
            throw new IllegalArgumentException("signup: email must be non-empty");
        }
        for (Map<String, Object> u : users) {
            if (email.equals(u.get("email"))) {
                throw new DuplicateSignupException(email);
            }
        }
        Map<String, Object> record = new LinkedHashMap<>();
        record.put("email", email);
        users.add(record);

        Map<String, Object> event = new LinkedHashMap<>();
        event.put("type", "UserSignedUp");
        event.put("email", email);
        events.add(event);

        return new LinkedHashMap<>(record);
    }

    /**
     * State-inspection port — return a snapshot of the universe slots requested.
     * Snapshot returns deep-copied entries so test assertions cannot mutate
     * production state by accident.
     */
    public Map<String, Object> captureUniverse(Set<String> keys) {
        Map<String, Object> snapshot = new LinkedHashMap<>();
        for (String key : keys) {
            switch (key) {
                case "registry.users" -> snapshot.put(key, deepCopyList(users));
                case "audit.events" -> snapshot.put(key, deepCopyList(events));
                default -> snapshot.put(key, null);
            }
        }
        return snapshot;
    }

    private static List<Map<String, Object>> deepCopyList(List<Map<String, Object>> src) {
        List<Map<String, Object>> out = new ArrayList<>(src.size());
        for (Map<String, Object> item : src) {
            out.add(new LinkedHashMap<>(item));
        }
        return out;
    }
}
