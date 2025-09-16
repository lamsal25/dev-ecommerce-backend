from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.core.signing import TimestampSigner
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import CustomUser


from .serializers import (
    RegisterSerializer,
    UserListSerializer
)




@api_view(["POST"])
@permission_classes([AllowAny])

def user_register(request):
    data= request.data
    data["role"]= "user"
    print(data)
    serializer = RegisterSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    user=serializer.save()

    signer    = TimestampSigner()
    reg_token = signer.sign(user.pk)
    return Response(
    {"message": "Registration successful!"},
    status=201
    )

@api_view(["PUT"])
def update_user_profile(request, pk):
    user = CustomUser.objects.get(pk=pk)
    if not user:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
    print(request.data)
    print(user.profile.country)
    user.profile.firstName=request.data.get("firstName", user.profile.firstName)
    user.profile.lastName=request.data.get("lastName", user.profile.lastName)
    user.profile.address=request.data.get("address", user.profile.address)
    user.profile.city=request.data.get("city", user.profile.city)
    user.profile.state=request.data.get("state", user.profile.state)
    user.profile.country=request.data.get("country", user.profile.country)
    user.profile.postalCode=request.data.get("postalCode", user.profile.postalCode)
    user.profile.mobile=request.data.get("mobile", user.profile.mobile)
    user.profile.save()
    user.save()
    return Response({"detail": "Profile updated successfully."}, status=status.HTTP_200_OK)    


class UserManagementView(APIView):
    permission_classes = [AllowAny]

    def get_object(self, pk):
        try:
            return CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return None
  
    def get(self, request, pk=None):
        if pk:
            user = self.get_object(pk)
            if not user:
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
            serializer = UserListSerializer(user)
            return Response(serializer.data)
        else:
            users = CustomUser.objects.all()
            serializer = UserListSerializer(users, many=True)
            return Response(serializer.data)

    def patch(self, request, pk=None):
        if not pk:
            return Response({"detail": "User ID required for update."}, status=status.HTTP_400_BAD_REQUEST)
        
        user = self.get_object(pk)
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserListSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
