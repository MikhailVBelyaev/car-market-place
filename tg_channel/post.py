#!/usr/bin/env python3
"""
Entry point for channel posts.

Usage:
  python post.py monday      # brand ranking
  python post.py wednesday   # price movers
  python post.py friday      # weekly digest
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))   # ensure charts/ and analytics/ are importable

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)

BOT_TOKEN   = os.getenv('CHANNEL_BOT_TOKEN', '')
CHANNEL_ID  = os.getenv('CHANNEL_ID', '')
DJANGO_URL  = os.getenv('DJANGO_URL', 'http://django:8000')

POST_TYPES  = ('monday', 'wednesday', 'friday')


def main():
    parser = argparse.ArgumentParser(description='Post analytics to Telegram channel')
    parser.add_argument('post_type', choices=POST_TYPES,
                        help='Which post to send')
    parser.add_argument('--dry-run', action='store_true',
                        help='Generate content but do not post to Telegram')
    args = parser.parse_args()

    if not BOT_TOKEN:
        logger.error("CHANNEL_BOT_TOKEN not set in .env")
        sys.exit(1)
    if not CHANNEL_ID:
        logger.error("CHANNEL_ID not set in .env")
        sys.exit(1)

    from channel import ChannelPoster
    poster = ChannelPoster(BOT_TOKEN, CHANNEL_ID)

    logger.info("Running %s post (dry_run=%s)", args.post_type, args.dry_run)

    if args.post_type == 'monday':
        from analytics.brand_ranking import run
    elif args.post_type == 'wednesday':
        from analytics.price_mover import run
    elif args.post_type == 'friday':
        from analytics.weekly_digest import run

    chart_buf, caption = run(DJANGO_URL)

    if args.dry_run:
        logger.info("DRY RUN — would post to %s", CHANNEL_ID)
        logger.info("Caption preview:\n%s", caption[:600])
        chart_buf.seek(0)
        out_path = f'/tmp/channel_{args.post_type}.png'
        with open(out_path, 'wb') as f:
            f.write(chart_buf.read())
        logger.info("Chart saved to %s", out_path)
    else:
        poster.post_photo(chart_buf, caption)
        logger.info("Done.")


if __name__ == '__main__':
    main()
