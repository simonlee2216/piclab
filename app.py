import os
from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from PIL import Image, ImageEnhance
import io
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)

# Set up SQLite as the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # SQLite database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder to store uploaded images
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['JWT_SECRET_KEY'] = 'secret'  # Change this in production

# Initialize database and JWT manager
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Define the User model for authentication
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

# Define the Image model
class ImageMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), unique=True, nullable=False)
    size = db.Column(db.String(120), nullable=False)
    format = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"ImageMetadata('{self.filename}', '{self.size}', '{self.format}')"

# Create the database tables before the first request
@app.before_first_request
def create_tables():
    db.create_all()

# User Registration Route
@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Check if the user already exists
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    # Create a new user
    new_user = User(username=username, email=email, password=password)  # Add hashed password in production
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201

# User Login Route
@app.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # Check if user exists and password matches
    user = User.query.filter_by(username=username).first()
    if not user or user.password != password:  # Add password hashing in production
        return jsonify({'error': 'Invalid credentials'}), 401

    # Create JWT token
    access_token = create_access_token(identity=username)
    return jsonify({'access_token': access_token}), 200

# Check if the file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Image Upload Route
@app.route('/upload', methods=['POST'])
@jwt_required  
def upload_image():
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

        new_image = ImageMetadata(filename=filename, size=size, format=format)
        db.session.add(new_image)
        db.session.commit()

        return jsonify({'message': 'File uploaded successfully', 'filename': filename}), 201

    return jsonify({'error': 'Invalid file type'}), 400

# Image Processing Route: Resize
@app.route('/resize/<filename>', methods=['GET'])
@jwt_required  
def resize_image(filename):
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = Image.open(filepath)

    # Resize image (e.g., to 200x200)
    img = img.resize((200, 200))
    img.save(filepath)

    return jsonify({'message': f'Image {filename} resized to 200x200'}), 200

# Image Processing Route: Rotate
@app.route('/rotate/<filename>', methods=['GET'])
@jwt_required 
def rotate_image(filename):
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = Image.open(filepath)

    # Rotate image by 90 degrees
    img = img.rotate(90)
    img.save(filepath)

    return jsonify({'message': f'Image {filename} rotated by 90 degrees'}), 200

# Image Processing Route: Adjust Brightness
@app.route('/adjust_brightness/<filename>', methods=['GET'])
@jwt_required  
def adjust_brightness(filename):
    image = ImageMetadata.query.filter_by(filename=filename).first()
    if not image:
        return jsonify({'error': 'Image not found'}), 404

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img = Image.open(filepath)

    # Adjust brightness (1.0 is original brightness)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.5)  # Increase brightness by 50%
    img.save(filepath)

    return jsonify({'message': f'Image {filename} brightness adjusted'}), 200

@app.route('/view_users', methods=['GET'])
@jwt_required  
def view_users():
    users = User.query.all()
    return jsonify([{'id': user.id, 'username': user.username, 'email': user.email} for user in users])

# View uploaded images metadata
@app.route('/view_images', methods=['GET'])
@jwt_required  
def view_images():
    images = ImageMetadata.query.all()
    if not images:
        return jsonify({'message': 'No images uploaded yet'}), 404
    
    # Format and return the image metadata as a list of dictionaries
    return jsonify([{
        'id': image.id,
        'filename': image.filename,
        'size': image.size,
        'format': image.format
    } for image in images]), 200
  

# Route to serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Home route
@app.route('/')
def home():
    return "Welcome to the Flask Image Processing App!"

if __name__ == '__main__':
    app.run(debug=True)
