from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seeds all 4 new target-group profiles: low_income, single_parent, student, early_retiree"

    def handle(self, *args, **options):
        for cmd in (
            "seed_low_income",
            "seed_single_parent",
            "seed_student",
            "seed_early_retiree",
        ):
            call_command(cmd, stdout=self.stdout, stderr=self.stderr)
        self.stdout.write(self.style.SUCCESS("All 4 target-group seed profiles created successfully."))
