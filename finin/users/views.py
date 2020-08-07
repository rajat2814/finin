import imaplib, email
from cryptography.fernet import Fernet
from rest_framework import viewsets, mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime, timedelta
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User, GmailCredentials, UserMail
from .permissions import IsUserOrReadOnly
from .serializers import CreateUserSerializer, UserSerializer
from .serializers import RegisterUserSerializer
from .serializers import LoginUserSerializer
from .serializers import GmailWriteSerializer, GmailReadSerializer, GmailMailReadSerializer
# from rest_framework.authtoken.models import Token
from knox.auth import TokenAuthentication
from knox.models import AuthToken
from rest_framework.permissions import AllowAny



KEY = 'eYXlXTwqfCwgfT-1x1gp_6bB19GP_KGRk0Z1KDPPBJg='.encode()



class UserLoginViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = User.objects.all()
    permission_classes = [AllowAny]
    authentication_classes = []

    @action(url_path='register', methods=['post'], detail=False)
    def register_user(self, request):
        serializer = RegisterUserSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = AuthToken.objects.create(user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token[1]
        })

    @action(url_path='login', methods=['post'], detail=False)
    def login_user(self, request):
        serializer = LoginUserSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        token = AuthToken.objects.create(user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token[1]
        })


class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    Updates and retrieves user accounts
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    write_gmail_serializer_class = GmailWriteSerializer
    read_gmail_serializer_class = GmailReadSerializer
    read_gmail_mail_serializer_class = GmailMailReadSerializer


    def list(self, request):
        if not request.user.is_superuser:
            return Response({
                    'Unauthorized Call'
                }, status=status.HTTP_401_UNAUTHORIZED)
        return super().list(request)


    def get_body(self, msg): 
        if msg.is_multipart(): 
            return self.get_body(msg.get_payload(0)) 
        else: 
            return msg.get_payload(None, True) 
  
    # Function to search for a key value pair  
    def search(self, key, value, con):  
        result, data = con.search(None, key, '"{}"'.format(value)) 
        return data 
      
    # Function to get the list of emails under this label 
    def get_emails(self, result_bytes, con): 
        msgs = [] # all the email data are pushed inside an array 
        for num in result_bytes[0].split(): 
            typ, data = con.fetch(num, '(RFC822)') 
            msgs.append(data) 
      
        return msgs 


    @action(url_path='logout-user-all-token', methods=['post'], detail=True)
    def logout_user(self, request, pk):
        if not request.user.is_superuser:
            return Response({
                    'Unauthorized Call'
                }, status=status.HTTP_401_UNAUTHORIZED)
        user = User.objects.get(id=pk)
        AuthToken.objects.filter(user=user).delete()
        return Response({
                'message': 'User logged Out Successfully'
            })

    @action(url_path='gmail-creds', methods=['post'], detail=False)
    def gmail_creds(self, request):
        data = request.data

        if not data.get('email_address'):
            raise serializers.ValidationError({
                'email_address': ['Enter Email Address']
            })

        if not data.get('password'):
            raise serializers.ValidationError({
                'password': ['Enter password']
            })

        _mutable = data._mutable

        # set to mutable
        data._mutable = True

        # сhange the values you want
        data.update({
            'password': Fernet(KEY).encrypt(data.get('password').encode()).decode()
        })

        # set mutable flag back
        data._mutable = _mutable
        write_serializer = self.write_gmail_serializer_class(
            data=data, context={'request': request})
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        read_serializer = self.read_gmail_serializer_class(instance)
        return Response(read_serializer.data)


    @action(url_path='sync-mail', methods=['post'], detail=False)
    def sync_mail(self, request):

        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        try:
            start_date_obj = datetime.strptime(start_date, '%Y/%m/%d')
        except Exception as e:
            raise serializers.ValidationError({
                'non_field_errors': ['Invalid Start Date']
            })
            # start_date_obj = datetime.today() - timedelta(days=10)
            # start_date = start_date_obj.strftime('%Y/%m/%d')


        try:
            end_date_obj = datetime.strptime(end_date, '%Y/%m/%d')
        except Exception as e:
            raise serializers.ValidationError({
                'non_field_errors': ['Invalid End Date']
            })
            # end_date_obj = datetime.today()
            # end_date = end_date_obj.strftime('%Y/%m/%d')

        SERVER = "imap.gmail.com"

        try:
            gmail_creds = GmailCredentials.objects.get(user=request.user)
        except Exception as e:
            raise serializer.ValidationError({
                    'non_field_errors': ['Gmail Creds are not present for you']
                })

        user = gmail_creds.email_address
        password = Fernet(KEY).decrypt(gmail_creds.password.encode()).decode()

        print(user, password)

        con = imaplib.IMAP4_SSL(SERVER)
  
        # logging the user in 
        con.login(user, password)

        con.select('Inbox')  

        print(con.list())
  
        # fetching emails from this user "tu**h*****1@gmail.com" 
        msgs = self.get_emails(self.search('X-GM-RAW', '{{(Bill)OR(Recharge)OR(credit)OR(debit)OR(investment)OR(invoice)}} -{{(OTP)}}  after:{0} before:{1}'.format(start_date, end_date), con), con)

        for msg in msgs[::-1]:  
            for sent in msg: 
                if type(sent) is tuple:  
          
                    # encoding set as utf-8 
          
                    # Handling errors related to unicodenecode 
                    try:  
                        content = str(sent[1], 'utf-8')  
                        data = str(content) 
                        indexstart = data.find("ltr") 
                        data2 = data[indexstart + 5: len(data)] 
                        indexend = data2.find("</div>") 
          
                        # printtng the required content which we need 
                        # to extract from our email i.e our body 
                        UserMail.objects.create(user=request.user, start_date=start_date_obj, end_date=end_date_obj, mail=data2[0: indexend])
          
                    except UnicodeEncodeError as e: 
                        pass

                    except UnicodeDecodeError as e: 
                        pass

        return Response({
                'message': 'success'
            })


    @action(url_path='all-mails', methods=['get'], detail=False)
    def all_mails(self, request):
        queryset = UserMail.objects.filter(user=request.user)
        read_serializer = self.read_gmail_mail_serializer_class(queryset, many=True)
        return Response(read_serializer.data)
