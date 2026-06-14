package com.example.todo;

import java.io.IOException;
import java.nio.file.Path;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Scanner;

public class Main {
    private static final DateTimeFormatter DISPLAY_DATE = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    public static void main(String[] args) {
        TaskStore store = new TaskStore(Path.of("data", "tasks.tsv"));

        try {
            TodoList todoList = new TodoList(store.load());
            runMenu(todoList, store);
        } catch (IOException exception) {
            System.out.println("Could not read or save tasks: " + exception.getMessage());
        }
    }

    private static void runMenu(TodoList todoList, TaskStore store) throws IOException {
        Scanner scanner = new Scanner(System.in);
        boolean running = true;

        while (running) {
            printMenu();
            String choice = scanner.nextLine().trim();

            switch (choice) {
                case "1":
                    listTasks(todoList.all());
                    break;
                case "2":
                    addTask(scanner, todoList, store);
                    break;
                case "3":
                    completeTask(scanner, todoList, store);
                    break;
                case "4":
                    deleteTask(scanner, todoList, store);
                    break;
                case "5":
                    running = false;
                    System.out.println("Goodbye!");
                    break;
                default:
                    System.out.println("Please choose an option from 1 to 5.");
                    break;
            }
        }
    }

    private static void printMenu() {
        System.out.println();
        System.out.println("=== To-Do List ===");
        System.out.println("1. List tasks");
        System.out.println("2. Add task");
        System.out.println("3. Complete task");
        System.out.println("4. Delete task");
        System.out.println("5. Exit");
        System.out.print("Choose an option: ");
    }

    private static void listTasks(List<Task> tasks) {
        if (tasks.isEmpty()) {
            System.out.println("No tasks yet.");
            return;
        }

        System.out.println();
        for (Task task : tasks) {
            String status = task.isCompleted() ? "[x]" : "[ ]";
            System.out.printf(
                    "%s #%d %s (created %s)%n",
                    status,
                    task.getId(),
                    task.getTitle(),
                    task.getCreatedAt().format(DISPLAY_DATE)
            );
        }
    }

    private static void addTask(Scanner scanner, TodoList todoList, TaskStore store) throws IOException {
        System.out.print("Task title: ");
        String title = scanner.nextLine().trim();

        if (title.isEmpty()) {
            System.out.println("Task title cannot be empty.");
            return;
        }

        Task task = todoList.add(title);
        store.save(todoList.all());
        System.out.println("Added task #" + task.getId() + ".");
    }

    private static void completeTask(Scanner scanner, TodoList todoList, TaskStore store) throws IOException {
        Integer id = readTaskId(scanner, "Task ID to complete: ");
        if (id == null) {
            return;
        }

        if (todoList.complete(id)) {
            store.save(todoList.all());
            System.out.println("Completed task #" + id + ".");
        } else {
            System.out.println("No task found with ID #" + id + ".");
        }
    }

    private static void deleteTask(Scanner scanner, TodoList todoList, TaskStore store) throws IOException {
        Integer id = readTaskId(scanner, "Task ID to delete: ");
        if (id == null) {
            return;
        }

        if (todoList.delete(id)) {
            store.save(todoList.all());
            System.out.println("Deleted task #" + id + ".");
        } else {
            System.out.println("No task found with ID #" + id + ".");
        }
    }

    private static Integer readTaskId(Scanner scanner, String prompt) {
        System.out.print(prompt);
        String input = scanner.nextLine().trim();

        try {
            return Integer.parseInt(input);
        } catch (NumberFormatException exception) {
            System.out.println("Please enter a valid numeric task ID.");
            return null;
        }
    }
}

