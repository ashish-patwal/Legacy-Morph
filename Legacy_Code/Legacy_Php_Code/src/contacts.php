<?php

declare(strict_types=1);

function save_contact_message(array $input): array
{
    $name = trim((string)($input['name'] ?? ''));
    $email = trim((string)($input['email'] ?? ''));
    $company = trim((string)($input['company'] ?? ''));
    $budget = trim((string)($input['budget'] ?? ''));
    $message = trim((string)($input['message'] ?? ''));

    $errors = [];

    if ($name === '') {
        $errors[] = 'Please enter your name.';
    }

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        $errors[] = 'Please enter a valid email address.';
    }

    if ($message === '') {
        $errors[] = 'Please tell us what you want to build.';
    }

    if ($errors !== []) {
        return ['ok' => false, 'errors' => $errors];
    }

    $record = [
        'name' => $name,
        'email' => $email,
        'company' => $company,
        'budget' => $budget,
        'message' => $message,
        'created_at' => date(DATE_ATOM),
    ];

    $storageDirectory = dirname(__DIR__) . DIRECTORY_SEPARATOR . 'storage';
    if (!is_dir($storageDirectory)) {
        mkdir($storageDirectory, 0775, true);
    }

    $file = $storageDirectory . DIRECTORY_SEPARATOR . 'contacts.jsonl';
    file_put_contents($file, json_encode($record, JSON_UNESCAPED_SLASHES) . PHP_EOL, FILE_APPEND | LOCK_EX);

    return ['ok' => true, 'errors' => []];
}

