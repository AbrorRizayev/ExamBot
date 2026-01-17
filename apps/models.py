from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, UserManager
from django.db.models import Model, CharField, PositiveIntegerField, FileField, DateTimeField, CASCADE, ForeignKey, \
    TextField, BigIntegerField, BooleanField


class CustomUserManager(UserManager):
    use_in_migrations = True

    def _create_user_object(self, phone_number, password, **extra_fields):
        if not phone_number:
            raise ValueError("The given phone_number must be set")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.password = make_password(password)
        return user

    def _create_user(self, phone_number, password, **extra_fields):
        """
        Create and save a user with the given phone_number, and password.
        """
        user = self._create_user_object(phone_number, password, **extra_fields)
        user.save(using=self._db)
        return user

    async def _acreate_user(self, phone_number,  password, **extra_fields):
        """See _create_user()"""
        user = self._create_user_object(phone_number, password, **extra_fields)
        await user.asave(using=self._db)
        return user

    def create_user(self, phone_number,  password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone_number,  password, **extra_fields)

    create_user.alters_data = True

    async def acreate_user(self, phone_number,  password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return await self._acreate_user(phone_number,  password, **extra_fields)

    acreate_user.alters_data = True

    def create_superuser(self, phone_number,  password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(phone_number,  password, **extra_fields)

    create_superuser.alters_data = True

    async def acreate_superuser(
            self, phone_number,  password=None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return await self._acreate_user(phone_number, password, **extra_fields)

    acreate_superuser.alters_data = True


class User(AbstractUser):
    username = None
    email = None

    phone_number = CharField(max_length=20, unique=True)
    telegram_id = BigIntegerField(null=True, blank=True)
    password = CharField(max_length=255, null=True, blank=True)
    objects = CustomUserManager()
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone_number



class Exam(Model):
    name = CharField(max_length=255)
    questions_count = PositiveIntegerField()
    excel_file = FileField(upload_to='exam_excels/')
    created_at = DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name



class Question(Model):
    exam = ForeignKey(Exam, on_delete=CASCADE, related_name='questions')
    text = TextField()
    option_a = CharField(max_length=255)
    option_b = CharField(max_length=255)
    option_c = CharField(max_length=255)
    option_d = CharField(max_length=255)
    correct_option = CharField(
        max_length=1,
        choices=[('A','A'),('B','B'),('C','C'),('D','D')]
    )



class UserAnswer(Model):
    user = ForeignKey(User, on_delete=CASCADE)
    exam = ForeignKey(Exam, on_delete=CASCADE)
    question = ForeignKey(Question, on_delete=CASCADE)
    selected_option = CharField(max_length=1)
    is_correct = BooleanField()

