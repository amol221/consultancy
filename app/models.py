from . import db
from datetime import datetime

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(50), nullable=False)  # First name
    lastname = db.Column(db.String(50), nullable=False)  # Last name
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile_number = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')
    age = db.Column(db.Integer)
    education = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'))  # Foreign key to Subscription
    transaction_id = db.Column(db.String(100))
    reset_token = db.Column(db.String(20), nullable=True)
    subscription_timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp for subscription
    notifications = db.relationship('Notification', backref='user', lazy=True)
    subscription = db.relationship('Subscription', back_populates='users')  # Link to Subscription

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    heading = db.Column(db.String(100), nullable=True)  # New field
    title = db.Column(db.String(100), nullable=True)    # New field
    validity = db.Column(db.String(50), nullable=True)   # New field
    price = db.Column(db.Float, nullable=False)
    course_offered = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='basic')
    # Set cascade behavior for related objects
    users = db.relationship('User', back_populates='subscription')
    pdfs = db.relationship('PDF', backref='subscription', lazy=True, cascade="all, delete-orphan")
    videos = db.relationship('Video', backref='subscription', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='subscription', lazy=True, cascade="all, delete-orphan")
    course_links = db.relationship('CourseLink', back_populates='subscription', cascade="all, delete-orphan")

class PDF(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pdf_type = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'))

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(255), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'))

class CourseLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)  # Display name for the link
    url = db.Column(db.String(255), nullable=False)   # The actual URL of the link
    subscription = db.relationship('Subscription', back_populates='course_links')


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription.id'), nullable=True)  # Foreign key to Subscription
    notification_type = db.Column(db.String(100), nullable=False)  # Usually the Subscription name or other types
    message = db.Column(db.Text, nullable=False)  # Message content
    is_read = db.Column(db.Boolean, default=False)  # Whether the user has read the notification
