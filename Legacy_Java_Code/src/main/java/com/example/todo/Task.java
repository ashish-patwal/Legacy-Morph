package com.example.todo;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class Task {
    private static final DateTimeFormatter FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE_TIME;

    private final int id;
    private final String title;
    private boolean completed;
    private final LocalDateTime createdAt;

    public Task(int id, String title, boolean completed, LocalDateTime createdAt) {
        this.id = id;
        this.title = title;
        this.completed = completed;
        this.createdAt = createdAt;
    }

    public static Task create(int id, String title) {
        return new Task(id, title, false, LocalDateTime.now());
    }

    public static Task fromStorageLine(String line) {
        String[] parts = line.split("\\t", 4);
        if (parts.length != 4) {
            throw new IllegalArgumentException("Invalid task row: " + line);
        }

        int id = Integer.parseInt(parts[0]);
        boolean completed = Boolean.parseBoolean(parts[1]);
        LocalDateTime createdAt = LocalDateTime.parse(parts[2], FORMATTER);
        String title = unescape(parts[3]);
        return new Task(id, title, completed, createdAt);
    }

    public String toStorageLine() {
        return id + "\t" + completed + "\t" + createdAt.format(FORMATTER) + "\t" + escape(title);
    }

    public int getId() {
        return id;
    }

    public String getTitle() {
        return title;
    }

    public boolean isCompleted() {
        return completed;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void markCompleted() {
        completed = true;
    }

    private static String escape(String value) {
        return value
                .replace("\\", "\\\\")
                .replace("\t", "\\t")
                .replace("\r", "\\r")
                .replace("\n", "\\n");
    }

    private static String unescape(String value) {
        StringBuilder result = new StringBuilder();
        boolean escaping = false;

        for (char character : value.toCharArray()) {
            if (escaping) {
                switch (character) {
                    case 't':
                        result.append('\t');
                        break;
                    case 'r':
                        result.append('\r');
                        break;
                    case 'n':
                        result.append('\n');
                        break;
                    default:
                        result.append(character);
                        break;
                }
                escaping = false;
            } else if (character == '\\') {
                escaping = true;
            } else {
                result.append(character);
            }
        }

        if (escaping) {
            result.append('\\');
        }

        return result.toString();
    }
}

