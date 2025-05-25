from django.db import models

class JobApplication(models.Model):
    subject = models.CharField(max_length=255)
    sender = models.CharField(max_length=255)
    date_received = models.DateTimeField()
    status = models.CharField(max_length=50, default='Applied')  # Applied, In Review, Interview, Offer, Rejected
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.subject} - {self.status}"
