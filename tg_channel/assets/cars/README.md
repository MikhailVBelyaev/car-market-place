# Car photos for vertical "shorts" price cards

Drop model photos here to use them as the (dimmed) background of the
`shorts_price` post. If a file is missing, the post falls back to a clean dark
gradient, so it always renders.

## Naming convention

`<brand>_<model>.jpg` — all lowercase, spaces as they are in the DB brand/model.

Examples:
- `chevrolet_spark.jpg`
- `chevrolet_nexia.jpg`
- `chevrolet_cobalt.jpg`
- `chevrolet_lacetti.jpg`
- `chevrolet_gentra.jpg`
- `chevrolet_malibu.jpg`
- `chevrolet_captiva.jpg`
- `chevrolet_tracker.jpg`

## Recommendations

- **Vertical or square** photos work best (the card is 9:16, 1080×1920).
- A clean side/3-4 view of the car on a plain background looks most premium.
- The image is darkened ~62% behind the price cards, so bright, well-lit
  photos read best.
- No rebuild needed: this folder is mounted into the tg_channel container
  (`./tg_channel/assets:/app/assets:ro`), so new files are picked up on the
  next post.
