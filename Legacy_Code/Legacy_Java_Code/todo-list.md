# Java To-Do List Project

This is a small command-line Java project for managing a personal to-do list. It uses only the Java standard library, so no Maven, Gradle, or external packages are required.

## What It Can Do

- List all saved tasks.
- Add a new task.
- Mark a task as completed.
- Delete a task.
- Save tasks between runs in `data/tasks.tsv`.

## Project Structure

```text
todo-list-java/
  src/main/java/com/example/todo/
    Main.java       # Starts the app and handles the menu
    Task.java       # Represents one to-do item
    TodoList.java   # Holds task operations like add, complete, and delete
    TaskStore.java  # Loads and saves tasks from disk
  HOW_IT_WORKS.md
  .gitignore
```

## How It Works

1. `Main.java` starts the program and creates a `TaskStore` that points to `data/tasks.tsv`.
2. `TaskStore` loads any existing saved tasks. If the file does not exist yet, the app starts with an empty list.
3. `TodoList` keeps the tasks in memory while the app is running.
4. The menu lets the user choose actions by entering numbers from `1` to `5`.
5. Whenever a task is added, completed, or deleted, `TaskStore` saves the updated list back to `data/tasks.tsv`.
6. Each task has an ID, title, completion status, and creation timestamp.

## Requirements

- Java Development Kit, JDK 17 or newer recommended.

Check your Java installation:

```powershell
java -version
javac -version
```

## Steps To Run

From the `todo-list-java` folder, compile the project:

```powershell
javac -d out src/main/java/com/example/todo/*.java
```

Then run it:

```powershell
java -cp out com.example.todo.Main
```

## How To Use

When the program starts, it shows this menu:

```text
=== To-Do List ===
1. List tasks
2. Add task
3. Complete task
4. Delete task
5. Exit
Choose an option:
```

### Add A Task

Choose `2`, then type the task title.

Example:

```text
Choose an option: 2
Task title: Finish Java assignment
Added task #1.
```

### List Tasks

Choose `1` to see all tasks.

Example:

```text
[ ] #1 Finish Java assignment (created 2026-06-14 10:30)
```

Completed tasks show `[x]`; incomplete tasks show `[ ]`.

### Complete A Task

Choose `3`, then enter the task ID.

Example:

```text
Choose an option: 3
Task ID to complete: 1
Completed task #1.
```

### Delete A Task

Choose `4`, then enter the task ID.

Example:

```text
Choose an option: 4
Task ID to delete: 1
Deleted task #1.
```

### Exit

Choose `5` to close the program.

## Saved Data

Tasks are saved in:

```text
data/tasks.tsv
```

That file is created automatically after the first change. It is ignored by Git because it is local user data.

