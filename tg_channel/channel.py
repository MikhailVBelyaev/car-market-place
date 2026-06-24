"""Telegram channel posting via Bot API."""
import io
import logging
import requests

logger = logging.getLogger(__name__)


class ChannelPoster:
    def __init__(self, bot_token: str, channel_id: str):
        self.base = f"https://api.telegram.org/bot{bot_token}"
        self.channel_id = channel_id

    def post_photo(self, photo_buf: io.BytesIO, caption: str) -> dict:
        photo_buf.seek(0)
        r = requests.post(
            f"{self.base}/sendPhoto",
            data={
                'chat_id':    self.channel_id,
                'caption':    caption[:1024],     # Telegram caption limit
                'parse_mode': 'Markdown',
            },
            files={'photo': ('chart.png', photo_buf, 'image/png')},
            timeout=30,
        )
        r.raise_for_status()
        logger.info("Posted photo to channel %s", self.channel_id)
        return r.json()

    def post_text(self, text: str) -> dict:
        r = requests.post(
            f"{self.base}/sendMessage",
            json={
                'chat_id':    self.channel_id,
                'text':       text,
                'parse_mode': 'Markdown',
            },
            timeout=15,
        )
        r.raise_for_status()
        logger.info("Posted text to channel %s", self.channel_id)
        return r.json()
