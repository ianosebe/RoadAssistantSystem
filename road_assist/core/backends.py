from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailOrPhoneModelBackend(ModelBackend):
    """
    Custom auth backend to allow users to log in using their 
    username, email, or phone_number.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        
        try:
            # Check if the input matches username, email, or phone_number
            user = UserModel.objects.get(
                Q(username__iexact=username) | 
                Q(email__iexact=username) | 
                Q(phone_number__iexact=username)
            )
        except UserModel.DoesNotExist:
            # Run the default password hasher once to mitigate timing attacks
            UserModel().set_password(password)
            return None
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None