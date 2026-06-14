<?php

declare(strict_types=1);

const DEMO_USER = [
    'email' => 'client@brightwave.test',
    'password' => 'Launch2026!',
    'name' => 'Avery Stone',
    'company' => 'Northstar Retail Group',
];

function start_app_session(): void
{
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }
}

function login_user(string $email, string $password): bool
{
    start_app_session();

    if (strtolower(trim($email)) !== DEMO_USER['email'] || $password !== DEMO_USER['password']) {
        return false;
    }

    $_SESSION['user'] = [
        'email' => DEMO_USER['email'],
        'name' => DEMO_USER['name'],
        'company' => DEMO_USER['company'],
    ];

    return true;
}

function current_user(): ?array
{
    start_app_session();
    return $_SESSION['user'] ?? null;
}

function require_login(): array
{
    $user = current_user();

    if ($user === null) {
        header('Location: /?login=required');
        exit;
    }

    return $user;
}

function logout_user(): void
{
    start_app_session();
    $_SESSION = [];

    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(
            session_name(),
            '',
            time() - 42000,
            $params['path'],
            $params['domain'],
            $params['secure'],
            $params['httponly']
        );
    }

    session_destroy();
}

