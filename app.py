from flask import Flask, render_template, request, Response, jsonify
import cv2
import os
import time
import json
from datetime import datetime, timedelta
import uuid

# Initialize the Flask app
app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global variables for live session tracking
live_session_data = {}
current_session_id = None

# Load pre-trained classifiers
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# Function to detect sleep/awake status in video
def detect_sleep_in_video(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video file.")
        return {
            'total_time': 0,
            'sleeping_time': 0,
            'engaged_time': 0,
            'sleeping_percentage': 0,
            'engaged_percentage': 0
        }

    # Initialize counters
    total_frames = 0
    sleeping_frames = 0
    engaged_frames = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            total_frames += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Use more conservative parameters to avoid OpenCV errors
            try:
                faces = face_cascade.detectMultiScale(gray, 1.1, 3, minSize=(60, 60), maxSize=(300, 300))
            except cv2.error as e:
                print(f"Face detection error: {e}")
                # Skip this frame if face detection fails
                continue

            frame_has_sleeping = False
            for (x, y, w, h) in faces:
                # Ensure ROI is within bounds
                if y + int(h/2) > gray.shape[0] or x + w > gray.shape[1]:
                    continue
                    
                # Focus on upper half of face for eye detection
                roi_gray = gray[y:y + int(h/2), x:x + w]
                
                # Use more conservative eye detection parameters
                try:
                    eyes = eye_cascade.detectMultiScale(roi_gray, 1.1, 3, minSize=(15, 15), maxSize=(60, 60))
                except cv2.error as e:
                    print(f"Eye detection error: {e}")
                    # If eye detection fails, assume sleeping
                    sleeping_frames += 1
                    frame_has_sleeping = True
                    break
                
                # Use same logic as live detection
                if len(eyes) >= 2:  # Both eyes detected
                    engaged_frames += 1
                else:  # Less than 2 eyes detected - sleeping
                    sleeping_frames += 1
                    frame_has_sleeping = True
                    break

            # If no face detected, don't count the frame
            if len(faces) == 0:
                total_frames -= 1

    except Exception as e:
        print(f"Error processing video: {e}")
        # Return default values if processing fails
        return {
            'total_time': 0,
            'sleeping_time': 0,
            'engaged_time': 0,
            'sleeping_percentage': 0,
            'engaged_percentage': 0
        }
    finally:
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
    global current_session_id, live_session_data
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Improve face detection with better parameters
        faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(80, 80))

        current_status = "No Face Detected"
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            
            # Focus on upper half of face for eye detection
            roi_gray = gray[y:y + int(h/2), x:x + w]
            roi_color = frame[y:y + int(h/2), x:x + w]
            
            # Improve eye detection with better parameters
            eyes = eye_cascade.detectMultiScale(roi_gray, 1.1, 5, minSize=(20, 20), maxSize=(80, 80))
            
            # More sophisticated eye state detection
            if len(eyes) >= 2:  # Both eyes detected
                current_status = "Engaged"
                # Draw rectangles around detected eyes
                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)
            elif len(eyes) == 1:  # Only one eye detected - likely partially closed
                current_status = "Sleeping"
                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 0, 255), 2)
            else:  # No eyes detected - likely closed
                current_status = "Sleeping"

            cv2.putText(frame, current_status, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            print(f"Student Status: {current_status}")

        # Update live session data if session is active
        if current_session_id and current_session_id in live_session_data:
            session = live_session_data[current_session_id]
            if session['active']:
                session['total_frames'] += 1
                if current_status == "Engaged":
                    session['engaged_frames'] += 1
                elif current_status == "Sleeping":
                    session['sleeping_frames'] += 1
                session['current_status'] = current_status
                session['last_update'] = datetime.now().isoformat()

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

def generate_detailed_report(session_data):
    """Generate comprehensive analytics report"""
    
    # Calculate additional metrics
    total_frames = session_data['total_frames']
    engaged_frames = session_data['engaged_frames']
    sleeping_frames = session_data['sleeping_frames']
    session_duration = session_data['session_duration']
    
    engagement_rate = (engaged_frames / total_frames * 100) if total_frames > 0 else 0
    sleeping_rate = (sleeping_frames / total_frames * 100) if total_frames > 0 else 0
    
    # Calculate time-based metrics
    engaged_time = (engaged_frames / 30) if total_frames > 0 else 0  # Assuming 30 fps
    sleeping_time = (sleeping_frames / 30) if total_frames > 0 else 0
    
    # Performance analysis
    performance_score = min(100, max(0, engagement_rate))
    
    if performance_score >= 80:
        performance_level = "Excellent"
        performance_color = "#27ae60"
    elif performance_score >= 60:
        performance_level = "Good"
        performance_color = "#3498db"
    elif performance_score >= 40:
        performance_level = "Fair"
        performance_color = "#f39c12"
    else:
        performance_level = "Needs Improvement"
        performance_color = "#e74c3c"
    
    # Recommendations based on analysis
    recommendations = []
    if sleeping_rate > 30:
        recommendations.append("High sleep detection rate detected. Consider adjusting lighting or seating position.")
    if engagement_rate < 50:
        recommendations.append("Low engagement detected. Consider interactive activities or breaks.")
    if session_duration > 3600:  # More than 1 hour
        recommendations.append("Long session duration. Consider shorter, focused sessions.")
    
    if not recommendations:
        recommendations.append("Good engagement levels maintained throughout the session.")
    
    report = {
        'session_id': session_data['session_id'],
        'session_start': session_data['session_start'],
        'session_duration': session_duration,
        'total_frames': total_frames,
        'engaged_frames': engaged_frames,
        'sleeping_frames': sleeping_frames,
        'engagement_rate': round(engagement_rate, 2),
        'sleeping_rate': round(sleeping_rate, 2),
        'engaged_time': round(engaged_time, 2),
        'sleeping_time': round(sleeping_time, 2),
        'performance_score': round(performance_score, 1),
        'performance_level': performance_level,
        'performance_color': performance_color,
        'recommendations': recommendations,
        'generated_at': datetime.now().isoformat()
    }
    
    return report

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
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            
            # Check if file is a valid video
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return "Error: Invalid video file. Please upload a valid video format (MP4, AVI, MOV, etc.)"
            cap.release()
            
            analysis = detect_sleep_in_video(file_path)
            
            # Check if analysis was successful
            if analysis['total_time'] == 0:
                return "Error: Could not process the video. Please ensure the video contains clear faces and try again."

            # Prepare session_data for report generation
            session_data = {
                'session_id': str(uuid.uuid4()),
                'session_start': datetime.now().isoformat(),
                'session_duration': analysis['total_time'],
                'total_frames': int((analysis['total_time'] + analysis['sleeping_time']) * 30),  # fallback if needed
                'engaged_frames': int(analysis['engaged_time'] * 30),
                'sleeping_frames': int(analysis['sleeping_time'] * 30),
                'current_status': 'Completed',
                'active': False,
                'last_update': datetime.now().isoformat()
            }
            report = generate_detailed_report(session_data)
            return render_template('live_report.html', report=report)
            
        except Exception as e:
            print(f"Upload error: {e}")
            return f"Error processing video: {str(e)}. Please try again with a different video file."

# Route for live video feed
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Route for live detection page
@app.route('/live')
def live_detection():
    return render_template('live.html')

# Route to start a new live session
@app.route('/start_live_session', methods=['POST'])
def start_live_session():
    global current_session_id, live_session_data
    
    session_id = str(uuid.uuid4())
    current_session_id = session_id
    
    live_session_data[session_id] = {
        'session_id': session_id,
        'session_start': datetime.now().isoformat(),
        'session_duration': 0,
        'total_frames': 0,
        'engaged_frames': 0,
        'sleeping_frames': 0,
        'current_status': 'Initializing',
        'active': True,
        'last_update': datetime.now().isoformat()
    }
    
    return jsonify({'success': True, 'session_id': session_id})

# Route to stop live session
@app.route('/stop_live_session', methods=['POST'])
def stop_live_session():
    global current_session_id, live_session_data
    
    if current_session_id and current_session_id in live_session_data:
        session = live_session_data[current_session_id]
        session['active'] = False
        session['session_duration'] = (datetime.now() - datetime.fromisoformat(session['session_start'])).total_seconds()
        
        return jsonify({'success': True, 'session_id': current_session_id})
    
    return jsonify({'success': False, 'error': 'No active session found'})

# Route to generate live report
@app.route('/generate_live_report', methods=['POST'])
def generate_live_report():
    global current_session_id, live_session_data
    
    try:
        data = request.get_json()
        
        if current_session_id and current_session_id in live_session_data:
            session_data = live_session_data[current_session_id].copy()
            session_data['session_duration'] = data.get('sessionDuration', 0)
            session_data['engaged_frames'] = data.get('engagedFrames', 0)
            session_data['sleeping_frames'] = data.get('sleepingFrames', 0)
            session_data['total_frames'] = data.get('totalFrames', 0)
            
            # Generate detailed report
            detailed_report = generate_detailed_report(session_data)
            
            # Store the report
            live_session_data[current_session_id]['report'] = detailed_report
            
            return jsonify({'success': True, 'session_id': current_session_id})
        else:
            return jsonify({'success': False, 'error': 'No active session found'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Route to get current session status
@app.route('/get_session_status')
def get_session_status():
    global current_session_id, live_session_data
    
    if current_session_id and current_session_id in live_session_data:
        session = live_session_data[current_session_id]
        return jsonify({
            'success': True,
            'session_id': current_session_id,
            'active': session['active'],
            'total_frames': session['total_frames'],
            'engaged_frames': session['engaged_frames'],
            'sleeping_frames': session['sleeping_frames'],
            'current_status': session['current_status'],
            'last_update': session['last_update']
        })
    
    return jsonify({'success': False, 'error': 'No active session'})

# Route to display live report
@app.route('/live_report')
def live_report():
    global current_session_id, live_session_data
    
    if current_session_id and current_session_id in live_session_data:
        session_data = live_session_data[current_session_id]
        if 'report' in session_data:
            return render_template('live_report.html', report=session_data['report'])
    
    return "No report available. Please generate a report first."

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
