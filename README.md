# My Flask App

This is a simple one-page Flask application that demonstrates the use of HTML templates, CSS, and JavaScript.

## Project Structure

```
my-flask-app
├── app.py               # Entry point of the Flask application
├── templates
│   └── index.html      # HTML structure for the one-page application
├── static
│   ├── css
│   │   └── styles.css   # CSS styles for the application
│   └── js
│       └── scripts.js    # JavaScript code for client-side functionality
├── requirements.txt     # Dependencies required for the Flask application
└── README.md            # Documentation for the project
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd my-flask-app
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```

4. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the application, execute the following command:
```
python app.py
```

The application will be accessible at `http://127.0.0.1:5000/`. Open this URL in your web browser to view the one-page application.