import json
import os
from django.core.management.base import BaseCommand
from cars.models import Car

class Command(BaseCommand):
    help = "Upload car ads from a local JSON file (skip duplicates)"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str)

    def handle(self, *args, **options):
        file_path = options['file_path']

        if not os.path.exists(file_path):
            self.stderr.write(f"❌ File not found: {file_path}")
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        created = 0
        skipped = 0

        for ad in data:
            fields = ad.get("fields", {})
            car_ad_id = fields.get("car_ad_id")

            if not car_ad_id:
                skipped += 1
                continue

            if Car.objects.filter(car_ad_id=car_ad_id).exists():
                skipped += 1
                continue

            try:
                Car.objects.create(**fields)
                created += 1
            except Exception as e:
                self.stderr.write(f"❌ Error creating ad {car_ad_id}: {e}")
                skipped += 1

        self.stdout.write(f"✅ Done. Created: {created}, Skipped: {skipped}")