from flask import Flask, request, jsonify, render_template_string, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import desc
import os
import base64
from PIL import Image
from io import BytesIO
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
import markdown
import re

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

STATIC_FOLDER = os.path.join(os.getcwd(), 'static', 'images')
THUMBNAIL_SIZE = (200, 200)  # Define thumbnail size

# Ensure the static image folder exists
os.makedirs(STATIC_FOLDER, exist_ok=True)

def convert_html(value):
    print("Value:", value)

    # Check if any line starts with Markdown elements
    markdown_patterns = [
        r"^# ",       # Heading 1-6 (#, ##, ###, etc.)
        r"^- ",       # Unordered list (- item)
        r"^\* ",      # Unordered list (* item)
        r"^\d+\. ",   # Ordered list (1., 2., 3., etc.)
        r"^> ",       # Blockquote (> quote)
        r"^```",      # Code block (```)
        r"^\*{1,2}[^ ]",  # Bold/italic without spaces (*bold*, **bold**)
        r"^_+[^ ]",       # Underscore-based formatting (_italic_, __bold__)
    ]

    if any(re.search(pattern, value, re.MULTILINE) for pattern in markdown_patterns):
        return markdown.markdown(value)

    # If no Markdown syntax at the start of lines, format sections properly
    formatted_value = ""
    paragraphs = value.strip().split("\n\n")  # Split sections by double newlines

    for paragraph in paragraphs:
        lines = paragraph.split("\n")  # Split within sections
        formatted_value += "<p>" + "<br>".join(lines) + "</p>\n"

    return formatted_value.strip()

# Register the filter
app.jinja_env.filters['convert_html'] = convert_html

# Resources Table
class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False, unique=True)
    post_body = db.Column(db.Text)
    post_summary = db.Column(db.String(500))
    main_image = db.Column(db.String(500))
    thumbnail_image = db.Column(db.String(500))
    featured = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(50))
    col_span = db.Column(db.Integer, default=1)
    topic = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cms_link = db.Column(db.String(500))
    field_type = db.Column(db.String(500))
    link = db.Column(db.String(500))
    report_file = db.Column(db.Text)

    def generate_cms_link(self):
        return f"/cms/resource/{self.slug}"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'post_body': self.post_body,
            'post_summary': self.post_summary,
            'main_image': self.main_image,
            'thumbnail_image': self.thumbnail_image,
            'featured': self.featured,
            'color': self.color,
            'col_span': self.col_span,
            'topic': self.topic,
            'created_at': self.created_at.isoformat(),
            'cms_link': self.cms_link,
            'field_type': self.field_type,
            'link': self.link,
            'report_file' : self.report_file
        }



# Jobs Table
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cms_link = db.Column(db.String(500))

    def generate_cms_link(self):
        return f"/cms/job/{str(self.id)}"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'cms_link': self.cms_link
        }
    

# Basic CMS template
CMS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ item.name }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background-color: #f8f9fa;
            padding-top: 100px;
            margin: 0;
        }

        .navbar {
            background-color: #005c38;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            padding: 10px 20px;
        }

        .navbar-brand span {
            font-weight: 600;
            font-size: 20px;
        }

        .navbar a {
            color: #fff;
            text-decoration: none;
        }

        .content {
            width: 100%;
            background: #fff;
            padding: 20px;
            border-radius: 0;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        .header h1 {
            color: #005c38;
            margin-bottom: 10px;
        }

        .metadata {
            color: #666;
            margin: 10px 0;
            font-size: 14px;
        }

        .image-container {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-top: 20px;
        }

        .image-container img {
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .description {
            text-align: justify;
            margin-top: 20px;
        }

        .pdf-viewer-container {
            width: 100%;
            max-height: 80vh;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-top: 20px;
            overflow-y: auto;
            overflow-x: hidden;
            -webkit-overflow-scrolling: touch;
        }

        .pdf-page {
            margin-bottom: 20px;
            width: 100%;
            height: auto;
        }

        @media print {
            .navbar, .btn {
                display: none;
            }

            .content {
                box-shadow: none;
                border: none;
            }

            .pdf-viewer-container {
                height: 100vh;
            }
        }

        @media (max-width: 576px) {
            .metadata p {
                font-size: 13px;
            }

            .description {
                font-size: 14px;
            }

            h1, h4 {
                font-size: 20px;
            }

            .navbar-brand span {
                font-size: 16px;
            }

            .navbar-brand img {
                width: 40px;
                height: 40px;
            }

            .content {
                padding: 15px;
            }
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand d-flex align-items-center" href="#">
                <a href="https://samagrith.com" target="_blank">
                  <img src="{{ url_for('static', filename='images/samagrith-logo-in-nav-bar-p-500.png') }}" width="50" height="50" alt="Main Image">
                </a>
                <span class="ms-2 text-white">Samagrith</span>
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarContent">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarContent">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link text-white" href="#">Home</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container-fluid p-0">
        <div class="content">
            <div class="header">
                <h1>{{ item.name }}</h1>
            </div>

            {% if item_type == 'resource' %}
                <div class="metadata">
                    <p><strong>Topic:</strong> {{ item.topic }}</p>
                    <p><strong>Created At:</strong> {{ item.created_at.strftime('%d/%m/%Y') }}</p>
                    <p><strong>Field Type:</strong> {{ item.field_type }}</p>
                </div>

                <div class="image-container">
                    {% if item.main_image %}
                        <img src="data:image/png;base64,{{ item.main_image }}" alt="Main Image" class="img-fluid">
                    {% endif %}
                </div>

                <div class="description">
                    <p>{{ item.post_summary }}</p>
                    <div>{{ item.post_body | convert_html | safe }}</div>
                </div>

                {% if item.field_type == 'reports' and item.report_file %}
                    <div class="mt-3">
                        <h4>Report File</h4>
                        <div id="pdf-viewer-container" class="pdf-viewer-container"></div>
                        <a href="{{ item.report_file }}" class="btn btn-success mt-3" download="report.pdf">Download Report</a>
                        <button class="btn btn-primary mt-3" onclick="printPage()">Print Report</button>
                    </div>
                {% endif %}

                {% if item.field_type == 'media' and item.link %}
                    <div class="mt-3">
                        <a href="{{ item.link }}" class="btn btn-success" target="_blank">Link to Published Article</a>
                    </div>
                {% endif %}
            {% elif item_type == 'job' %}
                <div class="metadata">
                    <p><strong>Title:</strong> {{ item.title }}</p>
                    <p><strong>Posted On:</strong> {{ item.created_at.strftime('%d/%m/%Y') }}</p>
                </div>

                <div class="description">
                    <p>{{ item.description | convert_html | safe }}</p>
                </div>
            {% endif %}
        </div>
    </div>

    <script>
        function printPage() {
            window.print();
        }

        async function renderPDF(base64Data) {
            const pdfData = atob(base64Data.split(',')[1]);
            const pdfjsLib = window['pdfjs-dist/build/pdf'];
            pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

            const loadingTask = pdfjsLib.getDocument({ data: pdfData });
            const pdf = await loadingTask.promise;
            const container = document.getElementById('pdf-viewer-container');
            container.innerHTML = '';
            const containerWidth = container.clientWidth;

            for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                const page = await pdf.getPage(pageNum);
                const viewport = page.getViewport({ scale: 1 });
                const scale = containerWidth / viewport.width;
                const scaledViewport = page.getViewport({ scale });

                const canvas = document.createElement('canvas');
                canvas.className = 'pdf-page';
                const context = canvas.getContext('2d');
                canvas.height = scaledViewport.height;
                canvas.width = scaledViewport.width;

                container.appendChild(canvas);

                const renderContext = {
                    canvasContext: context,
                    viewport: scaledViewport
                };
                await page.render(renderContext).promise;
            }
        }

        const reportFile = "{{ item.report_file }}";
        if (reportFile && reportFile.startsWith('data:application/pdf;base64,')) {
            renderPDF(reportFile);
        }

        window.addEventListener('resize', () => {
            if (reportFile && reportFile.startsWith('data:application/pdf;base64,')) {
                renderPDF(reportFile);
            }
        });
    </script>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

dummy_user = {
    "username": "merlynp",
    "password": "merlynp123"
}

@app.route('/')
def home():
    if 'user' in session:
        return render_template('index.html')  # Show main page if logged in
    return redirect(url_for('login'))  # Redirect to login if not logged in

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == dummy_user['username'] and password == dummy_user['password']:
            session['user'] = username
            return redirect(url_for('home'))
        else:
            return "Invalid credentials, please try again."
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/createresource')
def createresource():
    return render_template('createresource.html')

@app.route('/viewresource')
def viewresource():
    return render_template('UpdateandDelete.html')

@app.route('/createjob')
def createjob():
    return render_template('createjob.html')

@app.route('/updatejob')
def updatejob():
    return render_template('updateanddeletejob.html')

# Routes for Resources
@app.route('/api/resources', methods=['POST'])
def create_resource():
    try:
        data = request.json
        print("Received data keys:", data.keys())  # Debug: Check what keys are in the request
        
        main_image_b64 = data.get('main_image')
        thumbnail_image_b64 = data.get('thumbnail_image')
        report_file_b64 = data.get('report_file')
        
        # Debug log to check report file
        print("Report file present:", report_file_b64 is not None)
        
        if not main_image_b64:
            return jsonify({'error': 'main_image is required'}), 400

        # Remove base64 prefixes if present
        if main_image_b64.startswith("data:image"):
            main_image_b64 = main_image_b64.split(",")[1]
        if thumbnail_image_b64 and thumbnail_image_b64.startswith("data:image"):
            thumbnail_image_b64 = thumbnail_image_b64.split(",")[1]
        
        # Handle report file base64 data if present
        report_file_data = report_file_b64 if report_file_b64 else None

        # Get other form fields
        field_type = data.get('field_type')
        
        # Only process link if it exists in the data
        try:
            link = data.get('link')
        except:
            link = None

        # Store the base64 strings in the database
        new_resource = Resource(
            name=data['name'],
            slug=data['slug'],
            post_body=data.get('post_body'),
            post_summary=data.get('post_summary'),
            main_image=main_image_b64,
            thumbnail_image=thumbnail_image_b64,
            featured=data.get('featured', False),
            color=data.get('color'),
            col_span=data.get('col_span', 1),
            topic=data.get('topic'),
            field_type=field_type,
            link=link,
            report_file=report_file_data  # Store the report file data
        )

        new_resource.cms_link = "https://samagrithtsk.onrender.com/" + new_resource.generate_cms_link()
        db.session.add(new_resource)
        db.session.commit()

        return jsonify({'message': 'Resource created successfully', 'resource': new_resource.to_dict()}), 201

    except Exception as e:
        print("Error in create_resource:", str(e))  # Debug log for exception
        return jsonify({'error': str(e)}), 400

# Routes for Jobs
@app.route('/api/jobs', methods=['POST'])
def create_job():
    try:
        data = request.json
        new_job = Job(
            name=data['name'],
            title=data['title'],
            description=data.get('description')
        )

        db.session.add(new_job)
        db.session.commit()
        new_job.cms_link = "https://samagrithtsk.onrender.com/" + new_job.generate_cms_link()
        db.session.commit()
        return jsonify({'message': 'Job created successfully', 'job': new_job.to_dict()}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Dynamic CMS Pages
@app.route('/cms/<item_type>/<identifier>')
def cms_page(item_type, identifier):
    if item_type == 'resource':
        item = Resource.query.filter_by(slug=identifier).first_or_404()
    elif item_type == 'job':
        item = Job.query.get_or_404(identifier)
    else:
        return jsonify({'error': 'Invalid item type'}), 400

    return render_template_string(CMS_TEMPLATE, item=item, item_type=item_type)

# Get Resources
@app.route('/api/resources', methods=['GET'])
def get_resources():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    pagination = Resource.query.order_by(desc(Resource.created_at)).paginate(
        page=page, per_page=per_page, error_out=False)
    
    resources = pagination.items

    return jsonify({
        'resources': [resource.to_dict() for resource in resources],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page
    })



# Get Jobs
@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    pagination = Job.query.order_by(desc(Job.created_at)).paginate(
        page=page, per_page=per_page, error_out=False)

    jobs = pagination.items

    return jsonify({
        'jobs': [job.to_dict() for job in jobs],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page
    })

# Update Resource by Name
@app.route('/api/resources/<int:id>', methods=['PUT'])
def update_resource(id):
    try:
        resource = Resource.query.get(id)
        if not resource:
            return jsonify({'error': 'Resource not found'}), 404

        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update only provided fields
        updatable_fields = {
            'name', 'slug', 'post_body', 'post_summary', 'main_image', 'thumbnail_image',
            'featured', 'color', 'col_span', 'topic', 'field_type', 'cms_link', 'link',
            'report_file'  # Only include fields that exist in the model
        }

        for key, value in data.items():
            if key in updatable_fields:
                setattr(resource, key, value)

        # Regenerate CMS link if needed
        resource.cms_link = "https://samagrithtsk.onrender.com/" + resource.generate_cms_link()

        db.session.commit()
        return jsonify({'message': 'Resource updated successfully', 'resource': resource.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# Delete Resource by Name
@app.route('/api/resources', methods=['DELETE'])
def delete_resource():
    try:
        name = request.args.get('name')
        if not name:
            return jsonify({'error': 'Resource name is required'}), 400

        resource = Resource.query.filter_by(name=name).first()
        if not resource:
            return jsonify({'error': 'Resource not found'}), 404

        db.session.delete(resource)
        db.session.commit()
        return jsonify({'message': 'Resource deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@app.route('/api/jobs/<int:job_id>', methods=['PUT'])
def update_job(job_id):
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'message': 'Job not found'}), 404
    
    data = request.get_json()
    job.name = data.get('name', job.name)
    job.title = data.get('title', job.title)
    job.description = data.get('description', job.description)
    
    db.session.commit()
    return jsonify({'message': 'Job updated successfully'})

@app.route('/api/jobs/<int:job_id>', methods=['DELETE'])
def delete_job(job_id):
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'message': 'Job not found'}), 404
    
    db.session.delete(job)
    db.session.commit()
    return jsonify({'message': 'Job deleted successfully'})

@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({'job': job.to_dict()}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
