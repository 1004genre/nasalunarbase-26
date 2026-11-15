# How the public copy of the page runs

The page in `site/` is static. A web server gives its files to the browser, and no other program is necessary.
The public copy runs in two containers on one server.

1. A web server (nginx) gives the files of `site/`. Its configuration is `nginx-site.conf` and `nginx-models.inc`.
2. A model service (Ollama) runs the two optional AI models of the page: Qwen2.5 7B and nomic-embed-text. It has no port of its own on the internet.

The public copy has a name and a certificate from Let's Encrypt, so the page runs on https. `nginx-common.inc` holds the rules that the http and the https part share.

The web server passes only three requests to the model service: `/ollama/api/tags`, `/ollama/api/embed` and `/ollama/api/chat`.
The page uses the models only to change the words of a researcher into options. All places and all figures come from the data.

Two small steps prepare a copy of the page for a server.

- `add_http_fallback.py` adds `secure-fallback.js` to the page. On an address that is not secure (http), a browser gives a page no SHA-256 function. The file supplies that function, thus the page can check that its data files belong together.
- `add_named_options.py` changes `site/ask.js`. It gives a name, a unit and a category to 15 data fields that had a file name only, for example the yield of a solar panel and the wind speed at 50 m. The copy of `site/ask.js` in this repository has this change.
- `use_server_models.py` changes `site/ask.js`. On localhost, the page asks for the models of that computer. On each other address, it asks the server of the page. The copy of `site/ask.js` in this repository has this change.

The commands, with `<folder>` for the folder that holds `site/` and the two configuration files:

    docker network create etf-net
    docker run -d --name etf-ollama --restart unless-stopped --network etf-net -v etf-ollama:/root/.ollama ollama/ollama
    docker exec etf-ollama ollama pull nomic-embed-text
    docker exec etf-ollama ollama pull qwen2.5:7b
    docker run -d --name lunimartian-atlas --restart unless-stopped --network etf-net -p 80:80 \
      -v <folder>/site:/usr/share/nginx/html:ro \
      -v <folder>/nginx-site.conf:/etc/nginx/conf.d/default.conf:ro \
      -v <folder>/nginx-models.inc:/etc/nginx/conf.d/models.inc:ro nginx

This text and these files were written with AI assistance (Claude, Anthropic).
