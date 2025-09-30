<?php

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?? '/';
$publicRoot = __DIR__;
$staticRoot = realpath(__DIR__ . '/../static');

if ($uri !== '/' && file_exists($publicRoot . $uri) && !is_dir($publicRoot . $uri)) {
    return false; // Let PHP built-in server serve the file directly
}

if (str_starts_with($uri, '/static/') && $staticRoot !== false) {
    $relativePath = substr($uri, strlen('/static/'));
    $filePath = $staticRoot . DIRECTORY_SEPARATOR . $relativePath;
    if (file_exists($filePath) && is_file($filePath)) {
        $mimeTypes = [
            'css' => 'text/css',
            'js' => 'application/javascript',
            'json' => 'application/json',
            'png' => 'image/png',
            'jpg' => 'image/jpeg',
            'jpeg' => 'image/jpeg',
            'gif' => 'image/gif',
            'svg' => 'image/svg+xml',
            'webp' => 'image/webp',
        ];
        $ext = strtolower(pathinfo($filePath, PATHINFO_EXTENSION));
        if (isset($mimeTypes[$ext])) {
            header('Content-Type: ' . $mimeTypes[$ext]);
        }
        readfile($filePath);
        return true;
    }
}

require $publicRoot . '/index.php';
