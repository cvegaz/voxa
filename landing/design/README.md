# Design sources

Editable sources for the binary assets in `../public/`. A committed PNG with no
source is a dead end — the next person who needs to change one word has to
redraw it.

## `og-image.svg` → `public/og-image.png`

The social preview card (1200×630, the size Facebook, LinkedIn, WhatsApp,
Slack and X all expect). Colours come from `src/styles/tokens.css`; the mic
glyph is the one in `public/favicon.svg`.

Regenerating it on macOS, with no extra tooling:

```bash
cd landing/design

# Square canvas with the 1200×630 design vertically centred. Quick Look always
# renders to a square and scales the document; centring makes the crop
# deterministic instead of a guess about its scale factor.
sed 's|width="1200" height="630" viewBox="0 0 1200 630"|width="768" height="768" viewBox="0 -285 1200 1200"|' \
  og-image.svg > /tmp/og-sq.svg

qlmanage -t -s 1200 -o /tmp /tmp/og-sq.svg
sips -c 630 1200 /tmp/og-sq.svg.png --out ../public/og-image.png
```

Then check it: `sips -g pixelWidth -g pixelHeight ../public/og-image.png`
must report exactly 1200×630.

With ImageMagick or `rsvg-convert` installed, the whole dance collapses to
`rsvg-convert -w 1200 -h 630 og-image.svg -o ../public/og-image.png`.

**If the domain or the brand changes**, the card has `tryvoxa.com` baked into
it — update the SVG and regenerate, and update the absolute URLs in
`../index.html` in the same pass.
