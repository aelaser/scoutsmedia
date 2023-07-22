# Import necessary libraries
from flask import Flask, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import os
from zipfile import ZipFile
import io
import cv2
import numpy as np

# Define the upload folder and allowed extensions
UPLOAD_FOLDER = '/Users/rofilitrix/Documents/compressimages/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Set up the Flask application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize dictionary to hold the uploads
uploads = {
    'logo': None,
    'images': []
}

# Function to check if the uploaded file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to adjust the saturation of an image
def adjust_saturation(image, saturation_scale):
    image_hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype("float32")
    (h, s, v) = cv2.split(image_hsv)
    
    s = s * saturation_scale
    s = np.clip(s, 0, 255)
    
    image_hsv = cv2.merge([h, s, v])
    return cv2.cvtColor(image_hsv.astype("uint8"), cv2.COLOR_HSV2RGB)

# Function to process each image: open, adjust saturation, save, reopen, apply logo, save again
def process_image(image, filename, logo_img):
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Open image with cv2
    img = cv2.imdecode(np.frombuffer(image.read(), np.uint8), cv2.IMREAD_UNCHANGED)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert to RGB

    # Adjust saturation
    # img = adjust_saturation(img, 1.75)  # Adjust this value as needed
    img = adjust_saturation(img, 1)  # Adjust this value as needed

    # Save compressed image
    img_pil = Image.fromarray(img)
    img_pil = img_pil.convert("RGB")
    img_pil.save(image_path, "JPEG", optimize=True, quality=70)

    # Open the image file again and paste the logo onto it, then save it back to disk
    img_pil = Image.open(image_path)

    # Calculate the x, y coordinates to paste the logo at the center of the image
    x = (img_pil.width - logo_img.width) // 2
    y = (img_pil.height - logo_img.height) // 2

    img_pil.paste(logo_img, (x, y), logo_img)
    img_pil.save(image_path)

    return image_path

# Route for uploading files
@app.route('/', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        logo = request.files['logo']
        images = request.files.getlist('images')

        if logo and allowed_file(logo.filename):
            filename = secure_filename(logo.filename)
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            logo.save(logo_path)
            uploads['logo'] = logo_path

        logo_img = Image.open(uploads['logo'])

        valid_images = [(img, secure_filename(img.filename)) for img in images if img and allowed_file(img.filename)]
        uploads['images'] = [process_image(*args, logo_img) for args in valid_images]

        return redirect(url_for('download_file'))
    
    # HTML for the upload form
    return '''
    <!doctype html>
    <title>Upload Logo and Images</title>
    <h1>Upload Logo and Images</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p>Logo: <input type=file name=logo></p>
      <p>Images: <input type=file name=images multiple></p>
      <input type=submit value=Upload>
    </form>
    '''

# Route for downloading the zip file
@app.route('/download', methods=['GET'])
def download_file():
    if not uploads['logo'] or not uploads['images']:
        return "No logo or images uploaded!"

    with ZipFile(os.path.join(app.config['UPLOAD_FOLDER'], 'images_with_logo.zip'), 'w') as zipf:
        for i, image_path in enumerate(uploads['images']):
            zipf.write(image_path, arcname=os.path.basename(image_path))

    # Clear the list of images and delete them from disk
    for image_path in uploads['images']:
        os.remove(image_path)
    uploads['images'].clear()

    uploads['logo'] = None

    return send_from_directory(app.config['UPLOAD_FOLDER'], 'images_with_logo.zip')

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)
