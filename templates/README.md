# Schedule Management System

A web-based schedule management system built with Flask, MySQL, and PyMySQL. This application allows multiple users to manage machine operators and their schedules.

## Features

- User authentication (login/register)
- Machine management (add, edit, delete)
- Operator management (add, edit, delete)
- Weekly schedule management
- Shift rotation system
- Operator availability tracking
- Responsive web interface

## Prerequisites

- Python 3.7 or higher
- MySQL Server
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd schedule-management
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the following content:
```
DB_HOST=localhost
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=schedule_management
SECRET_KEY=your_secret_key
```

5. Create the database and tables:
```bash
mysql -u your_mysql_username -p < schema.sql
```

## Running the Application

1. Start the Flask development server:
```bash
python main.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

## Usage

1. Register a new account or login with existing credentials
2. Navigate to the home page to manage machines and operators
3. Use the schedule page to assign operators to machines and shifts
4. Operators can be marked as available/unavailable for specific weeks
5. The system automatically handles shift rotation

## Database Schema

The application uses the following main tables:
- users: Stores user account information
- machines: Stores machine information and status
- operators: Stores operator information and status
- shifts: Defines different shift types and times
- schedule: Stores operator assignments to machines and shifts
- operator_availability: Tracks operator availability for specific weeks

## Security Features

- Password hashing
- Session management
- CSRF protection
- Input validation
- SQL injection prevention

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
