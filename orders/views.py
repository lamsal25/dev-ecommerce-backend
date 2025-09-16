from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .models import Order
from products.models import ProductSize
from coupons.models import Coupon,CouponUsage
from rewards.utils import increaseRewardPoints
from .serializers import OrderSerializer
from cart.service import Cart
from django.core.mail import send_mail
from django.conf import settings
from products.models import Product
from django.http import FileResponse, Http404
from reportlab.pdfgen import canvas 
import io
from django.apps import apps 


@api_view(['POST'])
@permission_classes([AllowAny])
def createOrder(request):
    user = request.user
    print("User is: ",user)
    data = request.data
    print(request.data)
    coupon_codes = data.get('coupon_codes', []) 
    coupons = []
    for code in coupon_codes:
        try:
            coupon = Coupon.objects.get(code=code)
            coupons.append(coupon)
        except Coupon.DoesNotExist:
            continue
    billing_name = request.data.get("billing_details").get("name")
    billing_email = request.data.get("billing_details").get("email")
    
    serializer = OrderSerializer(data=data)
    if serializer.is_valid():
        order = serializer.save(user=user,payment_status="Pending", order_status="pending")
        
        #Coupon Logic
        for coupon in coupons:
            CouponUsage.objects.create(user=request.user, coupon=coupon)
            coupon.used_count += 1
            coupon.save()

        # Add reward points to user
        increaseRewardPoints(user,order.total_amount)
         # Import models safely without circular import issues
        VendorOrderItemStatus = apps.get_model('vendors', 'VendorOrderItemStatus')
        Product = apps.get_model('products', 'Product')

        # Process cart_items JSON and create VendorOrderItemStatus records
        cart_items = order.cart_items
        print("cart items", cart_items)

        for item in cart_items:
            product_id = item.get("productID")
            quantity = int(item.get("quantity"))
            has_sizes = item.get("has_sizes", False)
            selected_size = item.get("selected_size")  # may be None
            price = float(item.get("price"))

            try:
                product = Product.objects.get(id=product_id)
                vendor = product.vendor

                # Create vendor order item
                VendorOrderItemStatus.objects.create(
                    vendor=vendor,
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=price,
                    status="Pending"
                )

                # Deduct stock
                if has_sizes and selected_size:
                    # Case 1: Product has sizes → deduct stock from ProductSize
                    try:
                        size_obj = ProductSize.objects.get(product=product, size=selected_size)
                        current_stock = size_obj.stock
                        new_stock = max(current_stock - quantity, 0)
                        size_obj.stock = new_stock
                        size_obj.save()

                        print(
                            f"Stock updated for {product.name} ({selected_size}): "
                            f"{current_stock} → {new_stock}"
                        )

                    except ProductSize.DoesNotExist:
                        print(
                            f"Size {selected_size} for product {product.name} not found — skipping stock deduction."
                        )

                else:
                    # Case 2: Product without sizes → deduct from totalStock
                    current_stock = int(product.totalStock)
                    new_stock = max(current_stock - quantity, 0)
                    product.totalStock = str(new_stock)
                    product.save()

                    print(
                        f"Stock updated for {product.name}: {current_stock} → {new_stock}"
                    )

            except Product.DoesNotExist:
                print(f"Product with ID {product_id} not found — skipping.")
        cart = Cart(request)
        cart.clear()
        try:

            send_mail(
                subject='Order Confirmation - Thank You for Your Purchase!',
                message=f'Dear {billing_name},\n\nYour order has been successfully placed and the payment has been verified.\n\nThank you for shopping with us!',
                from_email=settings.DEFAULT_FROM_EMAIL,  # or use DEFAULT_FROM_EMAIL
                recipient_list=[billing_email],
                fail_silently=False,
            )
            print("Confirmation email sent.")
        except Exception as email_err:
            print("Error sending email:", email_err)
        return Response({
            "message": "Order created successfully",
            "order_id": order.id,
            "order_status": order.order_status,
        }, status=status.HTTP_201_CREATED)
    
    print(serializer.errors)  # debug if still error
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getOrders(request):
    user = request.user
    if user.is_authenticated:
        orders = Order.objects.filter(user=user.id).order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    else:
        return Response({"message": "User not Authenticated"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def getOrder(request, orderID):
    """Get details of a specific order"""
    try:
        order = Order.objects.get(id=orderID)
        serializer = OrderSerializer(order)
        return Response(serializer.data)
    except Order.DoesNotExist:
        return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)


# Mark order as received
# Notification = apps.get_model('notifications', 'Notification')
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def markOrderReceived(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Only allow marking received if fully delivered
        order_items = order.vendororderitemstatus_set.all()
        if any(item.status != "Dispatched" for item in order_items):
            return Response({"error": "All items must be dispatched first"}, status=400)

        order.delivery_status = "Received"
        order.save()
        return Response({"message": "Order marked as received"})
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)



# Download PDF Receipt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def downloadReceipt(request, orderID):
    try:
        order = Order.objects.get(id=orderID, user=request.user)
    except Order.DoesNotExist:
        raise Http404("Order not found")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=18
    )

    elements = []
    styles = getSampleStyleSheet()

    # Custom red title style
    red_title_style = ParagraphStyle(
        'RedTitle',
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        alignment=1,  # 0=left, 1=center
        textColor=colors.red,
    )

    # Title
    elements.append(Paragraph("Payment Receipt", red_title_style))
    elements.append(Spacer(1, 12))

    # Horizontal red line
    elements.append(
        Table(
            [['']],
            colWidths=[400],
            hAlign='CENTER'
        ).setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (0, 0), 0.5, colors.red),
        ]))
    )
    elements.append(Spacer(1, 20))

    # Common table style
    common_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
    ])

    billing = order.billing_details

    # Order Details Table
    order_info = [
        ['Order ID:', str(order.id)],
        ['Date:', order.created_at.strftime('%Y-%m-%d %H:%M')],
        ['Status:', order.order_status.title()],
        ['Payment Status:', order.payment_status],
        ['Transaction ID:', order.transaction_id or 'N/A'],
        ['Payment Reference (pidx):', order.pidx or 'N/A'],
        ['Name:', billing.get('name')],
        ['Phone:', billing.get('mobile')],
    ]
    order_table = Table(order_info, hAlign='LEFT', colWidths=[140, 350])
    order_table.setStyle(common_style)

    elements.append(Paragraph("<strong>Order Details</strong>", styles['Heading3']))
    elements.append(Spacer(1, 6))
    elements.append(order_table)
    elements.append(Spacer(1, 20))

    # Order Items Table
    item_data = [['Product', 'Quantity', 'Price', 'Subtotal']]
    for item in order.cart_items:
        price = float(item['price'])
        quantity = int(item['quantity'])
        subtotal = price * quantity
        item_data.append([
            item['productName'],
            str(quantity),
            f"${price:.2f}",
            f"${subtotal:.2f}"
        ])

    # Total row
    item_data.append([
        'Total (Includes tax & shipping)', '', '', f"${order.total_amount:.2f}"
    ])

    item_table = Table(item_data, hAlign='LEFT', colWidths=[200, 60, 70, 80])
    item_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.grey),
        ('INNERGRID', (0, 0), (-1, -2), 0.25, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    ])
    item_table.setStyle(item_table_style)

    elements.append(Paragraph("<strong>Order Items</strong>", styles['Heading3']))
    elements.append(Spacer(1, 6))
    elements.append(item_table)

    # Signature section
    elements.append(Spacer(1, 60))
    elements.append(Paragraph("Authorized Signature (DCart):", styles['Normal']))
    elements.append(Spacer(1, 12))

    signature_line = Table(
        [['']],
        colWidths=[120],
        hAlign='LEFT'
    )
    signature_line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (0, 0), 0.5, colors.black),
    ]))
    elements.append(signature_line)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("<i>Thank you for your purchase!</i>", styles['Italic']))

    # Final build
    doc.build(elements)
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename=f"Order_{order.id}_Receipt.pdf")
