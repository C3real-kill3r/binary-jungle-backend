import re

from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from rest_framework import serializers

from .models import User, BlacklistedToken
from authors.apps.profiles.models import Profile

email_expression = re.compile(
    r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")
trial_email = re.compile(
    r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[0-9-.]+$)")
trial_email_2 = re.compile(
    r"(^[a-zA-Z0-9_.+-]+@[0-9-]+\.[a-zA-Z0-9-.]+$)")
at_least_number = re.compile(
    r"^(?=.*[0-9]).*")
at_least_uppercase = re.compile(
    r"^(?=.*[A-Z])(?=.*[a-z])(?!.*\s).*")
at_least_special_char = re.compile(
    r".*[!@#$%^&*()_\-+={};:\'\"|`~,<.>?/].*")


class RegistrationSerializer(serializers.ModelSerializer):
    """Serializers registration requests and creates a new user."""
    # Username must be longer than 4 characters but shorter than 128 characters.
    # Username is a required field
    username = serializers.CharField(
        required=True,
    )
    # Ensure email is present and has the valid format example@mail.com
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "Email is required!"
        }
    )
    # Ensure passwords are at least 8 characters long, no longer than 128
    # characters, and can not be read by the client.
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True,
        required=True,
    )
    # The client should not be able to send a token along with a registration
    # request. Making `token` read-only handles that for us.
    token = serializers.CharField(
        read_only=True
    )

    class Meta:
        model = User
        # List all of the fields that could possibly be included in a request
        # or response, including fields specified explicitly above.
        fields = ['email', 'username', 'password', 'token']

    def validate_username(self, data):
        """
        Validate the provided username
        min_len=4
        max_len=128
        required=True
        unique=True
        """
        candidate_name = data
        try:
            if int(candidate_name):
                raise serializers.ValidationError({"username": ["Username cannot be numbers only!"]})
        except ValueError:
            pass
        if candidate_name == "":
            raise serializers.ValidationError({"username": ["Username is required!"]})
        elif User.objects.filter(username=candidate_name):
            raise serializers.ValidationError({"username": ["Username already exists!"]})
        elif len(candidate_name) < 4:
            raise serializers.ValidationError({"username": ["Username should be more than 4 charcaters!"]})
        elif len(candidate_name) > 128:
            raise serializers.ValidationError({"username": ["Username should not be longer than 128 charcaters!"]})
        return data

    def validate_email(self, data):
        """
        Validate the provided email
        required=True
        unique=True
        format: example@mail.com
        """
        candidate_email = data
        if candidate_email == "":
            raise serializers.ValidationError({"email": ["Email is required!"]})
        elif re.match(trial_email, candidate_email):
            raise serializers.ValidationError({"email": ["Invalid email! Hint: example@mail.com"]})
        elif re.match(trial_email_2, candidate_email):
            raise serializers.ValidationError({"email": ["Invalid email! Hint: example@mail.com"]})
        elif User.objects.filter(email=candidate_email):
            raise serializers.ValidationError({"email": ["User with provided email exists! Please login!"]})
        elif not re.match(email_expression, candidate_email):
            raise serializers.ValidationError({"email": ["Invalid email! Hint: example@mail.com!"]})
        return data

    def validate_password(self, data):
        """
        Validate the provided password
        required=True
        min_len=8
        is_alphanumeric=True

        """
        candidate_password = data
        if candidate_password == "":
            raise serializers.ValidationError({
                "password": ["Password is required!"]})
        elif len(candidate_password) < 8:
            raise serializers.ValidationError({
                "password": ["Password should be at least eight (8) characters long!"]})
        elif len(candidate_password) > 128:
            raise serializers.ValidationError({
                "password": ["Password should not be longer than (128) characters long!"]})
        elif not re.match(at_least_number, candidate_password):
            raise serializers.ValidationError({
                "password": ["Password must have at least one number!"]})
        elif not re.match(at_least_uppercase, candidate_password):
            raise serializers.ValidationError({
                "password": ["Password must have at least one uppercase letter!"]})
        elif not re.match(at_least_special_char, candidate_password):
            raise serializers.ValidationError({
                "password": ["Password must include a special character!"]})
        return data

    def create(self, validated_data):
        # Use the `create_user` method we wrote earlier to create a new user.
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=255, read_only=True)
    password = serializers.CharField(max_length=128, write_only=True)
    token = serializers.CharField(max_length=512, read_only=True)

    def validate(self, data):
        # The `validate` method is where we make sure that the current
        # instance of `LoginSerializer` has "valid". In the case of logging a
        # user in, this means validating that they've provided an email
        # and password and that this combination matches one of the users in
        # our database.
        email = data.get('email', None)
        password = data.get('password', None)

        # As mentioned above, an email is required. Raise an exception if an
        # email is not provided.
        if email is None:
            raise serializers.ValidationError(
                'An email address is required to log in.'
            )

        # As mentioned above, a password is required. Raise an exception if a
        # password is not provided.
        if password is None:
            raise serializers.ValidationError(
                'A password is required to log in.'
            )

        # The `authenticate` method is provided by Django and handles checking
        # for a user that matches this email/password combination. Notice how
        # we pass `email` as the `username` value. Remember that, in our User
        # model, we set `USERNAME_FIELD` as `email`.
        user = authenticate(username=email, password=password)

        # If no user was found matching this email/password combination then
        # `authenticate` will return `None`. Raise an exception in this case.
        if user is None:
            raise serializers.ValidationError(
                'A user with this email and password was not found.'
            )

        # Django provides a flag on our `User` model called `is_active`. The
        # purpose of this flag to tell us whether the user has been banned
        # or otherwise deactivated. This will almost never be the case, but
        # it is worth checking for. Raise an exception in this case.
        if not user.is_active:
            raise serializers.ValidationError(
                'This user has been deactivated.'
            )

        # The `validate` method should return a dictionary of validated data.
        # This is the data that is passed to the `create` and `update` methods
        # that we will see later on.
        return {
            'email': user.email,
            'username': user.username,
            'token': user.token
        }


class UserSerializer(serializers.ModelSerializer):
    """Handles serialization and deserialization of User objects."""

    # Passwords must be at least 8 characters, but no more than 128
    # characters. These values are the default provided by Django. We could
    # change them, but that would create extra work while introducing no real
    # benefit, so let's just stick with the defaults.
    password = serializers.CharField(
        max_length=128,
        min_length=8,
        write_only=True
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'password')

        # The `read_only_fields` option is an alternative for explicitly
        # specifying the field with `read_only=True` like we did for password
        # above. The reason we want to use `read_only_fields` here is because
        # we don't need to specify anything else about the field. For the
        # password field, we needed to specify the `min_length` and
        # `max_length` properties too, but that isn't the case for the token
        # field.

    def update(self, instance, validated_data):
        """Performs an update on a User."""

        # Passwords should not be handled with `setattr`, unlike other fields.
        # This is because Django provides a function that handles hashing and
        # salting passwords, which is important for security. What that means
        # here is that we need to remove the password field from the
        # `validated_data` dictionary before iterating over it.
        password = validated_data.pop('password', None)

        for (key, value) in validated_data.items():
            # For the keys remaining in `validated_data`, we will set them on
            # the current `User` instance one at a time.
            setattr(instance, key, value)

        if password is not None:
            # `.set_password()` is the method mentioned above. It handles all
            # of the security stuff that we shouldn't be concerned with.
            instance.set_password(password)

        # Finally, after everything has been updated, we must explicitly save
        # the model. It's worth pointing out that `.set_password()` does not
        # save the model.
        instance.save()

        return instance


class ForgotPasswordSerializer(serializers.Serializer):
    """Performs email serialization."""
    email = serializers.EmailField()


class ResetPasswordSerializers(serializers.Serializer):

    """
    Performs reset password fields serialization.
    """
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(
        max_length=128,
        min_length=8
    )
    confirm_password = serializers.CharField(
        max_length=128,
        min_length=8
    )
    token = serializers.CharField(max_length=255)

    def validate(self, data):
        """
        Validates passwords match and
        token can only be used once
        """
        # Query user from DB using email
        email = data.get('email')
        user = User.objects.filter(email=email).first()
        if data.get('password') != data.get('confirm_password'):
            msg = "The passwords do not match."
            raise serializers.ValidationError(msg)
        # Confirm if token is valid
        token = data.get('token')
        validate_token = default_token_generator.check_token(user, token)
        if not validate_token:
            msg = "Something went wrong. Try again."  # we don't want to give away security details
            raise serializers.ValidationError(msg)
        user.set_password(data.get('password'))
        user.save()
        return data


class SocialSignUpSerializer(serializers.Serializer):
    """Handles serialization and deserialization
        of the request data of social auth login
        """
    provider = serializers.CharField(max_length=20, required=True)
    access_token = serializers.CharField(max_length=255, required=True)


class LogoutSerializer(serializers.ModelSerializer):
    """Performs logout serializer"""
    token = serializers.CharField(max_length=500)


    class Meta:
        model = BlacklistedToken
        fields = "__all__"
