package com.example.todo;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;

public class TodoList {
    private final List<Task> tasks;
    private int nextId;

    public TodoList(List<Task> savedTasks) {
        tasks = new ArrayList<>(savedTasks);
        nextId = tasks.stream()
                .map(Task::getId)
                .max(Comparator.naturalOrder())
                .orElse(0) + 1;
    }

    public Task add(String title) {
        Task task = Task.create(nextId, title);
        nextId++;
        tasks.add(task);
        return task;
    }

    public List<Task> all() {
        return List.copyOf(tasks);
    }

    public Optional<Task> findById(int id) {
        return tasks.stream()
                .filter(task -> task.getId() == id)
                .findFirst();
    }

    public boolean complete(int id) {
        Optional<Task> task = findById(id);
        task.ifPresent(Task::markCompleted);
        return task.isPresent();
    }

    public boolean delete(int id) {
        return tasks.removeIf(task -> task.getId() == id);
    }
}

