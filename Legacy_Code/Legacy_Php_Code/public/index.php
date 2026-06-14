<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/auth.php';
require_once __DIR__ . '/../src/contacts.php';

start_app_session();

$loginError = '';
$contactSuccess = false;
$contactErrors = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $form = $_POST['form'] ?? '';

    if ($form === 'login') {
        if (login_user((string)($_POST['email'] ?? ''), (string)($_POST['password'] ?? ''))) {
            header('Location: /dashboard.php');
            exit;
        }

        $loginError = 'The email or password did not match our demo client account.';
    }

    if ($form === 'contact') {
        $result = save_contact_message($_POST);
        $contactSuccess = $result['ok'];
        $contactErrors = $result['errors'];
    }
}

if (isset($_GET['login']) && $_GET['login'] === 'required') {
    $loginError = 'Please log in before opening the client dashboard.';
}
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BrightWave Agency Portal</title>
    <link rel="stylesheet" href="/assets/styles.css">
</head>
<body>
    <main class="shell">
        <section class="hero" aria-labelledby="page-title">
            <div class="hero-copy">
                <p class="eyebrow">BrightWave Marketing Agency</p>
                <h1 id="page-title">Client growth campaigns with sharp strategy and measurable execution.</h1>
                <p class="intro">We plan, launch, and optimize brand campaigns across paid media, content, lifecycle email, and conversion-focused landing pages.</p>
                <div class="metrics" aria-label="Agency highlights">
                    <span><strong>42%</strong> average qualified lead lift</span>
                    <span><strong>18</strong> active growth channels managed</span>
                    <span><strong>24h</strong> client response target</span>
                </div>
            </div>

            <form class="panel login-panel" method="post" action="/" aria-label="Client login">
                <input type="hidden" name="form" value="login">
                <div class="panel-heading">
                    <p class="eyebrow">Client Portal</p>
                    <h2>Log in</h2>
                </div>

                <?php if ($loginError !== ''): ?>
                    <p class="alert error"><?= htmlspecialchars($loginError) ?></p>
                <?php endif; ?>

                <label>
                    Email
                    <input type="email" name="email" value="client@brightwave.test" required>
                </label>

                <label>
                    Password
                    <input type="password" name="password" value="Launch2026!" required>
                </label>

                <button type="submit">Open dashboard</button>
                <p class="hint">Demo access: client@brightwave.test / Launch2026!</p>
            </form>
        </section>

        <section class="services" aria-label="Agency services">
            <article>
                <span>01</span>
                <h2>Growth Strategy</h2>
                <p>Audience research, positioning, channel planning, and campaign roadmaps.</p>
            </article>
            <article>
                <span>02</span>
                <h2>Paid Media</h2>
                <p>Search, social, retargeting, creative testing, and budget pacing.</p>
            </article>
            <article>
                <span>03</span>
                <h2>Content Systems</h2>
                <p>Landing pages, lead magnets, email flows, and editorial calendars.</p>
            </article>
            <article>
                <span>04</span>
                <h2>Analytics</h2>
                <p>Dashboards, attribution reviews, conversion reporting, and insight briefs.</p>
            </article>
        </section>

        <section class="contact-grid" aria-labelledby="contact-title">
            <div>
                <p class="eyebrow">Start a project</p>
                <h2 id="contact-title">Contact the agency</h2>
                <p>Share a campaign goal, product launch, or funnel problem. The team will review the brief and respond with next steps.</p>
                <dl class="contact-list">
                    <div>
                        <dt>Email</dt>
                        <dd>hello@brightwave.test</dd>
                    </div>
                    <div>
                        <dt>Phone</dt>
                        <dd>+1 555 014 8820</dd>
                    </div>
                    <div>
                        <dt>Office</dt>
                        <dd>Chicago, Remote-first</dd>
                    </div>
                </dl>
            </div>

            <form class="panel" method="post" action="/#contact-title">
                <input type="hidden" name="form" value="contact">

                <?php if ($contactSuccess): ?>
                    <p class="alert success">Thanks. Your message has been saved and the agency team will follow up.</p>
                <?php endif; ?>

                <?php foreach ($contactErrors as $error): ?>
                    <p class="alert error"><?= htmlspecialchars($error) ?></p>
                <?php endforeach; ?>

                <label>
                    Name
                    <input type="text" name="name" required>
                </label>

                <label>
                    Email
                    <input type="email" name="email" required>
                </label>

                <label>
                    Company
                    <input type="text" name="company">
                </label>

                <label>
                    Budget
                    <select name="budget">
                        <option value="">Select a range</option>
                        <option>$2k - $5k</option>
                        <option>$5k - $15k</option>
                        <option>$15k - $40k</option>
                        <option>$40k+</option>
                    </select>
                </label>

                <label>
                    Message
                    <textarea name="message" rows="5" required></textarea>
                </label>

                <button type="submit">Send inquiry</button>
            </form>
        </section>
    </main>
</body>
</html>

