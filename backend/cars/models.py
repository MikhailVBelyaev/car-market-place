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

    class Meta:
        db_table = 'cars'  # Maps to the existing table
        managed = False    # Prevents Django from altering the table
        app_label = 'cars'  # Explicitly define the app label

    def __str__(self):
        return (
            f"brand: {self.brand}, model: {self.model}\n"
            f"year: {self.year}, price: {self.price}\n"
            f"description: {self.description}\n"
            f"created_at: {self.created_at}, mileage: {self.mileage}"
        )
