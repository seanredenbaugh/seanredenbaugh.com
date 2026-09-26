<?php
// Contact form handler for seanredenbaugh.com (runs on Hostinger's PHP).
// Sends the message to Sean's inbox, then sends the visitor back to /contact/.

$TO   = 'seanredenbaugh@yahoo.com';
// Must be an address at this domain, or Yahoo will reject the message.
// Create it in Hostinger (Emails) if you like, but mail() works without a mailbox too.
$FROM = 'website@seanredenbaugh.com';

function back($ok) {
    header('Location: /contact/?sent=' . ($ok ? '1' : '0') . '#main', true, 303);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') back(false);

$name    = trim($_POST['name'] ?? '');
$email   = trim($_POST['email'] ?? '');
$subject = trim($_POST['subject'] ?? '');
$message = trim($_POST['message'] ?? '');
$honey   = trim($_POST['website'] ?? '');
$t       = (int) ($_POST['t'] ?? 0);

// Spam checks: hidden field must be empty, and the form must have been open for a few seconds.
$ageMs = (int) (microtime(true) * 1000) - $t;
if ($honey !== '' || $t === 0 || $ageMs < 3000) back(true); // pretend success to bots

if ($name === '' || $message === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) back(false);
if (strlen($name) > 120 || strlen($email) > 200 || strlen($subject) > 200 || strlen($message) > 5000) back(false);

// Stop header injection
$clean = function ($s) { return str_replace(["\r", "\n", "%0a", "%0d"], ' ', $s); };
$name = $clean($name);
$email = $clean($email);
$subject = $clean($subject);

$mailSubject = 'Website message: ' . ($subject !== '' ? $subject : 'from ' . $name);
$body  = "Name: $name\nEmail: $email\n";
if ($subject !== '') $body .= "Subject: $subject\n";
$body .= "\n$message\n\n--\nSent from the contact form on seanredenbaugh.com\nIP: " . ($_SERVER['REMOTE_ADDR'] ?? '') . "\n";

$headers  = "From: Sean Redenbaugh website <$FROM>\r\n";
$headers .= "Reply-To: $name <$email>\r\n";
$headers .= "Content-Type: text/plain; charset=UTF-8\r\n";

$ok = mail($TO, '=?UTF-8?B?' . base64_encode($mailSubject) . '?=', $body, $headers, '-f' . $FROM);
back($ok);
