from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
import traceback

User = get_user_model()

class Command(BaseCommand):
    help = 'Test email functionality in production'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send test email to',
            default='deeghalbhaumik@gmail.com'
        )
        parser.add_argument(
            '--test-reset',
            action='store_true',
            help='Test password reset email specifically'
        )

    def handle(self, *args, **options):
        email = options['email']
        
        self.stdout.write(f"🔧 Testing email functionality...")
        self.stdout.write(f"📧 Target email: {email}")
        self.stdout.write(f"📮 SMTP Host: {settings.EMAIL_HOST}")
        self.stdout.write(f"👤 SMTP User: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"🔐 Has Password: {'Yes' if settings.EMAIL_HOST_PASSWORD else 'No'}")
        
        # Test 1: Basic email send
        try:
            self.stdout.write("\n📨 Test 1: Basic email send...")
            result = send_mail(
                subject='TaskPro Email Test',
                message='This is a test email from TaskPro production server.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False
            )
            if result:
                self.stdout.write(self.style.SUCCESS("✅ Basic email sent successfully!"))
            else:
                self.stdout.write(self.style.ERROR("❌ Email send failed (returned 0)"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Email error: {str(e)}"))
            self.stdout.write(f"Full traceback: {traceback.format_exc()}")

        # Test 2: Password reset email
        if options['test_reset']:
            try:
                self.stdout.write("\n🔐 Test 2: Password reset email...")
                # Find a user with email
                user = User.objects.filter(email=email).first()
                if not user:
                    self.stdout.write(f"❌ No user found with email {email}")
                    return
                
                from django.contrib.auth.forms import PasswordResetForm
                form = PasswordResetForm({'email': email})
                if form.is_valid():
                    form.save(
                        request=None,
                        use_https=True,
                        email_template_name='accounts/password_reset_email.txt',
                        html_email_template_name='accounts/password_reset_email.html',
                        subject_template_name='accounts/password_reset_subject.txt'
                    )
                    self.stdout.write(self.style.SUCCESS("✅ Password reset email sent!"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Form invalid: {form.errors}"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Password reset error: {str(e)}"))
                self.stdout.write(f"Full traceback: {traceback.format_exc()}")

        self.stdout.write("\n🏁 Email testing complete!") 