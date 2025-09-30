<?php

function render_layout(array $options): void
{
    $title = $options['title'] ?? 'Realtime Voice Chat';
    $contentTemplate = $options['content'] ?? null;
    ?><!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title><?= htmlspecialchars($title) ?></title>
        <link rel="stylesheet" href="/static/css/styles.css">
    </head>
    <body>
        <div id="app" class="app">
            <?php if ($contentTemplate && file_exists($contentTemplate)) {
                include $contentTemplate;
            } ?>
        </div>
        <script type="module" src="/static/js/app.js"></script>
    </body>
    </html><?php
}

