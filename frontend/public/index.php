<?php

require_once __DIR__ . '/../templates/layout.php';

render_layout([
    'title' => 'Realtime Voice Chat',
    'content' => __DIR__ . '/../templates/chat.php',
]);

