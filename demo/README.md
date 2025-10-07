# Demo Generation

Generate animated GIF demos of lazy-ecs using asciinema recordings.

## Generate GIF

```bash
# Download and extract Noto Emoji fonts (full font directory needed for emoji support)
curl -L https://github.com/googlefonts/noto-emoji/archive/refs/tags/v2.047.tar.gz -o /tmp/noto-emoji.tar.gz
tar -xzf /tmp/noto-emoji.tar.gz -C /tmp

# Generate GIF with Docker (mount /tmp which contains the extracted fonts)
docker run --rm -v $PWD:/data -v /tmp:/fonts \
  ghcr.io/asciinema/agg:latest \
  --font-dir /fonts \
  --font-size 13 \
  --theme dracula \
  /data/demo/lazy-ecs-demo.cast /data/demo/lazy-ecs-demo.gif
```

## Record New Demo

```bash
# Install asciinema
brew install asciinema

# Record session
asciinema rec demo.cast

# Run lazy-ecs and navigate
# When done, Ctrl+D to stop

# Preview
asciinema play demo.cast
```

## Files

- `lazy-ecs-demo.cast` - Asciinema recording (anonymized)
- `lazy-ecs-demo.gif` - Generated animated demo
