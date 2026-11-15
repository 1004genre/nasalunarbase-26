limit_req zone=ai burst=60 nodelay;
proxy_http_version 1.1;
proxy_set_header Host "localhost:11434";
proxy_set_header Origin "";
proxy_set_header Connection "";
proxy_read_timeout 180s;
proxy_send_timeout 60s;
proxy_buffering off;
add_header Cache-Control "no-store" always;
