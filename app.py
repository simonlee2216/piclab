import os
import cv2
import numpy as np
from flask import Flask, jsonify, request, send_from_directory, render_template, url_for
from flask_cors import CORS
from sqlalchemy import Integer, ForeignKey
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageEnhance
from flask_migrate import Migrate
import io
from datetime import timedelta
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, decode_token
from flask_jwt_extended.exceptions import JWTDecodeError
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
import logging

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

CORS(app, supports_credentials=True, allow_headers=["Authorization", "Content-Type"])
load_dotenv()

# Set up SQLite as the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default_secret_key')

# Initialize database and JWT manager
db = SQLAlchemy(app)
jwt = JWTManager(app)
# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Define the User model for authentication
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    images = db.relationship('ImageMetadata', back_populates='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

# Define the Image model
class ImageMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), unique=True, nullable=False)
    size = db.Column(db.String(120), nullable=False)
    format = db.Column(db.String(120), nullable=False)
    user_id = db.Column(Integer, ForeignKey('user.id', name='fk_image_user_id'), nullable=False)
    user = db.relationship('User', back_populates='images') 

    def __repr__(self):
        return f"ImageMetadata('{self.filename}', '{self.size}', '{self.format}')"

# Create the database tables before the first request
@app.before_first_request
def create_tables():
    db.create_all()

# User Registration Route (via API)
@app.route('/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # Check if the user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400

        # Hash the password before saving
        hashed_password = generate_password_hash(password)

        # Create a new user with the hashed password
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'User created successfully'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# User Login Route (via API)
@app.route('/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # Check if user exists
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):  # Check if the hashed password matches
            return jsonify({'error': 'Invalid credentials'}), 401

        # Create JWT token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(days=7),
            fresh=True)
        return jsonify({'access_token': access_token}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve Registration Page (HTML)
@app.route('/register')
def register_page():
    return render_template('register.html')

# Serve Login Page (HTML)
@app.route('/login')
def login_page():
    return render_template('login.html')
  
def verify_token(token):
    try:
        decoded_token = decode_token(token)
        return decoded_token  

    except JWTDecodeError as e:
        raise Exception(f"Token error: {str(e)}")

@app.route('/gallery')
def gallery_page():
        return render_template('gallery.html')
  
@app.route('/api/gallery', methods=['GET'])
@jwt_required
def get_gallery():
    try:
        current_user_id = get_jwt_identity()

        images = ImageMetadata.query.filter_by(user_id=current_user_id).all()

        image_data = [
            {"url": url_for('uploaded_file', filename=image.filename)} for image in images
        ]

        return jsonify({"images": image_data})
    except Exception as e:
        print(f"Error fetching gallery data: {str(e)}")
        return jsonify({"error": "Error fetching gallery data"}), 500
      
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Image Upload Route
@app.route('/upload', methods=['POST'])
@jwt_required  
def upload_image():
    current_user_id = get_jwt_identity()  # Get the current user's identity (username)
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save the file
        file.save(filepath)

        # Store metadata in the database
        img = Image.open(filepath)
        size = f"{img.width}x{img.height}"
        format = img.format

        new_image = ImageMetadata(filename=filename, size=size, format=format, user_id=user.id)
        db.session.add(new_image)
        db.session.commit()

        return jsonify({'message': 'File uploaded successfully', 'filename': filename}), 201

    return jsonify({'error': 'Invalid file type'}), 400

# Image Processing Route: Resize
@app.route('/resize/<filename>', methods=['GET'])
@jwt_required  
def resize_image(filename):
    width = request.args.get('width', type=int, default=200)
    height = request.args.get('height', type=int, default=200)
    
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = Image.open(filepath)

    # Resize image
    img = img.resize((width, height))
    img.save(filepath)

    return jsonify({'message': f'Image {filename} resized to {width}x{height}'}), 200

# Image Processing Route: Rotate
@app.route('/rotate/<filename>', methods=['GET'])
@jwt_required 
def rotate_image(filename):
    angle = request.args.get('angle', type=int, default=90)
    
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = Image.open(filepath)

    # Rotate image by the specified angle
    img = img.rotate(angle)
    img.save(filepath)

    return jsonify({'message': f'Image {filename} rotated by {angle} degrees'}), 200

# Image Processing Route: Adjust Brightness
@app.route('/adjust_brightness/<filename>', methods=['GET'])
@jwt_required  
def adjust_brightness(filename):
    factor = request.args.get('factor', type=float, default=1.5)  # Default brightness factor
    
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = Image.open(filepath)

    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(factor)  # Adjust brightness
    img.save(filepath)

    return jsonify({'message': f'Image {filename} brightness adjusted by factor {factor}'}), 200

# Image Processing Route: Apply Sharpen Filter
@app.route('/sharpen/<filename>', methods=['GET'])
@jwt_required  
def sharpen_image(filename):
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = Image.open(filepath)

    # Apply sharpen filter
    img = img.filter(ImageFilter.SHARPEN)
    img.save(filepath)

    return jsonify({'message': f'Image {filename} sharpened'}), 200

# Image Processing Route: Sobel Edge Detection
@app.route('/sobel_edge/<filename>', methods=['GET'])
@jwt_required
def sobel_edge(filename):
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)

    # Apply Sobel edge detection
    sobel_x = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
    sobel_edges = cv2.magnitude(sobel_x, sobel_y)

    # Save the result
    result_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"sobel_{filename}")
    cv2.imwrite(result_filepath, sobel_edges)

    return jsonify({'message': f'Sobel edge detection applied to {filename}', 'filename': f"sobel_{filename}"}), 200

# Image Processing Route: Canny Edge Detection
@app.route('/canny_edge/<filename>', methods=['GET'])
@jwt_required
def canny_edge(filename):
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)

    # Apply Canny edge detection
    edges = cv2.Canny(img, 100, 200)

    # Save the result
    result_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"canny_{filename}")
    cv2.imwrite(result_filepath, edges)

    return jsonify({'message': f'Canny edge detection applied to {filename}', 'filename': f"canny_{filename}"}), 200

# Image Processing Route: Histogram Equalization
@app.route('/histogram_equalization/<filename>', methods=['GET'])
@jwt_required
def histogram_equalization(filename):
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)

    # Apply histogram equalization
    equalized_img = cv2.equalizeHist(img)

    # Save the result
    result_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"equalized_{filename}")
    cv2.imwrite(result_filepath, equalized_img)

    return jsonify({'message': f'Histogram equalization applied to {filename}', 'filename': f"equalized_{filename}"}), 200

# Image Processing Route: Gaussian Blur
@app.route('/gaussian_blur/<filename>', methods=['GET'])
@jwt_required
def gaussian_blur(filename):
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = cv2.imread(filepath)

    # Apply Gaussian blur
    blurred_img = cv2.GaussianBlur(img, (15, 15), 0)

    # Save the result
    result_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"blurred_{filename}")
    cv2.imwrite(result_filepath, blurred_img)

    return jsonify({'message': f'Gaussian blur applied to {filename}', 'filename': f"blurred_{filename}"}), 200

# Image Processing Route: Perspective Transformation
@app.route('/perspective_transform/<filename>', methods=['GET'])
@jwt_required
def perspective_transform(filename):
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = cv2.imread(filepath)

    # Define points for perspective transformation (example)
    width, height = img.shape[1], img.shape[0]
    pts1 = np.float32([[50, 50], [width - 50, 50], [50, height - 50], [width - 50, height - 50]])
    pts2 = np.float32([[10, 100], [width - 10, 50], [100, height - 100], [width - 100, height - 50]])

    # Get perspective matrix
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    result_img = cv2.warpPerspective(img, matrix, (width, height))

    # Save the result
    result_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"perspective_{filename}")
    cv2.imwrite(result_filepath, result_img)

    return jsonify({'message': f'Perspective transformation applied to {filename}', 'filename': f"perspective_{filename}"}), 200


# Route to serve uploaded images with download option
@app.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Home route
@app.route('/')
def home():
    return render_template('index.html')

  
  
  
  
# Debug
@app.route('/debug/users', methods=['GET'])
def debug_users():
    users = User.query.all()
    users_list = [{'id': user.id, 'username': user.username, 'password': user.password, 'email': user.email} for user in users]
    return jsonify(users_list), 200


@app.route('/debug/images', methods=['GET'])
def debug_images():
    images = ImageMetadata.query.all()
    images_list = [{'id': img.id, 'filename': img.filename, 'size': img.size, 'format': img.format, 'user_id': img.user_id} for img in images]
    return jsonify(images_list), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)