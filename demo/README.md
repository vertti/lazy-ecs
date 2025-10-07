# Demo Generation

Generate animated GIF demos of lazy-ecs using asciinema recordings.

## Generate GIF

```bash
# Download Noto Emoji font for emoji support
curl -L https://github.com/googlefonts/noto-emoji/releases/download/v2.047/Noto-COLRv1.ttf -o /tmp/NotoEmoji.ttf

# Generate GIF with Docker (ensures emoji rendering)
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
