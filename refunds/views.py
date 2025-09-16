from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import RefundRequest, Order, Product
from .serializers import RefundRequestCreateSerializer, RefundRequestSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_refund_request(request):
    """
    Create a new refund request
    """
    print(request.data)
    serializer = RefundRequestCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        try:
            # Get validated data
            order_id = serializer.validated_data['orderId']
            product_id = serializer.validated_data['productId']
            reason = serializer.validated_data['reason']
            
            # Get objects
            order = Order.objects.get(id=order_id)
            product = Product.objects.get(id=product_id)
            vendor = product.vendor
            user = request.user
            
            # Create refund request
            refund_request = RefundRequest.objects.create(
                order=order,
                product=product,
                user=user,
                vendor=vendor,
                reason=reason
            )
            
            # Send email to vendor
            try:
                send_refund_email_to_vendor(refund_request)
            except Exception as email_error:
                print(f"Failed to send email: {email_error}")
                # Don't fail the request if email fails
            
            # Serialize and return the created refund request
            response_serializer = RefundRequestSerializer(refund_request)
            
            return Response({
                'message': 'Refund request submitted successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print("Serializer errors:", serializer.errors)  # 👈 add this
            return Response({
                'error': f'Failed to create refund request: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_refund_requests(request):
    """
    Get all refund requests for the authenticated user
    """
    refund_requests = RefundRequest.objects.filter(user=request.user).order_by('-created_at')
    serializer = RefundRequestSerializer(refund_requests, many=True)
    
    return Response({
        'data': serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_vendor_refund_requests(request):
    """
    Get all refund requests for vendor's products
    """
    try:
        vendor = request.user.vendor
        refund_requests = RefundRequest.objects.filter(vendor=vendor,status="pending").order_by('-created_at')
        serializer = RefundRequestSerializer(refund_requests, many=True)
        
        return Response({
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except:
        return Response({
            'error': 'Vendor profile not found'
        }, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_approved_vendor_refund_requests(request):
    """
    Get all refund requests for vendor's products
    """
    try:
        vendor = request.user.vendor
        refund_requests = RefundRequest.objects.filter(vendor=vendor,status="approved").order_by('-created_at')
        serializer = RefundRequestSerializer(refund_requests, many=True)
        
        return Response({
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    except:
        return Response({
            'error': 'Vendor profile not found'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_refund_status(request, refund_id):
    """
    Update refund request status (for vendors/admin)
    """
    try:
        refund_request = RefundRequest.objects.get(id=refund_id)
        
        # Check if user is the vendor or admin
        if hasattr(request.user, 'vendor') and request.user.vendor == refund_request.vendor:
            # Vendor can update
            pass
        elif request.user.is_staff or request.user.is_superuser:
            # Admin can update
            pass
        else:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        new_status = request.data.get('status')
        admin_notes = request.data.get('admin_notes', '')
        
        if new_status not in ['pending', 'approved', 'rejected', 'processed']:
            return Response({
                'error': 'Invalid status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        refund_request.status = new_status
        refund_request.admin_notes = admin_notes
        refund_request.save()
        
        # Send email to customer about status update
        try:
            send_refund_status_email_to_customer(refund_request)
        except Exception as email_error:
            print(f"Failed to send status email: {email_error}")
        
        serializer = RefundRequestSerializer(refund_request)
        
        return Response({
            'message': 'Refund status updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except RefundRequest.DoesNotExist:
        return Response({
            'error': 'Refund request not found'
        }, status=status.HTTP_404_NOT_FOUND)

def send_refund_email_to_vendor(refund_request):
    """
    Send email notification to vendor about new refund request
    """
    subject = f'New Refund Request - Order #{refund_request.order.id}'
    
    # Create email context
    context = {
        'vendor_name': refund_request.vendor.businessName,
        'customer_name': refund_request.user.username,
        'customer_email': refund_request.user.email,
        'order_id': refund_request.order.id,
        'product_name': refund_request.product.name,
        'refund_reason': refund_request.reason,
        'request_date': refund_request.created_at.strftime('%B %d, %Y at %I:%M %p'),
        'refund_request_id': refund_request.id,
    }
    
    # Render email template
    html_message = render_to_string('emails/vendor_notifications.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[refund_request.vendor.email],
        html_message=html_message,
        fail_silently=False,
    )

def send_refund_status_email_to_customer(refund_request):
    """
    Send email notification to customer about refund status update
    """
    subject = f'Refund Request Update - Order #{refund_request.order.id}'
    
    # Create email context
    context = {
        'customer_name': refund_request.user.username,
        'order_id': refund_request.order.id,
        'product_name': refund_request.product.name,
        'refund_status': refund_request.status.title(),
        'admin_notes': refund_request.admin_notes,
        'vendor_name': refund_request.vendor.businessName,
        'update_date': refund_request.updated_at.strftime('%B %d, %Y at %I:%M %p'),
    }
    
    # Render email template
    html_message = render_to_string('emails/customer_refund.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[refund_request.user.email],
        html_message=html_message,
        fail_silently=False,
    )

