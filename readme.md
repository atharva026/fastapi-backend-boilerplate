# FastAPI – Alembic – SQLAlchemy Boilerplate

A **production-ready backend boilerplate** built with **FastAPI**, **SQLAlchemy**, and **Alembic**, featuring **JWT-based authentication**, **user management**, and a **feature-based modular architecture** and includes **Redis integration** for efficient **access & refresh token management**..

This template is designed for building scalable, maintainable APIs with clean separation of concerns and best practices baked in from day one.

## Getting Started Setup

### Prerequisites
- Python (3.10+ recommended)
- PostgreSQL (or your preferred DB)
- Redis (for token storage)

### Installation
Clone the repository
```
git clone https://github.com/atharva026/fastapi-alembic-sqlalchemy-boilerplate

cd fastapi-alembic-sqlalchemy-boilerplate
```

### Virtual Environment
Create and activate virtual environment
```bash
python -m venv venv

source venv/bin/activate  # Linux/Mac

venv\Scripts\activate     # Windows
```

### Project Dependencies

#### Install
After activating the virtual environment, install all required dependencies using:
```bash
pip install -r requirements.txt
```

#### Update 
After installing or upgrading project dependencies, update `requirements.txt`
```bash
pip freeze > requirements.txt
```
> **Note**: Ensure this command is run inside the project’s virtual environment to avoid freezing unwanted packages.

### Environment Configuration & Files
This project supports automatic loading of environment-specific `.env` files using Pydantic Settings. Default is dev(`.env.dev`)

The application dynamically selects which env file to load based on the value of `ENVIRONMENT` variable.

#### Set environment variable
- On Linux / macOS (terminal)
    ```
    export ENVIRONMENT=prod
    ```

- On Windows (CMD)
    ```
    set ENVIRONMENT=prod
    ```

- On Windows (PowerShell)
    ```
    $env:ENVIRONMENT="prod"
    echo $env:ENVIRONMENT
    Remove-Item Env:ENVIRONMENT
    ```

Refer `.env.sample` for used env variables across the project

Create separate env files for each environment:
```
.env.dev
.env.staging
.env.prod
```

When the application starts:

| ENVIRONMENT | Loaded file
|-------------|---------------
| dev	      | .env.dev
| staging	  | .env.staging
| prod	      | .env.prod
| not set	  | .env.dev

#### Nested Configuration Support
Nested configs use __ as a delimiter. Example
```
DB_CONFIG__DB_NAME=
EMAIL_CONFIG__EMAIL_HOST=
REDIS_CONFIG__REDIS_HOST=l
```

### Initialize database & migrations
Make sure your database is running and the connection settings in your `.env.*` file are correct. Refer to `.env.sample` for required database env variables.

Then, initialize the database schema using Alembic migrations:

```
alembic upgrade head
```

### Redis Setup
Make sure Redis is installed and running on your machine. Configure Redis connection settings in your `.env.*` file. Refer to `.env.sample` for required Redis env variables.

### Run the application
Start the FastAPI application using Uvicorn:

```bash
uvicorn src.app.main:app --reload
``` 
For Swagger docs visit: http://localhost:8000/docs


## Database Migrations with Alembic
We use **Alembic** for managing schema migrations 

### Prerequisites
- Python ≥ 3.12.0 (3.10+ recommended)
- PostgreSQL installed (or your preferred DB)
- `.env.*` file with a valid **DATABASE** credentials

### Model Registration Requirement (Important)
When adding a new database model (table), you must import it in  `src/app/models/__init__.py`, otherwise Alembic will not detect the table during migration generation. For example:

If you add a new model file:
```bash
src/app/models/user.py
```

Update `src/app/models/__init__.py`:
```python
from src.app.models import user       # Incorrect
from src.app.models.user import User  # Correct
```
> **Note**: Always import the model class, not just the module.

--- 

### Developer Checklist
Before running Alembic migrations, confirm:
- Model inherits from Base
- Model is imported in `src/app/models/__init__.py`

After running Alembic migrations, confirm:
- Always Review Migration Files Before Applying
    Never trust Alembic blindly.

    Check for:
    - DROP TABLE
    - DROP COLUMN
    - ALTER COLUMN TYPE
    - nullable=False on existing columns
    - Missing server_default
    
    These operations can cause data loss or downtime.

---

### Create New Migration

To generate a migration after modifying or creating new SQLAlchemy models:

```bash
alembic revision --autogenerate -m "Your migration message"
```

This creates a migration file in the versions folder.

> **Note**: Use meaningful migration messages & Automatically generated migrations don’t guarantee correctness, always verify the automatically generated migration code
>
> For example, column renames may be treated as drop + add instead of `ALTER`, which you can manually fix.
--- 

### Apply Migrations (Upgrade DB)

Apply the latest migrations to the database:

```bash
alembic upgrade head
```

To upgrade a specific version:

``` bash
alembic upgrade <revision_id>
```

---

### Downgrade (Rollback)

To revert the last migration:

```bash
alembic downgrade -1
```

To downgrade to a specific revision:

```bash
alembic downgrade <revision_id>
```

**Tips**
- Use meaningful migration messages.
- Keep your model imports updated in `src/app/models/__init__.py`.
- Review and test migrations in a local environment before applying in staging or production.

## Contributing
Feel free to open issues or submit pull requests if you want to improve the project.