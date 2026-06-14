<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/auth.php';

$user = require_login();
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BrightWave Client Dashboard</title>
    <link rel="stylesheet" href="/assets/styles.css">
</head>
<body>
    <main class="dashboard">
        <nav class="topbar">
            <div>
                <p class="eyebrow">BrightWave Client Portal</p>
                <h1><?= htmlspecialchars($user['company']) ?></h1>
            </div>
            <a class="logout" href="/logout.php">Log out</a>
        </nav>

        <section class="dashboard-grid">
            <article class="panel">
                <p class="eyebrow">Campaign Status</p>
                <h2>Launch sprint active</h2>
                <p>Your acquisition campaign is in creative testing. The next optimization review is scheduled after the first full week of conversion data.</p>
            </article>

            <article class="panel">
                <p class="eyebrow">Lead Volume</p>
                <h2>318 leads</h2>
                <p>Month-to-date qualified leads across paid search, paid social, landing pages, and lifecycle email.</p>
            </article>

            <article class="panel">
                <p class="eyebrow">Next Actions</p>
                <ul class="action-list">
                    <li>Approve revised landing page headline set.</li>
                    <li>Review the Q3 audience expansion proposal.</li>
                    <li>Upload final product photography for retargeting ads.</li>
                </ul>
            </article>
        </section>
    </main>
</body>
</html>

