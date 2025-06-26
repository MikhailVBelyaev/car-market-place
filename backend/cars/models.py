from django.db import models

# Create your models here.

class Car(models.Model):
    car_id = models.AutoField(primary_key=True)
    brand = models.CharField(max_length=255, default='Chevrolet')
    model = models.CharField(max_length=255, default='Lacetti')
    year = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField()
    mileage = models.IntegerField(null=True, blank=True)
    car_ad_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    reference_url = models.URLField(null=True, blank=True)
    description_detail = models.TextField(null=True, blank=True)

    TRANSMISSION_CHOICES = [
        ('AT', 'Automatic'),
        ('MT', 'Manual'),
        ('DSG', 'Dual-clutch'),
    ]
    gear_type = models.CharField(
        max_length=10, choices=TRANSMISSION_CHOICES, null=True, blank=True
    )

    COLOR_CHOICES = [
        ('white', 'White'),
        ('black', 'Black'),
        ('silver', 'Silver'),
        ('grey', 'Grey'),
        ('blue', 'Blue'),
        ('red', 'Red'),
        ('green', 'Green'),
        ('yellow', 'Yellow'),
    ]
    color = models.CharField(
        max_length=20, choices=COLOR_CHOICES, null=True, blank=True
    )

    VEHICLE_TYPE_CHOICES = [
        ('EV', 'Electric Vehicle'),
        ('Fuel', 'Fuel-based'),
        ('Hybrid', 'Hybrid'),
    ]
    vehicle_type = models.CharField(
        max_length=10, choices=VEHICLE_TYPE_CHOICES, null=True, blank=True
    )

    FUEL_TYPE_CHOICES = [
        ('Gasoline', 'Gasoline'),
        ('Diesel', 'Diesel'),
        ('Electric', 'Electric'),
        ('Hybrid', 'Hybrid'),
        ('Gas', 'Gas'),
    ]
    fuel_type = models.CharField(
        max_length=10, choices=FUEL_TYPE_CHOICES, null=True, blank=True
    )

    CONDITION_CHOICES = [
        ('damaged', 'Damaged'),
        ('repaired', 'Repaired'),
        ('ideal', 'Ideal'),
        ('needs_repair', 'Needs Repair'),
    ]
    condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, null=True, blank=True
    )

    customer_paid_tax = models.BooleanField(null=True, blank=True)
    additional_options = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, null=True, blank=True)

    owner_name = models.CharField(max_length=255, null=True, blank=True)
    owner_member_since = models.CharField(max_length=255, null=True, blank=True)
    owner_last_seen = models.CharField(max_length=255, null=True, blank=True)
    owner_profile_url = models.URLField(null=True, blank=True)
    owner_tel_number = models.CharField(max_length=50, null=True, blank=True)
    owner_type = models.CharField(max_length=100, null=True, blank=True)
    body_type = models.CharField(max_length=100, null=True, blank=True)
    owner_count = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'cars'  # Maps to the existing table
        managed = False    # Prevents Django from altering the table
        app_label = 'cars'  # Explicitly define the app label

    def __str__(self):
        return (
            f"brand: {self.brand}, model: {self.model}\n"
            f"year: {self.year}, price: {self.price}\n"
            f"description: {self.description}\n"
            f"created_at: {self.created_at}, mileage: {self.mileage}\n"
            f"transmission: {self.gear_type}, color: {self.color}, "
            f"vehicle_type: {self.vehicle_type}, fuel_type: {self.fuel_type}\n"
            f"condition: {self.condition}, customer_paid_tax: {self.customer_paid_tax}\n"
            f"additional_options: {self.additional_options}, location: {self.location}"
        )
