#!/usr/bin/env python3
"""
Entry point for channel posts.

Usage:
  python post.py monday              # brand ranking
  python post.py wednesday           # price movers
  python post.py friday              # weekly digest
  python post.py brand_ranking       # same as monday
  python post.py price_movers        # same as wednesday
  python post.py weekly_digest       # same as friday
  python post.py color_premium
  python post.py gear_premium
  python post.py age_depreciation
  python post.py best_value
  python post.py seasonal_trends
  python post.py market_breadth
  python post.py mileage_depreciation
"""
import argparse
import importlib
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

BOT_TOKEN  = os.getenv('CHANNEL_BOT_TOKEN', '')
CHANNEL_ID = os.getenv('CHANNEL_ID', '')
DJANGO_URL = os.getenv('DJANGO_URL', 'http://django:8000')

# Canonical mapping: post_type alias → analytics module path
DISPATCH = {
    'monday':               'analytics.brand_ranking',
    'brand_ranking':        'analytics.brand_ranking',
    'wednesday':            'analytics.price_mover',
    'price_movers':         'analytics.price_mover',
    'friday':               'analytics.weekly_digest',
    'weekly_digest':        'analytics.weekly_digest',
    'color_premium':        'analytics.color_premium',
    'gear_premium':         'analytics.gear_premium',
    'age_depreciation':     'analytics.age_depreciation',
    'best_value':           'analytics.best_value',
    'seasonal_trends':      'analytics.seasonal_trends',
    'market_breadth':       'analytics.market_breadth',
    'mileage_depreciation': 'analytics.mileage_depreciation',
    'daily_price':          'analytics.daily_price',
}

POST_TYPES = tuple(DISPATCH.keys())


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

    module_path = DISPATCH[args.post_type]
    module = importlib.import_module(module_path)
    chart_buf, caption = module.run(DJANGO_URL)

    if args.dry_run:
        logger.info("DRY RUN — would post to %s", CHANNEL_ID)
        print("\n" + caption + "\n")
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
