from rest_framework import serializers
from .models import User, GmailCredentials, UserMail
from django.contrib.auth.hashers import check_password


class RegisterUserSerializer(serializers.ModelSerializer):

    def create(self, validated_data):

        first_name = validated_data.get('first_name')
        last_name = validated_data.get('last_name')
        email = validated_data['email']
        password = validated_data['password']

        if not email:
            raise serializers.ValidationError({
                'email': ['Please Enter Email']
            })

        if not password:
            raise serializers.ValidationError({
                'password': ['Please Enter password']
            })

        if not first_name:
            raise serializers.ValidationError({
                'first_name': ['Please Enter first_name']
            })

        if not last_name:
            raise serializers.ValidationError({
                'last_name': ['Please Enter last_name']
            })

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({
                'email': ['User with same email already exists']
            })

        user = User(**{
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'username': email
        })
        user.set_password(password)
        user.save()
        return user

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'password',
            'first_name',
            'last_name',
            'auth_token'
        )
        read_only_fields = ('auth_token',)
        extra_kwargs = {'password': {'write_only': True}}


class LoginUserSerializer(serializers.Serializer):

    email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):

        email = data.get('email')

        try:
            user_instance = \
                User.objects.filter(email=email)
            if user_instance.exists():
                user_instance = user_instance.first()
            else:
                raise Exception('This email does not exist in this workspace')
        except Exception as e:
            raise serializers.ValidationError({
                'email': str(e)
            })

        password = data.get('password')
        pwd_valid = check_password(password, user_instance.password)

        if user_instance and user_instance.is_active and pwd_valid:
            return user_instance

        if pwd_valid is False:
            raise serializers.ValidationError({
                'password': 'Invalid password'
            })

        if user_instance.is_active is False:
            raise serializers.ValidationError({
                'non_field_errors': 'User is inactive'
            })

        raise serializers.ValidationError(
            'Unable to log in with provided credentials.'
        )


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name',)
        read_only_fields = ('email', )


class GmailMailReadSerializer(serializers.ModelSerializer):

    user = UserSerializer()

    class Meta:
        model = UserMail
        fields = (
                'user',
                'start_date',
                'end_date',
                'mail',
                'created_on'
            )


class CreateUserSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        # call create_user on user object. Without this
        # the password will be stored in plain text.
        user = User.objects.create_user(**validated_data)
        return user

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 'email', 'auth_token',)
        read_only_fields = ('auth_token',)
        extra_kwargs = {'password': {'write_only': True}}


class GmailWriteSerializer(serializers.ModelSerializer):


    # def validate(self, data):

    #     gmail_creds = GmailCredentials.objects.filter(user=self.context['request'].user)

    #     if gmail_creds.count() > 0:
    #         raise serializers.ValidationError({
    #             'non_field_errors': ['Credentials Already Exists']
    #         })

    #     return data

    def create(self, validated_data):

        validated_data.update({
                'user': self.context['request'].user
            })

        gmail_creds = GmailCredentials.objects.filter(user=self.context['request'].user)

        if gmail_creds.count() > 0:
            GmailCredentials.objects.filter(user=self.context['request'].user).update(**validated_data)
            gmail_creds = GmailCredentials.objects.get(user=self.context['request'].user)
        else:
            gmail_creds = GmailCredentials.objects.create(**validated_data)

        print(123445)
        print(gmail_creds)

        return gmail_creds

    class Meta:
        model = GmailCredentials
        fields = [
            'email_address',
            'password'
        ]


class GmailReadSerializer(serializers.ModelSerializer):

    user = UserSerializer()
    
    class Meta:
        model = GmailCredentials
        fields = [
            'user',
            'email_address'
        ]
