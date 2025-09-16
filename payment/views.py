from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json
from uuid import uuid4
from django.http import JsonResponse
from django.shortcuts import redirect
from django.conf import settings
import os, requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from payment.models import PartialOrder
from orders.models import Order
from products.models import ProductSize
from rewards.models import RewardPoint
from orders.serializers import OrderSerializer
from django.core.mail import send_mail
from django.conf import settings
from cart.service import Cart
from coupons.models import Coupon, CouponUsage
from rewards.utils import increaseRewardPoints
from django.apps import apps
# Create your views here.

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initKhalti(request):
        try:
            data = json.loads(request.body)
        except Exception as e:
            return JsonResponse({'error': 'Invalid JSON', 'details': str(e)}, status=400)
        # Extract data
        billing = data.get('billingDetails', {})
        cart = data.get('cart', [])
        print(cart)
        total_amount = int(round(float(data.get('totalAmount')*100)))
        rewardPoint = data.get("rewardPoints")
        print("Reward point ya xax hai", rewardPoint)
        coupon_codes = data.get('coupon_codes', []) 
        coupons = []
        for code in coupon_codes:
            try:
                coupon = Coupon.objects.get(code=code)
                coupons.append(coupon)
            except Coupon.DoesNotExist:
                continue
        print("Cart Backend: ", cart)
        if not billing or not cart:
            return JsonResponse({'error': 'Missing billing or cart data'}, status=400)
        if len(cart) == 1:
            purchase_order_name = cart[0].get('productName', 'Product')
        else:
            purchase_order_name = f"{billing.get('name')}'s order ({len(cart)} items)"
        url = os.getenv("KHALTI_URL") 
        return_url = os.getenv("KHALTI_RETURN_URL") 
        # return_url = 'http://localhost:3000/paymentverify/'
        transaction_id = str(uuid4())  # Generate a unique transaction ID
        payload = json.dumps({
            "return_url": return_url,
            "website_url": return_url,
            "amount": total_amount,
            "purchase_order_id": transaction_id,
            "purchase_order_name": purchase_order_name,
            "transaction_id": transaction_id,
            "customer_info": {
                "name": billing.get('name'),
                "email": billing.get('email'),
                "phone": billing.get('mobile'),
            },
           
        })
        KHALTI_KEY = os.getenv("KHALTI_SECRET_KEY") 
        print(payload)
        print(KHALTI_KEY)
        headers = {
            'Authorization': f'Key {KHALTI_KEY}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(url, headers=headers, data=payload, timeout=10)
            new_res = response.json()
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': 'Failed to connect to Khalti', 'details': str(e)}, status=503)

        print("Khalti API Response:", new_res)

        if response.status_code == 200 and 'payment_url' in new_res:
            partial_order = PartialOrder.objects.create(
                transaction_id=transaction_id,
                pidx=new_res.get('pidx'),
                payment_url=new_res.get('payment_url'),
                expires_at=new_res.get('expires_at'),
                cart=cart,
                billing_name=billing.get('name', ''),
                billing_email=billing.get('email', ''),
                billing_phone=billing.get('mobile', ''),
                billing_address=billing.get('address', ''),
                billing_city=billing.get('city', ''),
                total_amount=total_amount,
                reward_points_used=rewardPoint or 0
            )
            for coupon in coupons:
                partial_order.coupons.add(coupon)
            partial_order.save()
            print("Partial Order Created:", partial_order.id)
            print("Partial Order Created:", partial_order)
            return Response({
                "message": "Khalti Response Received",
                "data": new_res
            }, status=status.HTTP_200_OK)
        else:
            return JsonResponse({'error': 'Failed to initiate payment', 'details': new_res}, status=400)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def verifyKhalti(request):
    url = os.getenv("KHALTI_VERIFY_URL")
    KHALTI_KEY = os.getenv("KHALTI_SECRET_KEY")
    headers = {
        'Authorization': f'Key {KHALTI_KEY}',
        'Content-Type': 'application/json',
    }

    pidx = request.GET.get('pidx')
    transaction_id = request.GET.get('transaction_id')
    purchase_order_id = request.GET.get('purchase_order_id')
    total_amount = request.GET.get('total_amount')

    if not pidx:
        return JsonResponse({"success": False, "message": "Missing pidx"}, status=400)

    data = json.dumps({'pidx': pidx})

    try:
        res = requests.post(url, headers=headers, data=data)
        lookup_data = res.json()
        print("Khalti response:", lookup_data)

        if lookup_data.get("status") == "Completed":
            try:
                current_user = request.user
                if current_user.is_authenticated:
                    print(f"User Id: {current_user.id}")

                partial_order = PartialOrder.objects.get(pidx=pidx)

                # Create order directly
                order_data = Order.objects.create(
                    user=current_user,
                    pidx=pidx,
                    transaction_id=transaction_id,
                    billing_details={
                        "name": partial_order.billing_name,
                        "email": partial_order.billing_email,
                        "mobile": partial_order.billing_phone,
                        "address": partial_order.billing_address,
                        "city": partial_order.billing_city
                    },
                    cart_items=partial_order.cart,
                    total_amount=total_amount,
                    payment_status='Paid',
                    order_status='completed'
                )

                # Deduct reward points if applied
                if getattr(partial_order, "reward_points_used", 0) > 0:
                    try:
                        reward_obj = RewardPoint.objects.get(user=current_user)
                        reward_obj.redeemedPoints += partial_order.reward_points_used
                        reward_obj.save()
                    except RewardPoint.DoesNotExist:
                        pass

                # Add new earned points
                increaseRewardPoints(current_user, int(total_amount)/100)

                # Handle coupons
                for coupon in partial_order.coupons.all():
                    CouponUsage.objects.create(user=current_user, coupon=coupon)
                    coupon.used_count += 1
                    coupon.save()

                # Send confirmation email
                try:
                    send_confirmation_email(partial_order.billing_email, partial_order.billing_name)
                except Exception as email_err:
                    print("Error sending email:", email_err)

                # VendorOrderItemStatus creation
                VendorOrderItemStatus = apps.get_model('vendors', 'VendorOrderItemStatus')
                Product = apps.get_model('products', 'Product')

                for item in partial_order.cart:
                    product_id = item.get('productID')
                    quantity = item.get('quantity')

                    try:
                        product = Product.objects.get(id=product_id)
                        vendor = product.vendor

                        VendorOrderItemStatus.objects.create(
                            vendor=vendor,
                            order=order_data,
                            product=product,
                            quantity=quantity,
                            price=product.originalPrice,
                            status='Pending'
                        )
                        print(f"VendorOrderItemStatus created for product {product_id}")
                    except Product.DoesNotExist:
                        print(f"Product with ID {product_id} not found — skipping.")

                # Deduct stock quantity
                for item in order_data.cart_items:
                    product_id = item.get("productID")
                    quantity = int(item.get("quantity"))
                    has_sizes = item.get("has_sizes", False)
                    selected_size = item.get("selected_size")  # may be None

                    try:
                        product = Product.objects.get(id=product_id)

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
                        print(
                            f"Product with ID {product_id} not found — skipping stock deduction."
                        )

                # Delete the partial order
                partial_order.delete()

                return JsonResponse({
                    "success": True,
                    "message": "Payment verified",
                    "data": lookup_data
                })

            except PartialOrder.DoesNotExist:
                return JsonResponse({"success": False, "message": "Partial order not found"}, status=404)

        else:
            return JsonResponse({
                "success": False,
                "message": "Payment not completed",
                "data": lookup_data
            })

    except Exception as e:
        print("Error during verification:", str(e))
        return JsonResponse({"success": False, "message": "Verification error"}, status=500)


import hmac
import hashlib
import base64

def generate_signature(secret_key, signed_field_names, data_dict):
    message = ",".join(f"{field}={data_dict[field]}" for field in signed_field_names.split(","))
    signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode()



@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initEsewa(request):
    try:
        data = json.loads(request.body)
    except Exception as e:
        return JsonResponse({'error': 'Invalid JSON', 'details': str(e)}, status=400)

    #For development this url
    # request_url = "https://rc-epay.esewa.com.np/api/epay/main/v2/form"
    #For production this url
    # request_url = "https://epay.esewa.com.np/api/epay/main/v2/form"
    tax_amount = data.get('taxAmount')
    amount = data.get('amount')
    total_amount = data.get('totalAmount')
    billing = data.get('billingDetails', {})
    cart = data.get('cart', [])
    if not billing or not cart or not total_amount:
        return JsonResponse({'error': 'Missing billing, cart, or total amount'}, status=400)

    coupon_codes = data.get('coupon_codes', []) 
    coupons = []
    for code in coupon_codes:
        try:
            coupon = Coupon.objects.get(code=code)
            coupons.append(coupon)
        except Coupon.DoesNotExist:
            continue

    # product_code = "EPAYTEST"  # Use actual code in prod
    transaction_uuid = str(uuid4())
    signed_field_names = "total_amount,transaction_uuid,product_code"

    request_data = {
        "amount": str(total_amount),
        "tax_amount": str(data.get('tax_amount', '0')),
        "total_amount": str(total_amount),
        "transaction_uuid": transaction_uuid,
        "product_code": "EPAYTEST",
        "product_service_charge": "0",
        "product_delivery_charge": "0",
        "success_url": "http://localhost:3000/esewaverify",
        "failure_url": "http://developer.esewa.com.np/failure",
        "signed_field_names": signed_field_names,
    }
    ESEWA_KEY = os.getenv("ESEWA_SECRET_KEY") 
    secret_key = ESEWA_KEY
    signature = generate_signature(secret_key, signed_field_names, request_data)
    request_data["signature"] = signature
    print(request_data)


     # Save Partial Order
    partial_order = PartialOrder.objects.create(
        transaction_id=transaction_uuid,
        pidx=None,  # Not used by eSewa
        payment_url="https://rc-epay.esewa.com.np/api/epay/main/v2/form",
        expires_at=None,  # eSewa doesn’t provide expiry
        cart=cart,
        billing_name=billing.get('name', ''),
        billing_email=billing.get('email', ''),
        billing_phone=billing.get('mobile', ''),
        billing_address=billing.get('address', ''),
        billing_city=billing.get('city', ''),
        total_amount=total_amount
    )
    for coupon in coupons:
        partial_order.coupons.add(coupon)
    partial_order.save()
    print("Partial eSewa Order Created:", partial_order.id)


    return Response({
        "form_url": "https://rc-epay.esewa.com.np/api/epay/main/v2/form",
        "data": request_data
    })




@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verifyEsewa(request):
    print("Verify ma chai aayo hai ta")
    data = request.data
    print("Verify data", data)

    transaction_uuid = data.get("transaction_uuid")
    transaction_code = data.get("transaction_code")
    status = data.get("status")
    total_amount = float(data.get("total_amount", 0))

    if not transaction_uuid or not transaction_code or not status:
        return JsonResponse({"success": False, "message": "Missing required fields"}, status=400)

    try:
        # Get the stored partial order by transaction_uuid
        partial_order = PartialOrder.objects.get(transaction_id=transaction_uuid)

        if status == "COMPLETE":
            # Finalize order
            current_user = request.user
            if current_user.is_authenticated:
                print(f"User Id lamsal: {current_user.id}")
            final_order = Order.objects.create(
                user=current_user,
                pidx=transaction_uuid,
                transaction_id=transaction_code,
                billing_details={
                        "name": partial_order.billing_name,
                        "email": partial_order.billing_email,
                        "mobile": partial_order.billing_phone,
                        "address":partial_order.billing_address,
                        "city":partial_order.billing_city
                },
                cart_items=partial_order.cart,
                total_amount=total_amount,
                payment_status='Paid',
                order_status='completed'
            )
            
            # Add VendorOrderItemStatus for each product
            VendorOrderItemStatus = apps.get_model('vendors', 'VendorOrderItemStatus')
            Product = apps.get_model('products', 'Product')
 
            for item in partial_order.cart:
                product_id = item.get('productID')
                quantity = item.get('quantity')

                try:
                    product = Product.objects.get(id=product_id)
                    vendor = product.vendor

                    VendorOrderItemStatus.objects.create(
                        vendor=vendor,
                        order=final_order,
                        product=product,
                        quantity=quantity,
                        price=product.originalPrice,
                        status='Pending'
                    )
                    print(f"VendorOrderItemStatus created for product {product_id}")

                except Product.DoesNotExist:
                    print(f"Product with ID {product_id} not found — skipping.")



            # Deduct stock quantity for each purchased item
            for item in final_order.cart_items:
                    product_id = item.get("productID")
                    quantity = int(item.get("quantity"))
                    has_sizes = item.get("has_sizes", False)
                    selected_size = item.get("selected_size")  # may be None

                    try:
                        product = Product.objects.get(id=product_id)

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
                        print(
                            f"Product with ID {product_id} not found — skipping stock deduction."
                        )

            ## cupon logic
            for coupon in partial_order.coupons.all():
                        CouponUsage.objects.create(user=request.user, coupon=coupon)
                        coupon.used_count += 1
                        coupon.save()

           # Add reward points to user
            increaseRewardPoints(current_user,final_order.total_amount)
            
            send_confirmation_email(partial_order.billing_email, partial_order.billing_name)
            # Optionally delete the partial order
            partial_order.delete()

            return JsonResponse({
                "success": True,
                "message": "Order confirmed",
                "order_id": final_order.id
            })

        else:
            return JsonResponse({
                "success": False,
                "message": f"Payment status is not complete: {status}"
            }, status=400)

    except PartialOrder.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Partial order not found"
        }, status=404)





def send_confirmation_email(to_email, user_name):
    subject = 'Order Confirmation - Thank You for Your Purchase!'
    message = f'''
    Dear {user_name},

    Your order has been successfully placed and the payment has been verified.

    For invoice, check the orders page in your dashboard and download the receipt. 
    
    Thank you for shopping with us!
    '''
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )
    print("Confirmation email sent.")