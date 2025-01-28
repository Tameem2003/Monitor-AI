from flask import Flask, render_template, request, Response
import cv2
import os
import time

# Initialize the Flask app
app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load pre-trained classifiers
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# Function to detect sleep/awake status in video
def detect_sleep_in_video(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    # Initialize counters
    total_frames = 0
    sleeping_frames = 0
    engaged_frames = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        total_frames += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        frame_has_sleeping = False
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y + h, x:x + w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            if len(eyes) == 0:
                sleeping_frames += 1
                frame_has_sleeping = True
                break

        if not frame_has_sleeping and len(faces) > 0:
            engaged_frames += 1

    cap.release()

    # Calculate statistics
    total_time = total_frames / 30  # Assuming 30 fps
    sleeping_time = sleeping_frames / 30
    engaged_time = engaged_frames / 30
    
    # Calculate percentages
    sleeping_percentage = (sleeping_frames / total_frames * 100) if total_frames > 0 else 0
    engaged_percentage = (engaged_frames / total_frames * 100) if total_frames > 0 else 0

    analysis = {
        'total_time': round(total_time, 2),
        'sleeping_time': round(sleeping_time, 2),
        'engaged_time': round(engaged_time, 2),
        'sleeping_percentage': round(sleeping_percentage, 2),
        'engaged_percentage': round(engaged_percentage, 2)
    }
    
    return analysis

def generate_frames():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            roi_gray = gray[y:y + h, x:x + w]

            eyes = eye_cascade.detectMultiScale(roi_gray)
            if len(eyes) == 0:
                status = "Sleeping"
            else:
                status = "Engaged"

            cv2.putText(frame, status, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            print(f"Student Status: {status}")

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

# Route for the home page
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle file upload
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part"

    file = request.files['file']
    if file.filename == '':
        return "No selected file"

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        analysis = detect_sleep_in_video(file_path)
        return render_template('analysis.html', analysis=analysis)

# Route for live video feed
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Route for live detection page
@app.route('/live')
def live_detection():
    return render_template('live.html')

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
