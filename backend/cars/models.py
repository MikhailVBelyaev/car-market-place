from django.db import models

# Create your models here.

class Car(models.Model):
    car_id = models.AutoField(primary_key=True)
    brand = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    year = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = 'cars'  # Maps to the existing table
        managed = False    # Prevents Django from altering the table

    def __str__(self):
        return f"{self.brand},model: {self.model}; year: {self.year}; price: {self.price}; description: {self.description}"
