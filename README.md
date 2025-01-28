# Student Behavior Monitoring System

A real-time student engagement monitoring system built with Python, Flask, and OpenCV that analyzes student behavior through facial detection and eye tracking.

## Features

- Real-time student engagement monitoring through webcam
- Video file upload and analysis
- Automated detection of "Engaged" vs "Sleeping" states
- Live analytics with engagement percentages and duration metrics
- Web-based interface for easy access and monitoring

## Technical Stack

- Python
- Flask (Web Framework)
- OpenCV (Computer Vision)
- HTML/CSS (Frontend)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Tameem2003/Monitor-AI.git
cd Monitor-AI
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your web browser and navigate to `http://localhost:5000`

## Usage

1. **Live Monitoring**: Click on "Live Detection" to start monitoring through your webcam
2. **Video Analysis**: Upload a video file to analyze student engagement over a recorded session
3. **View Analytics**: Get detailed metrics including:
   - Total monitoring time
   - Engagement percentage
   - Sleep detection stats

## Project Structure

```
Monitor-AI/
├── app.py              # Main application file
├── requirements.txt    # Project dependencies
├── static/            # Static files (CSS, JS)
│   └── uploads/       # Uploaded video files
└── templates/         # HTML templates
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
