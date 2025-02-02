# AI Web Dev - Demo

A simple multi-agent system for automatic full-stack web development. It generates application around Flask framework.
It can create new files and update existing, install additional packages, test backend and frontend and recover from its own mistakes.

Live demo:

https://github.com/user-attachments/assets/f045822c-996a-44f4-a9a6-676b29265e2d

> [!NOTE]  
> Work in progres...

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd ai-coding-web
   ```

2. Create a virtual environment:
   ```
   python -m venv .venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```
     .venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source .venv/bin/activate
     ```

4. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Configure your OpenAI API key

Create `.env` file with your OpenAI API Key:
```
OPENAI_API_KEY=<your open ai API key>
```

## Usage

To run the application, execute the following command:
```
python app.py
```

The application will be accessible at `http://127.0.0.1:5000/`. Open this URL in your web browser to view the one-page application.
