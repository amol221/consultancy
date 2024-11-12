from flask import Blueprint, request, jsonify
from .models import Notification, db, User, PDF, Video, Subscription
from .notifications import send_whatsapp_notification
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash


from twilio.rest import Client


from flask import send_file

main = Blueprint('main', __name__)

# Define base directory (path to the 'backend' folder)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # Gets you to the backend directory
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')  # Now points to backend/uploads

# Ensure that the uploads directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
# Allowable file types
ALLOWED_EXTENSIONS = {'pdf', 'mp4', 'avi', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route('/register', methods=['POST'])
def register():
    data = request.json
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')

    # Check if the email is one of the specific ones to assign 'admin' role
    role = 'admin' if data['email'] in ['admissionfirst7@gmail.com', 'patilamol1045@gmail.com'] else 'user'

    # Create a new user object with the assigned role
    user = User(
        email=data['email'],
        fname=data['fname'],
        lastname=data['lastname'],
        mobile_number=data['mobile_number'],
        password=hashed_password,  # Store the hashed password
        age=data.get('age'),
        education=data.get('education'),
        city=data['city'],
        state=data['state'],
        role=role  # Assign the role here
    )
    
    # Add the user to the database
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201




from flask import session

@main.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        # Save user ID in the session
        session['user_id'] = user.id
        user_data = {
            "fname" : user.fname,
            "role": user.role,
            "id":user.id, }
        return jsonify(user_data), 200
    else:
        return jsonify({'message': 'Invalid email or password'}), 401



@main.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear the session to log out the user
    return jsonify({'message': 'Logged out successfully'}), 200


@main.route('/update-transaction', methods=['POST'])
def update_transaction():
    data = request.json

    # Find the user by id
    user = User.query.filter_by(id=data['id']).first()
    
    # Find the subscription by name (use 'subscription' instead of 'subscription_name')
    subscription = Subscription.query.filter_by(title=data['subscription']).first()
    
    if not user:
        return jsonify({'message': 'User not found'}), 402
    
    if not subscription:
        return jsonify({'message': 'Subscription not found'}), 404

    # Update the transaction ID and subscription ID for the user
    user.transaction_id = data['transaction_id']
    user.subscription_id = subscription.id
    user.subscription_status = "pending Approval"
    
    # Commit the changes to the database
    db.session.commit()

    # Optionally notify admin via WhatsApp using Twilio (commented out)
    # send_whatsapp_notification(user.email, data['transaction_id'])

    return jsonify({'message': 'Transaction ID updated'}), 200



@main.route('/admin_dashboard', methods=['GET'])
def admin_dashboard():
    # Get total number of users
    total_users = User.query.count()

    # Get number of users with premium subscription
    total_premium_users = User.query.filter(User.role == 'premium').count()

    # Get users with transactions pending approval (i.e., with a transaction ID but not premium)
    pending_requests = User.query.filter(User.transaction_id.isnot(None), User.role == 'user').all()
    pending_requests_list = [
        {
            'id': user.id,
            'email': user.email,
            'transaction_id': user.transaction_id,
            'subscription': user.subscription.title if user.subscription else "No subscription"  # Get subscription name
        }
        for user in pending_requests
    ]
    
    # Get number of users with no subscription
    total_non_subscribers = User.query.filter(User.subscription_id.is_(None)).count()

    # Prepare data for the admin dashboard
    dashboard_data = {
        'total_users': total_users,
        'total_premium_users': total_premium_users,
        'pending_requests': pending_requests_list,
        'total_non_subscribers': total_non_subscribers
    }
    try:
        return jsonify(dashboard_data), 200
    
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500






# Twilio configuration
TWILIO_PHONE_NUMBER = 'whatsapp:+14155238886'  # Your Twilio WhatsApp-enabled number
TWILIO_ACCOUNT_SID = 'AC2dc18628d0ad8e62b267c84195aa6719'
TWILIO_AUTH_TOKEN = 'a65f61c4a4cba4f17b790700dbd8de23'

# Create a Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)




@main.route('/admin/send_notification', methods=['POST'])
def send_notification():
    # Extract form data
    data = request.json  # Get JSON data
    message = data.get('message')
    subscription_name = data.get('subscription')  # Get subscription name instead of ID

    if not message or not subscription_name:
        return jsonify({'message': 'Message and subscription name must be provided!'}), 400

    # Get the selected subscription by name
    subscription = Subscription.query.filter_by(title=subscription_name).first()
    if not subscription:
        return jsonify({'message': 'Subscription not found!'}), 404

    # Get all users subscribed to the selected subscription
    users = User.query.filter_by(subscription_id=subscription.id).all()

    if not users:
        return jsonify({'message': 'No users found for the selected subscription!'}), 404

    # Create a notification for each user and send a WhatsApp message
    for user in users:
        new_notification = Notification(
            user_id=user.id,
            subscription_id=subscription.id,
            notification_type=subscription.title,
            message=message
        )
        db.session.add(new_notification)

        # Send WhatsApp message to the user
        # Default country code for India
        DEFAULT_COUNTRY_CODE = '+91'
        if user.mobile_number:  # Make sure user has a valid WhatsApp number
            try:
                if not user.mobile_number.startswith('+'):
                    # If not, prepend the default country code (e.g., +91 for India)
                    user.mobile_number = DEFAULT_COUNTRY_CODE + user.mobile_number.lstrip('0')  # Remove leading zero if exists
                
                # Send the WhatsApp message using Twilio
                twilio_client.messages.create(
                    body=message,
                    from_=TWILIO_PHONE_NUMBER,
                    to=f'whatsapp:{user.mobile_number}'  # User's WhatsApp number
                )
            except Exception as e:
                db.session.rollback()  # Rollback if message fails
                return jsonify({'message': f'Error sending WhatsApp message: {str(e)}'}), 500

    db.session.commit()

    return jsonify({'message': f'Notifications sent to users subscribed to {subscription.title}'}), 200


@main.route('/user/notifications/<user_id>', methods=['GET'])
def get_user_notifications(user_id):
    # data = request.json
    # user_id = data['user_id']  # Get the logged-in user ID from the session
    if not user_id:
        return jsonify({'message': 'User not logged in'}), 401

    notifications = Notification.query.filter_by(user_id=user_id).all()

    notifications_list = [{
        'message': notification.message,
        'is_read': notification.is_read,
        'subscription': notification.subscription.title if notification.subscription else "No subscription"
    } for notification in notifications]

    return jsonify(notifications_list), 200




@main.route('/admin/add_documents/<string:subscription_name>', methods=['POST'])
def add_documents(subscription_name):
    # Ensure the subscription exists
    subscription = Subscription.query.filter_by(title=subscription_name).first()

    if not subscription:
        return jsonify({'message': 'Subscription not found'}), 404

    # Check if a file was included in the request
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    # Retrieve the file type from the form data
    file_type = request.form.get('file_type')
    if not file_type:
        return jsonify({'message': 'File type not provided'}), 400

    # Check if the file type is allowed and the file itself is valid
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        # Save the file to the database under the given subscription
        new_file = PDF(file_path=file_path, pdf_type=file_type, subscription_id=subscription.id)

        db.session.add(new_file)
        db.session.commit()

        return jsonify({'message': 'Document uploaded successfully'}), 201

    return jsonify({'message': 'File type not allowed'}), 400


# Route for serving documents
@main.route('/get_documents/<string:pdf_type>/<int:user_id>', methods=['GET'])
def get_docs(pdf_type, user_id):
    print("in get docs function")
    if not user_id:
        return jsonify({'message': 'User not logged in'}), 401

    # Fetch the user from the database
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Check if the user has a subscription
    if not user.subscription_id:
        return jsonify({'message': 'User does not have a valid subscription'}), 403

    # Find the PDF document that matches the subscription and pdf_type
    document = PDF.query.filter_by(subscription_id=user.subscription_id, pdf_type=pdf_type).first()

    if not document:
        return jsonify({'message': 'No document found for this type and subscription'}), 404

    # Correct the file path by ensuring it's absolute
    file_path = os.path.abspath(document.file_path)

    # Check if the document file exists
    print(file_path)
    if not os.path.exists(file_path):
        return jsonify({'message': 'File not found'}), 404

    # Serve the document for download
    return send_file(file_path, as_attachment=True)

@main.route('/get-subscriptions', methods=['GET'])
def get_all_subscriptions():
    subscriptions = Subscription.query.all()
    
    # Prepare the subscription data
    subscription_list = [
        {
            'id': subscription.id,
            'heading': subscription.heading,
            'title': subscription.title,
            'validity': subscription.validity,
            'price': subscription.price,
            'course_offered': subscription.course_offered,
            'type': subscription.type
        }
        for subscription in subscriptions
    ]

    return jsonify(subscription_list), 200


@main.route('/add-subscription', methods=['POST'])
def add_new_subscription():
    data = request.json

    # Validate input data
    if not all(key in data for key in ( 'title', 'price', 'course_offered')):
        return jsonify({'message': 'Missing required fields'}), 400

    # Create a new Subscription instance
    new_subscription = Subscription(
        heading=data.get('heading'),
        title=data.get('title'),
        validity=data.get('validity'),
        price=data['price'],
        course_offered=data['course_offered'],
        type=data.get('type', 'basic')  # Default to 'basic' if not provided
    )
    
    # Add and commit the new subscription to the database
    db.session.add(new_subscription)
    db.session.commit()
    
    return jsonify({'message': 'Subscription added successfully'}), 201


@main.route('/update-subscription/<string:subscription>', methods=['PUT'])
def update_subscription(subscription):
    data = request.json
    subscription = Subscription.query.filter_by(title=subscription).first()

    if not subscription:
        return jsonify({'message': 'Subscription not found'}), 404

    # Update subscription details
    subscription.heading = data.get('heading', subscription.heading)
    subscription.title = data.get('title', subscription.title)
    subscription.validity = data.get('validity', subscription.validity)
    subscription.price = data.get('price', subscription.price)
    subscription.course_offered = data.get('course_offered', subscription.course_offered)
    subscription.type = data.get('type', subscription.type)

    db.session.commit()
    return jsonify({'message': 'Subscription updated successfully'}), 200


import os

@main.route('/delete-subscription/<string:subscription>', methods=['DELETE'])
def delete_subscription(subscription):
    # Query the subscription by title
    subscription = Subscription.query.filter_by(title=subscription).first()

    if not subscription:
        return jsonify({'message': 'Subscription not found'}), 404

    # Delete associated PDF and Video files from the filesystem
    for pdf in subscription.pdfs:
        try:
            os.remove(pdf.file_path)
        except OSError as e:
            print(f"Error deleting PDF file {pdf.file_path}: {e}")

    for video in subscription.videos:
        try:
            os.remove(video.file_path)
        except OSError as e:
            print(f"Error deleting Video file {video.file_path}: {e}")

    # Delete the subscription from the database
    db.session.delete(subscription)
    db.session.commit()
    
    return jsonify({'message': 'Subscription and associated files deleted successfully'}), 200



# handle user request
@main.route('/admin/approve-transaction', methods=['POST'])
def approve_transaction():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if data['approved']:
        user.role = 'premium'
    else:
        user.role = 'user'
        user.subscription_id = None
        user.transaction_id = None

    db.session.commit()
    return jsonify({'message': 'Transaction status updated'}), 200





# user dashboard
@main.route('/user_profile/<user_id>', methods=['GET', 'PUT'])
def user_detail(user_id):
    # user_id = session.get('user_id')  # Get the user ID from session
    if not user_id:
        return jsonify({'message': 'User not logged in'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    if request.method == 'GET':
        user_details = {
            'fname': user.fname,
            'lastname': user.lastname,
            'email': user.email,
            'mobile_number': user.mobile_number,
            'age': user.age,
            'education': user.education,
            'city': user.city,
            'state': user.state,
            'role': user.role,
            'subscription': user.subscription.title if user.subscription else 'None',
            'subscription_status': 'currently You don\'t have any subscription' if user.role != 'premium' and user.transaction_id == None else 'Active',
        }
        return jsonify(user_details), 200

    elif request.method == 'PUT':
        data = request.json
        user.fname = data.get('fname', user.fname)
        user.lastname = data.get('lastname', user.lastname)
        user.age = data.get('age', user.age)
        user.education = data.get('education', user.education)
        user.city = data.get('city', user.city)
        user.state = data.get('state', user.state)
        db.session.commit()

        return jsonify({'message': 'User details updated successfully'}), 200



    # basic deatils / edit basic details
    # list of subscription plans if pending show profile under review
    # reject your request has been rejected ani please enter transaction id again

@main.route('/get-resources/<int:user_id>/<string:subscription>', methods=['GET'])
def get_resources(user_id, subscription):
    # Fetch the user by their ID
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message' : 'User not found'}), 404

    # Check if the user is subscribed to the provided subscription name
    if not user.subscription or user.subscription.name != subscription:
        return jsonify({'message': 'User does not have access to this subscription'}), 403

    # Fetch resources for the subscription
    pdfs = PDF.query.filter_by(subscription_id=user.subscription_id).all()
    videos = Video.query.filter_by(subscription_id=user.subscription_id).all()

    return jsonify({
        'pdfs': [pdf.file_path for pdf in pdfs],
        'videos': [video.file_path for video in videos]
    }), 200




from flask import request, jsonify
import smtplib
import random
import string

@main.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    
    if user:
        # Generate a random token
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
        
        # Save the token and its expiration (optional)
        user.reset_token = token
        db.session.commit()
        
        # Send email (set up your email server)
        send_reset_email(user.email, token)
        
        return jsonify({'success': True, 'message': 'Password reset email sent.'}), 200
    
    return jsonify({'success': False, 'error': 'Email not found.'}), 404

def send_reset_email(email, token):
    # Configure your email settings
    smtp_server = 'smtp.example.com'
    smtp_port = 587
    smtp_user = 'your-email@example.com'
    smtp_password = 'your-email-password'

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        
        subject = "Password Reset Request"
        body = f"To reset your password, click the link: http://yourdomain.com/reset-password/{token}"
        message = f"Subject: {subject}\n\n{body}"
        
        server.sendmail(smtp_user, email, message)


@main.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    data = request.json
    user = User.query.filter_by(reset_token=token).first()
    
    if user:
        if 'new_password' not in data:
            return jsonify({'success': False, 'error': 'New password required.'}), 400
        
        hashed_password = generate_password_hash(data['new_password'])
        user.password = hashed_password
        user.reset_token = None  # Clear the token after use
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Password reset successfully.'}), 200
    
    return jsonify({'success': False, 'error': 'Invalid or expired token.'}), 400

   
