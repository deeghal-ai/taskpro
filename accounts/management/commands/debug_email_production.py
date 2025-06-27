import os
from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.contrib.auth.forms import PasswordResetForm
from accounts.forms import CustomPasswordResetForm
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

User = get_user_model()

class Command(BaseCommand):
    help = 'Debug email functionality in production environment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='saket',
            help='Username to test password reset with'
        )
        parser.add_argument(
            '--test-smtp',
            action='store_true',
            help='Test direct SMTP connection'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=== EMAIL DEBUG REPORT ==='))
        
        # 1. Environment Check
        self.stdout.write(self.style.WARNING('\n1. ENVIRONMENT VARIABLES:'))
        env_vars = ['EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_USE_TLS', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD']
        for var in env_vars:
            value = os.environ.get(var, 'NOT SET')
            if var == 'EMAIL_HOST_PASSWORD' and value != 'NOT SET':
                value = '*' * len(value)  # Hide password
            self.stdout.write(f'{var}: {value}')

        # 2. Django Settings Check
        self.stdout.write(self.style.WARNING('\n2. DJANGO EMAIL SETTINGS:'))
        email_settings = [
            'EMAIL_BACKEND', 'EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_USE_TLS', 
            'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD', 'DEFAULT_FROM_EMAIL'
        ]
        for setting in email_settings:
            try:
                value = getattr(settings, setting, 'NOT SET')
                if setting == 'EMAIL_HOST_PASSWORD' and value != 'NOT SET':
                    value = '*' * len(str(value))
                self.stdout.write(f'{setting}: {value}')
            except Exception as e:
                self.stdout.write(f'{setting}: ERROR - {e}')

        # 3. User Check
        username = options['username']
        self.stdout.write(self.style.WARNING(f'\n3. USER CHECK ({username}):'))
        try:
            user = User.objects.get(username=username)
            self.stdout.write(f'User found: {user.username}')
            self.stdout.write(f'Email: {user.email or "NO EMAIL SET"}')
            self.stdout.write(f'Is active: {user.is_active}')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User "{username}" not found'))
            return

        # 4. Basic Email Test
        self.stdout.write(self.style.WARNING('\n4. BASIC EMAIL TEST:'))
        try:
            send_mail(
                'Test Email from TaskPro',
                'This is a test email from TaskPro production environment.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS('Basic email sent successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Basic email failed: {e}'))

        # 5. Password Reset Form Test
        self.stdout.write(self.style.WARNING('\n5. PASSWORD RESET FORM TEST:'))
        try:
            form = CustomPasswordResetForm({'email_or_username': username})
            if form.is_valid():
                self.stdout.write('Form is valid')
                
                # Create a fake request
                factory = RequestFactory()
                request = factory.post('/accounts/password/reset/')
                request.META['HTTP_HOST'] = 'taskspro.in'
                
                form.save(
                    request=request,
                    use_https=False,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                )
                self.stdout.write(self.style.SUCCESS('Password reset email sent via form'))
            else:
                self.stdout.write(self.style.ERROR(f'Form errors: {form.errors}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Password reset form failed: {e}'))

        # 6. Direct SMTP Test (if requested)
        if options['test_smtp']:
            self.stdout.write(self.style.WARNING('\n6. DIRECT SMTP TEST:'))
            try:
                # Create message
                msg = MIMEMultipart('alternative')
                msg['Subject'] = 'Direct SMTP Test from TaskPro'
                msg['From'] = settings.EMAIL_HOST_USER
                msg['To'] = user.email

                text = 'This is a direct SMTP test from TaskPro production environment.'
                html = '<p>This is a <b>direct SMTP test</b> from TaskPro production environment.</p>'

                part1 = MIMEText(text, 'plain')
                part2 = MIMEText(html, 'html')

                msg.attach(part1)
                msg.attach(part2)

                # Send via SMTP
                server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
                server.starttls()
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                self.stdout.write(self.style.SUCCESS('Direct SMTP email sent successfully'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Direct SMTP failed: {e}'))

        # 7. Email Queue Check (if using database backend)
        self.stdout.write(self.style.WARNING('\n7. ADDITIONAL CHECKS:'))
        self.stdout.write(f'Current time: {__import__("datetime").datetime.now()}')
        self.stdout.write(f'DEBUG mode: {settings.DEBUG}')
        self.stdout.write(f'ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}')
        
        self.stdout.write(self.style.WARNING('\n=== END DEBUG REPORT ==='))
        self.stdout.write(self.style.SUCCESS('Check your email inbox and spam folder for test emails.')) 