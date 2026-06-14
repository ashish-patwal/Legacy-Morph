package com.example.todo;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class TaskStore {
    private final Path file;

    public TaskStore(Path file) {
        this.file = file;
    }

    public List<Task> load() throws IOException {
        if (!Files.exists(file)) {
            return List.of();
        }

        List<Task> tasks = new ArrayList<>();
        for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
            if (!line.isBlank()) {
                tasks.add(Task.fromStorageLine(line));
            }
        }
        return tasks;
    }

    public void save(List<Task> tasks) throws IOException {
        Path parent = file.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }

        List<String> lines = tasks.stream()
                .map(Task::toStorageLine)
                .toList();
        Files.write(file, lines, StandardCharsets.UTF_8);
    }
}

