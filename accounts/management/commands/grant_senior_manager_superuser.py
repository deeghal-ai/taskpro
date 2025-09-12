from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User


class Command(BaseCommand):
    help = 'Grant superuser status to all users with SENIOR_MANAGER role for full admin access'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually making changes',
        )
        parser.add_argument(
            '--revoke',
            action='store_true',
            help='Revoke superuser status from Senior Managers instead of granting it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        revoke = options['revoke']
        
        # Find all Senior Manager users
        senior_managers = User.objects.filter(role='SENIOR_MANAGER')
        
        if not senior_managers.exists():
            self.stdout.write(
                self.style.WARNING('No users found with SENIOR_MANAGER role.')
            )
            return

        self.stdout.write(f"Found {senior_managers.count()} Senior Manager(s):")
        
        # Show current status
        for user in senior_managers:
            staff_status = "HAS staff access" if user.is_staff else "NO staff access"
            super_status = "HAS superuser access" if user.is_superuser else "NO superuser access"
            self.stdout.write(f"  - {user.username} ({user.get_full_name()}) - {staff_status}, {super_status}")

        if dry_run:
            action = "WOULD BE REVOKED from" if revoke else "WOULD BE GRANTED to"
            self.stdout.write(
                self.style.SUCCESS(f"\n[DRY RUN] Superuser access {action} {senior_managers.count()} Senior Manager(s)")
            )
            return

        # Perform the actual update
        if revoke:
            # Revoke superuser status
            users_to_update = senior_managers.filter(is_superuser=True)
            action_word = "revoked from"
            new_status = False
        else:
            # Grant superuser status
            users_to_update = senior_managers.filter(is_superuser=False)
            action_word = "granted to"
            new_status = True

        if not users_to_update.exists():
            already_status = "already have" if not revoke else "don't have"
            self.stdout.write(
                self.style.SUCCESS(f"All Senior Managers {already_status} superuser access. No changes needed.")
            )
            return

        # Update users in a transaction
        with transaction.atomic():
            updated_count = users_to_update.update(is_superuser=new_status)
            
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuperuser access {action_word} {updated_count} Senior Manager(s):"
            )
        )
        
        # Show updated users
        for user in users_to_update:
            self.stdout.write(f"  > {user.username} ({user.get_full_name()})")
            
        if not revoke:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSenior Managers now have full admin interface access at /admin/"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSenior Managers no longer have superuser admin access"
                )
            )
