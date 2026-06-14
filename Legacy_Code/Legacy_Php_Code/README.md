# Marketing Agency Login Page

This is a small PHP project for a marketing agency website with a client login page, contact form, service highlights, and a simple logged-in client dashboard.

It uses plain PHP, HTML, CSS, and a small JSON-lines file for saved contact messages. No database or external packages are required.

## Features

- Agency-branded login page.
- Demo client login.
- Contact form for new project inquiries.
- Services section for strategy, content, paid media, analytics, and brand campaigns.
- Client dashboard after login.
- Basic session-based authentication.
- Contact submissions saved locally in `storage/contacts.jsonl`.

## Project Structure

```text
marketing-agency-php/
  public/
    index.php         # Landing, login, and contact page
    dashboard.php     # Logged-in client dashboard
    logout.php        # Ends the session
    assets/
      styles.css      # Page styling
  src/
    auth.php          # Login/session helpers
    contacts.php      # Contact form validation and saving
  storage/
    .gitkeep          # Keeps the storage folder in the project
  README.md
  .gitignore
```

## How It Works

1. The visitor opens `public/index.php`.
2. The page shows agency information, a login form, and a contact form.
3. If the visitor submits the login form, `src/auth.php` checks the credentials.
4. If the credentials are correct, PHP stores the user in the session and redirects to `public/dashboard.php`.
5. The dashboard checks the session before showing client-only content.
6. If the visitor submits the contact form, `src/contacts.php` validates the input and appends the inquiry to `storage/contacts.jsonl`.
7. Clicking logout runs `public/logout.php`, clears the session, and returns the user to the login page.

## Demo Login

Use these credentials:

```text
Email: client@brightwave.test
Password: Launch2026!
```

## Requirements

- PHP 8.0 or newer.

Check your PHP installation:

```powershell
php -v
```

## Steps To Run

Open a terminal in the project folder:

```powershell
cd marketing-agency-php
```

Start PHP's built-in development server:

```powershell
php -S localhost:8000 -t public
```

Open this URL in your browser:

```text
http://localhost:8000
```

## How To Use

### Login

1. Go to `http://localhost:8000`.
2. Enter the demo email and password.
3. Submit the login form.
4. You will be redirected to the client dashboard.

### Contact The Agency

1. Go to `http://localhost:8000`.
2. Fill in the contact form with your name, email, company, budget, and message.
3. Submit the form.
4. The message is saved in `storage/contacts.jsonl`.

### Logout

1. From the dashboard, click `Log out`.
2. The session is cleared.
3. You return to the public login page.

## Notes

This project is made for learning and local demos. For a real production website, replace the demo login with database-backed users, hash passwords with `password_hash`, add CSRF protection, send contact messages by email or CRM integration, and use HTTPS.

